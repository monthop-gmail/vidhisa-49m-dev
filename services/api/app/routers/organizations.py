from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Organization, Record
from app.schemas import OrganizationCreate, OrganizationResponse

router = APIRouter()


@router.get("/organizations")
async def list_organizations(db: AsyncSession = Depends(get_db)):
    stmt = select(
        Organization.id, Organization.name, Organization.org_type,
        Organization.branch_id, Organization.province,
        Organization.latitude, Organization.longitude, Organization.contact,
        func.coalesce(func.sum(Record.minutes), 0).label("total_minutes"),
        func.count(Record.id).label("total_records"),
    ).outerjoin(
        Record, (Record.org_id == Organization.id) & (Record.status == "approved")
    ).group_by(
        Organization.id, Organization.name, Organization.org_type,
        Organization.branch_id, Organization.province,
        Organization.latitude, Organization.longitude, Organization.contact,
    ).order_by(Organization.name)

    result = await db.execute(stmt)
    return [
        {
            "id": r.id, "name": r.name, "org_type": r.org_type,
            "branch_id": r.branch_id, "province": r.province,
            "latitude": r.latitude, "longitude": r.longitude,
            "contact": r.contact,
            "total_minutes": r.total_minutes, "total_records": r.total_records,
        }
        for r in result.all()
    ]


@router.get("/organizations/{org_id}")
async def get_organization(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบองค์กร"})

    stmt = select(
        func.coalesce(func.sum(Record.minutes), 0),
        func.count(Record.id),
    ).where(Record.org_id == org_id, Record.status == "approved")
    stats = (await db.execute(stmt)).one()

    return {
        "id": org.id, "name": org.name, "org_type": org.org_type,
        "branch_id": org.branch_id, "province": org.province,
        "latitude": org.latitude, "longitude": org.longitude,
        "contact": org.contact,
        "total_minutes": stats[0], "total_records": stats[1],
    }


@router.post("/organizations", status_code=201)
async def create_organization(data: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Organization).where(Organization.id == data.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail={"error": "DUPLICATE_ID", "message": "รหัสองค์กรซ้ำ"})

    org = Organization(
        id=data.id,
        name=data.name,
        org_type=data.org_type,
        branch_id=data.branch_id,
        province=data.province,
        latitude=data.latitude,
        longitude=data.longitude,
        contact=data.contact,
    )
    db.add(org)
    await db.commit()
    return {"id": org.id, "name": org.name, "message": "สร้างองค์กรสำเร็จ"}


@router.put("/organizations/{org_id}")
async def update_organization(org_id: str, data: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบองค์กร"})

    org.name = data.name
    org.org_type = data.org_type
    org.branch_id = data.branch_id
    org.province = data.province
    org.latitude = data.latitude
    org.longitude = data.longitude
    org.contact = data.contact
    await db.commit()
    return {"id": org.id, "name": org.name, "message": "อัพเดทองค์กรสำเร็จ"}
