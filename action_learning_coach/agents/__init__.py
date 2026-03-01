"""
[INPUT]: 依赖 agents/master_coach, agents/evaluator, agents/user_proxy,
         agents/observer, agents/reflection_agent
[OUTPUT]: 对外提供 WIALMasterCoach, StrictEvaluator, UserProxy, observe_turn, ReflectionFacilitator
[POS]: agents 模块的入口，统一导出所有 Agent 类和函数
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from importlib import import_module

_EXPORTS = {
    "WIALMasterCoach": (".master_coach", "WIALMasterCoach"),
    "StrictEvaluator": (".evaluator", "StrictEvaluator"),
    "UserProxy": (".user_proxy", "UserProxy"),
    "observe_turn": (".observer", "observe_turn"),
    "ReflectionFacilitator": (".reflection_agent", "ReflectionFacilitator"),
}


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module 'agents' has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value

__all__ = [
    "WIALMasterCoach",
    "StrictEvaluator",
    "UserProxy",
    "observe_turn",
    "ReflectionFacilitator",
]
