# Action Learning Coach - WIAL 行动学习教练系统
Python 3.10+ + AG2 (AutoGen) 0.11.2 + Anthropic Claude API

## 架构概览
基于 Actor-Critic 模式的 AI 教练系统，使用 AG2 DefaultPattern + NestedChatTarget + FunctionTarget 实现质量审查循环与认知状态追踪。

<directory>
agents/ - Agent 实现模块 (4 文件: master_coach, evaluator, user_proxy, observer)
core/ - 核心逻辑模块 (3 文件: config, nested_chat, orchestrator)
prompts/ - Prompt 定义模块 (3 文件: coach_prompt, evaluator_prompt, observer_prompt)
memory/ - 三层记忆模块 (5 文件: cognitive_state, summary_chain, learner_profile, raw_log, session)
utils/ - 工具函数模块 (1 文件: logger)
tests/ - 测试用例模块 (6 文件: test_coach, test_evaluator, test_review_loop, test_e2e, test_phase2a, test_phase2c)
</directory>

<config>
main.py - Terminal 交互入口，真实模式走 AG2 Orchestrator，mock 模式使用模拟数据
requirements.txt - 项目依赖清单
.env.example - 环境变量模板
README.md - 项目说明文档，快速开始指南
</config>

## 核心流程
用户输入 → UserProxy → Observer(FunctionTarget, 提取L1认知状态) → Coach → NestedChatTarget(Evaluator 审查) → 评分 >= 95 通过 / < 95 打回重写

## 技术栈版本
- Python: 3.10+
- AG2 (AutoGen): 0.11.2
- LLM: Anthropic Claude (Sonnet 教练 / Opus 审查 / Haiku 观察)
- Testing: pytest 7.4.0+

## 开发状态
Phase 2a - AG2 编排集成 ✅
- ✅ Agent 迁移到真实 AG2 ConversableAgent
- ✅ Orchestrator 骨架 (DefaultPattern + initiate_group_chat)
- ✅ NestedChat 集成 (Coach → Evaluator 审查循环)
- ✅ main.py 使用 Orchestrator 替代手写 for 循环
- ✅ 42 个集成测试全部通过

Phase 2b - 三层记忆系统 ✅
- ✅ L1 CognitiveState / L2 SummaryChain / L3 LearnerProfile 数据结构
- ✅ SessionManager 文件 I/O (JSON + JSONL)
- ✅ ContextVariables 集成 + 每轮持久化

Phase 2c - Observer Agent ✅
- ✅ Observer prompt (传感器定位, < 400 tokens JSON 输出)
- ✅ observe_turn 函数 (FunctionTarget 回调, Haiku 级 LLM)
- ✅ Orchestrator 集成 (UserProxy.after_work → Observer → Coach)
- ✅ 28 个 Observer 测试全部通过

Phase 2d - 双轨 FSM + Reflection Agent ⏳
- ⏳ Reflection Agent prompt 和实现
- ⏳ Observer 双轨路由 (readiness >= 0.7 → Reflection)
- ⏳ FSM 状态转换

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
