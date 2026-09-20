from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.core.config import get_settings
from app.core.redis import redis_health
from app.db.models import User

router = APIRouter(tags=["health"])


@router.get("/system-health")
async def system_health(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("ADMIN", "DISPATCHER"))):
    settings = get_settings()
    db_status = {"status": "ok"}
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = {"status": "down", "detail": str(exc)}
    redis = await redis_health()
    return {
        "service": settings.app_name,
        "environment": settings.app_env,
        "time": datetime.now(timezone.utc).isoformat(),
        "api": {"status": "ok"},
        "database": db_status,
        "redis": redis,
        "websocket": {"status": "ok", "detail": "in-process hub"},
        "radio_gateway": {
            "status": "not_configured" if not settings.radio_gateway_enabled else "enabled",
            "detail": "Requires external radio hardware. Not claimed available without a connected gateway.",
        },
        "satellite": {
            "status": "not_configured" if not settings.satellite_adapter_enabled else "enabled",
            "provider": settings.satellite_provider or None,
            "detail": "Requires supported satellite hardware or provider. Software cannot create satellite links alone.",
        },
        "simulated_adapters_allowed": settings.allow_simulated_adapters,
    }


@router.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "abhaysetu-backend"}
