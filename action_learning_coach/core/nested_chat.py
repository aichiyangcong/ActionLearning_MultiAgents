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
# 消息提取
# ============================================================
def _extract_question(
    recipient: ConversableAgent,
    messages: list[dict[str, Any]],
    sender: ConversableAgent,
    config: Any,
) -> str:
    """从 Coach 输出中提取问题供 Evaluator 评估

    AG2 nested chat 的 message callable 签名:
        (recipient, messages, sender, config) -> str

    提取策略: 尝试 JSON 解析取 question 字段，回退到原始文本。
    """
    import json

    last_content = messages[-1].get("content", "") if messages else ""

    # 尝试从 JSON 格式中提取 question
    try:
        data = json.loads(last_content)
        question = data.get("question", last_content)
    except (json.JSONDecodeError, TypeError):
        question = last_content

    return f"请评估以下问题:\n\n{question}"


# ============================================================
# Nested Chat 配置工厂
# ============================================================
def create_nested_chat_config(
    evaluator_agent: ConversableAgent,
    max_rounds: int = 5,
) -> NestedChatTarget:
    """创建 NestedChatTarget 实例，配置 Coach-Evaluator 审查循环

    Args:
        evaluator_agent: AG2 ConversableAgent 实例（Evaluator）
        max_rounds: 最大审查轮次，每轮 = Coach 提交 + Evaluator 回复

    Returns:
        NestedChatTarget 实例，可直接传给 OnCondition.target
    """
    chat_queue = [
        {
            "recipient": evaluator_agent,
            "message": _extract_question,
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
