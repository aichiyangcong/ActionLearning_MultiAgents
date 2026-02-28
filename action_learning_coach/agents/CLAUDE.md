# action_learning_coach/agents/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 WIALMasterCoach, StrictEvaluator, UserProxy
- master_coach.py: WIAL Master Coach Agent，生成开放式提问，使用隐式 ReAct 模式，输出 JSON {question, reasoning}
- evaluator.py: Strict Evaluator Agent，评估问题质量，三维评分体系 (开放性40 + 无诱导性40 + 反思深度20)，评分 ≥95 通过
- user_proxy.py: UserProxy Agent，代理用户交互，注册 Nested Chat 审查流程，管理对话历史

## 设计哲学
- Actor-Critic 模式: Coach 生成，Evaluator 审查
- 高质量阈值: 评分 ≥95 通过，<95 打回重写
- 审查循环: 最多 5 轮，超出则输出最佳版本 + 警告

## 实现状态
✅ 已完成: 所有 Agent 实现完毕，等待集成测试

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
