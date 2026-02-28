# 项目进度状态

> **最后更新**: 2026-02-28
> **当前阶段**: Phase 2 准备启动

---

## Phase 1: MVP 核心骨架 ✅ 已完成

**完成时间**: 2026-02-28
**Git Commit**: `c7cee5a` - "Phase 1 MVP: Action Learning AI Coach System"

### 交付物

1. ✅ Actor-Critic 模式：`WIAL_Master_Coach` + `Strict_Evaluator` 的审查循环
2. ✅ 证明系统能"打回自己写得不好的建议"
3. ✅ 基础的 ReAct 模式推理（隐式）
4. ✅ Terminal 中可运行的完整对话流程
5. ✅ Mock 模式和真实模式双模式支持

### 技术栈

- Python 3.10+
- AG2 (AutoGen) 0.2.3+ (但实际使用了假适配器)
- Anthropic Claude API (claude-sonnet-4-6 / claude-opus-4-6)

### 已知技术债（Phase 2 需解决）

详见 `doc/phase1_technical_debt.md`

1. **AutoGen 是假的** — `core/autogen_adapter.py` 用 httpx 绕过 AG2 框架
2. **Nested Chat 是空架子** — `core/nested_chat.py` 从未被调用
3. **无状态** — 跨轮记忆靠字符串拼接，��持久化

---

## Phase 2: 真实 AG2 编排 + Observer 记忆系统 + 双轨 FSM 🚧 准备启动

**计划开始**: 2026-02-28
**预计工期**: 8.5-9.5 天（约 2 周）
**详细计划**: `doc/phase2_implementation_plan.md`

### 目标

1. 还清 Phase 1 技术债，迁移到真实 AG2 框架
2. 实现三层记忆系统（L1 认知状态、L2 会话摘要、L3 学习者画像）
3. 实现 Observer Agent（轻量 LLM 提取认知状态）
4. 实现 AI 驱动的双轨 FSM（Business Track ↔ Reflection Track）

### 关键架构决策

- **AG2 编排模式**: `DefaultPattern` + Handoffs
- **Observer 实现**: `FunctionTarget`（不是 ConversableAgent）
- **记忆系统**: 恒定 ~900 tokens，文件持久化
- **轨道切换**: AI 判断（reflection_readiness），非固定轮次

### 4 个阶段

| 阶段 | 目标 | 预计工期 | 状态 |
|------|------|----------|------|
| Phase 2a | AG2 迁移（地基） | 2-3 天 | ⏳ 待启动 |
| Phase 2b | 三层记忆系统 | 2 天 | ⏳ 待启动 |
| Phase 2c | Observer Agent | 2 天 | ⏳ 待启动 |
| Phase 2d | 双轨 FSM + Reflection Agent | 2 天 | ⏳ 待启动 |

### 关键里程碑

- [ ] **Milestone 1 (Day 3)**: Phase 2a 完成，AG2 真实编排跑通
- [ ] **Milestone 2 (Day 5)**: Phase 2b 完成，三层记忆系统可用
- [ ] **Milestone 3 (Day 7)**: Phase 2c 完成，Observer 驱动轨道决策
- [ ] **Milestone 4 (Day 9)**: Phase 2d 完成，双轨 FSM 全功能
- [ ] **Milestone 5 (Day 9.5)**: 文档更新完成，Phase 2 交付

---

## Phase 3: Web 界面 + 多视角智能体 📅 计划中

**预计开始**: Phase 2 完成后
**目标**: 封装 API，提供 Web 聊天界面

---

## Phase 4: 企业级功能 📅 计划中

**预计开始**: Phase 3 完成后
**目标**: 集成企业系统，提供数据看板

---

## 当前任务

**下一步**: 启动 Phase 2a - AG2 迁移

**角色分工**（基于 AGENTS.md）:
- **Backend**: 删除假适配器，创建 Orchestrator 骨架
- **Logic Engineer**: 重写 nested_chat，集成 NestedChat，更新 main.py
- **Tester**: Phase 2a 端到端测试

---

## 参考文档

- `doc/architecture_design.md` — 核心架构与工程说明书
- `doc/technical_architecture_cto_perspective.md` — CTO 技术架构方案
- `doc/phase1_mvp_plan.md` — Phase 1 MVP 计划
- `doc/phase2_implementation_plan.md` — Phase 2 实施计划（含角色分工）
- `doc/phase1_technical_debt.md` — Phase 1 技术债详细分析
- `doc/记忆机制的参考.md` — ChatGPT + OpenClaw 记忆系统参考
- `AGENTS.md` — 团队角色定义
