"""Unit tests for collector.py."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ccusage.collector import run_collector
from ccusage.config import Config
from ccusage.errors import CollectorError


def make_config(tmp_path: Path) -> Config:
    return Config(npx_path="/usr/bin/npx", db_path=tmp_path / "test.db")


DAILY_RESPONSE_WITH_BREAKDOWNS = json.dumps(
    {
        "daily": [
            {
                "date": "2024-01-15",
                "modelBreakdowns": [
                    {
                        "modelName": "claude-3-sonnet",
                        "inputTokens": 1000,
                        "outputTokens": 200,
                        "cost": 0.005,
                        "cacheCreationTokens": 50,
                        "cacheReadTokens": 100,
                    }
                ],
            }
        ]
    }
)

DAILY_RESPONSE_NO_BREAKDOWNS = json.dumps(
    {
        "daily": [
            {
                "date": "2024-01-15",
                "modelBreakdowns": [],
                "inputTokens": 1000,
                "outputTokens": 200,
                "totalCost": 0.003,
                "cacheCreationTokens": 0,
                "cacheReadTokens": 0,
            }
        ]
    }
)


class TestRunCollector:
    def test_inserts_rows_with_model_breakdowns(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        mock_result = MagicMock()
        mock_result.stdout = DAILY_RESPONSE_WITH_BREAKDOWNS

        with patch("ccusage.collector.subprocess.run", return_value=mock_result):
            run_collector(config)

        from ccusage.db import get_connection

        with get_connection(config.db_path) as conn:
            rows = conn.execute("SELECT * FROM usage_stats").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "claude-3-sonnet"

    def test_inserts_row_without_model_breakdowns(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        mock_result = MagicMock()
        mock_result.stdout = DAILY_RESPONSE_NO_BREAKDOWNS

        with patch("ccusage.collector.subprocess.run", return_value=mock_result):
            run_collector(config)

        from ccusage.db import get_connection

        with get_connection(config.db_path) as conn:
            rows = conn.execute("SELECT * FROM usage_stats").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == "Standard"

    def test_raises_on_subprocess_failure(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        with (
            patch(
                "ccusage.collector.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "npx", stderr="not found"),
            ),
            pytest.raises(CollectorError, match="ccusage CLI failed"),
        ):
            run_collector(config)

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        mock_result = MagicMock()
        mock_result.stdout = "not json"
        with (
            patch("ccusage.collector.subprocess.run", return_value=mock_result),
            pytest.raises(CollectorError, match="invalid JSON"),
        ):
            run_collector(config)
