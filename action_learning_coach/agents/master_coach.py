"""
[INPUT]: 依赖 autogen 的 ConversableAgent，依赖 prompts/coach_prompt 的 COACH_SYSTEM_MESSAGE，依赖 core/config 的 LLMConfig
[OUTPUT]: 对外提供 WIALMasterCoach 类，generate_question 方法，get_agent 方法
[POS]: agents 模块的核心组件，负责生成开放式提问，使用隐式 ReAct 模式
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from typing import Dict, Any

try:
    from autogen import ConversableAgent
except ImportError:
    class ConversableAgent:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("pyautogen is required for real agent mode")

try:
    from ..prompts.coach_prompt import COACH_SYSTEM_MESSAGE
    from ..core.config import LLMConfig
except ImportError:
    from prompts.coach_prompt import COACH_SYSTEM_MESSAGE
    from core.config import LLMConfig


# ============================================================
# WIAL Master Coach Agent
# ============================================================
class WIALMasterCoach:
    """
    WIAL Master Coach Agent

    职责:
    - 接收用户输入和对话线程上下文
    - 生成一条 AI 催化师回复: 简短共情 + 两个开放式问题
    - 输出 JSON 格式: {acknowledgment, questions, reasoning}
    """

    def __init__(self, llm_config: LLMConfig):
        """
        初始化 WIAL Master Coach

        Args:
            llm_config: LLM 配置对象
        """
        self.llm_config = llm_config
        self._agent = ConversableAgent(
            name="WIAL_Master_Coach",
            system_message=COACH_SYSTEM_MESSAGE,
            llm_config=llm_config.to_autogen_config(),
            human_input_mode="NEVER",
        )

    @staticmethod
    def _normalize_user_input(user_input: str) -> str:
        """避免向 Anthropic 发送空 user content。"""
        text = str(user_input or "").strip()
        if text:
            return text
        return "用户暂未提供具体业务背景。请先生成一个开放式澄清问题，帮助用户补充关键信息。"

    @staticmethod
    def _default_acknowledgment() -> str:
        """生成默认的简短共情。"""
        return "我听到这件事正在给你带来不小的压力。"

    @staticmethod
    def _default_questions() -> list[str]:
        """在 LLM 返回异常时使用的兜底问题。"""
        return [
            "在你看来，这个情境里最值得先看清的是什么？",
            "如果从另一个角度重新看这件事，你会先想到什么？",
        ]

    @staticmethod
    def _ensure_question_shape(text: str, fallback: str) -> str:
        """确保问题非空且以问句形式结尾。"""
        normalized = str(text or "").strip()
        if not normalized:
            normalized = fallback
        if "?" not in normalized and "？" not in normalized:
            normalized = normalized.rstrip("。.!！") + "？"
        return normalized

    @classmethod
    def _normalize_reply_payload(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """统一 Coach 输出结构，兼容旧 question 字段。"""
        raw_questions = payload.get("questions")
        questions: list[str] = []

        if isinstance(raw_questions, list):
            for item in raw_questions:
                text = str(item or "").strip()
                if text:
                    questions.append(text)

        if not questions:
            legacy_question = str(payload.get("question", "") or "").strip()
            if legacy_question:
                questions.append(legacy_question)

        fallback_questions = cls._default_questions()
        while len(questions) < 2:
            questions.append(fallback_questions[len(questions)])

        questions = [
            cls._ensure_question_shape(questions[0], fallback_questions[0]),
            cls._ensure_question_shape(questions[1], fallback_questions[1]),
        ]

        acknowledgment = str(payload.get("acknowledgment", "") or "").strip()
        if not acknowledgment:
            acknowledgment = cls._default_acknowledgment()

        reasoning = str(payload.get("reasoning", "") or "").strip()

        return {
            "acknowledgment": acknowledgment,
            "questions": questions,
            "question": questions[0],
            "reasoning": reasoning,
        }

    @classmethod
    def _parse_response(cls, raw: Any) -> Dict[str, Any]:
        """统一解析 LLM 返回。"""
        if raw is None:
            return cls._normalize_reply_payload({"reasoning": "LLM 未返回响应"})
        if isinstance(raw, dict):
            return cls._normalize_reply_payload(raw)

        response = str(raw)

        try:
            result = json.loads(response)
            if isinstance(result, dict):
                return cls._normalize_reply_payload(result)
        except json.JSONDecodeError:
            pass

        import re

        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    return cls._normalize_reply_payload(result)
            except json.JSONDecodeError:
                pass

        return cls._normalize_reply_payload({
            "question": response,
            "reasoning": "LLM 未返回标准 JSON 格式",
        })

    @staticmethod
    def _build_thread_context_text(thread_context: Dict[str, Any] | None) -> str:
        """把当前对话线程上下文压缩成提示词片段。"""
        if not thread_context:
            return ""

        parts: list[str] = []

        original_problem = str(thread_context.get("original_problem", "") or "").strip()
        if original_problem:
            parts.append(f"当前持续对话的原始问题: {original_problem}")

        last_reply = thread_context.get("last_coach_reply")
        if isinstance(last_reply, dict):
            ack = str(last_reply.get("acknowledgment", "") or "").strip()
            questions = last_reply.get("questions", [])
            if ack:
                parts.append(f"你上一轮的简短共情: {ack}")
            if isinstance(questions, list):
                for idx, question in enumerate(questions[:2], 1):
                    text = str(question or "").strip()
                    if text:
                        parts.append(f"你上一轮的问题{idx}: {text}")

        recent_turns = thread_context.get("recent_turns", [])
        if isinstance(recent_turns, list) and recent_turns:
            parts.append("最近对话摘录:")
            for turn in recent_turns[-3:]:
                if not isinstance(turn, dict):
                    continue
                user_text = str(turn.get("user_input", "") or "").strip()
                if user_text:
                    parts.append(f"- 用户: {user_text}")

        open_threads = thread_context.get("open_threads", [])
        if isinstance(open_threads, list) and open_threads:
            open_items = [str(item or "").strip() for item in open_threads if str(item or "").strip()]
            if open_items:
                parts.append("当前尚未展开完的线索:")
                for item in open_items[:2]:
                    parts.append(f"- {item}")

        if not parts:
            return ""

        parts.append("请把用户最新输入优先视为对当前线程的继续回应，而不是全新开题。")
        return "\n".join(parts)

    def _build_generation_prompt(
        self,
        user_input: str,
        thread_context: Dict[str, Any] | None = None,
    ) -> str:
        """组合本轮生成提示。"""
        prompt_parts = []
        context_text = self._build_thread_context_text(thread_context)
        if context_text:
            prompt_parts.append(context_text)
        prompt_parts.append(f"用户最新输入: {self._normalize_user_input(user_input)}")
        prompt_parts.append(
            "请输出一条完整的 AI 催化师回复: 先给一句简短共情，再给两个不同维度的开放式问题。"
            "绝对不要给建议、答案或行动步骤。"
            "必须严格输出 JSON。"
        )
        return "\n\n".join(prompt_parts)

    def _generate_with_prompt(self, prompt: str) -> Dict[str, Any]:
        """统一的生成入口。"""
        raw = self._agent.generate_reply(
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_response(raw)

    def generate_coach_reply(
        self,
        user_input: str,
        thread_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """生成完整的 AI 催化师回复。"""
        prompt = self._build_generation_prompt(user_input, thread_context=thread_context)
        return self._generate_with_prompt(prompt)

    def generate_question(
        self,
        user_input: str,
        thread_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        生成 AI 催化师回复。

        Args:
            user_input: 用户的业务问题描述

        Returns:
            包含 acknowledgment / questions / question / reasoning 的字典
        """
        return self.generate_coach_reply(user_input, thread_context=thread_context)

    @staticmethod
    def _build_previous_reply_text(previous_reply: Dict[str, Any] | None, previous_question: str) -> str:
        """把上一版回复压缩成可读文本。"""
        if isinstance(previous_reply, dict):
            acknowledgment = str(previous_reply.get("acknowledgment", "") or "").strip()
            questions = previous_reply.get("questions", [])
            lines = []
            if acknowledgment:
                lines.append(f"上一版共情: {acknowledgment}")
            if isinstance(questions, list):
                for idx, question in enumerate(questions[:2], 1):
                    text = str(question or "").strip()
                    if text:
                        lines.append(f"上一版问题{idx}: {text}")
            if lines:
                return "\n".join(lines)

        question_text = str(previous_question or "").strip() or "（上一版为空）"
        return f"上一版问题1: {question_text}"

    def rewrite_coach_reply(
        self,
        user_input: str,
        previous_reply: Dict[str, Any] | None,
        review_feedback: Dict[str, Any] | str,
        round_number: int,
        thread_context: Dict[str, Any] | None = None,
        previous_question: str = "",
    ) -> Dict[str, Any]:
        """基于评审反馈重写整条 AI 催化师回复。"""
        if isinstance(review_feedback, dict):
            feedback_text = str(review_feedback.get("feedback", "")).strip()
            score = review_feedback.get("score")
        else:
            feedback_text = str(review_feedback or "").strip()
            score = None

        prompt_parts = []
        context_text = self._build_thread_context_text(thread_context)
        if context_text:
            prompt_parts.append(context_text)

        prompt_parts.extend([
            f"用户最新输入: {self._normalize_user_input(user_input)}",
            f"这是第 {round_number} 轮优化。",
            self._build_previous_reply_text(previous_reply, previous_question),
        ])

        if score is not None:
            prompt_parts.append(f"上一轮评分: {score}/100")
        if feedback_text:
            prompt_parts.append(f"评审反馈: {feedback_text}")

        prompt_parts.append(
            "请严格根据以上反馈，重写整条 AI 催化师回复。"
            "必须保留“简短共情 + 两个不同维度的开放式问题”的结构。"
            "绝对不要给建议、答案或行动步骤。"
            "继续严格输出 JSON。"
        )

        return self._generate_with_prompt("\n\n".join(prompt_parts))

    def rewrite_question(
        self,
        user_input: str,
        previous_question: str,
        review_feedback: Dict[str, Any] | str,
        round_number: int,
        thread_context: Dict[str, Any] | None = None,
        previous_reply: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        基于评审反馈重写回复。

        Args:
            user_input: 原始用户问题
            previous_question: 上一版主问题（兼容旧接口）
            review_feedback: Evaluator 返回的反馈
            round_number: 当前重写轮次 (从 2 开始)

        Returns:
            包含 acknowledgment / questions / question / reasoning 的字典
        """
        return self.rewrite_coach_reply(
            user_input=user_input,
            previous_reply=previous_reply,
            review_feedback=review_feedback,
            round_number=round_number,
            thread_context=thread_context,
            previous_question=previous_question,
        )

    def get_agent(self) -> ConversableAgent:
        """
        获取底层 AutoGen Agent 实例

        Returns:
            ConversableAgent 实例
        """
        return self._agent
