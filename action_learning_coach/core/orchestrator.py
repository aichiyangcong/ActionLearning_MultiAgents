"""
[INPUT]: 依赖 autogen (ConversableAgent, UserProxyAgent),
         依赖 autogen.agentchat (initiate_group_chat, ContextVariables),
         依赖 autogen.agentchat.group (DefaultPattern, RevertToUserTarget, FunctionTarget),
         依赖 agents (WIALMasterCoach, StrictEvaluator, observe_turn, ReflectionFacilitator),
         依赖 core/config (LLMConfig, get_llm_config),
         依赖 core/nested_chat (create_nested_chat_config),
         依赖 memory (CognitiveState, SummaryChain, LearnerProfile, SessionManager)
[OUTPUT]: 对外提供 Orchestrator 类，create_session / run_turn 方法，TurnResult
[POS]: core 模块的中枢编排器，双轨 FSM (Business ↔ Reflection)，三层记忆持久化
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from autogen import ConversableAgent, UserProxyAgent
from autogen.agentchat import initiate_group_chat, ContextVariables
from autogen.agentchat.group import RevertToUserTarget, FunctionTarget, AgentTarget
from autogen.agentchat.group.patterns.pattern import DefaultPattern

from agents import WIALMasterCoach, StrictEvaluator, observe_turn, ReflectionFacilitator
from core.config import LLMConfig, get_llm_config
from core.nested_chat import create_nested_chat_config
from memory import CognitiveState, SummaryChain, LearnerProfile, SessionManager
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 会话结果
# ============================================================
@dataclass
class TurnResult:
    """单轮对话结果"""
    question: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    context: dict[str, Any] = field(default_factory=dict)


# ============================================================
# Orchestrator
# ============================================================
class Orchestrator:
    """Phase 2 编排器 — 双轨 FSM (Business ↔ Reflection)

    数据流:
        User → Observer(FunctionTarget) → Coach / Reflection → [NestedChat(Evaluator)] → 输出

    Handoff 配置:
        UserProxy.after_work → FunctionTarget(observe_turn) → AgentTarget(Coach | Reflection)
        Coach.OnCondition → NestedChatTarget(Evaluator 审查)
        Coach.after_work → RevertToUserTarget
        Reflection.after_work → RevertToUserTarget (无审查)

    双轨 FSM:
        业务轨: readiness < 0.7 → Coach
                readiness >= 0.7 → 切换到反思轨
        反思轨: readiness < 0.5 / 超 3 轮 / 用户要求 → 切回业务轨
    """

    def __init__(
        self,
        coach_config: LLMConfig | None = None,
        evaluator_config: LLMConfig | None = None,
        observer_config: LLMConfig | None = None,
        reflection_config: LLMConfig | None = None,
        learner_id: str = "default",
    ):
        self._coach_config = coach_config or get_llm_config("coach")
        self._evaluator_config = evaluator_config or get_llm_config("evaluator")

        # Observer / Reflection: 优先显式传入 → 环境变量 → 回退到 coach 配置
        if observer_config is not None:
            self._observer_config = observer_config
        else:
            try:
                self._observer_config = get_llm_config("observer")
            except ValueError:
                self._observer_config = self._coach_config

        if reflection_config is not None:
            self._reflection_config = reflection_config
        else:
            try:
                self._reflection_config = get_llm_config("reflection")
            except ValueError:
                self._reflection_config = self._coach_config
        self._learner_id = learner_id

        # Agent 实例 (延迟到 create_session 初始化)
        self._coach: ConversableAgent | None = None
        self._evaluator: ConversableAgent | None = None
        self._reflection: ConversableAgent | None = None
        self._user_proxy: UserProxyAgent | None = None

        # 业务包装层
        self._coach_wrapper: WIALMasterCoach | None = None
        self._evaluator_wrapper: StrictEvaluator | None = None
        self._reflection_wrapper: ReflectionFacilitator | None = None

        # 记忆系统
        self._session_mgr = SessionManager()
        self._cognitive_state = CognitiveState()
        self._summary_chain = SummaryChain()
        self._learner_profile = LearnerProfile()

        self._ctx = ContextVariables()
        self._session_ready = False

    def create_session(self) -> None:
        """创建 Agent 实例，配置 Handoffs，初始化 ContextVariables"""

        # ---- 创建业务包装 ----
        self._coach_wrapper = WIALMasterCoach(self._coach_config)
        self._evaluator_wrapper = StrictEvaluator(self._evaluator_config)

        self._coach = self._coach_wrapper.get_agent()
        self._evaluator = self._evaluator_wrapper.get_agent()

        # Reflection Agent
        self._reflection_wrapper = ReflectionFacilitator(self._reflection_config)
        self._reflection = self._reflection_wrapper.get_agent()
        self._reflection.handoffs.set_after_work(RevertToUserTarget())

        # ---- Handoff 配置 ----

        # Coach → Evaluator 审查 (nested chat)
        # 方案 2: 手动创建 wrapper agent 并使用 AgentTarget
        nested_target = create_nested_chat_config(
            self._evaluator,
            max_rounds=self._coach_config.max_review_rounds,
        )
        # 手动创建 wrapper agent
        self._nested_wrapper = nested_target.create_wrapper_agent(
            parent_agent=self._coach,
            index=0,
        )
        # 使用 AgentTarget 指向 wrapper agent
        self._coach.handoffs.set_after_work(AgentTarget(self._nested_wrapper))

        # UserProxy
        self._user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            code_execution_config=False,
        )

        # Observer → 双轨路由
        self._user_proxy.handoffs.set_after_work(
            FunctionTarget(
                observe_turn,
                extra_args={
                    "observer_config": self._observer_config,
                    "coach_agent": self._coach,
                    "reflection_agent": self._reflection,
                },
            )
        )

        # ---- 记忆系统初始化 ----

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
        self._session_mgr.init_session(session_id, self._learner_id)

        self._learner_profile = self._session_mgr.load_learner_profile()
        self._learner_profile.learner_id = self._learner_id
        self._cognitive_state = CognitiveState()
        self._summary_chain = SummaryChain()

        # 注入 ContextVariables (含 FSM 状态)
        self._ctx = ContextVariables(data={
            "round": 0,
            "current_track": "business",
            "reflection_turn_count": 0,
            "cognitive_state": self._cognitive_state.to_dict(),
            "summary_chain": self._summary_chain.to_dict(),
            "learner_profile": self._learner_profile.to_dict(),
        })
        self._session_ready = True

        logger.info(
            "Session created: coach=%s, evaluator=%s, reflection=%s",
            self._coach_config.model,
            self._evaluator_config.model,
            self._reflection_config.model,
        )

    def run_turn(self, user_input: str, max_rounds: int = 20) -> TurnResult:
        """执行一轮完整交互"""
        if not self._session_ready:
            self.create_session()

        self._ctx.set("round", self._ctx.get("round", 0) + 1)

        # agents 列表包含所有可能的 agent (包括 nested chat wrapper)
        agents = [self._coach, self._nested_wrapper]
        if self._reflection:
            agents.append(self._reflection)

        pattern = DefaultPattern(
            initial_agent=self._coach,
            agents=agents,
            user_agent=self._user_proxy,
            context_variables=self._ctx,
            group_after_work=RevertToUserTarget(),
        )

        chat_result, updated_ctx, last_speaker = initiate_group_chat(
            pattern=pattern,
            messages=user_input,
            max_rounds=max_rounds,
        )

        self._ctx = updated_ctx

        summary = chat_result.summary or ""
        messages = chat_result.chat_history or []
        ctx_dict = updated_ctx.to_dict() if updated_ctx else {}

        # ---- 同步 Observer 更新的认知状态 ----
        observer_state = ctx_dict.get("cognitive_state")
        if observer_state and isinstance(observer_state, dict):
            self._cognitive_state = CognitiveState.from_dict(observer_state)

        # ---- 持久化记忆 ----
        self._session_mgr.save_cognitive_state(self._cognitive_state)
        self._session_mgr.save_summary_chain(self._summary_chain)
        self._session_mgr.save_learner_profile(self._learner_profile)

        # Raw Log
        agent_output = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                agent_output = msg.get("content", "")
                break
        self._session_mgr.append_raw_log({
            "turn": ctx_dict.get("round", 0),
            "track": ctx_dict.get("current_track", "business"),
            "user_input": user_input,
            "agent_output": agent_output,
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
        })

        # 同步记忆到 ContextVariables
        self._ctx.set("cognitive_state", self._cognitive_state.to_dict())
        self._ctx.set("summary_chain", self._summary_chain.to_dict())
        self._ctx.set("learner_profile", self._learner_profile.to_dict())

        logger.info(
            "Turn complete: round=%d, track=%s, messages=%d, last_speaker=%s",
            ctx_dict.get("round", 0),
            ctx_dict.get("current_track", "business"),
            len(messages),
            last_speaker.name if last_speaker else "None",
        )

        return TurnResult(
            question=summary,
            messages=messages,
            summary=summary,
            context=ctx_dict,
        )

    @property
    def coach(self) -> WIALMasterCoach | None:
        return self._coach_wrapper

    @property
    def evaluator(self) -> StrictEvaluator | None:
        return self._evaluator_wrapper

    @property
    def reflection(self) -> ReflectionFacilitator | None:
        return self._reflection_wrapper
