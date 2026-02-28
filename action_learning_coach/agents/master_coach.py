"""
[INPUT]: 依赖 autogen 的 ConversableAgent，依赖 prompts/coach_prompt 的 COACH_SYSTEM_MESSAGE，依赖 core/config 的 LLMConfig
[OUTPUT]: 对外提供 WIALMasterCoach 类，generate_question 方法，get_agent 方法
[POS]: agents 模块的核心组件，负责生成开放式提问，使用隐式 ReAct 模式
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from typing import Dict, Any
from autogen import ConversableAgent
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

    def generate_question(self, user_input: str) -> Dict[str, Any]:
        """
        生成开放式提问

        Args:
            user_input: 用户的业务问题描述

        Returns:
            包含 question 和 reasoning 的字典
        """
        # 调用 LLM 生成问题
        raw = self._agent.generate_reply(
            messages=[{"role": "user", "content": user_input}]
        )

        # 统一为字符串 (AG2 可能返回 str / dict / None)
        if raw is None:
            return {"question": "", "reasoning": "LLM 未返回响应"}
        if isinstance(raw, dict):
            return raw
        response = str(raw)

        # 解析 JSON 响应 - 处理 markdown 代码块包裹的情况
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

    def get_agent(self) -> ConversableAgent:
        """
        获取底层 AutoGen Agent 实例

        Returns:
            ConversableAgent 实例
        """
        return self._agent
