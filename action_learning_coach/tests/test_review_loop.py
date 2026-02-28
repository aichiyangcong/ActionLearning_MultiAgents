"""
[INPUT]: 依赖 pytest，依赖 main 模块的审查循环逻辑
[OUTPUT]: 对外提供审查循环测试用例
[POS]: tests 模块的审查循环测试，验证 Actor-Critic 模式
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from action_learning_coach.core import get_llm_config
from action_learning_coach.agents import WIALMasterCoach, StrictEvaluator
from action_learning_coach.main import ConversationHistory


# ============================================================
# Test Fixtures
# ============================================================
@pytest.fixture
def llm_config():
    """获取 LLM 配置"""
    try:
        return get_llm_config()
    except ValueError:
        pytest.skip("OPENAI_API_KEY not found")


@pytest.fixture
def coach(llm_config):
    """创建 Coach 实例"""
    return WIALMasterCoach(llm_config)


@pytest.fixture
def evaluator(llm_config):
    """创建 Evaluator 实例"""
    return StrictEvaluator(llm_config)


# ============================================================
# 审查循环基础测试
# ============================================================
class TestReviewLoop:
    """测试审查循环的基本功能"""

    def test_max_rounds_limit_mock(self):
        """Mock 测试: 最大轮次限制"""
        max_rounds = 5
        current_round = 0

        # 模拟审查循环
        for i in range(10):
            current_round += 1
            if current_round >= max_rounds:
                break

        assert current_round == max_rounds, f"应该在第 {max_rounds} 轮停止"

    def test_pass_threshold_mock(self):
        """Mock 测试: 通过阈值"""
        pass_threshold = 95
        scores = [68, 85, 96]

        passed_scores = [s for s in scores if s >= pass_threshold]
        assert len(passed_scores) == 1, "只有 96 分应该通过"
        assert passed_scores[0] == 96, "96 分应该通过"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_review_loop_basic_flow(self, coach, evaluator):
        """真实测试: 基本审查流程"""
        user_input = "团队效率低"
        max_rounds = 5
        pass_threshold = 95

        final_question = ""
        final_score = 0

        for round_num in range(1, max_rounds + 1):
            # Coach 生成问题
            coach_result = coach.generate_question(user_input)
            question = coach_result.get("question", "")

            if not question:
                continue

            # Evaluator 审查
            eval_result = evaluator.evaluate(question)
            score = eval_result.get("score", 0)
            passed = eval_result.get("pass", False)

            if passed:
                final_question = question
                final_score = score
                break

            # 更新输入加入反馈
            feedback = eval_result.get("feedback", "")
            user_input = f"{user_input}\n\n上一轮问题: {question}\n评分: {score}/100\n反馈: {feedback}"

        # 验证结果
        assert final_question != "", "应该生成最终问题"
        assert final_score >= 0, "应该有最终评分"


# ============================================================
# 审查循环质量测试
# ============================================================
class TestReviewLoopQuality:
    """测试审查循环的质量保证"""

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_review_improves_quality(self, coach, evaluator):
        """真实测试: 审查应该提升问题质量"""
        user_input = "团队协作问题"
        scores = []

        for round_num in range(1, 4):  # 测试 3 轮
            coach_result = coach.generate_question(user_input)
            question = coach_result.get("question", "")

            if not question:
                break

            eval_result = evaluator.evaluate(question)
            score = eval_result.get("score", 0)
            scores.append(score)

            if eval_result.get("pass", False):
                break

            # 加入反馈
            feedback = eval_result.get("feedback", "")
            user_input = f"{user_input}\n\n反馈: {feedback}"

        # 验证质量提升趋势（至少不应该下降）
        if len(scores) >= 2:
            # 允许偶尔波动，但整体趋势应该向上
            assert scores[-1] >= scores[0] - 10, "质量不应显著下降"

    def test_conversation_history_mock(self):
        """Mock 测试: 对话历史记录"""
        history = ConversationHistory()

        # 添加记录
        history.add(
            user_input="测试输入",
            final_question="测试问题？",
            review_rounds=3,
            final_score=96
        )

        assert len(history.records) == 1, "应该有 1 条记录"
        assert history.records[0].user_input == "测试输入", "用户输入应正确"
        assert history.records[0].final_score == 96, "评分应正确"


# ============================================================
# 审查循环边界测试
# ============================================================
class TestReviewLoopEdgeCases:
    """测试审查循环的边界情况"""

    def test_first_round_pass_mock(self):
        """Mock 测试: 第一轮就通过"""
        score = 96
        pass_threshold = 95
        round_num = 1

        assert score >= pass_threshold, "第一轮就应该通过"
        assert round_num == 1, "应该只用 1 轮"

    def test_max_rounds_not_pass_mock(self):
        """Mock 测试: 达到最大轮次仍未通过"""
        max_rounds = 5
        scores = [68, 75, 82, 88, 92]  # 都未达到 95
        pass_threshold = 95

        best_score = max(scores)
        passed = best_score >= pass_threshold

        assert not passed, "应该未通过"
        assert len(scores) == max_rounds, "应该执行了最大轮次"
        assert best_score == 92, "应该输出最佳版本"

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_empty_input_handling(self, coach, evaluator):
        """真实测试: 空输入处理"""
        user_input = ""

        # Coach 应该能处理空输入
        coach_result = coach.generate_question(user_input)
        assert isinstance(coach_result, dict), "应返回有效结构"

        # Evaluator 应该能处理空问题
        eval_result = evaluator.evaluate("")
        assert isinstance(eval_result, dict), "应返回有效结构"
        assert not eval_result.get("pass", True), "空问题不应通过"


# ============================================================
# 性能测试
# ============================================================
class TestPerformance:
    """测试性能指标"""

    @pytest.mark.skipif(
        os.getenv("OPENAI_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_single_round_time(self, coach, evaluator):
        """真实测试: 单轮审查时间"""
        import time

        user_input = "团队效率问题"

        start_time = time.time()

        # Coach 生成
        coach_result = coach.generate_question(user_input)
        question = coach_result.get("question", "")

        # Evaluator 审查
        eval_result = evaluator.evaluate(question)

        end_time = time.time()
        duration = end_time - start_time

        # 单轮应该 <10s (宽松标准，考虑网络延迟)
        assert duration < 10, f"单轮审查时间过长: {duration:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
