"""
[INPUT]: 依赖 autogen (ConversableAgent, UserProxyAgent),
         依赖 autogen.agentchat (ContextVariables),
         依赖 autogen.agentchat.group (RevertToUserTarget, FunctionTarget),
         依赖 agents (WIALMasterCoach, StrictEvaluator, observe_turn, ReflectionFacilitator),
         依赖 core/config (LLMConfig, get_llm_config),
         依赖 memory (CognitiveState, SummaryChain, LearnerProfile, SessionManager)
[OUTPUT]: 对外提供 Orchestrator 类，create_session / run_turn 方法，TurnResult
[POS]: core 模块的中枢编排器。当前业务主路径使用显式的 Coach→Evaluator 多轮审查闭环，
       不再依赖 NestedChat / llm_condition；Observer / Reflection 相关配置仅作兼容保留。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import re
from typing import Any
from uuid import uuid4

from autogen import ConversableAgent, UserProxyAgent
from autogen.agentchat import ContextVariables
from autogen.agentchat.group import (
    RevertToUserTarget,
    FunctionTarget,
)

try:
    from ..agents import WIALMasterCoach, StrictEvaluator, observe_turn, ReflectionFacilitator
    from .config import LLMConfig, get_llm_config
    from ..memory import CognitiveState, SummaryChain, LearnerProfile, SessionManager
    from ..utils.logger import get_logger
except ImportError:
    from agents import WIALMasterCoach, StrictEvaluator, observe_turn, ReflectionFacilitator
    from core.config import LLMConfig, get_llm_config
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


@dataclass
class ReviewLoopResult:
    """显式审查闭环结果。"""
    question: str
    review_result: dict[str, Any] | None = None
    last_review_result: dict[str, Any] | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    review_rounds: int = 0
    passed: bool = False
    best_score: int = 0
    returned_best_version: bool = False


# ============================================================
# Orchestrator
# ============================================================
class Orchestrator:
    """Phase 2 编排器 — 显式审查闭环 + 兼容的 Observer/FSM 配置

    数据流:
        User Input → Explicit Review Loop(Coach ↔ Evaluator, max 5) → 输出

    Handoff 配置:
        UserProxy.after_work → FunctionTarget(observe_turn) → AgentTarget(Coach | Reflection)
        Coach.after_work → RevertToUserTarget
        Reflection.after_work → RevertToUserTarget (无审查)

    说明:
        真实业务主路径已不再使用 AG2 的 llm_condition / NestedChatTarget。
        Observer / Reflection 相关配置仍保留在 session 中，便于后续恢复多轨编排；
        但当前 run_turn 的核心审查逻辑由显式闭环主导。
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
        self._coach.handoffs.set_after_work(RevertToUserTarget())

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

    @staticmethod
    def _serialize_message(payload: dict[str, Any]) -> str:
        """统一消息序列化，便于测试和日志稳定。"""
        return json.dumps(payload, ensure_ascii=False)

    def _coerce_coach_payload(self, raw: Any) -> dict[str, Any]:
        """统一 Coach 输出结构。"""
        if isinstance(raw, dict):
            payload = dict(raw)
        else:
            payload = {"question": str(raw or ""), "reasoning": "Coach 返回了非结构化结果"}

        question = str(payload.get("question", "") or "").strip()
        payload["question"] = question
        payload.setdefault("reasoning", "")
        return payload

    def _coerce_review_payload(self, raw: Any) -> dict[str, Any]:
        """统一 Evaluator 输出结构。"""
        if isinstance(raw, dict):
            payload = dict(raw)
        else:
            parsed = self._load_json_payload(str(raw or ""))
            if isinstance(parsed, dict):
                payload = parsed
            else:
                payload = {
                    "score": 0,
                    "breakdown": {"openness": 0, "neutrality": 0, "depth": 0},
                    "pass": False,
                    "feedback": "Evaluator 返回了非结构化结果",
                }

        score = payload.get("score", 0)
        try:
            score = int(score)
        except (TypeError, ValueError):
            score = 0
        payload["score"] = score
        payload["pass"] = bool(payload.get("pass", score >= self._evaluator_config.pass_score_threshold))
        payload.setdefault("breakdown", {"openness": 0, "neutrality": 0, "depth": 0})
        payload.setdefault("feedback", "")
        return payload

    def _run_review_loop(self, user_input: str, max_rounds: int | None = None) -> ReviewLoopResult:
        """显式执行 Coach -> Evaluator -> Coach 的最多 5 轮闭环。"""
        if self._coach_wrapper is None or self._evaluator_wrapper is None:
            raise RuntimeError("Session not ready")

        configured_max_rounds = max(1, self._coach_config.max_review_rounds)
        if max_rounds is None:
            max_rounds = configured_max_rounds
        else:
            max_rounds = max(1, min(max_rounds, configured_max_rounds))
        messages = [{"role": "user", "name": "User", "content": user_input}]

        best_question = ""
        best_review_result: dict[str, Any] | None = None
        best_score = -1
        last_question = ""
        last_review_result: dict[str, Any] | None = None

        for review_round in range(1, max_rounds + 1):
            if review_round == 1:
                coach_raw = self._coach_wrapper.generate_question(user_input)
            else:
                coach_raw = self._coach_wrapper.rewrite_question(
                    user_input=user_input,
                    previous_question=last_question,
                    review_feedback=last_review_result or {},
                    round_number=review_round,
                )

            coach_payload = self._coerce_coach_payload(coach_raw)
            question = coach_payload.get("question", "")
            messages.append({
                "role": "assistant",
                "name": self._coach.name if self._coach else "WIAL_Master_Coach",
                "content": self._serialize_message(coach_payload),
            })

            review_raw = self._evaluator_wrapper.evaluate(question)
            review_payload = self._coerce_review_payload(review_raw)
            messages.append({
                "role": "assistant",
                "name": self._evaluator.name if self._evaluator else "Strict_Evaluator",
                "content": self._serialize_message(review_payload),
            })

            score = review_payload["score"]
            if question and score >= best_score:
                best_score = score
                best_question = question
                best_review_result = review_payload

            last_question = question or last_question
            last_review_result = review_payload

            if review_payload["pass"]:
                return ReviewLoopResult(
                    question=question,
                    review_result=review_payload,
                    last_review_result=review_payload,
                    messages=messages,
                    review_rounds=review_round,
                    passed=True,
                    best_score=max(score, 0),
                )

        selected_question = best_question or last_question
        selected_review_result = best_review_result or last_review_result
        returned_best_version = (
            bool(selected_question)
            and bool(last_question)
            and selected_question != last_question
        )

        return ReviewLoopResult(
            question=selected_question,
            review_result=selected_review_result,
            last_review_result=last_review_result,
            messages=messages,
            review_rounds=max_rounds,
            passed=False,
            best_score=max(best_score, 0),
            returned_best_version=returned_best_version,
        )

    @staticmethod
    def _load_json_payload(text: str) -> dict[str, Any] | list[Any] | None:
        """兼容裸 JSON 和 markdown code fence 的解析。"""
        if not text:
            return None

        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", str(text), re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def run_turn(self, user_input: str, max_rounds: int = 20) -> TurnResult:
        """执行一轮完整交互"""
        if not self._session_ready:
            self.create_session()

        self._ctx.set("round", self._ctx.get("round", 0) + 1)

        review_loop = self._run_review_loop(user_input, max_rounds=max_rounds)
        question = review_loop.question
        summary = question
        messages = review_loop.messages
        ctx_dict = self._ctx.to_dict()
        ctx_dict["review_rounds"] = review_loop.review_rounds
        ctx_dict["review_passed"] = review_loop.passed
        ctx_dict["best_score"] = review_loop.best_score
        if review_loop.returned_best_version:
            ctx_dict["returned_best_version"] = True
        if review_loop.review_result is not None:
            ctx_dict["review_result"] = review_loop.review_result
        if review_loop.last_review_result is not None:
            ctx_dict["last_review_result"] = review_loop.last_review_result

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
            content = msg.get("content", "")
            if msg.get("role") == "assistant" and content:
                agent_output = msg.get("content", "")
                break
        if not agent_output:
            agent_output = question or summary
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
            messages[-1].get("name", "None") if messages else "None",
        )

        return TurnResult(
            question=question or summary,
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
