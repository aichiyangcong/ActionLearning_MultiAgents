#!/usr/bin/env python3
"""
测试修复后的 ConversableAgent 是否能正常调用第三方 Anthropic API
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "action_learning_coach"))

from core.config import get_llm_config
from core.autogen_adapter import ConversableAgent

def test_conversable_agent():
    """测试 ConversableAgent 基本功能"""
    print("=" * 60)
    print("测试 ConversableAgent 与第三方 Anthropic API")
    print("=" * 60)

    # 获取配置
    print("\n1. 加载配置...")
    llm_config = get_llm_config("coach")
    print(f"   Model: {llm_config.model}")
    print(f"   Base URL: {llm_config.base_url}")
    print(f"   API Key: {llm_config.api_key[:20]}...")

    # 创建 Agent
    print("\n2. 创建 ConversableAgent...")
    agent = ConversableAgent(
        name="TestAgent",
        system_message="你是一个测试助手，请简洁回答问题。",
        llm_config=llm_config.to_autogen_config(),
    )
    print(f"   Agent Name: {agent.name}")
    print(f"   Model: {agent.model}")

    # 测试生成回复
    print("\n3. 测试生成回复...")
    messages = [
        {"role": "user", "content": "请用一句话介绍你自己"}
    ]

    try:
        reply = agent.generate_reply(messages)
        print(f"   ✅ 成功! 回复: {reply[:100]}...")
        return True
    except Exception as e:
        print(f"   ❌ 失败! 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_conversable_agent()
    sys.exit(0 if success else 1)
