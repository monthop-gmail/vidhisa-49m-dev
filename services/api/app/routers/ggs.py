"""Google Sheet (GGS) integration — pull data from shared Google Sheets."""

import csv
import io
import json
import re
from datetime import date as date_type, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_central_admin
from app.branch_auth import check_branch_access
from app.database import get_db
from app.models import Branch, Organization, Participant, Record, User

router = APIRouter()

GGS_URL_TYPES = ["ggs_url_org", "ggs_url_participant", "ggs_url_record_bulk", "ggs_url_record_ind"]

GGS_ORG_ENROLLMENT_URL = "https://docs.google.com/spreadsheets/d/1COYcLXAliYPqpVEPev22MJtiKHO6b7-drVGjhZxNpOY/gviz/tq?tqx=out:json&headers=1"


def extract_sheet_id(url: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise HTTPException(status_code=400, detail={"error": "INVALID_URL", "message": "URL ไม่ใช่ Google Sheet"})
    return match.group(1)


def build_csv_url(sheet_id: str, sheet_name: str = None) -> str:
    if sheet_name:
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"


def build_json_url(sheet_id: str, sheet_name: str = None) -> str:
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json&headers=1"
    return f"{base}&sheet={sheet_name}" if sheet_name else base


async def fetch_csv(url: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail={
                "error": "GGS_FETCH_FAILED",
                "message": f"ดึง Google Sheet ไม่ได้ (HTTP {res.status_code})",
            })
    text = res.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


async def fetch_gviz_rows(url: str) -> list[dict]:
    """Fetch gviz JSON and return rows as dicts.

    For date cells, extracts date from raw value (Date(y,m,d)) into ISO format
    — avoids locale ambiguity (M/D vs D/M) in the formatted value.
    For other cells, prefers formatted value (f) to preserve custom formats like 058.
    """
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail={
                "error": "GGS_FETCH_FAILED",
                "message": f"ดึง Google Sheet ไม่ได้ (HTTP {res.status_code})",
            })
    raw = res.text
    start = raw.find("(") + 1
    end = raw.rfind(")")
    data = json.loads(raw[start:end])
    table = data["table"]
    col_labels = [c.get("label", "") for c in table["cols"]]
    col_types = [c.get("type", "") for c in table["cols"]]

    rows = []
    for row in table["rows"]:
        d = {}
        for label, ctype, cell in zip(col_labels, col_types, row["c"]):
            if cell is None:
                d[label] = ""
                continue
            v = cell.get("v")
            f = cell.get("f")
            if ctype in ("date", "datetime") and isinstance(v, str) and v.startswith("Date("):
                m = re.match(r"Date\((\d+),(\d+),(\d+)", v)
                if m:
                    y, mo, dd = int(m.group(1)), int(m.group(2)) + 1, int(m.group(3))
                    d[label] = f"{y:04d}-{mo:02d}-{dd:02d}"
                    continue
            if f:
                d[label] = str(f)
            elif v is not None:
                d[label] = str(v)
            else:
                d[label] = ""
        rows.append(d)
    return rows


def parse_thai_date(s: str) -> date_type | None:
    """Parse date like '5/4/2026' (D/M/YYYY) or '2026-04-05'."""
    s = s.strip()
    if not s:
        return None
    if '-' in s:
        return date_type.fromisoformat(s)
    parts = s.split('/')
    if len(parts) == 3:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        return date_type(y, m, d)
    return None


def parse_sessions(s: str) -> tuple[bool, bool, bool]:
    """Parse 'เช้า 5 นาที, กลางวัน 5 นาที, เย็น 5 นาที'."""
    morning = 'เช้า' in s
    afternoon = 'กลางวัน' in s
    evening = 'เย็น' in s
    return morning, afternoon, evening


# === Set URLs ===

def _normalize_ggs_url(raw: str) -> str | None:
    """Normalize any Google Sheets URL to canonical gviz JSON form.

    Accepts /edit, /edit?usp=sharing, /gviz/tq?..., /pubhtml, etc.
    Returns None if raw is empty; raw unchanged if not a Google Sheets URL.
    """
    s = (raw or "").strip()
    if not s:
        return None
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", s)
    if not m:
        return s
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/gviz/tq?tqx=out:json"


@router.patch("/ggs/set-url")
async def set_ggs_url(
    data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set Google Sheet URLs for a branch."""
    branch_id = data.get("branch_id", "").strip() or user.branch_id
    if not branch_id:
        raise HTTPException(status_code=400, detail={"error": "MISSING", "message": "กรุณาระบุ branch_id"})
    check_branch_access(user, branch_id)

    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"ไม่พบสาขา {branch_id}"})

    updated = []
    for field in GGS_URL_TYPES:
        if field in data:
            setattr(branch, field, _normalize_ggs_url(data[field]))
            updated.append(field)

    # Backward compat: "url" sets all or specific type
    if "url" in data and "url_type" in data:
        url_type = data["url_type"]
        field = f"ggs_url_{url_type}" if not url_type.startswith("ggs_url_") else url_type
        if hasattr(branch, field):
            setattr(branch, field, _normalize_ggs_url(data["url"]))
            updated.append(field)
    elif "url" in data and not updated:
        # Default: set record_ind (most common)
        branch.ggs_url_record_ind = _normalize_ggs_url(data["url"])
        updated.append("ggs_url_record_ind")

    await db.commit()
    return {
        "branch_id": branch_id,
        "updated": updated,
        "ggs_url_org": branch.ggs_url_org,
        "ggs_url_participant": branch.ggs_url_participant,
        "ggs_url_record_bulk": branch.ggs_url_record_bulk,
        "ggs_url_record_ind": branch.ggs_url_record_ind,
        "message": f"บันทึก URL สำเร็จ ({len(updated)} fields)",
    }


# === Sync branch GGS ===

@router.post("/ggs/sync-branch")
async def sync_branch_ggs(
    data: dict = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync all GGS data for a branch."""
    data = data or {}
    branch_id = data.get("branch_id", "").strip() or user.branch_id
    if not branch_id:
        raise HTTPException(status_code=400, detail={"error": "MISSING", "message": "กรุณาระบุ branch_id"})
    check_branch_access(user, branch_id)

    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"ไม่พบสาขา {branch_id}"})

    results = {}
    sync_types = data.get("types", ["record_ind", "record_bulk", "org", "participant"])
    auto_approve = bool(data.get("auto_approve", False))

    if "record_ind" in sync_types and branch.ggs_url_record_ind:
        results["record_ind"] = await _sync_record_ind(branch.ggs_url_record_ind, branch_id, db, auto_approve)

    if "record_bulk" in sync_types and branch.ggs_url_record_bulk:
        results["record_bulk"] = await _sync_record_bulk(branch.ggs_url_record_bulk, branch_id, db)

    if "org" in sync_types and branch.ggs_url_org:
        results["org"] = await _sync_org(branch.ggs_url_org, branch_id, db)

    if "participant" in sync_types and branch.ggs_url_participant:
        results["participant"] = await _sync_participant(branch.ggs_url_participant, branch_id, db)

    if not results:
        return {"branch_id": branch_id, "message": "ไม่มี GGS URL ที่ตั้งไว้ — กรุณาบันทึก URL ก่อน"}

    return {"branch_id": branch_id, **results}


# === Sync: Individual Records (format จาก อ.เต้) ===

async def _sync_record_ind(url: str, branch_id: str, db: AsyncSession, auto_approve: bool = False) -> dict:
    """Sync individual records from GGS — format: ชื่อผู้ปฏิบัติ, วันที่, รอบ."""
    try:
        sheet_id = extract_sheet_id(url)
        rows = await fetch_gviz_rows(build_json_url(sheet_id))
    except Exception as e:
        return {"status": "error", "message": str(e)}

    created = 0
    updated = 0
    participants_created = 0
    errors = []

    # Load existing participants for this branch (cache)
    p_result = await db.execute(select(Participant).where(Participant.branch_id == branch_id))
    participant_map = {}  # "first last" → participant
    for p in p_result.scalars().all():
        key = f"{p.first_name} {p.last_name}"
        participant_map[key] = p

    for i, row in enumerate(rows, start=2):
        raw_name = (row.get("เลือกชื่อผู้ปฏิบัติ") or "").strip()
        raw_date = (row.get("วันที่ปฏิบัติ") or "").strip()
        raw_session = (row.get("รอบการปฏิบัติ") or "").strip()

        if not raw_name or not raw_date:
            errors.append(f"แถว {i}: ขาดชื่อหรือวันที่")
            continue

        # Parse name: รองรับ 3 format
        # 1. "WP047 001 วัชรัชชัย ดวงมณีกุลรัตน์"  (branch + space + code + space + name)
        # 2. "WP111006 พรพิมล รัตนสวรรยา"        (branch+code ติดกัน 3+3 หลัก + space + name)
        # 3. "003 บรรณวิทย์ ฉิมธนู"                (code อย่างเดียว + space + name)
        m_wp_spaced = re.match(r"^WP(\d+)\s+(\d+)\s+(.+)$", raw_name)
        m_wp_concat = re.match(r"^WP(\d{3})(\d{3})\s+(.+)$", raw_name)
        if m_wp_spaced:
            member_code = m_wp_spaced.group(2).strip()
            name = m_wp_spaced.group(3).strip()
        elif m_wp_concat:
            member_code = m_wp_concat.group(2).strip()
            name = m_wp_concat.group(3).strip()
        else:
            m_simple = re.match(r"^(\d+)\s+(.+)$", raw_name)
            member_code = m_simple.group(1).strip() if m_simple else None
            name = m_simple.group(2).strip() if m_simple else raw_name

        rec_date = parse_thai_date(raw_date)
        if not rec_date:
            errors.append(f"แถว {i}: วันที่ไม่ถูกต้อง '{raw_date}'")
            continue

        morning, afternoon, evening = parse_sessions(raw_session)
        sessions = sum([morning, afternoon, evening])
        minutes = sessions * 5

        if minutes == 0:
            errors.append(f"แถว {i}: ไม่มีรอบที่ปฏิบัติ")
            continue

        # Auto-create participant ถ้ายังไม่มี
        participant = participant_map.get(name)
        if not participant:
            # แยกชื่อ-นามสกุล
            parts = name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""

            # เช็คซ้ำข้ามสาขา
            dup_check = await db.execute(select(Participant).where(
                Participant.first_name == first_name,
                Participant.last_name == last_name,
            ))
            existing_p = dup_check.scalar_one_or_none()
            if existing_p and existing_p.branch_id != branch_id:
                errors.append(f"แถว {i}: '{name}' ลงทะเบียนในสาขา {existing_p.branch_id} แล้ว")
                continue
            elif existing_p:
                participant = existing_p
                if member_code and not participant.member_code:
                    participant.member_code = member_code
            else:
                participant = Participant(
                    branch_id=branch_id,
                    member_code=member_code,
                    first_name=first_name,
                    last_name=last_name,
                    enrolled_date=rec_date,
                    privacy_accepted=True,
                    status="approved",
                )
                db.add(participant)
                await db.flush()  # get id
                participants_created += 1

            participant_map[name] = participant

        # Upsert record by branch_id + name + date
        stmt = select(Record).where(
            Record.branch_id == branch_id,
            Record.name == name,
            Record.date == rec_date,
            Record.type == "individual",
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        new_status = "approved" if auto_approve else "pending"
        approved_by = "auto-sync" if auto_approve else None

        plj_org_id = f"{branch_id}-00"

        if existing:
            existing.participant_id = participant.id
            if not existing.org_id:
                existing.org_id = plj_org_id
            existing.morning_male = 1 if morning else 0
            existing.afternoon_male = 1 if afternoon else 0
            existing.evening_male = 1 if evening else 0
            existing.minutes = minutes
            if existing.status != "approved":
                existing.status = new_status
                if auto_approve:
                    existing.approved_by = approved_by
            updated += 1
        else:
            db.add(Record(
                type="individual", branch_id=branch_id, name=name,
                org_id=plj_org_id,
                participant_id=participant.id,
                minutes=minutes,
                morning_male=1 if morning else 0,
                afternoon_male=1 if afternoon else 0,
                evening_male=1 if evening else 0,
                date=rec_date, status=new_status,
                approved_by=approved_by,
            ))
            created += 1

    await db.commit()
    return {
        "created": created, "updated": updated,
        "participants_created": participants_created,
        "errors": errors[:10],
    }


# === Sync: Bulk Records (placeholder — format TBD) ===

async def _sync_record_bulk(url: str, branch_id: str, db: AsyncSession) -> dict:
    """Sync bulk records — format TBD."""
    return {"status": "skip", "message": "รอ format จาก อ.เต้"}


# === Sync: Organizations (placeholder — format TBD) ===

async def _sync_org(url: str, branch_id: str, db: AsyncSession) -> dict:
    """Sync organizations — format TBD."""
    return {"status": "skip", "message": "รอ format จาก อ.เต้"}


# === Sync: Participants (placeholder — format TBD) ===

async def _sync_participant(url: str, branch_id: str, db: AsyncSession) -> dict:
    """Sync participants — format TBD."""
    return {"status": "skip", "message": "รอ format จาก อ.เต้"}


# === Auto-sync all branches ===

async def sync_all_record_ind(db: AsyncSession, auto_approve: bool = True) -> dict:
    """Sync record_ind for all branches that have a URL set.

    Used by both the scheduled background task and the manual /ggs/sync-all endpoint.
    """
    result = await db.execute(
        select(Branch).where(Branch.ggs_url_record_ind.isnot(None))
    )
    branches = result.scalars().all()

    summary = {"branches": len(branches), "created": 0, "updated": 0, "participants_created": 0, "errors": []}
    details = []
    for branch in branches:
        res = await _sync_record_ind(branch.ggs_url_record_ind, branch.id, db, auto_approve=auto_approve)
        details.append({"branch_id": branch.id, **res})
        summary["created"] += res.get("created", 0)
        summary["updated"] += res.get("updated", 0)
        summary["participants_created"] += res.get("participants_created", 0)
        if res.get("errors"):
            summary["errors"].append({"branch_id": branch.id, "errors": res["errors"]})
    summary["details"] = details
    return summary


@router.post("/ggs/sync-all")
async def sync_all_ggs(
    data: dict = None,
    user: User = Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin กลาง: sync record_ind ทุกสาขาที่มี URL (auto_approve default: True)."""
    data = data or {}
    auto_approve = bool(data.get("auto_approve", True))
    return await sync_all_record_ind(db, auto_approve=auto_approve)


@router.delete("/ggs/branch/{branch_id}/records")
async def clear_branch_records(
    branch_id: str,
    user: User = Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin กลาง: ลบ individual records ของสาขา เพื่อ sync ใหม่ (participants คงอยู่)."""
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"ไม่พบสาขา {branch_id}"})

    count_result = await db.execute(
        select(Record).where(Record.branch_id == branch_id, Record.type == "individual")
    )
    records = count_result.scalars().all()
    deleted = len(records)
    for r in records:
        await db.delete(r)
    await db.commit()
    return {"branch_id": branch_id, "deleted": deleted, "message": f"ลบ {deleted} รายการ"}


# === Legacy sync (keep backward compat) ===

@router.post("/ggs/sync")
async def sync_from_ggs(data: dict, db: AsyncSession = Depends(get_db)):
    """Legacy sync — accepts URL directly."""
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail={"error": "MISSING_URL", "message": "กรุณาระบุ URL"})
    extract_sheet_id(url)  # validate
    return {"message": "ใช้ /api/ggs/sync-branch แทน — ตั้ง URL ที่ /api/ggs/set-url ก่อน"}


@router.get("/ggs/sources")
async def list_ggs_sources(db: AsyncSession = Depends(get_db)):
    """List all branches with GGS URL status."""
    stmt = select(
        Branch.id, Branch.name, Branch.group_id,
        Branch.ggs_url_org, Branch.ggs_url_participant,
        Branch.ggs_url_record_bulk, Branch.ggs_url_record_ind,
    ).order_by(Branch.id)
    result = await db.execute(stmt)
    return [
        {
            "branch_id": r.id, "branch_name": r.name, "group_id": r.group_id,
            "ggs_url_org": r.ggs_url_org, "ggs_url_participant": r.ggs_url_participant,
            "ggs_url_record_bulk": r.ggs_url_record_bulk, "ggs_url_record_ind": r.ggs_url_record_ind,
        }
        for r in result.all()
    ]


# === Sync external org enrollments (central sheet from อ.เต้) ===

def _to_int(v) -> int | None:
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


@router.post("/ggs/sync-org-enrollments")
async def sync_org_enrollments_ggs(
    user: User = Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Sync external org enrollments from central GGS → insert as pending Organizations."""
    rows = await fetch_gviz_rows(GGS_ORG_ENROLLMENT_URL)

    # Preload existing orgs + branches
    existing_result = await db.execute(select(Organization.name, Organization.branch_id))
    existing_pairs = {(r[0], r[1]) for r in existing_result.all()}

    branches_result = await db.execute(select(Branch.id))
    valid_branches = {r[0] for r in branches_result.all()}

    # Preload per-branch max seq for id generation (B234-01, B234-02, ...)
    seq_result = await db.execute(
        select(Organization.id).where(Organization.id.like("B%-%"))
    )
    max_seq: dict[str, int] = {}
    for (oid,) in seq_result.all():
        parts = oid.split("-")
        if len(parts) == 2 and parts[1].isdigit():
            max_seq[parts[0]] = max(max_seq.get(parts[0], 0), int(parts[1]))

    created = 0
    skipped = 0
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        name = (row.get("ชื่อหน่วยงาน/โรงเรียน/องค์กร") or "").strip()
        branch_num = (row.get("ระบุเลขสาขาที่ประสานงาน (3 หลัก)") or "").strip()
        if not name or not branch_num:
            errors.append(f"แถว {i}: ขาดชื่อหรือเลขสาขา")
            continue
        if branch_num.replace(".0", "").isdigit():
            branch_num = branch_num.replace(".0", "").zfill(3)
        branch_id = f"B{branch_num}"
        if branch_id not in valid_branches:
            errors.append(f"แถว {i}: ไม่พบสาขา {branch_id}")
            continue
        if (name, branch_id) in existing_pairs:
            skipped += 1
            continue

        max_seq[branch_id] = max_seq.get(branch_id, 0) + 1
        org_id = f"{branch_id}-{max_seq[branch_id]:02d}"

        def _parse_date(s: str):
            s = (s or "").strip()
            if not s:
                return None
            try:
                return date_type.fromisoformat(s)
            except ValueError:
                return None

        org = Organization(
            id=org_id,
            name=name,
            org_type="หน่วยงาน",
            branch_id=branch_id,
            sub_district=(row.get("ตำบล") or "").strip() or None,
            district=(row.get("อำเภอ") or "").strip() or None,
            province=(row.get("จังหวัด") or "").strip() or None,
            email=(row.get("อีเมล์ (สำหรับรับเกียรติบัตร)") or "").strip() or None,
            contact_name=(row.get("ชื่อ-สกุล ผู้ประสานงานของหน่วยงาน") or "").strip() or None,
            contact_phone=(row.get("เบอร์ติดต่อหน่วยงาน") or "").strip() or None,
            contact_line_id=(row.get("Line ID (ถ้ามี)") or "").strip() or None,
            max_participants=_to_int(row.get("จำนวนผู้เข้าร่วม")),
            gender_male=_to_int(row.get("เพศชาย")) or 0,
            gender_female=_to_int(row.get("เพศหญิง")) or 0,
            gender_unspecified=_to_int(row.get("ไม่ระบุเพศ")) or 0,
            enrolled_date=_parse_date(row.get("เข้าร่วมโครงการตั้งแต่วันที่")),
            enrolled_until=_parse_date(row.get("ถึงวันที่")),
            status="pending",
        )
        db.add(org)
        existing_pairs.add((name, branch_id))
        created += 1

    await db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors[:20],
        "message": f"ดึงข้อมูลสำเร็จ: ใหม่ {created}, ซ้ำ {skipped}",
    }
