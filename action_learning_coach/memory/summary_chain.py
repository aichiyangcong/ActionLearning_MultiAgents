"""
[INPUT]: 依赖 dataclasses, typing
[OUTPUT]: 对外提供 SummaryEntry + SummaryChain dataclass，~200 tokens 的会话摘要链
[POS]: memory 模块的 L2 层，阶段性追加，记录认知演变轨迹
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================
# L2: 会话摘要链 (~200 tokens) — 阶段追加
# ============================================================
@dataclass
class SummaryEntry:
    """单阶段摘要"""

    phase: str
    turns: str
    summary: str
    anchor_quote: str = ""
    cognitive_shift: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SummaryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SummaryChain:
    """会话摘要链 — 记录认知演变的阶段序列

    核心职责: 按阶段记录学习者的认知迁移路径
    更新策略: Observer 判定阶段切换时追加新条目
    """

    entries: list[SummaryEntry] = field(default_factory=list)

    def append(self, entry: SummaryEntry) -> None:
        self.entries.append(entry)

    def to_dict(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.entries]

    @classmethod
    def from_dict(cls, data: list[dict[str, Any]]) -> "SummaryChain":
        return cls(entries=[SummaryEntry.from_dict(d) for d in data])
