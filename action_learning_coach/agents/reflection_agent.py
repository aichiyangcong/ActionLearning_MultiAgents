"""
[INPUT]: 依赖 autogen (ConversableAgent, UpdateSystemMessage),
         依赖 prompts/reflection_prompt (REFLECTION_TEMPLATE),
         依赖 core/config (LLMConfig)
[OUTPUT]: 对外提供 ReflectionFacilitator 类，get_agent 方法
[POS]: agents 模块的反思组件，元认知引导，通过 UpdateSystemMessage 动态注入认知状态
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Any

from autogen import ConversableAgent
from autogen.agentchat.conversable_agent import UpdateSystemMessage

from core.config import LLMConfig
from prompts.reflection_prompt import REFLECTION_TEMPLATE
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Reflection Facilitator Agent
# ============================================================
class ReflectionFacilitator:
    """元认知反思引导 Agent

    职责:
    - 帮助学员暂停业务讨论，进入元认知反思
    - 基于 L1 认知状态 (盲点、假设) 设计反思问题
    - 三层反思: 模式识别 → 假设挑战 → 视角转换

    与 Coach 的区别:
    - Coach 针对业务问题提问，经 Evaluator 审查
    - Reflection 针对思维模式提问，无审查直接回到用户
    """

    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config

        # 使用 UpdateSystemMessage 动态注入认知状态
        # AG2 字符串模板模式: 从 context_variables 替换 {var_name}
        updater = UpdateSystemMessage(content_updater=self._build_system_message)

        self._agent = ConversableAgent(
            name="Reflection_Facilitator",
            system_message=REFLECTION_TEMPLATE,
            llm_config=llm_config.to_autogen_config(),
            human_input_mode="NEVER",
            update_agent_state_before_reply=[updater],
        )

    def get_agent(self) -> ConversableAgent:
        return self._agent

    @staticmethod
    def _build_system_message(
        agent: ConversableAgent,
        messages: list[dict[str, Any]],
    ) -> str:
        """从 context_variables 提取认知状态，注入到 REFLECTION_TEMPLATE"""
        ctx = agent.context_variables.to_dict() if agent.context_variables else {}
        cognitive = ctx.get("cognitive_state", {})

        return REFLECTION_TEMPLATE.format(
            current_topic=cognitive.get("current_topic", "未知"),
            thinking_depth=cognitive.get("thinking_depth", "surface"),
            emotional_tone=cognitive.get("emotional_tone", "neutral"),
            key_assumptions=cognitive.get("key_assumptions", []),
            blind_spots=cognitive.get("blind_spots", []),
        )
