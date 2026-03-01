"""
[INPUT]: 依赖 pytest, unittest.mock,
         依赖 agents/observer (observe_turn),
         依赖 prompts/observer_prompt (OBSERVER_SYSTEM_MESSAGE),
         依赖 core.orchestrator (Orchestrator, TurnResult),
         依赖 core.config (LLMConfig, get_llm_config),
         依赖 memory (CognitiveState)
[OUTPUT]: Phase 2c 集成测试 — 验证 Observer Agent 的完整性
[POS]: tests 模块的 Phase 2c 集成测试，覆盖 Observer 配置 / Prompt / FunctionTarget / Orchestrator 集成
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
import sys
import os
import json
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
# 1. Observer Config 测试
# ============================================================
class TestObserverConfig:
    """验证 config.py 支持 observer agent_type"""

    def test_observer_in_model_map(self):
        """get_llm_config('observer') 应返回 Haiku 级模型"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            from core.config import get_llm_config
            config = get_llm_config("observer")
            assert "haiku" in config.model.lower()

    def test_observer_env_override(self):
        """OBSERVER_MODEL 环境变量应覆盖默认模型"""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-test",
            "OBSERVER_MODEL": "claude-custom-model",
        }):
            from core.config import get_llm_config
            config = get_llm_config("observer")
            assert config.model == "claude-custom-model"


# ============================================================
# 2. Observer Prompt 测试
# ============================================================
class TestObserverPrompt:
    """验证 Observer prompt 定义"""

    def test_import_observer_prompt(self):
        """OBSERVER_SYSTEM_MESSAGE 可从 prompts 导入"""
        from prompts import OBSERVER_SYSTEM_MESSAGE
        assert OBSERVER_SYSTEM_MESSAGE is not None
        assert isinstance(OBSERVER_SYSTEM_MESSAGE, str)

    def test_prompt_contains_json_format(self):
        """prompt 中应包含 JSON 输出格式说明"""
        from prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE
        assert "current_topic" in OBSERVER_SYSTEM_MESSAGE
        assert "emotional_tone" in OBSERVER_SYSTEM_MESSAGE
        assert "thinking_depth" in OBSERVER_SYSTEM_MESSAGE
        assert "reflection_readiness" in OBSERVER_SYSTEM_MESSAGE

    def test_prompt_contains_cognitive_fields(self):
        """prompt 中应覆盖 CognitiveState 所有核心字段"""
        from prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE
        from memory import CognitiveState
        state = CognitiveState()
        for field_name in ["current_topic", "emotional_tone", "thinking_depth",
                           "key_assumptions", "blind_spots", "anchor_quotes"]:
            assert field_name in OBSERVER_SYSTEM_MESSAGE, f"Missing field: {field_name}"

    def test_prompt_under_token_budget(self):
        """prompt 不应过长 (粗略 word count < 2000)"""
        from prompts.observer_prompt import OBSERVER_SYSTEM_MESSAGE
        word_count = len(OBSERVER_SYSTEM_MESSAGE.split())
        assert word_count < 2000, f"Prompt too long: {word_count} words"


# ============================================================
# 3. observe_turn 函数签名测试
# ============================================================
class TestObserveTurnSignature:
    """验证 observe_turn 符合 AG2 FunctionTarget 规约"""

    def test_import_observe_turn(self):
        """observe_turn 可从 agents 导入"""
        from agents import observe_turn
        assert callable(observe_turn)

    def test_function_has_at_least_two_params(self):
        """FunctionTarget 规约: 至少两个位置参数"""
        from agents.observer import observe_turn
        sig = inspect.signature(observe_turn)
        params = list(sig.parameters.values())
        assert len(params) >= 2

    def test_first_param_is_output(self):
        """第一个参数应是 output (str)"""
        from agents.observer import observe_turn
        sig = inspect.signature(observe_turn)
        params = list(sig.parameters.values())
        assert params[0].name == "output"

    def test_second_param_is_ctx(self):
        """第二个参数应是 ctx (ContextVariables)"""
        from agents.observer import observe_turn
        sig = inspect.signature(observe_turn)
        params = list(sig.parameters.values())
        assert params[1].name == "ctx"

    def test_extra_params_have_defaults(self):
        """第 3+ 参数应有默认值 (FunctionTarget extra_args 兼容)"""
        from agents.observer import observe_turn
        sig = inspect.signature(observe_turn)
        params = list(sig.parameters.values())
        for p in params[2:]:
            assert p.default is not inspect.Parameter.empty, (
                f"Parameter '{p.name}' must have a default value"
            )

    def test_function_target_validation(self):
        """验证 observe_turn 通过 AG2 FunctionTarget 构造验证"""
        from agents.observer import observe_turn
        from autogen.agentchat.group import FunctionTarget
        # 应不抛出异常
        ft = FunctionTarget(
            observe_turn,
            extra_args={
                "observer_config": None,
                "coach_agent": MagicMock(),
            },
        )
        assert ft is not None


# ============================================================
# 4. observe_turn 逻辑测试
# ============================================================
class TestObserveTurnLogic:
    """验证 observe_turn 的核心逻辑"""

    def test_mock_mode_returns_default_state(self):
        """无 observer_config 时返回默认 CognitiveState"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        ctx = ContextVariables(data={"round": 1, "summary_chain": {"entries": []}})

        result = observe_turn(
            output="测试输入",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
        )

        assert result is not None
        assert result.context_variables is not None
        cognitive = result.context_variables.get("cognitive_state")
        assert cognitive is not None
        assert cognitive["turn_number"] == 1

    def test_returns_agent_target_to_coach(self):
        """Phase 2c: 始终路由到 Coach"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables
        from autogen.agentchat.group import AgentTarget

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        ctx = ContextVariables(data={"round": 1, "summary_chain": {"entries": []}})

        result = observe_turn(
            output="测试输入",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
        )

        assert isinstance(result.target, AgentTarget)

    def test_return_type_is_function_target_result(self):
        """返回值必须是 FunctionTargetResult"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables
        from autogen.agentchat.group import FunctionTargetResult

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        ctx = ContextVariables(data={"round": 3, "summary_chain": {"entries": []}})

        result = observe_turn(
            output="我的团队总是拖延",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
        )

        assert isinstance(result, FunctionTargetResult)

    def test_empty_output_terminates_run(self):
        """回到 User 但没有新输入时，应结束当前轮次，避免空转"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables
        from autogen.agentchat.group import TerminateTarget

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        ctx = ContextVariables(data={"round": 1, "summary_chain": {"entries": []}})

        result = observe_turn(
            output="",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
        )

        assert isinstance(result.target, TerminateTarget)
        assert result.context_variables is None

    def test_cognitive_state_fields_complete(self):
        """返回的 cognitive_state 应包含所有 CognitiveState 字段"""
        from agents.observer import observe_turn
        from autogen import ConversableAgent
        from autogen.agentchat import ContextVariables
        from memory import CognitiveState

        coach = ConversableAgent(name="Test_Coach", llm_config=False)
        ctx = ContextVariables(data={"round": 1, "summary_chain": {"entries": []}})

        result = observe_turn(
            output="测试",
            ctx=ctx,
            observer_config=None,
            coach_agent=coach,
        )

        cognitive = result.context_variables.get("cognitive_state")
        expected_fields = set(CognitiveState.__dataclass_fields__.keys())
        actual_fields = set(cognitive.keys())
        assert expected_fields.issubset(actual_fields), (
            f"Missing fields: {expected_fields - actual_fields}"
        )


# ============================================================
# 5. 内部工具函数测试
# ============================================================
class TestInternalHelpers:
    """验证 Observer 内部工具函数"""

    def test_build_analysis_input_basic(self):
        """基本输入构造"""
        from agents.observer import _build_analysis_input
        result = _build_analysis_input("用户的问题", {"entries": []}, 3)
        assert "[Turn 3]" in result
        assert "用户的问题" in result

    def test_build_analysis_input_with_summary(self):
        """包含 L2 摘要链上下文"""
        from agents.observer import _build_analysis_input
        summary_chain = {
            "entries": [
                {"phase": "exploration", "summary": "用户在探索团队管理问题"},
                {"phase": "deepening", "summary": "开始分析根因"},
            ]
        }
        result = _build_analysis_input("继续讨论", summary_chain, 5)
        assert "[Context]" in result
        assert "exploration" in result

    def test_parse_cognitive_json_valid(self):
        """解析有效 JSON"""
        from agents.observer import _parse_cognitive_json
        valid_json = json.dumps({
            "current_topic": "测试",
            "emotional_tone": "neutral",
            "thinking_depth": "surface",
        })
        result = _parse_cognitive_json(valid_json)
        assert result["current_topic"] == "测试"

    def test_parse_cognitive_json_with_markdown(self):
        """解析 markdown 包裹的 JSON"""
        from agents.observer import _parse_cognitive_json
        md_json = '```json\n{"current_topic": "test", "emotional_tone": "curious"}\n```'
        result = _parse_cognitive_json(md_json)
        assert result["current_topic"] == "test"

    def test_parse_cognitive_json_none(self):
        """None 输入返回默认值"""
        from agents.observer import _parse_cognitive_json
        result = _parse_cognitive_json(None)
        assert result["emotional_tone"] == "neutral"

    def test_parse_cognitive_json_invalid(self):
        """无效输入返回默认值"""
        from agents.observer import _parse_cognitive_json
        result = _parse_cognitive_json("这不是 JSON")
        assert "current_topic" in result


# ============================================================
# 6. Orchestrator 集成 Observer 测试
# ============================================================
class TestOrchestratorObserverIntegration:
    """验证 Orchestrator 正确集成了 Observer"""

    def test_orchestrator_accepts_observer_config(self):
        """Orchestrator 构造器接受 observer_config 参数"""
        from core.orchestrator import Orchestrator
        config = _fake_llm_config()
        observer_cfg = _fake_llm_config("claude-haiku-4-5")
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            observer_config=observer_cfg,
        )
        assert orch._observer_config.model == "claude-haiku-4-5"

    def test_create_session_configures_observer(self):
        """create_session 后 UserProxy 应配置 FunctionTarget after_work"""
        from core.orchestrator import Orchestrator
        from autogen.agentchat.group import FunctionTarget
        config = _fake_llm_config()
        observer_cfg = _fake_llm_config("claude-haiku-4-5")
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            observer_config=observer_cfg,
        )
        orch.create_session()

        # UserProxy 的 after_works 应包含 FunctionTarget
        after_works = orch._user_proxy.handoffs.after_works
        assert len(after_works) > 0
        ft = after_works[0].target
        assert isinstance(ft, FunctionTarget)

    def test_observer_function_target_has_correct_extra_args(self):
        """FunctionTarget 的 extra_args 应包含 observer_config 和 coach_agent"""
        from core.orchestrator import Orchestrator
        from autogen.agentchat.group import FunctionTarget
        config = _fake_llm_config()
        observer_cfg = _fake_llm_config("claude-haiku-4-5")
        orch = Orchestrator(
            coach_config=config,
            evaluator_config=config,
            observer_config=observer_cfg,
        )
        orch.create_session()

        ft = orch._user_proxy.handoffs.after_works[0].target
        assert "observer_config" in ft.extra_args
        assert "coach_agent" in ft.extra_args
        assert ft.extra_args["coach_agent"] is orch._coach

    def test_orchestrator_docstring_reflects_observer(self):
        """Orchestrator docstring 应描述 Observer 数据流"""
        from core.orchestrator import Orchestrator
        assert "Observer" in Orchestrator.__doc__


# ============================================================
# 7. CognitiveState 同步测试
# ============================================================
class TestCognitiveStateSync:
    """验证 Observer 更新的认知状态能同步到 Orchestrator"""

    def test_cognitive_state_from_ctx_dict(self):
        """从 ctx_dict 重建 CognitiveState"""
        from memory import CognitiveState
        data = {
            "current_topic": "团队管理",
            "emotional_tone": "frustrated",
            "thinking_depth": "analytical",
            "key_assumptions": [{"assumption": "人手不够", "evidence": "我总是加班"}],
            "blind_spots": ["忽略了流程问题"],
            "anchor_quotes": ["我已经试了各种方法"],
            "reflection_readiness": {"score": 0.5, "signals": ["开始自我质疑"]},
            "turn_number": 3,
        }
        state = CognitiveState.from_dict(data)
        assert state.current_topic == "团队管理"
        assert state.emotional_tone == "frustrated"
        assert state.thinking_depth == "analytical"
        assert len(state.key_assumptions) == 1
        assert state.reflection_readiness["score"] == 0.5

    def test_round_trip_cognitive_state(self):
        """CognitiveState to_dict → from_dict 应无损"""
        from memory import CognitiveState
        original = CognitiveState(
            current_topic="创新",
            emotional_tone="excited",
            thinking_depth="reflective",
            turn_number=7,
        )
        reconstructed = CognitiveState.from_dict(original.to_dict())
        assert reconstructed.current_topic == original.current_topic
        assert reconstructed.emotional_tone == original.emotional_tone
        assert reconstructed.turn_number == original.turn_number
