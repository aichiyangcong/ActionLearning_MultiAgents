"""
[INPUT]: 依赖 dataclasses, typing
[OUTPUT]: 对外提供 LearnerProfile dataclass，~300 tokens 的学习者画像
[POS]: memory 模块的 L3 层，跨会话渐进更新，学习者长期画像
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from dataclasses import dataclass, field, asdict
from typing import Any


# ============================================================
# L3: 学习者画像 (~300 tokens) — 跨会话渐进更新
# ============================================================
@dataclass
class LearnerProfile:
    """学习者长期画像

    核心职责: 跨会话积累学习者的思维模式、成长边界、偏好
    更新策略: 渐进合并 — 新数据与旧数据合并去重，不覆盖
    """

    learner_id: str = ""
    thinking_patterns: list[str] = field(default_factory=list)
    growth_edges: list[str] = field(default_factory=list)
    blind_spots: list[str] = field(default_factory=list)
    response_preferences: list[str] = field(default_factory=list)
    session_count: int = 0
    last_session_summary: str = ""

    def merge_update(self, new_data: dict[str, Any]) -> None:
        """渐进更新: 列表字段合并去重，标量字段直接覆盖"""
        list_fields = {
            "thinking_patterns",
            "growth_edges",
            "blind_spots",
            "response_preferences",
        }
        for key, value in new_data.items():
            if key not in self.__dataclass_fields__:
                continue
            if key in list_fields and isinstance(value, list):
                existing = getattr(self, key)
                merged = list(dict.fromkeys(existing + value))
                setattr(self, key, merged)
            else:
                setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnerProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
