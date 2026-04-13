"""Unit tests for data.py — pure logic, no I/O."""

import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ccusage.data import (
    INPUT_PRICE_PER_M,
    apply_filters,
    cache_hit_rate,
    cache_savings_usd,
    load_data,
    projected_month_cost,
)


def make_df(rows: list[dict]) -> pd.DataFrame:  # type: ignore[type-arg]
    """Build a DataFrame matching the usage_stats schema from a list of dicts."""
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["cache_creation_tokens"] = df.get("cache_creation_tokens", 0)
    df["cache_read_tokens"] = df.get("cache_read_tokens", 0)
    return df


# ── load_data ─────────────────────────────────────────────────────────────────


class TestLoadData:
    def test_returns_empty_df_when_db_missing(self, tmp_path: Path) -> None:
        result = load_data(tmp_path / "nonexistent.db")
        assert result.empty

    def test_returns_empty_df_when_table_empty(self, tmp_path: Path) -> None:
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(db)
        conn.execute("""
            CREATE TABLE usage_stats (
                date TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER,
                total_cost REAL, cache_creation_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0)
        """)
        conn.commit()
        conn.close()
        result = load_data(db)
        assert result.empty

    def test_loads_and_parses_rows(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        conn = sqlite3.connect(db)
        conn.execute("""
            CREATE TABLE usage_stats (
                date TEXT, model TEXT, input_tokens INTEGER, output_tokens INTEGER,
                total_cost REAL, cache_creation_tokens INTEGER DEFAULT 0,
                cache_read_tokens INTEGER DEFAULT 0)
        """)
        conn.execute(
            "INSERT INTO usage_stats VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2024-01-15", "claude-3", 1000, 200, 0.005, 50, 100),
        )
        conn.commit()
        conn.close()
        result = load_data(db)
        assert len(result) == 1
        assert pd.api.types.is_datetime64_any_dtype(result["date"])
        assert result.iloc[0]["cache_read_tokens"] == 100


# ── apply_filters ─────────────────────────────────────────────────────────────


class TestApplyFilters:
    def test_no_filters_returns_all_rows(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_cost": 1.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
                {
                    "date": "2024-01-02",
                    "model": "B",
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "total_cost": 2.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
            ]
        )
        result = apply_filters(df, None, None, "Alle")
        assert len(result) == 2

    def test_date_range_filters_rows(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_cost": 1.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
                {
                    "date": "2024-01-05",
                    "model": "A",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_cost": 1.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
                {
                    "date": "2024-01-10",
                    "model": "A",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_cost": 1.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
            ]
        )
        result = apply_filters(df, pd.Timestamp("2024-01-03"), pd.Timestamp("2024-01-07"), "Alle")
        assert len(result) == 1
        assert result.iloc[0]["date"].date() == date(2024, 1, 5)

    def test_model_filter_excludes_other_models(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "claude-3",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_cost": 1.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
                {
                    "date": "2024-01-01",
                    "model": "claude-4",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_cost": 2.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                },
            ]
        )
        result = apply_filters(df, None, None, "claude-3")
        assert len(result) == 1
        assert result.iloc[0]["model"] == "claude-3"

    def test_empty_dataframe_stays_empty(self) -> None:
        df = pd.DataFrame(
            columns=[
                "date",
                "model",
                "input_tokens",
                "output_tokens",
                "total_cost",
                "cache_creation_tokens",
                "cache_read_tokens",
            ]
        )
        df["date"] = pd.to_datetime(df["date"])
        result = apply_filters(df, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-31"), "Alle")
        assert result.empty


# ── cache_hit_rate ─────────────────────────────────────────────────────────────


class TestCacheHitRate:
    def test_returns_zero_when_no_tokens(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                }
            ]
        )
        assert cache_hit_rate(df) == 0.0

    def test_calculates_correct_percentage(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 700,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                    "cache_creation_tokens": 100,
                    "cache_read_tokens": 200,
                }
            ]
        )
        # total = 700 + 100 + 200 = 1000; cache_reads = 200 → 20%
        assert cache_hit_rate(df) == pytest.approx(20.0)

    def test_aggregates_across_multiple_rows(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 500,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 500,
                },
                {
                    "date": "2024-01-02",
                    "model": "A",
                    "input_tokens": 500,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 500,
                },
            ]
        )
        assert cache_hit_rate(df) == pytest.approx(50.0)


# ── cache_savings_usd ─────────────────────────────────────────────────────────


class TestCacheSavingsUsd:
    def test_returns_zero_without_cache_reads(self) -> None:
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 1000,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                }
            ]
        )
        assert cache_savings_usd(df) == 0.0

    def test_calculates_savings_correctly(self) -> None:
        # 1M cache_read_tokens → savings = (3.0 - 0.30) / 1 = 2.70 USD
        df = make_df(
            [
                {
                    "date": "2024-01-01",
                    "model": "A",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_cost": 0.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 1_000_000,
                }
            ]
        )
        expected = INPUT_PRICE_PER_M - 0.30
        assert cache_savings_usd(df) == pytest.approx(expected)


# ── projected_month_cost ──────────────────────────────────────────────────────


class TestProjectedMonthCost:
    def test_returns_zero_for_empty_df(self) -> None:
        df = pd.DataFrame(columns=["date", "total_cost"])
        df["date"] = pd.to_datetime(df["date"])
        assert projected_month_cost(df) == 0.0

    def test_projection_scales_to_full_month(self) -> None:
        today = date.today()
        # 1 entry on the 1st of this month with cost 1.0
        df = make_df(
            [
                {
                    "date": today.replace(day=1).isoformat(),
                    "model": "A",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_cost": 1.0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                }
            ]
        )
        result = projected_month_cost(df)
        # days_elapsed >= 1; result should be >= 1.0
        assert result >= 1.0
