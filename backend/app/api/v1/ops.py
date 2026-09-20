from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import STAFF_ROLES, get_db, require_roles
from app.db.models import Resource, Shelter, User
from app.schemas.common import ResourceCreate, ShelterCreate
from app.services.sos_service import dashboard_metrics

router = APIRouter(tags=["ops"])


def _haversine(lat1, lon1, lat2, lon2) -> float | None:
    if None in (lat1, lon1, lat2, lon2):
        return None
    from math import atan2, cos, radians, sin, sqrt

    r = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(1 - a))


@router.get("/resources")
async def list_resources(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(*STAFF_ROLES, "CITIZEN", "VOLUNTEER"))):
    rows = (await db.scalars(select(Resource))).all()
    return {
        "items": [
            {
                "resource_id": r.id,
                "type": r.type,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "availability": r.availability,
                "capacity": r.capacity,
                "owner": r.owner if user.role in STAFF_ROLES else None,
                "contact": r.contact if user.role in STAFF_ROLES else None,
                "verification_status": r.verification_status,
                "last_updated": r.updated_at,
            }
            for r in rows
        ]
    }


@router.post("/resources")
async def create_resource(
    body: ResourceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    from abhaysetu_protocol.ids import generate_event_id

    resource = Resource(id=generate_event_id(), **body.model_dump())
    db.add(resource)
    await db.commit()
    return {"resource_id": resource.id}


@router.get("/shelters")
async def list_shelters(
    lat: float | None = None,
    lon: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.scalars(select(Shelter))).all()
    items = []
    for s in rows:
        items.append(
            {
                "shelter_id": s.id,
                "name": s.name,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "capacity": s.capacity,
                "occupied": s.occupied,
                "available_capacity": max(s.capacity - s.occupied, 0),
                "facilities": s.facilities,
                "accessibility": s.accessibility,
                "medical_support": s.medical_support,
                "contact": s.contact,
                "verification_status": s.verification_status,
                "last_updated": s.updated_at,
                "last_verified_at": s.last_verified_at,
                "distance_km": _haversine(lat, lon, s.latitude, s.longitude) if lat is not None else None,
            }
        )
    items.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0))
    return {"items": items}


@router.post("/shelters")
async def create_shelter(body: ShelterCreate, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(*STAFF_ROLES))):
    from abhaysetu_protocol.ids import generate_event_id

    shelter = Shelter(id=generate_event_id(), **body.model_dump())
    db.add(shelter)
    await db.commit()
    return {"shelter_id": shelter.id}


@router.get("/map")
async def crisis_map(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(*STAFF_ROLES, "CITIZEN", "VOLUNTEER"))):
    from app.core.config import get_settings
    from app.db.models import BlockedRoad, SosAlert

    settings = get_settings()
    alerts = (await db.scalars(select(SosAlert).where(SosAlert.lifecycle.notin_(["RESOLVED", "CANCELLED"])))).all()
    shelters = (await db.scalars(select(Shelter))).all()
    roads = (await db.scalars(select(BlockedRoad))).all()
    staff = user.role in STAFF_ROLES
    markers = []
    for a in alerts:
        lat, lon = a.latitude, a.longitude
        if lat is None:
            continue
        if not staff:
            lat, lon = round(lat, 2), round(lon, 2)
        markers.append(
            {
                "kind": "SOS" if a.priority != "CRITICAL" else "HIGH_PRIORITY",
                "id": a.sos_id,
                "latitude": lat,
                "longitude": lon,
                "emergency_type": a.emergency_type,
                "priority": a.priority,
                "status": a.lifecycle,
            }
        )
    for s in shelters:
        markers.append(
            {
                "kind": "SHELTER",
                "id": s.id,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "name": s.name,
                "available_capacity": max(s.capacity - s.occupied, 0),
                "verification_status": s.verification_status,
            }
        )
    for r in roads:
        markers.append(
            {
                "kind": "BLOCKED_ROAD",
                "id": r.id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "name": r.name,
                "last_verified_at": r.last_verified_at,
                "disclaimer": "Reported condition. Not a guarantee of safety.",
            }
        )
    return {
        "tile_url": settings.map_tile_url,
        "attribution": settings.map_attribution,
        "map_data_last_updated": settings.map_data_updated_at or datetime.now(timezone.utc).isoformat(),
        "route_disclaimer": "Routes are reported accessible only. Never treated as confirmed safe.",
        "markers": markers,
    }


@router.get("/dashboard/metrics")
async def metrics(db: AsyncSession = Depends(get_db), user: User = Depends(require_roles(*STAFF_ROLES))):
    return await dashboard_metrics(db)
