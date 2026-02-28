"""
[INPUT]: 依赖 memory/cognitive_state, memory/summary_chain, memory/learner_profile,
         依赖 memory/raw_log, 依赖 json, pathlib
[OUTPUT]: 对外提供 SessionManager 类，管理三层记忆的文件 I/O
[POS]: memory 模块的持久化层，磁盘是唯一 source of truth
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from pathlib import Path
from typing import Any

from .cognitive_state import CognitiveState
from .summary_chain import SummaryChain, SummaryEntry
from .learner_profile import LearnerProfile
from .raw_log import append_raw_log, read_all_raw_logs


# ============================================================
# 默认数据根目录
# ============================================================
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


# ============================================================
# SessionManager — 文件 I/O 管理器
# ============================================================
class SessionManager:
    """管理三层记忆的文件读写

    目录结构:
        data/
        ├── sessions/{session_id}/
        │   ├── cognitive_state.json   # L1, 每轮覆写
        │   ├── summary_chain.json     # L2, 阶段追加
        │   └── raw_dialogue.jsonl     # Raw, 只追加
        └── learners/{learner_id}/
            └── profile.json           # L3, 跨会话渐进更新
    """

    def __init__(self, data_dir: Path | str | None = None):
        self._data_dir = Path(data_dir) if data_dir else _DEFAULT_DATA_DIR
        self._session_dir: Path | None = None
        self._learner_dir: Path | None = None

    def init_session(self, session_id: str, learner_id: str) -> None:
        """创建会话目录结构"""
        self._session_dir = self._data_dir / "sessions" / session_id
        self._learner_dir = self._data_dir / "learners" / learner_id
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._learner_dir.mkdir(parents=True, exist_ok=True)

    # ---- L1: 认知状态 (覆写) ----

    def save_cognitive_state(self, state: CognitiveState) -> None:
        self._write_json(self._session_path("cognitive_state.json"), state.to_dict())

    def load_cognitive_state(self) -> CognitiveState:
        data = self._read_json(self._session_path("cognitive_state.json"))
        return CognitiveState.from_dict(data) if data else CognitiveState()

    # ---- L2: 摘要链 (追加) ----

    def save_summary_chain(self, chain: SummaryChain) -> None:
        self._write_json(self._session_path("summary_chain.json"), chain.to_dict())

    def append_summary(self, entry: SummaryEntry) -> None:
        """追加单条摘要到 summary_chain.json"""
        chain = self.load_summary_chain()
        chain.append(entry)
        self.save_summary_chain(chain)

    def load_summary_chain(self) -> SummaryChain:
        data = self._read_json(self._session_path("summary_chain.json"))
        return SummaryChain.from_dict(data) if data else SummaryChain()

    # ---- L3: 学习者画像 (渐进更新) ----

    def save_learner_profile(self, profile: LearnerProfile) -> None:
        self._write_json(self._learner_path("profile.json"), profile.to_dict())

    def load_learner_profile(self) -> LearnerProfile:
        data = self._read_json(self._learner_path("profile.json"))
        return LearnerProfile.from_dict(data) if data else LearnerProfile()

    # ---- Raw: 对话日志 (追加) ----

    def append_raw_log(self, turn_data: dict[str, Any]) -> None:
        append_raw_log(self._session_path("raw_dialogue.jsonl"), turn_data)

    def read_raw_logs(self) -> list[dict[str, Any]]:
        """读取当前会话全部原始对话记录"""
        return read_all_raw_logs(self._session_path("raw_dialogue.jsonl"))

    # ---- 内部工具 ----

    def _session_path(self, filename: str) -> Path:
        if not self._session_dir:
            raise RuntimeError("Session not initialized. Call init_session() first.")
        return self._session_dir / filename

    def _learner_path(self, filename: str) -> Path:
        if not self._learner_dir:
            raise RuntimeError("Session not initialized. Call init_session() first.")
        return self._learner_dir / filename

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
