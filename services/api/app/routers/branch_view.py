"""Public read-only API for participants (me-ui).

Auth: branch_id + view_secret (Crockford base32 6-char) — no JWT.
PII protection: search returns 5 fields only; me/{id} masks phone, omits ip/device.
Rate limited via slowapi (in-memory).
"""

import re
import secrets as _secrets
from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Branch, BranchViewLog, Participant, Record

router = APIRouter()

limiter = Limiter(key_func=get_remote_address)

SECRET_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{6}$")
SECRET_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford (no I L O U)


def generate_view_secret() -> str:
    """Generate a 6-char Crockford base32 secret."""
    return "".join(_secrets.choice(SECRET_ALPHABET) for _ in range(6))


def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7:
        return phone
    return f"{digits[:3]}-xxx-{digits[-4:]}"


async def _log(db: AsyncSession, request: Request, branch_id: str | None, action: str,
               status_code: int, participant_id: int | None = None) -> None:
    try:
        ua = request.headers.get("user-agent", "")[:500]
        db.add(BranchViewLog(
            branch_id=branch_id, ip=get_remote_address(request), action=action,
            participant_id=participant_id, status_code=status_code, user_agent=ua,
        ))
        await db.commit()
    except Exception:
        await db.rollback()


async def _verify_secret(db: AsyncSession, branch_id: str, secret: str) -> Branch | None:
    """Constant-time secret check. Returns branch or None."""
    if not SECRET_RE.match(secret or ""):
        return None
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch or not branch.view_secret:
        return None
    if not _secrets.compare_digest(branch.view_secret, secret):
        return None
    return branch


# === 3.1 GET /info ===

@router.get("/branch-view/{branch_id}/{secret}/info")
@limiter.limit("30/minute")
async def view_info(branch_id: str, secret: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Verify secret + return branch name."""
    branch = await _verify_secret(db, branch_id, secret)
    if not branch:
        await _log(db, request, branch_id, "invalid", 404)
        raise HTTPException(status_code=404, detail={"error": "INVALID_LINK", "message": "Link ไม่ถูกต้อง"})
    await _log(db, request, branch_id, "info", 200)
    return {"branch_id": branch.id, "branch_name": branch.name, "province": branch.province}


# === 3.2 GET /participants ===

@router.get("/branch-view/{branch_id}/{secret}/participants")
@limiter.limit("60/minute")
async def view_participants(
    branch_id: str, secret: str, request: Request,
    q: str = "", db: AsyncSession = Depends(get_db),
):
    """Search approved participants by substring. Empty q → []."""
    branch = await _verify_secret(db, branch_id, secret)
    if not branch:
        await _log(db, request, branch_id, "invalid", 404)
        raise HTTPException(status_code=404, detail={"error": "INVALID_LINK", "message": "Link ไม่ถูกต้อง"})

    q = (q or "").strip()
    if not q:
        await _log(db, request, branch_id, "search", 200)
        return []

    pat = f"%{q}%"
    stmt = (
        select(Participant)
        .where(
            Participant.branch_id == branch_id,
            Participant.status == "approved",
            (Participant.first_name.ilike(pat))
            | (Participant.last_name.ilike(pat))
            | (Participant.member_code.ilike(pat)),
        )
        .order_by(func.lower(Participant.first_name))
        .limit(50)
    )
    result = await db.execute(stmt)
    participants = result.scalars().all()
    await _log(db, request, branch_id, "search", 200)
    return [
        {
            "id": p.id, "prefix": p.prefix,
            "first_name": p.first_name, "last_name": p.last_name,
            "member_code": p.member_code,
        }
        for p in participants
    ]


# === 3.3 GET /me/{participant_id} ===

@router.get("/branch-view/{branch_id}/{secret}/me/{participant_id}")
@limiter.limit("120/minute")
async def view_me(
    branch_id: str, secret: str, participant_id: int, request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Return participant profile + stats. Cross-branch lookup → 404."""
    branch = await _verify_secret(db, branch_id, secret)
    if not branch:
        await _log(db, request, branch_id, "invalid", 404)
        raise HTTPException(status_code=404, detail={"error": "INVALID_LINK", "message": "Link ไม่ถูกต้อง"})

    p_result = await db.execute(select(Participant).where(Participant.id == participant_id))
    p = p_result.scalar_one_or_none()
    if not p or p.branch_id != branch_id:
        await _log(db, request, branch_id, "me", 404, participant_id)
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบผู้เข้าร่วม"})

    # Stats
    stats_result = await db.execute(
        select(
            func.coalesce(func.sum(Record.minutes), 0),
            func.count(Record.id),
            func.count(func.distinct(Record.date)),
        ).where(
            Record.participant_id == participant_id,
            Record.status == "approved",
        )
    )
    total_minutes, total_records, distinct_days = stats_result.one()

    # Daily minutes (30 วันล่าสุด)
    cutoff = date_type.today() - timedelta(days=30)
    daily_result = await db.execute(
        select(Record.date, func.sum(Record.minutes))
        .where(
            Record.participant_id == participant_id,
            Record.status == "approved",
            Record.date >= cutoff,
        )
        .group_by(Record.date)
        .order_by(Record.date)
    )
    daily_minutes = [{"date": str(d), "minutes": int(m)} for d, m in daily_result.all()]

    # Recent 10 records (ทุก status)
    recent_result = await db.execute(
        select(Record)
        .where(Record.participant_id == participant_id)
        .order_by(desc(Record.date), desc(Record.id))
        .limit(10)
    )
    recent_records = [
        {"id": r.id, "date": str(r.date), "minutes": r.minutes, "status": r.status}
        for r in recent_result.scalars().all()
    ]

    await _log(db, request, branch_id, "me", 200, participant_id)
    return {
        "id": p.id, "prefix": p.prefix,
        "first_name": p.first_name, "last_name": p.last_name,
        "member_code": p.member_code,
        "branch_id": branch.id, "branch_name": branch.name,
        "profile": {
            "gender": p.gender, "age": p.age,
            "sub_district": p.sub_district, "district": p.district, "province": p.province,
            "phone_masked": _mask_phone(p.phone),
            "line_id": p.line_id,
            "enrolled_date": str(p.enrolled_date) if p.enrolled_date else None,
            "status": p.status,
        },
        "branch_links": {"record_form_url": branch.record_form_url},
        "stats": {
            "total_minutes": int(total_minutes),
            "total_records": int(total_records),
            "approved_records": int(total_records),
            "distinct_days": int(distinct_days),
        },
        "daily_minutes": daily_minutes,
        "recent_records": recent_records,
    }
