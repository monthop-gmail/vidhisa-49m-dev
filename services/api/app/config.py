import os
from datetime import date


def _build_db_url() -> str:
    user = os.getenv("POSTGRES_USER", "vidhisa")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    db = os.getenv("POSTGRES_DB", "vidhisa49m")
    host = os.getenv("DB_HOST", "vidhisa-db")
    return f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"


DATABASE_URL = os.getenv("DATABASE_URL") or _build_db_url()

TARGET_MINUTES = 49_000_000
START_DATE = date(2026, 3, 1)
DEADLINE = date(2026, 7, 31)

# Anti-fraud limits (วิทิสาสมาธิ: ครั้งละ 5 นาที, 3 ครั้ง/วัน)
MAX_SESSION_MINUTES = 5
MAX_DAILY_MINUTES = 15          # 3 ครั้ง × 5 นาที
COOLDOWN_SECONDS = 0            # ยังไม่ยืนยัน — ปิดไว้ก่อน
MAX_BULK_MINUTES_PER_PERSON = 5
