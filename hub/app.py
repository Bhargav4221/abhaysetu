from __future__ import annotations

import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from abhaysetu_protocol.comms import apply_relay_rules
from abhaysetu_protocol.crypto import hash_payload, verify_signature
from abhaysetu_protocol.enums import HONEST_DELIVERY_MESSAGES, SosLifecycle
from abhaysetu_protocol.ids import generate_event_id
from abhaysetu_protocol.messages import RelayEnvelope, SosPayload

HUB_ID = os.getenv("HUB_ID", "hub-local-001")
HUB_NAME = os.getenv("HUB_NAME", "Local Emergency Hub")
DB_PATH = os.getenv("HUB_SQLITE_PATH", "./data/hub.sqlite3")
CLOUD_URL = os.getenv("CLOUD_SYNC_URL", "http://localhost:8000")
SYNC_TOKEN = os.getenv("HUB_SYNC_TOKEN", "")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


class HubSos(Base):
    __tablename__ = "hub_sos"
    sos_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(Text)
    lifecycle: Mapped[str] = mapped_column(String(40), default="DELIVERED_TO_HUB")
    synced: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    hop_count: Mapped[int] = mapped_column(Integer, default=0)
    honest_status_message: Mapped[str] = mapped_column(Text, default="")


class HubEvent(Base):
    __tablename__ = "hub_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sos_id: Mapped[str] = mapped_column(String(40), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class HubResource(Base):
    __tablename__ = "hub_resources"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200), default="")
    availability: Mapped[str] = mapped_column(String(32), default="AVAILABLE")
    extra: Mapped[dict] = mapped_column(JSON, default=dict)


engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

clients: set[WebSocket] = set()


async def broadcast(event: dict) -> None:
    dead = []
    for ws in list(clients):
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)


class SosIn(BaseModel):
    payload: SosPayload
    digital_signature: str
    hop_count: int = 0
    ttl: int = 8
    relay_path: list[str] = []
    received_via: str = "local_network"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="AbhaySetu Local Emergency Hub", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "hub_id": HUB_ID, "name": HUB_NAME, "mode": "LOCAL_EMERGENCY_NETWORK"}


@app.post("/api/sos")
async def receive_sos(body: SosIn):
    if not verify_signature(body.payload.signing_dict(), body.digital_signature, body.payload.origin_public_key):
        raise HTTPException(status_code=400, detail="Invalid signature")
    with SessionLocal() as db:
        existing = db.get(HubSos, body.payload.sos_id)
        if existing:
            return {
                "acknowledged": True,
                "duplicate": True,
                "honest_status_message": existing.honest_status_message,
                "sos_id": existing.sos_id,
            }
        msg = HONEST_DELIVERY_MESSAGES["hub_ack"]
        row = HubSos(
            sos_id=body.payload.sos_id,
            payload=body.payload.model_dump(mode="json"),
            signature=body.digital_signature,
            hop_count=body.hop_count,
            honest_status_message=msg,
        )
        db.add(row)
        db.add(HubEvent(id=generate_event_id(), sos_id=row.sos_id, event_type="HUB_RECEIVED", payload={"via": body.received_via}))
        db.commit()
    await broadcast({"type": "sos.created", "sos_id": body.payload.sos_id})
    return {
        "acknowledged": True,
        "honest_status_message": msg,
        "sos_id": body.payload.sos_id,
        "lifecycle": SosLifecycle.DELIVERED_TO_HUB.value,
    }


@app.get("/api/sos")
def list_sos():
    with SessionLocal() as db:
        rows = db.scalars(select(HubSos).order_by(HubSos.created_at.desc())).all()
        return {
            "items": [
                {
                    "sos_id": r.sos_id,
                    "payload": r.payload,
                    "lifecycle": r.lifecycle,
                    "synced": r.synced,
                    "honest_status_message": r.honest_status_message,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        }


@app.post("/api/sos/{sos_id}/acknowledge")
async def ack(sos_id: str):
    with SessionLocal() as db:
        row = db.get(HubSos, sos_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        row.lifecycle = SosLifecycle.DISPATCHER_ACKNOWLEDGED.value
        db.add(HubEvent(id=generate_event_id(), sos_id=sos_id, event_type="DISPATCHER_ACKNOWLEDGED", payload={}))
        db.commit()
    await broadcast({"type": "sos.ack", "sos_id": sos_id})
    return {"ok": True, "lifecycle": SosLifecycle.DISPATCHER_ACKNOWLEDGED.value}


@app.post("/api/relay")
async def relay(envelope: dict, node_id: str = HUB_ID):
    env = RelayEnvelope.model_validate(envelope)
    if not verify_signature(env.payload.signing_dict(), env.digital_signature, env.origin_public_key):
        raise HTTPException(status_code=400, detail="Invalid signature")
    with SessionLocal() as db:
        seen = {r.sos_id for r in db.scalars(select(HubSos)).all()}
    outcome, forwarded = apply_relay_rules(env, node_id, seen)
    if forwarded is None and outcome.value != "DUPLICATE":
        raise HTTPException(status_code=400, detail=outcome.value)
    body = SosIn(
        payload=env.payload,
        digital_signature=env.digital_signature,
        hop_count=env.hop_count,
        ttl=env.ttl,
        relay_path=env.relay_path,
        received_via="peer_relay",
    )
    result = await receive_sos(body)
    result["relay_outcome"] = outcome.value
    return result


@app.post("/api/sync")
async def sync_to_cloud():
    """Push unsynced SOS records to the cloud backend when internet is available."""
    headers = {"Authorization": f"Bearer {SYNC_TOKEN}"} if SYNC_TOKEN else {}
    with SessionLocal() as db:
        pending = db.scalars(select(HubSos).where(HubSos.synced.is_(False))).all()
        items = []
        for row in pending:
            items.append(
                {
                    "idempotency_key": f"hub:{HUB_ID}:{row.sos_id}",
                    "entity_type": "sos_alerts",
                    "entity_id": row.sos_id,
                    "operation": "UPSERT",
                    "payload": {
                        "payload": row.payload,
                        "digital_signature": row.signature,
                        "received_via": "local_network",
                        "current_channel": "local_network",
                    },
                    "version": 1,
                    "updated_at": row.created_at.isoformat(),
                }
            )
    if not items:
        return {"synced": 0, "cloud_reachable": True, "detail": "Nothing pending"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{CLOUD_URL.rstrip('/')}/api/v1/sync",
                json={"hub_id": HUB_ID, "items": items},
                headers=headers,
            )
        if response.status_code >= 400:
            return {"synced": 0, "cloud_reachable": True, "detail": f"Cloud rejected sync: HTTP {response.status_code}"}
        with SessionLocal() as db:
            for row in db.scalars(select(HubSos).where(HubSos.synced.is_(False))).all():
                row.synced = True
            db.commit()
        return {"synced": len(items), "cloud_reachable": True, "result": response.json()}
    except httpx.HTTPError as exc:
        return {
            "synced": 0,
            "cloud_reachable": False,
            "detail": f"Cloud unreachable. Local hub continues independently. {exc}",
        }


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)


@app.get("/")
def root():
    return {
        "product": "AbhaySetu Local Emergency Hub",
        "hub_id": HUB_ID,
        "name": HUB_NAME,
        "note": "This hub stores SOS locally and syncs to the cloud only after the cloud acknowledges.",
    }
