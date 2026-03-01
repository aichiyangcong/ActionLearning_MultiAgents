# action_learning_coach/core/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 LLMConfig, get_llm_config, create_nested_chat_config, Orchestrator, TurnResult
- config.py: LLM 配置管理，封装 Anthropic API 配置和审查参数，支持 coach/evaluator/observer/reflection 四种 agent_type
- nested_chat.py: 返回 AG2 NestedChatTarget 实例，配置 Coach-Evaluator 审查循环（chat_queue 格式），可直接用于 OnCondition
- orchestrator.py: Phase 2 中枢编排器，双轨 FSM (Business ↔ Reflection)，数据流 User → Observer → Coach/Reflection → [NestedChat(Evaluator)] → 输出

## 设计哲学
- 配置集中化: 所有 LLM 参数从环境变量统一加载
- 接口标准化: 提供 AutoGen 兼容的配置格式 (api_type: "anthropic")
- 审查参数化: MAX_REVIEW_ROUNDS=5, PASS_SCORE_THRESHOLD=95
- Observer 内联: FunctionTarget 不创建 wrapper agent，零对话开销
- Nested Chat 用 NestedChatTarget 包装，AG2 自动创建 wrapper agent 并管理生命周期
- Orchestrator 通过 DefaultPattern + initiate_group_chat 驱动，返回 (ChatResult, ContextVariables, LastSpeaker)
- 双轨 FSM: Observer 按 readiness 路由，Coach 经审查，Reflection 无审查直接回到用户

## 数据流
```
User Input → UserProxy → Observer(FunctionTarget, 提取L1 + 双轨路由)
                                    ↓
                         readiness < 0.7 → Coach → NestedChat(Evaluator) → 输出
                         readiness >= 0.7 → Reflection → 输出 (无审查)
```

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
