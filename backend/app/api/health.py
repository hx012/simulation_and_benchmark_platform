from fastapi import APIRouter

from app.common.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check():
    settings = get_settings()

    return {
        "status": "ok",
        "environment": settings.app_env,
        "version": settings.app_version,
    }
