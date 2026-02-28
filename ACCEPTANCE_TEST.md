# Action Learning Coach 系统验收测试说明书

## 测试环境准备

### 1. 检查 Python 环境
```bash
python3 --version
# 预期输出: Python 3.10 或更高版本
```

### 2. 检查依赖安装
```bash
python3 -c "import httpx; import dotenv; import colorlog; print('✅ 依赖已安装')"
# 预期输出: ✅ 依赖已安装
```

如果报错，执行：
```bash
python3 -m pip install --break-system-packages python-dotenv httpx colorlog
```

### 3. 验证配置文件
```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
cat .env
```

**预期内容**:
```
ANTHROPIC_API_KEY=cr_4ecddb1343efd9ac49c7be9865b183f039f1632b7269e74a0ad7cc13b2eff952
ANTHROPIC_BASE_URL=https://aicode.life/api
COACH_MODEL=claude-sonnet-4-5-20250929
EVALUATOR_MODEL=claude-opus-4-6
```

---

## 测试 1: 基础 API 连接测试

### 目的
验证系统能否成功连接第三方 Anthropic API

### 执行步骤
```bash
cd /Users/zhaoziwei/Desktop/关系行动
python3 test_agent_fix.py
```

### 预期输出
```
============================================================
测试 ConversableAgent 与第三方 Anthropic API
============================================================

1. 加载配置...
   Model: claude-sonnet-4-5-20250929
   Base URL: https://aicode.life/api
   API Key: cr_4ecddb1343efd9ac4...

2. 创建 ConversableAgent...
   Agent Name: TestAgent
   Model: claude-sonnet-4-5-20250929

3. 测试生成回复...
   ✅ 成功! 回复: [LLM 的回复内容]...
```

### 验收标准
- ✅ 无报错信息
- ✅ 显示 "✅ 成功!"
- ✅ 能看到 LLM 的实际回复内容

### 常见问题排查
**问题**: `ModuleNotFoundError: No module named 'dotenv'`
**解决**: 运行 `python3 -m pip install --break-system-packages python-dotenv httpx`

**问题**: `httpx.HTTPStatusError: 403 Forbidden`
**解决**: 检查 API Key 是否正确，检查 .env 文件配置

---

## 测试 2: Coach 生成问题测试

### 目的
验证 WIAL Master Coach 能否正确生成开放式提问

### 执行步骤
```bash
cd /Users/zhaoziwei/Desktop/关系行动
python3 test_system.py
```

### 预期输出 - Coach 部分
```
============================================================
测试 WIAL Master Coach
============================================================

1. 初始化 Coach...
   ✅ Model: claude-sonnet-4-5-20250929

2. 生成问题...
   ✅ 成功!

   Question:
   [生成的开放式问题，例如: "当你说'大家都很焦虑'时，这种焦虑具体是如何表现出来的？"]

   Reasoning:
   [Coach 的推理过程，解释为什么选择这个问题]...
```

### 验收标准
- ✅ Coach 成功初始化
- ✅ 生成的问题是开放式的（不能用是/否回答）
- ✅ 问题不包含隐含建议或预设答案
- ✅ 有清晰的 reasoning 说明

---

## 测试 3: Evaluator 评分测试

### 目的
验证 Strict Evaluator 能否正确评估问题质量

### 执行步骤
继续观察 `test_system.py` 的输出

### 预期输出 - Evaluator 部分
```
============================================================
测试 Strict Evaluator
============================================================

1. 初始化 Evaluator...
   ✅ Model: claude-opus-4-6

2. 评分...
   ✅ 成功!

   Total Score: [分数]/100
   Pass: [True/False]

   Feedback:
   [详细的评分反馈]
```

### 验收标准
- ✅ Evaluator 成功初始化
- ✅ 能够给出 0-100 的分数
- ✅ Pass 状态正确（≥95 为 True，<95 为 False）
- ✅ 提供了详细的反馈说明

---

## 测试 4: 完整系统集成测试

### 目的
验证 Coach 和 Evaluator 能够协同工作

### 执行步骤
观察 `test_system.py` 的最终输出

### 预期输出
```
============================================================
✅ 所有测试通过!
============================================================
```

### 验收标准
- ✅ Coach 和 Evaluator 都成功运行
- ✅ 没有任何错误或异常
- ✅ 显示 "✅ 所有测试通过!"

---

## 测试 5: 交互式 Terminal UI 测试（可选）

### 目的
验证完整的用户交互界面

### 执行步骤
```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
python3 -m main
```

### 预期输出
```
======================================================================
                      行动学习 AI 陪练系统 (Phase 1 MVP)
======================================================================

💡 提示:
  - 输入 'quit' 或 'exit' 退出系统
  - 输入 'history' 查看对话历史

ℹ️  真实 LLM 模式已启用

请描述您的业务问题:
>
```

### 测试场景

#### 场景 1: 基本对话流程
1. 输入: `我们团队最近在项目交付上总是延期，大家都很焦虑`
2. 观察系统生成的问题
3. 检查是否显示评分和审查轮次

**预期行为**:
- 系统生成开放式问题
- 显示评分结果
- 如果评分 ≥95，显示 "✅ 通过审查"
- 如果评分 <95，显示重写过程（最多 5 轮）

#### 场景 2: 查看历史
1. 输入: `history`
2. 观察对话历史记录

**预期行为**:
- 显示所有历史对话
- 包含用户输入、最终问题、审查轮次、最终评分

#### 场景 3: 退出系统
1. 输入: `quit` 或 `exit`

**预期行为**:
- 系统正常退出
- 显示告别消息

---

## 性能验收标准

### 响应时间
- Coach 生成问题: < 30 秒
- Evaluator 评分: < 30 秒
- 完整流程（含审查循环）: < 3 分钟

### 质量标准
- Coach 生成的问题开放性: 应该无法用是/否回答
- Evaluator 评分准确性: 高质量问题应得分 ≥95
- 审查循环有效性: 低质量问题应被打回重写

---

## 故障排查指南

### 问题 1: 导入错误
```
ImportError: attempted relative import beyond top-level package
```

**原因**: 导入路径问题
**解决**: 确保从正确的目录运行脚本
```bash
cd /Users/zhaoziwei/Desktop/关系行动
python3 test_system.py  # 正确

cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
python3 ../test_system.py  # 错误
```

### 问题 2: API 认证失败
```
httpx.HTTPStatusError: 403 Forbidden
```

**原因**: API Key 错误或过期
**解决**:
1. 检查 `.env` 文件中的 `ANTHROPIC_API_KEY`
2. 确认 API Key 有效且有足够额度
3. 测试 API 连接:
```bash
curl -X POST "https://aicode.life/api/v1/messages" \
  -H "x-api-key: YOUR_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5-20250929","messages":[{"role":"user","content":"test"}],"max_tokens":100}'
```

### 问题 3: JSON 解析错误
```
json.JSONDecodeError: Expecting value
```

**原因**: LLM 返回格式异常
**状态**: 已修复（自动提取 markdown 代码块中的 JSON）
**验证**: 运行 `test_system.py` 应该不再出现此错误

### 问题 4: 超时错误
```
httpx.ReadTimeout
```

**原因**: 网络慢或 API 响应慢
**解决**:
1. 检查网络连接
2. 重试请求
3. 如果持续超时，考虑增加 timeout 设置（当前 60 秒）

---

## 验收检查清单

### 基础功能
- [ ] Python 环境正确（3.10+）
- [ ] 依赖包已安装（httpx, python-dotenv）
- [ ] .env 配置文件正确
- [ ] API 连接测试通过

### Coach 功能
- [ ] Coach 能成功初始化
- [ ] 能生成开放式问题
- [ ] 问题质量符合 WIAL 标准
- [ ] 提供清晰的 reasoning

### Evaluator 功能
- [ ] Evaluator 能成功初始化
- [ ] 能正确评分（0-100）
- [ ] Pass/Fail 判断准确（阈值 95）
- [ ] 提供详细反馈

### 系统集成
- [ ] Coach 和 Evaluator 协同工作
- [ ] JSON 解析正常（支持 markdown 代码块）
- [ ] 错误处理健壮
- [ ] 响应时间在可接受范围内

### 用户体验（可选）
- [ ] Terminal UI 正常启动
- [ ] 对话流程流畅
- [ ] 历史记录功能正常
- [ ] 退出功能正常

---

## 验收结论

完成所有测试后，填写以下信息：

**测试日期**: _______________
**测试人员**: _______________
**Python 版本**: _______________
**系统版本**: _______________

**测试结果**:
- 基础 API 连接: [ ] 通过 [ ] 失败
- Coach 生成问题: [ ] 通过 [ ] 失败
- Evaluator 评分: [ ] 通过 [ ] 失败
- 完整系统集成: [ ] 通过 [ ] 失败
- Terminal UI（可选）: [ ] 通过 [ ] 失败 [ ] 未测试

**总体评价**: [ ] 验收通过 [ ] 需要修复

**备注**:
_______________________________________________
_______________________________________________
_______________________________________________

---

## 联系支持

如遇到问题，请提供以下信息：
1. 完整的错误信息（截图或文本）
2. 执行的命令
3. Python 版本和系统版本
4. .env 配置（隐藏 API Key）
