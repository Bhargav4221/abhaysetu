from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.common import LoginRequest, RegisterRequest
from app.services.auth_service import login_user, register_user
from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.redis import incr_with_ttl

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await register_user(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    hits = await incr_with_ttl(f"login:{ip}", 60)
    if hits and hits > settings.login_rate_limit_per_ip_per_minute:
        raise HTTPException(status_code=429, detail="Too many login attempts")
    try:
        return await login_user(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "language": user.language,
    }
