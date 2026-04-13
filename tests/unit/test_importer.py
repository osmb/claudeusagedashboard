"""Unit tests for importer.py."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ccusage.config import Config
from ccusage.errors import HistoryImportError
from ccusage.importer import import_history


def make_config(tmp_path: Path) -> Config:
    return Config(npx_path="/usr/bin/npx", db_path=tmp_path / "test.db")


WEEKLY_RESPONSE = json.dumps(
    {
        "weekly": [
            {"week": "2024-W01", "inputTokens": 5000, "outputTokens": 1000, "totalCost": 0.02},
            {"week": "2024-W02", "inputTokens": 6000, "outputTokens": 1200, "totalCost": 0.024},
        ]
    }
)


class TestImportHistory:
    def test_inserts_all_weekly_entries(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        mock_result = MagicMock()
        mock_result.stdout = WEEKLY_RESPONSE

        with patch("ccusage.importer.subprocess.run", return_value=mock_result):
            import_history(config)

        from ccusage.db import get_connection

        with get_connection(config.db_path) as conn:
            rows = conn.execute("SELECT * FROM usage_stats").fetchall()
        assert len(rows) == 2
        assert rows[0][1] == "Historischer Import"

    def test_raises_on_subprocess_failure(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        with (
            patch(
                "ccusage.importer.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "npx", stderr="error"),
            ),
            pytest.raises(HistoryImportError, match="ccusage CLI failed"),
        ):
            import_history(config)

    def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        mock_result = MagicMock()
        mock_result.stdout = "{invalid"
        with (
            patch("ccusage.importer.subprocess.run", return_value=mock_result),
            pytest.raises(HistoryImportError, match="invalid JSON"),
        ):
            import_history(config)

    def test_handles_empty_weekly_response(self, tmp_path: Path) -> None:
        config = make_config(tmp_path)
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"weekly": []})
        with patch("ccusage.importer.subprocess.run", return_value=mock_result):
            import_history(config)  # must not raise

        from ccusage.db import get_connection

        with get_connection(config.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM usage_stats").fetchone()[0]
        assert count == 0
