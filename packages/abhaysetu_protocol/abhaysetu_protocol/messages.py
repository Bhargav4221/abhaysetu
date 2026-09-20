from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .crypto import hash_payload, utcnow
from .enums import (
    AcknowledgementStatus,
    ChannelId,
    CommunicationMode,
    DeliveryState,
    EmergencyCategory,
    Priority,
    SosLifecycle,
)
from .ids import generate_sos_id


class LocationFix(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    captured_at: Optional[datetime] = None
    source: Literal["gps", "network", "manual", "unknown", "unavailable"] = "unknown"


class SosPayload(BaseModel):
    sos_id: str = Field(default_factory=generate_sos_id)
    user_id: Optional[str] = None
    device_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    location: LocationFix = Field(default_factory=LocationFix)
    emergency_type: EmergencyCategory = EmergencyCategory.OTHER
    priority: Priority = Priority.HIGH
    description: str = ""
    people_count: Optional[int] = None
    injured_count: Optional[int] = None
    children_count: Optional[int] = None
    elderly_count: Optional[int] = None
    special_requirements: str = ""
    accessibility_requirements: str = ""
    medicine_requirements: str = ""
    language: str = "en"
    origin_public_key: str
    schema_version: int = 1

    def signing_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RelayEnvelope(BaseModel):
    sos_id: str
    origin_device_id: str
    timestamp: datetime
    hop_count: int = 0
    ttl: int = 8
    message_hash: str
    digital_signature: str
    origin_public_key: str
    payload: SosPayload
    delivery_state: DeliveryState = DeliveryState.QUEUED_LOCALLY
    relay_path: list[str] = Field(default_factory=list)

    @field_validator("ttl")
    @classmethod
    def ttl_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("ttl cannot be negative")
        return value


class TimelineInstant(BaseModel):
    sos_created_at: Optional[datetime] = None
    gps_captured_at: Optional[datetime] = None
    transmission_started_at: Optional[datetime] = None
    relayed_at: Optional[datetime] = None
    hub_received_at: Optional[datetime] = None
    dispatcher_ack_at: Optional[datetime] = None
    responder_assigned_at: Optional[datetime] = None
    responder_en_route_at: Optional[datetime] = None
    responding_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class DurationMetrics(BaseModel):
    """Measured system timings in seconds. These are not promised SLA values."""

    time_to_hub_seconds: Optional[float] = None
    time_to_dispatcher_seconds: Optional[float] = None
    time_to_assignment_seconds: Optional[float] = None
    time_to_response_seconds: Optional[float] = None
    total_resolution_seconds: Optional[float] = None
    time_to_dispatch_seconds: Optional[float] = None


class SosRecord(BaseModel):
    payload: SosPayload
    lifecycle: SosLifecycle = SosLifecycle.CREATED
    communication_status: CommunicationMode = CommunicationMode.COMPLETELY_OFFLINE
    current_channel: Optional[ChannelId] = None
    hop_count: int = 0
    ttl: int = 8
    message_hash: str = ""
    digital_signature: str = ""
    acknowledgement_status: AcknowledgementStatus = AcknowledgementStatus.NONE
    dispatcher_status: str = "NONE"
    responder_status: str = "NONE"
    resolution_status: str = "OPEN"
    delivery_state: DeliveryState = DeliveryState.NOT_ATTEMPTED
    honest_status_message: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    last_updated: datetime = Field(default_factory=utcnow)
    timeline: TimelineInstant = Field(default_factory=TimelineInstant)
    metrics: DurationMetrics = Field(default_factory=DurationMetrics)
    version: int = 1

    def ensure_hash(self) -> None:
        if not self.message_hash:
            self.message_hash = hash_payload(self.payload.signing_dict())


def compute_metrics(timeline: TimelineInstant) -> DurationMetrics:
    def delta(end: datetime | None, start: datetime | None) -> float | None:
        if end is None or start is None:
            return None
        return (end - start).total_seconds()

    created = timeline.sos_created_at
    return DurationMetrics(
        time_to_hub_seconds=delta(timeline.hub_received_at, created),
        time_to_dispatcher_seconds=delta(timeline.dispatcher_ack_at, created),
        time_to_assignment_seconds=delta(timeline.responder_assigned_at, created),
        time_to_response_seconds=delta(timeline.responding_at, created),
        total_resolution_seconds=delta(timeline.resolved_at, created),
        time_to_dispatch_seconds=delta(timeline.responder_assigned_at, timeline.dispatcher_ack_at),
    )
