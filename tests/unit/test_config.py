"""Unit tests for config.py."""

from pathlib import Path

import pytest

from ccusage.config import load_config


class TestLoadConfig:
    def test_defaults_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NPX_PATH", raising=False)
        monkeypatch.delenv("DB_PATH", raising=False)
        config = load_config()
        assert config.npx_path == "npx"
        assert config.db_path.name == "claude_usage.db"

    def test_reads_npx_path_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NPX_PATH", "/usr/local/bin/npx")
        config = load_config()
        assert config.npx_path == "/usr/local/bin/npx"

    def test_relative_db_path_resolved_to_absolute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_PATH", "data/test.db")
        config = load_config()
        assert config.db_path.is_absolute()

    def test_absolute_db_path_used_as_is(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        abs_path = str(tmp_path / "mydb.db")
        monkeypatch.setenv("DB_PATH", abs_path)
        config = load_config()
        assert str(config.db_path) == abs_path

    def test_config_is_frozen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NPX_PATH", raising=False)
        config = load_config()
        with pytest.raises(AttributeError):
            config.npx_path = "other"  # type: ignore[misc]
