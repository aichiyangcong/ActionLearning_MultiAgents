"""
[INPUT]: 依赖 python-dotenv 的环境变量加载，依赖 os 的系统环境访问
[OUTPUT]: 对外提供 get_llm_config() 函数，LLMConfig 数据类
[POS]: core 模块的配置中心，为所有 Agent 提供统一的 LLM 配置
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# ============================================================
# Load Environment Variables
# ============================================================
load_dotenv()


# ============================================================
# Proxy-Compatible HTTP Client
# ============================================================
# Anthropic SDK 的 x-stainless-* headers 会被部分代理 Cloudflare 规则拦截
# 用纯 httpx 替换 SDK 的 HTTP 层，只保留 Message 模型解析

def _patch_anthropic_client():
    """替换 AG2 AnthropicClient._client 为纯 httpx 实现"""
    try:
        import httpx
        from anthropic.types import Message
        from autogen.oai.anthropic import AnthropicClient

        class _HttpxMessages:
            """只实现 messages.create()，返回 Anthropic Message 对象"""

            def __init__(self, api_key: str, base_url: str):
                self._api_key = api_key
                self._base_url = base_url.rstrip("/")
                self._http = httpx.Client(timeout=120)

            def create(self, **params):
                resp = self._http.post(
                    f"{self._base_url}/v1/messages",
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json=params,
                )
                resp.raise_for_status()
                data = resp.json()

                # 修复代理 API 返回的空 stop_reason
                if "stop_reason" in data and not data["stop_reason"]:
                    data["stop_reason"] = "end_turn"

                return Message.model_validate(data)

        class _HttpxProxy:
            """模拟 anthropic.Anthropic，只暴露 .messages 属性"""

            def __init__(self, api_key: str, base_url: str):
                self.messages = _HttpxMessages(api_key, base_url)

        _orig_init = AnthropicClient.__init__

        def _patched_init(self, *args, **kwargs):
            _orig_init(self, *args, **kwargs)
            if hasattr(self, "_client") and self._client is not None:
                self._client = _HttpxProxy(
                    api_key=self._api_key,
                    base_url=self._base_url or "https://api.anthropic.com",
                )

        AnthropicClient.__init__ = _patched_init
    except ImportError:
        pass

_patch_anthropic_client()


# ============================================================
# Configuration Data Class
# ============================================================
@dataclass
class LLMConfig:
    """LLM 配置数据类，封装所有 LLM 相关参数"""

    api_key: str
    base_url: Optional[str]
    model: str
    temperature: float
    max_review_rounds: int
    pass_score_threshold: int

    def to_autogen_config(self) -> dict:
        """转换为 AutoGen 所需的配置格式"""
        config = {
            "config_list": [
                {
                    "model": self.model,
                    "api_key": self.api_key,
                    "api_type": "anthropic",
                }
            ],
            "temperature": self.temperature,
        }

        if self.base_url:
            config["config_list"][0]["base_url"] = self.base_url

        return config


# ============================================================
# Configuration Factory
# ============================================================
def get_llm_config(agent_type: str = "default") -> LLMConfig:
    """从环境变量加载 LLM 配置，支持不同 Agent 使用不同模型

    Args:
        agent_type: Agent 类型 ("coach", "evaluator", "observer", "reflection", "default")

    Returns:
        LLMConfig 实例
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    base_url = os.getenv("ANTHROPIC_BASE_URL", None)

    model_map = {
        "coach": os.getenv("COACH_MODEL", "claude-sonnet-4-6"),
        "evaluator": os.getenv("EVALUATOR_MODEL", "claude-opus-4-6"),
        "observer": os.getenv("OBSERVER_MODEL", "claude-haiku-4-5"),
        "reflection": os.getenv("REFLECTION_MODEL", "claude-sonnet-4-6"),
        "default": os.getenv("COACH_MODEL", "claude-sonnet-4-6"),
    }

    return LLMConfig(
        api_key=api_key,
        base_url=base_url,
        model=model_map.get(agent_type, model_map["default"]),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7")),
        max_review_rounds=int(os.getenv("MAX_REVIEW_ROUNDS", "5")),
        pass_score_threshold=int(os.getenv("PASS_SCORE_THRESHOLD", "95")),
    )
