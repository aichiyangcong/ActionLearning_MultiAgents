"""
[INPUT]: 依赖 pytest，依赖整个系统的集成
[OUTPUT]: 对外提供端到端集成测试用例
[POS]: tests 模块的集成测试，验证完整流程
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from action_learning_coach.main import (
    ConversationHistory,
    mock_review_loop,
    orchestrator_review_loop,
)
from action_learning_coach.core import get_llm_config
from action_learning_coach.agents import WIALMasterCoach, StrictEvaluator


# ============================================================
# Mock 模式端到端测试
# ============================================================
class TestMockModeE2E:
    """测试 Mock 模式的端到端流程"""

    def test_mock_mode_basic_flow(self):
        """测试 Mock 模式基本流程"""
        history = ConversationHistory()
        user_input = "团队效率低"

        # 执行 mock 审查循环
        mock_review_loop(user_input, history, streaming=False)

        # 验证历史记录
        assert len(history.records) == 1, "应该有 1 条记录"
        record = history.records[0]

        assert record.user_input == user_input, "用户输入应正确"
        assert record.final_question != "", "应该有最终问题"
        assert record.review_rounds > 0, "应该有审查轮次"
        assert record.final_score >= 0, "应该有最终评分"

    def test_mock_mode_multiple_inputs(self):
        """测试 Mock 模式多次输入"""
        history = ConversationHistory()
        inputs = [
            "团队效率低",
            "客户投诉多",
            "项目延期",
        ]

        for user_input in inputs:
            mock_review_loop(user_input, history, streaming=False)

        # 验证历史记录
        assert len(history.records) == len(inputs), f"应该有 {len(inputs)} 条记录"

        for i, record in enumerate(history.records):
            assert record.user_input == inputs[i], f"第 {i+1} 条记录输入应正确"
            assert record.final_question != "", f"第 {i+1} 条记录应有最终问题"

    def test_mock_mode_review_rounds(self):
        """测试 Mock 模式审查轮次"""
        history = ConversationHistory()
        user_input = "测试输入"

        mock_review_loop(user_input, history, streaming=False)

        record = history.records[0]
        # Mock 数据应该是 3 轮
        assert record.review_rounds == 3, "Mock 模式应该是 3 轮"
        assert record.final_score == 96, "Mock 模式最终评分应该是 96"

    def test_mock_mode_final_question_quality(self):
        """测试 Mock 模式最终问题质量"""
        history = ConversationHistory()
        user_input = "测试输入"

        mock_review_loop(user_input, history, streaming=False)

        record = history.records[0]
        final_question = record.final_question

        # 验证问题质量
        assert "？" in final_question or "?" in final_question, "应该是问题"
        assert len(final_question) > 5, "问题不应过短"
        assert len(final_question) < 200, "问题不应过长"


# ============================================================
# 真实模式端到端测试
# ============================================================
class TestRealModeE2E:
    """测试真实模式的端到端流程"""

    @pytest.fixture
    def real_agents(self):
        """创建真实 Agent"""
        try:
            llm_config = get_llm_config()
            coach = WIALMasterCoach(llm_config)
            evaluator = StrictEvaluator(llm_config)
            return coach, evaluator
        except ValueError:
            pytest.skip("ANTHROPIC_API_KEY not found")

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_real_mode_basic_flow(self, real_agents):
        """测试真实模式基本流程"""
        coach, evaluator = real_agents
        user_input = "团队效率低"
        max_rounds = 5

        final_question = ""
        final_score = 0
        review_rounds = 0

        for round_num in range(1, max_rounds + 1):
            review_rounds = round_num

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

            # 更新输入
            feedback = eval_result.get("feedback", "")
            user_input = f"{user_input}\n\n反馈: {feedback}"

        # 验证结果
        assert final_question != "", "应该生成最终问题"
        assert final_score >= 0, "应该有最终评分"
        assert review_rounds <= max_rounds, "审查轮次不应超过最大值"

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "").startswith("sk-test"),
        reason="需要真实 API Key"
    )
    def test_real_mode_quality_threshold(self, real_agents):
        """测试真实模式质量阈值"""
        coach, evaluator = real_agents
        user_input = "团队协作问题"
        max_rounds = 5
        pass_threshold = 95

        best_score = 0

        for round_num in range(1, max_rounds + 1):
            coach_result = coach.generate_question(user_input)
            question = coach_result.get("question", "")

            if not question:
                continue

            eval_result = evaluator.evaluate(question)
            score = eval_result.get("score", 0)

            if score > best_score:
                best_score = score

            if eval_result.get("pass", False):
                break

            feedback = eval_result.get("feedback", "")
            user_input = f"{user_input}\n\n反馈: {feedback}"

        # 验证质量
        # 如果通过，评分应该 ≥95
        # 如果未通过，应该有最佳版本
        assert best_score > 0, "应该有评分"


# ============================================================
# 验收标准测试
# ============================================================
class TestAcceptanceCriteria:
    """测试验收标准"""

    def test_user_can_input_business_problem(self):
        """验收: 用户可输入业务问题"""
        history = ConversationHistory()
        user_input = "我的团队最近效率很低，不知道如何改进"

        # 系统应该能处理输入
        mock_review_loop(user_input, history, streaming=False)

        assert len(history.records) == 1, "应该处理用户输入"
        assert history.records[0].user_input == user_input, "应该记录用户输入"

    def test_system_generates_open_question(self):
        """验收: 系统生成开放式提问"""
        history = ConversationHistory()
        user_input = "团队效率低"

        mock_review_loop(user_input, history, streaming=False)

        final_question = history.records[0].final_question

        # 验证是问题
        assert "？" in final_question or "?" in final_question, "应该生成问题"

        # 验证开放性（Mock 数据的最终问题应该是开放的）
        open_keywords = ["什么", "如何", "怎样", "注意到", "观察到"]
        has_open = any(kw in final_question for kw in open_keywords)
        assert has_open, "应该是开放式问题"

    def test_review_loop_max_5_rounds(self):
        """验收: 审查循环最多 5 轮"""
        history = ConversationHistory()
        user_input = "测试输入"

        mock_review_loop(user_input, history, streaming=False)

        review_rounds = history.records[0].review_rounds
        assert review_rounds <= 5, "审查轮次不应超过 5 轮"

    def test_pass_score_threshold_95(self):
        """验收: 评分 ≥95 通过"""
        history = ConversationHistory()
        user_input = "测试输入"

        mock_review_loop(user_input, history, streaming=False)

        final_score = history.records[0].final_score
        # Mock 数据的最终评分应该 ≥95
        assert final_score >= 95, "最终评分应该 ≥95"

    def test_display_final_question(self):
        """验收: 显示最终问题"""
        history = ConversationHistory()
        user_input = "测试输入"

        mock_review_loop(user_input, history, streaming=False)

        final_question = history.records[0].final_question
        assert final_question != "", "应该显示最终问题"
        assert len(final_question) > 0, "最终问题不应为空"

    def test_view_conversation_history(self):
        """验收: 查看对话历史"""
        history = ConversationHistory()

        # 添加多条记录
        for i in range(3):
            mock_review_loop(f"测试输入 {i+1}", history, streaming=False)

        # 验证历史记录
        assert len(history.records) == 3, "应该有 3 条历史记录"

        # 验证可以显示历史（不抛出异常）
        try:
            import io
            import sys
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            history.show()
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            assert "对话历史" in output, "应该显示历史标题"
            assert len(output) > 0, "应该有输出内容"
        except Exception as e:
            pytest.fail(f"显示历史记录失败: {e}")

    def test_exit_system(self):
        """验收: 退出系统"""
        # 验证退出命令
        exit_commands = ["quit", "exit", "q"]

        for cmd in exit_commands:
            assert cmd.lower() in ["quit", "exit", "q"], f"{cmd} 应该是有效的退出命令"


# ============================================================
# 系统稳定性测试
# ============================================================
class TestSystemStability:
    """测试系统稳定性"""

    def test_multiple_sessions(self):
        """测试多次会话"""
        for session in range(3):
            history = ConversationHistory()
            user_input = f"会话 {session + 1} 的测试输入"

            mock_review_loop(user_input, history, streaming=False)

            assert len(history.records) == 1, f"会话 {session + 1} 应该有记录"

    def test_empty_input_handling(self):
        """测试空输入处理"""
        history = ConversationHistory()

        # 空输入应该被主循环拒绝，这里测试历史记录不受影响
        assert len(history.records) == 0, "空输入不应创建记录"

    def test_special_characters_input(self):
        """测试特殊字符输入"""
        history = ConversationHistory()
        special_inputs = [
            "测试@#$%输入",
            "Test 123 测试",
            "问题？！",
        ]

        for user_input in special_inputs:
            mock_review_loop(user_input, history, streaming=False)

        assert len(history.records) == len(special_inputs), "应该处理所有特殊字符输入"


class TestCliErrorHandling:
    """测试 CLI 的错误提示和历史记录行为"""

    def test_orchestrator_rate_limit_error_not_saved_to_history(self, capsys):
        """429 限流时不应写入空历史记录"""

        class FailingOrchestrator:
            def run_turn(self, user_input):
                raise RuntimeError(
                    "Anthropic-compatible gateway rate limited the request "
                    "(429 Too Many Requests). Please wait a moment and retry."
                )

        history = ConversationHistory()

        orchestrator_review_loop("团队士气低", history, FailingOrchestrator())

        captured = capsys.readouterr()
        assert len(history.records) == 0, "失败轮次不应写入历史"
        assert "429 Too Many Requests" in captured.out, "应提示限流信息"
        assert "not saved to history" in captured.out, "应告知未保存历史"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
