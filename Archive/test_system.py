#!/usr/bin/env python3
"""
非交互式测试 - 测试 Coach 和 Evaluator 的基本功能
"""

import sys
import os

# 切换到项目目录
os.chdir("/Users/zhaoziwei/Desktop/关系行动/action_learning_coach")
sys.path.insert(0, "/Users/zhaoziwei/Desktop/关系行动/action_learning_coach")

from core.config import get_llm_config
from agents.master_coach import WIALMasterCoach
from agents.evaluator import StrictEvaluator

def test_coach():
    """测试 Coach 生成问题"""
    print("=" * 60)
    print("测试 WIAL Master Coach")
    print("=" * 60)

    # 初始化
    print("\n1. 初始化 Coach...")
    config = get_llm_config("coach")
    coach = WIALMasterCoach(config)
    print(f"   ✅ Model: {config.model}")

    # 生成问题
    print("\n2. 生成问题...")
    user_input = "我们团队最近在项目交付上总是延期，大家都很焦虑"

    try:
        result = coach.generate_question(user_input)
        print(f"   ✅ 成功!")
        print(f"\n   Question:\n   {result.get('question', 'N/A')}")
        print(f"\n   Reasoning:\n   {result.get('reasoning', 'N/A')[:200]}...")
        return result
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_evaluator(user_input, question):
    """测试 Evaluator 评分"""
    print("\n" + "=" * 60)
    print("测试 Strict Evaluator")
    print("=" * 60)

    # 初始化
    print("\n1. 初始化 Evaluator...")
    config = get_llm_config("evaluator")
    evaluator = StrictEvaluator(config)
    print(f"   ✅ Model: {config.model}")

    # 评分 - 使用正确的方法名
    print("\n2. 评分...")
    try:
        result = evaluator.evaluate(question)
        print(f"   ✅ 成功!")
        print(f"\n   Total Score: {result.get('score', 0)}/100")
        print(f"   Pass: {result.get('pass', False)}")
        print(f"\n   Feedback:\n   {result.get('feedback', 'N/A')}")
        return result
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # 测试 Coach
    coach_result = test_coach()

    if coach_result:
        # 测试 Evaluator
        user_input = "我们团队最近在项目交付上总是延期，大家都很焦虑"
        question = coach_result.get('question', '')
        eval_result = test_evaluator(user_input, question)

        # 总结
        print("\n" + "=" * 60)
        if coach_result and eval_result:
            print("✅ 所有测试通过!")
        else:
            print("❌ 部分测试失败")
        print("=" * 60)
