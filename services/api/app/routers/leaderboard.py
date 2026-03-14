from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Record, Branch

router = APIRouter()


@router.get("/leaderboard")
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
    type: str = Query("branch"),
    limit: int = Query(10),
):
    if type == "org":
        stmt = select(
            Record.name,
            func.coalesce(func.sum(Record.minutes), 0).label("total"),
            Branch.name.label("branch_name"),
        ).join(Branch, Record.branch_id == Branch.id).where(
            Record.status == "approved", Record.type == "bulk"
        ).group_by(Record.name, Branch.name).order_by(func.sum(Record.minutes).desc()).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()
        return [
            {"rank": i + 1, "name": r[0], "branch": r[2], "minutes": r[1]}
            for i, r in enumerate(rows)
        ]

    else:  # branch
        stmt = select(
            Branch.id, Branch.name,
            func.coalesce(func.sum(Record.minutes), 0).label("total"),
        ).join(Record, Record.branch_id == Branch.id).where(
            Record.status == "approved"
        ).group_by(Branch.id, Branch.name).order_by(func.sum(Record.minutes).desc()).limit(limit)

        result = await db.execute(stmt)
        rows = result.all()
        return [
            {"rank": i + 1, "branch_id": r[0], "branch_name": r[1], "minutes": r[2]}
            for i, r in enumerate(rows)
        ]
