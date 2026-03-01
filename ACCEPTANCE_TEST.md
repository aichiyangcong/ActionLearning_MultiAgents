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

---

# Phase 2 验收测试说明书

> **版本**: v1.0
> **日期**: 2026-03-01
> **覆盖范围**: Phase 2a (AG2 迁移) + Phase 2b (三层记忆) + Phase 2c (Observer) + Phase 2d (双轨 FSM)

---

## Phase 2 测试环境准备

> **注意**: 虚拟环境位于项目根目录 `/Users/zhaoziwei/Desktop/关系行动/.venv/`
> 以下所有命令中 `PYTHON` 指 `/Users/zhaoziwei/Desktop/关系行动/.venv/bin/python`
> 业务代码目录为 `action_learning_coach/`，需在该目录下运行 Agent 相关命令

### 1. 检查 Python 环境与依赖

```bash
cd /Users/zhaoziwei/Desktop/关系行动
.venv/bin/python --version
# 预期: Python 3.10+
```

### 2. 验证 AG2 框架可用

```bash
cd /Users/zhaoziwei/Desktop/关系行动
.venv/bin/python -c "
from autogen import ConversableAgent, UserProxyAgent
from autogen.agentchat import initiate_group_chat, ContextVariables
from autogen.agentchat.group import OnCondition, RevertToUserTarget, FunctionTarget
from autogen.agentchat.group.patterns.pattern import DefaultPattern
print('AG2 框架导入成功')
"
# 预期: AG2 框架导入成功
```

### 3. 验证 Phase 2 新增环境变量

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
cat .env
```

**预期内容（Phase 2 新增项）**:
```
OBSERVER_MODEL=claude-haiku-4-5        # Observer 轻量模型（可选，默认 claude-haiku-4-5）
REFLECTION_MODEL=claude-sonnet-4-5-20250929  # Reflection 模型（可选，默认同 Coach）
```

---

## 测试 6: Phase 2 自动化测试套件（核心验证）

### 目的
一次性验证 Phase 2 全部 108 个测试用例

### 执行步骤
```bash
cd /Users/zhaoziwei/Desktop/关系行动
.venv/bin/python -m pytest action_learning_coach/tests/test_phase2a_integration.py action_learning_coach/tests/test_phase2c_observer.py action_learning_coach/tests/test_phase2d_fsm.py -v
```

### 预期输出
```
test_phase2a_integration.py  — 42 passed
test_phase2c_observer.py     — 28 passed
test_phase2d_fsm.py          — 38 passed
============================= 108 passed ==============================
```

### 验收标准
- [ ] 108 个测试全部通过
- [ ] 无 warning 或 error
- [ ] 运行时间 < 5 秒（不调用真实 API）

---

## 测试 7: Phase 2a — AG2 真实迁移验证

### 目的
验证假适配器已删除，所有 Agent 使用真实 AG2 ConversableAgent

### 7.1 假适配器已删除

```bash
ls /Users/zhaoziwei/Desktop/关系行动/action_learning_coach/core/autogen_adapter.py 2>&1
# 预期: No such file or directory
```

### 7.2 Agent 导入验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from agents import WIALMasterCoach, StrictEvaluator, UserProxy, observe_turn, ReflectionFacilitator
print('5 个 Agent 导入成功')
print(f'  WIALMasterCoach: {WIALMasterCoach}')
print(f'  StrictEvaluator: {StrictEvaluator}')
print(f'  UserProxy: {UserProxy}')
print(f'  observe_turn: {observe_turn}')
print(f'  ReflectionFacilitator: {ReflectionFacilitator}')
"
```

### 7.3 Orchestrator 创建 Session

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from core.orchestrator import Orchestrator, TurnResult
orch = Orchestrator()
orch.create_session()
print(f'Coach: {orch.coach}')
print(f'Evaluator: {orch.evaluator}')
print(f'Reflection: {orch.reflection}')
assert orch.coach is not None, 'Coach 未创建'
assert orch.evaluator is not None, 'Evaluator 未创建'
assert orch.reflection is not None, 'Reflection 未创建'
print('Orchestrator 创建成功，所有 Agent 就绪')
"
```

### 7.4 NestedChat 配置验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from core.nested_chat import create_nested_chat_config
from autogen import ConversableAgent
from autogen.agentchat.group.targets.transition_target import NestedChatTarget

# 创建临时 evaluator 以验证配置
evaluator = ConversableAgent(name='test_eval', llm_config=False)
target = create_nested_chat_config(evaluator, max_rounds=5)
print(f'返回类型: {type(target).__name__}')
assert isinstance(target, NestedChatTarget), 'NestedChatTarget 类型不匹配'
print('NestedChatTarget 配置正确')
"
```

### 验收标准
- [ ] `autogen_adapter.py` 源文件已删除
- [ ] 5 个 Agent（Coach, Evaluator, UserProxy, Observer, Reflection）导入成功
- [ ] Orchestrator 可创建 Session，所有 Agent 初始化无报错
- [ ] NestedChat 返回真实 AG2 `NestedChatTarget` 实例

---

## 测试 8: Phase 2b — 三层记忆系统验证

### 目的
验证 L1/L2/L3 数据结构、文件 I/O、ContextVariables 集成

### 8.1 数据结构验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from memory import CognitiveState, SummaryChain, SummaryEntry, LearnerProfile, SessionManager

# L1 认知状态
cs = CognitiveState(current_topic='测试问题', emotional_tone='neutral', turn_number=1)
d = cs.to_dict()
cs2 = CognitiveState.from_dict(d)
assert cs2.current_topic == '测试问题'
print(f'L1 CognitiveState: 序列化/反序列化 通过')

# L2 摘要链
sc = SummaryChain()
sc.append(SummaryEntry(phase='test', turns='1-3', summary='测试摘要'))
assert len(sc.entries) == 1
print(f'L2 SummaryChain: 追加 通过')

# L3 学习者画像
lp = LearnerProfile(learner_id='test_user')
d = lp.to_dict()
lp2 = LearnerProfile.from_dict(d)
assert lp2.learner_id == 'test_user'
print(f'L3 LearnerProfile: 序列化/反序列化 通过')

print('三层数据结构全部正常')
"
```

### 8.2 文件 I/O 验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
import json, os, shutil
from memory import CognitiveState, SummaryChain, SummaryEntry, LearnerProfile, SessionManager
from memory.raw_log import append_raw_log

# 创建临时会话
sm = SessionManager('test_acceptance', 'test_learner')
sm.init_session()

# L1 覆写测试
cs1 = CognitiveState(current_topic='第一轮', turn_number=1)
sm.save_cognitive_state(cs1)
cs2 = CognitiveState(current_topic='第二轮', turn_number=2)
sm.save_cognitive_state(cs2)
loaded = sm.load_cognitive_state()
assert loaded.current_topic == '第二轮', 'L1 应为覆写而非累积'
print('L1 覆写验证: 通过')

# L2 追加测试
sc = SummaryChain()
sc.append(SummaryEntry(phase='p1', turns='1-3', summary='阶段1摘要'))
sm.save_summary_chain(sc)
sc.append(SummaryEntry(phase='p2', turns='4-6', summary='阶段2摘要'))
sm.save_summary_chain(sc)
loaded_sc = sm.load_summary_chain()
assert len(loaded_sc.entries) == 2
print('L2 追加验证: 通过')

# Raw JSONL 测试
session_dir = sm.session_dir
append_raw_log(session_dir, {'role': 'user', 'content': '测试1', 'turn': 1})
append_raw_log(session_dir, {'role': 'coach', 'content': '测试2', 'turn': 2})
log_path = os.path.join(session_dir, 'raw_dialogue.jsonl')
with open(log_path) as f:
    lines = f.readlines()
assert len(lines) == 2
print('Raw JSONL 追加验证: 通过')

# 清理
shutil.rmtree(os.path.dirname(session_dir), ignore_errors=True)
print('三层记忆文件 I/O 全部正常')
"
```

### 8.3 数据持久化验证（检查已有会话数据）

```bash
ls /Users/zhaoziwei/Desktop/关系行动/action_learning_coach/data/sessions/ | head -5
# 预期: 显示多个 session 目录（格式: YYYYMMDD_HHMMSS_xxxxxx）

ls /Users/zhaoziwei/Desktop/关系行动/action_learning_coach/data/learners/
# 预期: 显示 learner 目录（至少有 default/）
```

### 验收标准
- [ ] L1 CognitiveState 序列化/反序列化正确
- [ ] L2 SummaryChain 追加逻辑正确
- [ ] L3 LearnerProfile 序列化/反序列化正确
- [ ] L1 为覆写模式（后写覆盖先写）
- [ ] Raw JSONL 逐行追加
- [ ] `data/sessions/` 和 `data/learners/` 目录存在且有真实数据

---

## 测试 9: Phase 2c — Observer Agent 验证

### 目的
验证 Observer 作为 FunctionTarget 实现，可提取认知状态并路由

### 9.1 Observer 函数签名验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
import inspect
from agents.observer import observe_turn

sig = inspect.signature(observe_turn)
params = list(sig.parameters.keys())
print(f'参数列表: {params}')

# 验证 FunctionTarget 兼容签名
assert params[0] == 'output', '第一参数必须是 output'
assert params[1] == 'ctx', '第二参数必须是 ctx'
assert 'observer_config' in params
assert 'coach_agent' in params
assert 'reflection_agent' in params
print('Observer 函数签名符合 FunctionTarget 规范')
"
```

### 9.2 Observer Mock 模式测试

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from autogen.agentchat import ContextVariables
from agents.observer import observe_turn

# Mock 模式：不传 observer_config，不调用 LLM
ctx = ContextVariables(data={'round': 1, 'summary_chain': {'entries': []}})
result = observe_turn('用户说了一些话', ctx)

print(f'返回类型: {type(result).__name__}')
cognitive = result.context_variables.get('cognitive_state')
print(f'认知状态: {cognitive}')
print(f'目标 Agent: {result.target}')
print('Observer Mock 模式正常工作')
"
```

### 9.3 Observer Prompt 验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE

# 验证关键字段
assert 'current_topic' in OBSERVER_SYSTEM_MESSAGE
assert 'reflection_readiness' in OBSERVER_SYSTEM_MESSAGE
assert 'emotional_tone' in OBSERVER_SYSTEM_MESSAGE
assert 'JSON' in OBSERVER_SYSTEM_MESSAGE

# 验证 token 预算 (粗略估算: 1 token ~ 4 chars)
token_estimate = len(OBSERVER_SYSTEM_MESSAGE) / 4
print(f'Observer Prompt 预估 tokens: {token_estimate:.0f}')
print('Observer Prompt 包含所有必要字段')
"
```

### 9.4 Observer 模型配置验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from core.config import get_llm_config

config = get_llm_config('observer')
print(f'Observer 模型: {config.model}')
print(f'Observer 配置: {config}')
print('Observer 模型配置正确')
"
```

### 验收标准
- [ ] `observe_turn` 函数签名符合 `FunctionTarget` 规范（output, ctx, **extra_args）
- [ ] Mock 模式下不调用 LLM，返回默认 CognitiveState
- [ ] 返回类型为 `FunctionTargetResult`
- [ ] Observer Prompt 包含 `current_topic`, `reflection_readiness`, `emotional_tone` 等字段
- [ ] `get_llm_config('observer')` 返回正确配置（默认 claude-haiku-4-5）

---

## 测试 10: Phase 2d — 双轨 FSM + Reflection Agent 验证

### 目的
验证双轨切换逻辑（Business ↔ Reflection）和 Reflection Agent

### 10.1 Reflection Agent 创建

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from agents.reflection_agent import ReflectionFacilitator
from core.config import get_llm_config

config = get_llm_config('reflection')
rf = ReflectionFacilitator(config)
agent = rf.get_agent()

print(f'Agent 名称: {agent.name}')
print(f'Agent 类型: {type(agent).__name__}')
print('ReflectionFacilitator 创建成功')
"
```

### 10.2 Reflection Prompt 模板验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from prompts.reflection_prompt import REFLECTION_TEMPLATE

# 验证 5 个占位符存在
placeholders = ['current_topic', 'emotional_tone', 'blind_spots', 'key_assumptions', 'anchor_quotes']
for p in placeholders:
    assert '{' + p + '}' in REFLECTION_TEMPLATE, f'缺少占位符: {p}'
    print(f'  占位符 {p}: 存在')

# 验证三层反思结构
assert '表层' in REFLECTION_TEMPLATE or 'surface' in REFLECTION_TEMPLATE.lower() or '第一层' in REFLECTION_TEMPLATE
print('Reflection Prompt 模板验证通过')
"
```

### 10.3 双轨路由逻辑验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from agents.observer import _route
from autogen import ConversableAgent
from autogen.agentchat import ContextVariables

# 创建 mock agents
coach = ConversableAgent(name='Coach', llm_config=False)
reflection = ConversableAgent(name='Reflection', llm_config=False)

# _route 签名: (current_track, readiness, output, ctx, coach_agent, reflection_agent)
# 返回: (target_agent, next_track, reflection_turn_count)

# 场景 1: Business Track, 低 readiness → 留在 Business
ctx = ContextVariables(data={'reflection_turn_count': 0})
agent, track, _ = _route('business', 0.3, '正常讨论', ctx, coach, reflection)
print(f'低 readiness (0.3): → {agent.name}, track={track}')
assert agent.name == 'Coach'

# 场景 2: Business Track, 高 readiness → 切到 Reflection
agent, track, _ = _route('business', 0.8, '正常讨论', ctx, coach, reflection)
print(f'高 readiness (0.8): → {agent.name}, track={track}')
assert agent.name == 'Reflection'

# 场景 3: Reflection Track, 低 readiness → 切回 Business
ctx3 = ContextVariables(data={'reflection_turn_count': 1})
agent, track, _ = _route('reflection', 0.3, '正常讨论', ctx3, coach, reflection)
print(f'反思中低 readiness (0.3): → {agent.name}, track={track}')
assert agent.name == 'Coach'

# 场景 4: Reflection Track, 用户要求回到业务
agent, track, _ = _route('reflection', 0.8, '继续讨论业务问题', ctx3, coach, reflection)
print(f'用户请求回业务: → {agent.name}, track={track}')
assert agent.name == 'Coach'

# 场景 5: Reflection Track, 超过最大轮次
ctx5 = ContextVariables(data={'reflection_turn_count': 3})
agent, track, _ = _route('reflection', 0.8, '继续反思', ctx5, coach, reflection)
print(f'超过最大轮次 (3): → {agent.name}, track={track}')
assert agent.name == 'Coach'

print('双轨路由全部 5 个场景验证通过')
"
```

### 10.4 Orchestrator 完整 FSM 配置验证

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach
../.venv/bin/python -c "
from core.orchestrator import Orchestrator

orch = Orchestrator()
orch.create_session()

# 验证 ContextVariables 包含轨道状态
ctx = orch._ctx
print(f'current_track: {ctx[\"current_track\"]}')
print(f'reflection_turn_count: {ctx[\"reflection_turn_count\"]}')
print(f'cognitive_state: {type(ctx[\"cognitive_state\"]).__name__}')
print(f'summary_chain: {type(ctx[\"summary_chain\"]).__name__}')

# 验证 Reflection Agent 存在
assert orch.reflection is not None, 'Reflection Agent 未创建'
print(f'Reflection: {orch.reflection}')
print('Orchestrator FSM 配置完整')
"
```

### 验收标准
- [ ] ReflectionFacilitator 可创建，使用 UpdateSystemMessage 动态注入认知状态
- [ ] Reflection Prompt 包含 5 个占位符（current_topic, emotional_tone, blind_spots, key_assumptions, anchor_quotes）
- [ ] 双轨路由 5 个场景全部正确：
  - 低 readiness → Business Track
  - 高 readiness (>= 0.7) → Reflection Track
  - Reflection 中低 readiness → 切回 Business
  - 用户关键词请求 → 切回 Business
  - 超过最大反思轮次 (3) → 切回 Business
- [ ] Orchestrator ContextVariables 包含 `current_track`, `reflection_turn_count`
- [ ] Reflection Agent 在 Orchestrator 中正确初始化

---

## 测试 11: 文档完整性验证（GEB 协议）

### 目的
验证所有 CLAUDE.md 已按 GEB 分形文档协议更新

### 执行步骤

```bash
cd /Users/zhaoziwei/Desktop/关系行动/action_learning_coach

# 检查所有 CLAUDE.md 是否存在
echo "=== L2 文档检查 ==="
for dir in agents core memory prompts tests; do
    if [ -f "$dir/CLAUDE.md" ]; then
        echo "  $dir/CLAUDE.md: 存在"
    else
        echo "  $dir/CLAUDE.md: 缺失!"
    fi
done

# 检查 PROTOCOL 标记
echo ""
echo "=== PROTOCOL 标记检查 ==="
grep -rl "PROTOCOL" --include="*.md" . | sort
```

### 验收标准
- [ ] `agents/CLAUDE.md` — 包含 observer.py 和 reflection_agent.py
- [ ] `core/CLAUDE.md` — 包含 orchestrator.py，不含 autogen_adapter.py
- [ ] `memory/CLAUDE.md` — 新建，描述三层记忆架构
- [ ] `prompts/CLAUDE.md` — 包含 observer_prompt.py 和 reflection_prompt.py
- [ ] `tests/CLAUDE.md` — 包含 Phase 2 测试文件
- [ ] 所有 CLAUDE.md 包含 `[PROTOCOL]` 标记

---

## 测试 12: 交互式端到端测试（Terminal，推荐先做）

### 目的
验证当前真实终端交互链路可运行，并确认“连续追问线程”与内部 5 轮审查闭环正常工作。

### 执行步骤

```bash
cd /Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents/action_learning_coach

# 如果当前机器访问第三方 Anthropic 兼容网关需要代理，先设置
export https_proxy=http://127.0.0.1:8118
export http_proxy=http://127.0.0.1:8118

../.venv/bin/python main.py
```

### 启动成功的预期输出

```text
======================================================================
                  Action Learning AI Coach (Phase 2)
======================================================================

  Commands:
  - 'quit' or 'exit' to leave
  - 'history' to view conversation history
  - 'new' or 'reset' to start a new conversation thread

  Orchestrator mode enabled
  Coach: ...
  Evaluator: ...
```

### 测试场景

#### 场景 1: 首轮问题输入
1. 在 `Describe your business problem:` 提示后输入:
   - `销售团队因为销量下滑士气大降，理财卖不出去，遭受拒绝比例很高，人员流动大增`
2. 观察系统输出

**预期行为**:
- 系统完成内部“Coach 生成 → Evaluator 审查 → 必要时重写”的闭环
- 终端最终显示 `AI Catalyst Reply`
- 回复内容包含:
  - 一句简短共情
  - `Q1`
  - `Q2`
- `data/sessions/` 下生成新的会话目录

#### 场景 2: 连续追问线程
1. 在 `Continue the conversation:` 提示后继续输入:
   - `他们最明显的变化是开始回避客户，而且会在晨会里沉默。`
2. 观察系统输出

**预期行为**:
- 系统不应把这次输入当成全新开题
- 新一轮回复应明显承接上一轮上下文继续深挖
- 回复仍然保持:
  - 一句简短共情
  - 两个不同维度的问题

#### 场景 3: 重置线程
1. 输入: `new`
2. 再输入一个全新业务问题

**预期行为**:
- 终端显示 `Started a new conversation thread.`
- 下一次提问应从新线程开始，不再默认承接上一轮问题

#### 场景 4: 查看持久化数据
```bash
ls -la /Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents/data/sessions/ | tail -3
```

任选最新目录后，检查:

```bash
cat /Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents/data/sessions/{最新目录}/raw_dialogue.jsonl | head -5
```

### 验收标准
- [ ] 终端可正常启动，不报初始化错误
- [ ] 首轮输入后能返回完整 `AI Catalyst Reply`
- [ ] 回复包含一句简短共情和两个问题
- [ ] 第二轮输入可延续当前线程，而不是默认重新开题
- [ ] `new` / `reset` 可成功开启新线程
- [ ] `data/sessions/` 中出现新的会话目录和原始日志文件

---

## 测试 13: Web UI 端到端测试（推荐体验界面）

### 目的
验证 Web 聊天界面可以正常启动，用户可通过输入框进行提问，并在等待期间看到“思考中”的转动小圈。

### 执行步骤

在仓库根目录启动 Web 服务:

```bash
cd /Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents
./.venv/bin/python -m uvicorn action_learning_coach.web_app:app --host 127.0.0.1 --port 8000 --reload
```

在浏览器打开:

```text
http://127.0.0.1:8000
```

### 页面加载成功的预期状态
- 左侧显示 `AI Catalyst` 说明面板
- 右侧显示聊天消息区
- 底部有多行输入框
- 顶部有 `New Thread`
- 初始系统消息提示可以开始输入业务问题

### 测试场景

#### 场景 1: 首轮输入
1. 在输入框中输入:
   - `销售团队因为销量下滑士气大降，理财卖不出去，遭受拒绝比例很高，人员流动大增`
2. 点击 `Send`

**预期行为**:
- 页面立刻新增一条用户消息
- AI 侧立刻出现一个带转动小圈的占位消息
- 若干秒后，占位消息被替换为正式回复
- 正式回复包含:
  - 一句简短共情
  - `Q1`
  - `Q2`
  - 底部显示 `Review: X rounds | Score: Y/100`

#### 场景 2: 连续对话
1. 在同一页面继续输入:
   - `他们最明显的变化是开始回避客户，而且会在晨会里沉默。`
2. 点击 `Send`

**预期行为**:
- 页面再次显示转动小圈
- 返回的新回复应承接上一轮上下文，而不是完全重置

#### 场景 3: 新建线程
1. 点击 `New Thread`
2. 观察页面状态

**预期行为**:
- 旧消息区被清空
- 页面插入一条新的系统提示消息
- 之后输入的新问题不再承接上一轮上下文

### 验收标准
- [ ] `uvicorn` 可正常启动，无导入错误
- [ ] 浏览器可打开 `http://127.0.0.1:8000`
- [ ] 点击 `Send` 后，AI 侧会先显示转动小圈
- [ ] 返回结果为完整的 AI 催化师回复，而不是空白
- [ ] Web UI 支持连续对话
- [ ] `New Thread` 可重置当前 Web 会话线程

---

## Phase 2 验收检查清单

### Phase 2a: AG2 迁移
- [ ] `autogen_adapter.py` 已删除
- [ ] 所有 Agent import 改为真实 `autogen`
- [ ] Orchestrator 当前主路径使用显式 `Coach -> Evaluator -> 重写` 最多 5 轮闭环
- [ ] `NestedChat` 已降级为 legacy 兼容路径，不再承担主流程
- [ ] Terminal 模式支持连续追问线程与 `new` / `reset`
- [ ] 47 个 Phase 2a 集成测试全部通过

### Phase 2b: 三层记忆系统
- [ ] L1 CognitiveState 覆写模式正确
- [ ] L2 SummaryChain 追加模式正确
- [ ] L3 LearnerProfile 渐进更新正确
- [ ] Raw JSONL 逐行追加
- [ ] SessionManager 文件 I/O 正常
- [ ] ContextVariables 携带 L1/L2/L3

### Phase 2c: Observer Agent
- [ ] Observer 实现为 `FunctionTarget`（非 ConversableAgent）
- [ ] Observer Prompt 输出 < 400 tokens 结构化 JSON
- [ ] Mock 模式可用（无 API 调用）
- [ ] 模型配置支持 `claude-haiku-4-5`
- [ ] 29 个 Observer 测试全部通过

### Phase 2d: 双轨 FSM
- [ ] ReflectionFacilitator 使用 `UpdateSystemMessage`
- [ ] Reflection Prompt 包含 5 个动态占位符
- [ ] 双轨路由 5 个场景全部正确
- [ ] `after_work` 链路完整: UserProxy→Observer→Coach/Reflection
- [ ] Reflection Agent 使用 `RevertToUserTarget`
- [ ] 38 个 FSM 测试全部通过

### 文档完整性
- [ ] 根级 CLAUDE.md 已更新（Phase 2 状态）
- [ ] agents/CLAUDE.md 包含 5 个文件
- [ ] core/CLAUDE.md 包含 3 个文件（无 autogen_adapter）
- [ ] memory/CLAUDE.md 新建完成
- [ ] prompts/CLAUDE.md 包含 4 个文件
- [ ] tests/CLAUDE.md 包含 7 个测试文件

### 已知缺项
- [ ] `tests/test_memory.py` 未创建（memory 模块独立单元测试缺失，但 memory 功能被 Observer 和 Orchestrator 测试间接覆盖）
- [ ] SSE / 真正流式输出尚未实现（当前 Web UI 为非流式最终返回 + spinner）
- [ ] 跨进程重启后的会话线程恢复尚未实现（当前连续追问仅保证单次运行进程内有效）

---

## Phase 2 验收结论

**测试日期**: _______________
**测试人员**: _______________
**Python 版本**: _______________
**AG2 版本**: _______________

**自动化测试结果**:
- Phase 2a 集成测试 (47): [ ] 通过 [ ] 失败
- Phase 2c Observer 测试 (29): [ ] 通过 [ ] 失败
- Phase 2d FSM 测试: [ ] 通过 [ ] 失败
- Web UI API 测试 (4): [ ] 通过 [ ] 失败
- 合计核心测试: [ ] 全部通过 [ ] 部分失败

**手动验证结果**:
- AG2 迁移验证: [ ] 通过 [ ] 失败
- 三层记忆验证: [ ] 通过 [ ] 失败
- Observer 验证: [ ] 通过 [ ] 失败
- 双轨 FSM 验证: [ ] 通过 [ ] 失败
- Terminal 连续对话验证: [ ] 通过 [ ] 失败
- 文档完整性: [ ] 通过 [ ] 失败
- 交互式端到端（Terminal）: [ ] 通过 [ ] 失败 [ ] 未测试
- Web UI 端到端（可选）: [ ] 通过 [ ] 失败 [ ] 未测试

**总体评价**: [ ] Phase 2 验收通过 [ ] 需要修复

**备注**:
_______________________________________________
_______________________________________________

---

## 联系支持

如遇到问题，请提供以下信息：
1. 完整的错误信息（截图或文本）
2. 执行的命令
3. Python 版本和系统版本
4. .env 配置（隐藏 API Key）
