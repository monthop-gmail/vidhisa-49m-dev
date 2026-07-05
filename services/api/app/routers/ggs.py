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
from app.models import Branch, Organization, Participant, Record, SyncLog, User

router = APIRouter()

GGS_URL_TYPES = ["ggs_url_org", "ggs_url_participant", "ggs_url_record_bulk", "ggs_url_record_ind"]

GGS_ORG_ENROLLMENT_URL = "https://docs.google.com/spreadsheets/d/1COYcLXAliYPqpVEPev22MJtiKHO6b7-drVGjhZxNpOY/gviz/tq?tqx=out:json&headers=1"


# ─── Thai name normalization (สำหรับ GGS sync fuzzy match) ─────────────────────
# เรียงจาก "ยาว → สั้น" — ต้องจับ "ผศ.ดร." ก่อน "ผศ." ก่อน "ดร."
_THAI_TITLES: tuple[str, ...] = (
    # ยาวสุดก่อน — ให้จับ prefix ที่ specific ที่สุดก่อน
    "ผศ.ดร.", "รศ.ดร.", "ศ.ดร.",
    "พ.ต.ท.หญิง",
    "นางสาว", "เด็กชาย", "เด็กหญิง",
    "ทันตแพทย์",
    "เรือเอก", "เรือโท", "เรือตรี",
    "ร.ต.อ.", "พ.ต.ท.", "พ.ต.อ.",
    "พล.ต.", "พล.ท.", "พล.อ.",
    "น.ส.", "ด.ช.", "ด.ญ.",
    "น.ท.", "น.อ.", "น.ต.",
    "จ.อ.", "จ.ท.", "จ.ต.",
    "ทพญ.", "ทพ.",
    "นพ.", "พญ.",
    "น.พ.", "พ.ญ.",
    "พ.ต.", "ร.ต.",
    "พระครู", "สามเณร", "แม่ชี",
    "ผศ.", "รศ.", "ศ.",
    "ดร.", "อ.",
    "พระ",
    "นาย", "นาง", "คุณ",
)


def extract_thai_title(name: str) -> tuple[str, str]:
    """Return (title, rest). ถ้าไม่พบ title → ('', name).

    ตัวอย่าง:
      'นาย สมชาย ใจดี' → ('นาย', 'สมชาย ใจดี')
      'นางสาวมณี'       → ('นางสาว', 'มณี')
      'สมชาย ใจดี'      → ('', 'สมชาย ใจดี')
    """
    n = (name or "").strip()
    for t in _THAI_TITLES:
        if n.startswith(t + " "):
            return t, n[len(t):].strip()
        # ติดกันไม่มีเว้น: "นายสมชาย" (เฉพาะ title ที่ไม่มีจุด — กันชน "ดร." ที่ต้องเว้น)
        if "." not in t and n.startswith(t) and len(n) > len(t):
            nxt = n[len(t)]
            # ตัวอักษรถัดไปต้องเป็น letter (ไทย/eng non-ascii) เพื่อกัน "นายก" match "นาย"
            if nxt.isalpha() and not nxt.isascii():
                return t, n[len(t):].strip()
    return "", n


def _normalize_thai_name_part(s: str) -> str:
    """ทำ canonical form: strip punctuation, collapse whitespace, lowercase."""
    s = re.sub(r"[.\-_,()\[\]]+", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def normalize_name_key(first: str, last: str) -> str:
    """คีย์สำหรับเทียบชื่อ (fuzzy match) — เอา title, punctuation, whitespace, case ออก."""
    return f"{_normalize_thai_name_part(first)}|{_normalize_thai_name_part(last)}"


def extract_sheet_id(url: str) -> str:
    # รองรับทั้ง /spreadsheets/d/{id} และ /spreadsheets/u/{n}/d/{id} (Google account switcher prefix)
    match = re.search(r"/spreadsheets/(?:u/\d+/)?d/([a-zA-Z0-9-_]+)", url)
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
    # strip whitespace ที่ header — กันสาขากรอก "วันที่ปฏิบัติ " (มี space เกิน) เผลอ
    col_labels = [(c.get("label", "") or "").strip() for c in table["cols"]]
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
    m = re.search(r"/spreadsheets/(?:u/\d+/)?d/([a-zA-Z0-9-_]+)", s)
    if not m:
        return s
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/gviz/tq?tqx=out:json"


@router.get("/ggs/duplicate-urls")
async def scan_duplicate_urls(
    user: User = Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Scan สาขาทั้งหมด — คืน list ของ sheet id ที่ผูกกับ >1 สาขา (ไม่นับ ggs_url_org)."""
    from collections import defaultdict
    result = await db.execute(select(Branch).order_by(Branch.id))
    branches = result.scalars().all()
    dup_map: dict[str, list[dict]] = defaultdict(list)
    check_fields = [f for f in GGS_URL_TYPES if f != "ggs_url_org"]
    for b in branches:
        for f in check_fields:
            url = getattr(b, f)
            if not url:
                continue
            try:
                sid = extract_sheet_id(url)
            except HTTPException:
                continue
            dup_map[sid].append({"branch_id": b.id, "branch_name": b.name, "field": f})
    dups = [
        {"sheet_id": sid, "usages": usages}
        for sid, usages in dup_map.items()
        if len(usages) > 1
    ]
    return {"count": len(dups), "duplicates": dups}


async def _check_url_conflict(
    db: AsyncSession, branch_id: str, field: str, url: str | None,
) -> None:
    """Raise 409 ถ้า URL sheet เดียวกันถูกใช้กับสาขาอื่นแล้ว.

    ข้าม ggs_url_org (ทุกสาขาใช้ sheet ลงทะเบียนกลางเดียวกัน by design)
    """
    if not url or field == "ggs_url_org":
        return
    try:
        sid = extract_sheet_id(url)
    except HTTPException:
        return  # invalid URL — set-url จะ error เอง
    # หา branch อื่นที่ใช้ sheet เดียวกัน (ใน field ใดก็ได้ที่ไม่ใช่ ggs_url_org)
    check_fields = [f for f in GGS_URL_TYPES if f != "ggs_url_org"]
    for f in check_fields:
        col = getattr(Branch, f)
        stmt = select(Branch.id, Branch.name).where(
            Branch.id != branch_id,
            col.like(f"%{sid}%"),
        ).limit(1)
        other = (await db.execute(stmt)).first()
        if other:
            raise HTTPException(status_code=409, detail={
                "error": "URL_CONFLICT",
                "message": (
                    f"URL นี้ถูกใช้กับสาขา {other.id} ({other.name}) แล้ว "
                    f"(field: {f}) — sheet id ซ้ำ อาจ copy วางผิดสาขา"
                ),
                "conflict_branch_id": other.id,
                "conflict_field": f,
            })


@router.patch("/ggs/set-url")
async def set_ggs_url(
    data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set Google Sheet URLs for a branch. Rejects if URL is already used by another branch."""
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
            new_url = _normalize_ggs_url(data[field])
            await _check_url_conflict(db, branch_id, field, new_url)
            setattr(branch, field, new_url)
            updated.append(field)

    # Backward compat: "url" sets all or specific type
    if "url" in data and "url_type" in data:
        url_type = data["url_type"]
        field = f"ggs_url_{url_type}" if not url_type.startswith("ggs_url_") else url_type
        if hasattr(branch, field):
            new_url = _normalize_ggs_url(data["url"])
            await _check_url_conflict(db, branch_id, field, new_url)
            setattr(branch, field, new_url)
            updated.append(field)
    elif "url" in data and not updated:
        # Default: set record_ind (most common)
        new_url = _normalize_ggs_url(data["url"])
        await _check_url_conflict(db, branch_id, "ggs_url_record_ind", new_url)
        branch.ggs_url_record_ind = new_url
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
        results["record_ind"] = await _sync_record_ind(
            branch.ggs_url_record_ind, branch_id, db, auto_approve, triggered_by="manual",
        )

    if "record_bulk" in sync_types and branch.ggs_url_record_bulk:
        results["record_bulk"] = await _sync_record_bulk(branch.ggs_url_record_bulk, branch_id, db)

    if "org" in sync_types and branch.ggs_url_org:
        results["org"] = await _sync_org(branch.ggs_url_org, branch_id, db)

    if "participant" in sync_types and branch.ggs_url_participant:
        results["participant"] = await _sync_participant(
            branch.ggs_url_participant, branch_id, db, triggered_by="manual",
        )

    if not results:
        return {"branch_id": branch_id, "message": "ไม่มี GGS URL ที่ตั้งไว้ — กรุณาบันทึก URL ก่อน"}

    return {"branch_id": branch_id, **results}


# === Sync: Individual Records (format จาก อ.เต้) ===

async def _sync_record_ind(
    url: str,
    branch_id: str,
    db: AsyncSession,
    auto_approve: bool = False,
    triggered_by: str = "auto",
) -> dict:
    """Sync individual records from GGS — format: ชื่อผู้ปฏิบัติ, วันที่, รอบ."""
    log = SyncLog(
        branch_id=branch_id,
        sync_type="record_ind",
        triggered_by=triggered_by,
    )
    db.add(log)
    try:
        sheet_id = extract_sheet_id(url)
        rows = await fetch_gviz_rows(build_json_url(sheet_id))
    except Exception as e:
        log.finished_at = datetime.now()
        log.status = "error"
        log.error_count = 1
        log.errors = [str(e)]
        log.message = str(e)
        await db.commit()
        return {"status": "error", "message": str(e)}

    # === Column aliases — รองรับ header หลากหลาย ===
    # แต่ละ field มี list ของ combination (tuple of keywords) — combination แรกที่ match ชนะ
    # ลำดับสำคัญ: specific → generic (specific first เพื่อไม่ให้ fallback match false positive)
    def _norm_col(s: str) -> str:
        """Normalize column name: ฎ↔ฏ + ลบวรรณยุกต์ (่ ้ ๊ ๋) + lower."""
        s = (s or "").replace("ฎ", "ฏ")
        for tm in "่้๊๋":
            s = s.replace(tm, "")
        return s.lower()

    field_aliases: dict[str, list[tuple[str, ...]]] = {
        "name": [
            ("ชื่อ", "ผู้ปฏิบัติ"),      # specific
            ("ชื่อ-นามสกุล",),
            ("ชื่อ", "นามสกุล"),
            ("ผู้ปฏิบัติ",),             # loose fallback
            ("ชื่อสมาชิก",),
            ("ชื่อ", "สมาชิก"),
        ],
        "date": [
            ("วันที่", "ปฏิบัติ"),
            ("วันปฏิบัติ",),
            ("date",),
            ("วันที่",),                # loose — เผื่อ typo ตัวหลัง
        ],
        "session": [
            ("รอบการปฏิบัติ",),
            ("รอบ", "ปฏิบัติ"),
            ("รอบ",),
            ("session",),
        ],
    }

    def _find_field(row: dict, field: str) -> str:
        """หา column ตาม alias list — คืนค่าแรกที่ match."""
        for combo in field_aliases[field]:
            nkws = [_norm_col(kw) for kw in combo]
            for k, v in row.items():
                nk = _norm_col(k)
                if all(kw in nk for kw in nkws):
                    return v
        return ""

    def _has_field(row: dict, field: str) -> bool:
        for combo in field_aliases[field]:
            nkws = [_norm_col(kw) for kw in combo]
            if any(all(kw in _norm_col(k) for kw in nkws) for k in row.keys()):
                return True
        return False

    if rows:
        sample = rows[0]
        cols_found = list(sample.keys())
        missing: list[str] = []
        if not _has_field(sample, "name"):
            hints = " หรือ ".join(" + ".join(f"'{k}'" for k in c) for c in field_aliases["name"][:3])
            missing.append(f"ชื่อผู้ปฏิบัติ (คาดหวัง column ที่มี: {hints})")
        if not _has_field(sample, "date"):
            hints = " หรือ ".join(" + ".join(f"'{k}'" for k in c) for c in field_aliases["date"][:3])
            missing.append(f"วันที่ปฏิบัติ (คาดหวัง column ที่มี: {hints})")
        if not _has_field(sample, "session"):
            hints = " หรือ ".join(" + ".join(f"'{k}'" for k in c) for c in field_aliases["session"][:3])
            missing.append(f"รอบการปฏิบัติ (คาดหวัง column ที่มี: {hints})")
        if missing:
            msg = (
                "❌ Header ของ sheet ไม่ถูกต้อง — sync ไม่ได้\n"
                "ขาดคอลัมน์: " + ", ".join(missing) + "\n"
                f"Column ที่พบใน sheet: {cols_found}\n"
                "💡 คำแนะนำ: ตรวจสอบชื่อคอลัมน์ให้ตรงกับที่คาดหวัง (แนะนำแก้ที่ Google Form)"
            )
            log.finished_at = datetime.now()
            log.status = "error"
            log.error_count = 1
            log.errors = [msg]
            log.message = msg[:500]
            await db.commit()
            return {"status": "error", "message": msg, "columns_found": cols_found, "columns_missing": missing}

    created = 0
    updated = 0
    participants_created = 0
    errors = []

    # Load existing participants for this branch
    # ข้าม status=rejected (กัน zombie link: sync ผูก records เข้า rejected participant)
    # order_by id ASC → กรณี duplicate ตัวที่ id ใหม่สุดชนะ (deterministic)
    p_result = await db.execute(
        select(Participant)
        .where(Participant.branch_id == branch_id, Participant.status != "rejected")
        .order_by(Participant.id)
    )
    participant_map: dict[str, Participant] = {}  # normalized name → participant (fallback)
    code_map: dict[str, Participant] = {}  # member_code → participant (primary match)
    for p in p_result.scalars().all():
        name_key = normalize_name_key(p.first_name or "", p.last_name or "")
        participant_map[name_key] = p
        if p.member_code:
            code_map[p.member_code.strip()] = p

    # Cross-branch dup check — โหลด participants ของสาขาอื่นทั้งหมด (สร้าง normalized map)
    # ข้าม status=rejected เช่นเดียวกัน (ไม่ต้อง block ชื่อที่ถูก reject แล้ว)
    other_result = await db.execute(
        select(Participant)
        .where(Participant.branch_id != branch_id, Participant.status != "rejected")
        .order_by(Participant.id)
    )
    cross_branch_map: dict[str, Participant] = {}
    for p in other_result.scalars().all():
        key = normalize_name_key(p.first_name or "", p.last_name or "")
        cross_branch_map[key] = p

    for i, row in enumerate(rows, start=2):
        raw_name = (_find_field(row, "name") or "").strip()
        raw_date = (_find_field(row, "date") or "").strip()
        raw_session = (_find_field(row, "session") or "").strip()

        if not raw_name or not raw_date:
            errors.append(f"แถว {i}: ขาดชื่อหรือวันที่")
            continue

        # Parse name: รองรับหลาย format (title อาจอยู่ก่อน/หลัง code)
        # ทดลองก่อน — ตัด title ออกจากด้านหน้า (ถ้ามี) เพื่อให้ regex match code ได้
        pre_title, name_after_title = extract_thai_title(raw_name)
        parse_target = name_after_title if pre_title else raw_name

        m_wp_spaced = re.match(r"^WP(\d+)\s+(\d+)\s+(.+)$", parse_target)
        m_wp_concat = re.match(r"^WP(\d{3})(\d{3})\s+(.+)$", parse_target)
        m_branch_concat = re.match(r"^(\d{3})(\d{3})\s+(.+)$", parse_target)
        if m_wp_spaced:
            member_code = m_wp_spaced.group(2).strip()
            name = m_wp_spaced.group(3).strip()
        elif m_wp_concat:
            member_code = m_wp_concat.group(2).strip()
            name = m_wp_concat.group(3).strip()
        elif m_branch_concat and f"B{m_branch_concat.group(1)}" == branch_id:
            member_code = m_branch_concat.group(2).strip()
            name = m_branch_concat.group(3).strip()
        else:
            # รองรับ code + space หรือ code + dash (เช่น "128-นางสาว...")
            m_simple = re.match(r"^(\d+)[\s\-]+(.+)$", parse_target)
            member_code = m_simple.group(1).strip() if m_simple else None
            name = m_simple.group(2).strip() if m_simple else parse_target

        # ถ้าตัด title ตอนแรก + name ที่ได้ยังไม่มี title → เอา title กลับใส่ให้ extract_thai_title ตอนหลังจับได้
        if pre_title and not any(name.startswith(t) for t in (pre_title + " ", pre_title)):
            name = f"{pre_title} {name}"

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

        # แยก title (คำนำหน้า) ออกจากชื่อ → เก็บใน Participant.prefix
        title, name_no_title = extract_thai_title(name)
        parts = name_no_title.split(" ", 1)
        first_name = parts[0].strip() if parts and parts[0].strip() else name_no_title
        last_name = parts[1].strip() if len(parts) > 1 else ""
        lookup_key = normalize_name_key(first_name, last_name)

        # หา participant เดิม — ลำดับความสำคัญ:
        # 1) match by member_code (คงที่สุด — ชื่อใน sheet อาจแก้ไข typo แต่ code นิ่ง)
        # 2) fallback: match by normalized name
        participant = None
        if member_code:
            participant = code_map.get(member_code.strip())
        if not participant:
            participant = participant_map.get(lookup_key)
        if not participant:
            # เช็คซ้ำข้ามสาขา (normalized match — enforce "1 คน = 1 สาขา")
            cross = cross_branch_map.get(lookup_key)
            if cross:
                errors.append(f"แถว {i}: '{first_name} {last_name}' ลงทะเบียนในสาขา {cross.branch_id} แล้ว")
                continue
            # สร้างใหม่
            participant = Participant(
                branch_id=branch_id,
                member_code=member_code,
                prefix=title or None,
                first_name=first_name,
                last_name=last_name,
                enrolled_date=rec_date,
                privacy_accepted=True,
                status="approved",
            )
            db.add(participant)
            await db.flush()  # get id
            participants_created += 1
            participant_map[lookup_key] = participant
            if member_code:
                code_map[member_code.strip()] = participant
        else:
            # backfill prefix/member_code หากยังว่าง
            if title and not participant.prefix:
                participant.prefix = title
            if member_code and not participant.member_code:
                participant.member_code = member_code
                code_map[member_code.strip()] = participant

        # ใช้ชื่อสะอาด (ไม่มี title) เป็น record.name — สม่ำเสมอกันทั้งระบบ
        clean_name = f"{first_name} {last_name}".strip()

        # Upsert record — match by participant_id (แม่นสุด) → fallback by name (สำหรับ record เก่าที่ไม่มี participant_id)
        stmt = select(Record).where(
            Record.branch_id == branch_id,
            Record.date == rec_date,
            Record.type == "individual",
            Record.participant_id == participant.id,
        ).order_by(Record.id)
        existing = (await db.execute(stmt)).scalars().first()

        if not existing:
            # legacy fallback: match by raw name (records เก่าที่ยังไม่มี participant_id)
            stmt = select(Record).where(
                Record.branch_id == branch_id,
                Record.date == rec_date,
                Record.type == "individual",
                Record.name.in_([name, clean_name]),  # ทั้งชื่อดั้งเดิมและชื่อสะอาด
            ).order_by(Record.id)
            existing = (await db.execute(stmt)).scalars().first()

        new_status = "approved" if auto_approve else "pending"
        approved_by = "auto-sync" if auto_approve else None

        plj_org_id = f"{branch_id}-00"

        if existing:
            existing.participant_id = participant.id
            if not existing.org_id:
                existing.org_id = plj_org_id
            # OR-merge sessions — กัน "หลายแถวต่อวัน" (เช่น 3 แถวแยกรอบ) ทับกัน
            existing.morning_male = max(existing.morning_male or 0, 1 if morning else 0)
            existing.afternoon_male = max(existing.afternoon_male or 0, 1 if afternoon else 0)
            existing.evening_male = max(existing.evening_male or 0, 1 if evening else 0)
            # คำนวณ minutes ใหม่จาก sessions รวม (5 นาที/รอบ)
            existing.minutes = (existing.morning_male + existing.afternoon_male + existing.evening_male) * 5
            if existing.status != "approved":
                existing.status = new_status
                if auto_approve:
                    existing.approved_by = approved_by
            updated += 1
        else:
            db.add(Record(
                type="individual", branch_id=branch_id, name=clean_name,
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

    log.finished_at = datetime.now()
    log.status = "partial" if errors else "ok"
    log.created = created
    log.updated = updated
    log.participants_created = participants_created
    log.error_count = len(errors)
    log.errors = errors[:100] if errors else None
    log.message = f"created={created} updated={updated} participants_created={participants_created} errors={len(errors)}"
    await db.commit()
    return {
        "created": created, "updated": updated,
        "participants_created": participants_created,
        "error_count": len(errors),
        "errors": errors[:10],
    }


# === Sync: Bulk Records (ยังไม่รองรับ) ===

async def _sync_record_bulk(url: str, branch_id: str, db: AsyncSession) -> dict:
    """Sync bulk records — ยังไม่รองรับ format นี้."""
    return {
        "status": "skip",
        "message": "ยังไม่รองรับ bulk record — สาขากรุณาใช้ record_ind (link 4) ไปก่อน",
    }


# === Sync: Organizations (ใช้ sheet ลงทะเบียนกลาง — sync ต่อรายสาขายังไม่รองรับ) ===

async def _sync_org(url: str, branch_id: str, db: AsyncSession) -> dict:
    """Sync organizations — ใช้ sheet ลงทะเบียนกลาง (org enrollment)."""
    return {
        "status": "skip",
        "message": "องค์กรใช้ sheet ลงทะเบียนกลาง — ไม่ต้อง sync ที่ระดับสาขา",
    }


# === Sync: Participants (link 2) — profile data จาก Google Form ===

def _norm_gender(v: str | None) -> str | None:
    if not v:
        return None
    s = str(v).strip()
    if s in ("ชาย", "male", "M", "m"):
        return "male"
    if s in ("หญิง", "female", "F", "f"):
        return "female"
    if s in ("ไม่ระบุ", "unspecified", "-"):
        return "unspecified"
    return None


def _clean_str(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "—", "NULL"):
        return None
    return s


async def _sync_participant(
    url: str,
    branch_id: str,
    db: AsyncSession,
    triggered_by: str = "auto",
) -> dict:
    """Sync participant profiles from GGS (link 2) — update gender/age/address/phone/line_id.

    Sheet columns (Thai):
      - คำนำหน้าชื่อ, ชื่อ, นามสกุล → match key (normalized name)
      - เพศ, อายุ, เบอร์ติดต่อ, Line ID, ตำบล/อำเภอ/จังหวัด → profile fields
      - ยืนยันการสมัคร... → consent gate (skip row if empty)

    Match: (branch_id, normalized_name) → update ถ้ามี, สร้างใหม่ status=approved ถ้าไม่มี
    """
    log = SyncLog(branch_id=branch_id, sync_type="participant", triggered_by=triggered_by)
    db.add(log)
    try:
        sheet_id = extract_sheet_id(url)
        rows = await fetch_gviz_rows(build_json_url(sheet_id))
    except Exception as e:
        log.finished_at = datetime.now()
        log.status = "error"
        log.error_count = 1
        log.errors = [str(e)]
        log.message = str(e)
        await db.commit()
        return {"status": "error", "message": str(e)}

    # โหลด participants ในสาขานี้ (ยกเว้น rejected — deterministic winner = id สูงสุด)
    p_result = await db.execute(
        select(Participant)
        .where(Participant.branch_id == branch_id, Participant.status != "rejected")
        .order_by(Participant.id)
    )
    participant_map: dict[str, Participant] = {}
    for p in p_result.scalars().all():
        key = normalize_name_key(p.first_name or "", p.last_name or "")
        participant_map[key] = p

    def _norm_col(s: str) -> str:
        """Normalize Thai lookalike typos (ฎ ↔ ฏ)."""
        return (s or "").replace("ฎ", "ฏ")

    def _find(row: dict, *keywords: str) -> str:
        """Return first value where col name contains ALL keywords (tolerate Thai typos)."""
        nkws = [_norm_col(kw) for kw in keywords]
        for k, v in row.items():
            nk = _norm_col(k)
            if all(kw in nk for kw in nkws):
                return v
        return ""

    def _exact(row: dict, name: str) -> str:
        """Return value where column name matches exactly (ignore surrounding whitespace + Thai typos)."""
        target = _norm_col(name)
        for k, v in row.items():
            if _norm_col(k.strip()) == target:
                return v
        return ""

    created = 0
    updated = 0
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        # "ชื่อ" / "นามสกุล" ต้อง exact match (ไม่งั้น "คำนำหน้าชื่อ" จะโดนจับด้วย)
        first = _clean_str(_exact(row, "ชื่อ")) or ""
        last = _clean_str(_exact(row, "นามสกุล")) or ""

        if not first and not last:
            continue  # skip empty row

        prefix = _clean_str(_find(row, "คำนำหน้า"))
        gender = _norm_gender(_find(row, "เพศ"))
        age_raw = _find(row, "อายุ")
        age = None
        if age_raw not in (None, ""):
            try:
                age = int(float(str(age_raw)))
            except (ValueError, TypeError):
                pass
        phone = _clean_str(_find(row, "เบอร์"))
        line_id = _clean_str(_find(row, "Line"))
        sub_district = _clean_str(_find(row, "ตำบล"))
        district = _clean_str(_find(row, "อำเภอ"))
        province = _clean_str(_find(row, "จังหวัด"))
        consent = _clean_str(_find(row, "ยืนยัน"))

        if not consent:
            errors.append(f"แถว {i}: ไม่มี consent — ข้าม")
            continue

        key = normalize_name_key(first, last)
        p = participant_map.get(key)

        if p:
            # UPDATE ถ้าค่าใหม่ไม่ว่าง (ไม่เขียนทับค่าเดิมด้วย None)
            if prefix and not p.prefix:
                p.prefix = prefix
            if gender and not p.gender:
                p.gender = gender
            if age is not None and not p.age:
                p.age = age
            if phone and not p.phone:
                p.phone = phone
            if line_id and not p.line_id:
                p.line_id = line_id
            if sub_district and not p.sub_district:
                p.sub_district = sub_district
            if district and not p.district:
                p.district = district
            if province and not p.province:
                p.province = province
            if not p.privacy_accepted:
                p.privacy_accepted = True
            updated += 1
        else:
            # CREATE — คนที่สมัครแต่ยังไม่เคยปฏิบัติ
            p = Participant(
                branch_id=branch_id,
                prefix=prefix,
                first_name=first,
                last_name=last,
                gender=gender,
                age=age,
                phone=phone,
                line_id=line_id,
                sub_district=sub_district,
                district=district,
                province=province,
                privacy_accepted=True,
                status="approved",
            )
            db.add(p)
            await db.flush()
            participant_map[key] = p
            created += 1

    log.finished_at = datetime.now()
    log.status = "partial" if errors else "ok"
    log.created = created
    log.updated = updated
    log.participants_created = created
    log.error_count = len(errors)
    log.errors = errors[:100] if errors else None
    log.message = f"created={created} updated={updated} errors={len(errors)}"
    await db.commit()
    return {
        "created": created,
        "updated": updated,
        "participants_created": created,
        "errors": errors[:10],
    }


# === Auto-sync all branches ===

async def sync_all_record_ind(
    db: AsyncSession, auto_approve: bool = True, triggered_by: str = "auto"
) -> dict:
    """Sync record_ind for all branches that have a URL set.

    Used by both the scheduled background task and the manual /ggs/sync-all endpoint.
    """
    batch_log = SyncLog(branch_id=None, sync_type="sync_all", triggered_by=triggered_by)
    db.add(batch_log)
    await db.flush()

    # Sync participants ก่อน (profile data) — เพื่อให้ record_ind มี profile ที่ update แล้ว
    p_branches = (await db.execute(
        select(Branch).where(Branch.ggs_url_participant.isnot(None))
    )).scalars().all()
    for branch in p_branches:
        try:
            await _sync_participant(branch.ggs_url_participant, branch.id, db, triggered_by=triggered_by)
        except Exception:
            pass  # log บันทึกในตัว sync แล้ว

    result = await db.execute(
        select(Branch).where(Branch.ggs_url_record_ind.isnot(None))
    )
    branches = result.scalars().all()

    summary = {"branches": len(branches), "created": 0, "updated": 0, "participants_created": 0, "errors": []}
    details = []
    for branch in branches:
        res = await _sync_record_ind(
            branch.ggs_url_record_ind, branch.id, db, auto_approve=auto_approve, triggered_by=triggered_by,
        )
        details.append({"branch_id": branch.id, **res})
        summary["created"] += res.get("created", 0)
        summary["updated"] += res.get("updated", 0)
        summary["participants_created"] += res.get("participants_created", 0)
        if res.get("errors"):
            summary["errors"].append({"branch_id": branch.id, "errors": res["errors"]})
    summary["details"] = details
    summary["participant_branches_synced"] = len(p_branches)

    batch_log.finished_at = datetime.now()
    batch_log.status = "partial" if summary["errors"] else "ok"
    batch_log.created = summary["created"]
    batch_log.updated = summary["updated"]
    batch_log.participants_created = summary["participants_created"]
    batch_log.error_count = sum(len(e.get("errors", [])) for e in summary["errors"])
    batch_log.message = (
        f"branches={len(branches)} created={summary['created']} "
        f"updated={summary['updated']} errors={batch_log.error_count}"
    )
    await db.commit()

    return summary


@router.get("/ggs/sync-logs")
async def list_sync_logs(
    branch_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List sync logs — central admin เห็นทั้งระบบ, branch admin เห็นเฉพาะสาขาตน (+ batch)."""
    stmt = select(SyncLog).order_by(SyncLog.started_at.desc())
    if user.role != "central_admin":
        # branch admin — ดูได้เฉพาะสาขาตัวเอง (+ NULL = batch sync-all)
        stmt = stmt.where((SyncLog.branch_id == user.branch_id) | (SyncLog.branch_id.is_(None)))
    if branch_id:
        if user.role != "central_admin" and branch_id != user.branch_id:
            raise HTTPException(status_code=403, detail={"error": "FORBIDDEN"})
        stmt = stmt.where(SyncLog.branch_id == branch_id)
    if status:
        stmt = stmt.where(SyncLog.status == status)
    stmt = stmt.limit(min(limit, 200)).offset(offset)
    logs = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": log.id,
            "branch_id": log.branch_id,
            "sync_type": log.sync_type,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
            "status": log.status,
            "created": log.created,
            "updated": log.updated,
            "participants_created": log.participants_created,
            "error_count": log.error_count,
            "message": log.message,
            "triggered_by": log.triggered_by,
        }
        for log in logs
    ]


@router.get("/ggs/sync-logs/{log_id}")
async def get_sync_log(
    log_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Detail log พร้อม errors[] เต็ม."""
    log = (await db.execute(select(SyncLog).where(SyncLog.id == log_id))).scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND"})
    if user.role != "central_admin":
        if log.branch_id and log.branch_id != user.branch_id:
            raise HTTPException(status_code=403, detail={"error": "FORBIDDEN"})
    return {
        "id": log.id,
        "branch_id": log.branch_id,
        "sync_type": log.sync_type,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        "status": log.status,
        "created": log.created,
        "updated": log.updated,
        "participants_created": log.participants_created,
        "error_count": log.error_count,
        "errors": log.errors or [],
        "message": log.message,
        "triggered_by": log.triggered_by,
    }


@router.post("/ggs/sync-all")
async def sync_all_ggs(
    data: dict = None,
    user: User = Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin กลาง: sync record_ind ทุกสาขาที่มี URL (auto_approve default: True)."""
    data = data or {}
    auto_approve = bool(data.get("auto_approve", True))
    return await sync_all_record_ind(db, auto_approve=auto_approve, triggered_by="manual")


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
