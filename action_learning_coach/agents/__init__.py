"""
[INPUT]: 依赖 agents/master_coach, agents/evaluator, agents/user_proxy, agents/observer
[OUTPUT]: 对外提供 WIALMasterCoach, StrictEvaluator, UserProxy, observe_turn
[POS]: agents 模块的入口，统一导出所有 Agent 类和函数
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from agents.master_coach import WIALMasterCoach
from agents.evaluator import StrictEvaluator
from agents.user_proxy import UserProxy
from agents.observer import observe_turn

__all__ = ["WIALMasterCoach", "StrictEvaluator", "UserProxy", "observe_turn"]
