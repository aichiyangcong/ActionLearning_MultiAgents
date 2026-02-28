# Phase 1 MVP 实施计划

## 一、项目目录结构

```
action_learning_coach/
├── agents/
│   ├── __init__.py
│   ├── master_coach.py      # WIAL_Master_Coach - 主控导师
│   ├── evaluator.py          # Strict_Evaluator - 严苛审查员
│   └── user_proxy.py         # UserProxy - 用户代理
├── core/
│   ├── __init__.py
│   ├── nested_chat.py        # Nested Chat 审查循环逻辑
│   └── config.py             # LLM 配置管理
├── prompts/
│   ├── __init__.py
│   ├── coach_prompt.py       # Coach 的隐式 ReAct prompt
│   └── evaluator_prompt.py   # Evaluator 的评分标准 prompt
├── utils/
│   ├── __init__.py
│   └── logger.py             # 日志工具
├── tests/
│   ├── __init__.py
│   ├── test_coach.py
│   ├── test_evaluator.py
│   └── test_nested_chat.py
├── main.py                   # MVP 入口
├── requirements.txt
├── .env.example
└── README.md
```

## 二、核心组件设计

### 2.1 WIAL_Master_Coach (master_coach.py)
**职责**:
- 接收用户的业务问题输入
- 使用隐式 ReAct 模式生成开放式提问
- 调用 Nested Chat 触发审查流程
- 输出高质量问题给用户

**关键接口**:
```python
class WIALMasterCoach:
    def __init__(self, llm_config: dict)
    def generate_question(self, user_input: str) -> str
    def get_agent(self) -> ConversableAgent
```

### 2.2 Strict_Evaluator (evaluator.py)
**职责**:
- 评估 Coach 生成的问题质量
- 打分 0-100 (开放性 40分 + 无诱导性 40分 + 反思深度 20分)
- 评分 <95 则打回并给出修改建议
- 评分 ≥95 则通过

**关键接口**:
```python
class StrictEvaluator:
    def __init__(self, llm_config: dict)
    def evaluate(self, question: str) -> dict  # {score, feedback, pass}
    def get_agent(self) -> ConversableAgent
```

### 2.3 UserProxy (user_proxy.py)
**职责**:
- 代理用户与系统交互
- 注册 Nested Chat 审查流程
- 管理对话历史

**关键接口**:
```python
class UserProxyAgent:
    def __init__(self, llm_config: dict)
    def register_nested_review(self, coach, evaluator)
    def initiate_chat(self, message: str)
```

## 三、Nested Chat 审查流程

```
用户输入业务问题
    ↓
WIAL_Master_Coach 生成问题草案
    ↓
触发 Nested Chat
    ↓
Strict_Evaluator 审查
    ├─ 评分 ≥95 → 通过 → 输出给用户
    └─ 评分 <95 → 打回 → Coach 重写 → 再次审查 (最多5轮)
```

**流程控制**:
- 最大审查轮次: 5轮
- 超过5轮仍未通过: 输出最佳版本 + 警告
- 每轮审查结果记录到日志

## 四、关键文件清单

### 4.1 agents/master_coach.py
```python
# [INPUT]: 依赖 core/config 的 LLM 配置，依赖 prompts/coach_prompt 的提示词
# [OUTPUT]: 对外提供 WIALMasterCoach 类，generate_question 方法
# [POS]: agents 模块的核心组件，负责生成开放式提问
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
```

### 4.2 agents/evaluator.py
```python
# [INPUT]: 依赖 core/config 的 LLM 配置，依赖 prompts/evaluator_prompt 的评分标准
# [OUTPUT]: 对外提供 StrictEvaluator 类，evaluate 方法
# [POS]: agents 模块的审查组件，负责质量把关
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
```

### 4.3 core/nested_chat.py
```python
# [INPUT]: 依赖 agents/master_coach 和 agents/evaluator
# [OUTPUT]: 对外提供 setup_nested_chat 函数
# [POS]: core 模块的编排逻辑，实现 Actor-Critic 模式
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
```

### 4.4 prompts/coach_prompt.py
```python
# [INPUT]: 无外部依赖
# [OUTPUT]: 对外提供 COACH_SYSTEM_MESSAGE 常量
# [POS]: prompts 模块，定义 Coach 的行为规则
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
```

### 4.5 prompts/evaluator_prompt.py
```python
# [INPUT]: 无外部依赖
# [OUTPUT]: 对外提供 EVALUATOR_SYSTEM_MESSAGE 常量
# [POS]: prompts 模块，定义 Evaluator 的评分标准
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
```

### 4.6 main.py
```python
# [INPUT]: 依赖所有 agents 和 core 模块
# [OUTPUT]: Terminal 交互入口
# [POS]: 项目入口，编排整体流程
# [PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
```

## 五、实施顺序建议

### 阶段 1: 基础设施 (并行)
- **Backend**: 搭建项目结构，配置 AG2 环境 (core/config.py)
- **Logic Engineer**: 设计 Coach 和 Evaluator 的 Prompt (prompts/)

### 阶段 2: 核心实现 (并行)
- **Backend**: 实现 master_coach.py 和 evaluator.py
- **Backend**: 实现 nested_chat.py 审查逻辑
- **Frontend**: 实现 main.py Terminal 交互界面

### 阶段 3: 集成测试 (串行)
- **Tester**: 编写测试用例
- **Tester**: 端到端验收测试

## 六、验收标准细化

### 6.1 功能验收
- [ ] 用户输入业务问题，系统能生成开放式提问
- [ ] Evaluator 能检测出诱导性问题 (准确率 >85%)
- [ ] 审查循环能正常工作，最多5轮
- [ ] 最终输出的问题评分 ≥95 分

### 6.2 质量验收
- [ ] 代码覆盖率 ≥80%
- [ ] 所有测试用例通过
- [ ] 符合 PEP8 代码规范
- [ ] 每个文件有 L3 头部注释

### 6.3 性能验收
- [ ] 首字延迟 <1.5s (隐式 ReAct)
- [ ] 单轮审查时间 <3s
- [ ] 完整对话响应 <10s

### 6.4 用户体验验收
- [ ] Terminal 输出清晰易读
- [ ] 审查过程可见 (显示评分和反馈)
- [ ] 错误提示友好

## 七、技术栈确认

- **Python**: 3.10+
- **AG2 (AutoGen)**: 0.2.3+
- **LLM**: OpenAI API (gpt-4o-mini for MVP)
- **测试**: pytest
- **代码质量**: black, flake8, mypy

## 八、环境配置

### requirements.txt
```
pyautogen>=0.2.3
python-dotenv>=1.0.0
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
```

### .env.example
```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
MAX_REVIEW_ROUNDS=5
PASS_SCORE_THRESHOLD=95
```

## 九、开发时间估算

- **阶段 1**: 1天 (项目搭建 + Prompt 设计)
- **阶段 2**: 2-3天 (核心实现 + 集成)
- **阶段 3**: 1天 (测试 + 优化)
- **总计**: 4-5天

## 十、风险与应对

### 风险 1: Evaluator 评分不准确
**应对**: 准备测试用例集，迭代优化 Prompt

### 风险 2: 审查循环陷入死循环
**应对**: 设置最大轮次限制 (5轮)

### 风险 3: LLM API 调用失败
**应对**: 添加重试机制和错误处理

---

**文档状态**: ✅ 已完成
**创建时间**: 2026-02-28
**负责人**: Team Lead
