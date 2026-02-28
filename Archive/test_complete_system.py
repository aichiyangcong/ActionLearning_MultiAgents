#!/usr/bin/env python3
"""
测试完整的 Coach + Evaluator 系统
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.join(os.path.dirname(__file__), "action_learning_coach")
sys.path.insert(0, project_root)

# 修改工作目录以支持相对导入
os.chdir(project_root)

from action_learning_coach.core.config import get_llm_config
from action_learning_coach.agents.master_coach import WIALMasterCoach
from action_learning_coach.agents.evaluator import StrictEvaluator

def test_complete_system():
    """测试完整的 Coach + Evaluator 系统"""
    print("=" * 60)
    print("测试 Action Learning Coach 完整系统")
    print("=" * 60)

    # 1. 初始化 Coach
    print("\n1. 初始化 WIAL Master Coach...")
    coach_config = get_llm_config("coach")
    coach = WIALMasterCoach(coach_config)
    print(f"   ✅ Coach 已创建 (Model: {coach_config.model})")

    # 2. 初始化 Evaluator
    print("\n2. 初始化 Strict Evaluator...")
    evaluator_config = get_llm_config("evaluator")
    evaluator = StrictEvaluator(evaluator_config)
    print(f"   ✅ Evaluator 已创建 (Model: {evaluator_config.model})")

    # 3. 测试 Coach 生成问题
    print("\n3. 测试 Coach 生成问题...")
    user_input = "我们团队最近在项目交付上总是延期，大家都很焦虑"

    try:
        result = coach.generate_question(user_input)
        print(f"   ✅ 成功生成问题!")
        print(f"   Question: {result.get('question', 'N/A')[:100]}...")
        print(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}...")

        # 4. 测试 Evaluator 评分
        print("\n4. 测试 Evaluator 评分...")
        evaluation = evaluator.evaluate_question(
            user_input=user_input,
            generated_question=result.get('question', '')
        )
        print(f"   ✅ 成功评分!")
        print(f"   Total Score: {evaluation.get('total_score', 0)}")
        print(f"   Pass: {evaluation.get('pass', False)}")
        print(f"   Feedback: {evaluation.get('feedback', 'N/A')[:100]}...")

        return True

    except Exception as e:
        print(f"   ❌ 失败! 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_system()
    print("\n" + "=" * 60)
    print(f"测试结果: {'✅ 通过' if success else '❌ 失败'}")
    print("=" * 60)
    sys.exit(0 if success else 1)
