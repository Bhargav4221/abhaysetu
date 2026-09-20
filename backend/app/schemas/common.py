from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from abhaysetu_protocol.enums import EmergencyCategory, Priority
from abhaysetu_protocol.messages import LocationFix, SosPayload


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    name: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str
    role: str = "CITIZEN"
    language: str = "en"
    device_id: Optional[str] = None
    public_key: Optional[str] = None
    platform: str = "web"


class LoginRequest(BaseModel):
    email: str
    password: str
    device_id: Optional[str] = None
    public_key: Optional[str] = None
    platform: str = "web"


class SosCreateRequest(BaseModel):
    payload: SosPayload
    digital_signature: str
    current_channel: Optional[str] = None
    hop_count: int = 0
    ttl: int = 8
    relay_path: list[str] = Field(default_factory=list)
    received_via: str = "internet"
    idempotency_key: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    lifecycle: str
    note: str = ""


class AssignRequest(BaseModel):
    responder_id: str
    note: str = ""


class ResourceCreate(BaseModel):
    type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    availability: str = "AVAILABLE"
    capacity: Optional[int] = None
    owner: str = ""
    contact: str = ""


class ShelterCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    capacity: int = 0
    occupied: int = 0
    facilities: list[str] = Field(default_factory=list)
    accessibility: bool = False
    medical_support: bool = False
    contact: str = ""


class SyncItem(BaseModel):
    idempotency_key: str
    entity_type: str
    entity_id: str
    operation: str
    payload: dict
    version: int = 1
    updated_at: datetime


class SyncRequest(BaseModel):
    hub_id: str
    items: list[SyncItem]


class RelayIngestRequest(BaseModel):
    envelope: dict
    node_id: str
