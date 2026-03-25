"""Records API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anti_fraud import validate_record
from app.database import get_db
from app.events import publish
from app.models import Record
from app.schemas import (
    ApproveRequest,
    RecordCreate,
    RecordResponse,
    RejectRequest,
    StatusResponse,
)

router = APIRouter()


@router.post("/records", response_model=RecordResponse, status_code=201)
async def create_record(data: RecordCreate, db: AsyncSession = Depends(get_db)):
    """Create a new meditation record.

    Validates against anti-fraud rules and publishes an event on success.
    """
    flags = await validate_record(data, db)

    # Upsert: ถ้า branch_id + org_id + name + date ซ้ำ → อัพเดตแทน
    existing = None
    if data.org_id:
        stmt = select(Record).where(
            Record.branch_id == data.branch_id,
            Record.org_id == data.org_id,
            Record.name == data.name,
            Record.date == data.date,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

    if existing:
        existing.minutes = data.minutes
        existing.participant_count = data.participant_count
        existing.minutes_per_person = data.minutes_per_person
        existing.session_morning = data.session_morning
        existing.session_afternoon = data.session_afternoon
        existing.session_evening = data.session_evening
        existing.gender_male = data.gender_male
        existing.gender_female = data.gender_female
        existing.gender_unspecified = data.gender_unspecified
        existing.submitted_by = data.submitted_by
        existing.submitted_phone = data.submitted_phone
        existing.flags = flags
        existing.status = "pending"
        await db.commit()
        await db.refresh(existing)
        await publish("record")
        return RecordResponse(
            id=existing.id,
            status="pending",
            message="อัพเดตบันทึกสำเร็จ รอสาขาตรวจสอบ",
        )

    record = Record(
        type=data.type,
        branch_id=data.branch_id,
        name=data.name,
        org_id=data.org_id,
        participant_id=data.participant_id,
        minutes=data.minutes,
        participant_count=data.participant_count,
        minutes_per_person=data.minutes_per_person,
        session_morning=data.session_morning,
        session_afternoon=data.session_afternoon,
        session_evening=data.session_evening,
        gender_male=data.gender_male,
        gender_female=data.gender_female,
        gender_unspecified=data.gender_unspecified,
        date=data.date,
        photo_url=data.photo_url,
        latitude=data.latitude,
        longitude=data.longitude,
        submitted_by=data.submitted_by,
        submitted_phone=data.submitted_phone,
        status="pending",
        flags=flags,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    await publish("record")
    return RecordResponse(
        id=record.id,
        status="pending",
        message="บันทึกสำเร็จ รอสาขาตรวจสอบ",
    )


@router.patch("/records/{record_id}/approve", response_model=StatusResponse)
async def approve_record(record_id: int, data: ApproveRequest, db: AsyncSession = Depends(get_db)):
    """Approve a pending meditation record."""
    result = await db.execute(select(Record).where(Record.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "ไม่พบรายการ"},
        )

    record.status = "approved"
    record.approved_by = data.approved_by
    await db.commit()
    await publish("approved")
    return {"id": record_id, "status": "approved"}


@router.patch("/records/{record_id}/reject", response_model=StatusResponse)
async def reject_record(record_id: int, data: RejectRequest, db: AsyncSession = Depends(get_db)):
    """Reject a pending meditation record."""
    result = await db.execute(select(Record).where(Record.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "ไม่พบรายการ"},
        )

    record.status = "rejected"
    record.flags = (record.flags or []) + [f"rejected: {data.reason}"]
    await db.commit()
    await publish("rejected")
    return {"id": record_id, "status": "rejected"}
