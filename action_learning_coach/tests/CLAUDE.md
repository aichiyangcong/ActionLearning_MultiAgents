# action_learning_coach/tests/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，标记为测试包
- test_evaluator.py: Evaluator 测试，诱导性问题检测（7 个诱导性用例 + 5 个开放式用例），评分维度验证，边界测试
- test_coach.py: Coach 测试，问题生成质量验证，开放式问题特征检测，错误处理测试
- test_review_loop.py: 审查循环测试，Actor-Critic 模式验证，最大 5 轮限制，通过阈值 95 分，性能测试
- test_e2e.py: 端到端集成测试，Mock 模式完整流程，真实模式流程，验收标准检查，系统稳定性测试
- test_phase2a_integration.py: Phase 2a 集成测试 (42 用例)，验证 AG2 编排骨架 + Coach-Evaluator 审查循环场景
- test_phase2c_observer.py: Phase 2c Observer 测试 (28 用例)，验证 Observer config/prompt/FunctionTarget 签名/逻辑/Orchestrator 集成/认知状态同步
- test_phase2d_fsm.py: Phase 2d 双轨 FSM 测试 (38 用例)，验证 Reflection config/prompt/Agent/双轨路由/关键词检测/Orchestrator 集成/边界值

## 测试统计
- 总测试用例: 149
- Phase 1 Mock 模式: 24 个（100% 通过）
- Phase 1 真实模式: 17 个（需 API Key）
- Phase 2a 集成测试: 42 个（100% 通过，无需 API Key）
- Phase 2c Observer 测试: 28 个（100% 通过，无需 API Key）
- Phase 2d 双轨 FSM 测试: 38 个（100% 通过，无需 API Key）

## 运行方式
```bash
# 全部测试
PYTHONPATH=action_learning_coach .venv/bin/python -m pytest action_learning_coach/tests/ -v

# 仅 Phase 2d 双轨 FSM 测试
PYTHONPATH=action_learning_coach .venv/bin/python -m pytest action_learning_coach/tests/test_phase2d_fsm.py -v

# Phase 2 全部测试 (无回归验证)
PYTHONPATH=action_learning_coach .venv/bin/python -m pytest action_learning_coach/tests/test_phase2a_integration.py action_learning_coach/tests/test_phase2c_observer.py action_learning_coach/tests/test_phase2d_fsm.py -v
```

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
