"""
[INPUT]: 依赖 logging 标准库，依赖 colorlog 的彩色输出
[OUTPUT]: 对外提供 get_logger() 函数，返回配置好的 Logger 实例
[POS]: utils 模块的日志工具，为整个项目提供统一的日志记录
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import logging
import os
from typing import Optional

try:
    import colorlog
except ImportError:
    colorlog = None


# ============================================================
# Logger Configuration
# ============================================================
def get_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    创建并配置 Logger 实例

    Args:
        name: Logger 名称，通常使用 __name__
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)，默认从环境变量读取
        log_file: 日志文件路径，默认从环境变量读取

    Returns:
        配置好的 Logger 实例
    """
    # 从环境变量获取配置
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if log_file is None:
        log_file = os.getenv("LOG_FILE", "action_learning_coach.log")

    # 创建 Logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加 Handler
    if logger.handlers:
        return logger

    # Console Handler: use plain logging when colorlog is unavailable.
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    if colorlog:
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (Plain Text)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level.upper()))
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger
