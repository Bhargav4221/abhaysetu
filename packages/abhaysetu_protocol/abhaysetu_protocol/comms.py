from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from .enums import ChannelId, CommunicationMode, DeliveryState, RelayOutcome
from .messages import RelayEnvelope, SosRecord
from .policy import CommunicationPolicy


@dataclass
class AdapterCapabilities:
    channel: ChannelId
    available: bool
    reason: str
    signal_quality: float | None = None
    latency_ms: float | None = None
    battery_cost: float = 0.3
    requires_hardware: bool = False
    requires_external_service: bool = False
    background_supported: bool = False


@dataclass
class SendResult:
    ok: bool
    channel: ChannelId
    delivery_state: DeliveryState
    acknowledgement: bool
    status_message: str
    detail: str = ""
    hop_count: int | None = None


@runtime_checkable
class CommunicationAdapter(Protocol):
    channel: ChannelId

    def capabilities(self) -> AdapterCapabilities: ...

    def send(self, envelope: RelayEnvelope) -> SendResult: ...


class CommunicationManager:
    """Selects the best *actually available* path. Never reports success without ack."""

    def __init__(self, adapters: list[CommunicationAdapter], policy: CommunicationPolicy | None = None):
        self.adapters = {adapter.channel: adapter for adapter in adapters}
        self.policy = policy or CommunicationPolicy()

    def snapshot(self) -> list[AdapterCapabilities]:
        return [self.adapters[channel].capabilities() for channel in self.policy.order if channel in self.adapters]

    def current_mode(self) -> CommunicationMode:
        caps = {cap.channel: cap for cap in self.snapshot()}
        if caps.get(ChannelId.INTERNET) and caps[ChannelId.INTERNET].available:
            return CommunicationMode.ONLINE
        if caps.get(ChannelId.LOCAL_NETWORK) and caps[ChannelId.LOCAL_NETWORK].available:
            return CommunicationMode.LOCAL_EMERGENCY_NETWORK
        if caps.get(ChannelId.PEER_RELAY) and caps[ChannelId.PEER_RELAY].available:
            return CommunicationMode.PEER_RELAY
        if caps.get(ChannelId.RADIO) and caps[ChannelId.RADIO].available:
            return CommunicationMode.RADIO
        if caps.get(ChannelId.SATELLITE) and caps[ChannelId.SATELLITE].available:
            return CommunicationMode.SATELLITE
        return CommunicationMode.COMPLETELY_OFFLINE

    def select_channel(self) -> ChannelId:
        for channel in self.policy.order:
            adapter = self.adapters.get(channel)
            if adapter is None:
                continue
            cap = adapter.capabilities()
            if cap.available and channel != ChannelId.STORE_AND_FORWARD:
                return channel
        return ChannelId.STORE_AND_FORWARD

    def transmit(self, envelope: RelayEnvelope) -> SendResult:
        channel = self.select_channel()
        adapter = self.adapters[channel]
        result = adapter.send(envelope)
        if result.ok and not result.acknowledgement and channel != ChannelId.STORE_AND_FORWARD:
            return SendResult(
                ok=False,
                channel=channel,
                delivery_state=DeliveryState.AWAITING_ACK,
                acknowledgement=False,
                status_message="Transmission attempted; acknowledgement has not been received.",
                detail=result.detail,
            )
        return result


def apply_relay_rules(
    envelope: RelayEnvelope,
    node_id: str,
    seen_ids: set[str],
    now: datetime | None = None,
) -> tuple[RelayOutcome, RelayEnvelope | None]:
    now = now or datetime.now(timezone.utc)
    if envelope.sos_id in seen_ids:
        return RelayOutcome.DUPLICATE, None
    if envelope.ttl <= 0:
        return RelayOutcome.TTL_EXHAUSTED, None
    age_seconds = (now - envelope.timestamp.replace(tzinfo=timezone.utc)).total_seconds()
    if age_seconds > 24 * 3600:
        return RelayOutcome.EXPIRED, None
    if node_id in envelope.relay_path:
        return RelayOutcome.DUPLICATE, None

    forwarded = envelope.model_copy(deep=True)
    forwarded.hop_count += 1
    forwarded.ttl -= 1
    forwarded.relay_path = list(envelope.relay_path) + [node_id]
    forwarded.delivery_state = DeliveryState.RELAYED
    return RelayOutcome.FORWARDED, forwarded


def backoff_seconds(attempt: int, base: float = 2.0, cap: float = 120.0) -> float:
    return min(cap, base * (2 ** max(0, attempt - 1)))
