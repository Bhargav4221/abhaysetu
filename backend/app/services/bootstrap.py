from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal
from abhaysetu_protocol.ids import generate_event_id


async def bootstrap() -> None:
    settings = get_settings()
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == settings.bootstrap_admin_email.lower()))
        if existing:
            return
        db.add(
            User(
                id=generate_event_id(),
                email=settings.bootstrap_admin_email.lower(),
                name=settings.bootstrap_admin_name,
                hashed_password=hash_password(settings.bootstrap_admin_password),
                role="ADMIN",
            )
        )
        await db.commit()
