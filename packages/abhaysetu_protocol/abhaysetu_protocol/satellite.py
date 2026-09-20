"""Provider-independent satellite adapter.

An ordinary phone cannot become a satellite communicator through software.
Real delivery requires supported hardware or a contracted satellite service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from abhaysetu_protocol.comms import AdapterCapabilities, SendResult
from abhaysetu_protocol.enums import ChannelId, DeliveryState
from abhaysetu_protocol.messages import RelayEnvelope


class SatelliteProvider(Protocol):
    def check_availability(self) -> bool: ...
    def signal(self) -> float | None: ...
    def send(self, message: bytes) -> str | None: ...
    def delivery_status(self, handle: str) -> str: ...
    def receive_ack(self, handle: str) -> bool: ...


class NoSatelliteProvider:
    def check_availability(self) -> bool:
        return False

    def signal(self) -> float | None:
        return None

    def send(self, message: bytes) -> str | None:
        return None

    def delivery_status(self, handle: str) -> str:
        return "UNAVAILABLE"

    def receive_ack(self, handle: str) -> bool:
        return False


class SimulatedSatelliteProvider:
    """Development-only. Must never be wired when ALLOW_SIMULATED_ADAPTERS is false."""

    def check_availability(self) -> bool:
        return True

    def signal(self) -> float | None:
        return 0.5

    def send(self, message: bytes) -> str | None:
        return "SIM-HANDLE"

    def delivery_status(self, handle: str) -> str:
        return "SIMULATED"

    def receive_ack(self, handle: str) -> bool:
        return False


@dataclass
class SatelliteAdapter:
    channel: ChannelId = ChannelId.SATELLITE
    provider: SatelliteProvider = None  # type: ignore[assignment]
    enabled: bool = False
    allow_simulated: bool = False

    def __post_init__(self) -> None:
        if self.provider is None:
            self.provider = NoSatelliteProvider()
        if isinstance(self.provider, SimulatedSatelliteProvider) and not self.allow_simulated:
            self.provider = NoSatelliteProvider()
            self.enabled = False

    def checkAvailability(self) -> bool:
        return self.enabled and self.provider.check_availability()

    def getSignalStatus(self) -> float | None:
        return self.provider.signal() if self.checkAvailability() else None

    def capabilities(self) -> AdapterCapabilities:
        available = self.checkAvailability()
        return AdapterCapabilities(
            channel=self.channel,
            available=available,
            reason="Satellite hardware/service available" if available else "Satellite communication requires supported hardware or a provider. Not available on this device.",
            requires_hardware=True,
            requires_external_service=True,
            battery_cost=0.7,
        )

    def sendEmergencyMessage(self, envelope: RelayEnvelope) -> SendResult:
        return self.send(envelope)

    def send(self, envelope: RelayEnvelope) -> SendResult:
        if not self.checkAvailability():
            return SendResult(
                False,
                self.channel,
                DeliveryState.FAILED,
                False,
                "Satellite communication is not available on this device.",
            )
        handle = self.provider.send(envelope.model_dump_json().encode("utf-8"))
        if not handle:
            return SendResult(False, self.channel, DeliveryState.FAILED, False, "Satellite service did not accept the message.")
        if self.provider.delivery_status(handle) == "SIMULATED":
            return SendResult(
                False,
                self.channel,
                DeliveryState.AWAITING_ACK,
                False,
                "Simulated satellite adapter is active in development. This is not a real satellite delivery.",
            )
        if not self.provider.receive_ack(handle):
            return SendResult(
                False,
                self.channel,
                DeliveryState.AWAITING_ACK,
                False,
                "Satellite message submitted; provider acknowledgement has not been received.",
            )
        return SendResult(
            True,
            self.channel,
            DeliveryState.ACKNOWLEDGED,
            True,
            "SOS submitted through satellite communication service.",
        )

    def getDeliveryStatus(self, handle: str) -> str:
        return self.provider.delivery_status(handle)

    def receiveAcknowledgement(self, handle: str) -> bool:
        return self.provider.receive_ack(handle)
