"""Configuration settings for the Vidhisa 49M API."""

import os
from datetime import date


def _build_db_url() -> str:
    """Build database URL from environment variables."""
    user = os.getenv("POSTGRES_USER", "vidhisa")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    db = os.getenv("POSTGRES_DB", "vidhisa49m")
    host = os.getenv("DB_HOST", "vidhisa-db")
    return f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"


DATABASE_URL: str = os.getenv("DATABASE_URL") or _build_db_url()

TARGET_MINUTES: int = 49_000_000
START_DATE: date = date(2026, 3, 1)
DEADLINE: date = date(2026, 7, 31)

MAX_SESSION_MINUTES: int = 5
MAX_DAILY_MINUTES: int = 15
COOLDOWN_SECONDS: int = 0
MAX_BULK_MINUTES_PER_PERSON: int = 5
