from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reputation_score: Mapped[float] = mapped_column(Float, default=1.0)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)


class Device(Base, TimestampMixin):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    public_key: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(32), default="unknown")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    org_type: Mapped[str] = mapped_column(String(64), default="relief")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)


class SosAlert(Base, TimestampMixin):
    __tablename__ = "sos_alerts"

    sos_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canonical_id: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_id: Mapped[str] = mapped_column(String(40), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_source: Mapped[str] = mapped_column(String(32), default="unknown")
    emergency_type: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(16), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    people_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    injured_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    children_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elderly_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    special_requirements: Mapped[str] = mapped_column(Text, default="")
    accessibility_requirements: Mapped[str] = mapped_column(Text, default="")
    medicine_requirements: Mapped[str] = mapped_column(Text, default="")
    voice_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    lifecycle: Mapped[str] = mapped_column(String(40), index=True)
    communication_status: Mapped[str] = mapped_column(String(40))
    current_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hop_count: Mapped[int] = mapped_column(Integer, default=0)
    ttl: Mapped[int] = mapped_column(Integer, default=8)
    message_hash: Mapped[str] = mapped_column(String(64), index=True)
    digital_signature: Mapped[str] = mapped_column(Text)
    origin_public_key: Mapped[str] = mapped_column(Text)
    acknowledgement_status: Mapped[str] = mapped_column(String(32), default="NONE")
    dispatcher_status: Mapped[str] = mapped_column(String(32), default="NONE")
    responder_status: Mapped[str] = mapped_column(String(32), default="NONE")
    resolution_status: Mapped[str] = mapped_column(String(32), default="OPEN")
    honest_status_message: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    received_via: Mapped[str] = mapped_column(String(32), default="internet")
    sequence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    events: Mapped[list["SosEvent"]] = relationship(back_populates="sos")


class SosEvent(Base):
    __tablename__ = "sos_events"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sos_id: Mapped[str] = mapped_column(ForeignKey("sos_alerts.sos_id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    immutable: Mapped[bool] = mapped_column(Boolean, default=True)

    sos: Mapped[SosAlert] = relationship(back_populates="events")


class CommunicationAttempt(Base):
    __tablename__ = "communication_attempts"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sos_id: Mapped[str] = mapped_column(ForeignKey("sos_alerts.sos_id"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledgement: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[str] = mapped_column(Text, default="")


class RelayNode(Base, TimestampMixin):
    __tablename__ = "relay_nodes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sos_id: Mapped[str] = mapped_column(ForeignKey("sos_alerts.sos_id"), index=True)
    node_id: Mapped[str] = mapped_column(String(40), index=True)
    hop_count: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(32))


class SyncQueueItem(Base, TimestampMixin):
    __tablename__ = "sync_queue"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    operation: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sos_id: Mapped[str] = mapped_column(ForeignKey("sos_alerts.sos_id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    assigned_responder_id: Mapped[str | None] = mapped_column(ForeignKey("responders.id"), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(40), nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Responder(Base, TimestampMixin):
    __tablename__ = "responders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE", index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)


class Volunteer(Base, TimestampMixin):
    __tablename__ = "volunteers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    medical_training: Mapped[bool] = mapped_column(Boolean, default=False)
    rescue_skills: Mapped[bool] = mapped_column(Boolean, default=False)
    transport: Mapped[str] = mapped_column(String(64), default="")
    availability: Mapped[str] = mapped_column(String(32), default="UNKNOWN")
    status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability: Mapped[str] = mapped_column(String(32), default="AVAILABLE")
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner: Mapped[str] = mapped_column(String(200), default="")
    contact: Mapped[str] = mapped_column(String(200), default="")
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResourceAssignment(Base, TimestampMixin):
    __tablename__ = "resource_assignments"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("resources.id"))
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"))
    assigned_by: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Shelter(Base, TimestampMixin):
    __tablename__ = "shelters"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    occupied: Mapped[int] = mapped_column(Integer, default=0)
    facilities: Mapped[list] = mapped_column(JSON, default=list)
    accessibility: Mapped[bool] = mapped_column(Boolean, default=False)
    medical_support: Mapped[bool] = mapped_column(Boolean, default=False)
    contact: Mapped[str] = mapped_column(String(200), default="")
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MedicalCenter(Base, TimestampMixin):
    __tablename__ = "medical_centers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    services: Mapped[list] = mapped_column(JSON, default=list)
    contact: Mapped[str] = mapped_column(String(200), default="")
    verification_status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED")


class MapRegion(Base, TimestampMixin):
    __tablename__ = "map_regions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    geojson: Mapped[dict] = mapped_column(JSON, default=dict)
    data_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DangerZone(Base, TimestampMixin):
    __tablename__ = "danger_zones"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    zone_type: Mapped[str] = mapped_column(String(40))
    geojson: Mapped[dict] = mapped_column(JSON, default=dict)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BlockedRoad(Base, TimestampMixin):
    __tablename__ = "blocked_roads"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text, default="")
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    sos_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class AiAnalysis(Base, TimestampMixin):
    __tablename__ = "ai_analysis"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    sos_id: Mapped[str] = mapped_column(ForeignKey("sos_alerts.sos_id"), index=True)
    mode: Mapped[str] = mapped_column(String(24))
    suggestion: Mapped[dict] = mapped_column(JSON)
    override_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    label: Mapped[str] = mapped_column(String(64), default="AI-assisted suggestion")


class SosSequence(Base):
    __tablename__ = "sos_sequences"
    __table_args__ = (UniqueConstraint("year"),)

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)
