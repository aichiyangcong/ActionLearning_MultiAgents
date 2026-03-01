"""
[INPUT]: 依赖 python-dotenv 的环境变量加载，依赖 os 的系统环境访问
[OUTPUT]: 对外提供 get_llm_config() 函数，LLMConfig 数据类
[POS]: core 模块的配置中心，为所有 Agent 提供统一的 LLM 配置
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import os
import time
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        """Allow mock mode imports when python-dotenv is unavailable."""
        return False

# ============================================================
# Load Environment Variables
# ============================================================
load_dotenv()


# ============================================================
# Proxy-Compatible HTTP Client
# ============================================================
# Anthropic SDK 的 x-stainless-* headers 会被部分代理 Cloudflare 规则拦截
# 用纯 httpx 替换 SDK 的 HTTP 层，只保留 Message 模型解析


def _read_non_negative_int(name: str, default: int) -> int:
    """读取非负整型环境变量，解析失败时回退默认值。"""
    raw = str(os.getenv(name, default)).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def _read_non_negative_float(name: str, default: float) -> float:
    """读取非负浮点环境变量，解析失败时回退默认值。"""
    raw = str(os.getenv(name, default)).strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return max(0.0, value)


def _is_retryable_status(status_code: int) -> bool:
    """判断 HTTP 状态码是否适合重试。"""
    return status_code in {408, 409, 429, 500, 502, 503, 504}


def _get_retry_delay(response, attempt: int, base_delay: float) -> float:
    """优先尊重 Retry-After，否则使用指数退避。"""
    if response is not None:
        retry_after = response.headers.get("Retry-After", "").strip()
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
    return max(0.0, base_delay * (2 ** attempt))


def _format_http_error(exc) -> RuntimeError | None:
    """把常见网关错误转换成更易懂的异常消息。"""
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code == 429:
        return RuntimeError(
            "Anthropic-compatible gateway rate limited the request (429 Too Many Requests). "
            "Please wait a moment and retry."
        )
    return None

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
                self._max_retries = _read_non_negative_int("ANTHROPIC_MAX_RETRIES", 2)
                self._retry_backoff_seconds = _read_non_negative_float(
                    "ANTHROPIC_RETRY_BACKOFF_SECONDS", 1.0
                )

            def create(self, **params):
                for attempt in range(self._max_retries + 1):
                    try:
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
                    except httpx.HTTPStatusError as exc:
                        status_code = getattr(exc.response, "status_code", None)
                        should_retry = (
                            status_code is not None
                            and _is_retryable_status(status_code)
                            and attempt < self._max_retries
                        )
                        if should_retry:
                            time.sleep(
                                _get_retry_delay(
                                    exc.response,
                                    attempt,
                                    self._retry_backoff_seconds,
                                )
                            )
                            continue

                        friendly_error = _format_http_error(exc)
                        if friendly_error is not None:
                            raise friendly_error from exc
                        raise
                    except httpx.RequestError as exc:
                        if attempt < self._max_retries:
                            time.sleep(_get_retry_delay(None, attempt, self._retry_backoff_seconds))
                            continue
                        raise RuntimeError(
                            "Unable to reach the Anthropic-compatible gateway. "
                            "Check network, proxy, or ANTHROPIC_BASE_URL and retry."
                        ) from exc

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
