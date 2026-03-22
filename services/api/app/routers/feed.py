"""Activity feed API endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Branch, Record

router = APIRouter()


@router.get("/feed")
async def get_feed(db: AsyncSession = Depends(get_db), limit: int = Query(20)):
    """Get recent activity feed of meditation records."""
    stmt = (
        select(Record, Branch.name.label("branch_name"))
        .join(Branch, Record.branch_id == Branch.id)
        .where(Record.status != "rejected")
        .order_by(Record.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    feed = []
    for record, branch_name in rows:
        if record.type == "individual":
            msg = f"คุณ{record.name} จาก{branch_name} เพิ่งสะสมเพิ่ม {record.minutes} นาที"
        else:
            msg = f"{record.name} ร่วมสะสมยอดรวม {record.minutes:,} นาที"

        feed.append(
            {
                "id": record.id,
                "message": msg,
                "minutes": record.minutes,
                "type": record.type,
                "timestamp": record.created_at.isoformat() if record.created_at else None,
            }
        )

    return feed
