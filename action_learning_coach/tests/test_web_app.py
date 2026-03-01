"""
[INPUT]: 依赖 pytest，依赖 fastapi.testclient，依赖 web_app
[OUTPUT]: 对外提供 Web API 最小回归测试
[POS]: tests 模块的 Web UI 后端测试，验证聊天接口和线程重置
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from action_learning_coach.web_app import app, ConversationManager


class _FakeOrchestrator:
    """最小 fake orchestrator，用于隔离 Web API 测试。"""

    def __init__(self):
        self.calls = []

    def run_turn(self, message: str):
        self.calls.append(message)
        return SimpleNamespace(
            question="你现在最先注意到的变化是什么？",
            coach_reply={
                "acknowledgment": "我听到这件事已经开始牵动你的注意力。",
                "questions": [
                    "你现在最先注意到的变化是什么？",
                    "这些变化背后，你最在意的是什么？",
                ],
                "question": "你现在最先注意到的变化是什么？",
            },
            context={
                "review_rounds": 2,
                "review_result": {"score": 97, "pass": True},
                "review_passed": True,
            },
        )


class _ExplodingOrchestrator:
    """用于验证错误路径 JSON 化。"""

    def run_turn(self, _message: str):
        raise RuntimeError("Internal Server Error")


@pytest.fixture
def client():
    created = []

    def _factory():
        orchestrator = _FakeOrchestrator()
        created.append(orchestrator)
        return orchestrator

    original_manager = app.state.session_manager
    app.state.session_manager = ConversationManager(orchestrator_factory=_factory)

    with TestClient(app) as test_client:
        yield test_client, created

    app.state.session_manager = original_manager


@pytest.fixture
def failing_client():
    original_manager = app.state.session_manager
    app.state.session_manager = ConversationManager(
        orchestrator_factory=lambda: _ExplodingOrchestrator()
    )

    with TestClient(app) as test_client:
        yield test_client

    app.state.session_manager = original_manager


def test_chat_endpoint_returns_structured_reply(client):
    """聊天接口应返回 conversation_id 和结构化回复。"""
    test_client, created = client

    response = test_client.post("/api/chat", json={"message": "团队士气在下滑"})

    assert response.status_code == 200
    payload = response.json()

    assert payload["conversation_id"] != ""
    assert payload["primary_question"] == "你现在最先注意到的变化是什么？"
    assert "Q1." in payload["reply_text"]
    assert payload["final_score"] == 97
    assert payload["review_rounds"] == 2
    assert len(created) == 1
    assert created[0].calls == ["团队士气在下滑"]


def test_index_serves_html(client):
    """首页应返回聊天页面 HTML。"""
    test_client, _created = client

    response = test_client.get("/")

    assert response.status_code == 200
    assert "AI Catalyst" in response.text


def test_reset_endpoint_starts_new_session(client):
    """重置线程应返回新的 conversation_id。"""
    test_client, created = client

    first = test_client.post("/api/chat", json={"message": "第一个问题"})
    first_id = first.json()["conversation_id"]

    reset = test_client.post("/api/reset", json={"conversation_id": first_id})
    reset_id = reset.json()["conversation_id"]

    assert reset.status_code == 200
    assert reset_id != first_id
    assert len(created) == 2


def test_chat_endpoint_rejects_empty_message(client):
    """空消息应被拒绝。"""
    test_client, _created = client

    response = test_client.post("/api/chat", json={"message": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Message cannot be empty."


def test_chat_endpoint_returns_json_error_on_internal_failure(failing_client):
    """内部异常时仍应返回 JSON detail，避免前端 JSON.parse 报错。"""
    response = failing_client.post("/api/chat", json={"message": "测试"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Internal Server Error"
