"""Branch authorization — check user can access branch."""

from fastapi import HTTPException

from app.models import User


def check_branch_access(user: User, branch_id: str):
    """Raise 403 if user cannot access this branch (supports multi-branch admin)."""
    if user.role == "central_admin":
        return  # central admin can access all
    allowed = list(user.branch_ids or [])
    if user.branch_id and user.branch_id not in allowed:
        allowed.append(user.branch_id)
    if branch_id not in allowed:
        raise HTTPException(status_code=403, detail={
            "error": "FORBIDDEN",
            "message": f"คุณไม่มีสิทธิ์จัดการสาขา {branch_id} (คุณดูแล {allowed})",
        })
