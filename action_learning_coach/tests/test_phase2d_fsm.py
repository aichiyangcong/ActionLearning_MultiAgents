"""
[INPUT]: 依赖 pytest, unittest.mock,
         依赖 agents/observer (observe_turn, _route, _user_requests_business, REFLECTION_THRESHOLD, REFLECTION_EXIT_THRESHOLD, MAX_REFLECTION_TURNS),
         依赖 agents/reflection_agent (ReflectionFacilitator),
         依赖 prompts/reflection_prompt (REFLECTION_TEMPLATE),
         依赖 core.orchestrator (Orchestrator),
         依赖 core.config (LLMConfig, get_llm_config),
         依赖 memory (CognitiveState)
[OUTPUT]: Phase 2d 集成测试 — 验证双轨 FSM + Reflection Agent 的完整性
[POS]: tests 模块的 Phase 2d 集成测试，覆盖 Reflection 配置 / Prompt / Agent / 双轨路由 / Orchestrator 集成
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os
import inspect
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ============================================================
# 测试用 LLMConfig 工厂
# ============================================================
def _fake_llm_config(model="claude-sonnet-4-6"):
    from core.config import LLMConfig
    return LLMConfig(
        api_key="sk-test-fake-key",
        base_url=None,
        model=model,
        temperature=0.7,
        max_review_rounds=5,
        pass_score_threshold=95,
    )


# ============================================================
# 1. Reflection Config 测试
# ============================================================
class TestReflectionConfig:
    """验证 config.py 支持 reflection agent_type"""

    def test_reflection_in_model_map(self):
        """get_llm_config('reflection') 应返回 Sonnet 级模型"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            from core.config import get_llm_config
            config = get_llm_config("reflection")
            assert "sonnet" in config.model.lower()

    def test_reflection_env_override(self):
        """REFLECTION_MODEL 环境变量应覆盖默认模型"""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-test",
            "REFLECTION_MODEL": "claude-custom-reflection",
        }):
            from core.config import get_llm_config
            config = get_llm_config("reflection")
            assert config.model == "claude-custom-reflection"


# ============================================================
# 2. Reflection Prompt 测试
# ============================================================
class TestReflectionPrompt:
    """验证 Reflection prompt 定义"""

    def test_import_reflection_template(self):
        """REFLECTION_TEMPLATE 可从 prompts 导入"""
        from prompts import REFLECTION_TEMPLATE
        assert REFLECTION_TEMPLATE is not None
        assert isinstance(REFLECTION_TEMPLATE, str)

    def test_template_contains_placeholders(self):
        """模板中应包含 5 个认知状态占位符"""
        from prompts.reflection_prompt import REFLECTION_TEMPLATE
        placeholders = [
            "{current_topic}",
            "{thinking_depth}",
            "{emotional_tone}",
            "{key_assumptions}",
            "{blind_spots}",
        ]
        for ph in placeholders:
            assert ph in REFLECTION_TEMPLATE, f"Missing placeholder: {ph}"

    def test_template_format_succeeds(self):
        """模板可用 .format() 正常替换"""
        from prompts.reflection_prompt import REFLECTION_TEMPLATE
        result = REFLECTION_TEMPLATE.format(
            current_topic="测试话题",
            thinking_depth="analytical",
            emotional_tone="curious",
            key_assumptions=["假设1"],
            blind_spots=["盲点1"],
        )
        assert "测试话题" in result
        assert "analytical" in result

    def test_template_contains_three_layers(self):
        """模板应包含三层反思: 模式识别 / 假设挑战 / 视角转换"""
        from prompts.reflection_prompt import REFLECTION_TEMPLATE
        assert "模式识别" in REFLECTION_TEMPLATE
        assert "假设挑战" in REFLECTION_TEMPLATE
        assert "视角转换" in REFLECTION_TEMPLATE

    def test_template_contains_constraints(self):
        """模板应包含核心约束: 不讨论业务 / 不给建议"""
        from prompts.reflection_prompt import REFLECTION_TEMPLATE
        assert "不讨论业务" in REFLECTION_TEMPLATE
        assert "不给建议" in REFLECTION_TEMPLATE


# ============================================================
# 3. ReflectionFacilitator Agent 测试
# ============================================================
class TestReflectionFacilitator:
    """验证 ReflectionFacilitator 的创建和接口"""

    def test_import_from_agents(self):
        """ReflectionFacilitator 可从 agents 导入"""
        from agents import ReflectionFacilitator
        assert ReflectionFacilitator is not None

    def test_create_facilitator(self):
        """ReflectionFacilitator 可正常创建"""
        from agents.reflection_agent import ReflectionFacilitator
        config = _fake_llm_config()
        facilitator = ReflectionFacilitator(config)
        assert facilitator is not None

    def test_get_agent_returns_conversable(self):
        """get_agent() 返回 ConversableAgent"""
        from agents.reflection_agent import ReflectionFacilitator
        from autogen import ConversableAgent
        config = _fake_llm_config()
        facilitator = ReflectionFacilitator(config)
        agent = facilitator.get_agent()
        assert isinstance(agent, ConversableAgent)

    def test_agent_name_is_reflection(self):
        """Agent 名称为 Reflection_Facilitator"""
        from agents.reflection_agent import ReflectionFacilitator
        config = _fake_llm_config()
        agent = ReflectionFacilitator(config).get_agent()
        assert agent.name == "Reflection_Facilitator"

    def test_agent_has_update_state_hook(self):
        """Agent 应配置 update_agent_state_before_reply (UpdateSystemMessage)"""
        from agents.reflection_agent import ReflectionFacilitator
        config = _fake_llm_config()
        agent = ReflectionFacilitator(config).get_agent()
        # UpdateSystemMessage 通过 _register_update_agent_state_before_reply 注册
        # 验证方式: 确认 update_agent_state_before_reply 可调用
        assert callable(agent.update_agent_state_before_reply)

    def test_build_system_message_static(self):
        """_build_system_message 应从 context_variables 提取认知状态"""
        from agents.reflection_agent import ReflectionFacilitator
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables

        config = _fake_llm_config()
        facilitator = ReflectionFacilitator(config)
        agent = facilitator.get_agent()

        # 设置 context_variables
        agent.context_variables = ContextVariables(data={
            "cognitive_state": {
                "current_topic": "团队协作",
                "thinking_depth": "analytical",
                "emotional_tone": "frustrated",
                "key_assumptions": ["假设A"],
                "blind_spots": ["盲点B"],
            }
        })

        result = ReflectionFacilitator._build_system_message(agent, [])
        assert "团队协作" in result
        assert "analytical" in result
        assert "frustrated" in result

    def test_build_system_message_defaults(self):
        """无 context_variables 时使用默认值"""
        from agents.reflection_agent import ReflectionFacilitator
        from autogen import ConversableAgent

        config = _fake_llm_config()
        facilitator = ReflectionFacilitator(config)
        agent = facilitator.get_agent()
        agent.context_variables = None

        result = ReflectionFacilitator._build_system_message(agent, [])
        assert "未知" in result
        assert "surface" in result


# ============================================================
# 4. Observer 双轨路由常量测试
# ============================================================
class TestObserverConstants:
    """验证 Observer 双轨 FSM 常量"""

    def test_reflection_threshold(self):
        from agents.observer import REFLECTION_THRESHOLD
        assert REFLECTION_THRESHOLD == 0.7

    def test_reflection_exit_threshold(self):
        from agents.observer import REFLECTION_EXIT_THRESHOLD
        assert REFLECTION_EXIT_THRESHOLD == 0.5

    def test_max_reflection_turns(self):
        from agents.observer import MAX_REFLECTION_TURNS
        assert MAX_REFLECTION_TURNS == 3


# ============================================================
# 5. 双轨 FSM 路由逻辑测试
# ============================================================
class TestDualTrackRouting:
    """验证 _route() 双轨 FSM 路由决策"""

    def _make_agents(self):
        from autogen import ConversableAgent
        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        reflection = ConversableAgent(name="Test_Reflection", llm_config=False)
        return coach, reflection

    def test_business_low_readiness_stays_business(self):
        """业务轨 + readiness < 0.7 → 继续业务轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 0})

        target, track, turns = _route(
            current_track="business",
            readiness=0.5,
            output="普通问题",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is coach
        assert track == "business"
        assert turns == 0

    def test_business_high_readiness_switches_to_reflection(self):
        """业务轨 + readiness >= 0.7 → 切换到反思轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 0})

        target, track, turns = _route(
            current_track="business",
            readiness=0.8,
            output="深度思考",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is reflection
        assert track == "reflection"
        assert turns == 1

    def test_reflection_user_requests_business(self):
        """反思轨 + 用户要求切回 → 回到业务轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 1})

        target, track, turns = _route(
            current_track="reflection",
            readiness=0.8,
            output="继续业务讨论吧",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is coach
        assert track == "business"
        assert turns == 0

    def test_reflection_low_readiness_exits(self):
        """反思轨 + readiness < 0.5 → 回到业务轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 2})

        target, track, turns = _route(
            current_track="reflection",
            readiness=0.3,
            output="我不确定",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is coach
        assert track == "business"
        assert turns == 0

    def test_reflection_max_turns_exits(self):
        """反思轨 + 超过 3 轮 → 回到业务轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 3})

        target, track, turns = _route(
            current_track="reflection",
            readiness=0.8,
            output="继续反思",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is coach
        assert track == "business"
        assert turns == 0

    def test_reflection_continues(self):
        """反思轨 + 条件满足 → 继续反思"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 1})

        target, track, turns = _route(
            current_track="reflection",
            readiness=0.8,
            output="继续反思",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is reflection
        assert track == "reflection"
        assert turns == 2

    def test_no_reflection_agent_stays_business(self):
        """无 Reflection Agent → 始终走业务轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, _ = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 0})

        target, track, turns = _route(
            current_track="business",
            readiness=0.9,
            output="深度思考",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=None,
        )

        assert target is coach
        assert track == "business"
        assert turns == 0

    def test_boundary_readiness_exactly_threshold(self):
        """readiness == 0.7 (边界值) → 切换到反思轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 0})

        target, track, turns = _route(
            current_track="business",
            readiness=0.7,
            output="边界情况",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is reflection
        assert track == "reflection"

    def test_boundary_exit_readiness_exactly_threshold(self):
        """readiness == 0.5 (边界值) → 不退出反思轨"""
        from agents.observer import _route
        from autogen.agentchat import ContextVariables

        coach, reflection = self._make_agents()
        ctx = ContextVariables(data={"reflection_turn_count": 1})

        target, track, turns = _route(
            current_track="reflection",
            readiness=0.5,
            output="普通输入",
            ctx=ctx,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        assert target is reflection
        assert track == "reflection"


# ============================================================
# 6. _user_requests_business 关键词测试
# ============================================================
class TestUserRequestsBusiness:
    """验证用户切回业务轨的关键词检测"""

    def test_detects_keywords(self):
        from agents.observer import _user_requests_business
        assert _user_requests_business("我们继续业务讨论")
        assert _user_requests_business("回到问题本身")
        assert _user_requests_business("继续讨论具体方案")
        assert _user_requests_business("回到业务上")
        assert _user_requests_business("说一下具体问题")

    def test_no_match(self):
        from agents.observer import _user_requests_business
        assert not _user_requests_business("这个问题很有趣")
        assert not _user_requests_business("我需要再想想")


# ============================================================
# 7. observe_turn 双轨集成测试
# ============================================================
class TestObserveTurnDualTrack:
    """验证 observe_turn 的双轨路由输出"""

    def test_business_track_output(self):
        """业务轨: ctx 包含 current_track=business"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        reflection = ConversableAgent(name="Test_Reflection", llm_config=False)
        ctx = ContextVariables(data={
            "round": 1,
            "current_track": "business",
            "reflection_turn_count": 0,
            "summary_chain": {"entries": []},
        })

        result = observe_turn(
            output="普通问题",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
            reflection_agent=reflection,
        )

        # Mock 模式 readiness=0 → 业务轨
        assert result.context_variables.get("current_track") == "business"

    def test_ctx_includes_track_fields(self):
        """返回的 ContextVariables 应包含 track 相关字段"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        ctx = ContextVariables(data={
            "round": 1,
            "current_track": "business",
            "reflection_turn_count": 0,
            "summary_chain": {"entries": []},
        })

        result = observe_turn(
            output="测试",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
        )

        ctx_data = result.context_variables
        assert "current_track" in ctx_data
        assert "reflection_turn_count" in ctx_data


# ============================================================
# 8. Orchestrator 集成 Reflection Agent 测试
# ============================================================
class TestOrchestratorReflectionIntegration:
    """验证 Orchestrator 正确集成了 Reflection Agent"""

    def test_orchestrator_accepts_reflection_config(self):
        """Orchestrator 构造器接受 reflection_config 参数"""
        from core.orchestrator import Orchestrator
        config = _fake_llm_config()
        reflection_cfg = _fake_llm_config("claude-sonnet-4-6")
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            reflection_config=reflection_cfg,
        )
        assert orch._reflection_config.model == "claude-sonnet-4-6"

    def test_create_session_creates_reflection_agent(self):
        """create_session 后 Reflection Agent 应被创建"""
        from core.orchestrator import Orchestrator
        config = _fake_llm_config()
        reflection_cfg = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            reflection_config=reflection_cfg,
        )
        orch.create_session()

        assert orch._reflection is not None
        assert orch._reflection_wrapper is not None
        assert orch._reflection.name == "Reflection_Facilitator"

    def test_create_session_without_reflection(self):
        """无 reflection_config 且环境无配置时，回退到 coach_config"""
        from core.orchestrator import Orchestrator
        config = _fake_llm_config()
        # __init__ 阶段 patch: get_llm_config("reflection") 失败 → 回退到 coach_config
        with patch("core.orchestrator.get_llm_config", side_effect=ValueError):
            orch = Orchestrator(
                coach_config=config,
                evaluator_config=config,
            )
        assert orch._reflection_config is config
        orch.create_session()
        assert orch._reflection is not None

    def test_observer_extra_args_includes_reflection(self):
        """FunctionTarget extra_args 应包含 reflection_agent"""
        from core.orchestrator import Orchestrator
        config = _fake_llm_config()
        reflection_cfg = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            reflection_config=reflection_cfg,
        )
        orch.create_session()

        ft = orch._user_proxy.handoffs.after_works[0].target
        assert "reflection_agent" in ft.extra_args
        assert ft.extra_args["reflection_agent"] is orch._reflection

    def test_ctx_has_track_fields(self):
        """ContextVariables 应包含 current_track 和 reflection_turn_count"""
        from core.orchestrator import Orchestrator
        config = _fake_llm_config()
        reflection_cfg = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            reflection_config=reflection_cfg,
        )
        orch.create_session()

        assert orch._ctx.get("current_track") == "business"
        assert orch._ctx.get("reflection_turn_count") == 0

    def test_reflection_has_revert_after_work(self):
        """Reflection Agent 的 after_work 应设置为 RevertToUserTarget"""
        from core.orchestrator import Orchestrator
        from autogen.agentchat.group import RevertToUserTarget
        config = _fake_llm_config()
        reflection_cfg = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            reflection_config=reflection_cfg,
        )
        orch.create_session()

        after_works = orch._reflection.handoffs.after_works
        assert len(after_works) > 0
        assert isinstance(after_works[0].target, RevertToUserTarget)

    def test_reflection_property(self):
        """orchestrator.reflection 属性应返回 ReflectionFacilitator"""
        from core.orchestrator import Orchestrator
        from agents.reflection_agent import ReflectionFacilitator
        config = _fake_llm_config()
        reflection_cfg = _fake_llm_config()
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            reflection_config=reflection_cfg,
        )
        orch.create_session()

        assert isinstance(orch.reflection, ReflectionFacilitator)

    def test_orchestrator_docstring_reflects_dual_track(self):
        """Orchestrator docstring 应描述双轨 FSM"""
        from core.orchestrator import Orchestrator
        assert "Reflection" in Orchestrator.__doc__
        assert "双轨" in Orchestrator.__doc__
