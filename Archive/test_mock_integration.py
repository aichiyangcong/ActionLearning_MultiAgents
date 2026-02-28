#!/usr/bin/env python3
"""
Mock 模式集成测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from action_learning_coach.main import (
    ConversationHistory,
    mock_review_loop,
    print_header,
)


def test_mock_mode():
    """测试 Mock 模式的完整流程"""
    print("=" * 70)
    print("Mock 模式集成测试".center(70))
    print("=" * 70)

    history = ConversationHistory()

    # 测试用例 1: 正常输入
    print("\n[测试 1] 正常业务问题输入")
    user_input = "我的团队最近效率很低，不知道如何改进"
    mock_review_loop(user_input, history, streaming=False)

    # 测试用例 2: 短输入
    print("\n\n[测试 2] 短输入")
    user_input = "团队协作问题"
    mock_review_loop(user_input, history, streaming=False)

    # 验证历史记录
    print("\n\n[测试 3] 历史记录验证")
    history.show()

    print("\n" + "=" * 70)
    print("✅ Mock 模式集成测试完成".center(70))
    print("=" * 70)


if __name__ == "__main__":
    test_mock_mode()
