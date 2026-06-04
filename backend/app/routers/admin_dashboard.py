from fastapi import APIRouter

from app.core.response import ok
from app.services.admin_service import dashboard

router = APIRouter()


@router.get("/admin/dashboard")
def admin_dashboard():
    return ok(dashboard())
