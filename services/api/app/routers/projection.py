from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, timedelta
from app.database import get_db
from app.models import Record, DailyStat
from app.config import TARGET_MINUTES, START_DATE, DEADLINE

router = APIRouter()


@router.get("/projection")
async def get_projection(db: AsyncSession = Depends(get_db)):
    # Current total
    stmt = select(func.coalesce(func.sum(Record.minutes), 0)).where(Record.status == "approved")
    result = await db.execute(stmt)
    current = result.scalar()

    remaining = TARGET_MINUTES - current
    today = date.today()
    days_remaining = (DEADLINE - today).days

    # Average daily rate from daily_stats
    stmt = select(func.count(), func.coalesce(func.sum(DailyStat.total_minutes), 0)).select_from(DailyStat)
    result = await db.execute(stmt)
    row = result.one()
    days_with_data = row[0] or 1
    total_from_stats = row[1]

    daily_rate_current = total_from_stats // max(days_with_data, 1)
    daily_rate_needed = remaining // max(days_remaining, 1) if days_remaining > 0 else 0

    estimated_date = None
    if daily_rate_current > 0 and remaining > 0:
        days_to_complete = int(remaining // daily_rate_current)
        estimated_date = today + timedelta(days=days_to_complete)
        # ถ้าเกิน deadline มาก (เกิน 2 เท่า) ถือว่าคาดการณ์ไม่ได้
        if estimated_date > DEADLINE + timedelta(days=(DEADLINE - START_DATE).days):
            estimated_date = None

    on_track = daily_rate_current >= daily_rate_needed if daily_rate_needed > 0 else current >= TARGET_MINUTES

    return {
        "target_minutes": TARGET_MINUTES,
        "current_minutes": current,
        "remaining_minutes": max(remaining, 0),
        "start_date": str(START_DATE),
        "today": str(today),
        "deadline": str(DEADLINE),
        "days_remaining": max(days_remaining, 0),
        "daily_rate_current": daily_rate_current,
        "daily_rate_needed": daily_rate_needed,
        "estimated_completion_date": str(estimated_date) if estimated_date else None,
        "on_track": on_track,
    }
