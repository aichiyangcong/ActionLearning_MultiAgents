"""
[INPUT]: 依赖 core/config, core/nested_chat, core/orchestrator (lazy)
[OUTPUT]: 对外提供 LLMConfig, get_llm_config, create_nested_chat_config, Orchestrator, TurnResult
[POS]: core 模块的入口，统一导出配置管理、Nested Chat 编排、Orchestrator
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from .config import LLMConfig, get_llm_config
from .nested_chat import create_nested_chat_config


# Orchestrator 延迟导入: orchestrator → agents → core 存在循环依赖
def __getattr__(name):
    if name in ("Orchestrator", "TurnResult"):
        from .orchestrator import Orchestrator, TurnResult
        globals()["Orchestrator"] = Orchestrator
        globals()["TurnResult"] = TurnResult
        return globals()[name]
    raise AttributeError(f"module 'core' has no attribute {name!r}")


__all__ = [
    "LLMConfig",
    "get_llm_config",
    "create_nested_chat_config",
    "Orchestrator",
    "TurnResult",
]
