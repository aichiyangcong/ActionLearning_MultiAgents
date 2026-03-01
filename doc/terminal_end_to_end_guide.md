# 终端端到端体验说明

本文档用于在终端里直接体验 `ActionLearning_MultiAgents` 当前版本的问答流程。

## 1. 前提

- 代码目录: `/Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents`
- Python 虚拟环境: `/Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents/.venv`
- 运行配置文件: `/Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents/action_learning_coach/.env`
- 当前生产环境只使用 `ANTHROPIC_API_KEY`
- 不再依赖 `OPENAI_API_KEY`

## 2. 启动前检查

进入项目目录:

```bash
cd /Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents/action_learning_coach
```

确认 `.env` 已存在:

```bash
ls -la .env
```

如果当前机器访问你的 Anthropic 兼容网关需要代理，先设置:

```bash
export https_proxy=http://127.0.0.1:8118
export http_proxy=http://127.0.0.1:8118
```

如果当前网络直连可用，可以不设置这两个变量。

## 3. 启动交互程序

推荐直接用虚拟环境里的 Python:

```bash
../.venv/bin/python main.py
```

启动成功后，你会看到类似:

- `Orchestrator mode enabled`
- `Coach: ...`
- `Evaluator: ...`

这表示程序已进入真实模型模式。

如果初始化失败，它会自动退回 mock 模式。

## 4. 如何体验一轮问答

程序会提示:

```text
Describe your business problem:
> 
```

此时直接输入你的业务问题，例如:

```text
销售团队因为销量下滑士气大降，理财卖不出去，遭受拒绝比例很高，人员流动大增
```

当前真实主流程会执行:

1. `Coach` 生成第 1 版 AI 催化师回复
   - 一句简短共情
   - 两个不同维度的开放式问题
2. `Evaluator` 对整条回复打分
3. 如果未通过，`Coach` 会根据原始输入、上一版回复、评审反馈重写
4. 再次评审
5. 最多 `5` 轮
6. 最终输出:
   - 通过时: 返回通过的那一版回复
   - 5 轮都没过: 返回 5 轮里分数最高的一版回复

终端当前默认展示的是完整 AI 催化师回复。

## 5. 常用命令

查看历史记录:

```text
history
```

退出程序:

```text
quit
```

或:

```text
exit
```

开始新话题（清空当前连续追问线程，但不清空历史）:

```text
new
```

或:

```text
reset
```

## 6. 当前是否支持“多轮对答”

支持两种“多轮”，但含义要区分开:

### 6.1 支持: 单次输入内部的多轮审查

这是当前最稳定、最核心的能力。

一次用户输入后，系统内部会自动进行最多 5 轮:

- `Coach -> Evaluator -> Coach -> Evaluator ...`

这就是当前的“多轮闭环”。

### 6.2 支持: 终端里连续多次输入，并延续当前线程

你可以在同一个终端会话里连续输入多个业务问题。

每输入一次，程序会跑一轮新的审查闭环，并把结果追加到历史记录里。

如果你不输入 `new` / `reset`，系统会默认把下一次输入当作对当前线程的继续回应，
并把最近几轮的上下文、上一轮 AI 催化师的两问一起带入下一轮生成。

### 6.3 目前已支持: 会话内的连续追问

当前版本已经支持“同一终端会话内”的连续追问:

- 第 1 轮你描述业务问题
- 第 2 轮你回答上一轮的两个问题之一或继续补充
- 系统会基于当前线程继续追问，而不是默认重新开题

### 6.4 仍然有限: 跨进程/跨重启的深度连续追问

当前代码还**不等于**一个完全跨会话持久化的连续教练对话系统。

也就是说:

- 你可以在同一进程里连续输入多轮，并延续当前线程
- 当前线程会继承最近几轮上下文和上一轮的双问题
- 历史和记忆会被记录
- 但跨进程重启后，还没有把长期记忆完整还原成同样强度的连续追问体验

如果你重启程序，想直接恢复到上一次未结束的线程，当前还需要进一步做持久化线程恢复。

## 7. 快速验证当前版本是否工作正常

你可以直接用这句做冒烟测试:

```text
销售团队因为销量下滑士气大降，理财卖不出去，遭受拒绝比例很高，人员流动大增
```

在当前环境下，如果代理可用，程序应该能正常返回一个经过评审的最终问题。

如果上游网关返回 `429 Too Many Requests`:

- 这通常是代理网关限流，不是业务逻辑崩溃
- 当前版本会自动做有限重试
- 如果仍失败，这一轮不会写入历史记录
- 等待几十秒后再重试即可

如果你想退出，请等当前请求返回后，在新的输入提示符下输入 `exit` 或 `quit`。

## 8. 测试命令

如果你只想验证主要单元测试（并跳过真实联机测试），可以用:

```bash
ANTHROPIC_API_KEY=sk-test-fake ../.venv/bin/python -m pytest -q
```

这会让依赖真实模型的测试自动跳过，只检查本地逻辑。
