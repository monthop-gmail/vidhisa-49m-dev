"""Branches API endpoints with CSV import/export support."""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional, scoped_branch_id
from app.database import get_db
from app.models import Branch, BranchGroup, Record, User
from app.schemas import BranchCreateResponse, BranchDetail, BranchListItem, ImportResult

router = APIRouter()

EXPORT_FIELDS = [
    "id",
    "name",
    "group_id",
    "province",
    "province_code",
    "latitude",
    "longitude",
    "admin_name",
    "contact",
]


@router.get("/branches")
async def list_branches(
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
):
    """List branches with their statistics (branch_admin sees only their own)."""
    branch_filter = scoped_branch_id(user, None)
    stmt = (
        select(
            Branch,
            func.coalesce(func.sum(Record.minutes), 0).label("total_minutes"),
            func.count(Record.id).label("total_records"),
        )
        .outerjoin(
            Record,
            (Record.branch_id == Branch.id) & (Record.status == "approved") & (Record.org_id.like("%-00")),
        )
        .group_by(Branch.id)
        .order_by(Branch.id)
    )
    if branch_filter:
        stmt = stmt.where(Branch.id == branch_filter)

    result = await db.execute(stmt)
    return [
        {
            "id": r.Branch.id, "name": r.Branch.name,
            "group_id": r.Branch.group_id, "custom_region": r.Branch.custom_region,
            "sub_district": r.Branch.sub_district, "district": r.Branch.district,
            "province": r.Branch.province, "province_code": r.Branch.province_code,
            "latitude": r.Branch.latitude, "longitude": r.Branch.longitude,
            "admin_name": r.Branch.admin_name, "contact": r.Branch.contact,
            "opening_hours": r.Branch.opening_hours,
            "total_minutes": r.total_minutes, "total_records": r.total_records,
        }
        for r in result.all()
    ]


@router.get("/branches/export")
async def export_branches(db: AsyncSession = Depends(get_db)):
    """Export all branches as CSV with UTF-8 BOM for Excel compatibility."""
    result = await db.execute(select(Branch).order_by(Branch.id))
    branches = result.scalars().all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(EXPORT_FIELDS)
    for b in branches:
        writer.writerow([getattr(b, f) or "" for f in EXPORT_FIELDS])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=branches.csv"},
    )


@router.post("/branches/import", response_model=ImportResult)
async def import_branches(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Import branches from CSV file.

    Creates new branches or updates existing ones based on ID.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_FILE", "message": "รองรับเฉพาะไฟล์ .csv"},
        )

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    required = {"id", "name", "province", "province_code"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_HEADER",
                "message": f"CSV ต้องมีคอลัมน์: {', '.join(EXPORT_FIELDS)}",
            },
        )

    existing_result = await db.execute(select(Branch.id))
    existing_ids = {r[0] for r in existing_result.all()}
    group_result = await db.execute(select(BranchGroup.id))
    valid_groups = {r[0] for r in group_result.all()}

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        branch_id = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        province = (row.get("province") or "").strip()
        province_code = (row.get("province_code") or "").strip()
        group_id = (row.get("group_id") or "").strip()

        if not branch_id or not name or not province or not province_code:
            errors.append(f"แถว {i}: ขาด id, name, province หรือ province_code")
            continue
        if group_id and group_id not in valid_groups:
            errors.append(f"แถว {i}: group_id '{group_id}' ไม่มีในระบบ")
            continue

        lat = (row.get("latitude") or "").strip()
        lng = (row.get("longitude") or "").strip()

        if branch_id in existing_ids:
            result = await db.execute(select(Branch).where(Branch.id == branch_id))
            branch = result.scalar_one()
            branch.name = name
            branch.group_id = group_id or branch.group_id
            branch.province = province
            branch.province_code = province_code
            branch.latitude = float(lat) if lat else None
            branch.longitude = float(lng) if lng else None
            branch.admin_name = (row.get("admin_name") or "").strip() or None
            branch.contact = (row.get("contact") or "").strip() or None
            updated += 1
        else:
            branch = Branch(
                id=branch_id,
                name=name,
                group_id=group_id or None,
                province=province,
                province_code=province_code,
                latitude=float(lat) if lat else None,
                longitude=float(lng) if lng else None,
                admin_name=(row.get("admin_name") or "").strip() or None,
                contact=(row.get("contact") or "").strip() or None,
            )
            db.add(branch)
            existing_ids.add(branch_id)
            created += 1

    await db.commit()
    return {
        "created": created,
        "updated": updated,
        "errors": errors,
        "message": (
            f"นำเข้าสำเร็จ: สร้างใหม่ {created}, อัพเดท {updated}" + (f", ข้อผิดพลาด {len(errors)} แถว" if errors else "")
        ),
    }


@router.get("/branches/{branch_id}", response_model=BranchDetail)
async def get_branch(branch_id: str, db: AsyncSession = Depends(get_db)):
    """Get details and statistics for a specific branch."""
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "ไม่พบสาขา"},
        )

    stmt = select(
        func.coalesce(func.sum(Record.minutes), 0),
        func.count(Record.id),
    ).where(
        Record.branch_id == branch_id,
        Record.status == "approved",
        Record.org_id.like("%-00"),
    )
    stats = (await db.execute(stmt)).one()

    return {
        "id": branch.id,
        "name": branch.name,
        "group_id": branch.group_id,
        "province": branch.province,
        "province_code": branch.province_code,
        "latitude": branch.latitude,
        "longitude": branch.longitude,
        "admin_name": branch.admin_name,
        "contact": branch.contact,
        "total_minutes": stats[0],
        "total_records": stats[1],
    }


@router.post("/branches", status_code=201, response_model=BranchCreateResponse)
async def create_branch(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new branch."""
    branch_id = data.get("id", "").strip()
    name = data.get("name", "").strip()
    if not branch_id or not name:
        raise HTTPException(
            status_code=400,
            detail={"error": "MISSING_FIELDS", "message": "ต้องระบุ id และ name"},
        )

    existing = await db.execute(select(Branch).where(Branch.id == branch_id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": "DUPLICATE_ID", "message": "รหัสสาขาซ้ำ"},
        )

    branch = Branch(
        id=branch_id,
        name=name,
        group_id=data.get("group_id") or None,
        province=data.get("province", ""),
        province_code=data.get("province_code", ""),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        admin_name=data.get("admin_name"),
        contact=data.get("contact"),
    )
    db.add(branch)
    await db.commit()
    return {"id": branch.id, "name": branch.name, "message": "สร้างสาขาสำเร็จ"}


@router.put("/branches/{branch_id}")
async def update_branch(branch_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an existing branch."""
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    branch = result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "ไม่พบสาขา"},
        )

    branch.name = data.get("name", branch.name)
    branch.group_id = data.get("group_id", branch.group_id)
    branch.province = data.get("province", branch.province)
    branch.province_code = data.get("province_code", branch.province_code)
    branch.latitude = data.get("latitude", branch.latitude)
    branch.longitude = data.get("longitude", branch.longitude)
    branch.admin_name = data.get("admin_name", branch.admin_name)
    branch.contact = data.get("contact", branch.contact)
    await db.commit()
    return {"id": branch.id, "name": branch.name, "message": "อัพเดทสาขาสำเร็จ"}
