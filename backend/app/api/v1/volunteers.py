from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import STAFF_ROLES, get_current_user, get_db, require_roles
from app.db.models import User, Volunteer

router = APIRouter(tags=["volunteers"])


@router.get("/volunteers")
async def list_volunteers(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(*STAFF_ROLES))):
    rows = (await db.scalars(select(Volunteer))).all()
    items = []
    for v in rows:
        owner = await db.get(User, v.user_id)
        items.append(
            {
                "id": v.id,
                "name": owner.name if owner else None,
                "skills": v.skills,
                "languages": v.languages,
                "availability": v.availability,
                "status": v.status,
                "medical_training": v.medical_training,
                "rescue_skills": v.rescue_skills,
                "latitude": v.latitude,
                "longitude": v.longitude,
            }
        )
    return {"items": items}


@router.get("/volunteers/me")
async def my_volunteer(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    row = await db.scalar(select(Volunteer).where(Volunteer.user_id == user.id))
    if not row:
        raise HTTPException(status_code=404, detail="No volunteer profile")
    return {
        "id": row.id,
        "skills": row.skills,
        "status": row.status,
        "availability": row.availability,
    }
