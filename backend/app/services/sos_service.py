from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from abhaysetu_protocol.ai_local import classify_text
from abhaysetu_protocol.crypto import hash_payload, verify_signature
from abhaysetu_protocol.enums import AcknowledgementStatus, HONEST_DELIVERY_MESSAGES, SosLifecycle
from abhaysetu_protocol.ids import generate_canonical_sequence_id, generate_event_id
from abhaysetu_protocol.messages import compute_metrics, TimelineInstant

from app.core.config import get_settings
from app.core.redis import incr_with_ttl
from app.db.models import (
    AiAnalysis,
    AuditLog,
    CommunicationAttempt,
    Incident,
    Notification,
    RelayNode,
    SosAlert,
    SosEvent,
    SosSequence,
    User,
)
from app.schemas.common import SosCreateRequest
from app.ws.hub import ws_hub


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def next_canonical_id(db: AsyncSession, year: int) -> tuple[str, int]:
    seq = await db.get(SosSequence, year)
    if seq is None:
        seq = SosSequence(year=year, last_value=0)
        db.add(seq)
        await db.flush()
    seq.last_value += 1
    return generate_canonical_sequence_id(year, seq.last_value), seq.last_value


async def append_event(
    db: AsyncSession,
    sos_id: str,
    event_type: str,
    actor_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> SosEvent:
    event = SosEvent(
        id=generate_event_id(),
        sos_id=sos_id,
        event_type=event_type,
        actor_id=actor_id,
        payload=payload or {},
        created_at=_now(),
    )
    db.add(event)
    return event


async def audit(db: AsyncSession, actor_id: str | None, action: str, entity_type: str, entity_id: str, detail: dict) -> None:
    db.add(
        AuditLog(
            id=generate_event_id(),
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
        )
    )


async def notify(db: AsyncSession, user_id: str | None, event_type: str, title: str, body: str, sos_id: str | None) -> None:
    db.add(
        Notification(
            id=generate_event_id(),
            user_id=user_id,
            event_type=event_type,
            title=title,
            body=body,
            sos_id=sos_id,
        )
    )


async def ingest_sos(db: AsyncSession, body: SosCreateRequest, actor: User | None) -> SosAlert:
    settings = get_settings()
    payload = body.payload
    signing_dict = payload.signing_dict()
    digest = hash_payload(signing_dict)
    signature_ok = verify_signature(signing_dict, body.digital_signature, payload.origin_public_key)
    if not signature_ok:
        raise ValueError("Invalid message signature")

    device_key = f"sos:rate:{payload.device_id}"
    count = await incr_with_ttl(device_key, 3600)
    if count and count > settings.sos_rate_limit_per_device_per_hour:
        raise PermissionError("Device SOS rate limit exceeded")

    existing = await db.get(SosAlert, payload.sos_id)
    if existing:
        await append_event(db, existing.sos_id, "DUPLICATE_INGEST", actor.id if actor else None, {"via": body.received_via})
        await db.commit()
        return existing

    canonical_id, seq = await next_canonical_id(db, payload.timestamp.year)
    now = _now()
    alert = SosAlert(
        sos_id=payload.sos_id,
        canonical_id=canonical_id,
        sequence_number=seq,
        user_id=payload.user_id or (actor.id if actor else None),
        device_id=payload.device_id,
        timestamp=payload.timestamp,
        latitude=payload.location.latitude,
        longitude=payload.location.longitude,
        location_accuracy=payload.location.accuracy_meters,
        location_source=payload.location.source,
        emergency_type=payload.emergency_type.value,
        priority=payload.priority.value,
        description=payload.description,
        people_count=payload.people_count,
        injured_count=payload.injured_count,
        children_count=payload.children_count,
        elderly_count=payload.elderly_count,
        special_requirements=payload.special_requirements,
        accessibility_requirements=payload.accessibility_requirements,
        medicine_requirements=payload.medicine_requirements,
        lifecycle=SosLifecycle.DELIVERED_TO_HUB.value,
        communication_status="ONLINE" if body.received_via == "internet" else body.received_via.upper(),
        current_channel=body.current_channel,
        hop_count=body.hop_count,
        ttl=body.ttl,
        message_hash=digest,
        digital_signature=body.digital_signature,
        origin_public_key=payload.origin_public_key,
        acknowledgement_status=AcknowledgementStatus.SERVER_ACK.value
        if body.received_via == "internet"
        else AcknowledgementStatus.HUB_ACK.value,
        honest_status_message=HONEST_DELIVERY_MESSAGES["server_ack"]
        if body.received_via == "internet"
        else HONEST_DELIVERY_MESSAGES["hub_ack"],
        received_via=body.received_via,
    )
    db.add(alert)
    incident = Incident(id=f"INC-{secrets.token_hex(6).upper()}", sos_id=alert.sos_id, status="OPEN")
    db.add(incident)
    db.add(
        CommunicationAttempt(
            id=generate_event_id(),
            sos_id=alert.sos_id,
            channel=body.received_via,
            finished_at=now,
            success=True,
            acknowledgement=True,
            detail="Accepted by AbhaySetu backend",
        )
    )
    for hop, node in enumerate(body.relay_path):
        db.add(RelayNode(id=generate_event_id(), sos_id=alert.sos_id, node_id=node, hop_count=hop + 1, outcome="FORWARDED"))

    await append_event(db, alert.sos_id, "SOS_CREATED", alert.user_id, {"timestamp": payload.timestamp.isoformat()})
    if payload.location.latitude is not None:
        await append_event(db, alert.sos_id, "GPS_CAPTURED", None, {"accuracy": payload.location.accuracy_meters})
    await append_event(db, alert.sos_id, "HUB_RECEIVED", None, {"via": body.received_via, "canonical_id": canonical_id})

    category, priority, reason = classify_text(payload.description)
    db.add(
        AiAnalysis(
            id=generate_event_id(),
            sos_id=alert.sos_id,
            mode="LOCAL_RULES",
            suggestion={
                "category": category.value,
                "priority": priority.value,
                "reason": reason,
                "label": "AI-assisted suggestion",
            },
        )
    )

    await audit(db, actor.id if actor else None, "SOS_INGEST", "sos_alerts", alert.sos_id, {"via": body.received_via})
    await notify(
        db,
        alert.user_id,
        "SOS_DELIVERED",
        "SOS delivered",
        alert.honest_status_message,
        alert.sos_id,
    )
    await db.commit()
    await db.refresh(alert)
    await ws_hub.broadcast({"type": "sos.created", "sos_id": alert.sos_id, "priority": alert.priority})
    return alert


async def get_sos(db: AsyncSession, sos_id: str) -> SosAlert | None:
    return await db.get(SosAlert, sos_id)


async def list_events(db: AsyncSession, sos_id: str) -> list[SosEvent]:
    result = await db.scalars(select(SosEvent).where(SosEvent.sos_id == sos_id).order_by(SosEvent.created_at))
    return list(result)


async def update_lifecycle(
    db: AsyncSession,
    alert: SosAlert,
    lifecycle: str,
    actor: User,
    note: str = "",
) -> SosAlert:
    previous = alert.lifecycle
    alert.lifecycle = lifecycle
    alert.version += 1
    alert.updated_at = _now()
    mapping = {
        SosLifecycle.DISPATCHER_ACKNOWLEDGED.value: ("DISPATCHER_ACKNOWLEDGED", "dispatcher_status"),
        SosLifecycle.RESPONDER_ASSIGNED.value: ("RESPONDER_ASSIGNED", "responder_status"),
        SosLifecycle.RESPONDER_EN_ROUTE.value: ("RESPONDER_EN_ROUTE", "responder_status"),
        SosLifecycle.RESPONDING.value: ("RESPONDING", "responder_status"),
        SosLifecycle.RESOLVED.value: ("RESOLVED", "resolution_status"),
        SosLifecycle.CANCELLED.value: ("CANCELLED", "resolution_status"),
    }
    if lifecycle in mapping:
        event_name, field = mapping[lifecycle]
        setattr(alert, field, lifecycle)
        if lifecycle == SosLifecycle.DISPATCHER_ACKNOWLEDGED.value:
            alert.acknowledgement_status = AcknowledgementStatus.DISPATCHER_ACK.value
            incident = await db.scalar(select(Incident).where(Incident.sos_id == alert.sos_id))
            if incident:
                incident.status = "ACKNOWLEDGED"
                incident.acknowledged_by = actor.id
    await append_event(db, alert.sos_id, lifecycle, actor.id, {"from": previous, "note": note})
    await audit(db, actor.id, "STATUS_CHANGE", "sos_alerts", alert.sos_id, {"from": previous, "to": lifecycle})
    await notify(db, alert.user_id, lifecycle, "SOS update", f"Status is now {lifecycle}.", alert.sos_id)
    await db.commit()
    await db.refresh(alert)
    await ws_hub.broadcast({"type": "sos.status", "sos_id": alert.sos_id, "lifecycle": lifecycle})
    return alert


async def assign_responder(db: AsyncSession, alert: SosAlert, responder_id: str, actor: User, note: str) -> SosAlert:
    from app.db.models import Responder

    responder = await db.get(Responder, responder_id)
    if responder is None:
        raise ValueError("Responder not found")
    incident = await db.scalar(select(Incident).where(Incident.sos_id == alert.sos_id))
    if incident:
        incident.assigned_responder_id = responder_id
        incident.status = "ASSIGNED"
    responder.status = "ASSIGNED"
    alert.lifecycle = SosLifecycle.RESPONDER_ASSIGNED.value
    alert.responder_status = "ASSIGNED"
    alert.version += 1
    await append_event(db, alert.sos_id, "RESPONDER_ASSIGNED", actor.id, {"responder_id": responder_id, "note": note})
    await db.commit()
    await ws_hub.broadcast({"type": "sos.assigned", "sos_id": alert.sos_id, "responder_id": responder_id})
    return alert


def serialize_sos(alert: SosAlert, events: list[SosEvent] | None = None, approximate: bool = False) -> dict[str, Any]:
    lat, lon = alert.latitude, alert.longitude
    if approximate and lat is not None and lon is not None:
        lat = round(lat, 2)
        lon = round(lon, 2)
    timeline = TimelineInstant(
        sos_created_at=alert.timestamp,
        gps_captured_at=alert.timestamp if alert.latitude is not None else None,
        hub_received_at=alert.created_at,
    )
    for event in events or []:
        if event.event_type == "DISPATCHER_ACKNOWLEDGED":
            timeline.dispatcher_ack_at = event.created_at
        elif event.event_type == "RESPONDER_ASSIGNED":
            timeline.responder_assigned_at = event.created_at
        elif event.event_type == "RESPONDER_EN_ROUTE":
            timeline.responder_en_route_at = event.created_at
        elif event.event_type == "RESPONDING":
            timeline.responding_at = event.created_at
        elif event.event_type == "RESOLVED":
            timeline.resolved_at = event.created_at
        elif event.event_type == "HUB_RECEIVED":
            timeline.hub_received_at = event.created_at
    metrics = compute_metrics(timeline)
    return {
        "sos_id": alert.sos_id,
        "canonical_id": alert.canonical_id,
        "user_id": alert.user_id,
        "device_id": alert.device_id,
        "timestamp": alert.timestamp,
        "latitude": lat,
        "longitude": lon,
        "location_accuracy": None if approximate else alert.location_accuracy,
        "emergency_type": alert.emergency_type,
        "priority": alert.priority,
        "description": alert.description if not approximate else "",
        "people_count": alert.people_count,
        "injured_count": alert.injured_count,
        "special_requirements": alert.special_requirements if not approximate else "",
        "lifecycle": alert.lifecycle,
        "communication_status": alert.communication_status,
        "current_channel": alert.current_channel,
        "hop_count": alert.hop_count,
        "ttl": alert.ttl,
        "message_hash": alert.message_hash,
        "acknowledgement_status": alert.acknowledgement_status,
        "dispatcher_status": alert.dispatcher_status,
        "responder_status": alert.responder_status,
        "resolution_status": alert.resolution_status,
        "honest_status_message": alert.honest_status_message,
        "created_at": alert.created_at,
        "last_updated": alert.updated_at,
        "version": alert.version,
        "received_via": alert.received_via,
        "metrics": metrics.model_dump(),
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "created_at": e.created_at,
                "payload": e.payload,
                "actor_id": e.actor_id,
            }
            for e in (events or [])
        ],
    }


async def dashboard_metrics(db: AsyncSession) -> dict[str, Any]:
    active = await db.scalar(
        select(func.count()).select_from(SosAlert).where(SosAlert.lifecycle.notin_(["RESOLVED", "CANCELLED", "EXPIRED"]))
    )
    critical = await db.scalar(select(func.count()).select_from(SosAlert).where(SosAlert.priority == "CRITICAL"))
    unassigned = await db.scalar(
        select(func.count()).select_from(Incident).where(Incident.status == "OPEN")
    )
    responding = await db.scalar(select(func.count()).select_from(SosAlert).where(SosAlert.lifecycle == "RESPONDING"))
    resolved = await db.scalar(select(func.count()).select_from(SosAlert).where(SosAlert.lifecycle == "RESOLVED"))
    return {
        "active_emergencies": active or 0,
        "critical_emergencies": critical or 0,
        "unassigned_incidents": unassigned or 0,
        "responding": responding or 0,
        "resolved": resolved or 0,
        "average_response_time_seconds": None,
        "average_dispatch_time_seconds": None,
        "note": "Averages are measured from recorded events and are not promised response times.",
    }
