# Web UI Quickstart

这个版本新增了一个最小可用的 Web 聊天页，封装了当前 `Action Learning` 后端。

## 1. 安装新增依赖

先进入仓库根目录:

```bash
cd /Users/zhaoziwei/Desktop/CodexTest/ActionLearning_MultiAgents
```

如果你的当前环境还没有安装 `FastAPI` 和 `uvicorn`，执行:

```bash
./.venv/bin/python -m pip install -r action_learning_coach/requirements.txt
```

## 2. 启动 Web 服务

在仓库根目录执行:

```bash
./.venv/bin/python -m uvicorn action_learning_coach.web_app:app --host 127.0.0.1 --port 8000 --reload
```

启动后，在浏览器打开:

```text
http://127.0.0.1:8000
```

## 3. 当前交互方式

- 页面提供聊天消息区、输入框、发送按钮和 `New Thread`
- 用户发送消息后，AI 侧会先显示一个转动小圈，表示系统正在内部思考
- 当前版本是**非流式最终返回**
- 也就是说，后端会先完成完整的“生成 → 评审 → 重写(最多 5 轮)”闭环，再一次性把最终回复返回给前端

## 4. 当前为什么先不用真正的 token 流式

当前后端不是单次模型直出，而是内部多轮质量审查:

1. `Coach` 生成催化师回复
2. `Evaluator` 审查
3. 如不通过则重写再审
4. 最终返回最佳结果

所以第一版更适合:

- 前端用 spinner 告知“正在思考”
- 后端完成后一次性返回最终回复

这样不会把中间未通过的草稿直接暴露给用户。

## 5. 后续可扩展方向

如果你后面希望进一步增强体验，下一步最自然的是:

1. 增加 SSE，把 `thinking / reviewing / rewriting / done` 状态推给前端
2. 再决定是否做真正的逐字流式输出
