"""Unit tests for db.py."""

import sqlite3
from pathlib import Path

import pytest

from ccusage.db import ensure_schema, get_connection


class TestEnsureSchema:
    def test_creates_table_if_not_exists(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.db")
        ensure_schema(conn.cursor())
        conn.commit()
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert ("usage_stats",) in tables
        conn.close()

    def test_idempotent_when_called_twice(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.db")
        cursor = conn.cursor()
        ensure_schema(cursor)
        ensure_schema(cursor)  # must not raise
        conn.commit()
        conn.close()

    def test_adds_cache_columns_to_legacy_table(self, tmp_path: Path) -> None:
        conn = sqlite3.connect(tmp_path / "test.db")
        conn.execute(
            "CREATE TABLE usage_stats "
            "(date TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER, total_cost REAL)"
        )
        conn.commit()
        ensure_schema(conn.cursor())
        conn.commit()
        cols = [row[1] for row in conn.execute("PRAGMA table_info(usage_stats)").fetchall()]
        assert "cache_creation_tokens" in cols
        assert "cache_read_tokens" in cols
        conn.close()


class TestGetConnection:
    def test_yields_connection_with_schema(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        with get_connection(db) as conn:
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert ("usage_stats",) in tables

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        db = tmp_path / "subdir" / "test.db"
        with get_connection(db) as conn:
            assert conn is not None
        assert db.exists()

    def test_connection_closed_after_context(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        with get_connection(db) as conn:
            pass
        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
            conn.execute("SELECT 1")
