"""
Application configuration loaded from environment variables.

All env vars are documented in .env.example. This module is the single
place where os.environ is read — business logic receives a Config instance.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass(frozen=True)
class Config:
    npx_path: str
    db_path: Path


def load_config() -> Config:
    """Load and validate configuration from environment variables."""
    npx_path = os.getenv("NPX_PATH", "npx")
    db_path_raw = os.getenv("DB_PATH", "data/claude_usage.db")

    db_path = Path(db_path_raw)
    if not db_path.is_absolute():
        db_path = _PROJECT_ROOT / db_path

    return Config(npx_path=npx_path, db_path=db_path)
