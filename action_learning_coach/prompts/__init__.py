"""
[INPUT]: 无外部依赖
[OUTPUT]: 对外提供 COACH_SYSTEM_MESSAGE, EVALUATOR_SYSTEM_MESSAGE
[POS]: prompts 模块入口，聚合所有 prompt 常量
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from .coach_prompt import COACH_SYSTEM_MESSAGE
from .evaluator_prompt import EVALUATOR_SYSTEM_MESSAGE

__all__ = ["COACH_SYSTEM_MESSAGE", "EVALUATOR_SYSTEM_MESSAGE"]
