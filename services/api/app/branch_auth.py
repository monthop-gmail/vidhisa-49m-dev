"""Branch authorization — check user can access branch."""

from fastapi import HTTPException

from app.models import User


def check_branch_access(user: User, branch_id: str):
    """Raise 403 if user cannot access this branch."""
    if user.role == "central_admin":
        return  # central admin can access all
    if user.branch_id != branch_id:
        raise HTTPException(status_code=403, detail={
            "error": "FORBIDDEN",
            "message": f"คุณไม่มีสิทธิ์จัดการสาขา {branch_id} (คุณดูแลสาขา {user.branch_id})",
        })
