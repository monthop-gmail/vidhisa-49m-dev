from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Branch, Record

router = APIRouter()


@router.get("/markers")
async def get_markers(db: AsyncSession = Depends(get_db)):
    """Return GPS markers: branches + bulk orgs that have coordinates."""
    markers = []

    # 1) Branch markers (with stats)
    stmt = select(
        Branch.id, Branch.name, Branch.province,
        Branch.latitude, Branch.longitude,
        func.coalesce(func.sum(Record.minutes), 0).label("minutes"),
        func.count(Record.id).label("records"),
    ).outerjoin(Record, (Record.branch_id == Branch.id) & (Record.status == "approved")
    ).where(
        Branch.latitude.isnot(None), Branch.longitude.isnot(None)
    ).group_by(Branch.id, Branch.name, Branch.province, Branch.latitude, Branch.longitude)

    result = await db.execute(stmt)
    for r in result.all():
        markers.append({
            "type": "branch",
            "id": r.id,
            "name": r.name,
            "province": r.province,
            "lat": r.latitude,
            "lng": r.longitude,
            "minutes": r.minutes,
            "records": r.records,
        })

    # 2) Bulk org markers (records that have GPS)
    stmt = select(
        Record.name, Record.minutes, Record.latitude, Record.longitude,
        Branch.name.label("branch_name"),
    ).join(Branch, Record.branch_id == Branch.id).where(
        Record.type == "bulk",
        Record.status == "approved",
        Record.latitude.isnot(None),
        Record.longitude.isnot(None),
    )
    result = await db.execute(stmt)
    for r in result.all():
        markers.append({
            "type": "org",
            "name": r.name,
            "branch": r.branch_name,
            "lat": r.latitude,
            "lng": r.longitude,
            "minutes": r.minutes,
        })

    return markers
