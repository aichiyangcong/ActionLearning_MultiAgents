# action_learning_coach/core/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 LLMConfig, get_llm_config, setup_nested_chat
- config.py: LLM 配置管理，封装 OpenAI API 配置和审查参数，提供 to_autogen_config() 转换
- nested_chat.py: Nested Chat 审查循环逻辑，实现 Actor-Critic 模式编排，最多 5 轮审查

## 设计哲学
- 配置集中化: 所有 LLM 参数从环境变量统一加载
- 接口标准化: 提供 AutoGen 兼容的配置格式
- 审查参数化: MAX_REVIEW_ROUNDS=5, PASS_SCORE_THRESHOLD=95

## 实现状态
✅ 已完成: 配置管理和 Nested Chat 编排逻辑

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
