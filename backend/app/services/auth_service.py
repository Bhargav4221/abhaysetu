from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.db.models import Device, User
from app.schemas.common import LoginRequest, RegisterRequest, TokenPair

ALLOWED_SELF_REGISTER = {"CITIZEN", "VOLUNTEER"}


def _id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(8)}"


async def register_user(db: AsyncSession, body: RegisterRequest) -> TokenPair:
    role = body.role.upper()
    if role not in ALLOWED_SELF_REGISTER:
        role = "CITIZEN"
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing:
        raise ValueError("Email already registered")
    user = User(
        id=_id("USR"),
        email=body.email.lower(),
        name=body.name,
        hashed_password=hash_password(body.password),
        role=role,
        language=body.language,
    )
    db.add(user)
    if body.device_id and body.public_key:
        db.add(
            Device(
                id=body.device_id,
                user_id=user.id,
                public_key=body.public_key,
                platform=body.platform,
                last_seen_at=datetime.now(timezone.utc),
            )
        )
    await db.commit()
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
        role=user.role,
        user_id=user.id,
        name=user.name,
    )


async def login_user(db: AsyncSession, body: LoginRequest) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.hashed_password):
        raise ValueError("Invalid credentials")
    if not user.is_active:
        raise ValueError("Account disabled")
    if body.device_id and body.public_key:
        device = await db.get(Device, body.device_id)
        if device:
            device.public_key = body.public_key
            device.user_id = user.id
            device.platform = body.platform
            device.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(
                Device(
                    id=body.device_id,
                    user_id=user.id,
                    public_key=body.public_key,
                    platform=body.platform,
                    last_seen_at=datetime.now(timezone.utc),
                )
            )
        await db.commit()
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
        role=user.role,
        user_id=user.id,
        name=user.name,
    )
