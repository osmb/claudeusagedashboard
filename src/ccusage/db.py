"""
SQLite database access.

Single source of truth for schema creation and migration.
All other modules obtain connections through get_connection().
"""

import contextlib
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


def ensure_schema(cursor: sqlite3.Cursor) -> None:
    """Create the usage_stats table and run pending column migrations."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_stats (
            date                    TEXT,
            model                   TEXT,
            input_tokens            INTEGER,
            output_tokens           INTEGER,
            total_cost              REAL,
            cache_creation_tokens   INTEGER DEFAULT 0,
            cache_read_tokens       INTEGER DEFAULT 0
        )
    """)
    # Idempotent column additions for databases created before cache columns existed.
    for col in ("cache_creation_tokens", "cache_read_tokens"):
        with contextlib.suppress(sqlite3.OperationalError):
            cursor.execute(f"ALTER TABLE usage_stats ADD COLUMN {col} INTEGER DEFAULT 0")


@contextmanager
def get_connection(db_path: Path) -> Generator[sqlite3.Connection]:
    """Yield an open connection with schema ensured; commit and close on exit."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        ensure_schema(cursor)
        conn.commit()
        yield conn
    finally:
        conn.close()
