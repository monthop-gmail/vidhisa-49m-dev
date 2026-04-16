"""Branch enrollment — sync from GGS, approve, create users, send email."""

import csv
import io
import json
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import generate_password, hash_password, require_central_admin
from app.database import get_db
from app.email_service import send_credentials_email
from app.models import Branch, BranchEnrollment, Organization, User

router = APIRouter()

GGS_URL = "https://docs.google.com/spreadsheets/d/1yXs6dHAxNvRne9jcFzr3ttNKvDHbzYMVpy3gV_O2QTA/gviz/tq?tqx=out:json&headers=1&sheet=Form+Responses+1"


def _parse_gviz_json(raw: str) -> list[dict]:
    """Parse Google gviz JSON (JSONP format) and return list of dicts.

    Prefers formatted value (f) over raw value (v) so that custom-formatted
    numbers like 058 are preserved instead of being converted to 58.
    """
    start = raw.find("(") + 1
    end = raw.rfind(")")
    data = json.loads(raw[start:end])
    table = data["table"]
    col_labels = [c.get("label", "") for c in table["cols"]]

    rows = []
    for row in table["rows"]:
        d = {}
        for col, cell in zip(col_labels, row["c"]):
            if cell is None:
                d[col] = ""
                continue
            f = cell.get("f")
            v = cell.get("v")
            if f:
                d[col] = str(f)
            elif v is not None:
                d[col] = str(v)
            else:
                d[col] = ""
        rows.append(d)
    return rows


@router.get("/enrollments")
async def list_enrollments(db: AsyncSession = Depends(get_db)):
    """List all branch enrollment requests."""
    result = await db.execute(select(BranchEnrollment).order_by(BranchEnrollment.id))
    enrollments = result.scalars().all()
    return [
        {
            "id": e.id, "branch_number": e.branch_number, "branch_name": e.branch_name,
            "admin1_name": e.admin1_name, "admin1_email": e.admin1_email,
            "admin2_name": e.admin2_name, "admin2_email": e.admin2_email,
            "admin3_name": e.admin3_name, "admin3_email": e.admin3_email,
            "submitted_email": e.submitted_email, "submitted_at": str(e.submitted_at) if e.submitted_at else None,
            "status": e.status,
        }
        for e in enrollments
    ]


@router.post("/enrollments/sync")
async def sync_enrollments(
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Sync enrollment data from Google Sheet (uses gviz JSON to preserve formatted values)."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        res = await client.get(GGS_URL)
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail={"error": "GGS_FETCH_FAILED", "message": "ดึง Google Sheet ไม่ได้"})

    rows_data = _parse_gviz_json(res.text)

    # Load existing
    existing_result = await db.execute(select(BranchEnrollment.branch_name))
    existing_names = {r[0] for r in existing_result.all()}

    created = 0
    skipped = 0

    for row in rows_data:
        branch_name = (row.get("ชื่อสาขา") or "").strip()
        if not branch_name:
            continue
        if branch_name in existing_names:
            skipped += 1
            continue

        branch_num = (row.get("เลขสาขา (3 หลัก)") or "").strip()
        # Normalize: "47" → "047", "9" → "009", "101" → "101"
        if branch_num and branch_num.isdigit():
            branch_num = branch_num.zfill(3)
        timestamp_str = (row.get("Timestamp") or "").strip()

        e = BranchEnrollment(
            branch_number=branch_num or None,
            branch_name=branch_name,
            admin1_name=(row.get("ชื่อ-นามสกุล ผู้ประสานงานลำดับที่ 1") or "").strip() or None,
            admin1_email=(row.get("อีเมล์  ผู้ประสานงานลำดับที่ 1") or "").strip() or None,
            admin1_phone=(row.get("เบอร์มือถือ  ผู้ประสานงานลำดับที่ 1") or "").strip() or None,
            admin2_name=(row.get("ชื่อ-นามสกุล ผู้ประสานงานลำดับที่ 2") or "").strip() or None,
            admin2_email=(row.get("อีเมล์  ผู้ประสานงานลำดับที่ 2") or "").strip() or None,
            admin2_phone=(row.get("เบอร์มือถือ  ผู้ประสานงานลำดับที่ 2") or "").strip() or None,
            admin3_name=(row.get("ชื่อ-นามสกุล ผู้ประสานงานลำดับที่ 3") or "").strip() or None,
            admin3_email=(row.get("อีเมล์  ผู้ประสานงานลำดับที่ 3") or "").strip() or None,
            admin3_phone=(row.get("เบอร์มือถือ  ผู้ประสานงานลำดับที่ 3") or "").strip() or None,
            submitted_email=(row.get("Email Address") or "").strip() or None,
            status="pending",
        )
        db.add(e)
        existing_names.add(branch_name)
        created += 1

    await db.commit()
    return {"created": created, "skipped": skipped, "message": f"ดึงข้อมูลสำเร็จ: ใหม่ {created}, ซ้ำ {skipped}"}


def _make_username(branch_num: str, admin_index: int) -> str:
    """Generate username like B101-1, B101-2."""
    num = branch_num or "000"
    return f"B{num}-{admin_index}"


@router.patch("/enrollments/{enrollment_id}/approve")
async def approve_enrollment(
    enrollment_id: int,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve enrollment → create users → send email."""
    result = await db.execute(select(BranchEnrollment).where(BranchEnrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบรายการ"})

    if enrollment.status == "approved":
        raise HTTPException(status_code=400, detail={"error": "ALREADY_APPROVED", "message": "อนุมัติแล้ว"})

    enrollment.status = "approved"
    enrollment.approved_at = datetime.now(timezone.utc)

    branch_id = f"B{enrollment.branch_number}" if enrollment.branch_number else None
    users_created = []
    emails_sent = []
    org_created = False

    # Auto-create PLJ org for this branch
    if branch_id:
        # Check branch exists
        br_check = await db.execute(select(Branch).where(Branch.id == branch_id))
        branch_obj = br_check.scalar_one_or_none()
        if branch_obj:
            plj_id = f"{branch_id}-00"
            org_check = await db.execute(select(Organization).where(Organization.id == plj_id))
            if not org_check.scalar_one_or_none():
                org = Organization(
                    id=plj_id,
                    name=f"สถาบันพลังจิตตานุภาพ {branch_obj.name}",
                    org_type="สถาบันพลังจิตตานุภาพ",
                    branch_id=branch_id,
                    status="approved",
                )
                db.add(org)
                org_created = True

    # Create users for each admin (1-3)
    admins = [
        (enrollment.admin1_name, enrollment.admin1_email, enrollment.admin1_phone, 1),
        (enrollment.admin2_name, enrollment.admin2_email, enrollment.admin2_phone, 2),
        (enrollment.admin3_name, enrollment.admin3_email, enrollment.admin3_phone, 3),
    ]

    for name, email, phone, idx in admins:
        if not name:
            continue

        # ใช้ email เป็น username, เบอร์โทรเป็น password
        username = email if email else _make_username(enrollment.branch_number, idx)
        password = phone if phone else generate_password()

        # Check if username exists
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            username = f"{username}-{enrollment.id}"

        u = User(
            username=username,
            password_hash=hash_password(password),
            full_name=name,
            email=email,
            phone=phone,
            role="branch_admin",
            branch_id=branch_id,
            status="active",
        )
        db.add(u)
        users_created.append({"username": username, "password": password, "name": name, "email": email})

        # Send email
        if email:
            sent = send_credentials_email(email, name, username, password, enrollment.branch_name)
            if sent:
                emails_sent.append(email)

    await db.commit()

    return {
        "id": enrollment.id,
        "status": "approved",
        "branch_name": enrollment.branch_name,
        "users_created": len(users_created),
        "emails_sent": len(emails_sent),
        "org_created": org_created,
        "users": [{"username": u["username"], "name": u["name"], "email": u["email"]} for u in users_created],
        "message": f"อนุมัติสำเร็จ สร้าง {len(users_created)} users"
                   + (f", สร้าง PLJ org" if org_created else "")
                   + f", ส่ง email {len(emails_sent)} ฉบับ",
        "_credentials": users_created,
    }


@router.patch("/enrollments/{enrollment_id}/reject")
async def reject_enrollment(
    enrollment_id: int,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject enrollment."""
    result = await db.execute(select(BranchEnrollment).where(BranchEnrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบรายการ"})
    enrollment.status = "rejected"
    await db.commit()
    return {"id": enrollment.id, "status": "rejected"}


@router.patch("/enrollments/{enrollment_id}/update-branch")
async def update_enrollment_branch(
    enrollment_id: int,
    data: dict,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """แก้เลขสาขาของ enrollment + อัพเดท users ที่สร้างไปแล้ว."""
    new_branch_num = (data.get("branch_number") or "").strip()
    if not new_branch_num:
        raise HTTPException(status_code=400, detail={"error": "MISSING", "message": "กรุณาระบุ branch_number"})
    if new_branch_num.isdigit():
        new_branch_num = new_branch_num.zfill(3)

    result = await db.execute(select(BranchEnrollment).where(BranchEnrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบรายการ"})

    old_branch_id = f"B{enrollment.branch_number}" if enrollment.branch_number else None
    new_branch_id = f"B{new_branch_num}"

    enrollment.branch_number = new_branch_num

    # อัพเดท users ที่สร้างจาก enrollment นี้
    updated_users = 0
    if old_branch_id:
        user_result = await db.execute(select(User).where(User.branch_id == old_branch_id, User.role == "branch_admin"))
        for u in user_result.scalars().all():
            u.branch_id = new_branch_id
            updated_users += 1

    await db.commit()
    return {
        "id": enrollment.id,
        "old_branch": old_branch_id,
        "new_branch": new_branch_id,
        "users_updated": updated_users,
        "message": f"เปลี่ยนเลขสาขาจาก {old_branch_id or 'ว่าง'} → {new_branch_id} สำเร็จ (อัพเดท {updated_users} users)",
    }


@router.get("/users")
async def list_users(user=Depends(require_central_admin), db: AsyncSession = Depends(get_db)):
    """List all users (central admin only)."""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    return [
        {
            "id": u.id, "username": u.username, "full_name": u.full_name,
            "email": u.email, "role": u.role, "branch_id": u.branch_id, "status": u.status,
        }
        for u in users
    ]


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    data: dict,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user (username, email, branch_id, status)."""
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบ user"})

    new_username = (data.get("username") or "").strip()
    if new_username and new_username != u.username:
        dup = await db.execute(select(User).where(User.username == new_username))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail={"error": "DUPLICATE", "message": f"username '{new_username}' ซ้ำ"})
        u.username = new_username

    if "email" in data:
        u.email = (data["email"] or "").strip() or None
    if "full_name" in data:
        u.full_name = (data["full_name"] or "").strip() or u.full_name
    if "branch_id" in data:
        u.branch_id = (data["branch_id"] or "").strip() or None
    if "status" in data and data["status"] in ("active", "disabled"):
        u.status = data["status"]

    await db.commit()
    return {"id": u.id, "username": u.username, "message": "อัพเดทสำเร็จ"}
