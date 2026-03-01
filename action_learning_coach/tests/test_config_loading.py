"""Tests for configuration environment loading behavior."""

from pathlib import Path

import action_learning_coach.core.config as config_module


def test_load_environment_variables_reads_package_env_first(monkeypatch, tmp_path):
    """Web mode should load action_learning_coach/.env before cwd fallback."""
    calls: list[object] = []
    package_env = tmp_path / ".env"
    package_env.write_text("ANTHROPIC_API_KEY=test\n", encoding="utf-8")

    def fake_load_dotenv(*args, **kwargs):
        calls.append(args[0] if args else None)
        return True

    monkeypatch.setattr(config_module, "load_dotenv", fake_load_dotenv)
    monkeypatch.setattr(config_module, "PACKAGE_ENV_FILE", package_env)

    config_module._load_environment_variables()

    assert calls == [package_env, None]
