"""
[INPUT]: 依赖 agents/master_coach 的 WIALMasterCoach，依赖 agents/evaluator 的 StrictEvaluator，依赖 core/config 的 LLMConfig
[OUTPUT]: 对外提供 setup_nested_chat 函数，返回配置好的 Nested Chat 审查流程
[POS]: core 模块的编排逻辑，实现 Actor-Critic 模式，最多 5 轮审查循环
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Dict, Any, List
from ..agents.master_coach import WIALMasterCoach
from ..agents.evaluator import StrictEvaluator
from ..core.config import LLMConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Nested Chat Setup
# ============================================================
def setup_nested_chat(
    coach: WIALMasterCoach,
    evaluator: StrictEvaluator,
    max_rounds: int = 5,
) -> List[Dict[str, Any]]:
    """
    配置 Nested Chat 审查流程

    Args:
        coach: WIAL Master Coach 实例
        evaluator: Strict Evaluator 实例
        max_rounds: 最大审查轮次

    Returns:
        Nested Chat 配置列表
    """
    nested_chat_config = [
        {
            "recipient": evaluator.get_agent(),
            "message": lambda sender_msg: _extract_question(sender_msg),
            "summary_method": "last_msg",
            "max_turns": max_rounds * 2,  # Coach + Evaluator 各一轮
        }
    ]

    logger.info(f"Nested Chat 配置完成: max_rounds={max_rounds}")
    return nested_chat_config


# ============================================================
# Helper Functions
# ============================================================
def _extract_question(sender_msg: Dict[str, Any]) -> str:
    """
    从 Coach 的消息中提取问题

    Args:
        sender_msg: Coach 发送的消息

    Returns:
        提取的问题文本
    """
    import json

    content = sender_msg.get("content", "")

    # 尝试解析 JSON 格式
    try:
        data = json.loads(content)
        return data.get("question", content)
    except json.JSONDecodeError:
        # 如果不是 JSON，直接返回原文
        return content