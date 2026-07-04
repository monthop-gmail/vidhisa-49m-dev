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

from app.auth import generate_password, get_current_user, hash_password, require_central_admin
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
    col_labels = [(c.get("label", "") or "").strip() for c in table["cols"]]

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
async def list_enrollments(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List branch enrollment requests. Central: all. Branch admin: own branch only."""
    result = await db.execute(select(BranchEnrollment).order_by(BranchEnrollment.id))
    enrollments = result.scalars().all()
    if user.role != "central_admin":
        # ดูเฉพาะ enrollment ของสาขาตัวเอง (branch_id "B020" ↔ branch_number "020")
        allowed = set(list(user.branch_ids or []) + ([user.branch_id] if user.branch_id else []))
        allowed_numbers = {b.lstrip("B") for b in allowed if b}
        enrollments = [
            e for e in enrollments
            if e.branch_number and e.branch_number.lstrip("B") in allowed_numbers
        ]
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


@router.get("/enrollments/{enrollment_id}/preview-approve")
async def preview_approve_enrollment(
    enrollment_id: int,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Preview ก่อน approve — บอกว่า admin emails ใดมี user อยู่แล้ว ให้ admin ตัดสินใจ on_conflict"""
    result = await db.execute(select(BranchEnrollment).where(BranchEnrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบรายการ"})

    branch_id = f"B{enrollment.branch_number}" if enrollment.branch_number else None
    admins = [
        ("admin1", enrollment.admin1_name, enrollment.admin1_email),
        ("admin2", enrollment.admin2_name, enrollment.admin2_email),
        ("admin3", enrollment.admin3_name, enrollment.admin3_email),
    ]
    out = []
    for slot, name, email in admins:
        if not name:
            continue
        existing = None
        if email:
            er = await db.execute(select(User).where(User.email == email))
            existing_u = er.scalars().first()
            if existing_u:
                existing = {
                    "id": existing_u.id, "username": existing_u.username,
                    "full_name": existing_u.full_name,
                    "branch_id": existing_u.branch_id,
                    "branch_ids": list(existing_u.branch_ids or []),
                }
        out.append({"slot": slot, "name": name, "email": email, "existing_user": existing})
    return {"enrollment_id": enrollment.id, "branch_id": branch_id, "admins": out}


@router.patch("/enrollments/{enrollment_id}/approve")
async def approve_enrollment(
    enrollment_id: int,
    on_conflict: str = "add_branch",
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve enrollment → create users (or add branch to existing) → send email.

    on_conflict (เมื่อ admin email มี user อยู่แล้ว):
      - 'add_branch' (default): เพิ่ม branch_id เข้า user.branch_ids ของ user เดิม
      - 'create_new': สร้าง user ใหม่พร้อม username suffix (-2, -3, ...)
    """
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
                    sub_district=branch_obj.sub_district,
                    district=branch_obj.district,
                    province=branch_obj.province,
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

    # Track used usernames (DB + pending adds in this txn) so admins sharing an email don't collide
    taken_usernames_result = await db.execute(select(User.username))
    used_usernames = {r[0] for r in taken_usernames_result.all()}

    users_added_branch = []  # for users that already exist and got branch added
    for name, email, phone, idx in admins:
        if not name:
            continue

        # Check if email already exists (multi-branch admin support)
        existing_user = None
        if email and on_conflict == "add_branch":
            er = await db.execute(select(User).where(User.email == email))
            existing_user = er.scalars().first()

        if existing_user and branch_id:
            # Add branch_id to existing user's branch_ids if not already there
            current_ids = list(existing_user.branch_ids or [])
            if existing_user.branch_id and existing_user.branch_id not in current_ids:
                current_ids.append(existing_user.branch_id)
            if branch_id not in current_ids:
                current_ids.append(branch_id)
                existing_user.branch_ids = current_ids
            users_added_branch.append({
                "username": existing_user.username, "name": existing_user.full_name,
                "email": email, "branch_added": branch_id, "user_id": existing_user.id,
            })
            continue

        # ใช้ email เป็น username, เบอร์โทรเป็น password
        base = email if email else _make_username(enrollment.branch_number, idx)
        password = phone if phone else generate_password()

        username = base
        if username in used_usernames:
            username = f"{base}-{idx}"
        suffix = 2
        while username in used_usernames:
            username = f"{base}-{idx}-{suffix}"
            suffix += 1
        used_usernames.add(username)

        u = User(
            username=username,
            password_hash=hash_password(password),
            full_name=name,
            email=email,
            phone=phone,
            role="branch_admin",
            branch_id=branch_id,
            branch_ids=[branch_id] if branch_id else [],
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
        "users_added_branch": users_added_branch,  # existing users ที่ได้รับ branch เพิ่ม
        "emails_sent": len(emails_sent),
        "org_created": org_created,
        "users": [{"username": u["username"], "name": u["name"], "email": u["email"]} for u in users_created],
        "message": f"อนุมัติสำเร็จ สร้าง {len(users_created)} users ใหม่"
                   + (f", เพิ่ม branch ให้ {len(users_added_branch)} users เดิม" if users_added_branch else "")
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
async def list_users(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List users. Central: all. Branch admin: co-admins ของสาขาที่ตัวเองดูแล."""
    result = await db.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    if user.role != "central_admin":
        allowed = set(list(user.branch_ids or []) + ([user.branch_id] if user.branch_id else []))
        def user_branches(u: User) -> set[str]:
            return set(list(u.branch_ids or []) + ([u.branch_id] if u.branch_id else []))
        users = [u for u in users if user_branches(u) & allowed]
    return [
        {
            "id": u.id, "username": u.username, "full_name": u.full_name,
            "email": u.email, "phone": u.phone, "role": u.role,
            "branch_id": u.branch_id, "branch_ids": list(u.branch_ids or []),
            "status": u.status,
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
    if "phone" in data:
        u.phone = (data["phone"] or "").strip() or None
    if "branch_id" in data:
        u.branch_id = (data["branch_id"] or "").strip() or None
    if "branch_ids" in data:
        # รายการสาขาที่ user ดูแล (multi-branch admin)
        ids = data["branch_ids"]
        if isinstance(ids, list):
            u.branch_ids = [str(b).strip() for b in ids if str(b).strip()]
    if "status" in data and data["status"] in ("active", "disabled"):
        u.status = data["status"]

    await db.commit()
    return {"id": u.id, "username": u.username, "message": "อัพเดทสำเร็จ"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    data: dict,
    user=Depends(require_central_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin reset password — set new password (≥6 chars)."""
    new_password = (data.get("password") or "").strip()
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail={"error": "PASSWORD_TOO_SHORT", "message": "รหัสผ่านต้อง ≥ 6 ตัวอักษร"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบ user"})
    u.password_hash = hash_password(new_password)
    await db.commit()
    return {"id": u.id, "username": u.username, "message": "เปลี่ยนรหัสผ่านสำเร็จ"}
