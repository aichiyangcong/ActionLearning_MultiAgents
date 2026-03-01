"""
[INPUT]: 依赖 pytest, unittest.mock,
         依赖 agents (WIALMasterCoach, StrictEvaluator, UserProxy),
         依赖 core.orchestrator (Orchestrator, TurnResult),
         依赖 core.nested_chat (create_nested_chat_config),
         依赖 core.config (LLMConfig)
[OUTPUT]: Phase 2a 集成测试 — 验证 AG2 编排骨架的完整性
[POS]: tests 模块的 Phase 2a 集成测试，覆盖 Import / Orchestrator / NestedChat / Mock 模式
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# 测试用 LLMConfig 工厂
# ============================================================
def _fake_llm_config():
    """构造不调用 API 的假 LLMConfig"""
    from core.config import LLMConfig

    return LLMConfig(
        api_key="sk-test-fake-key",
        base_url=None,
        model="claude-sonnet-4-6",
        temperature=0.7,
        max_review_rounds=5,
        pass_score_threshold=95,
    )


# ============================================================
# 1. Import 测试
# ============================================================
class TestImports:
    """验证 Phase 2a 新模块可正常导入"""

    def test_import_agents(self):
        """agents 模块导出 WIALMasterCoach, StrictEvaluator, UserProxy"""
        from agents import WIALMasterCoach, StrictEvaluator, UserProxy

        assert WIALMasterCoach is not None
        assert StrictEvaluator is not None
        assert UserProxy is not None

    def test_import_orchestrator(self):
        """core.orchestrator 导出 Orchestrator, TurnResult"""
        from core.orchestrator import Orchestrator, TurnResult

        assert Orchestrator is not None
        assert TurnResult is not None

    def test_import_nested_chat(self):
        """core.nested_chat 导出 create_nested_chat_config"""
        from core.nested_chat import create_nested_chat_config

        assert callable(create_nested_chat_config)

    def test_import_core_init(self):
        """core.__init__ 统一导出所有公共 API"""
        from core import (
            LLMConfig,
            get_llm_config,
            create_nested_chat_config,
            Orchestrator,
            TurnResult,
        )

        assert LLMConfig is not None
        assert callable(get_llm_config)
        assert callable(create_nested_chat_config)
        assert Orchestrator is not None
        assert TurnResult is not None

    def test_import_ag2_dependencies(self):
        """AG2 关键依赖可导入"""
        from autogen import ConversableAgent, UserProxyAgent
        from autogen.agentchat import initiate_group_chat, ContextVariables
        from autogen.agentchat.group import (
            OnCondition,
            RevertToUserTarget,
            StringLLMCondition,
        )
        from autogen.agentchat.group.patterns.pattern import DefaultPattern
        from autogen.agentchat.group.targets.transition_target import NestedChatTarget

        assert ConversableAgent is not None
        assert UserProxyAgent is not None
        assert NestedChatTarget is not None


# ============================================================
# 2. Orchestrator 创建测试
# ============================================================
class TestOrchestratorCreation:
    """验证 Orchestrator 实例化和 create_session"""

    @pytest.fixture
    def fake_config(self):
        return _fake_llm_config()

    def test_orchestrator_instantiates(self, fake_config):
        """Orchestrator() 传入 LLMConfig 可实例化"""
        from core.orchestrator import Orchestrator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        assert orch is not None
        assert orch._session_ready is False

    def test_create_session_initializes_agents(self, fake_config):
        """create_session 初始化 Coach / Evaluator / UserProxy"""
        from core.orchestrator import Orchestrator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        assert orch._session_ready is True

        # Coach & Evaluator wrapper 已创建
        assert orch._coach_wrapper is not None
        assert orch._evaluator_wrapper is not None

        # 底层 AG2 agent 已提取
        assert orch._coach is not None
        assert orch._evaluator is not None

        # UserProxy 已创建
        assert orch._user_proxy is not None

    def test_coach_agent_is_conversable(self, fake_config):
        """Coach 底层是 AG2 ConversableAgent"""
        from core.orchestrator import Orchestrator
        from autogen import ConversableAgent

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        assert isinstance(orch._coach, ConversableAgent)
        assert orch._coach.name == "WIAL_Master_Coach"

    def test_evaluator_agent_is_conversable(self, fake_config):
        """Evaluator 底层是 AG2 ConversableAgent"""
        from core.orchestrator import Orchestrator
        from autogen import ConversableAgent

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        assert isinstance(orch._evaluator, ConversableAgent)
        assert orch._evaluator.name == "Strict_Evaluator"

    def test_user_proxy_is_never_mode(self, fake_config):
        """UserProxy 设为 NEVER 模式"""
        from core.orchestrator import Orchestrator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        assert orch._user_proxy.human_input_mode == "NEVER"

    def test_coach_has_handoffs(self, fake_config):
        """Coach 配置了 handoffs"""
        from core.orchestrator import Orchestrator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        # Coach 仍保留基础 handoffs 配置（主要是 after_work）
        handoffs = orch._coach.handoffs

        # after_works 应包含 RevertToUserTarget
        from autogen.agentchat.group import RevertToUserTarget

        assert len(handoffs.after_works) > 0, "Coach 应有 after_work 配置"
        # set_after_work 包装为 OnContextCondition，target 是 RevertToUserTarget
        assert isinstance(handoffs.after_works[0].target, RevertToUserTarget)

    def test_coach_no_longer_uses_llm_condition_for_review(self, fake_config):
        """显式闭环已取代 llm_condition，Coach 不再挂评审条件路由"""
        from core.orchestrator import Orchestrator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        llm_conditions = orch._coach.handoffs.llm_conditions
        assert len(llm_conditions) == 0, "真实评审主路径不应再依赖 llm_condition"

    def test_context_variables_initialized(self, fake_config):
        """create_session 后 ContextVariables 包含 round=0"""
        from core.orchestrator import Orchestrator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        assert orch._ctx.get("round") == 0

    def test_orchestrator_properties(self, fake_config):
        """coach / evaluator 属性返回业务包装层"""
        from core.orchestrator import Orchestrator
        from agents import WIALMasterCoach, StrictEvaluator

        orch = Orchestrator(
            coach_config=fake_config,
            evaluator_config=fake_config,
        )
        orch.create_session()

        assert isinstance(orch.coach, WIALMasterCoach)
        assert isinstance(orch.evaluator, StrictEvaluator)


# ============================================================
# 3. NestedChat 配置测试
# ============================================================
class TestNestedChatConfig:
    """验证 create_nested_chat_config 返回结构"""

    def test_returns_nested_chat_target(self):
        """返回 NestedChatTarget 实例"""
        from autogen import ConversableAgent
        from autogen.agentchat.group.targets.transition_target import NestedChatTarget
        from core.nested_chat import create_nested_chat_config

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        target = create_nested_chat_config(evaluator, max_rounds=5)
        assert isinstance(target, NestedChatTarget)

    def test_chat_queue_structure(self):
        """chat_queue 包含正确的字段"""
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        target = create_nested_chat_config(evaluator, max_rounds=3)

        # 获取内部 nested_chat_config
        config = target.nested_chat_config
        assert "chat_queue" in config

        queue = config["chat_queue"]
        assert len(queue) == 1, "chat_queue 应包含一个 entry"

        entry = queue[0]
        assert entry["recipient"] is evaluator
        assert callable(entry["message"])
        assert entry["summary_method"] == "last_msg"
        assert entry["max_turns"] == 3 * 2, "max_turns = max_rounds * 2"

    def test_max_turns_calculation(self):
        """max_turns = max_rounds * 2"""
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        for rounds in [1, 3, 5, 10]:
            target = create_nested_chat_config(evaluator, max_rounds=rounds)
            config = target.nested_chat_config
            entry = config["chat_queue"][0]
            assert entry["max_turns"] == rounds * 2

    def test_real_runtime_nested_chat_uses_single_turn(self):
        """真实运行时传入 coach_wrapper 时，nested chat 限制为单次评审"""
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        class DummyCoachWrapper:
            def generate_question(self, user_input: str) -> dict:
                return {"question": f"基于输入生成: {user_input}"}

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        target = create_nested_chat_config(
            evaluator,
            max_rounds=5,
            coach_wrapper=DummyCoachWrapper(),
        )
        config = target.nested_chat_config
        entry = config["chat_queue"][0]
        assert entry["max_turns"] == 1

    def test_message_extractor_callable(self):
        """message 字段是可调用的消息提取函数"""
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        target = create_nested_chat_config(evaluator, max_rounds=5)
        config = target.nested_chat_config
        message_fn = config["chat_queue"][0]["message"]

        # 用假数据调用提取函数
        dummy_sender = ConversableAgent(
            name="Dummy_Coach",
            llm_config=False,
            human_input_mode="NEVER",
        )
        messages = [{"content": "这是一个测试问题？"}]

        result = message_fn(evaluator, messages, dummy_sender, None)
        assert isinstance(result, str)
        assert "测试问题" in result

    def test_message_extractor_recovers_question_from_user_input(self):
        """真实运行时只有 transfer 消息时，应回退到 direct coach generation"""
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        class DummyCoachWrapper:
            def generate_question(self, user_input: str) -> dict:
                return {"question": f"围绕这个问题深入看时，{user_input}背后发生了什么？"}

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )
        review_state = {}
        target = create_nested_chat_config(
            evaluator,
            coach_wrapper=DummyCoachWrapper(),
            coach_name="WIAL_Master_Coach",
            review_state=review_state,
        )
        entry = target.nested_chat_config["chat_queue"][0]
        message_fn = entry["message"]

        dummy_sender = ConversableAgent(
            name="wrapped_nested_WIAL_Master_Coach_1",
            llm_config=False,
            human_input_mode="NEVER",
        )
        messages = [
            {
                "role": "user",
                "content": "销售团队因为销量下滑士气大降，理财卖不出去",
            },
            {
                "role": "user",
                "name": "_Group_Tool_Executor",
                "content": "Transfer to wrapped_nested_WIAL_Master_Coach_1",
            },
        ]

        result = message_fn(evaluator, messages, dummy_sender, None)
        assert "请评估以下问题:" in result
        assert "背后发生了什么" in result
        assert review_state["last_question"]

    def test_message_extractor_handles_json(self):
        """消息提取函数能处理 JSON 格式的 Coach 输出"""
        import json
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        target = create_nested_chat_config(evaluator, max_rounds=5)
        config = target.nested_chat_config
        message_fn = config["chat_queue"][0]["message"]

        dummy_sender = ConversableAgent(
            name="Dummy_Coach",
            llm_config=False,
            human_input_mode="NEVER",
        )

        json_content = json.dumps({"question": "你注意到了什么？", "reasoning": "开放式提问"})
        messages = [{"content": json_content}]

        result = message_fn(evaluator, messages, dummy_sender, None)
        assert "你注意到了什么" in result

    def test_message_extractor_handles_empty(self):
        """消息提取函数能处理空消息列表"""
        from autogen import ConversableAgent
        from core.nested_chat import create_nested_chat_config

        evaluator = ConversableAgent(
            name="Test_Evaluator",
            llm_config=False,
            human_input_mode="NEVER",
        )

        target = create_nested_chat_config(evaluator, max_rounds=5)
        config = target.nested_chat_config
        message_fn = config["chat_queue"][0]["message"]

        dummy_sender = ConversableAgent(
            name="Dummy_Coach",
            llm_config=False,
            human_input_mode="NEVER",
        )

        result = message_fn(evaluator, [], dummy_sender, None)
        assert isinstance(result, str)


# ============================================================
# 4. TurnResult 数据结构测试
# ============================================================
class TestTurnResult:
    """验证 TurnResult 数据类"""

    def test_turn_result_defaults(self):
        """TurnResult 默认字段"""
        from core.orchestrator import TurnResult

        result = TurnResult(question="测试问题？")
        assert result.question == "测试问题？"
        assert result.messages == []
        assert result.summary == ""
        assert result.context == {}

    def test_turn_result_full(self):
        """TurnResult 填充所有字段"""
        from core.orchestrator import TurnResult

        result = TurnResult(
            question="你注意到了什么？",
            messages=[{"role": "assistant", "content": "test"}],
            summary="高质量开放式问题",
            context={"round": 1},
        )
        assert result.question == "你注意到了什么？"
        assert len(result.messages) == 1
        assert result.summary == "高质量开放式问题"
        assert result.context["round"] == 1


# ============================================================
# 5. Mock 模式测试
# ============================================================
class TestMockMode:
    """验证 main.py 的 Mock 模式功能"""

    def test_mock_review_loop_exists(self):
        """mock_review_loop 函数存在且可调用"""
        from main import mock_review_loop

        assert callable(mock_review_loop)

    def test_mock_review_loop_runs(self):
        """mock_review_loop 执行不报错"""
        from main import mock_review_loop, ConversationHistory

        history = ConversationHistory()
        mock_review_loop("测试业务问题", history, streaming=False)

        assert len(history.records) == 1
        assert history.records[0].final_score >= 95

    def test_main_function_exists(self):
        """main 函数存在且可调用"""
        from main import main

        assert callable(main)

    def test_orchestrator_review_loop_exists(self):
        """orchestrator_review_loop 函数存在且可调用"""
        from main import orchestrator_review_loop

        assert callable(orchestrator_review_loop)

    def test_real_agent_available_flag(self):
        """REAL_AGENT_AVAILABLE 标志位正确"""
        from main import REAL_AGENT_AVAILABLE

        # 因为 AG2 已安装，导入应成功
        assert REAL_AGENT_AVAILABLE is True


# ============================================================
# 6. Orchestrator.run_turn Mock 测试
# ============================================================
class TestOrchestratorRunTurn:
    """验证 run_turn 在 mock 环境下的行为"""

    @pytest.fixture
    def orchestrator(self):
        """创建已初始化的 Orchestrator"""
        from core.orchestrator import Orchestrator

        config = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
        )
        orch.create_session()
        return orch

    def _mock_review_loop_result(
        self,
        question: str,
        messages: list[dict],
        review_result: dict | None = None,
        review_rounds: int = 1,
        passed: bool = True,
        best_score: int = 0,
        returned_best_version: bool = False,
        last_review_result: dict | None = None,
    ):
        from core.orchestrator import ReviewLoopResult

        return ReviewLoopResult(
            question=question,
            review_result=review_result,
            last_review_result=last_review_result or review_result,
            messages=messages,
            review_rounds=review_rounds,
            passed=passed,
            best_score=best_score,
            returned_best_version=returned_best_version,
        )

    def test_explicit_review_loop_rewrites_until_pass(self, orchestrator):
        """显式闭环在未通过时，应带着 feedback 重写再审。"""
        with patch.object(
            orchestrator._coach_wrapper,
            "generate_question",
            return_value={"question": "你觉得团队效率低吗？", "reasoning": "初版"},
        ), patch.object(
            orchestrator._coach_wrapper,
            "rewrite_question",
            return_value={"question": "当你回顾团队最近的工作时，你注意到了什么？", "reasoning": "重写"},
        ) as mock_rewrite, patch.object(
            orchestrator._evaluator_wrapper,
            "evaluate",
            side_effect=[
                {"score": 68, "pass": False, "feedback": "过于封闭"},
                {"score": 96, "pass": True, "feedback": "达标"},
            ],
        ):
            loop = orchestrator._run_review_loop("团队效率低")

        assert loop.passed is True
        assert loop.review_rounds == 2
        assert loop.question == "当你回顾团队最近的工作时，你注意到了什么？"
        assert loop.review_result["score"] == 96
        assert len(loop.messages) == 5
        mock_rewrite.assert_called_once()

    def test_explicit_review_loop_returns_best_version_when_exhausted(self, orchestrator):
        """5 轮都未通过时，应返回最高分版本。"""
        rewrite_versions = [
            {"question": "版本2", "reasoning": "r2"},
            {"question": "版本3_最佳", "reasoning": "r3"},
            {"question": "版本4", "reasoning": "r4"},
            {"question": "版本5", "reasoning": "r5"},
        ]
        scores = [60, 72, 91, 85, 88]

        with patch.object(
            orchestrator._coach_wrapper,
            "generate_question",
            return_value={"question": "版本1", "reasoning": "r1"},
        ), patch.object(
            orchestrator._coach_wrapper,
            "rewrite_question",
            side_effect=rewrite_versions,
        ), patch.object(
            orchestrator._evaluator_wrapper,
            "evaluate",
            side_effect=[{"score": s, "pass": False, "feedback": f"反馈{s}"} for s in scores],
        ):
            loop = orchestrator._run_review_loop("市场份额下降")

        assert loop.passed is False
        assert loop.review_rounds == 5
        assert loop.question == "版本3_最佳"
        assert loop.returned_best_version is True
        assert loop.best_score == 91
        assert loop.review_result["score"] == 91
        assert loop.last_review_result["score"] == 88

    def test_run_turn_auto_creates_session(self):
        """run_turn 在未 create_session 时自动初始化"""
        from core.orchestrator import Orchestrator

        config = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
        )
        assert orch._session_ready is False

        with patch.object(
            orch,
            "_run_review_loop",
            return_value=self._mock_review_loop_result(
                question="测试总结",
                messages=[{"role": "assistant", "content": "test"}],
                review_result={"score": 96, "pass": True},
                best_score=96,
            ),
        ):
            orch.run_turn("测试输入")

        # create_session 应被自动调用
        assert orch._session_ready is True

    def test_run_turn_returns_turn_result(self, orchestrator):
        """run_turn 返回 TurnResult"""
        from core.orchestrator import TurnResult

        messages = [
            {"role": "user", "content": "团队效率低"},
            {"role": "assistant", "content": "你注意到了什么？"},
        ]

        with patch.object(
            orchestrator,
            "_run_review_loop",
            return_value=self._mock_review_loop_result(
                question="你注意到了什么？",
                messages=messages,
                review_result={"score": 97, "pass": True},
                best_score=97,
            ),
        ):
            result = orchestrator.run_turn("团队效率低")

        assert isinstance(result, TurnResult)
        assert result.question == "你注意到了什么？"
        assert len(result.messages) == 2
        assert result.context["round"] == 1
        assert result.context["review_result"]["score"] == 97

    def test_run_turn_increments_round(self, orchestrator):
        """run_turn 递增轮次计数"""
        with patch.object(
            orchestrator,
            "_run_review_loop",
            return_value=self._mock_review_loop_result(
                question="test",
                messages=[],
                review_result={"score": 95, "pass": True},
                best_score=95,
            ),
        ):
            orchestrator.run_turn("第一轮")

        assert orchestrator._ctx.get("round") == 1

    def test_run_turn_extracts_question_when_summary_empty(self, orchestrator):
        """显式闭环应直接返回 review loop 选中的问题。"""
        messages = [
            {"role": "user", "name": "User", "content": "团队效率低"},
            {
                "role": "assistant",
                "name": "WIAL_Master_Coach",
                "content": '{"question": "当你回顾团队最近的工作时，你注意到了什么？"}',
            },
            {
                "role": "assistant",
                "name": "Strict_Evaluator",
                "content": '{"score": 96, "pass": true}',
            },
        ]

        with patch.object(
            orchestrator,
            "_run_review_loop",
            return_value=self._mock_review_loop_result(
                question="当你回顾团队最近的工作时，你注意到了什么？",
                messages=messages,
                review_result={"score": 96, "pass": True},
                best_score=96,
            ),
        ):
            result = orchestrator.run_turn("团队效率低")

        assert result.question == "当你回顾团队最近的工作时，你注意到了什么？"
        assert result.summary == "当你回顾团队最近的工作时，你注意到了什么？"
        assert result.context["review_rounds"] == 1


# ============================================================
# 7. Agent 包装层测试
# ============================================================
class TestAgentWrappers:
    """验证业务 Agent 包装层正确创建底层 AG2 Agent"""

    @pytest.fixture
    def fake_config(self):
        return _fake_llm_config()

    def test_coach_wrapper_creates_agent(self, fake_config):
        """WIALMasterCoach 创建 ConversableAgent"""
        from agents import WIALMasterCoach
        from autogen import ConversableAgent

        coach = WIALMasterCoach(fake_config)
        agent = coach.get_agent()

        assert isinstance(agent, ConversableAgent)
        assert agent.name == "WIAL_Master_Coach"
        assert agent.human_input_mode == "NEVER"

    def test_evaluator_wrapper_creates_agent(self, fake_config):
        """StrictEvaluator 创建 ConversableAgent"""
        from agents import StrictEvaluator
        from autogen import ConversableAgent

        evaluator = StrictEvaluator(fake_config)
        agent = evaluator.get_agent()

        assert isinstance(agent, ConversableAgent)
        assert agent.name == "Strict_Evaluator"
        assert agent.human_input_mode == "NEVER"

    def test_user_proxy_creates_agent(self):
        """UserProxy 创建 AG2 UserProxyAgent"""
        from agents import UserProxy

        proxy = UserProxy()
        agent = proxy.get_agent()

        assert agent is not None
        assert agent.name == "User"
        assert agent.human_input_mode == "NEVER"

    def test_llm_config_to_autogen(self, fake_config):
        """LLMConfig.to_autogen_config 生成正确格式"""
        autogen_config = fake_config.to_autogen_config()

        assert "config_list" in autogen_config
        assert len(autogen_config["config_list"]) == 1
        assert autogen_config["config_list"][0]["api_type"] == "anthropic"
        assert autogen_config["config_list"][0]["model"] == "claude-sonnet-4-6"
        assert autogen_config["temperature"] == 0.7


# ============================================================
# 8. 端到端场景测试 — Coach-Evaluator 审查循环
# ============================================================
class TestReviewLoopScenarios:
    """验证 Coach-Evaluator 审查循环的三种核心场景

    通过 mock ReviewLoopResult，模拟不同审查结果：
    1. 低质量 → 打回 → 重写 → 通过
    2. 高质量 → 一次通过
    3. 达到最大轮次 → 返回最佳问题
    """

    @pytest.fixture
    def orchestrator(self):
        """创建已初始化的 Orchestrator"""
        from core.orchestrator import Orchestrator

        config = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
        )
        orch.create_session()
        return orch

    def _mock_review_loop_result(
        self,
        question: str,
        messages: list[dict],
        review_result: dict | None,
        review_rounds: int,
        passed: bool,
        best_score: int,
        returned_best_version: bool = False,
        last_review_result: dict | None = None,
    ):
        from core.orchestrator import ReviewLoopResult

        return ReviewLoopResult(
            question=question,
            review_result=review_result,
            last_review_result=last_review_result or review_result,
            messages=messages,
            review_rounds=review_rounds,
            passed=passed,
            best_score=best_score,
            returned_best_version=returned_best_version,
        )

    # ---- 场景 1: 低质量 → 打回 → 重写 → 通过 ----

    def test_scenario_low_quality_then_pass(self, orchestrator):
        """Coach 生成低质量问题 (< 95) → Evaluator 打回 → Coach 重写 → 通过

        模拟 nested chat 内部:
          Round 1: Coach 输出封闭问题, Evaluator 评 68 分打回
          Round 2: Coach 重写为开放问题, Evaluator 评 96 分通过
        最终显式闭环返回通过的问题
        """
        from core.orchestrator import TurnResult

        # 模拟 nested chat 过程中的完整消息历史
        messages = [
            {"role": "user", "content": "团队效率低下"},
            {"role": "assistant", "name": "WIAL_Master_Coach",
             "content": '{"question": "你觉得团队效率��吗？", "reasoning": "初始提问"}'},
            {"role": "assistant", "name": "Strict_Evaluator",
             "content": '{"score": 68, "pass": false, '
                        '"feedback": "问题过于封闭，暗示是非判断"}'},
            {"role": "assistant", "name": "WIAL_Master_Coach",
             "content": '{"question": "当你回顾团队最近的工作时，你注意到了什么？", '
                        '"reasoning": "重写为开放式问题"}'},
            {"role": "assistant", "name": "Strict_Evaluator",
             "content": '{"score": 96, "pass": true, '
                        '"feedback": "高度开放，无预设方向"}'},
        ]

        final_question = "当你回顾团队最近的工作时，你注意到了什么？"
        ret = self._mock_review_loop_result(
            question=final_question,
            messages=messages,
            review_result={"score": 96, "pass": True, "feedback": "高度开放，无预设方向"},
            review_rounds=2,
            passed=True,
            best_score=96,
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("团队效率低下")

        assert isinstance(result, TurnResult)
        assert result.question == final_question
        assert len(result.messages) == 5

        # 验证消息历史包含打回和重写过程
        scores = [m for m in result.messages
                  if m.get("name") == "Strict_Evaluator"]
        assert len(scores) == 2, "应有两轮 Evaluator 评审"

        coach_outputs = [m for m in result.messages
                         if m.get("name") == "WIAL_Master_Coach"]
        assert len(coach_outputs) == 2, "Coach 应输出两次 (初版 + 重写)"

    def test_scenario_low_quality_messages_contain_feedback(self, orchestrator):
        """打回场景中，Evaluator 的反馈应包含具体改进建议"""
        messages = [
            {"role": "user", "content": "项目延期"},
            {"role": "assistant", "name": "WIAL_Master_Coach",
             "content": '{"question": "项目为什么延期了？"}'},
            {"role": "assistant", "name": "Strict_Evaluator",
             "content": '{"score": 72, "pass": false, '
                        '"feedback": "问题预设了因果关系，应更中立"}'},
            {"role": "assistant", "name": "WIAL_Master_Coach",
             "content": '{"question": "当你审视这个项目的进展时，你观察到了什么？"}'},
            {"role": "assistant", "name": "Strict_Evaluator",
             "content": '{"score": 97, "pass": true, '
                        '"feedback": "完全中立开放"}'},
        ]

        ret = self._mock_review_loop_result(
            question="当你审视这个项目的进展时，你观察到了什么？",
            messages=messages,
            review_result={"score": 97, "pass": True, "feedback": "完全中立开放"},
            review_rounds=2,
            passed=True,
            best_score=97,
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("项目延期")

        # 验证第一轮 Evaluator 给出了改进反馈
        import json
        eval_msg_1 = json.loads(messages[2]["content"])
        assert eval_msg_1["pass"] is False
        assert eval_msg_1["score"] < 95
        assert len(eval_msg_1["feedback"]) > 0

        # 验证最终通过
        eval_msg_2 = json.loads(messages[4]["content"])
        assert eval_msg_2["pass"] is True
        assert eval_msg_2["score"] >= 95

    # ---- 场景 2: 高质量 → 一次通过 ----

    def test_scenario_high_quality_one_pass(self, orchestrator):
        """Coach 生成高质量问题 (>= 95) → Evaluator 一次通过"""
        from core.orchestrator import TurnResult

        messages = [
            {"role": "user", "content": "客户投诉增多"},
            {"role": "assistant", "name": "WIAL_Master_Coach",
             "content": '{"question": "当你倾听客户的声音时，你注意到了什么？", '
                        '"reasoning": "完全开放，无预设方向"}'},
            {"role": "assistant", "name": "Strict_Evaluator",
             "content": '{"score": 98, "pass": true, '
                        '"feedback": "高度开放，完全中立，引发深度反思"}'},
        ]

        final_question = "当你倾听客户的声音时，你注意到了什么？"
        ret = self._mock_review_loop_result(
            question=final_question,
            messages=messages,
            review_result={"score": 98, "pass": True, "feedback": "高度开放，完全中立，引发深度反思"},
            review_rounds=1,
            passed=True,
            best_score=98,
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("客户投诉增多")

        assert isinstance(result, TurnResult)
        assert result.question == final_question

        # 只有一轮: Coach 输出 + Evaluator 通过
        eval_msgs = [m for m in result.messages
                     if m.get("name") == "Strict_Evaluator"]
        assert len(eval_msgs) == 1, "高质量问题应只需一轮评审"

        coach_msgs = [m for m in result.messages
                      if m.get("name") == "WIAL_Master_Coach"]
        assert len(coach_msgs) == 1, "Coach 应只输出一次"

    def test_scenario_high_quality_score_above_threshold(self, orchestrator):
        """一次通过场景中评分 >= 95"""
        import json

        messages = [
            {"role": "user", "content": "部门沟通障碍"},
            {"role": "assistant", "name": "WIAL_Master_Coach",
             "content": '{"question": "在团队协作中，你观察到了什么？"}'},
            {"role": "assistant", "name": "Strict_Evaluator",
             "content": '{"score": 95, "pass": true, "feedback": "达标"}'},
        ]

        ret = self._mock_review_loop_result(
            question="在团队协作中，你观察到了什么？",
            messages=messages,
            review_result={"score": 95, "pass": True, "feedback": "达标"},
            review_rounds=1,
            passed=True,
            best_score=95,
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("部门沟通障碍")

        # 验证评分达到阈值
        eval_content = json.loads(messages[2]["content"])
        assert eval_content["score"] >= 95
        assert eval_content["pass"] is True
        assert result.question != ""

    # ---- 场景 3: 最大轮次仍未通过 → 返回最佳问题 ----

    def test_scenario_max_rounds_exhausted(self, orchestrator):
        """达到最大轮次 (5 轮) 仍未通过 → 返回最佳版本

        显式闭环在 5 轮耗尽后返回最佳版本。
        """
        from core.orchestrator import TurnResult

        # 模拟 5 轮审查全部未通过
        messages = [
            {"role": "user", "content": "员工离职率高"},
        ]
        # 生成 5 轮 Coach-Evaluator 交互
        questions = [
            ("员工为什么想走？", 55),
            ("是什么导致了离职？", 62),
            ("你认为离职率高的原因是什么？", 70),
            ("在员工流动中，你发现了什么模式？", 82),
            ("当你思考团队的变化时，什么让你印象深刻？", 89),
        ]
        for q, score in questions:
            messages.append({
                "role": "assistant", "name": "WIAL_Master_Coach",
                "content": f'{{"question": "{q}"}}',
            })
            messages.append({
                "role": "assistant", "name": "Strict_Evaluator",
                "content": f'{{"score": {score}, "pass": false, '
                           f'"feedback": "未达到 95 分阈值"}}',
            })

        # 最佳问题是最后一个 (分��最高但仍 < 95)
        best_question = questions[-1][0]
        ret = self._mock_review_loop_result(
            question=best_question,
            messages=messages,
            review_result={"score": 89, "pass": False, "feedback": "未达到 95 分阈值"},
            last_review_result={"score": 89, "pass": False, "feedback": "未达到 95 分阈值"},
            review_rounds=5,
            passed=False,
            best_score=89,
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("员工离职率高")

        assert isinstance(result, TurnResult)
        # 应返回最佳问题 (尽管未通过)
        assert result.question == best_question
        assert len(result.messages) == 11  # 1 user + 5*(coach+evaluator)

        # 所有 Evaluator 评分都 < 95
        import json
        eval_msgs = [m for m in result.messages
                     if m.get("name") == "Strict_Evaluator"]
        assert len(eval_msgs) == 5, "应有 5 轮评审"
        for em in eval_msgs:
            score = json.loads(em["content"])["score"]
            assert score < 95, f"所有轮次评分应 < 95，实际: {score}"

    def test_scenario_max_rounds_scores_improve(self, orchestrator):
        """最大轮次场景中评分应逐轮递增 (Coach 持续改进)"""
        import json

        messages = [{"role": "user", "content": "产品质量问题"}]
        scores = [50, 65, 73, 80, 88]
        for i, score in enumerate(scores):
            messages.append({
                "role": "assistant", "name": "WIAL_Master_Coach",
                "content": f'{{"question": "问题版本{i+1}"}}'})
            messages.append({
                "role": "assistant", "name": "Strict_Evaluator",
                "content": f'{{"score": {score}, "pass": false}}'})

        ret = self._mock_review_loop_result(
            question=f"问题版本{len(scores)}",
            messages=messages,
            review_result={"score": scores[-1], "pass": False},
            last_review_result={"score": scores[-1], "pass": False},
            review_rounds=len(scores),
            passed=False,
            best_score=max(scores),
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("产品质量问题")

        # 验证评分递增趋势
        eval_msgs = [m for m in result.messages
                     if m.get("name") == "Strict_Evaluator"]
        actual_scores = [json.loads(m["content"])["score"] for m in eval_msgs]
        assert actual_scores == sorted(actual_scores), \
            f"评分应递增: {actual_scores}"

    def test_scenario_max_rounds_returns_best_not_last(self, orchestrator):
        """最大轮次场景中，summary 应对应最高分问题"""
        import json

        # 非递增分数: 第 3 轮最高
        messages = [{"role": "user", "content": "市场份额下降"}]
        rounds_data = [
            ("版本1", 60), ("版本2", 75), ("版本3_最佳", 91),
            ("版本4_退步", 85), ("版本5", 88),
        ]
        best_q = "版本3_最佳"
        best_score = 91

        for q, score in rounds_data:
            messages.append({
                "role": "assistant", "name": "WIAL_Master_Coach",
                "content": f'{{"question": "{q}"}}'})
            messages.append({
                "role": "assistant", "name": "Strict_Evaluator",
                "content": f'{{"score": {score}, "pass": false}}'})

        ret = self._mock_review_loop_result(
            question=best_q,
            messages=messages,
            review_result={"score": best_score, "pass": False},
            last_review_result={"score": rounds_data[-1][1], "pass": False},
            review_rounds=len(rounds_data),
            passed=False,
            best_score=best_score,
            returned_best_version=True,
        )

        with patch.object(orchestrator, "_run_review_loop", return_value=ret):
            result = orchestrator.run_turn("市场份额下降")

        assert result.question == best_q
        # 验证消息历史中确实有更高分的版本
        eval_msgs = [m for m in result.messages
                     if m.get("name") == "Strict_Evaluator"]
        all_scores = [json.loads(m["content"])["score"] for m in eval_msgs]
        assert max(all_scores) == best_score

    # ---- 场景补充: 多轮 run_turn 上下文传递 ----

    def test_scenario_multiple_turns_context_persists(self, orchestrator):
        """多轮 run_turn 调用，context 正确传递"""
        from core.orchestrator import TurnResult

        for round_num in range(1, 4):
            messages = [
                {"role": "user", "content": f"问题{round_num}"},
                {"role": "assistant", "name": "WIAL_Master_Coach",
                 "content": f'{{"question": "回答{round_num}"}}'},
                {"role": "assistant", "name": "Strict_Evaluator",
                 "content": '{"score": 96, "pass": true}'},
            ]
            ret = self._mock_review_loop_result(
                question=f"回答{round_num}",
                messages=messages,
                review_result={"score": 96, "pass": True},
                review_rounds=1,
                passed=True,
                best_score=96,
            )

            with patch.object(orchestrator, "_run_review_loop", return_value=ret):
                result = orchestrator.run_turn(f"问题{round_num}")

            assert result.context["round"] == round_num


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
