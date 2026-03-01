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
    - 接收用户的业务问题输入
    - 使用隐式 ReAct 模式生成开放式提问
    - 输出 JSON 格式: {question, reasoning}
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
    def _parse_response(raw: Any) -> Dict[str, Any]:
        """统一解析 LLM 返回。"""
        if raw is None:
            return {"question": "", "reasoning": "LLM 未返回响应"}
        if isinstance(raw, dict):
            return raw

        response = str(raw)

        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

        return {
            "question": response,
            "reasoning": "LLM 未返回标准 JSON 格式",
        }

    def _generate_with_prompt(self, prompt: str) -> Dict[str, Any]:
        """统一的生成入口。"""
        raw = self._agent.generate_reply(
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_response(raw)

    def generate_question(self, user_input: str) -> Dict[str, Any]:
        """
        生成开放式提问

        Args:
            user_input: 用户的业务问题描述

        Returns:
            包含 question 和 reasoning 的字典
        """
        prompt = self._normalize_user_input(user_input)
        return self._generate_with_prompt(prompt)

    def rewrite_question(
        self,
        user_input: str,
        previous_question: str,
        review_feedback: Dict[str, Any] | str,
        round_number: int,
    ) -> Dict[str, Any]:
        """
        基于评审反馈重写问题。

        Args:
            user_input: 原始用户问题
            previous_question: 上一版问题
            review_feedback: Evaluator 返回的反馈
            round_number: 当前重写轮次 (从 2 开始)

        Returns:
            包含 question 和 reasoning 的字典
        """
        if isinstance(review_feedback, dict):
            feedback_text = str(review_feedback.get("feedback", "")).strip()
            score = review_feedback.get("score")
        else:
            feedback_text = str(review_feedback or "").strip()
            score = None

        prompt_parts = [
            self._normalize_user_input(user_input),
            f"这是第 {round_number} 轮优化。",
            f"上一版问题: {previous_question or '（上一版为空）'}",
        ]

        if score is not None:
            prompt_parts.append(f"上一轮评分: {score}/100")
        if feedback_text:
            prompt_parts.append(f"评审反馈: {feedback_text}")

        prompt_parts.append(
            "请严格根据以上反馈，重写一个更符合 WIAL 标准的开放式问题。"
            "必须避免重复上一版问题，优先修正开放性、无诱导性和反思深度方面的缺陷。"
            "继续严格输出 JSON 格式。"
        )

        return self._generate_with_prompt("\n\n".join(prompt_parts))

    def get_agent(self) -> ConversableAgent:
        """
        获取底层 AutoGen Agent 实例

        Returns:
            ConversableAgent 实例
        """
        return self._agent
