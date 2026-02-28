# action_learning_coach/utils/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 get_logger
- logger.py: 日志工具，提供彩色 Console 输出 + 文件记录，支持环境变量配置 LOG_LEVEL 和 LOG_FILE

## 设计哲学
- 双输出: Console (colorlog 彩色) + File (纯文本)
- 环境驱动: 日志级别和文件路径从 .env 读取
- 单例模式: 避免重复添加 Handler

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
