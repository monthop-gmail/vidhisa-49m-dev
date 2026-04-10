"""Authentication module — JWT + bcrypt."""

import os
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User

SECRET_KEY = os.getenv("JWT_SECRET", "vidhisa-49m-secret-change-me")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int, username: str, role: str, branch_id: str | None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "role": role, "branch_id": branch_id or "", "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail={"error": "INVALID_TOKEN", "message": "Token ไม่ถูกต้อง"})


def generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Extract user from Authorization header or cookie."""
    token = None

    # Check Authorization header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]

    # Check cookie
    if not token:
        token = request.cookies.get("token")

    if not token:
        raise HTTPException(status_code=401, detail={"error": "NOT_AUTHENTICATED", "message": "กรุณา login"})

    payload = decode_token(token)
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id, User.status == "active"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail={"error": "USER_NOT_FOUND", "message": "ไม่พบ user"})
    return user


def require_central_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "central_admin":
        raise HTTPException(status_code=403, detail={"error": "FORBIDDEN", "message": "ต้องเป็น Admin กลาง"})
    return user
