"""
[INPUT]: 依赖 core/orchestrator (Orchestrator, TurnResult)，依赖 core (get_llm_config)，依赖 utils/logger
[OUTPUT]: Terminal 交互入口，支持 Mock 和 AG2 Orchestrator 双模式
[POS]: 项目入口，真实模式走 AG2 编排，mock 模式使用模拟数据
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from __future__ import annotations

import sys
import time
import os
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module


# ============================================================================
# Real Agent Integration - 真实 Agent 集成
# ============================================================================

def _import_first(*module_names):
    last_error = None
    for module_name in module_names:
        try:
            return import_module(module_name)
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ImportError("No module names provided")


try:
    _logger_module = _import_first("action_learning_coach.utils.logger", "utils.logger")
    get_logger = _logger_module.get_logger
    logger = get_logger(__name__)
except Exception:
    get_logger = None
    logger = None

REAL_AGENT_AVAILABLE = False
Orchestrator = None
TurnResult = None
get_llm_config = None
_real_agent_error = None

try:
    _core_module = _import_first("action_learning_coach.core", "core")
    get_llm_config = _core_module.get_llm_config
    Orchestrator = _core_module.Orchestrator
    TurnResult = _core_module.TurnResult
    REAL_AGENT_AVAILABLE = True
except Exception as exc:
    _real_agent_error = exc
    if get_llm_config is None:
        try:
            _core_module = _import_first("action_learning_coach.core", "core")
            get_llm_config = _core_module.get_llm_config
        except Exception:
            pass

if not REAL_AGENT_AVAILABLE and _real_agent_error is not None:
    print(f"Warning: Agent modules unavailable, mock mode only: {_real_agent_error}")


# ============================================================================
# Data Structures - 数据结构
# ============================================================================

@dataclass
class ConversationRecord:
    """对话记录"""
    timestamp: str
    user_input: str
    final_question: str
    review_rounds: int
    final_score: int


class ConversationHistory:
    """对话历史管理"""

    def __init__(self):
        self.records: List[ConversationRecord] = []

    def add(self, user_input: str, final_question: str, review_rounds: int, final_score: int):
        """添加对话记录"""
        record = ConversationRecord(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user_input=user_input,
            final_question=final_question,
            review_rounds=review_rounds,
            final_score=final_score,
        )
        self.records.append(record)

    def show(self):
        """显示对话历史"""
        if not self.records:
            print("\n  No conversation records yet.\n")
            return

        print("\n" + "=" * 70)
        print("  对话历史".center(70))
        print("=" * 70)

        for i, record in enumerate(self.records, 1):
            print(f"\n[{i}] {record.timestamp}")
            print(f"  Input:    {record.user_input[:50]}{'...' if len(record.user_input) > 50 else ''}")
            print(f"  Question: {record.final_question[:50]}{'...' if len(record.final_question) > 50 else ''}")
            print(f"  Rounds: {record.review_rounds} | Score: {record.final_score}/100")

        print("\n" + "=" * 70 + "\n")


# ============================================================================
# Mock Data - 模拟审查循环的输出
# ============================================================================

MOCK_REVIEW_ROUNDS = [
    {
        "round": 1,
        "draft": "你觉得这个方案能解决问题吗？",
        "score": 68,
        "feedback": {
            "开放性": {"score": 22, "max": 40, "comment": "问题过于封闭，暗示是非判断"},
            "无诱导性": {"score": 28, "max": 40, "comment": "\"能解决问题\"带有诱导性假设"},
            "反思深度": {"score": 18, "max": 20, "comment": "反思深度尚可"}
        },
        "passed": False
    },
    {
        "round": 2,
        "draft": "在这个方案中，你看到了哪些可能的风险？",
        "score": 85,
        "feedback": {
            "开放性": {"score": 34, "max": 40, "comment": "问题较开放，但限定在\"风险\"维度"},
            "无诱导性": {"score": 34, "max": 40, "comment": "\"可能的风险\"略带负面倾向"},
            "反思深度": {"score": 17, "max": 20, "comment": "引导反思但深度不足"}
        },
        "passed": False
    },
    {
        "round": 3,
        "draft": "当你回顾这个方案时，你注意到了什么？",
        "score": 96,
        "feedback": {
            "开放性": {"score": 39, "max": 40, "comment": "高度开放，无预设方向"},
            "无诱导性": {"score": 39, "max": 40, "comment": "完全中立，无诱导"},
            "反思深度": {"score": 18, "max": 20, "comment": "深度反思，触及本质"}
        },
        "passed": True
    }
]


# ============================================================================
# Streaming Output - 流式输出
# ============================================================================

def stream_text(text: str, delay: float = 0.02):
    """流式输出文本"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def stream_thinking(agent_name: str, duration: float = 0.8):
    """流式显示思考动画"""
    sys.stdout.write(f"\n[{agent_name} thinking")
    sys.stdout.flush()

    dots = 0
    steps = int(duration / 0.2)
    for _ in range(steps):
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(0.2)
        dots += 1
        if dots >= 3:
            sys.stdout.write("\b\b\b   \b\b\b")
            sys.stdout.flush()
            dots = 0

    sys.stdout.write("]\n")
    sys.stdout.flush()


# ============================================================================
# UI Components - 界面组件
# ============================================================================

def print_header():
    """打印欢迎界面"""
    print("\n" + "=" * 70)
    print("Action Learning AI Coach (Phase 2)".center(70))
    print("=" * 70)
    print("\n  Commands:")
    print("  - 'quit' or 'exit' to leave")
    print("  - 'history' to view conversation history")
    print("  - 'new' or 'reset' to start a new conversation thread\n")


def print_separator(char="-", length=70):
    """打印分隔线"""
    print(char * length)


def print_draft(draft: str, streaming: bool = True):
    """打印问题草案"""
    if streaming:
        sys.stdout.write('\n  Draft: "')
        sys.stdout.flush()
        stream_text(draft + '"', delay=0.015)
    else:
        print(f'\n  Draft: "{draft}"')


def print_evaluation(round_num: int, score: int, feedback: Dict, passed: bool):
    """打印评估结果"""
    status = "PASS" if passed else "FAIL"
    print(f"\n[Evaluator] Round {round_num} | Score: {score}/100 | {status}")

    for dimension, details in feedback.items():
        mark = "+" if details["score"] >= details["max"] * 0.9 else "-"
        print(f"  {mark} {dimension}: {details['score']}/{details['max']} - {details['comment']}")


def print_final_question(question: str):
    """打印最终问题"""
    print("\n" + "=" * 70)
    print("  Final Question:")
    print(f'\n  "{question}"\n')
    print("=" * 70)


def print_final_coach_reply(coach_reply: Dict | None, fallback_question: str = ""):
    """打印最终 AI 催化师回复。"""
    print("\n" + "=" * 70)
    print("  AI Catalyst Reply:")

    if isinstance(coach_reply, dict):
        acknowledgment = str(coach_reply.get("acknowledgment", "") or "").strip()
        questions = coach_reply.get("questions", [])

        if acknowledgment:
            print(f"\n  {acknowledgment}")

        if isinstance(questions, list):
            for idx, question in enumerate(questions[:2], 1):
                text = str(question or "").strip()
                if text:
                    print(f"  Q{idx}. {text}")
        elif fallback_question:
            print(f'\n  "{fallback_question}"')
    elif fallback_question:
        print(f'\n  "{fallback_question}"')
    else:
        print("\n  (No coach reply available)")

    print("\n" + "=" * 70)


def get_user_input(has_active_thread: bool = False) -> str:
    """获取用户输入"""
    if has_active_thread:
        print("\nContinue the conversation:")
    else:
        print("\nDescribe your business problem:")
    user_input = input("> ").strip()
    return user_input


def _is_rate_limit_error(exc: Exception) -> bool:
    """判断是否为上游限流错误。"""
    response = getattr(exc, "response", None)
    if getattr(response, "status_code", None) == 429:
        return True
    return "429 Too Many Requests" in str(exc)


def _format_orchestrator_error(exc: Exception) -> str:
    """把底层异常转换成终端友好的错误提示。"""
    if _is_rate_limit_error(exc):
        return (
            "Upstream model gateway is rate limiting requests (429 Too Many Requests). "
            "This turn was not completed. Please wait a moment and retry."
        )
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


# ============================================================================
# Orchestrator Review Loop - AG2 编排审查循环
# ============================================================================

def orchestrator_review_loop(
    user_input: str,
    history: ConversationHistory,
    orchestrator: Orchestrator,
):
    """通过 Orchestrator 显式审查闭环执行一轮问题生成"""
    print_separator()
    print(f'\n  Input: "{user_input}"')

    try:
        result = orchestrator.run_turn(user_input)

        question = result.question
        coach_reply = result.coach_reply
        review_rounds = int(result.context.get("review_rounds", 0) or 0)
        review_result = result.context.get("review_result", {})
        final_score = 0
        if isinstance(review_result, dict):
            try:
                final_score = int(review_result.get("score", 0) or 0)
            except (TypeError, ValueError):
                final_score = 0

        if question:
            print_final_coach_reply(coach_reply, fallback_question=question)
        else:
            print("\n  Warning: No question generated.")

        history.add(user_input, question, review_rounds, final_score)

    except Exception as e:
        if logger:
            logger.error(f"Orchestrator error: {e}")
        print(f"\n  Error: {_format_orchestrator_error(e)}")
        print("  This turn was not saved to history.")


# ============================================================================
# Mock Review Loop - 模拟审查循环
# ============================================================================

def mock_review_loop(user_input: str, history: ConversationHistory, streaming: bool = True):
    """模拟审查循环流程"""
    print_separator()
    print(f'\n  Input: "{user_input}"')

    if streaming:
        stream_thinking("Coach", duration=1.0)

    final_question = ""
    final_score = 0
    review_rounds = 0

    for round_data in MOCK_REVIEW_ROUNDS:
        review_rounds = round_data["round"]
        print_draft(round_data["draft"], streaming=streaming)
        print_evaluation(
            round_data["round"],
            round_data["score"],
            round_data["feedback"],
            round_data["passed"]
        )

        if round_data["passed"]:
            final_question = round_data["draft"]
            final_score = round_data["score"]
            print_final_question(round_data["draft"])
            break
        else:
            print("\n[Coach rewriting...]")
            if streaming:
                time.sleep(0.5)

    history.add(user_input, final_question, review_rounds, final_score)


# ============================================================================
# Main Loop - 主循环
# ============================================================================

def main(use_real_agent: bool = None):
    """
    主函数

    Args:
        use_real_agent: 是否使用真实 Agent (None=自动检测, True=强制真实, False=强制 mock)
    """
    print_header()
    history = ConversationHistory()

    # 决定使用哪种模式
    if use_real_agent is None:
        use_real_agent = REAL_AGENT_AVAILABLE and os.getenv("ANTHROPIC_API_KEY")

    # 初始化 Orchestrator (如果需要)
    orchestrator = None
    if use_real_agent:
        try:
            orchestrator = Orchestrator()
            orchestrator.create_session()

            coach_model = orchestrator._coach_config.model
            evaluator_model = orchestrator._evaluator_config.model
            observer_model = orchestrator._observer_config.model
            reflection_model = orchestrator._reflection_config.model
            print(f"  Orchestrator mode enabled")
            print(f"  Coach: {coach_model}")
            print(f"  Evaluator: {evaluator_model}")
            print(f"  Observer: {observer_model}")
            print(f"  Reflection: {reflection_model}\n")
            if logger:
                logger.info("Orchestrator: coach=%s, evaluator=%s", coach_model, evaluator_model)
        except Exception as e:
            print(f"  Orchestrator init failed, falling back to mock: {e}\n")
            use_real_agent = False
            orchestrator = None
    else:
        print("  Mock mode enabled (simulated data)\n")

    while True:
        has_active_thread = bool(use_real_agent and orchestrator and orchestrator.has_active_thread())
        user_input = get_user_input(has_active_thread=has_active_thread)

        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n  Goodbye!\n")
            sys.exit(0)

        if user_input.lower() == "history":
            history.show()
            continue

        if user_input.lower() in ["new", "reset"]:
            if use_real_agent and orchestrator:
                orchestrator.reset_thread()
            print("  Started a new conversation thread.")
            continue

        if not user_input:
            print("  Input cannot be empty.")
            continue

        if use_real_agent and orchestrator:
            orchestrator_review_loop(user_input, history, orchestrator)
        else:
            mock_review_loop(user_input, history)


if __name__ == "__main__":
    main()
