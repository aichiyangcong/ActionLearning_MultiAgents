"""
[INPUT]: 依赖 autogen.ConversableAgent (AG2 0.11.2)，
         依赖 autogen.agentchat.group.targets.transition_target.NestedChatTarget
[OUTPUT]: 对外提供 create_nested_chat_config(evaluator_agent, max_rounds) 函数，
          返回 NestedChatTarget 实例，可直接用于 OnCondition/OnContextCondition
[POS]: core 模块的 Nested Chat 编排器，实现 Actor-Critic 审查循环，
       Coach 问题经 Evaluator 评分，< 95 分打回重写，最多 max_rounds 轮
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Any

from autogen import ConversableAgent
from autogen.agentchat.group.targets.transition_target import NestedChatTarget

from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 消息提取 (从 GroupChat carryover 中提取)
# ============================================================
def _extract_question_from_carryover(
    recipient: ConversableAgent,
    messages: list[dict[str, Any]],
    summary_args: dict[str, Any],
) -> str:
    """从 carryover messages 中提取 Coach 的问题

    carryover_config 的 summary_method Callable 签名:
        (recipient, messages, summary_args) -> str

    messages 是 GroupChat 的完整历史（已 trim 最后 2 条 transition 消息）
    从后往前找 Coach 的最后一条消息，提取其中的 question 字段。
    """
    import json

    logger.info(f"Carryover messages count: {len(messages)}")
    for i, msg in enumerate(messages[-5:]):  # 只打印最后 5 条
        logger.info(f"Message {i}: role={msg.get('role')}, name={msg.get('name')}, content={msg.get('content', '')[:100]}")

    # 从后往前找 Coach 的最后一条消息
    for msg in reversed(messages):
        if msg.get("name") == "WIAL_Master_Coach" and msg.get("role") == "assistant":
            content = msg.get("content", "")

            # 尝试 JSON 解析
            try:
                data = json.loads(content)
                question = data.get("question", content)
            except (json.JSONDecodeError, TypeError):
                question = content

            logger.info(f"Extracted question: {question}")
            return f"请评估以下问题:\n\n{question}"

    # Fallback: 使用最后一条消息
    last_content = messages[-1].get("content", "") if messages else ""
    logger.warning(f"No Coach message found, using last message: {last_content[:100]}")
    return f"请评估以下问题:\n\n{last_content}"


# ============================================================
# Nested Chat 配置工厂
# ============================================================
def create_nested_chat_config(
    evaluator_agent: ConversableAgent,
    max_rounds: int = 5,
) -> NestedChatTarget:
    """创建 NestedChatTarget 实例，配置 Coach-Evaluator 审查循环

    使用 carryover_config 从 GroupChat 传递消息到 nested chat。
    carryover 会接收 GroupChat 的完整历史（trim 最后 2 条 transition 消息）。

    Args:
        evaluator_agent: AG2 ConversableAgent 实例（Evaluator）
        max_rounds: 最大审查轮次，每轮 = Coach 提交 + Evaluator 回复

    Returns:
        NestedChatTarget 实例，可直接传给 OnCondition.target
    """
    chat_queue = [
        {
            "recipient": evaluator_agent,
            "message": "开始评估",  # 初始消息
            "carryover_config": {
                "summary_method": _extract_question_from_carryover,
                "summary_args": {},
            },
            "summary_method": "last_msg",
            "max_turns": max_rounds * 2,
        }
    ]

    target = NestedChatTarget(
        nested_chat_config={"chat_queue": chat_queue}
    )

    logger.info(
        "NestedChatTarget 配置完成: evaluator=%s, max_turns=%d",
        evaluator_agent.name,
        max_rounds * 2,
    )
    return target
