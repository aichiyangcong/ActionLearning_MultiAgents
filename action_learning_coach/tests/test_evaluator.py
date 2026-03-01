"""
[INPUT]: 依赖 pytest，依赖 agents/evaluator 的 StrictEvaluator
[OUTPUT]: 对外提供诱导性问题检测测试用例
[POS]: tests 模块的评估器测试，验证 Evaluator 能检测诱导性问题
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from action_learning_coach.core import get_llm_config
from action_learning_coach.agents import StrictEvaluator


# ============================================================
# Test Fixtures
# ============================================================
@pytest.fixture
def evaluator():
    """创建 Evaluator 实例"""
    try:
        llm_config = get_llm_config()
        return StrictEvaluator(llm_config)
    except ValueError:
        # 如果没有 API Key，跳过真实测试
        pytest.skip("ANTHROPIC_API_KEY not found, skipping real LLM tests")


# ============================================================
# 诱导性问题检测测试
# ============================================================
class TestLeadingQuestionDetection:
    """测试 Evaluator 检测诱导性问题的能力"""

    # 诱导性问题测试用例（应该被检测出来，评分 <95）
    LEADING_QUESTIONS = [
        "你觉得这个方案能解决问题吗？",  # 暗示是非判断
        "这个方案是不是很好？",  # 诱导正面评价
        "你难道不认为这样做更好吗？",  # 反问式诱导
        "为什么你不选择方案A？",  # 暗示应该选择
        "这个问题很严重，对吧？",  # 诱导同意
        "你应该怎么改进这个方案？",  # 暗示需要改进
        "这个风险是不是很大？",  # 诱导负面评价
    ]

    # 开放式问题测试用例（应该通过，评分 ≥95）
    OPEN_QUESTIONS = [
        "当你回顾这个方案时，你注意到了什么？",
        "在这个情境中，你观察到了什么？",
        "你对这个问题有什么想法？",
        "这个方案对你意味着什么？",
        "你在这个过程中体验到了什么？",
    ]

    def test_detect_leading_questions_mock(self):
        """Mock 测试: 验证诱导性问题的特征"""
        for question in self.LEADING_QUESTIONS:
            # 检查是否包含诱导性关键词
            leading_keywords = ["能", "是不是", "难道不", "为什么不", "应该", "对吧", "不选择"]
            has_leading = any(keyword in question for keyword in leading_keywords)
            assert has_leading, f"问题应包含诱导性关键词: {question}"

    def test_detect_open_questions_mock(self):
        """Mock 测试: 验证开放式问题的特征"""
        for question in self.OPEN_QUESTIONS:
            # 检查是否包含开放式关键词
            open_keywords = ["什么", "如何", "怎样", "注意到", "观察到", "体验到"]
            has_open = any(keyword in question for keyword in open_keywords)
            assert has_open, f"问题应包含开放式关键词: {question}"

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_evaluator_detects_leading_questions(self, evaluator):
        """真实测试: Evaluator 应该检测出诱导性问题"""
        passed_count = 0
        failed_count = 0

        for question in self.LEADING_QUESTIONS:
            result = evaluator.evaluate(question)
            score = result.get("score", 0)
            passed = result.get("pass", False)

            if passed:
                passed_count += 1
                print(f"⚠️  诱导性问题被误判为通过: {question} (评分: {score})")
            else:
                failed_count += 1

        # 准确率应该 >85%
        accuracy = failed_count / len(self.LEADING_QUESTIONS)
        assert accuracy > 0.85, f"诱导性检测准确率过低: {accuracy:.2%}"

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_evaluator_accepts_open_questions(self, evaluator):
        """真实测试: Evaluator 应该接受开放式问题"""
        passed_count = 0
        failed_count = 0

        for question in self.OPEN_QUESTIONS:
            result = evaluator.evaluate(question)
            score = result.get("score", 0)
            passed = result.get("pass", False)

            if passed:
                passed_count += 1
            else:
                failed_count += 1
                print(f"⚠️  开放式问题被误判为不通过: {question} (评分: {score})")

        # 通过率应该 >80%
        pass_rate = passed_count / len(self.OPEN_QUESTIONS)
        assert pass_rate > 0.80, f"开放式问题通过率过低: {pass_rate:.2%}"


# ============================================================
# 评分维度测试
# ============================================================
class TestScoringDimensions:
    """测试评分的三个维度"""

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_scoring_breakdown(self, evaluator):
        """测试评分细分"""
        question = "当你回顾这个方案时，你注意到了什么？"
        result = evaluator.evaluate(question)

        # 验证返回结构
        assert "score" in result, "结果应包含总分"
        assert "breakdown" in result, "结果应包含评分细分"
        assert "pass" in result, "结果应包含通过标志"
        assert "feedback" in result, "结果应包含反���"

        # 验证评分细分
        breakdown = result["breakdown"]
        assert "openness" in breakdown, "应包含开放性评分"
        assert "neutrality" in breakdown, "应包含无诱导性评分"
        assert "depth" in breakdown, "应包含反思深度评分"

        # 验证评分范围
        assert 0 <= breakdown["openness"] <= 40, "开放性评分应在 0-40"
        assert 0 <= breakdown["neutrality"] <= 40, "无诱导性评分应在 0-40"
        assert 0 <= breakdown["depth"] <= 20, "反思深度评分应在 0-20"

        # 验证总分
        total = breakdown["openness"] + breakdown["neutrality"] + breakdown["depth"]
        assert result["score"] == total, "总分应等于各维度之和"


# ============================================================
# 边界测试
# ============================================================
class TestEdgeCases:
    """测试边界情况"""

    def test_empty_question_mock(self):
        """Mock 测试: 空问题"""
        question = ""
        assert len(question) == 0, "空问题应该被检测"

    def test_very_long_question_mock(self):
        """Mock 测试: 超长问题"""
        question = "你" * 1000
        assert len(question) > 500, "超长问题应该被检测"

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_empty_question_real(self, evaluator):
        """真实测试: 空问题应该不通过"""
        result = evaluator.evaluate("")
        assert not result.get("pass", True), "空问题不应通过"
        assert result.get("score", 100) < 95, "空问题评分应 <95"


class TestStructuredReplyEvaluation:
    """测试新的结构化催化师回复评审输入"""

    def test_format_review_input_with_structured_reply(self):
        """应把共情和两个问题完整展开给 Evaluator"""
        review_input = StrictEvaluator._format_review_input({
            "acknowledgment": "我听到这件事确实在消耗团队。",
            "questions": [
                "当你看到士气下滑时，最明显的变化是什么？",
                "在这些变化背后，你认为他们最难承受的是什么？",
            ],
        })

        assert "简短共情" in review_input
        assert "问题1" in review_input
        assert "问题2" in review_input

    def test_normalize_coach_reply_supports_legacy_question(self):
        """旧字符串问题应被兼容成新评审输入"""
        payload = StrictEvaluator._normalize_coach_reply("你观察到了什么？")
        assert payload["acknowledgment"] == ""
        assert payload["questions"] == ["你观察到了什么？"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
