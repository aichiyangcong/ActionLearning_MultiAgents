# action_learning_coach/prompts/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 COACH_SYSTEM_MESSAGE, EVALUATOR_SYSTEM_MESSAGE, OBSERVER_SYSTEM_MESSAGE, REFLECTION_TEMPLATE
- coach_prompt.py: WIAL Master Coach 的隐式 ReAct system message，定义开放式提问规则
- evaluator_prompt.py: Strict Evaluator 的评分标准 system message，定义三维评分体系 (开放性40 + 无诱导性40 + 反思深度20)
- observer_prompt.py: Observer 认知状态提取器 system message，输入对话内容，输出 L1 CognitiveState JSON (< 400 tokens)
- reflection_prompt.py: Reflection Facilitator 的元认知反思模板，含 {current_topic}/{thinking_depth}/{emotional_tone}/{key_assumptions}/{blind_spots} 占位符，由 UpdateSystemMessage 动态注入

## 设计哲学
- Coach: 禁止建议 + 开放提问 + 避免诱导，通过正反例和自检清单强制执行
- Evaluator: 95分阈值 + 三维评分 + 可操作反馈，确保输出质量
- Observer: 传感器定位 + 结构化 JSON + 轻量推理，零对话开销
- Reflection: 不讨论业务本身 + 三层反思 (模式识别/假设挑战/视角转换) + 无审查直达用户

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
