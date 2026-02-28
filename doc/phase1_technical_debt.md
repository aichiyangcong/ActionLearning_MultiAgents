# Phase 1 技术债详细分析

> **文档版本**: v1.0
> **分析日期**: 2026-02-28
> **基于**: Phase 1 MVP (commit c7cee5a) 代码审查

---

## 技术债 #1: AutoGen 是假的

### 问题描述

`core/autogen_adapter.py` (110 行) 是一个手写的 HTTP 客户端，伪装成 AG2 的 `ConversableAgent`。它用 `httpx` 直接调用 Anthropic API，完全绕过了 AG2 框架。

### 具体表现

```python
# core/autogen_adapter.py 第 23-53 行
class ConversableAgent:
    def __init__(self, name, system_message, llm_config, human_input_mode="NEVER"):
        # 提取 model, api_key, base_url
        self._api_key = llm_config["config_list"][0]["api_key"]
        self._model = llm_config["config_list"][0]["model"]
        # ...

    def generate_reply(self, messages: List[Dict[str, str]]) -> str:
        # 直接 POST /v1/messages
        response = httpx.Client().post(
            self._base_url,
            headers={"x-api-key": self._api_key, ...},
            json={"model": self._model, "messages": messages, ...}
        )
        return response.json()["content"][0]["text"]
```

**这个类没有任何 AG2 代码**：
- 没有 `import autogen`
- 没有多 Agent 协议
- 没有 `ConversationResult`
- 没有消息路由
- 只是一个 Anthropic API 的薄包装

### 影响范围

- `agents/master_coach.py` 第 10 行：`from core.autogen_adapter import ConversableAgent`
- `agents/evaluator.py` 第 10 行：同上
- `agents/user_proxy.py` 第 7 行：使用真实 `autogen.UserProxyAgent`，但被注释禁用

**结果**：整个系统实际上没有使用 AG2 框架，只是在用 AG2 的 API 形状。

### 为什么是技术债

1. **无法使用 AG2 的核心功能**：
   - 无法使用 `register_nested_chats`（虽然 `nested_chat.py` 写了，但从未被调用）
   - 无法使用 `GroupChat` 和 `GroupChatManager`
   - 无法使用 `Handoffs` 和 FSM 状态转移
   - 无法使用 `ContextVariables` 跨 Agent 共享状态

2. **维护成本高**：
   - 需要手动维护 HTTP 客户端代码
   - AG2 的 bug 修复和新特性无法自动获得
   - 与 AG2 社区脱节

3. **阻碍 Phase 2 实现**：
   - Phase 2 需要 `DefaultPattern` + Handoffs 实现双轨 FSM
   - Phase 2 需要 `FunctionTarget` 实现 Observer
   - Phase 2 需要 `NestedChatTarget` 实现 Coach→Evaluator 审查
   - 这些都是真实 AG2 的功能，假适配器无法提供

### Phase 2 解决方案

**Task 2a-B1**: 删除 `core/autogen_adapter.py`，修改所有 import 为 `from autogen import ConversableAgent`

---

## 技术债 #2: Nested Chat 是空架子

### 问题描述

`core/nested_chat.py` (72 行) 定义了 `setup_nested_chat()` 函数，返回正确的 AG2 `chat_queue` 配置，但这个函数**从未被 `main.py` 调用**。

### 具体表现

```python
# core/nested_chat.py 第 20-46 行
def setup_nested_chat(coach, evaluator, max_rounds=5):
    return [{
        "recipient": evaluator.get_agent(),
        "message": lambda sender_msg: _extract_question(sender_msg),
        "summary_method": "last_msg",
        "max_turns": max_rounds * 2,
    }]
```

这个配置是正确的，但 `main.py` 的 `real_review_loop()` 用的是手写 Python `for` 循环：

```python
# main.py 第 220-315 行
def real_review_loop(user_input, history, coach, evaluator, max_rounds=5):
    for round_num in range(1, max_rounds + 1):
        question = coach.generate_question(user_input)
        eval_result = evaluator.evaluate(question)
        if eval_result["pass"]:
            break
        # 手动拼接反馈到下一轮
        user_input = f"{user_input}\n\n上一轮问题: {question}\n评分: {score}/100\n反馈: {feedback}"
```

### 为什么是技术债

1. **重复造轮子**：AG2 的 `register_nested_chats` 已经实现了审查循环的逻辑，我们却用手写循环重新实现
2. **无法扩展**：手写循环只能处理 Coach→Evaluator 二人对话，无法扩展到多 Agent 场景
3. **上下文管理混乱**：通过字符串拼接传递历史，而非 AG2 的结构化消息历史
4. **与 AG2 生态脱节**：无法利用 AG2 的日志、监控、调试工具

### Phase 2 解决方案

**Task 2a-L1**: 重写 `nested_chat.py`，对齐真实 AG2 API
**Task 2a-L2**: 在 `orchestrator.py` 中使用 `NestedChatTarget` 实现审查循环

---

## 技术债 #3: 无状态

### 问题描述

每轮 `generate_question()` 和 `evaluate()` 都是无状态的单次调用，跨轮的"记忆"完全通过字符串拼接实现，无结构化记忆机制，无持久化存储。

### 具体表现

```python
# main.py 第 300 行
user_input = f"{user_input}\n\n上一轮问题: {question}\n评分: {score}/100\n反馈: {feedback_text}"
```

**问题**：
1. **Token 线性膨胀**：每轮对话都把完整历史拼接到 `user_input`，第 5 轮时 token 消耗是第 1 轮的 5 倍
2. **无语义压缩**：只是简单拼接，没有提取关键信息
3. **无持久化**：`ConversationHistory` 只是内存中的 Python 列表，重启程序后全部丢失
4. **无跨会话记忆**：每次对话都是全新开始，无法记住学习者的思维模式、盲点、成长轨迹

### 影响

```python
# main.py 第 46-79 行
class ConversationHistory:
    def __init__(self):
        self.records: List[ConversationRecord] = []  # 纯内存

    def add(self, record: ConversationRecord):
        self.records.append(record)  # 无持久化
```

**Agent 跨轮状态**：
- `generate_reply()` 传入的 `messages` 列表只含当轮消息
- 无结构化的认知状态（问题深度、假设、盲点、情绪轨迹）
- 无法判断何时应该切换到反思轨（只能靠固定轮次）

### 为什么是技术债

1. **无法实现 AI 驱动的轨道切换**：没有认知状态，Observer 无法判断 `reflection_readiness`
2. **无法实现个性化教练**：无法记住学习者的特点，每次都是"陌生人"
3. **性能问题**：Token 线性膨胀，长对话成本高
4. **数据丢失风险**：无持久化，程序崩溃或重启后历史全部丢失

### Phase 2 解决方案

**Phase 2b**: 实现三层记忆系统
- L1: 认知状态 (~400 tokens)，每轮覆写
- L2: 会话摘要链 (~200 tokens)，阶段追加
- L3: 学习者画像 (~300 tokens)，跨会话渐进更新
- Raw: JSONL 对话日志，只追加

**Phase 2c**: 实现 Observer Agent，每轮提取认知状态，驱动轨道切换

---

## 技术债优先级

| 技术债 | 优先级 | 阻塞 Phase 2 | 解决阶段 |
|--------|--------|--------------|----------|
| #1 AutoGen 是假的 | **P0** | 是 | Phase 2a |
| #2 Nested Chat 是空架子 | **P0** | 是 | Phase 2a |
| #3 无状态 | **P1** | 部分 | Phase 2b + 2c |

**结论**：技术债 #1 和 #2 必须在 Phase 2a 解决，否则无法进行后续开发。技术债 #3 在 Phase 2b/2c 解决。

---

## 参考

- Phase 1 代码：commit `c7cee5a`
- Phase 2 实施计划：`doc/phase2_implementation_plan.md`
- AG2 源码分析：探索 agent 报告（会话历史）
