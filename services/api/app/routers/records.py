"""Records API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anti_fraud import validate_record
from app.database import get_db
from app.events import publish
from app.models import Record
from app.schemas import ApproveRequest, RecordCreate, RecordResponse, RejectRequest

router = APIRouter()


@router.post("/records", response_model=RecordResponse, status_code=201)
async def create_record(data: RecordCreate, db: AsyncSession = Depends(get_db)):
    """Create a new meditation record.

    Validates against anti-fraud rules and publishes an event on success.
    """
    flags = await validate_record(data, db)

    record = Record(
        type=data.type,
        branch_id=data.branch_id,
        name=data.name,
        org_id=data.org_id,
        minutes=data.minutes,
        participant_count=data.participant_count,
        minutes_per_person=data.minutes_per_person,
        date=data.date,
        photo_url=data.photo_url,
        latitude=data.latitude,
        longitude=data.longitude,
        submitted_by=data.submitted_by,
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


@router.patch("/records/{record_id}/approve")
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


@router.patch("/records/{record_id}/reject")
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
