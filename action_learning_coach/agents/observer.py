"""
[INPUT]: 依赖 autogen.agentchat.group (FunctionTargetResult, AgentTarget),
         依赖 autogen.agentchat (ContextVariables),
         依赖 core/config (LLMConfig),
         依赖 memory (CognitiveState),
         依赖 prompts/observer_prompt (OBSERVER_SYSTEM_MESSAGE)
[OUTPUT]: 对外提供 observe_turn 函数，作为 AG2 FunctionTarget 回调
[POS]: agents 模块的观察组件，传感器定位，提取 L1 认知状态，双轨 FSM 路由
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
import re

from autogen import ConversableAgent
from autogen.agentchat import ContextVariables
from autogen.agentchat.group import AgentTarget, FunctionTargetResult, TerminateTarget

try:
    from ..core.config import LLMConfig
    from ..memory import CognitiveState
    from ..prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE
    from ..utils.logger import get_logger
except ImportError:
    from core.config import LLMConfig
    from memory import CognitiveState
    from prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE
    from utils.logger import get_logger

logger = get_logger(__name__)

# ============================================================
# 常量
# ============================================================
REFLECTION_THRESHOLD = 0.7
REFLECTION_EXIT_THRESHOLD = 0.5
MAX_REFLECTION_TURNS = 3


# ============================================================
# Observer — 认知状态提取 + 双轨 FSM 路由
# ============================================================
def observe_turn(
    output: str,
    ctx: ContextVariables,
    observer_config: LLMConfig | None = None,
    coach_agent: ConversableAgent | None = None,
    reflection_agent: ConversableAgent | None = None,
) -> FunctionTargetResult:
    """分析对话内容，提取 L1 认知状态，双轨路由

    双轨 FSM:
        业务轨: readiness < 0.7 → Coach
                readiness >= 0.7 → Reflection Agent
        反思轨: readiness < 0.5 / 超 3 轮 / 用户要求 → Coach
                否则 → 继续 Reflection Agent
    """
    if not str(output or "").strip():
        logger.info("Observer: empty user output, terminating current run")
        return FunctionTargetResult(target=TerminateTarget())

    turn = ctx.get("round", 0)
    current_track = ctx.get("current_track", "business")

    # 提取 L1 认知状态
    summary_chain = ctx.get("summary_chain", {"entries": []})
    analysis_input = _build_analysis_input(output, summary_chain, turn)
    cognitive_dict = _extract_cognitive_state(analysis_input, observer_config)
    cognitive_dict["turn_number"] = turn

    readiness = cognitive_dict.get("reflection_readiness", {}).get("score", 0.0)

    logger.info(
        "Observer: turn=%d, track=%s, depth=%s, readiness=%.2f",
        turn, current_track,
        cognitive_dict.get("thinking_depth", "unknown"),
        readiness,
    )

    # 双轨路由
    target_agent, next_track, reflection_turns = _route(
        current_track=current_track,
        readiness=readiness,
        output=output,
        ctx=ctx,
        coach_agent=coach_agent,
        reflection_agent=reflection_agent,
    )

    updated_ctx = ContextVariables(data={
        "cognitive_state": cognitive_dict,
        "current_track": next_track,
        "reflection_turn_count": reflection_turns,
    })

    return FunctionTargetResult(
        context_variables=updated_ctx,
        target=AgentTarget(target_agent),
    )


# ============================================================
# 双轨路由决策
# ============================================================
def _route(
    current_track: str,
    readiness: float,
    output: str,
    ctx: ContextVariables,
    coach_agent: ConversableAgent | None,
    reflection_agent: ConversableAgent | None,
) -> tuple[ConversableAgent, str, int]:
    """返回 (target_agent, next_track, reflection_turn_count)"""
    reflection_turns = ctx.get("reflection_turn_count", 0)

    # 无 Reflection Agent → 始终走业务轨
    if reflection_agent is None:
        return coach_agent, "business", 0

    if current_track == "business":
        if readiness >= REFLECTION_THRESHOLD:
            logger.info("Track switch: business → reflection (readiness=%.2f)", readiness)
            return reflection_agent, "reflection", 1
        return coach_agent, "business", 0

    # current_track == "reflection"
    # 条件 1: 用户明确要求切回
    if _user_requests_business(output):
        logger.info("Track switch: reflection → business (user request)")
        return coach_agent, "business", 0

    # 条件 2: 反思完成 (readiness 下降)
    if readiness < REFLECTION_EXIT_THRESHOLD:
        logger.info("Track switch: reflection → business (readiness=%.2f)", readiness)
        return coach_agent, "business", 0

    # 条件 3: 反思轨超过 3 轮
    if reflection_turns >= MAX_REFLECTION_TURNS:
        logger.info("Track switch: reflection → business (max turns=%d)", reflection_turns)
        return coach_agent, "business", 0

    # 继续反思
    return reflection_agent, "reflection", reflection_turns + 1


def _user_requests_business(output: str) -> bool:
    """检测用户是否要���切回业务轨"""
    keywords = ["继续业务", "回到问题", "继续讨论", "回到业务", "具体问题"]
    return any(kw in output for kw in keywords)


# ============================================================
# 内部工具
# ============================================================
def _build_analysis_input(
    user_message: str,
    summary_chain: dict | list,
    turn: int,
) -> str:
    """构造 Observer 的分析输入"""
    parts = [f"[Turn {turn}] User: {user_message}"]

    # 兼容 dict 和 list 格式
    if isinstance(summary_chain, dict):
        entries = summary_chain.get("entries", [])
    elif isinstance(summary_chain, list):
        entries = summary_chain
    else:
        entries = []

    if entries:
        recent = entries[-2:]
        chain_text = " | ".join(
            f"Phase {e.get('phase', '?')}: {e.get('summary', '')}"
            for e in recent
        )
        parts.append(f"[Context] {chain_text}")

    return "\n".join(parts)


def _extract_cognitive_state(
    analysis_input: str,
    observer_config: LLMConfig | None,
) -> dict:
    """调用轻量 LLM 提取 L1 认知状态

    若无 config (mock 模式)，返回默认状态。
    """
    if observer_config is None:
        return CognitiveState().to_dict()

    observer_agent = ConversableAgent(
        name="Observer_LLM",
        system_message=OBSERVER_SYSTEM_MESSAGE,
        llm_config=observer_config.to_autogen_config(),
        human_input_mode="NEVER",
    )

    raw = observer_agent.generate_reply(
        messages=[{"role": "user", "content": analysis_input}]
    )

    return _parse_cognitive_json(raw)


def _parse_cognitive_json(raw) -> dict:
    """解析 LLM 返回的认知状态 JSON"""
    if raw is None:
        return CognitiveState().to_dict()

    if isinstance(raw, dict):
        return raw

    text = str(raw)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    logger.warning("Observer: failed to parse JSON, using defaults. raw=%s", text[:200])
    return CognitiveState().to_dict()
