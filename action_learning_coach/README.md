# Action Learning Coach - Terminal UI (Phase 1 MVP)

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 OPENAI_API_KEY
```

### 3. 运行 Terminal 交互界面

```bash
cd action_learning_coach
python3 main.py
```

## 运行模式

系统支持两种运行模式:

### Mock 模式 (默认)
- 无需 API Key
- 使用预设的模拟数据演示审查循环
- 适合测试和演示

### 真实 Agent 模式
- 需要配置 `OPENAI_API_KEY`
- 调用真实的 LLM API
- 完整的 Actor-Critic 审查循环

系统会自动检测环境变量，如果配置了 API Key 则使用真实模式，否则使用 Mock 模式。

### 当前状态

✅ Terminal UI 框架已完成
✅ 流式输出支持
✅ 对话历史记录
✅ Backend Agent 逻辑已完成
✅ Prompt 设计已完成
✅ 真实 LLM 集成已完成
✅ Mock 和真实模式自动切换

## 功能演示

当前版本使用 mock 数据演示完整的审查循环流程:

1. **用户输入**: 描述业务问题
2. **流式输出**: 实时显示思考过程和问题生成
3. **Coach 生成**: 生成问题草案
4. **Evaluator 审查**: 评分 + 反馈
5. **迭代优化**: 未通过则重写，最多 5 轮
6. **输出结果**: 评分 ≥95 分的高质量问题
7. **历史记录**: 输入 'history' 查看对话历史

## 交互命令

- `quit` / `exit` / `q`: 退出系统
- `history`: 查看对话历史

## 示例输出

```
=== 行动学习 AI 陪练系统 (Phase 1 MVP) ===

💡 提示:
  - 输入 'quit' 或 'exit' 退出系统
  - 输入 'history' 查看对话历史

请描述您的业务问题:
> 我们的销售额下降了，怎么办？

[Coach 思考中...]
📝 问题草案: "你觉得这个方案能解决问题吗？"

[Evaluator 审查中... 第 1 轮]
评分: 68/100 ❌ 未通过
  ✗ 开放性: 22/40 - 问题过于封闭，暗示是非判断
  ✗ 无诱导性: 28/40 - "能解决问题"带有诱导性假设
  ✓ 反思深度: 18/20 - 反思深度尚可

[Coach 重写中...]
...

[Evaluator 审查中... 第 3 轮]
评分: 96/100 ✅ 通过
  ✓ 开放性: 39/40 - 高度开放，无预设方向
  ✓ 无诱导性: 39/40 - 完全中立，无诱导
  ✓ 反思深度: 18/20 - 深度反思，触及本质

✨ 最终问题:
  "当你回顾这个方案时，你注意到了什么？"
```

## 技术特性

- **双模式运行**: 自动检测 API Key，支持 Mock 和真实 LLM 模式
- **流式输出**: 模拟真实 LLM 的打字效果
- **思考动画**: 动态显示 Agent 思考状态
- **对话历史**: 记录所有对话，支持回顾
- **模块化设计**: UI 与 Backend 完全解耦
- **Actor-Critic 模式**: Coach 生成 + Evaluator 审查
- **三维评分体系**: 开放性(40) + 无诱导性(40) + 反思深度(20)

## 项目结构

```
action_learning_coach/
├── agents/          # Agent 实现 (Coach, Evaluator, UserProxy)
├── core/            # 核心逻辑 (Config, Nested Chat)
├── prompts/         # Prompt 定义
├── utils/           # 工具函数 (Logger)
├── tests/           # 测试用例
├── main.py          # Terminal UI 入口
├── requirements.txt # 依赖清单
└── .env.example     # 环境变量模板
```

## 下一步

- [x] Backend 实现 WIALMasterCoach 和 StrictEvaluator
- [x] Logic Engineer 设计 Prompt
- [x] 集成真实 LLM API
- [x] 双模式支持 (Mock + Real)
- [ ] 编写测试用例
- [ ] 端到端验收测试
