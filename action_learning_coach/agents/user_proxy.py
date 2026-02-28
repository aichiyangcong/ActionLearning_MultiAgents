"""
[INPUT]: 依赖 autogen 的 ConversableAgent, UserProxyAgent
[OUTPUT]: 对外提供 UserProxy 类，register_nested_review 方法，initiate_chat 方法
[POS]: agents 模块的用户代理组件，管理对话历史，注册 Nested Chat 审查流程
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Dict, Any, List, Callable
from autogen import UserProxyAgent as AutoGenUserProxy


# ============================================================
# User Proxy Agent
# ============================================================
class UserProxy:
    """
    UserProxy Agent

    职责:
    - 代理用户与系统交互
    - 注册 Nested Chat 审查流程
    - 管理对话历史
    """

    def __init__(self):
        """初始化 UserProxy"""
        self._agent = AutoGenUserProxy(
            name="User",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
        )

    def register_nested_review(
        self,
        trigger_func: Callable,
        nested_chat_config: List[Dict[str, Any]],
    ):
        """
        注册 Nested Chat 审查流程

        Args:
            trigger_func: 触发 Nested Chat 的条件函数
            nested_chat_config: Nested Chat 配置列表
        """
        self._agent.register_nested_chats(
            trigger=trigger_func,
            chat_queue=nested_chat_config,
        )

    def initiate_chat(self, recipient, message: str) -> Dict[str, Any]:
        """
        发起对话

        Args:
            recipient: 接收消息的 Agent
            message: 用户消息

        Returns:
            对话结果
        """
        return self._agent.initiate_chat(
            recipient=recipient,
            message=message,
        )

    def get_agent(self):
        """获取底层 AutoGen Agent 实例"""
        return self._agent
