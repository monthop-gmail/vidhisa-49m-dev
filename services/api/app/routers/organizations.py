"""Organizations API endpoints with CSV import/export support."""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.branch_auth import check_branch_access
from app.database import get_db
from app.models import Branch, Organization, Record
from app.schemas import (
    ImportResult,
    OrganizationCreate,
    OrganizationCreateResponse,
    OrganizationDetail,
    OrganizationListItem,
)

router = APIRouter()

EXPORT_FIELDS = [
    "id",
    "name",
    "org_type",
    "branch_id",
    "sub_district",
    "district",
    "province",
    "email",
    "max_participants",
    "gender_male",
    "gender_female",
    "gender_unspecified",
    "contact_name",
    "contact_phone",
    "contact_line_id",
    "enrolled_date",
    "enrolled_until",
    "latitude",
    "longitude",
    "contact",
]


@router.get("/organizations")
async def list_organizations(db: AsyncSession = Depends(get_db)):
    """List all organizations with their statistics."""
    stmt = (
        select(
            Organization,
            func.coalesce(func.sum(Record.minutes), 0).label("total_minutes"),
            func.count(Record.id).label("total_records"),
        )
        .outerjoin(
            Record,
            (Record.org_id == Organization.id) & (Record.status == "approved"),
        )
        .group_by(Organization.id)
        .order_by(Organization.name)
    )

    result = await db.execute(stmt)
    return [
        {
            "id": r.Organization.id, "name": r.Organization.name,
            "org_type": r.Organization.org_type, "branch_id": r.Organization.branch_id,
            "sub_district": r.Organization.sub_district, "district": r.Organization.district,
            "province": r.Organization.province, "email": r.Organization.email,
            "max_participants": r.Organization.max_participants,
            "enrolled_date": r.Organization.enrolled_date,
            "enrolled_until": r.Organization.enrolled_until,
            "latitude": r.Organization.latitude, "longitude": r.Organization.longitude,
            "contact": r.Organization.contact, "status": r.Organization.status,
            "total_minutes": r.total_minutes, "total_records": r.total_records,
        }
        for r in result.all()
    ]


@router.get("/organizations/export")
async def export_organizations(db: AsyncSession = Depends(get_db)):
    """Export all organizations as CSV with UTF-8 BOM for Excel compatibility."""
    result = await db.execute(select(Organization).order_by(Organization.name))
    orgs = result.scalars().all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(EXPORT_FIELDS)
    for o in orgs:
        writer.writerow([getattr(o, f) or "" for f in EXPORT_FIELDS])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=organizations.csv"},
    )


@router.post("/organizations/import", response_model=ImportResult)
async def import_organizations(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import organizations from CSV file.

    Creates new organizations or updates existing ones based on ID.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_FILE", "message": "รองรับเฉพาะไฟล์ .csv"},
        )

    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    required = {"id", "name"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_HEADER",
                "message": f"CSV ต้องมีคอลัมน์: {', '.join(EXPORT_FIELDS)}",
            },
        )

    existing_result = await db.execute(select(Organization.id))
    existing_ids = {r[0] for r in existing_result.all()}
    branch_result = await db.execute(select(Branch.id))
    valid_branches = {r[0] for r in branch_result.all()}

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        org_id = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        branch_id = (row.get("branch_id") or "").strip()

        if not org_id or not name:
            errors.append(f"แถว {i}: ขาด id หรือ name")
            continue
        if branch_id and branch_id not in valid_branches:
            errors.append(f"แถว {i}: branch_id '{branch_id}' ไม่มีในระบบ")
            continue

        lat = (row.get("latitude") or "").strip()
        lng = (row.get("longitude") or "").strip()
        max_p = (row.get("max_participants") or "").strip()
        g_male = (row.get("gender_male") or "").strip()
        g_female = (row.get("gender_female") or "").strip()
        g_unspec = (row.get("gender_unspecified") or "").strip()

        fields = {
            "name": name,
            "org_type": (row.get("org_type") or "").strip() or None,
            "branch_id": branch_id or None,
            "sub_district": (row.get("sub_district") or "").strip() or None,
            "district": (row.get("district") or "").strip() or None,
            "province": (row.get("province") or "").strip() or None,
            "email": (row.get("email") or "").strip() or None,
            "max_participants": int(max_p) if max_p else None,
            "gender_male": int(g_male) if g_male else 0,
            "gender_female": int(g_female) if g_female else 0,
            "gender_unspecified": int(g_unspec) if g_unspec else 0,
            "contact_name": (row.get("contact_name") or "").strip() or None,
            "contact_phone": (row.get("contact_phone") or "").strip() or None,
            "contact_line_id": (row.get("contact_line_id") or "").strip() or None,
            "enrolled_date": (row.get("enrolled_date") or "").strip() or None,
            "enrolled_until": (row.get("enrolled_until") or "").strip() or None,
            "latitude": float(lat) if lat else None,
            "longitude": float(lng) if lng else None,
            "contact": (row.get("contact") or "").strip() or None,
        }

        if org_id in existing_ids:
            result = await db.execute(select(Organization).where(Organization.id == org_id))
            org = result.scalar_one()
            for k, v in fields.items():
                if k == "branch_id" and not v:
                    continue  # keep existing branch_id if not provided
                setattr(org, k, v)
            updated += 1
        else:
            org = Organization(id=org_id, **fields)
            db.add(org)
            existing_ids.add(org_id)
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


@router.get("/organizations/{org_id}", response_model=OrganizationDetail)
async def get_organization(org_id: str, db: AsyncSession = Depends(get_db)):
    """Get details and statistics for a specific organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "ไม่พบองค์กร"},
        )

    stmt = select(
        func.coalesce(func.sum(Record.minutes), 0),
        func.count(Record.id),
    ).where(Record.org_id == org_id, Record.status == "approved")
    stats = (await db.execute(stmt)).one()

    return {
        "id": org.id, "name": org.name, "org_type": org.org_type,
        "branch_id": org.branch_id, "sub_district": org.sub_district,
        "district": org.district, "province": org.province,
        "email": org.email, "max_participants": org.max_participants,
        "gender_male": org.gender_male, "gender_female": org.gender_female,
        "gender_unspecified": org.gender_unspecified,
        "contact_name": org.contact_name, "contact_phone": org.contact_phone,
        "contact_line_id": org.contact_line_id,
        "enrolled_date": org.enrolled_date, "enrolled_until": org.enrolled_until,
        "latitude": org.latitude, "longitude": org.longitude,
        "contact": org.contact, "status": org.status,
        "total_minutes": stats[0], "total_records": stats[1],
    }


@router.post("/organizations", status_code=201, response_model=OrganizationCreateResponse)
async def create_organization(data: OrganizationCreate, db: AsyncSession = Depends(get_db)):
    """Create a new organization."""
    existing = await db.execute(select(Organization).where(Organization.id == data.id))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": "DUPLICATE_ID", "message": "รหัสองค์กรซ้ำ"},
        )

    org = Organization(
        id=data.id,
        name=data.name,
        org_type=data.org_type,
        branch_id=data.branch_id,
        sub_district=data.sub_district,
        district=data.district,
        province=data.province,
        email=data.email,
        max_participants=data.max_participants,
        gender_male=data.gender_male,
        gender_female=data.gender_female,
        gender_unspecified=data.gender_unspecified,
        contact_name=data.contact_name,
        contact_phone=data.contact_phone,
        contact_line_id=data.contact_line_id,
        enrolled_date=data.enrolled_date,
        enrolled_until=data.enrolled_until,
        latitude=data.latitude,
        longitude=data.longitude,
        contact=data.contact,
    )
    db.add(org)
    await db.commit()
    return {"id": org.id, "name": org.name, "message": "สร้างองค์กรสำเร็จ"}


@router.put("/organizations/{org_id}")
async def update_organization(
    org_id: str,
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "ไม่พบองค์กร"},
        )

    org.name = data.name
    org.org_type = data.org_type
    org.branch_id = data.branch_id
    org.sub_district = data.sub_district
    org.district = data.district
    org.province = data.province
    org.email = data.email
    org.max_participants = data.max_participants
    org.gender_male = data.gender_male
    org.gender_female = data.gender_female
    org.gender_unspecified = data.gender_unspecified
    org.contact_name = data.contact_name
    org.contact_phone = data.contact_phone
    org.contact_line_id = data.contact_line_id
    org.enrolled_date = data.enrolled_date
    org.enrolled_until = data.enrolled_until
    org.latitude = data.latitude
    org.longitude = data.longitude
    org.contact = data.contact
    await db.commit()
    return {"id": org.id, "name": org.name, "message": "อัพเดทองค์กรสำเร็จ"}


@router.patch("/organizations/{org_id}/approve")
async def approve_organization(org_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Approve a pending organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบองค์กร"})
    if org.branch_id:
        check_branch_access(user, org.branch_id)
    org.status = "approved"
    await db.commit()
    return {"id": org.id, "status": "approved"}


@router.patch("/organizations/{org_id}/reject")
async def reject_organization(org_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Reject a pending organization."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "ไม่พบองค์กร"})
    if org.branch_id:
        check_branch_access(user, org.branch_id)
    org.status = "rejected"
    await db.commit()
    return {"id": org.id, "status": "rejected"}
