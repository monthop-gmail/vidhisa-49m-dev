from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Record

router = APIRouter()


@router.get("/branch/{branch_id}/pending")
async def get_pending(branch_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Record).where(
        Record.branch_id == branch_id,
        Record.status == "pending"
    ).order_by(Record.created_at.desc())

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "type": r.type,
            "name": r.name,
            "minutes": r.minutes,
            "date": str(r.date),
            "status": r.status,
            "flags": r.flags or [],
        }
        for r in rows
    ]
