"""
Collects daily Claude API usage via the ccusage CLI and persists it to SQLite.

Entry point: run_collector(config)
"""

import json
import logging
import subprocess
from datetime import datetime

from ccusage.config import Config, load_config
from ccusage.db import get_connection
from ccusage.errors import CollectorError

logger = logging.getLogger(__name__)


def _fetch_daily_data(npx_path: str) -> list[dict]:  # type: ignore[type-arg]
    """Call `ccusage daily --json` and return the list of daily entries."""
    try:
        result = subprocess.run(  # noqa: S603 — npx_path comes from trusted config, not user input
            [npx_path, "ccusage", "daily", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        msg = f"ccusage CLI failed: {exc.stderr.strip()}"
        raise CollectorError(msg) from exc

    try:
        return json.loads(result.stdout).get("daily", [])
    except json.JSONDecodeError as exc:
        msg = f"ccusage returned invalid JSON: {exc}"
        raise CollectorError(msg) from exc


def run_collector(config: Config) -> None:
    """Fetch today's usage data and insert it into the database."""
    daily_entries = _fetch_daily_data(config.npx_path)

    with get_connection(config.db_path) as conn:
        cursor = conn.cursor()
        total_inserted = 0

        for day in daily_entries:
            day_date = day.get("date")
            # Remove stale rows for this date so a re-run replaces rather than duplicates them.
            cursor.execute("DELETE FROM usage_stats WHERE date = ?", (day_date,))
            breakdowns = day.get("modelBreakdowns", [])

            if breakdowns:
                for m in breakdowns:
                    cursor.execute(
                        "INSERT INTO usage_stats VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            day_date,
                            m.get("modelName", "Unknown"),
                            m.get("inputTokens", 0),
                            m.get("outputTokens", 0),
                            m.get("cost", 0.0),
                            m.get("cacheCreationTokens", 0),
                            m.get("cacheReadTokens", 0),
                        ),
                    )
                    total_inserted += 1
            else:
                cursor.execute(
                    "INSERT INTO usage_stats VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        day_date,
                        "Standard",
                        day.get("inputTokens", 0),
                        day.get("outputTokens", 0),
                        day.get("totalCost", 0.0),
                        day.get("cacheCreationTokens", 0),
                        day.get("cacheReadTokens", 0),
                    ),
                )
                total_inserted += 1

        conn.commit()

    logger.info(
        f"Collected {total_inserted} entries for {len(daily_entries)} day(s) "
        f"at {datetime.now():%Y-%m-%d %H:%M}"
    )


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run_collector(load_config())
