# action_learning_coach/prompts/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 COACH_SYSTEM_MESSAGE, EVALUATOR_SYSTEM_MESSAGE
- coach_prompt.py: WIAL Master Coach 的隐式 ReAct system message，定义开放式提问规则
- evaluator_prompt.py: Strict Evaluator 的评分标准 system message，定义三维评分体系 (开放性40 + 无诱导性40 + 反思深度20)

## 设计哲学
- Coach: 禁止建议 + 开放提问 + 避免诱导，通过正反例和自检清单强制执行
- Evaluator: 95分阈值 + 三维评分 + 可操作反馈，确保输出质量

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
