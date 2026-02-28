"""
[INPUT]: 依赖 autogen.agentchat.group (FunctionTargetResult, AgentTarget),
         依赖 autogen.agentchat (ContextVariables),
         依赖 core/config (LLMConfig),
         依赖 memory (CognitiveState),
         依赖 prompts/observer_prompt (OBSERVER_SYSTEM_MESSAGE)
[OUTPUT]: 对外提供 observe_turn 函数，作为 AG2 FunctionTarget 回调
[POS]: agents 模块的观察组件，传感器定位，提取 L1 认知状态，零对话开销
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json

from autogen import ConversableAgent
from autogen.agentchat import ContextVariables
from autogen.agentchat.group import AgentTarget, FunctionTargetResult

from core.config import LLMConfig
from memory import CognitiveState
from prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Observer — 认知状态提取 (FunctionTarget 回调)
# ============================================================
def observe_turn(
    output: str,
    ctx: ContextVariables,
    observer_config: LLMConfig | None = None,
    coach_agent: ConversableAgent | None = None,
) -> FunctionTargetResult:
    """分析对话内容，提取 L1 认知状态，路由到 Coach

    AG2 FunctionTarget 规约:
        参数1 output: groupchat.messages[-1]["content"]
        参数2 ctx: current_agent.context_variables
        其余参数: 通过 FunctionTarget(extra_args={...}) 注入

    Returns:
        FunctionTargetResult — 更新后的 ContextVariables + 下一跳 AgentTarget
    """
    # 更新轮次
    turn = ctx.get("round", 0)

    # 构造 Observer 分析输入
    summary_chain = ctx.get("summary_chain", {})
    analysis_input = _build_analysis_input(output, summary_chain, turn)

    # 调用轻量 LLM 提取认知状态
    cognitive_dict = _extract_cognitive_state(analysis_input, observer_config)

    # 合并轮次
    cognitive_dict["turn_number"] = turn

    # 更新 ContextVariables
    updated_ctx = ContextVariables(data={
        "cognitive_state": cognitive_dict,
    })

    logger.info(
        "Observer: turn=%d, depth=%s, readiness=%.2f",
        turn,
        cognitive_dict.get("thinking_depth", "unknown"),
        cognitive_dict.get("reflection_readiness", {}).get("score", 0.0),
    )

    # Phase 2c: 始终路由到 Coach (Phase 2d 将添加 Reflection 分支)
    return FunctionTargetResult(
        context_variables=updated_ctx,
        target=AgentTarget(coach_agent),
    )


# ============================================================
# 内部工具
# ============================================================
def _build_analysis_input(
    user_message: str,
    summary_chain: dict,
    turn: int,
) -> str:
    """构造 Observer 的分析输入"""
    parts = [f"[Turn {turn}] User: {user_message}"]

    entries = summary_chain.get("entries", [])
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

    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # markdown 代码块
    import re
    match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    logger.warning("Observer: failed to parse JSON, using defaults. raw=%s", text[:200])
    return CognitiveState().to_dict()
