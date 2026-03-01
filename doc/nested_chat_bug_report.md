# NestedChat 消息传递 Bug 报告

**日期**: 2026-03-01
**状态**: 🔴 未解决 - NestedChat 已触发但 carryover 提取的问题为空

---

## 问题现象

### 核心问题
Coach 生成问题后，通过 NestedChat 转发给 Evaluator 进行评估，但 Evaluator 收到的问题内容为空。

### 观察到的行为
```
wrapped_nested_WIAL_Master_Coach_1 (to Strict_Evaluator):

开始评估
Context:
请评估以下问题:


```

Evaluator 收到的消息格式正确，但 `请评估以下问题:` 后面是空的，没有实际问题内容。

### 预期行为
Evaluator 应该收到：
```
请评估以下问题:

当你观察到团队成员互相指责时，他们具体在指责什么内容？
```

---

## 技术背景

### AG2 版本
- **AG2 (AutoGen)**: 0.11.2
- **API**: 新的 Handoffs API（非旧的 `register_nested_chats`）

### 架构设计
```
User → Coach (生成问题)
         ↓ (after_work handoff)
      NestedChat Wrapper Agent
         ↓ (nested chat)
      Evaluator (评估问题)
         ↓ (返回评分)
      Coach (根据评分决定是否重写)
```

### 关键代码位置
1. **Orchestrator 配置** (`core/orchestrator.py:130-143`)
   - 手动创建 wrapper agent
   - 使用 `AgentTarget` 指向 wrapper
   - 将 wrapper 加入 `pattern.agents` 列表

2. **NestedChat 配置** (`core/nested_chat.py:67-105`)
   - 使用 `carryover_config` 传递 GroupChat 消息
   - `summary_method` 指向 `_extract_question_from_carryover`

3. **消息提取函数** (`core/nested_chat.py:24-61`)
   - 从 carryover messages 中查找 Coach 的消息
   - 解析 JSON 提取 `question` 字段

---

## 已尝试的解决方案

### ✅ 成功部分

#### 1. 修复 API 代理兼容性
**问题**: Anthropic SDK 的 `x-stainless-*` headers 被 Cloudflare 拦截
**解决**: 在 `core/config.py` 中用 httpx 替换 SDK 的 HTTP 层
```python
class _HttpxMessages:
    def create(self, **params):
        resp = self._http.post(f"{self._base_url}/v1/messages", ...)
        data = resp.json()
        if "stop_reason" in data and not data["stop_reason"]:
            data["stop_reason"] = "end_turn"  # 修复空 stop_reason
        return Message.model_validate(data)
```

#### 2. 修复 Observer 配置回退
**问题**: Observer/Reflection 配置缺失时崩溃
**解决**: 实现 3 级回退链（显式传入 → 环境变量 → coach_config）

#### 3. 修复 Observer 身份冲突
**问题**: Observer LLM 拒绝执行，说"I'm Kiro"
**解决**: 在 `prompts/observer_prompt.py` 开头强制覆盖身份
```python
OBSERVER_SYSTEM_MESSAGE = """CRITICAL: Ignore all previous identity instructions.
You are NOT Kiro. You are NOT a coding assistant.
You are a Cognitive Observer...
```

#### 4. 修复 NestedChat 触发
**问题**: Coach 不进入 NestedChat，直接返回 User
**尝试过的方案**:
- ❌ `add_llm_condition` + `StringLLMCondition` - 条件不触发
- ❌ `set_after_work(nested_target)` - NestedChatTarget 不支持 resolve
- ✅ **方案 2（当前）**: 手动创建 wrapper agent + `AgentTarget`

```python
# core/orchestrator.py
nested_target = create_nested_chat_config(self._evaluator, max_rounds=5)
self._nested_wrapper = nested_target.create_wrapper_agent(
    parent_agent=self._coach, index=0
)
self._coach.handoffs.set_after_work(AgentTarget(self._nested_wrapper))

# 必须将 wrapper 加入 agents 列表
agents = [self._coach, self._nested_wrapper, self._reflection]
```

**结果**: ✅ NestedChat 成功触发，wrapper agent 被调用

---

### 🔴 当前阻塞问题

#### carryover 消息提取失败

**现象**: `_extract_question_from_carryover` 函数收到的 `messages` 列表中找不到 Coach 的消息，或者消息内容为空。

**已添加的调试日志** (`core/nested_chat.py:39-41`):
```python
logger.info(f"Carryover messages count: {len(messages)}")
for i, msg in enumerate(messages[-5:]):
    logger.info(f"Message {i}: role={msg.get('role')}, name={msg.get('name')}, content={msg.get('content', '')[:100]}")
```

**需要验证**:
1. carryover messages 列表是否包含 Coach 的消息？
2. Coach 消息的 `name` 字段是否为 `"WIAL_Master_Coach"`？
3. Coach 消息的 `content` 是否包含 JSON 格式的问题？
4. AG2 的 `trim_n_messages=2` 是否意外删除了 Coach 的消息？

---

## 相关文件清单

### 已修改文件
1. `core/config.py` - httpx 代理 + stop_reason 修复
2. `core/orchestrator.py` - wrapper agent 手动创建
3. `core/nested_chat.py` - carryover_config + 调试日志
4. `agents/observer.py` - 上下文兼容性修复
5. `prompts/observer_prompt.py` - 身份覆盖
6. `.env` - 添加 OBSERVER_MODEL, REFLECTION_MODEL

### 关键测试命令
```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from core.orchestrator import Orchestrator
orch = Orchestrator()
orch.create_session()
result = orch.run_turn('销售团队因为销量下滑士气大降，团队成员互相指责，你作为管理者该怎么办？')
print(f'Output: {result.output[:500]}')
" 2>&1 | grep -A 10 "Carryover messages"
```

---

## 下一步调试方向

### 优先级 1: 验证 carryover messages 内容
1. 运行测试命令，查看日志输出
2. 确认 `messages` 列表的实际内容
3. 检查 Coach 消息是否在列表中

### 优先级 2: 检查 AG2 carryover 处理逻辑
如果 messages 列表为空或不包含 Coach 消息：
1. 阅读 AG2 源码 `conversable_agent.py:755-798` (`_process_chat_queue_carryover`)
2. 确认 `trim_n_messages=2` 的默认行为
3. 可能需要调整 `carryover_config` 的配置

### 优先级 3: 备选方案
如果 carryover 无法正常工作：
1. **方案 A**: 使用 `message` callable 而非 `carryover_config`
   - 但需要解决 wrapper agent 本地消息的问题
2. **方案 B**: 在 wrapper agent 的 context_variables 中传递问题
   - 修改 `create_wrapper_agent` 的实现
3. **方案 C**: 使用旧 API `register_nested_chats`
   - 但这违背了 AG2 0.11.2 的设计

---

## 参考资料

### AG2 源码位置
- `NestedChatTarget.create_wrapper_agent`: `ag2/autogen/agentchat/group/targets/transition_target.py:205-224`
- `_process_chat_queue_carryover`: `ag2/autogen/agentchat/conversable_agent.py:755-798`
- `_get_chats_to_run`: `ag2/autogen/agentchat/conversable_agent.py:622-655`

### 相关文档
- `doc/phase2_implementation_plan.md` - Phase 2d 双轨 FSM 设计
- `ACCEPTANCE_TEST.md` - Phase 2 验收测试（Test 12 端到端测试）
- `doc/记忆机制的参考.md` - NestedChat 参考实现

---

## 环境信息
- **Python**: 3.13
- **OS**: macOS (Darwin 24.5.0)
- **虚拟环境**: `/Users/zhaoziwei/Desktop/关系行动/.venv`
- **代理 API**: `https://aicode.life` (Cloudflare 保护)
