# AI Onboarding Guide - Action Learning Coach

> 本文档为新接手的 AI 提供系统的项目理解路径

---

## 📖 阅读顺序（必读）

### Level 1: 项目背景（5 分钟）

**目标**: 理解"这是什么项目"、"要解决什么问题"

1. **`doc/project_description.md`** - 项目愿景、WIAL 方法论、核心价值
   - 关键点：这是一个 AI 行动学习教练，基于 WIAL 方法论
   - 核心能力：通过开放式提问引导反思，而非给建议

2. **`doc/project_status.md`** - 当前进度和状态
   - 关键点：Phase 2 完成 97%，被 NestedChat Bug 阻塞
   - 了解已完成什么、还缺什么

### Level 2: 技术架构（10 分钟）

**目标**: 理解技术栈、架构设计、关键决策

3. **`doc/architecture_design.md`** - 核心架构设计
   - 关键点：Actor-Critic 模式、三层记忆系统、双轨 FSM
   - 理解为什么这样设计

4. **`CLAUDE.md`** - 项目规范 + 集成经验
   - 关键点：目录结构、开发环境、集成经验（API 代理、NestedChat 配置等）
   - **必读**："集成经验与最佳实践"章节

5. **`doc/phase2_implementation_plan.md`** - Phase 2 实施计划
   - 关键点：4 个子阶段（2a/2b/2c/2d）的目标和实现
   - 理解当前在哪个阶段

### Level 3: 当前问题（15 分钟）

**目标**: 深入理解当前阻塞的 Bug

6. **`doc/nested_chat_bug_report.md`** ⭐ **最重要**
   - 问题现象：Evaluator 收到空问题
   - 已尝试的解决方案（5 个已修复的问题）
   - 当前阻塞：carryover 消息提取失败
   - 下一步调试方向

7. **`ACCEPTANCE_TEST.md`** - 验收测试用例
   - 关键点：Test 12 端到端测试（当前失败的测试）
   - 理解预期行为 vs 实际行为

### Level 4: 代码结构（10 分钟）

**目标**: 理解关键文件位置和职责

8. **`action_learning_coach/CLAUDE.md`** - 模块结构
   - 目录树：agents/, core/, prompts/, memory/, tests/
   - 每个模块的职责

9. **关键文件**（按重要性排序）:
   - `core/nested_chat.py` - ⭐ Bug 所在文件
   - `core/orchestrator.py` - 编排器，创建 wrapper agent
   - `core/config.py` - httpx 代理封装
   - `agents/observer.py` - Observer 实现
   - `prompts/observer_prompt.py` - Observer system message

### Level 5: 环境和调试（5 分钟）

**目标**: 能够运行代码、查看日志

10. **环境信息**（见 `CLAUDE.md`）:
    - Python 3.13，虚拟环境：`/Users/zhaoziwei/Desktop/关系行动/.venv`
    - 代理 API：`https://aicode.life`（Cloudflare 保护）
    - 关键环境变量：`.env` 文件

11. **调试命令**（见 `nested_chat_bug_report.md`）:
    ```bash
    cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
    ../.venv/bin/python -c "..." 2>&1 | grep -A 10 "Carryover messages"
    ```

---

## 🎯 核心知识点（必须掌握）

### 1. AG2 (AutoGen) 0.11.2 Handoffs API

**关键概念**:
- `DefaultPattern` - 编排模式
- `Handoffs` - Agent 间转移
- `NestedChatTarget` - 嵌套对话目标
- `FunctionTarget` - 函数回调目标

**关键约束**:
- `NestedChatTarget` 不能直接用于 `set_after_work`
- 必须手动创建 wrapper agent + `AgentTarget`
- wrapper agent 必须加入 `pattern.agents` 列表

**参考**: `CLAUDE.md` - "AG2 NestedChat 配置"章节

### 2. NestedChat 消息流

**正常流程**:
```
User → Coach (生成问题)
         ↓ (after_work handoff)
      Wrapper Agent (nested chat)
         ↓ (carryover_config)
      Evaluator (评估问题)
         ↓ (返回评分)
      Coach (根据评分决定是否重写)
```

**当前问题**:
- Wrapper Agent 成功触发 ✅
- carryover_config 的 `summary_method` 被调用 ✅
- 但 `_extract_question_from_carryover` 收到的 `messages` 列表中找不到 Coach 的消息 ❌

**参考**: `doc/nested_chat_bug_report.md` - "技术背景"章节

### 3. carryover_config 机制

**AG2 源码位置**:
- `conversable_agent.py:755-798` - `_process_chat_queue_carryover`
- `conversable_agent.py:622-655` - `_get_chats_to_run`

**关键参数**:
- `trim_n_messages=2` - 默认裁剪最后 2 条消息（transition messages）
- `summary_method` - Callable 签名：`(recipient, messages, summary_args) -> str`

**当前实现**:
```python
# core/nested_chat.py:24-61
def _extract_question_from_carryover(recipient, messages, summary_args):
    # 从后往前找 Coach 的消息
    for msg in reversed(messages):
        if msg.get("name") == "WIAL_Master_Coach" and msg.get("role") == "assistant":
            content = msg.get("content", "")
            # 解析 JSON 提取 question 字段
            ...
```

**参考**: `doc/nested_chat_bug_report.md` - "下一步调试方向"

### 4. 已修复的问题（避免重复踩坑）

1. ✅ **API 代理兼容性** - 用 httpx 替换 SDK
2. ✅ **Observer/Reflection 配置回退** - 3 级回退链
3. ✅ **Observer 身份冲突** - 强制覆盖 Kiro 身份
4. ✅ **NestedChat 触发** - 手动创建 wrapper agent
5. ✅ **空 stop_reason** - 代理 API 返回空值

**参考**: `CLAUDE.md` - "集成经验与最佳实践"章节

---

## 🔍 调试起点

### 第一步：验证 carryover messages 内容

**目标**: 确认 `_extract_question_from_carryover` 收到的 `messages` 列表内容

**方法**: 运行测试，查看日志输出（已在 `nested_chat.py:39-41` 添加日志）

**命令**:
```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from core.orchestrator import Orchestrator
orch = Orchestrator()
orch.create_session()
result = orch.run_turn('销售团队因为销量下滑士气大降，团队成员互相指责，你作为管理者该怎么办？')
" 2>&1 | grep -A 10 "Carryover messages"
```

**预期输出**:
```
[INFO] Carryover messages count: X
[INFO] Message 0: role=..., name=..., content=...
[INFO] Message 1: role=..., name=..., content=...
...
```

**关键问题**:
1. `messages` 列表是否为空？
2. 是否包含 `name="WIAL_Master_Coach"` 的消息？
3. Coach 消息的 `content` 是否包含 JSON 格式的问题？

### 第二步：根据日志结果选择方案

**场景 A**: messages 列表为空或不包含 Coach 消息
- 原因：AG2 的 `trim_n_messages=2` 可能删除了 Coach 的消息
- 方案：调整 `carryover_config` 的 `trim_n_messages` 参数

**场景 B**: messages 包含 Coach 消息但 content 为空
- 原因：GroupChat 的消息格式与预期不符
- 方案：检查 GroupChat 的消息结构，调整提取逻辑

**场景 C**: carryover 机制本身有问题
- 原因：AG2 0.11.2 的 carryover 实现可能有 bug
- 方案：考虑备选方案（见 `nested_chat_bug_report.md` - "备选方案"）

---

## 📚 可选阅读（深入理解）

- `doc/technical_architecture_cto_perspective.md` - CTO 视角的技术架构
- `doc/phase1_technical_debt.md` - Phase 1 技术债分析
- `doc/记忆机制的参考.md` - ChatGPT + OpenClaw 记忆系统参考
- `AGENTS.md` - 团队角色定义

---

## ⚡ 快速上手清单

- [ ] 读完 Level 1-3（必读，30 分钟）
- [ ] 理解 AG2 NestedChat 配置（核心知识点 1-3）
- [ ] 查看已修复的 5 个问题（避免重复）
- [ ] 运行调试命令，查看 carryover messages 日志
- [ ] 根据日志结果选择调试方案
- [ ] 开始修复 Bug

---

## 💡 关键提示

1. **不要重复已修复的问题** - 查看 `CLAUDE.md` 的集成经验章节
2. **理解 AG2 的约束** - NestedChatTarget 的使用方式是固定的
3. **先看日志再行动** - carryover messages 的实际内容是关键
4. **参考 Bug 报告** - `nested_chat_bug_report.md` 包含完整的上下文

---

**祝调试顺利！如有疑问，优先查看 `doc/nested_chat_bug_report.md`**
