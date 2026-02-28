"""
[INPUT]: 无外部依赖
[OUTPUT]: 对外提供 utils 模块的公共接口 (logger)
[POS]: utils 模块的入口，统一导出工具函数
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from .logger import get_logger

__all__ = ["get_logger"]
