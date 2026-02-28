# action_learning_coach/agents/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 WIALMasterCoach, StrictEvaluator, UserProxy, observe_turn
- master_coach.py: WIAL Master Coach Agent，依赖真实 AG2 ConversableAgent，生成开放式提问，输出 JSON {question, reasoning}
- evaluator.py: Strict Evaluator Agent，依赖真实 AG2 ConversableAgent，三维评分体系 (开放性40 + 无诱导性40 + 反思深度20)，评分 >= 95 通过
- user_proxy.py: UserProxy Agent，依赖 autogen.UserProxyAgent，代理用户交互，管理对话历史
- observer.py: Observer 认知状态提取函数 (FunctionTarget 回调)，调用 Haiku 级 LLM 提取 L1 CognitiveState，路由到 Coach

## 变更记录
- Phase 2a: 所有 Agent 从假 core/autogen_adapter 迁移到真实 AG2 ConversableAgent
- Phase 2c: 新增 observer.py，observe_turn 作为 FunctionTarget 回调，传感器定位

## 设计哲学
- Actor-Critic 模式: Coach 生成，Evaluator 审查
- Observer 传感器: 只读不写，零对话开销，通过 FunctionTarget 内联执行
- 高质量阈值: 评分 >= 95 通过，< 95 打回重写
- 审查循环: 最多 5 轮，超出则输出最佳版本 + 警告

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
