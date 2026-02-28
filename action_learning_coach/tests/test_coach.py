"""
[INPUT]: 依赖 pytest，依赖 agents/master_coach 的 WIALMasterCoach
[OUTPUT]: 对外提供 Coach 生成问题测试用例
[POS]: tests 模块的 Coach 测试，验证问题生成质量
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from action_learning_coach.core import get_llm_config
from action_learning_coach.agents import WIALMasterCoach


# ============================================================
# Test Fixtures
# ============================================================
@pytest.fixture
def coach():
    """创建 Coach 实例"""
    try:
        llm_config = get_llm_config()
        return WIALMasterCoach(llm_config)
    except ValueError:
        pytest.skip("OPENAI_API_KEY not found, skipping real LLM tests")


# ============================================================
# 问题生成测试
# ============================================================
class TestQuestionGeneration:
    """测试 Coach 生成问题的能力"""

    TEST_INPUTS = [
        "我的团队最近效率很低，不知道如何改进",
        "客户投诉率上升了20%",
        "新产品上线后用户留存率下降",
        "团队成员之间沟通不畅",
        "项目进度总是延期",
    ]

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_generate_question_returns_valid_structure(self, coach):
        """测试生成的问题结构"""
        user_input = self.TEST_INPUTS[0]
        result = coach.generate_question(user_input)

        # 验证返回结构
        assert isinstance(result, dict), "返回值应该是字典"
        assert "question" in result, "结果应包含 question 字段"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_generate_question_not_empty(self, coach):
        """测试生成的问题不为空"""
        user_input = self.TEST_INPUTS[0]
        result = coach.generate_question(user_input)

        question = result.get("question", "")
        assert len(question) > 0, "生成的问题不应为空"
        assert len(question) < 500, "生成的问题不应过长"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_generate_question_is_question(self, coach):
        """测试生成的是问题（包含问号）"""
        user_input = self.TEST_INPUTS[0]
        result = coach.generate_question(user_input)

        question = result.get("question", "")
        assert "？" in question or "?" in question, "生成的内容应该是问题"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_generate_multiple_questions(self, coach):
        """测试生成多个问题"""
        for user_input in self.TEST_INPUTS[:3]:
            result = coach.generate_question(user_input)
            question = result.get("question", "")
            assert len(question) > 0, f"输入 '{user_input}' 应生成有效问题"


# ============================================================
# 问题质量测试
# ============================================================
class TestQuestionQuality:
    """测试生成问题的质量"""

    def test_question_should_be_open_ended_mock(self):
        """Mock 测试: 问题应该是开放式的"""
        # 开放式问题特征
        open_keywords = ["什么", "如何", "怎样", "为什么", "哪些"]
        closed_keywords = ["是不是", "能不能", "对吗", "好吗"]

        # 模拟一个好问题
        good_question = "在这个情境中，你观察到了什么？"
        assert any(kw in good_question for kw in open_keywords), "应包含开放式关键词"
        assert not any(kw in good_question for kw in closed_keywords), "不应包含封闭式关键词"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_question_avoids_leading_words(self, coach):
        """测试生成的问题避免诱导性词汇"""
        user_input = "团队效率低"
        result = coach.generate_question(user_input)
        question = result.get("question", "")

        # 诱导性词汇
        leading_words = ["应该", "必须", "一定", "肯定", "显然"]
        has_leading = any(word in question for word in leading_words)

        assert not has_leading, f"问题不应包含诱导性词汇: {question}"


# ============================================================
# 错误处理测试
# ============================================================
class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_empty_input(self, coach):
        """测试空输入"""
        result = coach.generate_question("")
        # 应该返回有效结构，即使输入为空
        assert isinstance(result, dict), "即使输入为空，也应返回字典"
        assert "question" in result, "应包含 question 字段"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_very_long_input(self, coach):
        """测试超长输入"""
        long_input = "问题" * 500
        result = coach.generate_question(long_input)
        # 应该能处理超长输入
        assert isinstance(result, dict), "应能处理超长输入"
        assert "question" in result, "应包含 question 字段"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
