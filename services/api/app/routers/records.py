"""Records API endpoints with CSV export."""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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

EXPORT_FIELDS_BULK = [
    "id", "type", "branch_id", "org_id", "name", "minutes",
    "participant_count", "minutes_per_person",
    "session_morning", "session_afternoon", "session_evening",
    "gender_male", "gender_female", "gender_unspecified",
    "date", "status", "submitted_by", "submitted_phone",
]

EXPORT_FIELDS_INDIVIDUAL = [
    "id", "type", "branch_id", "participant_id", "name", "minutes",
    "session_morning", "session_afternoon", "session_evening",
    "date", "status", "submitted_by",
]


@router.get("/records")
async def list_records(
    branch_id: str | None = None,
    record_type: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List records with optional filters."""
    stmt = select(Record).order_by(Record.date.desc(), Record.id.desc())
    if branch_id:
        stmt = stmt.where(Record.branch_id == branch_id)
    if record_type:
        stmt = stmt.where(Record.type == record_type)
    if status:
        stmt = stmt.where(Record.status == status)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        {
            "id": r.id, "type": r.type, "branch_id": r.branch_id,
            "org_id": r.org_id, "participant_id": r.participant_id,
            "name": r.name, "minutes": r.minutes,
            "participant_count": r.participant_count,
            "session_morning": r.session_morning,
            "session_afternoon": r.session_afternoon,
            "session_evening": r.session_evening,
            "gender_male": r.gender_male, "gender_female": r.gender_female,
            "gender_unspecified": r.gender_unspecified,
            "date": str(r.date), "status": r.status,
            "submitted_by": r.submitted_by,
        }
        for r in records
    ]


@router.get("/records/export")
async def export_records(
    branch_id: str | None = None,
    record_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export records as CSV."""
    stmt = select(Record).order_by(Record.date.desc(), Record.id.desc())
    if branch_id:
        stmt = stmt.where(Record.branch_id == branch_id)
    if record_type:
        stmt = stmt.where(Record.type == record_type)
    result = await db.execute(stmt)
    records = result.scalars().all()

    fields = EXPORT_FIELDS_BULK if record_type == "bulk" else EXPORT_FIELDS_INDIVIDUAL if record_type == "individual" else EXPORT_FIELDS_BULK
    filename = f"records-{record_type or 'all'}.csv"

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(fields)
    for r in records:
        writer.writerow([getattr(r, f, "") or "" for f in fields])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
