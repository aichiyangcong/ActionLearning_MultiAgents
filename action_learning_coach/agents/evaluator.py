"""
[INPUT]: 依赖 autogen 的 ConversableAgent，依赖 prompts/evaluator_prompt 的 EVALUATOR_SYSTEM_MESSAGE，依赖 core/config 的 LLMConfig
[OUTPUT]: 对外提供 StrictEvaluator 类，evaluate 方法，get_agent 方法
[POS]: agents 模块的审查组件，负责质量把关，三维评分体系
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
    from ..prompts.evaluator_prompt import EVALUATOR_SYSTEM_MESSAGE
    from ..core.config import LLMConfig
except ImportError:
    from prompts.evaluator_prompt import EVALUATOR_SYSTEM_MESSAGE
    from core.config import LLMConfig


# ============================================================
# Strict Evaluator Agent
# ============================================================
class StrictEvaluator:
    """
    Strict Evaluator Agent

    职责:
    - 评估 AI 催化师整条回复的质量
    - 三维评分: 开放性(40) + 无诱导性(40) + 反思深度(20)
    - 评分 ≥95 通过，<95 打回并给出修改建议
    """

    def __init__(self, llm_config: LLMConfig):
        """
        初始化 Strict Evaluator

        Args:
            llm_config: LLM 配置对象
        """
        self.llm_config = llm_config
        self.pass_threshold = llm_config.pass_score_threshold
        self._agent = ConversableAgent(
            name="Strict_Evaluator",
            system_message=EVALUATOR_SYSTEM_MESSAGE,
            llm_config=llm_config.to_autogen_config(),
            human_input_mode="NEVER",
        )

    @staticmethod
    def _empty_result(feedback: str) -> Dict[str, Any]:
        """统一空结果结构。"""
        return {
            "score": 0,
            "breakdown": {"openness": 0, "neutrality": 0, "depth": 0},
            "pass": False,
            "feedback": feedback,
        }

    @staticmethod
    def _normalize_coach_reply(coach_reply: Dict[str, Any] | str) -> Dict[str, Any]:
        """兼容旧 question 字段和新催化师回复结构。"""
        if isinstance(coach_reply, dict):
            acknowledgment = str(coach_reply.get("acknowledgment", "") or "").strip()
            raw_questions = coach_reply.get("questions", [])
            questions = []
            if isinstance(raw_questions, list):
                for item in raw_questions:
                    text = str(item or "").strip()
                    if text:
                        questions.append(text)
            if not questions:
                legacy_question = str(coach_reply.get("question", "") or "").strip()
                if legacy_question:
                    questions.append(legacy_question)
            return {
                "acknowledgment": acknowledgment,
                "questions": questions,
            }

        question = str(coach_reply or "").strip()
        return {
            "acknowledgment": "",
            "questions": [question] if question else [],
        }

    @staticmethod
    def _format_review_input(coach_reply: Dict[str, Any] | str) -> str:
        """把 Coach 回复转换成明确的评审输入。"""
        payload = StrictEvaluator._normalize_coach_reply(coach_reply)
        acknowledgment = payload["acknowledgment"]
        questions = payload["questions"]

        lines = ["请评估以下 AI 催化师回复:"]
        lines.append("")
        lines.append(f"简短共情: {acknowledgment or '（缺失）'}")

        if questions:
            for idx, question in enumerate(questions, 1):
                lines.append(f"问题{idx}: {question}")
        else:
            lines.append("问题: （缺失）")

        return "\n".join(lines)

    def _parse_result(self, raw: Any) -> Dict[str, Any]:
        """统一解析 Evaluator 的 LLM 输出。"""
        if raw is None:
            return self._empty_result("LLM 未返回响应")
        if isinstance(raw, dict):
            raw["pass"] = raw.get("score", 0) >= self.pass_threshold
            return raw

        response = str(raw)

        try:
            result = json.loads(response)
            if isinstance(result, dict):
                result["pass"] = result.get("score", 0) >= self.pass_threshold
                return result
        except json.JSONDecodeError:
            pass

        import re

        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                if isinstance(result, dict):
                    result["pass"] = result.get("score", 0) >= self.pass_threshold
                    return result
            except json.JSONDecodeError:
                pass

        return self._empty_result(
            f"评估失败: LLM 未返回标准 JSON 格式。原始响应: {response[:200]}..."
        )

    def evaluate(self, coach_reply: Dict[str, Any] | str) -> Dict[str, Any]:
        """
        评估 AI 催化师回复质量

        Args:
            coach_reply: 待评估的催化师回复

        Returns:
            评估结果字典: {score, breakdown, pass, feedback}
        """
        # 调用 LLM 进行评估
        raw = self._agent.generate_reply(
            messages=[{"role": "user", "content": self._format_review_input(coach_reply)}]
        )
        return self._parse_result(raw)

    def get_agent(self) -> ConversableAgent:
        """
        获取底层 AutoGen Agent 实例

        Returns:
            ConversableAgent 实例
        """
        return self._agent
