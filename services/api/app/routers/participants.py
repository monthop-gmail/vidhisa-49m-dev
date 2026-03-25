"""Participants API endpoints — individual registration."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Participant
from app.schemas import ParticipantCreate, ParticipantResponse

router = APIRouter()


@router.get("/participants", response_model=list[ParticipantResponse])
async def list_participants(
    branch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List participants, optionally filtered by branch."""
    stmt = select(Participant).order_by(Participant.first_name)
    if branch_id:
        stmt = stmt.where(Participant.branch_id == branch_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/participants/{participant_id}", response_model=ParticipantResponse)
async def get_participant(participant_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific participant."""
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบผู้เข้าร่วม"})
    return p


@router.post("/participants", status_code=201)
async def create_participant(data: ParticipantCreate, db: AsyncSession = Depends(get_db)):
    """Register a new individual participant."""
    p = Participant(
        branch_id=data.branch_id,
        prefix=data.prefix,
        first_name=data.first_name,
        last_name=data.last_name,
        gender=data.gender,
        age=data.age,
        sub_district=data.sub_district,
        district=data.district,
        province=data.province,
        phone=data.phone,
        line_id=data.line_id,
        enrolled_date=data.enrolled_date,
        privacy_accepted=data.privacy_accepted,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {"id": p.id, "name": f"{p.first_name} {p.last_name}", "message": "ลงทะเบียนสำเร็จ"}


@router.put("/participants/{participant_id}")
async def update_participant(participant_id: int, data: ParticipantCreate, db: AsyncSession = Depends(get_db)):
    """Update participant details."""
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบผู้เข้าร่วม"})

    p.branch_id = data.branch_id
    p.prefix = data.prefix
    p.first_name = data.first_name
    p.last_name = data.last_name
    p.gender = data.gender
    p.age = data.age
    p.sub_district = data.sub_district
    p.district = data.district
    p.province = data.province
    p.phone = data.phone
    p.line_id = data.line_id
    p.enrolled_date = data.enrolled_date
    p.privacy_accepted = data.privacy_accepted
    await db.commit()
    return {"id": p.id, "name": f"{p.first_name} {p.last_name}", "message": "อัพเดทสำเร็จ"}
