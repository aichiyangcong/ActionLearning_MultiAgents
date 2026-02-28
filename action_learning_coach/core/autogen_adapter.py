"""
[INPUT]: 依赖 httpx 的 HTTP 客户端，依赖 json 的数据解析
[OUTPUT]: 对外提供 ConversableAgent 适配器类
[POS]: core 模块的适配层，封装 Anthropic API 调用，支持第三方 API
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
import httpx
from typing import Dict, Any, List


# ============================================================
# ConversableAgent Adapter - 简化版本
# ============================================================
class ConversableAgent:
    """
    简化的 Agent 适配器，直接使用 httpx 调用 Anthropic API

    支持第三方 Anthropic API (如 aicode.life)，使用 x-api-key 认证
    """

    def __init__(
        self,
        name: str,
        system_message: str,
        llm_config: Dict[str, Any],
        human_input_mode: str = "NEVER",
    ):
        """
        初始化适配器

        Args:
            name: Agent 名称
            system_message: 系统消息
            llm_config: LLM 配置 (格式: {config_list: [{model, api_key, base_url}], temperature})
            human_input_mode: 人类输入模式 (兼容参数，未使用)
        """
        self.name = name
        self.system_message = system_message

        # 从 llm_config 提取配置
        config_list = llm_config.get("config_list", [{}])
        first_config = config_list[0] if config_list else {}

        self.model = first_config.get("model", "claude-sonnet-4-6")
        self.api_key = first_config.get("api_key", "")
        self.base_url = first_config.get("base_url", "https://api.anthropic.com")
        self.temperature = llm_config.get("temperature", 0.7)

        # 确保 base_url 以 /v1/messages 结尾
        if not self.base_url.endswith("/v1/messages"):
            self.base_url = self.base_url.rstrip("/") + "/v1/messages"

    def generate_reply(self, messages: List[Dict[str, str]]) -> str:
        """
        生成回复 (同步接口)

        Args:
            messages: 消息列表，格式 [{\"role\": \"user\", \"content\": \"...\"}]

        Returns:
            LLM 生成的回复文本
        """
        # 构建请求头 - 使用 x-api-key 而非标准 Anthropic 认证
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        # 转换消息格式为 Anthropic API 格式
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # 跳过 system 消息 (已在初始化时设置)
            if role != "system":
                anthropic_messages.append({
                    "role": role,
                    "content": content
                })

        # 构建请求体
        request_body = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "temperature": self.temperature,
            "system": self.system_message,  # 系统消息单独传递
        }

        # 发送同步请求
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                self.base_url,
                headers=headers,
                json=request_body,
            )
            response.raise_for_status()
            result = response.json()

        # 提取响应内容
        content = ""
        if "content" in result and len(result["content"]) > 0:
            content = result["content"][0].get("text", "")

        return content
