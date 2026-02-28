# 📄 行动学习（WIAL）AI陪练系统 - 核心架构与工程说明书

## 一、 核心产品哲学与系统“红线”（System Boundaries）

*明确告诉 CTO，我们不是在做一个聪明的问答机器人，而是一个“克制的提问者”。*

* **绝对红线（Zero-Tolerance Rule）**：系统在任何情况下，**绝对禁止**直接解答用户的业务问题（No Deterministic Direct Answers）。
* **交互范式**：从“Query-Response（问答）”转变为“Listen-Reflect-Facilitate（倾听-反思-引导）”。
* **核心输出**：系统的大部分有效输出必须是**结构化提问**，或者是为了铺垫提问而进行的客观事实陈述。

## 二、 系统架构图谱：5层架构映射 (Architecture Mapping)

*将前期的 5 层理论翻译为 CTO 能懂的组件。*

1. **交互层 (Interaction Layer)**：MVP 阶段仅支持纯文本流式输入/输出（WebSocket 或 SSE），预留未来接入实时语音（如 WebRTC/LiveKit）的接口。
2. **路由与状态机层 (FSM Routing Layer)**：控制“业务探索轨（Business Track）”与“学习反思轨（Reflection Track）”的强行切换。
3. **多智能体核心层 (Agentic Core via AG2)**：使用纯 AG2 (AutoGen 2) 框架实现，包含主控、评估、模拟对象等多个 Agent 的博弈。
4. **工具与知识注入层 (Tool & Knowledge Layer)**：将 ORID、MECE 等框架封装为 Python Functions。对于外部专业知识库或复杂流转，预留通过 Webhook 呼叫外部编排工具（如 n8n 或 Coze）的接口。
5. **数据治理层 (Data Layer)**：记录全量对话日志、评估打分 JSON 和状态转移轨迹，用于后续 SaaS 看板展示。

## 三、 核心智能体拓扑与职责划分 (Agent Topology)

*详细定义 AG2 中的具体 Agent 角色。*

* **1. UserProxy Agent (人类代理)**：
* 负责接收人类学员的自然语言输入，并传递给系统。


* **2. WIAL_Master_Coach (主控导师 Agent)**：
* **职责**：维持 WIAL 状态机，决定何时发言、调用何种引导框架。
* **机制**：必须采用 ReAct 模式，先输出 `<thought>`（语义树解析、意图判定），再决定下一步 Action（是继续沉默、调用 ORID 工具，还是生成问题草案）。


* **3. Strict_Evaluator (严苛的内部审查 Agent)**：
* **职责**：把关主控导师生成的每一次“问题草案”。
* **机制**：根据预设的 Rubrics（开放性、无诱导性、语气），对草案进行打分（0-100）。得分 `<95` 则打回，并附带具体的修改要求（Critique）。


* **4. Counterpart_Sim (模拟沟通对象 Agent)** *(注：如果是角色扮演模式才需要)*：
* **职责**：扮演特定职场角色（如老板、下属），自带情绪曲线和预设的业务挑战。



## 四、 核心工作流：Nested Chat 审查机制 (The Actor-Critic Workflow)

*这是防翻车的最关键工程设计。*

1. 学员输入信息。
2. `WIAL_Master_Coach` 被触发，结合上下文生成一个干预问题草案。
3. **[静默拦截]**：系统不将草案发给学员，而是通过 AG2 的 `Nested Chat` 机制，将草案发送给 `Strict_Evaluator`。
4. `Strict_Evaluator` 校验：“该问题是否包含隐性建议？” -> 发现违规，返回：“包含诱导，重写为纯开放式”。
5. `WIAL_Master_Coach` 重写草案，再次提交审查。
6. 循环直到 `Strict_Evaluator` 返回 `PASS`。
7. 系统将最终问题流式输出给学员。

## 五、 双轨状态机流转 (Dual-Track FSM)

*定义什么时候讨论业务，什么时候进行反思。*

* **Track A: 业务探索轨 (BUSINESS_TRACK)**
* **常态**：系统旁观学员（或团队）解决具体商业 Problem。
* **触发转移条件**：检测到对话陷入停滞（如情绪词激增、重复性对话）、或攻克了一个关键节点、或已满 15 轮对话。


* **Track B: 学习反思轨 (REFLECTION_TRACK)**
* **动作**：强制切断业务讨论。调用 `trigger_reflection_tool()`。
* **输出**：“暂停一下业务讨论。刚才遇到分歧时，你们是如何调整沟通策略的？”
* **触发转移条件**：学员完成元认知复盘，输入“继续业务”，状态机切回 Track A。



## 六、 MVP 阶段的“先决目标”（To Cursor / CTO）

*控制开发边界，避免一上来就写出庞大且无法运行的代码。*

* **Phase 1 (本周)**：不搞前端，不接语音。在终端（Terminal）里跑通 AG2 的 `WIAL_Master_Coach` 与 `Strict_Evaluator` 的 **Nested Chat 审查循环**。证明系统能“打回自己写得不好的建议”。
* **Phase 2**：加入 FSM，跑通从“业务轨”硬切到“反思轨”的逻辑。
* **Phase 3**：用 FastAPI 将后端封装，写一个极简的 Web 聊天框，测试整体连贯性。
