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
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """List participants with aggregated record stats, optional branch/status filter + pagination."""
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
    if status:
        stmt = stmt.where(Participant.status == status)
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


@router.post("/participants/merge-duplicate-codes")
async def merge_duplicate_codes(
    branch_id: str | None = None,
    dry_run: bool = True,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """รวม participants ที่ซ้ำ (branch_id + member_code เดียวกัน ทั้งคู่ status=approved).

    Winner = id สูงสุด (ตรงกับ deterministic ของ code_map ใน sync)
    Loser records:
      - วันซ้ำกับ winner → OR-merge sessions, ลบ loser record (กัน double-count)
      - วันไม่ซ้ำ → move participant_id ไป winner
    Loser participant → set status=rejected
    """
    # หา (branch_id, member_code) ที่ approved > 1
    dup_stmt = (
        select(Participant.branch_id, Participant.member_code, func.count().label("cnt"))
        .where(Participant.status == "approved", Participant.member_code.isnot(None))
        .group_by(Participant.branch_id, Participant.member_code)
        .having(func.count() > 1)
    )
    if branch_id:
        dup_stmt = dup_stmt.where(Participant.branch_id == branch_id)
    dup_rows = (await db.execute(dup_stmt)).all()

    merged_pairs = 0
    records_deleted = 0
    records_moved = 0
    losers_rejected = 0
    sample = []

    for row in dup_rows:
        bid, code = row.branch_id, row.member_code
        ps_result = await db.execute(
            select(Participant)
            .where(
                Participant.branch_id == bid,
                Participant.member_code == code,
                Participant.status == "approved",
            )
            .order_by(Participant.id)
        )
        ps = ps_result.scalars().all()
        if len(ps) < 2:
            continue
        winner = ps[-1]
        losers = ps[:-1]

        for loser in losers:
            # โหลด records ทั้งคู่ (index by date)
            w_recs = (await db.execute(
                select(Record).where(Record.participant_id == winner.id)
            )).scalars().all()
            w_by_date: dict = {r.date: r for r in w_recs}

            l_recs = (await db.execute(
                select(Record).where(Record.participant_id == loser.id)
            )).scalars().all()

            for lrec in l_recs:
                w = w_by_date.get(lrec.date)
                if w is not None:
                    # OR-merge sessions + คำนวณ minutes ใหม่ + ลบ loser record
                    w.morning_male = max(w.morning_male or 0, lrec.morning_male or 0)
                    w.afternoon_male = max(w.afternoon_male or 0, lrec.afternoon_male or 0)
                    w.evening_male = max(w.evening_male or 0, lrec.evening_male or 0)
                    w.minutes = (w.morning_male + w.afternoon_male + w.evening_male) * 5
                    if not dry_run:
                        await db.delete(lrec)
                    records_deleted += 1
                else:
                    if not dry_run:
                        lrec.participant_id = winner.id
                    records_moved += 1

            if not dry_run:
                loser.status = "rejected"
            losers_rejected += 1

        merged_pairs += 1
        if len(sample) < 15:
            sample.append({
                "branch_id": bid,
                "member_code": code,
                "winner_id": winner.id,
                "loser_ids": [l.id for l in losers],
            })

    if not dry_run:
        await db.commit()

    return {
        "dry_run": dry_run,
        "pairs": merged_pairs,
        "records_deleted": records_deleted,
        "records_moved": records_moved,
        "losers_rejected": losers_rejected,
        "sample": sample,
        "message": (
            f"ตรวจสอบพบ {merged_pairs} กลุ่มซ้ำ (ยังไม่แก้) — "
            f"จะลบ {records_deleted} records ซ้ำ, ย้าย {records_moved} records"
            if dry_run else
            f"รวมสำเร็จ {merged_pairs} กลุ่ม — ลบ {records_deleted} records ซ้ำ, "
            f"ย้าย {records_moved} records, reject loser {losers_rejected}"
        ),
    }


def _normalize_name(first: str | None, last: str | None) -> str:
    import re as _re
    def clean(s: str) -> str:
        s = _re.sub(r"[.\-_,()\[\]]+", " ", s or "")
        s = _re.sub(r"\s+", " ", s).strip().lower()
        return s
    return f"{clean(first or '')}|{clean(last or '')}"


@router.post("/participants/merge-duplicate-names")
async def merge_duplicate_names(
    branch_id: str | None = None,
    dry_run: bool = True,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """รวม participants ที่ (branch, normalized_name) ซ้ำ + ฝั่งหนึ่ง code=None.

    ใช้เมื่อ parser เก่าไม่แยก member_code ออกจากชื่อ (code=None)
    Winner = ตัวที่มี member_code (id สูงสุด), Loser = ตัวที่ code=None
    """
    all_result = await db.execute(
        select(Participant).where(Participant.status == "approved")
        .order_by(Participant.branch_id, Participant.id)
    )
    if branch_id:
        all_result = await db.execute(
            select(Participant).where(
                Participant.status == "approved",
                Participant.branch_id == branch_id,
            ).order_by(Participant.id)
        )
    all_ps = all_result.scalars().all()

    from collections import defaultdict
    groups: dict[tuple[str, str], list[Participant]] = defaultdict(list)
    for p in all_ps:
        key = (p.branch_id, _normalize_name(p.first_name, p.last_name))
        groups[key].append(p)

    merged_pairs = 0
    records_deleted = 0
    records_moved = 0
    losers_rejected = 0
    sample = []

    for (bid, name_key), ps in groups.items():
        if len(ps) < 2:
            continue
        coded = [p for p in ps if p.member_code]
        uncoded = [p for p in ps if not p.member_code]
        # ต้องมีอย่างน้อย 1 coded + 1 uncoded
        if not coded or not uncoded:
            continue
        # Winner = coded ที่ id สูงสุด (สอดคล้อง Fix A ใน sync)
        winner = max(coded, key=lambda p: p.id)
        losers = uncoded  # เฉพาะ uncoded — coded ตัวอื่นข้าม (อาจเป็นคนละคนจริง)

        for loser in losers:
            w_recs = (await db.execute(
                select(Record).where(Record.participant_id == winner.id)
            )).scalars().all()
            w_by_date: dict = {r.date: r for r in w_recs}

            l_recs = (await db.execute(
                select(Record).where(Record.participant_id == loser.id)
            )).scalars().all()

            for lrec in l_recs:
                w = w_by_date.get(lrec.date)
                if w is not None:
                    w.morning_male = max(w.morning_male or 0, lrec.morning_male or 0)
                    w.afternoon_male = max(w.afternoon_male or 0, lrec.afternoon_male or 0)
                    w.evening_male = max(w.evening_male or 0, lrec.evening_male or 0)
                    w.minutes = (w.morning_male + w.afternoon_male + w.evening_male) * 5
                    if not dry_run:
                        await db.delete(lrec)
                    records_deleted += 1
                else:
                    if not dry_run:
                        lrec.participant_id = winner.id
                    records_moved += 1

            if not dry_run:
                loser.status = "rejected"
            losers_rejected += 1

        merged_pairs += 1
        if len(sample) < 15:
            sample.append({
                "branch_id": bid,
                "name": name_key,
                "winner_id": winner.id,
                "winner_code": winner.member_code,
                "loser_ids": [l.id for l in losers],
            })

    if not dry_run:
        await db.commit()

    return {
        "dry_run": dry_run,
        "pairs": merged_pairs,
        "records_deleted": records_deleted,
        "records_moved": records_moved,
        "losers_rejected": losers_rejected,
        "sample": sample,
        "message": (
            f"ตรวจสอบพบ {merged_pairs} กลุ่มซ้ำ (name-based, ยังไม่แก้) — "
            f"จะลบ {records_deleted} records ซ้ำ, ย้าย {records_moved} records"
            if dry_run else
            f"รวมสำเร็จ {merged_pairs} กลุ่ม — ลบ {records_deleted} records ซ้ำ, "
            f"ย้าย {records_moved} records, reject loser {losers_rejected}"
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

    # ถ้าเปลี่ยน member_code — เช็คว่าไม่ซ้ำในสาขาเดียวกัน (approved เท่านั้น)
    new_code = (data.member_code or "").strip() or None
    if new_code and new_code != (p.member_code or ""):
        dup = (await db.execute(
            select(Participant).where(
                Participant.branch_id == data.branch_id,
                Participant.member_code == new_code,
                Participant.status == "approved",
                Participant.id != participant_id,
            )
        )).scalar_one_or_none()
        if dup:
            raise HTTPException(status_code=409, detail={
                "error": "MEMBER_CODE_CONFLICT",
                "message": f"member_code '{new_code}' ถูกใช้แล้วในสาขา {data.branch_id} (id={dup.id} {dup.first_name} {dup.last_name})",
            })
    p.branch_id = data.branch_id
    p.member_code = new_code
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
