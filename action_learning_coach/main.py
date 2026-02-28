"""
[INPUT]: 依赖 agents 模块 (WIALMasterCoach, StrictEvaluator)，依赖 core 模块 (get_llm_config)，依赖 utils/logger
[OUTPUT]: Terminal 交互入口，支持 Mock 和真实 LLM 双模式
[POS]: 项目入口，编排整体流程，自动检测 API Key 切换模式
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import sys
import time
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# Real Agent Integration - 真实 Agent 集成
# ============================================================================

try:
    from agents import WIALMasterCoach, StrictEvaluator
    from core import get_llm_config
    from utils.logger import get_logger
    REAL_AGENT_AVAILABLE = True
    logger = get_logger(__name__)
except ImportError as e:
    REAL_AGENT_AVAILABLE = False
    logger = None
    print(f"⚠️  真实 Agent 不可用，将使用 mock 模式: {e}")


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
            final_score=final_score
        )
        self.records.append(record)

    def show(self):
        """显示对话历史"""
        if not self.records:
            print("\n📋 对话历史: 暂无记录\n")
            return

        print("\n" + "=" * 70)
        print("📋 对话历史".center(70))
        print("=" * 70)

        for i, record in enumerate(self.records, 1):
            print(f"\n[{i}] {record.timestamp}")
            print(f"  用户输入: {record.user_input[:50]}{'...' if len(record.user_input) > 50 else ''}")
            print(f"  最终问题: {record.final_question[:50]}{'...' if len(record.final_question) > 50 else ''}")
            print(f"  审查轮次: {record.review_rounds} | 最终评分: {record.final_score}/100")

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
    sys.stdout.write(f"\n[{agent_name} 思考中")
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
    print("行动学习 AI 陪练系统 (Phase 1 MVP)".center(70))
    print("=" * 70)
    print("\n💡 提示:")
    print("  - 输入 'quit' 或 'exit' 退出系统")
    print("  - 输入 'history' 查看对话历史\n")


def print_separator(char="-", length=70):
    """打印分隔线"""
    print(char * length)


def print_thinking(agent_name: str):
    """打印思考状态 (非流式版本，保留用于快速模式)"""
    print(f"\n[{agent_name} 思考中...]")


def print_draft(draft: str, streaming: bool = True):
    """打印问题草案"""
    if streaming:
        sys.stdout.write("\n📝 问题草案: \"")
        sys.stdout.flush()
        stream_text(draft + "\"", delay=0.015)
    else:
        print(f"\n📝 问题草案: \"{draft}\"")


def print_evaluation(round_num: int, score: int, feedback: Dict, passed: bool):
    """打印评估结果"""
    print(f"\n[Evaluator 审查中... 第 {round_num} 轮]")
    print(f"评分: {score}/100 {'✅ 通过' if passed else '❌ 未通过'}")

    for dimension, details in feedback.items():
        status = "✓" if details["score"] >= details["max"] * 0.9 else "✗"
        print(f"  {status} {dimension}: {details['score']}/{details['max']} - {details['comment']}")


def print_final_question(question: str):
    """打印最终问题"""
    print("\n" + "=" * 70)
    print("✨ 最终问题:")
    print(f"\n  \"{question}\"\n")
    print("=" * 70)


def get_user_input() -> str:
    """获取用户输入"""
    print("\n请描述您的业务问题:")
    user_input = input("> ").strip()
    return user_input


# ============================================================================
# Real Review Loop - 真实审查循环
# ============================================================================

def real_review_loop(
    user_input: str,
    history: "ConversationHistory",
    coach: "WIALMasterCoach",
    evaluator: "StrictEvaluator",
    max_rounds: int = 5,
    streaming: bool = True,
):
    """真实审查循环流程"""
    print_separator()
    print(f"\n📥 收到输入: \"{user_input}\"")

    final_question = ""
    final_score = 0
    review_rounds = 0
    best_question = ""
    best_score = 0

    for round_num in range(1, max_rounds + 1):
        review_rounds = round_num

        # Coach 生成问题
        if streaming:
            stream_thinking("Coach", duration=1.0)
        else:
            print_thinking("Coach")

        try:
            coach_result = coach.generate_question(user_input)
            question = coach_result.get("question", "")

            if not question:
                print("\n⚠️  Coach 未生成有效问题，跳过本轮")
                continue

            print_draft(question, streaming=streaming)

            # Evaluator 审查
            eval_result = evaluator.evaluate(question)
            score = eval_result.get("score", 0)
            breakdown = eval_result.get("breakdown", {})
            passed = eval_result.get("pass", False)
            feedback_text = eval_result.get("feedback", "")

            # 转换为 UI 格式
            feedback = {
                "开放性": {
                    "score": breakdown.get("openness", 0),
                    "max": 40,
                    "comment": feedback_text.split("开放性")[1].split("\n")[0] if "开放性" in feedback_text else ""
                },
                "无诱导性": {
                    "score": breakdown.get("neutrality", 0),
                    "max": 40,
                    "comment": feedback_text.split("无诱导性")[1].split("\n")[0] if "无诱导性" in feedback_text else ""
                },
                "反思深度": {
                    "score": breakdown.get("depth", 0),
                    "max": 20,
                    "comment": feedback_text.split("反思深度")[1].split("\n")[0] if "反思深度" in feedback_text else ""
                }
            }

            print_evaluation(round_num, score, feedback, passed)

            # 记录最佳版本
            if score > best_score:
                best_score = score
                best_question = question

            if passed:
                final_question = question
                final_score = score
                print_final_question(question)
                break
            else:
                print("\n[Coach 重写中...]")
                if streaming:
                    time.sleep(0.5)
                # 更新 user_input 加入反馈
                user_input = f"{user_input}\n\n上一轮问题: {question}\n评分: {score}/100\n反馈: {feedback_text}"

        except Exception as e:
            logger.error(f"审查循环出错: {e}")
            print(f"\n⚠️  审查出错: {e}")
            break

    # 如果未通过，输出最佳版本
    if not final_question and best_question:
        print(f"\n⚠️  达到最大轮次 ({max_rounds})，输出最佳版本 (评分: {best_score}/100)")
        final_question = best_question
        final_score = best_score
        print_final_question(best_question)

    # 记录对话历史
    history.add(user_input.split("\n")[0], final_question, review_rounds, final_score)


# ============================================================================
# Mock Review Loop - 模拟审查循环
# ============================================================================

def mock_review_loop(user_input: str, history: ConversationHistory, streaming: bool = True):
    """模拟审查循环流程"""
    print_separator()
    print(f"\n📥 收到输入: \"{user_input}\"")

    if streaming:
        stream_thinking("Coach", duration=1.0)
    else:
        print_thinking("Coach")

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
            print("\n[Coach 重写中...]")
            if streaming:
                time.sleep(0.5)

    # 记录对话历史
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

    # 初始化真实 Agent (如果需要)
    coach = None
    evaluator = None
    if use_real_agent:
        try:
            # Coach 使用 Sonnet 模型
            coach_config = get_llm_config("coach")
            coach = WIALMasterCoach(coach_config)

            # Evaluator 使用 Opus 模型
            evaluator_config = get_llm_config("evaluator")
            evaluator = StrictEvaluator(evaluator_config)

            print(f"✅ 真实 Agent 模式已启用")
            print(f"   Coach: {coach_config.model}")
            print(f"   Evaluator: {evaluator_config.model}\n")
            logger.info(f"真实 Agent 模式已启用 - Coach: {coach_config.model}, Evaluator: {evaluator_config.model}")
        except Exception as e:
            print(f"⚠️  真实 Agent 初始化失败，切换到 mock 模式: {e}\n")
            use_real_agent = False
    else:
        print("ℹ️  Mock 模式已启用 (使用模拟数据)\n")

    while True:
        user_input = get_user_input()

        # 退出机制
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 感谢使用，再见！\n")
            sys.exit(0)

        # 查看历史
        if user_input.lower() == "history":
            history.show()
            continue

        # 空输入处理
        if not user_input:
            print("⚠️  输入不能为空，请重新输入")
            continue

        # 执行审查循环
        if use_real_agent and coach and evaluator:
            real_review_loop(user_input, history, coach, evaluator)
        else:
            mock_review_loop(user_input, history)


if __name__ == "__main__":
    main()
