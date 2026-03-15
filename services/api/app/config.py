import os
from datetime import date

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://vithisa:changeme@localhost:5432/vithisa49m")

TARGET_MINUTES = 49_000_000
START_DATE = date(2026, 3, 1)
DEADLINE = date(2026, 7, 31)

# Anti-fraud limits (วิทิสาสมาธิ: ครั้งละ 5 นาที, 3 ครั้ง/วัน)
MAX_SESSION_MINUTES = 5
MAX_DAILY_MINUTES = 15          # 3 ครั้ง × 5 นาที
COOLDOWN_SECONDS = 0            # ยังไม่ยืนยัน — ปิดไว้ก่อน
MAX_BULK_MINUTES_PER_PERSON = 5
