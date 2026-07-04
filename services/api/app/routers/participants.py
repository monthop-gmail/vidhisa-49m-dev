"""Participants API endpoints — individual registration with CSV import/export."""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_optional, require_central_admin, scoped_branch_filter
from app.branch_auth import check_branch_access
from app.database import get_db
from app.models import Branch, Participant, Record, User
from app.schemas import ImportResult, ParticipantCreate, ParticipantResponse

router = APIRouter()

EXPORT_FIELDS = [
    "id", "branch_id", "prefix", "first_name", "last_name",
    "gender", "age", "sub_district", "district", "province",
    "phone", "line_id", "enrolled_date",
]


@router.get("/participants", response_model=list[ParticipantResponse])
async def list_participants(
    branch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """List participants with aggregated record stats, optional branch filter + pagination."""
    branch_filter = scoped_branch_filter(user, branch_id)
    stmt = (
        select(
            Participant,
            func.coalesce(func.sum(Record.minutes), 0).label("total_minutes"),
            func.count(Record.id).label("total_records"),
        )
        .outerjoin(
            Record,
            (Record.participant_id == Participant.id) & (Record.status == "approved"),
        )
        .group_by(Participant.id)
        .order_by(Participant.first_name)
    )
    if isinstance(branch_filter, list):
        stmt = stmt.where(Participant.branch_id.in_(branch_filter))
    elif branch_filter:
        stmt = stmt.where(Participant.branch_id == branch_filter)
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [
        ParticipantResponse.model_validate({
            **{c.name: getattr(r.Participant, c.name) for c in Participant.__table__.columns},
            "total_minutes": r.total_minutes,
            "total_records": r.total_records,
        })
        for r in result.all()
    ]


@router.get("/participants/export")
async def export_participants(
    branch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export participants as CSV with UTF-8 BOM."""
    stmt = select(Participant).order_by(Participant.branch_id, Participant.first_name)
    if branch_id:
        stmt = stmt.where(Participant.branch_id == branch_id)
    result = await db.execute(stmt)
    participants = result.scalars().all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(EXPORT_FIELDS)
    for p in participants:
        writer.writerow([getattr(p, f) or "" for f in EXPORT_FIELDS])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=participants.csv"},
    )


@router.post("/participants/import", response_model=ImportResult)
async def import_participants(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import participants from CSV. Creates new records based on branch_id + name."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail={"error": "INVALID_FILE", "message": "รองรับเฉพาะไฟล์ .csv"})

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    required = {"branch_id", "first_name", "last_name"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=400, detail={
            "error": "INVALID_HEADER",
            "message": f"CSV ต้องมีคอลัมน์: {', '.join(sorted(required))}",
        })

    branch_result = await db.execute(select(Branch.id))
    valid_branches = {r[0] for r in branch_result.all()}

    created = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        branch_id = (row.get("branch_id") or "").strip()
        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()

        if not branch_id or not first_name or not last_name:
            errors.append(f"แถว {i}: ขาด branch_id, first_name หรือ last_name")
            continue
        if branch_id not in valid_branches:
            errors.append(f"แถว {i}: branch_id '{branch_id}' ไม่มีในระบบ")
            continue

        age_str = (row.get("age") or "").strip()
        p = Participant(
            branch_id=branch_id,
            prefix=(row.get("prefix") or "").strip() or None,
            first_name=first_name,
            last_name=last_name,
            gender=(row.get("gender") or "").strip() or None,
            age=int(age_str) if age_str else None,
            sub_district=(row.get("sub_district") or "").strip() or None,
            district=(row.get("district") or "").strip() or None,
            province=(row.get("province") or "").strip() or None,
            phone=(row.get("phone") or "").strip() or None,
            line_id=(row.get("line_id") or "").strip() or None,
            enrolled_date=(row.get("enrolled_date") or "").strip() or None,
            privacy_accepted=True,
        )
        db.add(p)
        created += 1

    await db.commit()
    return {
        "created": created,
        "updated": 0,
        "errors": errors,
        "message": f"นำเข้าสำเร็จ: สร้างใหม่ {created}" + (f", ข้อผิดพลาด {len(errors)} แถว" if errors else ""),
    }


@router.post("/participants/reject-orphans")
async def reject_orphan_participants(
    branch_id: str | None = None,
    dry_run: bool = True,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject participants ที่มี 0 approved records (เดา: ชื่อเก่า/ซ้ำที่ไม่มีบันทึกผูก).

    dry_run=true (default) → คืน list เฉพาะ ไม่แก้ DB
    dry_run=false → set status='rejected' ให้ทุก orphan
    """
    stmt = (
        select(Participant)
        .outerjoin(Record, (Record.participant_id == Participant.id) & (Record.status == "approved"))
        .where(Participant.status == "approved")
        .group_by(Participant.id)
        .having(func.count(Record.id) == 0)
        .order_by(Participant.branch_id, Participant.id)
    )
    if branch_id:
        stmt = stmt.where(Participant.branch_id == branch_id)
    result = await db.execute(stmt)
    orphans = result.scalars().all()

    rejected_ids = []
    if not dry_run:
        for p in orphans:
            p.status = "rejected"
            rejected_ids.append(p.id)
        await db.commit()

    return {
        "dry_run": dry_run,
        "count": len(orphans),
        "rejected_ids": rejected_ids,
        "sample": [
            {"id": p.id, "branch_id": p.branch_id, "member_code": p.member_code,
             "prefix": p.prefix, "first_name": p.first_name, "last_name": p.last_name}
            for p in orphans[:30]
        ],
        "message": (
            f"ตรวจสอบพบ {len(orphans)} orphan participants (ยังไม่แก้)"
            if dry_run else
            f"reject {len(orphans)} orphan participants แล้ว"
        ),
    }


@router.post("/participants/restore-with-records")
async def restore_participants_with_records(
    branch_id: str | None = None,
    dry_run: bool = True,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """คืนสถานะ approved ให้ participants ที่ status=rejected แต่ยังมี approved records ผูกอยู่.

    (เกิดจาก sync ผูก records เข้า rejected participant — zombie link)
    """
    stmt = (
        select(Participant)
        .join(Record, (Record.participant_id == Participant.id) & (Record.status == "approved"))
        .where(Participant.status == "rejected")
        .group_by(Participant.id)
        .having(func.count(Record.id) > 0)
        .order_by(Participant.branch_id, Participant.id)
    )
    if branch_id:
        stmt = stmt.where(Participant.branch_id == branch_id)
    result = await db.execute(stmt)
    victims = result.scalars().all()

    restored_ids = []
    if not dry_run:
        for p in victims:
            p.status = "approved"
            restored_ids.append(p.id)
        await db.commit()

    return {
        "dry_run": dry_run,
        "count": len(victims),
        "restored_ids": restored_ids,
        "sample": [
            {"id": p.id, "branch_id": p.branch_id, "member_code": p.member_code,
             "prefix": p.prefix, "first_name": p.first_name, "last_name": p.last_name}
            for p in victims[:30]
        ],
        "message": (
            f"ตรวจสอบพบ {len(victims)} participants ที่ rejected แต่ยังมี records (ยังไม่แก้)"
            if dry_run else
            f"restore {len(victims)} participants กลับเป็น approved แล้ว"
        ),
    }


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
    """Register a new individual participant. 1 คน = 1 สาขา (ชื่อ+นามสกุลซ้ำไม่ได้)."""
    # Check duplicate: ชื่อ+นามสกุลเดียวกัน ไม่ว่าสาขาไหน
    dup_stmt = select(Participant).where(
        Participant.first_name == data.first_name,
        Participant.last_name == data.last_name,
    )
    dup_result = await db.execute(dup_stmt)
    existing = dup_result.scalar_one_or_none()
    if existing:
        if existing.branch_id == data.branch_id:
            raise HTTPException(status_code=409, detail={
                "error": "DUPLICATE",
                "message": f"'{data.first_name} {data.last_name}' ลงทะเบียนในสาขา {data.branch_id} แล้ว",
            })
        else:
            raise HTTPException(status_code=409, detail={
                "error": "ALREADY_REGISTERED",
                "message": f"'{data.first_name} {data.last_name}' ลงทะเบียนในสาขา {existing.branch_id} แล้ว (1 คน 1 สาขา) — ใช้ API ย้ายสาขาแทน",
            })

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


@router.patch("/participants/{participant_id}/transfer")
async def transfer_participant(participant_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Transfer participant to a different branch."""
    new_branch = (data.get("branch_id") or "").strip()
    if not new_branch:
        raise HTTPException(status_code=400, detail={"error": "MISSING_BRANCH", "message": "กรุณาระบุ branch_id ใหม่"})

    # Check branch exists
    branch_check = await db.execute(select(Branch).where(Branch.id == new_branch))
    if not branch_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"error": "BRANCH_NOT_FOUND", "message": f"ไม่พบสาขา '{new_branch}'"})

    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบผู้เข้าร่วม"})

    old_branch = p.branch_id
    p.branch_id = new_branch
    await db.commit()
    return {
        "id": p.id,
        "name": f"{p.first_name} {p.last_name}",
        "old_branch": old_branch,
        "new_branch": new_branch,
        "message": f"ย้ายจากสาขา {old_branch} → {new_branch} สำเร็จ",
    }


@router.patch("/participants/{participant_id}/approve")
async def approve_participant(participant_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Approve a pending participant."""
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบผู้เข้าร่วม"})
    if p.branch_id:
        check_branch_access(user, p.branch_id)
    p.status = "approved"
    await db.commit()
    return {"id": p.id, "status": "approved"}


@router.patch("/participants/{participant_id}/reject")
async def reject_participant(participant_id: int, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Reject a pending participant."""
    result = await db.execute(select(Participant).where(Participant.id == participant_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบผู้เข้าร่วม"})
    if p.branch_id:
        check_branch_access(user, p.branch_id)
    p.status = "rejected"
    await db.commit()
    return {"id": p.id, "status": "rejected"}
