"""Records API endpoints with CSV export."""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.anti_fraud import validate_record
from app.database import get_db
from app.events import publish
from app.models import Branch, Organization, Record
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
    "morning_male", "morning_female", "morning_unspecified",
    "afternoon_male", "afternoon_female", "afternoon_unspecified",
    "evening_male", "evening_female", "evening_unspecified",
    "date", "status", "submitted_by", "submitted_phone",
]

EXPORT_FIELDS_INDIVIDUAL = [
    "id", "type", "branch_id", "participant_id", "name", "minutes",
    "morning_male", "morning_female", "morning_unspecified",
    "afternoon_male", "afternoon_female", "afternoon_unspecified",
    "evening_male", "evening_female", "evening_unspecified",
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
            "morning_male": r.morning_male, "morning_female": r.morning_female,
            "morning_unspecified": r.morning_unspecified,
            "afternoon_male": r.afternoon_male, "afternoon_female": r.afternoon_female,
            "afternoon_unspecified": r.afternoon_unspecified,
            "evening_male": r.evening_male, "evening_female": r.evening_female,
            "evening_unspecified": r.evening_unspecified,
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


@router.post("/records/import")
async def import_records(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import records from CSV. Upsert by branch_id + org_id + name + date."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail={"error": "INVALID_FILE", "message": "รองรับเฉพาะไฟล์ .csv"})

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    required = {"type", "branch_id", "name", "minutes", "date"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail={
            "error": "INVALID_HEADER",
            "message": f"CSV ต้องมีคอลัมน์: {', '.join(sorted(required))}",
        })

    branch_result = await db.execute(select(Branch.id))
    valid_branches = {r[0] for r in branch_result.all()}
    org_result = await db.execute(select(Organization.id))
    valid_orgs = {r[0] for r in org_result.all()}

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        rec_type = (row.get("type") or "").strip()
        branch_id = (row.get("branch_id") or "").strip()
        name = (row.get("name") or "").strip()
        minutes_str = (row.get("minutes") or "").strip()
        date_str = (row.get("date") or "").strip()
        org_id = (row.get("org_id") or "").strip()

        if not rec_type or not branch_id or not name or not minutes_str or not date_str:
            errors.append(f"แถว {i}: ขาดข้อมูลที่จำเป็น")
            continue
        if branch_id not in valid_branches:
            errors.append(f"แถว {i}: branch_id '{branch_id}' ไม่มีในระบบ")
            continue
        if org_id and org_id not in valid_orgs:
            errors.append(f"แถว {i}: org_id '{org_id}' ไม่มีในระบบ")
            continue

        minutes = int(minutes_str)
        pc_str = (row.get("participant_count") or "").strip()
        mpp_str = (row.get("minutes_per_person") or "").strip()

        fields = {
            "type": rec_type,
            "branch_id": branch_id,
            "name": name,
            "org_id": org_id or None,
            "minutes": minutes,
            "participant_count": int(pc_str) if pc_str else None,
            "minutes_per_person": int(mpp_str) if mpp_str else None,
            "morning_male": int((row.get("morning_male") or "0").strip() or "0"),
            "morning_female": int((row.get("morning_female") or "0").strip() or "0"),
            "morning_unspecified": int((row.get("morning_unspecified") or "0").strip() or "0"),
            "afternoon_male": int((row.get("afternoon_male") or "0").strip() or "0"),
            "afternoon_female": int((row.get("afternoon_female") or "0").strip() or "0"),
            "afternoon_unspecified": int((row.get("afternoon_unspecified") or "0").strip() or "0"),
            "evening_male": int((row.get("evening_male") or "0").strip() or "0"),
            "evening_female": int((row.get("evening_female") or "0").strip() or "0"),
            "evening_unspecified": int((row.get("evening_unspecified") or "0").strip() or "0"),
            "date": date_str,
            "status": (row.get("status") or "pending").strip(),
            "submitted_by": (row.get("submitted_by") or "").strip() or None,
            "submitted_phone": (row.get("submitted_phone") or "").strip() or None,
        }

        # Upsert
        existing = None
        if org_id:
            stmt = select(Record).where(
                Record.branch_id == branch_id, Record.org_id == org_id,
                Record.name == name, Record.date == date_str,
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(Record(**fields))
            created += 1

    await db.commit()
    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "message": f"นำเข้าสำเร็จ: สร้างใหม่ {created}, อัพเดท {updated}" + (f", ข้อผิดพลาด {len(errors)} แถว" if errors else ""),
    }


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
        existing.morning_male = data.morning_male
        existing.morning_female = data.morning_female
        existing.morning_unspecified = data.morning_unspecified
        existing.afternoon_male = data.afternoon_male
        existing.afternoon_female = data.afternoon_female
        existing.afternoon_unspecified = data.afternoon_unspecified
        existing.evening_male = data.evening_male
        existing.evening_female = data.evening_female
        existing.evening_unspecified = data.evening_unspecified
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
        morning_male=data.morning_male,
        morning_female=data.morning_female,
        morning_unspecified=data.morning_unspecified,
        afternoon_male=data.afternoon_male,
        afternoon_female=data.afternoon_female,
        afternoon_unspecified=data.afternoon_unspecified,
        evening_male=data.evening_male,
        evening_female=data.evening_female,
        evening_unspecified=data.evening_unspecified,
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
