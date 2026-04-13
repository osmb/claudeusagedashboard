"""
Imports historical weekly usage data via the ccusage CLI.

Entry point: import_history(config)
"""

import json
import logging
import subprocess

from ccusage.config import Config, load_config
from ccusage.db import get_connection
from ccusage.errors import HistoryImportError

logger = logging.getLogger(__name__)


def _fetch_weekly_data(npx_path: str) -> list[dict]:  # type: ignore[type-arg]
    """Call `ccusage weekly --json` and return the list of weekly entries."""
    try:
        result = subprocess.run(  # noqa: S603 — npx_path comes from trusted config, not user input
            [npx_path, "ccusage", "weekly", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        msg = f"ccusage CLI failed: {exc.stderr.strip()}"
        raise HistoryImportError(msg) from exc

    try:
        return json.loads(result.stdout).get("weekly", [])
    except json.JSONDecodeError as exc:
        msg = f"ccusage returned invalid JSON: {exc}"
        raise HistoryImportError(msg) from exc


def import_history(config: Config) -> None:
    """Fetch all available weekly history and insert it into the database."""
    weekly_entries = _fetch_weekly_data(config.npx_path)

    with get_connection(config.db_path) as conn:
        cursor = conn.cursor()
        for entry in weekly_entries:
            cursor.execute(
                "INSERT INTO usage_stats VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.get("week"),
                    "Historischer Import",
                    entry.get("inputTokens", 0),
                    entry.get("outputTokens", 0),
                    entry.get("totalCost", 0.0),
                    0,
                    0,
                ),
            )
        conn.commit()

    logger.info(f"Imported {len(weekly_entries)} weekly entries")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import_history(load_config())
