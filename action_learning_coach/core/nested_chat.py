"""
[INPUT]: 依赖 autogen.ConversableAgent (AG2 0.11.2)，
         依赖 autogen.agentchat.group.targets.transition_target.NestedChatTarget
[OUTPUT]: 对外提供 create_nested_chat_config(evaluator_agent, max_rounds) 函数，
          返回 NestedChatTarget 实例，可直接用于 OnCondition/OnContextCondition
[POS]: core 模块的 Legacy Nested Chat 兼容工具。
       当前真实业务主路径已改为 Orchestrator 内的显式 Coach→Evaluator 多轮闭环，
       本模块仅保留给历史实验、兼容测试和 AG2 handoff 参考使用。
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Any

from autogen import ConversableAgent
from autogen.agentchat.group.targets.transition_target import NestedChatTarget
from autogen.agentchat.group import RevertToUserTarget

try:
    from ..utils.logger import get_logger
except ImportError:
    from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 自定义 Target (nested 结束后直接回用户，避免回到 Coach 死循环)
# ============================================================
class ReviewNestedChatTarget(NestedChatTarget):
    """让 nested review 结束后回用户，而不是回父 Agent。"""

    def create_wrapper_agent(self, parent_agent: ConversableAgent, index: int) -> ConversableAgent:
        wrapper = super().create_wrapper_agent(parent_agent, index)
        wrapper.handoffs.set_after_work(RevertToUserTarget())
        return wrapper


# ============================================================
# 消息提取 (从 Coach 输出中提取)
# ============================================================
def _normalize_text(content: Any) -> str:
    """统一文本清洗。"""
    if content is None:
        return ""
    return str(content).strip()


def _looks_like_transfer_message(text: str) -> bool:
    """判断是否是 AG2 handoff 的工具转移文本。"""
    candidate = text.strip()
    return (
        candidate.startswith("Transfer to ")
        or "transfer_to_wrapped_nested_" in candidate
    )


def _strip_review_request_prefix(text: str) -> str:
    """移除嵌套评审包装前缀。"""
    prefix = "请评估以下问题:"
    if text.startswith(prefix):
        return text[len(prefix):].strip()
    return text


def _looks_like_evaluator_feedback(text: str) -> bool:
    """判断是否是评估器在索要问题，而不是实际问题。"""
    feedback_markers = (
        "请直接发送",
        "请提供 WIAL Master Coach 生成的",
        "需要一个具体的问题",
        "需要一个具体的教练问题",
        "我无法对其进行评分",
        "我会按照三个维度",
    )
    return any(marker in text for marker in feedback_markers)


def _is_valid_question_candidate(text: str, *, allow_plain_text: bool) -> bool:
    """判断提取结果是否像一个真实待评估问题。"""
    if not text:
        return False
    if text.lstrip().startswith("```"):
        return False
    if _looks_like_transfer_message(text):
        return False
    if _looks_like_evaluator_feedback(text):
        return False
    if allow_plain_text:
        return True
    return "?" in text or "？" in text


def extract_user_input_from_messages(messages: list[dict[str, Any]] | None) -> str:
    """从父消息历史中提取原始用户输入。"""
    if not messages:
        return ""

    for msg in messages:
        name = msg.get("name")
        text = _normalize_text(msg.get("content", ""))
        if not text:
            continue
        if _looks_like_transfer_message(text):
            continue
        if text.startswith("请评估以下问题:"):
            continue
        if isinstance(name, str):
            if name == "_Group_Tool_Executor":
                continue
            if name.startswith("wrapped_nested_"):
                continue
        return text

    return ""


def extract_question_from_messages(
    messages: list[dict[str, Any]] | None,
    coach_name: str | None = None,
) -> str:
    """从消息历史中提取最近一次 Coach 问题。"""
    import json

    if not messages:
        return ""

    def _parse_question(content: Any, *, allow_plain_text: bool) -> str:
        import re

        text = _normalize_text(content)
        if not text:
            return ""

        text = _strip_review_request_prefix(text)
        if not text:
            return ""

        parsed_payload: Any = None
        try:
            parsed_payload = json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
            if match:
                try:
                    parsed_payload = json.loads(match.group(1))
                except (json.JSONDecodeError, TypeError, ValueError):
                    parsed_payload = None

        if isinstance(parsed_payload, dict):
            review_keys = {"score", "pass", "feedback", "breakdown"}
            if any(key in parsed_payload for key in review_keys):
                return ""

            question = _normalize_text(parsed_payload.get("question", ""))
            if _is_valid_question_candidate(question, allow_plain_text=True):
                return question
            return ""

        if _is_valid_question_candidate(text, allow_plain_text=allow_plain_text):
            return text
        return ""

    if coach_name:
        for msg in reversed(messages):
            if msg.get("name") != coach_name:
                continue
            question = _parse_question(msg.get("content", ""), allow_plain_text=True)
            if question:
                return question

    for msg in reversed(messages):
        name = msg.get("name", "")
        if not isinstance(name, str) or not name.startswith("wrapped_nested_"):
            continue
        question = _parse_question(msg.get("content", ""), allow_plain_text=True)
        if question:
            return question

    for msg in reversed(messages):
        question = _parse_question(msg.get("content", ""), allow_plain_text=False)
        if question:
            return question

    return ""


# ============================================================
# Nested Chat 首条消息构造
# ============================================================
def _build_evaluator_message(
    recipient: ConversableAgent,
    messages: list[dict[str, Any]],
    sender: ConversableAgent | None,
    config: dict[str, Any] | None,
) -> str:
    """从消息列表中提取待评估的问题，生成发给 Evaluator 的输入。"""
    logger.info("NestedChat message count: %d", len(messages))
    state = config.get("review_state") if isinstance(config, dict) else None
    if not isinstance(state, dict):
        state = {}

    cached_question = _normalize_text(state.get("last_question", ""))
    if cached_question:
        logger.info("Reusing cached nested question: %s", cached_question)
        return f"请评估以下问题:\n\n{cached_question}"

    coach_name = None
    if isinstance(config, dict):
        coach_name = config.get("coach_name")

    question = extract_question_from_messages(messages, coach_name=coach_name)
    if not question and isinstance(config, dict):
        coach_wrapper = config.get("coach_wrapper")
        user_input = extract_user_input_from_messages(messages)
        if coach_wrapper is not None and user_input:
            generated: Any = None
            try:
                generated = coach_wrapper.generate_question(user_input)
                if isinstance(generated, dict):
                    question = _normalize_text(generated.get("question", ""))
                else:
                    question = _normalize_text(generated)
            except Exception as exc:
                logger.warning("Coach fallback generation failed in nested chat: %s", exc)
            if generated is not None and not question:
                logger.warning("Coach fallback returned no usable question: %r", generated)
            if question:
                logger.warning("NestedChat recovered question via direct coach generation")

    if question:
        state["last_question"] = question
        logger.info("Extracted question: %s", question)
        return f"请评估以下问题:\n\n{question}"

    logger.warning("No message content found for nested evaluation")
    return "请评估以下问题:\n\n"


# ============================================================
# Nested Chat 配置工厂
# ============================================================
def create_nested_chat_config(
    evaluator_agent: ConversableAgent,
    max_rounds: int = 5,
    coach_name: str | None = None,
    coach_wrapper: Any | None = None,
    review_state: dict[str, Any] | None = None,
) -> NestedChatTarget:
    """创建 Legacy NestedChatTarget 配置。

    Args:
        evaluator_agent: AG2 ConversableAgent 实例（Evaluator）
        max_rounds: 最大审查轮次，每轮 = Coach 提交 + Evaluator 回复

    Returns:
        NestedChatTarget 实例，可直接传给 OnCondition.target。
        注意: 当前主流程不再使用这条路径。
    """
    # 真实运行时如果直接把 coach wrapper 传进来，说明需要在 nested chat 内兜底补生成。
    # 这条路径只能做单次评审；多轮改写需要显式的 coach→evaluator→coach 编排。
    max_turns = 1 if coach_wrapper is not None else max_rounds * 2
    shared_review_state = review_state if review_state is not None else {}
    message_context = {
        "coach_name": coach_name,
        "coach_wrapper": coach_wrapper,
        "review_state": shared_review_state,
    }

    def message_builder(
        recipient: ConversableAgent,
        messages: list[dict[str, Any]],
        sender: ConversableAgent | None,
        runtime_config: dict[str, Any] | None,
    ) -> str:
        del runtime_config
        return _build_evaluator_message(
            recipient,
            messages,
            sender,
            message_context,
        )

    chat_queue = [
        {
            "recipient": evaluator_agent,
            "message": message_builder,
            "summary_method": "last_msg",
            "max_turns": max_turns,
        }
    ]

    target = ReviewNestedChatTarget(
        nested_chat_config={"chat_queue": chat_queue}
    )

    logger.info(
        "NestedChatTarget 配置完成: evaluator=%s, max_turns=%d",
        evaluator_agent.name,
        max_turns,
    )
    return target
