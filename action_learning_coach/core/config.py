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

        # 如果有自定义 base_url，添加到配置中
        if self.base_url:
            config["config_list"][0]["base_url"] = self.base_url

        return config


# ============================================================
# Configuration Factory
# ============================================================
def get_llm_config(agent_type: str = "default") -> LLMConfig:
    """从环境变量加载 LLM 配置，支持不同 Agent 使用不同模型

    Args:
        agent_type: Agent 类型 ("coach", "evaluator", "default")

    Returns:
        LLMConfig 实例
    """
    # 获取 API Key 和 Base URL
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    base_url = os.getenv("ANTHROPIC_BASE_URL", None)

    # 根据 Agent 类型选择模型
    model_map = {
        "coach": os.getenv("COACH_MODEL", "claude-sonnet-4-6"),
        "evaluator": os.getenv("EVALUATOR_MODEL", "claude-opus-4-6"),
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
