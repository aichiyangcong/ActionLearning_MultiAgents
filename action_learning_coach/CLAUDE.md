# Action Learning Coach - WIAL 行动学习教练系统
Python 3.10+ + AG2 (AutoGen) 0.2.3+ + OpenAI API

## 架构概览
基于 Actor-Critic 模式的 AI 教练系统，使用 Nested Chat 实现质量审查循环。

<directory>
agents/ - Agent 实现模块 (3 文件: master_coach, evaluator, user_proxy)
core/ - 核心逻辑模块 (2 文件: config, nested_chat)
prompts/ - Prompt 定义模块 (2 文件: coach_prompt, evaluator_prompt)
utils/ - 工具函数模块 (1 文件: logger)
tests/ - 测试用例模块 (3 文件: test_coach, test_evaluator, test_nested_chat)
</directory>

<config>
main.py - Terminal 交互入口，支持 Mock 和真实 LLM 双模式，自动检测 API Key
requirements.txt - 项目依赖清单
.env.example - 环境变量模板
README.md - 项目说明文档，快速开始指南
</config>

## 核心流程
用户输入 → WIAL_Master_Coach 生成问题 → Nested Chat 触发审查 → Strict_Evaluator 评分 → 评分 ≥95 通过 / <95 打回重写 (最多 5 轮)

## 技术栈版本
- Python: 3.10+
- AG2 (AutoGen): 0.2.3+
- LLM: OpenAI gpt-4o-mini
- Testing: pytest 7.4.0+
- Code Quality: black 23.0.0+, flake8 6.0.0+

## 开发状态
Phase 1 MVP - ✅ 完整集成完成
- ✅ 基础设施 (Config, Logger)
- ✅ Prompt 设计 (Coach + Evaluator)
- ✅ Agent 逻辑 (WIALMasterCoach + StrictEvaluator)
- ✅ Terminal UI (流式输出 + 对话历史)
- ✅ Backend 与 Frontend 集成 (双模式支持)
- ⏳ 测试用例编写中

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
