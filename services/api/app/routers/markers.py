"""Map markers API endpoint for GPS locations."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Branch, Organization, Record

router = APIRouter()


@router.get("/markers")
async def get_markers(db: AsyncSession = Depends(get_db)):
    """Return GPS markers for branches and organizations with coordinates.

    Includes statistics for each location.
    """
    markers = []

    stmt = (
        select(
            Branch.id,
            Branch.name,
            Branch.province,
            Branch.latitude,
            Branch.longitude,
            func.coalesce(func.sum(Record.minutes), 0).label("minutes"),
            func.count(Record.id).label("records"),
        )
        .outerjoin(Record, (Record.branch_id == Branch.id) & (Record.status == "approved"))
        .where(Branch.latitude.isnot(None), Branch.longitude.isnot(None))
        .group_by(Branch.id, Branch.name, Branch.province, Branch.latitude, Branch.longitude)
    )

    result = await db.execute(stmt)
    for r in result.all():
        markers.append(
            {
                "type": "branch",
                "id": r.id,
                "name": r.name,
                "province": r.province,
                "lat": r.latitude,
                "lng": r.longitude,
                "minutes": r.minutes,
                "records": r.records,
            }
        )

    stmt = (
        select(
            Organization.id,
            Organization.name,
            Organization.org_type,
            Organization.province,
            Organization.latitude,
            Organization.longitude,
            Organization.branch_id,
            func.coalesce(func.sum(Record.minutes), 0).label("minutes"),
            func.count(Record.id).label("records"),
        )
        .outerjoin(
            Record,
            (Record.org_id == Organization.id) & (Record.status == "approved"),
        )
        .where(
            Organization.latitude.isnot(None),
            Organization.longitude.isnot(None),
        )
        .group_by(
            Organization.id,
            Organization.name,
            Organization.org_type,
            Organization.province,
            Organization.latitude,
            Organization.longitude,
            Organization.branch_id,
        )
    )
    result = await db.execute(stmt)
    for r in result.all():
        markers.append(
            {
                "type": "org",
                "id": r.id,
                "name": r.name,
                "org_type": r.org_type,
                "province": r.province,
                "branch_id": r.branch_id,
                "lat": r.latitude,
                "lng": r.longitude,
                "minutes": r.minutes,
                "records": r.records,
            }
        )

    return markers
