from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.db.models import SosAlert, SyncQueueItem, User
from app.schemas.common import SosCreateRequest, SyncRequest
from app.services.sos_service import ingest_sos, serialize_sos

router = APIRouter(tags=["sync"])


@router.post("/sync")
async def sync_from_hub(body: SyncRequest, db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("DISPATCHER", "ADMIN", "ORGANIZATION"))):
    results = []
    for item in body.items:
        existing = await db.scalar(select(SyncQueueItem).where(SyncQueueItem.idempotency_key == item.idempotency_key))
        if existing:
            results.append({"idempotency_key": item.idempotency_key, "status": "duplicate_ignored"})
            continue
        db.add(
            SyncQueueItem(
                id=item.idempotency_key[:40],
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                operation=item.operation,
                payload=item.payload,
                version=item.version,
                status="APPLIED",
                idempotency_key=item.idempotency_key,
            )
        )
        if item.entity_type == "sos_alerts" and item.operation in {"CREATE", "UPSERT"}:
            try:
                req = SosCreateRequest.model_validate(item.payload)
                req.received_via = "local_network"
                alert = await ingest_sos(db, req, user)
                results.append({"idempotency_key": item.idempotency_key, "status": "ingested", "sos_id": alert.sos_id})
            except Exception as exc:  # noqa: BLE001
                results.append({"idempotency_key": item.idempotency_key, "status": "error", "detail": str(exc)})
        else:
            results.append({"idempotency_key": item.idempotency_key, "status": "recorded"})
    await db.commit()
    return {"hub_id": body.hub_id, "results": results}


@router.get("/connectivity")
async def connectivity():
    return {
        "backend": "ok",
        "mode": "ONLINE",
        "message": "AbhaySetu emergency server is reachable.",
    }
