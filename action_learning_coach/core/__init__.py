"""
[INPUT]: 依赖 core/config, core/nested_chat, core/orchestrator (lazy)
[OUTPUT]: 对外提供 LLMConfig, get_llm_config, create_nested_chat_config, Orchestrator, TurnResult
[POS]: core 模块的入口，统一导出配置管理、Legacy NestedChat 兼容工具、Orchestrator
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from importlib import import_module

from .config import LLMConfig, get_llm_config


# 延迟导入: 避免循环依赖，也避免在 mock/测试收集阶段强制加载 AG2 依赖。
# create_nested_chat_config 仍然保留，但仅作为 Legacy 兼容 API。
def __getattr__(name):
    if name == "create_nested_chat_config":
        func = import_module(".nested_chat", __name__).create_nested_chat_config
        globals()[name] = func
        return func
    if name in ("Orchestrator", "TurnResult"):
        orchestrator_module = import_module(".orchestrator", __name__)
        globals()["Orchestrator"] = orchestrator_module.Orchestrator
        globals()["TurnResult"] = orchestrator_module.TurnResult
        return globals()[name]
    raise AttributeError(f"module 'core' has no attribute {name!r}")


__all__ = [
    "LLMConfig",
    "get_llm_config",
    "create_nested_chat_config",
    "Orchestrator",
    "TurnResult",
]
