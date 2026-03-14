from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
from app.database import get_db
from app.models import Record, Branch, BranchGroup, ProvinceStat, DailyStat

router = APIRouter()


@router.get("/stats/total")
async def get_total(db: AsyncSession = Depends(get_db)):
    stmt = select(
        func.coalesce(func.sum(Record.minutes), 0),
        func.count(Record.id),
        func.count(func.distinct(Record.branch_id)),
    ).where(Record.status == "approved")
    result = await db.execute(stmt)
    row = result.one()

    stmt_orgs = select(func.count(func.distinct(Record.name))).where(
        Record.status == "approved", Record.type == "bulk"
    )
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
    stmt = select(ProvinceStat).order_by(ProvinceStat.total_minutes.desc())
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        {"province": r.province, "code": r.province_code, "minutes": r.total_minutes, "records": r.total_records}
        for r in rows
    ]


@router.get("/stats/by-group")
async def get_by_group(db: AsyncSession = Depends(get_db)):
    groups_result = await db.execute(select(BranchGroup))
    groups = groups_result.scalars().all()

    out = []
    for g in groups:
        stmt = select(
            func.coalesce(func.sum(Record.minutes), 0),
            func.count(func.distinct(Record.branch_id)),
        ).join(Branch, Record.branch_id == Branch.id).where(
            Branch.group_id == g.id, Record.status == "approved"
        )
        result = await db.execute(stmt)
        row = result.one()

        province_names = []
        for code in (g.provinces or []):
            ps = await db.execute(select(ProvinceStat.province).where(ProvinceStat.province_code == code))
            name = ps.scalar()
            if name:
                province_names.append(name)

        out.append({
            "group_id": g.id,
            "group_name": g.name,
            "provinces": province_names,
            "province_codes": g.provinces or [],
            "minutes": row[0],
            "branches_count": row[1],
        })

    return sorted(out, key=lambda x: x["minutes"], reverse=True)


@router.get("/stats/by-branch")
async def get_by_branch(db: AsyncSession = Depends(get_db)):
    stmt = select(
        Branch.id, Branch.name, Branch.province,
        func.coalesce(func.sum(Record.minutes), 0).label("total")
    ).join(Record, Record.branch_id == Branch.id).where(
        Record.status == "approved"
    ).group_by(Branch.id, Branch.name, Branch.province).order_by(func.sum(Record.minutes).desc())

    result = await db.execute(stmt)
    rows = result.all()
    return [
        {"branch_id": r[0], "branch_name": r[1], "province": r[2], "minutes": r[3]}
        for r in rows
    ]


@router.get("/stats/daily")
async def get_daily(
    db: AsyncSession = Depends(get_db),
    from_date: date = Query(None, alias="from"),
    to_date: date = Query(None, alias="to"),
):
    stmt = select(DailyStat).order_by(DailyStat.date)
    if from_date:
        stmt = stmt.where(DailyStat.date >= from_date)
    if to_date:
        stmt = stmt.where(DailyStat.date <= to_date)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [{"date": str(r.date), "minutes": r.total_minutes} for r in rows]
