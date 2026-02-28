"""
[INPUT]: 无外部依赖
[OUTPUT]: 对外提供 agents 模块的公共接口
[POS]: agents 模块的入口，统一导出 WIALMasterCoach, StrictEvaluator
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from agents.master_coach import WIALMasterCoach
from agents.evaluator import StrictEvaluator
# UserProxy 暂时不导出，因为它依赖旧版 API 且当前未使用
# from .user_proxy import UserProxy

__all__ = ["WIALMasterCoach", "StrictEvaluator"]
