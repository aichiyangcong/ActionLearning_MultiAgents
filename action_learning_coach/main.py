"""
[INPUT]: 依赖 core/orchestrator (Orchestrator, TurnResult)，依赖 core (get_llm_config)，依赖 utils/logger
[OUTPUT]: Terminal 交互入口，支持 Mock 和 AG2 Orchestrator 双模式
[POS]: 项目入口，真实模式走 AG2 编排，mock 模式使用模拟数据
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import sys
import time
import os
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# Real Agent Integration - 真实 Agent 集成
# ============================================================================

try:
    from core.orchestrator import Orchestrator, TurnResult
    from core import get_llm_config
    from utils.logger import get_logger
    REAL_AGENT_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError as e:
    REAL_AGENT_AVAILABLE = False
    logger = None
    print(f"Warning: Agent modules unavailable, mock mode only: {e}")


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
        print("  Conversation History".center(70))
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
    print("  - 'history' to view conversation history\n")


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


def get_user_input() -> str:
    """获取用户输入"""
    print("\nDescribe your business problem:")
    user_input = input("> ").strip()
    return user_input


# ============================================================================
# Orchestrator Review Loop - AG2 编排审查循环
# ============================================================================

def orchestrator_review_loop(
    user_input: str,
    history: ConversationHistory,
    orchestrator: Orchestrator,
):
    """通过 Orchestrator (AG2 编排) 执行审查循环"""
    print_separator()
    print(f'\n  Input: "{user_input}"')

    try:
        result = orchestrator.run_turn(user_input)

        question = result.question
        messages = result.messages
        n_messages = len(messages)

        if question:
            print_final_question(question)
        else:
            print("\n  Warning: No question generated.")

        history.add(user_input, question, n_messages, 0)

    except Exception as e:
        if logger:
            logger.error(f"Orchestrator error: {e}")
        print(f"\n  Error: {e}")
        history.add(user_input, "", 0, 0)


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
            observer_model = orchestrator._observer_config.model if orchestrator._observer_config else "mock"
            print(f"  AG2 Orchestrator mode enabled")
            print(f"  Coach: {coach_model}")
            print(f"  Evaluator: {evaluator_model}")
            print(f"  Observer: {observer_model}\n")
            if logger:
                logger.info("AG2 Orchestrator: coach=%s, evaluator=%s", coach_model, evaluator_model)
        except Exception as e:
            print(f"  Orchestrator init failed, falling back to mock: {e}\n")
            use_real_agent = False
            orchestrator = None
    else:
        print("  Mock mode enabled (simulated data)\n")

    while True:
        user_input = get_user_input()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n  Goodbye!\n")
            sys.exit(0)

        if user_input.lower() == "history":
            history.show()
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
