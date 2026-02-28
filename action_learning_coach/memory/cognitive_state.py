"""
[INPUT]: 依赖 dataclasses, typing
[OUTPUT]: 对外提供 CognitiveState dataclass，~400 tokens 的认知状态快照
[POS]: memory 模块的 L1 层，每轮由 Observer 覆写，捕捉学习者当前认知状态
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================
# L1: 认知状态 (~400 tokens) — 每轮覆写
# ============================================================
@dataclass
class CognitiveState:
    """学习者当前认知状态快照

    核心职责: 捕捉此刻的认知全景 — 话题、情绪、深度、假设、盲点
    更新策略: 每轮由 Observer 完整覆写，不累积历史
    """

    current_topic: str = ""
    emotional_tone: str = "neutral"
    thinking_depth: str = "surface"  # surface | analytical | reflective
    key_assumptions: list[dict[str, Any]] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)
    anchor_quotes: list[str] = field(default_factory=list)
    reflection_readiness: dict[str, Any] = field(
        default_factory=lambda: {"score": 0.0, "signals": []}
    )
    turn_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CognitiveState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
