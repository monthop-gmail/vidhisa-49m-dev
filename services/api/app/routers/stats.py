"""Statistics API endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Branch, BranchGroup, DailyStat, Organization, Record

router = APIRouter()


@router.get("/stats/total")
async def get_total(db: AsyncSession = Depends(get_db)):
    """Get overall statistics across all branches and organizations."""
    stmt = select(
        func.coalesce(func.sum(Record.minutes), 0),
        func.count(Record.id),
        func.count(func.distinct(Record.branch_id)),
    ).where(Record.status == "approved")
    result = await db.execute(stmt)
    row = result.one()

    stmt_orgs = select(func.count(Organization.id))
    orgs = (await db.execute(stmt_orgs)).scalar()

    return {
        "total_minutes": row[0],
        "total_records": row[1],
        "total_branches": row[2],
        "total_orgs": orgs,
        "last_updated": None,
    }


@router.get("/stats/by-province")
async def get_by_province(db: AsyncSession = Depends(get_db)):
    """Get statistics grouped by province."""
    stmt = (
        select(
            Branch.province,
            Branch.province_code,
            func.coalesce(func.sum(Record.minutes), 0).label("total_minutes"),
            func.count(Record.id).label("total_records"),
        )
        .join(Record, Record.branch_id == Branch.id)
        .where(Record.status == "approved")
        .group_by(Branch.province, Branch.province_code)
        .order_by(func.sum(Record.minutes).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "province": r.province,
            "code": r.province_code,
            "minutes": r.total_minutes,
            "records": r.total_records,
        }
        for r in rows
    ]


@router.get("/stats/by-group")
async def get_by_group(db: AsyncSession = Depends(get_db)):
    """Get statistics grouped by branch regions.

    Only includes ORG-PLJ records, excluding external organizations.
    """
    groups_result = await db.execute(select(BranchGroup))
    groups = groups_result.scalars().all()

    out = []
    for g in groups:
        stmt = (
            select(
                func.coalesce(func.sum(Record.minutes), 0),
                func.count(func.distinct(Record.branch_id)),
            )
            .join(Branch, Record.branch_id == Branch.id)
            .where(
                Branch.group_id == g.id,
                Record.status == "approved",
                Record.org_id.like("%-00"),
            )
        )
        result = await db.execute(stmt)
        row = result.one()

        province_names = []
        for code in g.provinces or []:
            bs = await db.execute(
                select(func.distinct(Branch.province)).where(Branch.province_code == code),
            )
            name = bs.scalar()
            if name:
                province_names.append(name)

        out.append(
            {
                "group_id": g.id,
                "group_name": g.name,
                "provinces": province_names,
                "province_codes": g.provinces or [],
                "minutes": row[0],
                "branches_count": row[1],
            }
        )

    return sorted(out, key=lambda x: x["minutes"], reverse=True)


@router.get("/stats/by-branch")
async def get_by_branch(db: AsyncSession = Depends(get_db)):
    """Get statistics for individual branches.

    Only includes ORG-PLJ records.
    """
    stmt = (
        select(
            Branch.id,
            Branch.name,
            Branch.province,
            func.coalesce(func.sum(Record.minutes), 0).label("total"),
        )
        .join(Record, Record.branch_id == Branch.id)
        .where(
            Record.status == "approved",
            Record.org_id.like("%-00"),
        )
        .group_by(Branch.id, Branch.name, Branch.province)
        .order_by(func.sum(Record.minutes).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()
    return [{"branch_id": r[0], "branch_name": r[1], "province": r[2], "minutes": r[3]} for r in rows]


@router.get("/stats/daily")
async def get_daily(
    db: AsyncSession = Depends(get_db),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    """Get daily statistics with optional date range filter."""
    stmt = select(DailyStat).order_by(DailyStat.date)
    if from_date:
        stmt = stmt.where(DailyStat.date >= from_date)
    if to_date:
        stmt = stmt.where(DailyStat.date <= to_date)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [{"date": str(r.date), "minutes": r.total_minutes} for r in rows]
