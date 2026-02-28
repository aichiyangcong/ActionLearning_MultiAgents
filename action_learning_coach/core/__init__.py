"""
[INPUT]: 无外部依赖
[OUTPUT]: 对外提供 core 模块的公共接口 (config, autogen_adapter)
[POS]: core 模块的入口，统一导出配置管理和 API 适配器
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from .config import LLMConfig, get_llm_config
from .autogen_adapter import ConversableAgent

# nested_chat 延迟导入以避免循环依赖
def setup_nested_chat(*args, **kwargs):
    from .nested_chat import setup_nested_chat as _setup
    return _setup(*args, **kwargs)

__all__ = ["LLMConfig", "get_llm_config", "setup_nested_chat", "ConversableAgent"]
