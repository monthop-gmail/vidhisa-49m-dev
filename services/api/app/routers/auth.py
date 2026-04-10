"""Auth API — login, me, change password."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_token, get_current_user, hash_password, verify_password,
)
from app.database import get_db
from app.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/auth/login")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login and return JWT token."""
    result = await db.execute(
        select(User).where(User.username == data.username, User.status == "active")
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail={
            "error": "INVALID_CREDENTIALS", "message": "username หรือ password ไม่ถูกต้อง"
        })

    token = create_token(user.id, user.username, user.role, user.branch_id)
    return {
        "token": token,
        "user": {
            "id": user.id, "username": user.username, "full_name": user.full_name,
            "role": user.role, "branch_id": user.branch_id,
        },
    }


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return {
        "id": user.id, "username": user.username, "full_name": user.full_name,
        "email": user.email, "phone": user.phone,
        "role": user.role, "branch_id": user.branch_id,
    }


@router.post("/auth/change-password")
async def change_password(
    data: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change own password."""
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail={
            "error": "WRONG_PASSWORD", "message": "รหัสผ่านเดิมไม่ถูกต้อง"
        })
    user.password_hash = hash_password(data.new_password)
    await db.commit()
    return {"message": "เปลี่ยนรหัสผ่านสำเร็จ"}
