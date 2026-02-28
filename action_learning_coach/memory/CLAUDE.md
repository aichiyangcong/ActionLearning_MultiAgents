# action_learning_coach/memory/
> L2 | 父级: /action_learning_coach/CLAUDE.md

## 成员清单
- __init__.py: 模块入口，导出 CognitiveState, SummaryEntry, SummaryChain, LearnerProfile, SessionManager
- cognitive_state.py: L1 认知状态 (~400 tokens)，每轮覆写，含 current_topic, emotional_tone, key_assumptions, blind_spots, reflection_readiness
- summary_chain.py: L2 会话摘要链 (~200 tokens)，阶段追加，SummaryEntry 记录 phase/turns/summary/anchor_quote/cognitive_shift
- learner_profile.py: L3 学习者画像 (~300 tokens)，跨会话渐进更新 (merge_update: 列表合并去重，标量覆盖)
- raw_log.py: Raw 层 JSONL 读写器，append_raw_log(path, turn_data) 追加 + read_all_raw_logs(path) 全量读取
- session.py: SessionManager 文件 I/O 管理器，管理 data/sessions/{id}/ 和 data/learners/{id}/ 的读写，含 append_summary 便捷追加

## 存储结构
```
data/
├── sessions/{session_id}/
│   ├── cognitive_state.json   # L1, 每轮覆写
│   ├── summary_chain.json     # L2, 阶段追加
│   └── raw_dialogue.jsonl     # Raw, 只追加
└── learners/{learner_id}/
    └── profile.json           # L3, 跨会话渐进更新
```

## 设计哲学
- 三层恒定 ~900 tokens，不随对话增长
- L1 覆写，L2 追加，L3 合并 — 三种更新策略对应三种时间尺度
- 磁盘是唯一 source of truth，L1/L2/L3 可从 Raw 重建
- 用户原话是"金"(anchor_quotes)，Coach 的话是"银"

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
