import os
from datetime import date

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://vithisa:changeme@localhost:5432/vithisa49m")

TARGET_MINUTES = 49_000_000
START_DATE = date(2026, 3, 1)
DEADLINE = date(2026, 7, 31)

# Anti-fraud limits
MAX_SESSION_MINUTES = 30
MAX_DAILY_MINUTES = 120
COOLDOWN_SECONDS = 300
MAX_BULK_MINUTES_PER_PERSON = 30
