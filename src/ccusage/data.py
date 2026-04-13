"""
Data loading and aggregation logic for the dashboard.

All functions are pure (no Streamlit imports) to allow unit testing.
"""

import calendar
from datetime import date
from pathlib import Path

import pandas as pd

from ccusage.db import get_connection

INPUT_PRICE_PER_M = 3.0
CACHE_READ_PRICE_PER_M = 0.30


def load_data(db_path: Path) -> pd.DataFrame:
    """Load all usage_stats rows from the database as a DataFrame.

    Returns an empty DataFrame if the database does not exist yet.
    The 'date' column is parsed to datetime; cache token columns are
    guaranteed to be present and integer-typed.
    """
    if not db_path.exists():
        return pd.DataFrame()

    with get_connection(db_path) as conn:
        df = pd.read_sql_query("SELECT * FROM usage_stats", conn)

    if df.empty:
        return df

    df["date"] = pd.to_datetime(df["date"], format="mixed")
    for col in ("cache_creation_tokens", "cache_read_tokens"):
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    return df


def apply_filters(
    df: pd.DataFrame,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    model: str,
) -> pd.DataFrame:
    """Return a filtered copy of df restricted to the given date range and model.

    Passing start=None skips date filtering. Passing model='Alle' skips model filtering.
    """
    out = df.copy()
    if start is not None:
        out = out[(out["date"].dt.normalize() >= start) & (out["date"].dt.normalize() <= end)]
    if model != "Alle":
        out = out[out["model"] == model]
    return out


def cache_hit_rate(df: pd.DataFrame) -> float:
    """Return the cache-read share of all tokens as a percentage (0-100)."""
    total = (
        df["input_tokens"].sum() + df["cache_creation_tokens"].sum() + df["cache_read_tokens"].sum()
    )
    return float(df["cache_read_tokens"].sum() / total * 100) if total else 0.0


def cache_savings_usd(df: pd.DataFrame) -> float:
    """Return estimated USD savings from cache reads vs. regular input pricing (0.30 vs 3.0/M)."""
    return float(
        df["cache_read_tokens"].sum() * (INPUT_PRICE_PER_M - CACHE_READ_PRICE_PER_M) / 1_000_000
    )


def projected_month_cost(df: pd.DataFrame) -> float:
    """Extrapolate the current month's cost based on the daily average so far."""
    today = date.today()
    month_df = df[df["date"].dt.date >= today.replace(day=1)]
    if month_df.empty:
        return 0.0
    days_elapsed = (today - today.replace(day=1)).days + 1
    days_total = calendar.monthrange(today.year, today.month)[1]
    return float(month_df["total_cost"].sum() / days_elapsed * days_total)
