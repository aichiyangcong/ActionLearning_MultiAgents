"""
[INPUT]: 依赖 json, pathlib, typing
[OUTPUT]: 对外提供 append_raw_log(path, turn_data), read_all_raw_logs(path) 函数
[POS]: memory 模块的 Raw 层，JSONL 格式追加写入 + 全量读取
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from pathlib import Path
from typing import Any


# ============================================================
# Raw: JSONL 追加写入 + 全量读取
# ============================================================
def append_raw_log(path: Path, turn_data: dict[str, Any]) -> None:
    """追加一条对话记录到 JSONL 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(turn_data, ensure_ascii=False) + "\n")


def read_all_raw_logs(path: Path) -> list[dict[str, Any]]:
    """读取 JSONL 文件全部记录"""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
