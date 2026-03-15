from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Record
from app.config import MAX_SESSION_MINUTES, MAX_DAILY_MINUTES, COOLDOWN_SECONDS, MAX_BULK_MINUTES_PER_PERSON


async def validate_record(data, db: AsyncSession) -> list[str]:
    flags = []

    # Basic validation
    if data.minutes <= 0:
        raise HTTPException(status_code=422, detail={
            "error": "INVALID_MINUTES",
            "message": "จำนวนนาทีต้องมากกว่า 0",
            "detail": {"attempted": data.minutes}
        })

    if data.type == "individual":
        # Hard limit: session
        if data.minutes > MAX_SESSION_MINUTES:
            raise HTTPException(status_code=422, detail={
                "error": "SESSION_LIMIT_EXCEEDED",
                "message": f"เกินเพดาน {MAX_SESSION_MINUTES} นาทีต่อครั้ง",
                "detail": {"attempted": data.minutes, "limit": MAX_SESSION_MINUTES}
            })

        # Check daily total
        stmt = select(func.coalesce(func.sum(Record.minutes), 0)).where(
            Record.name == data.name,
            Record.branch_id == data.branch_id,
            Record.date == data.date,
            Record.status.in_(["pending", "approved"])
        )
        result = await db.execute(stmt)
        current_today = result.scalar()

        if current_today + data.minutes > MAX_DAILY_MINUTES:
            raise HTTPException(status_code=422, detail={
                "error": "DAILY_LIMIT_EXCEEDED",
                "message": f"เกินเพดาน {MAX_DAILY_MINUTES} นาทีต่อวัน",
                "detail": {"current_today": current_today, "attempted": data.minutes, "limit": MAX_DAILY_MINUTES}
            })

        if current_today + data.minutes >= MAX_DAILY_MINUTES:
            flags.append("daily_limit_reached")

        # Cooldown check (skip if COOLDOWN_SECONDS == 0)
        if COOLDOWN_SECONDS > 0:
            stmt = select(Record.created_at).where(
                Record.name == data.name,
                Record.branch_id == data.branch_id,
            ).order_by(Record.created_at.desc()).limit(1)
            result = await db.execute(stmt)
            last_record = result.scalar()

            if last_record:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                diff = (now - last_record).total_seconds()
                if diff < COOLDOWN_SECONDS:
                    raise HTTPException(status_code=422, detail={
                        "error": "COOLDOWN_ACTIVE",
                        "message": f"รอ {COOLDOWN_SECONDS} วินาที ก่อนบันทึกครั้งถัดไป",
                        "detail": {"wait_seconds": int(COOLDOWN_SECONDS - diff)}
                    })

    elif data.type == "bulk":
        if data.participant_count and data.minutes > data.participant_count * MAX_BULK_MINUTES_PER_PERSON:
            raise HTTPException(status_code=422, detail={
                "error": "BULK_LIMIT_EXCEEDED",
                "message": f"ยอดเกิน {data.participant_count} คน × {MAX_BULK_MINUTES_PER_PERSON} นาที",
                "detail": {"attempted": data.minutes, "limit": data.participant_count * MAX_BULK_MINUTES_PER_PERSON}
            })

    return flags
