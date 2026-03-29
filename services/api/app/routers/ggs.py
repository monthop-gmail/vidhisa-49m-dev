"""Google Sheet (GGS) integration — pull data from shared Google Sheets."""

import csv
import io
import re
from datetime import date as date_type

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Branch, BranchGroup, Organization, Participant, Record

router = APIRouter()


def extract_sheet_id(url: str) -> str:
    """Extract Google Sheet ID from URL."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise HTTPException(status_code=400, detail={"error": "INVALID_URL", "message": "URL ไม่ใช่ Google Sheet"})
    return match.group(1)


def build_csv_url(sheet_id: str, sheet_name: str) -> str:
    """Build CSV export URL for a specific sheet."""
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"


async def fetch_csv(url: str) -> list[dict]:
    """Fetch CSV from URL and return list of dicts."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        res = await client.get(url)
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail={
                "error": "GGS_FETCH_FAILED",
                "message": f"ดึงข้อมูลจาก Google Sheet ไม่ได้ (HTTP {res.status_code})",
            })
    text = res.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


@router.post("/ggs/sync")
async def sync_from_ggs(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Sync data from a Google Sheet URL.

    Body: {"url": "https://docs.google.com/spreadsheets/d/xxx/edit", "sheets": ["organizations", "participants", "records"]}
    """
    url = data.get("url", "").strip()
    sheets = data.get("sheets", ["organizations", "participants", "records"])
    if not url:
        raise HTTPException(status_code=400, detail={"error": "MISSING_URL", "message": "กรุณาระบุ URL ของ Google Sheet"})

    sheet_id = extract_sheet_id(url)
    results = {}

    # Load valid references
    branch_result = await db.execute(select(Branch.id))
    valid_branches = {r[0] for r in branch_result.all()}
    org_result = await db.execute(select(Organization.id))
    existing_orgs = {r[0] for r in org_result.all()}

    if "organizations" in sheets:
        results["organizations"] = await _sync_organizations(sheet_id, db, valid_branches, existing_orgs)

    if "participants" in sheets:
        results["participants"] = await _sync_participants(sheet_id, db, valid_branches)

    if "records" in sheets:
        results["records"] = await _sync_records(sheet_id, db, valid_branches)

    return results


async def _sync_organizations(sheet_id: str, db: AsyncSession, valid_branches: set, existing_orgs: set) -> dict:
    """Sync organizations sheet."""
    try:
        rows = await fetch_csv(build_csv_url(sheet_id, "organizations"))
    except Exception:
        return {"status": "skip", "message": "ไม่พบ sheet 'organizations'"}

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(rows, start=2):
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

        fields = {
            "name": name,
            "org_type": (row.get("org_type") or "").strip() or None,
            "branch_id": branch_id or None,
            "sub_district": (row.get("sub_district") or "").strip() or None,
            "district": (row.get("district") or "").strip() or None,
            "province": (row.get("province") or "").strip() or None,
            "email": (row.get("email") or "").strip() or None,
            "max_participants": int(max_p) if max_p else None,
            "gender_male": int((row.get("gender_male") or "0").strip() or "0"),
            "gender_female": int((row.get("gender_female") or "0").strip() or "0"),
            "gender_unspecified": int((row.get("gender_unspecified") or "0").strip() or "0"),
            "contact_name": (row.get("contact_name") or "").strip() or None,
            "contact_phone": (row.get("contact_phone") or "").strip() or None,
            "contact_line_id": (row.get("contact_line_id") or "").strip() or None,
            "enrolled_date": (row.get("enrolled_date") or "").strip() or None,
            "enrolled_until": (row.get("enrolled_until") or "").strip() or None,
            "latitude": float(lat) if lat else None,
            "longitude": float(lng) if lng else None,
        }

        if org_id in existing_orgs:
            result = await db.execute(select(Organization).where(Organization.id == org_id))
            org = result.scalar_one()
            for k, v in fields.items():
                setattr(org, k, v)
            updated += 1
        else:
            org = Organization(id=org_id, **fields)
            db.add(org)
            existing_orgs.add(org_id)
            created += 1

    await db.commit()
    return {"created": created, "updated": updated, "errors": errors}


async def _sync_participants(sheet_id: str, db: AsyncSession, valid_branches: set) -> dict:
    """Sync participants sheet."""
    try:
        rows = await fetch_csv(build_csv_url(sheet_id, "participants"))
    except Exception:
        return {"status": "skip", "message": "ไม่พบ sheet 'participants'"}

    created = 0
    errors = []

    for i, row in enumerate(rows, start=2):
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
    return {"created": created, "errors": errors}


async def _sync_records(sheet_id: str, db: AsyncSession, valid_branches: set) -> dict:
    """Sync records sheet — upsert by branch_id + org_id/name + date."""
    try:
        rows = await fetch_csv(build_csv_url(sheet_id, "records"))
    except Exception:
        return {"status": "skip", "message": "ไม่พบ sheet 'records'"}

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(rows, start=2):
        rec_type = (row.get("type") or "").strip()
        branch_id = (row.get("branch_id") or "").strip()
        name = (row.get("name") or "").strip()
        date_str = (row.get("date") or "").strip()

        if not rec_type or not branch_id or not name or not date_str:
            errors.append(f"แถว {i}: ขาดข้อมูลที่จำเป็น")
            continue
        if branch_id not in valid_branches:
            errors.append(f"แถว {i}: branch_id '{branch_id}' ไม่มีในระบบ")
            continue

        org_id = (row.get("org_id") or "").strip() or None
        rec_date = date_type.fromisoformat(date_str)

        if rec_type == "bulk":
            mm = int((row.get("morning_male") or "0").strip() or "0")
            mf = int((row.get("morning_female") or "0").strip() or "0")
            mu = int((row.get("morning_unspecified") or "0").strip() or "0")
            am = int((row.get("afternoon_male") or "0").strip() or "0")
            af = int((row.get("afternoon_female") or "0").strip() or "0")
            au = int((row.get("afternoon_unspecified") or "0").strip() or "0")
            em = int((row.get("evening_male") or "0").strip() or "0")
            ef = int((row.get("evening_female") or "0").strip() or "0")
            eu = int((row.get("evening_unspecified") or "0").strip() or "0")
            total_people = (mm+mf+mu) + (am+af+au) + (em+ef+eu)
            minutes = total_people * 5

            fields = {
                "type": "bulk", "branch_id": branch_id, "name": name, "org_id": org_id,
                "minutes": minutes if minutes > 0 else int((row.get("minutes") or "0").strip() or "0"),
                "participant_count": max(mm+mf+mu, am+af+au, em+ef+eu),
                "minutes_per_person": 5,
                "morning_male": mm, "morning_female": mf, "morning_unspecified": mu,
                "afternoon_male": am, "afternoon_female": af, "afternoon_unspecified": au,
                "evening_male": em, "evening_female": ef, "evening_unspecified": eu,
                "date": rec_date, "status": "pending",
                "submitted_by": (row.get("submitted_by") or "").strip() or None,
                "submitted_phone": (row.get("submitted_phone") or "").strip() or None,
            }
        else:
            # individual
            morning = int((row.get("morning") or "0").strip() or "0")
            afternoon = int((row.get("afternoon") or "0").strip() or "0")
            evening = int((row.get("evening") or "0").strip() or "0")
            minutes = (morning + afternoon + evening) * 5

            fields = {
                "type": "individual", "branch_id": branch_id, "name": name,
                "minutes": minutes if minutes > 0 else int((row.get("minutes") or "0").strip() or "0"),
                "morning_male": morning, "afternoon_male": afternoon, "evening_male": evening,
                "date": rec_date, "status": "pending",
            }

        # Upsert
        existing = None
        if org_id:
            stmt = select(Record).where(
                Record.branch_id == branch_id, Record.org_id == org_id,
                Record.name == name, Record.date == rec_date,
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
    return {"created": created, "updated": updated, "errors": errors}


@router.get("/ggs/sources")
async def list_ggs_sources(db: AsyncSession = Depends(get_db)):
    """List all registered GGS sources (branches with ggs_url)."""
    stmt = select(Branch.id, Branch.name, Branch.group_id).order_by(Branch.id)
    result = await db.execute(stmt)
    # For now return branch list — ggs_url will be added to branch table later
    return [{"branch_id": r.id, "branch_name": r.name, "group_id": r.group_id} for r in result.all()]
