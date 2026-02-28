"""
[INPUT]: 依赖 autogen 的 ConversableAgent，依赖 prompts/evaluator_prompt 的 EVALUATOR_SYSTEM_MESSAGE，依赖 core/config 的 LLMConfig
[OUTPUT]: 对外提供 StrictEvaluator 类，evaluate 方法，get_agent 方法
[POS]: agents 模块的审查组件，负责质量把关，三维评分体系
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from typing import Dict, Any
from autogen import ConversableAgent
from prompts.evaluator_prompt import EVALUATOR_SYSTEM_MESSAGE
from core.config import LLMConfig


# ============================================================
# Strict Evaluator Agent
# ============================================================
class StrictEvaluator:
    """
    Strict Evaluator Agent

    职责:
    - 评估 Coach 生成的问题质量
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

    def evaluate(self, question: str) -> Dict[str, Any]:
        """
        评估问题质量

        Args:
            question: 待评估的问题

        Returns:
            评估结果字典: {score, breakdown, pass, feedback}
        """
        # 调用 LLM 进行评估
        raw = self._agent.generate_reply(
            messages=[{"role": "user", "content": f"请评估以下问题:\n\n{question}"}]
        )

        # 统一为字符串 (AG2 可能返回 str / dict / None)
        if raw is None:
            return {
                "score": 0, "breakdown": {"openness": 0, "neutrality": 0, "depth": 0},
                "pass": False, "feedback": "LLM 未返回响应",
            }
        if isinstance(raw, dict):
            raw["pass"] = raw.get("score", 0) >= self.pass_threshold
            return raw
        response = str(raw)

        # 解析 JSON 响应 - 处理 markdown 代码块包裹的情况
        try:
            result = json.loads(response)
            result["pass"] = result.get("score", 0) >= self.pass_threshold
            return result
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                    result["pass"] = result.get("score", 0) >= self.pass_threshold
                    return result
                except json.JSONDecodeError:
                    pass
            return {
                "score": 0,
                "breakdown": {"openness": 0, "neutrality": 0, "depth": 0},
                "pass": False,
                "feedback": f"评估失败: LLM 未返回标准 JSON 格式。原始响应: {response[:200]}...",
            }

    def get_agent(self) -> ConversableAgent:
        """
        获取底层 AutoGen Agent 实例

        Returns:
            ConversableAgent 实例
        """
        return self._agent
