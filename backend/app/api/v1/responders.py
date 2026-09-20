from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import STAFF_ROLES, get_db, require_roles
from app.db.models import Responder, User

router = APIRouter(tags=["responders"])


@router.get("/responders")
async def list_responders(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(*STAFF_ROLES))):
    rows = (await db.scalars(select(Responder))).all()
    items = []
    for r in rows:
        owner = await db.get(User, r.user_id)
        items.append(
            {
                "id": r.id,
                "name": owner.name if owner else None,
                "status": r.status,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "skills": r.skills,
            }
        )
    return {"items": items}
