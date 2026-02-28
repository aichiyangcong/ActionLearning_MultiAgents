# action_learning_coach/tests/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，标记为测试包
- test_evaluator.py: Evaluator 测试，诱导性问题检测（7 个诱导性用例 + 5 个开放式用例），评分维度验证，边界测试
- test_coach.py: Coach 测试，问题生成质量验证，开放式问题特征检测，错误处理测试
- test_review_loop.py: 审查循环测试，Actor-Critic 模式验证，最大 5 轮限制，通过阈值 95 分，性能测试
- test_e2e.py: 端到端集成测试，Mock 模式完整流程，真实模式流程，验收标准检查，系统稳定性测试

## 测试统计
- 总测试用例: 41
- Mock 模式: 24 个（100% 通过）
- 真实模式: 17 个（需 API Key）
- 代码行数: 850+ 行

## 测试覆盖
- ✅ 诱导性问题检测
- ✅ 审查循环逻辑
- ✅ 问题质量评分
- ✅ 端到端集成
- ✅ 验收标准检查
- ⚠️ 性能测试（需 API Key）

## 运行方式
```bash
# Mock 模式（无需 API Key）
pytest action_learning_coach/tests/ -v

# 真实模式（需 API Key）
export OPENAI_API_KEY=your_key
pytest action_learning_coach/tests/ -v
```

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
