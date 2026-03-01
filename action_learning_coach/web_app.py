"""
[INPUT]: 依赖 FastAPI, core/orchestrator, utils/logger
[OUTPUT]: 对外提供 Web 版聊天入口 app
[POS]: Web UI 后端入口，封装 Orchestrator 为 HTTP API，并管理浏览器会话级对话线程
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError as exc:
    raise RuntimeError(
        "fastapi and uvicorn are required for the web UI. "
        "Install them from action_learning_coach/requirements.txt first."
    ) from exc

try:
    from .core import Orchestrator
    from .utils.logger import get_logger
except ImportError:
    from core import Orchestrator
    from utils.logger import get_logger


logger = get_logger(__name__)
BASE_DIR = Path(__file__).resolve().parent
INDEX_HTML = BASE_DIR / "web" / "static" / "index.html"


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """聊天响应"""

    conversation_id: str
    reply_text: str
    coach_reply: dict[str, Any]
    primary_question: str
    review_rounds: int
    final_score: int
    review_passed: bool
    returned_best_version: bool = False


class ResetRequest(BaseModel):
    """重置线程请求"""

    conversation_id: str | None = None


class ResetResponse(BaseModel):
    """重置线程响应"""

    conversation_id: str


@dataclass
class ConversationSession:
    """浏览器会话级对话上下文"""

    orchestrator: Orchestrator
    lock: Lock = field(default_factory=Lock)


class ConversationManager:
    """管理 Web 端的会话级 Orchestrator 实例。"""

    def __init__(self, orchestrator_factory: Callable[[], Orchestrator] | None = None):
        self._orchestrator_factory = orchestrator_factory or self._build_orchestrator
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = Lock()

    @staticmethod
    def _build_orchestrator() -> Orchestrator:
        orchestrator = Orchestrator()
        orchestrator.create_session()
        return orchestrator

    def create_session(self) -> tuple[str, ConversationSession]:
        """创建全新的 Web 会话。"""
        conversation_id = uuid4().hex
        session = ConversationSession(orchestrator=self._orchestrator_factory())
        with self._lock:
            self._sessions[conversation_id] = session
        return conversation_id, session

    def get_or_create_session(self, conversation_id: str | None) -> tuple[str, ConversationSession]:
        """获取现有会话；若不存在则新建。"""
        normalized_id = str(conversation_id or "").strip()
        if normalized_id:
            with self._lock:
                existing = self._sessions.get(normalized_id)
            if existing is not None:
                return normalized_id, existing
        return self.create_session()

    def reset_session(self, conversation_id: str | None) -> tuple[str, ConversationSession]:
        """开始一个全新的线程会话，丢弃旧会话引用。"""
        normalized_id = str(conversation_id or "").strip()
        if normalized_id:
            with self._lock:
                self._sessions.pop(normalized_id, None)
        return self.create_session()


def _format_runtime_error(exc: Exception) -> str:
    """把底层异常转换成前端友好的错误文本。"""
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


def _render_coach_reply(coach_reply: dict[str, Any] | None, fallback_question: str = "") -> str:
    """把结构化回复渲染为纯文本，便于前端兼容展示。"""
    if not isinstance(coach_reply, dict):
        return fallback_question

    lines = []
    acknowledgment = str(coach_reply.get("acknowledgment", "") or "").strip()
    if acknowledgment:
        lines.append(acknowledgment)

    questions = coach_reply.get("questions", [])
    if isinstance(questions, list):
        for idx, question in enumerate(questions[:2], 1):
            text = str(question or "").strip()
            if text:
                lines.append(f"Q{idx}. {text}")

    if not lines and fallback_question:
        lines.append(fallback_question)
    return "\n".join(lines).strip()


def _extract_final_score(review_result: Any) -> int:
    """兼容各种 review_result 结构，提取最终分数。"""
    if not isinstance(review_result, dict):
        return 0
    try:
        return int(review_result.get("score", 0) or 0)
    except (TypeError, ValueError):
        return 0


app = FastAPI(
    title="Action Learning AI Coach Web UI",
    description="Minimal web chat wrapper around the Action Learning Orchestrator.",
)
app.state.session_manager = ConversationManager()


@app.get("/", include_in_schema=False)
def index():
    """返回单页聊天 UI。"""
    if not INDEX_HTML.exists():
        raise HTTPException(status_code=500, detail="Web UI assets are missing.")
    return FileResponse(INDEX_HTML)


@app.get("/health")
def health_check() -> dict[str, str]:
    """基础健康检查。"""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    """把未捕获异常统一转换为 JSON，避免前端收到纯文本 500。"""
    logger.exception("Unhandled web exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": _format_runtime_error(exc)},
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """执行一轮非流式聊天，并返回最终催化师回复。"""
    message = str(request.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    manager: ConversationManager = app.state.session_manager
    conversation_id, session = manager.get_or_create_session(request.conversation_id)

    try:
        with session.lock:
            result = session.orchestrator.run_turn(message)
        review_result = result.context.get("review_result", {}) if isinstance(result.context, dict) else {}

        return ChatResponse(
            conversation_id=conversation_id,
            reply_text=_render_coach_reply(result.coach_reply, fallback_question=result.question),
            coach_reply=result.coach_reply or {},
            primary_question=result.question,
            review_rounds=int(result.context.get("review_rounds", 0) or 0),
            final_score=_extract_final_score(review_result),
            review_passed=bool(result.context.get("review_passed", False)),
            returned_best_version=bool(result.context.get("returned_best_version", False)),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Web chat error: %s", exc)
        raise HTTPException(status_code=503, detail=_format_runtime_error(exc)) from exc


@app.post("/api/reset", response_model=ResetResponse)
def reset_conversation(request: ResetRequest):
    """开启新的 Web 会话线程。"""
    manager: ConversationManager = app.state.session_manager
    conversation_id, _session = manager.reset_session(request.conversation_id)
    return ResetResponse(conversation_id=conversation_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "action_learning_coach.web_app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
