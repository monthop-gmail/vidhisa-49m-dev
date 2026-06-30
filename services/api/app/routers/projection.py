"""Project completion projection API endpoint."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import DEADLINE, START_DATE, TARGET_MINUTES
from app.database import get_db
from app.models import Record

router = APIRouter()


@router.get("/projection")
async def get_projection(db: AsyncSession = Depends(get_db)):
    """Calculate projection for meeting the 49M minute target.

    Returns current progress, required daily rate, and estimated completion date.
    """
    stmt = select(func.coalesce(func.sum(Record.minutes), 0)).where(Record.status == "approved")
    result = await db.execute(stmt)
    current = result.scalar()

    remaining = TARGET_MINUTES - current
    today = date.today()
    days_remaining = (DEADLINE - today).days

    # daily_rate_current = นาที approved เฉลี่ยต่อ "วันที่มีข้อมูลจริง" (สะท้อน pace ตอนปฏิบัติ)
    stmt_days = select(func.count(func.distinct(Record.date))).where(Record.status == "approved")
    result_days = await db.execute(stmt_days)
    days_with_data = result_days.scalar() or 0

    daily_rate_current = current // max(days_with_data, 1) if days_with_data > 0 else 0
    daily_rate_needed = remaining // max(days_remaining, 1) if days_remaining > 0 else 0

    estimated_date = None
    if daily_rate_current > 0 and remaining > 0:
        days_to_complete = int(remaining // daily_rate_current)
        estimated_date = today + timedelta(days=days_to_complete)

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
