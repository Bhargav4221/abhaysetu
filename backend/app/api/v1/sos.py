from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from abhaysetu_protocol.comms import apply_relay_rules
from abhaysetu_protocol.crypto import verify_signature
from abhaysetu_protocol.messages import RelayEnvelope

from app.api.deps import DISPATCH_ROLES, STAFF_ROLES, get_current_user, get_db, optional_user, require_roles
from app.db.models import RelayNode, SosAlert, User
from app.schemas.common import AssignRequest, RelayIngestRequest, SosCreateRequest, StatusUpdateRequest
from app.services.sos_service import (
    assign_responder,
    get_sos,
    ingest_sos,
    list_events,
    serialize_sos,
    update_lifecycle,
)
from abhaysetu_protocol.ids import generate_event_id

router = APIRouter(tags=["sos"])


@router.post("/sos")
async def create_sos(
    body: SosCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(optional_user),
):
    try:
        alert = await ingest_sos(db, body, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    events = await list_events(db, alert.sos_id)
    return {
        "acknowledged": True,
        "acknowledgement_status": alert.acknowledgement_status,
        "honest_status_message": alert.honest_status_message,
        "sos": serialize_sos(alert, events, approximate=False),
    }


@router.get("/sos/{sos_id}")
async def read_sos(
    sos_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    alert = await get_sos(db, sos_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS not found")
    staff = user.role in STAFF_ROLES
    owner = alert.user_id == user.id
    if not staff and not owner:
        raise HTTPException(status_code=403, detail="Not authorized")
    events = await list_events(db, sos_id)
    return serialize_sos(alert, events, approximate=not staff and not owner)


@router.patch("/sos/{sos_id}/status")
async def patch_status(
    sos_id: str,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    alert = await get_sos(db, sos_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS not found")
    alert = await update_lifecycle(db, alert, body.lifecycle, user, body.note)
    events = await list_events(db, sos_id)
    return serialize_sos(alert, events)


@router.post("/sos/{sos_id}/acknowledge")
async def acknowledge(
    sos_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*DISPATCH_ROLES)),
):
    alert = await get_sos(db, sos_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS not found")
    alert = await update_lifecycle(db, alert, "DISPATCHER_ACKNOWLEDGED", user, "Dispatcher acknowledged")
    events = await list_events(db, sos_id)
    return serialize_sos(alert, events)


@router.post("/sos/{sos_id}/assign")
async def assign(
    sos_id: str,
    body: AssignRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*DISPATCH_ROLES)),
):
    alert = await get_sos(db, sos_id)
    if not alert:
        raise HTTPException(status_code=404, detail="SOS not found")
    try:
        alert = await assign_responder(db, alert, body.responder_id, user, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    events = await list_events(db, sos_id)
    return serialize_sos(alert, events)


@router.get("/incidents")
async def list_incidents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    rows = (await db.scalars(select(SosAlert).order_by(SosAlert.created_at.desc()).limit(200))).all()
    out = []
    for alert in rows:
        events = await list_events(db, alert.sos_id)
        out.append(serialize_sos(alert, events))
    return {"items": out}


@router.post("/relay")
async def ingest_relay(
    body: RelayIngestRequest,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(optional_user),
):
    envelope = RelayEnvelope.model_validate(body.envelope)
    if not verify_signature(envelope.payload.signing_dict(), envelope.digital_signature, envelope.origin_public_key):
        raise HTTPException(status_code=400, detail="Invalid signature")
    seen = set(
        (
            await db.scalars(select(RelayNode.node_id).where(RelayNode.sos_id == envelope.sos_id))
        ).all()
    )
    outcome, forwarded = apply_relay_rules(envelope, body.node_id, seen)
    if outcome.value in {"EXPIRED", "TTL_EXHAUSTED", "INVALID_SIGNATURE", "REJECTED"}:
        raise HTTPException(status_code=400, detail=outcome.value)
    req = SosCreateRequest(
        payload=envelope.payload,
        digital_signature=envelope.digital_signature,
        current_channel="peer_relay",
        hop_count=envelope.hop_count,
        ttl=envelope.ttl,
        relay_path=envelope.relay_path + [body.node_id],
        received_via="peer_relay",
    )
    alert = await ingest_sos(db, req, user)
    db.add(
        RelayNode(
            id=generate_event_id(),
            sos_id=alert.sos_id,
            node_id=body.node_id,
            hop_count=envelope.hop_count + 1,
            outcome=outcome.value,
        )
    )
    await db.commit()
    return {"outcome": outcome.value, "sos_id": alert.sos_id, "acknowledged": True}
