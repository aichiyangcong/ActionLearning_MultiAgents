# Phase 2 实施计划：真实 AG2 编排 + Observer 记忆系统 + 双轨 FSM

> **版本**: v1.0
> **作者**: CTO Architecture
> **日期**: 2026-02-28
> **基于**: Phase 1 MVP (commit c7cee5a) + 记忆机制参考研究

---

## Context

Phase 1 MVP 存在三个技术债：

1. **AutoGen 是假的** — `core/autogen_adapter.py` 用 httpx 直接调 Anthropic API，完全绕过 AG2 框架
2. **Nested Chat 是空架子** — `core/nested_chat.py` 写了但从未被 `main.py` 调用，实际用手写 for 循环
3. **无状态** — 每轮调用独立，跨轮"记忆"靠字符串拼接，无持久化

Phase 2 目标：还技术债 + 实现 AI 驱动的双轨切换 + 三层记忆系统。

---

## 关键架构决策

### AG2 编排模式选择：`DefaultPattern` + Handoffs

| 方案 | 优劣 | 结论 |
|------|------|------|
| `register_nested_chats` 二人对话 | 能做 Actor-Critic，但无法扩展到多 Agent FSM | 不够 |
| `AutoPattern` (LLM 选人) | 每轮额外 LLM 调用选 speaker，浪费且不可控 | 过度 |
| **`DefaultPattern` + Handoffs** | Agent 自带确定性转移规则，`FunctionTarget` 做 Observer，`NestedChatTarget` 做审查 | **选它** |

**选择理由**：

- `DefaultPattern` 是 AG2 的最小化 Pattern，不做任何 speaker 选择，完全依赖 Agent 自身的 Handoffs 规则
- `FunctionTarget` 允许任意 Python 函数作为转移目标 — 完美匹配 Observer 的需求
- `NestedChatTarget` 是 AG2 一等公民，可将 Coach→Evaluator 审查包装为不可见的嵌套对话
- `ContextVariables` 提供跨 Agent 共享状态 — 天然的记忆系统载体

### AG2 Anthropic 支持：已验证原生支持

- `ag2/autogen/oai/anthropic.py` 实现完整的 `AnthropicClient`
- 只需 `"api_type": "anthropic"` + `"api_key"` 配置即可
- 支持 Claude 全系列模型（haiku/sonnet/opus），含最新 claude-opus-4-6
- 现有 `config.py` 的 `to_autogen_config()` 已经输出正确格式，无需修改

---

## 实施分为 4 个阶段，严格按依赖顺序

---

### Phase 2a: AG2 迁移（地基）

**目标**：删除假适配器，用真 AG2 跑通 Coach→Evaluator 的 Nested Chat 审查

#### Step 1: 删除假适配器，修复 import

**删除：**
- `action_learning_coach/core/autogen_adapter.py`

**修改：**
- `agents/master_coach.py` — `from core.autogen_adapter import ConversableAgent` → `from autogen import ConversableAgent`
- `agents/evaluator.py` — 同上
- `agents/__init__.py` — 恢复 UserProxy 导出
- `agents/user_proxy.py` — 对齐新编排
- `core/__init__.py` — 移除 `ConversableAgent` 从 autogen_adapter 的导出

Agent 包装类保留 `generate_question()` / `evaluate()` 用于 mock 模式和单元测试，但真实模式走 AG2 消息传递。

#### Step 2: 创建 Orchestrator

**新建：** `core/orchestrator.py` — Phase 2 的大脑

核心职责：
- `create_session()` — 创建所有 Agent、配置 Handoffs、初始化 ContextVariables
- `run_turn(user_input)` — 调用 `initiate_group_chat` 执行一轮完整交互
- 用 `NestedChatTarget` 实现 Coach→Evaluator 审查（替代手写 for 循环）

```
数据流（Phase 2a 阶段）：
User Input → UserProxy → Coach → NestedChat(Evaluator 审查循环) → 输出
```

#### Step 3: 重写 nested_chat.py

对齐真实 AG2 API，`chat_queue` 格式：

```python
chat_queue = [{
    "recipient": evaluator_agent,
    "message": callable,          # 提取 Coach 输出中的问题
    "summary_method": "last_msg",
    "max_turns": 10,              # 5 轮 × 2 turns
}]
```

#### Step 4: 更新 main.py

- 替换 `real_review_loop()` 为 `orchestrator.run_turn()`
- 保留 mock 模式不变

**Phase 2a 验证**：设置 ANTHROPIC_API_KEY，运行 `python main.py`，Coach 生成问题 → Evaluator 通过 AG2 Nested Chat 审查 → 最终问题输出。日志中可见 nested chat 交互。

---

### Phase 2b: 三层记忆系统

**目标**：实现恒定 ~900 token 的记忆架构 + 文件持久化

#### Step 1: 创建 memory 模块

**新建文件：**
```
memory/
├── __init__.py
├── cognitive_state.py   # L1: 认知状态 (~400 tokens)，每轮覆写
├── summary_chain.py     # L2: 会话摘要链 (~200 tokens)，阶段追加
├── learner_profile.py   # L3: 学习者画像 (~300 tokens)，跨会话渐进更新
├── raw_log.py           # Raw: JSONL 对话日志，只追加
└── session.py           # 文件 I/O 管理器
```

**存储结构：**
```
data/
├── sessions/{session_id}/
│   ├── cognitive_state.json    # L1, 每轮覆写
│   ├── summary_chain.json      # L2, 阶段追加
│   └── raw_dialogue.jsonl      # Raw, 只追加
└── learners/{learner_id}/
    └── profile.json            # L3, 跨会话渐进更新
```

**三层记忆数据结构：**

```python
# L1: 认知状态 (~400 tokens) — 每轮由 Observer 覆写
cognitive_state = {
    "current_topic": "团队跨部门协作效率低",
    "emotional_tone": "frustrated",
    "thinking_depth": "surface | analytical | reflective",
    "key_assumptions": [
        {"content": "认为问题出在流程", "turn": 5, "confidence": "high"}
    ],
    "blind_spots": ["回避权力关系讨论"],
    "anchor_quotes": ["每次周会定好的事,第二天就变了"],  # 用户原话优先
    "reflection_readiness": {
        "score": 0.72,
        "signals": ["已暴露两个核心假设", "出现认知矛盾但未自行察觉"]
    },
    "turn_number": 8
}

# L2: 会话摘要链 (~200 tokens) — 阶段性追加
summary_chain = [
    {
        "phase": "problem_clarification",
        "turns": "1-8",
        "summary": "学员从'效率低'逐步聚焦到'周会决策被推翻'",
        "anchor_quote": "每次周会定好的事,第二天就变了",
        "cognitive_shift": "从抱怨现象到触及权力结构"
    }
]

# L3: 学习者画像 (~300 tokens) — 跨会话，渐进更新
learner_profile = {
    "learner_id": "user_001",
    "thinking_patterns": ["倾向归因于外部环境", "善于类比但缺乏系统思考"],
    "growth_edges": ["从抱怨到反思自身角色的转变"],
    "blind_spots": ["回避权力关系讨论"],
    "response_preferences": ["对故事性问题响应好", "对直接追问会防御"],
    "session_count": 3,
    "last_session_summary": "..."
}
```

**设计原则：**

- 锚定引用优先用户原话（ChatGPT 启发：用户的话是"金"，Coach 的话是"银"）
- 磁盘是唯一 source of truth（OpenClaw 启发）
- L1/L2/L3 可从 Raw Layer 重建
- 总 token 消耗：~900 tokens，恒定，不随对话增长

#### Step 2: 与 AG2 ContextVariables 集成

L1/L2/L3 序列化后注入 `ContextVariables`，供所有 Agent 读取：

```python
context_variables = ContextVariables({
    "cognitive_state": cognitive_state.to_dict(),  # L1
    "summary_chain": summary_chain.to_dict(),      # L2
    "learner_profile": profile.to_dict(),           # L3
    "current_track": "business",
    "reflection_readiness": 0.0,
})
```

**Phase 2b 验证**：跑 3 轮对话，检查 `data/sessions/` 目录下文件正确生成，L1 被覆写而非累积，raw_dialogue.jsonl 逐行增长。

---

### Phase 2c: Observer Agent

**目标**：轻量 Observer 提取认知状态，驱动轨道切换决策

#### Step 1: 创建 Observer

**新建：**
- `agents/observer.py` — **不是 ConversableAgent，而是 FunctionTarget**
- `prompts/observer_prompt.py` — 结构化提取 prompt，输出 < 400 tokens

**Observer 实现为 AG2 `FunctionTarget`：**

```python
def observe_turn(
    output: str,                    # 上一条消息内容
    ctx: ContextVariables,          # 共享上下文
    observer_config=None,           # 轻量模型配置 (Haiku 级)
    coach_agent=None,               # Business Track 目标
    reflection_agent=None,          # Reflection Track 目标
) -> FunctionTargetResult:
    # 1. 调用轻量 LLM (Haiku 级) 提取认知状态
    # 2. 更新 L1 (覆写)、判断是否更新 L2/L3
    # 3. 持久化到磁盘
    # 4. 根据 reflection_readiness 返回下一个 Agent
```

AG2 的 `FunctionTarget.resolve()` 调用签名：`fn(last_message, current_agent.context_variables, **extra_args)`，与我们的设计完美匹配。

**为什么不是 ConversableAgent？**

Observer 不需要参与对话、不需要消息历史、不需要 system message。它是一个"传感器"——读取对话流，输出结构化状态。`FunctionTarget` 是 AG2 中最轻量的转移机制，零开销。

#### Step 2: 接入编排流程

**修改 `core/orchestrator.py`：**

```
User Input → UserProxy → Observer(FunctionTarget)
  ├─ readiness < 阈值 → Coach → NestedChat(Evaluator) → 输出
  └─ readiness ≥ 阈值 → Reflection Agent → 输出
```

UserProxy 的 `after_work` 设为 `FunctionTarget(observe_turn)`，Observer 根据 `reflection_readiness` 返回对应的 `AgentTarget`。

#### Step 3: 更新 config.py

新增 observer 模型配置（最便宜的模型）：

```python
"observer": os.getenv("OBSERVER_MODEL", "claude-haiku-4-5")
```

**Phase 2c 验证**：运行对话，确认 Observer 每轮调用轻量 LLM，`cognitive_state.json` 被正确写入，日志中可见认知状态变化。

---

### Phase 2d: 双轨 FSM + Reflection Agent

**目标**：实现 AI 驱动的 Business↔Reflection 轨道切换

#### Step 1: 创建 Reflection Agent

**新建：**
- `agents/reflection_agent.py` — 元认知引导 Agent
- `prompts/reflection_prompt.py` — 反思轨 system message

Reflection Agent 使用 AG2 的 `UpdateSystemMessage` 注入当前认知状态，让它基于 Observer 提取的盲点和假设来引导反思。

#### Step 2: 完善 FSM 转移

**完整 FSM 流转：**

```
Observer 判断 → Business Track:
  Coach 提问 → NestedChat(Evaluator 审查) → 用户回答 → Observer 再判断

Observer 判断 → Reflection Track:
  Reflection Agent 元认知提问 → 用户回答 → Observer 再判断
  (用户说"继续业务"或 Observer 判定反思完成 → 切回 Business Track)
```

**Handoffs 配置：**

- `user_proxy.after_work` → `FunctionTarget(observe_turn)`
- Observer 返回 `AgentTarget(coach)` 或 `AgentTarget(reflection_agent)`
- `coach.after_work` → `NestedChatTarget(evaluator 审查)`
- `reflection_agent.after_work` → `RevertToUserTarget()`

**Phase 2d 验证**：构造触发反思的对话（重复模式、情绪升级），确认系统自动切换到 Reflection Track，反思后切回 Business Track。

---

## 文件变更总表

### 删除 (1)

| 文件 | 原因 |
|------|------|
| `core/autogen_adapter.py` | 假的 AG2 适配器，用 httpx 绕过框架 |

### 新建 (11)

| 文件 | 职责 |
|------|------|
| `core/orchestrator.py` | 编排核心：Agent 创建、Handoffs 配置、group chat 生命周期 |
| `memory/__init__.py` | 记忆模块入口 |
| `memory/cognitive_state.py` | L1：认知状态 dataclass + 序列化 |
| `memory/summary_chain.py` | L2：会话摘要链 dataclass + 追加逻辑 |
| `memory/learner_profile.py` | L3：学习者画像 dataclass + 渐进更新 |
| `memory/raw_log.py` | Raw：JSONL 追加写入器 |
| `memory/session.py` | 文件 I/O 管理器：路径管理、读写、初始化 |
| `agents/observer.py` | FunctionTarget 观察者：轻量 LLM 提取 + 轨道决策 |
| `agents/reflection_agent.py` | 反思轨 Agent：元认知引导 |
| `prompts/observer_prompt.py` | Observer 结构化提取 prompt |
| `prompts/reflection_prompt.py` | 反思轨 system message |

### 修改 (8)

| 文件 | 变更内容 |
|------|----------|
| `agents/master_coach.py` | import 从 `core.autogen_adapter` 改为真 `autogen` |
| `agents/evaluator.py` | 同上 |
| `agents/user_proxy.py` | 对齐新编排，取消禁用 |
| `agents/__init__.py` | 导出所有 Agent（含新增的 Observer、Reflection） |
| `core/__init__.py` | 移除假适配器导出，加 orchestrator |
| `core/config.py` | 新增 observer/reflection 模型配置 |
| `core/nested_chat.py` | 重写为真实 AG2 `register_nested_chats` API |
| `main.py` | 用 orchestrator 替代手写 for 循环 |

### CLAUDE.md 更新

按 GEB 分形文档协议，架构变更必须同步更新：
- 根级 `CLAUDE.md` — 更新目录结构和模块清单
- `agents/CLAUDE.md` — ���增 observer、reflection_agent 成员
- `core/CLAUDE.md` — 新增 orchestrator，移除 autogen_adapter
- `memory/CLAUDE.md` — 新建，记录三层记忆架构
- `prompts/CLAUDE.md` — 新增 observer_prompt、reflection_prompt

---

## 依赖链与并行化

```
2a.1 删除假适配器 + 修复 import ──→ 2a.2 重写 nested_chat ──→ 2a.3 创建 orchestrator ──→ 2a.4 更新 main.py
                                                                      ↑
2b.1 创建 memory 模块 ──→ 2b.2 ContextVariables 集成 ─────────────────┘
                                    ↑
2c.1 创建 Observer ──→ 2c.2 接入编排 ┘
                            ↑
2d.1 创建 Reflection Agent ──┘──→ 2d.2 完善 FSM 转移
```

**可并行的工作：**
- 2a.1 和 2b.1 无依赖，可并行启动
- 2d.1 和 2c.1 在 2a.1 完成后可并行

---

## 风险与缓解

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| AG2 Anthropic API 兼容性 | **已验证无风险** — `oai/anthropic.py` 原生支持 | 需确认 `pip install anthropic` |
| NestedChatTarget 包装机制 | 自动创建 wrapper agent，可能与 DefaultPattern agent 列表冲突 | 端到端测试验证，阅读源码确认包装逻辑 |
| FunctionTarget 闭包引用 | Agent 引用需在 session 生命周期内稳定 | 通过 `extra_args` 传递，session 级创建一次 |
| Observer 延迟 | Haiku 级 LLM 仍有 ~200ms 延迟 | 可异步执行，只在 reflection_readiness 判断上阻塞 |
| requirements.txt 依赖 | `pyautogen>=0.2.3` 可能与新 Pattern API 不兼容 | 确认 ag2 子模块版本，必要时锁定版本 |
| 上下文变量膨胀 | ContextVariables 可能随对话增长 | 三层记忆设计保证 ~900 tokens 恒定，Raw 日志不进 ContextVariables |

---

## 验证方案

每个阶段完成后的端到端验证：

1. **Phase 2a 验证**：`python main.py` 真实模式，Coach 提问 → Evaluator 通过 AG2 Nested Chat 审查 → 输出。日志中可见 nested chat 交互，手写 for 循环不再存在。
2. **Phase 2b 验证**：跑 3 轮对话后检查 `data/sessions/` 目录，确认文件正确生成，L1 大小恒定不膨胀。
3. **Phase 2c 验证**：日志中可见 Observer 每轮调用轻量 LLM，`cognitive_state.json` 反映对话语义进展（不只是轮次计数）。
4. **Phase 2d 验证**：构造"反复抱怨 + 情绪升级"的对话，确认系统自动切换到反思轨，反思完成后自动切回业务轨。

---

## 角色分工与任务分配（基于 AGENTS.md）

### Team Lead 职责
- 总体协调各阶段进度
- 审查 Architect 的设计方案
- 分配任务给各角色
- 最终验收每个 Phase

### Architect 职责
- 已完成：Phase 2 整体架构设计（本文档）
- 待办：审查各角色实现方案，确保架构一致性

---

### Phase 2a: AG2 迁移 — 角色分工

#### Backend 负责

**Task 2a-B1: 删除假适配器 + 修复 import**
- 删除 `core/autogen_adapter.py`
- 修改 `agents/master_coach.py` — import 改为 `from autogen import ConversableAgent`
- 修改 `agents/evaluator.py` — 同上
- 修改 `agents/user_proxy.py` — 取消禁用，对齐新 API
- 修改 `agents/__init__.py` — 恢复 UserProxy 导出
- 修改 `core/__init__.py` — 移除假适配器导出
- **验收标准**：`from agents import WIALMasterCoach, StrictEvaluator, UserProxy` 不报错，agents 使用真 AG2 ConversableAgent

**Task 2a-B2: 创建 Orchestrator 骨架**
- 新建 `core/orchestrator.py`
- 实现 `create_session()` — 创建 Coach、Evaluator、UserProxy 三个 Agent
- 实现 `run_turn(user_input)` — 调用 `initiate_group_chat` 的最小可运行版本（先不加 Handoffs）
- **验收标准**：能跑通一轮 User → Coach → 输出（不含 Evaluator 审查）

#### Logic Engineer 负责

**Task 2a-L1: 重写 nested_chat.py**
- 重写 `core/nested_chat.py`，对齐真实 AG2 `register_nested_chats` API
- 实现 `setup_nested_chat(coach, evaluator, max_rounds)` 返回正确的 `chat_queue` 配置
- 实现消息提取函数 `_extract_question(sender_msg)` — 从 Coach 输出中提取问题
- **验收标准**：配置格式符合 AG2 API，可被 `register_nested_chats` 接受

**Task 2a-L2: 集成 NestedChat 到 Orchestrator**
- 修改 `core/orchestrator.py`，在 `create_session()` 中配置 Coach 的 `NestedChatTarget`
- 配置 Handoffs：`coach.after_work` → `NestedChatTarget(evaluator 审查)`
- **验收标准**：Coach 生成问题后自动触发 Evaluator 审查，审查通过后输出

**Task 2a-L3: 更新 main.py**
- 修改 `main.py`，替换 `real_review_loop()` 为 `orchestrator.run_turn()`
- 保留 mock 模式不变
- **验收标准**：真实模式走 AG2 编排，mock 模式仍可用

#### Tester 负责

**Task 2a-T1: Phase 2a 端到端测试**
- 编写测试用例 `tests/test_phase2a_integration.py`
- 测试场景：
  1. Coach 生成低质量问题（< 95 分）→ Evaluator 打回 → Coach 重写 → 通过
  2. Coach 生成高质量问题（≥ 95 分）→ Evaluator 一次通过
  3. 达到最大轮次仍未通过 → 返回最佳问题
- **验收标准**：所有测试通过，日志中可见 nested chat 交互

---

### Phase 2b: 三层记忆系统 — 角色分工

#### Logic Engineer 负责

**Task 2b-L1: 创建 memory 数据结构**
- 新建 `memory/cognitive_state.py` — L1 dataclass + `to_dict()` / `from_dict()`
- 新建 `memory/summary_chain.py` — L2 dataclass + 追加逻辑
- 新建 `memory/learner_profile.py` — L3 dataclass + 渐进更新逻辑
- 新建 `memory/__init__.py` — 导出所有 dataclass
- **验收标准**：dataclass 可序列化为 JSON，token 估算在目标范围内

**Task 2b-L2: 实现文件 I/O**
- 新建 `memory/raw_log.py` — JSONL 追加写入器
- 新建 `memory/session.py` — 文件 I/O 管理器
  - `SessionManager.init_session(session_id, learner_id)` — 创建目录结构
  - `SessionManager.save_cognitive_state(state)` — 覆写 L1
  - `SessionManager.append_summary_chain(summary)` — 追加 L2
  - `SessionManager.update_learner_profile(profile)` — 渐进更新 L3
  - `SessionManager.append_raw_log(turn_data)` — 追加 Raw
- **验收标准**：调用方法后文件正确写入 `data/` 目录

**Task 2b-L3: 集成 ContextVariables**
- 修改 `core/orchestrator.py`，在 `create_session()` 中初始化 `ContextVariables`
- 将 L1/L2/L3 序列化后注入 `ContextVariables`
- 每轮对话后更新 `ContextVariables`（暂时手动更新，Phase 2c 后由 Observer 自动更新）
- **验收标准**：所有 Agent 可通过 `context_variables` 访问记忆

#### Tester 负责

**Task 2b-T1: 记忆系统单元测试**
- 编写 `tests/test_memory.py`
- 测试场景：
  1. L1 覆写不累积
  2. L2 追加正确
  3. L3 渐进更新（合并而非覆盖）
  4. Raw JSONL 逐行增长
  5. 从空目录初始化
- **验收标准**：所有测试通过

**Task 2b-T2: Phase 2b 端到端测试**
- 跑 3 轮对话，检查 `data/sessions/{session_id}/` 目录
- 验证文件结构、内容正确性、token 大小
- **验收标准**：L1 ~400 tokens，L2 ~200 tokens，L3 ~300 tokens

---

### Phase 2c: Observer Agent — 角色分工

#### Logic Engineer 负责

**Task 2c-L1: 编写 Observer prompt**
- 新建 `prompts/observer_prompt.py` — `OBSERVER_SYSTEM_MESSAGE`
- Prompt 要求：
  - 输入：最新对话轮次 + L2 摘要链
  - 输出：JSON 格式的 L1 认知状态（< 400 tokens）
  - 包含 `reflection_readiness` 评分逻辑
- **验收标准**：Prompt 清晰，输出格式可解析

**Task 2c-L2: 实现 Observer 函数**
- 新建 `agents/observer.py`
- 实现 `observe_turn(output, ctx, observer_config, coach_agent, reflection_agent)` → `FunctionTargetResult`
- 核心逻辑：
  1. 调用轻量 LLM（Haiku）提取认知状态
  2. 更新 L1（覆写）
  3. 判断是否更新 L2/L3
  4. 持久化到磁盘
  5. 根据 `reflection_readiness` 返回 `AgentTarget(coach)` 或 `AgentTarget(reflection_agent)`
- **验收标准**：函数签名符合 `FunctionTarget` 要求，返回正确的 `FunctionTargetResult`

**Task 2c-L3: 集成 Observer 到 Orchestrator**
- 修改 `core/orchestrator.py`
- 在 `create_session()` 中创建 `FunctionTarget(observe_turn, extra_args={...})`
- 配置 `user_proxy.after_work` → `FunctionTarget(observe_turn)`
- **验收标准**：每轮对话后 Observer 自动执行

#### Backend 负责

**Task 2c-B1: 更新 config.py**
- 修改 `core/config.py`，新增 `"observer"` 模型配置
- 默认值：`claude-haiku-4-5`
- **验收标准**：`get_llm_config("observer")` 返回正确配置

#### Tester 负责

**Task 2c-T1: Observer 单元测试**
- 编写 `tests/test_observer.py`
- 测试场景：
  1. 提取认知状态格式正确
  2. `reflection_readiness` 计算逻辑
  3. 低 readiness → 返回 Coach
  4. 高 readiness → 返回 Reflection Agent
- **验收标准**：所有测试通过

**Task 2c-T2: Phase 2c 端到端测试**
- 运行对话，检查日志中 Observer 调用记录
- 检查 `cognitive_state.json` 每轮更新
- **验收标准**：认知状态反映对话语义进展

---

### Phase 2d: 双轨 FSM + Reflection Agent — 角色分工

#### Logic Engineer 负责

**Task 2d-L1: 编写 Reflection prompt**
- 新建 `prompts/reflection_prompt.py` — `REFLECTION_SYSTEM_MESSAGE`
- Prompt 要求：
  - 基于 L1 认知状态（盲点、假设）引导元认知反思
  - 不直接给建议，只提问
  - 使用 `UpdateSystemMessage` 模板注入认知状态
- **验收标准**：Prompt 符合 WIAL 反思轨要求

**Task 2d-L2: 实现 Reflection Agent**
- 新建 `agents/reflection_agent.py`
- 创建 `ConversableAgent` with `UpdateSystemMessage`
- 配置 `after_work` → `RevertToUserTarget()`
- **验收标准**：Agent 可基于认知状态生成反思问题

**Task 2d-L3: 完善 FSM 转移**
- 修改 `core/orchestrator.py`
- 在 `create_session()` 中添加 Reflection Agent
- 修改 Observer 逻辑，根据 `reflection_readiness` 返回正确的 Agent
- 配置完整 Handoffs：
  - `user_proxy.after_work` → `FunctionTarget(observe_turn)`
  - `coach.after_work` → `NestedChatTarget(evaluator)`
  - `reflection_agent.after_work` → `RevertToUserTarget()`
- **验收标准**：FSM 流转正确，可在两轨间切换

#### Tester 负责

**Task 2d-T1: FSM 单元测试**
- 编写 `tests/test_fsm.py`
- 测试场景：
  1. 低 readiness → 保持 Business Track
  2. 高 readiness → 切换到 Reflection Track
  3. 反思完成 → 切回 Business Track
- **验收标准**：所有测试通过

**Task 2d-T2: Phase 2d 端到端测试**
- 构造触发反思的对话（重复模式、情绪升级）
- 验证系统自动切换到 Reflection Track
- 验证反思后切回 Business Track
- **验收标准**：轨道切换符合预期

---

### 文档更新 — 角色分工

#### Architect 负责

**Task DOC-1: 更新 CLAUDE.md**
- 根级 `CLAUDE.md` — 更新目录结构，新增 memory 模块
- `agents/CLAUDE.md` — 新增 observer、reflection_agent 成员清单
- `core/CLAUDE.md` — 新增 orchestrator，移除 autogen_adapter
- 新建 `memory/CLAUDE.md` — 记录三层记忆架构
- `prompts/CLAUDE.md` — 新增 observer_prompt、reflection_prompt
- **验收标准**：所有 CLAUDE.md 符合 GEB 分形文档协议

---

## 任务执行顺序（按角色）

### Sprint 1: Phase 2a（预计 2-3 天）

**Day 1:**
- Backend: Task 2a-B1（删除假适配器）
- Logic Engineer: Task 2a-L1（重写 nested_chat）

**Day 2:**
- Backend: Task 2a-B2（创建 Orchestrator 骨架）
- Logic Engineer: Task 2a-L2（集成 NestedChat）

**Day 3:**
- Logic Engineer: Task 2a-L3（更新 main.py）
- Tester: Task 2a-T1（端到端测试）
- Team Lead: 验收 Phase 2a

### Sprint 2: Phase 2b（预计 2 天）

**Day 1:**
- Logic Engineer: Task 2b-L1（创建 memory 数据结构）+ Task 2b-L2（实现文件 I/O）

**Day 2:**
- Logic Engineer: Task 2b-L3（集成 ContextVariables）
- Tester: Task 2b-T1（单元测试）+ Task 2b-T2（端到端测试）
- Team Lead: 验收 Phase 2b

### Sprint 3: Phase 2c（预计 2 天）

**Day 1:**
- Logic Engineer: Task 2c-L1（编写 Observer prompt）+ Task 2c-L2（实现 Observer 函数）
- Backend: Task 2c-B1（更新 config.py）

**Day 2:**
- Logic Engineer: Task 2c-L3（集成 Observer 到 Orchestrator）
- Tester: Task 2c-T1（单元测试）+ Task 2c-T2（端到端测试）
- Team Lead: 验收 Phase 2c

### Sprint 4: Phase 2d（预计 2 天）

**Day 1:**
- Logic Engineer: Task 2d-L1（编写 Reflection prompt）+ Task 2d-L2（实现 Reflection Agent）

**Day 2:**
- Logic Engineer: Task 2d-L3（完善 FSM 转移）
- Tester: Task 2d-T1（FSM 单元测试）+ Task 2d-T2（端到端测试）
- Team Lead: 验收 Phase 2d

### Sprint 5: 文档更新（预计 0.5 天）

- Architect: Task DOC-1（更新所有 CLAUDE.md）
- Team Lead: 最终验收整个 Phase 2

---

## 总工期估算

- **Phase 2a**: 2-3 天
- **Phase 2b**: 2 天
- **Phase 2c**: 2 天
- **Phase 2d**: 2 天
- **文档更新**: 0.5 天
- **总计**: 8.5-9.5 天（约 2 周）

---

## 关键里程碑

1. **Milestone 1 (Day 3)**: Phase 2a 完成，AG2 真实编排跑通
2. **Milestone 2 (Day 5)**: Phase 2b 完成，三层记忆系统可用
3. **Milestone 3 (Day 7)**: Phase 2c 完成，Observer 驱动轨道决策
4. **Milestone 4 (Day 9)**: Phase 2d 完成，双轨 FSM 全功能
5. **Milestone 5 (Day 9.5)**: 文档更新完成，Phase 2 交付
