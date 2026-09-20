"""Hardware abstraction for emergency radio gateways.

This module does not talk to a specific commercial radio network.
A physical ESP32/LoRa (or equivalent) gateway must implement the
byte protocol documented in radio-gateway/README.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from abhaysetu_protocol.comms import AdapterCapabilities, SendResult
from abhaysetu_protocol.enums import ChannelId, DeliveryState
from abhaysetu_protocol.messages import RelayEnvelope


class RadioTransport(Protocol):
    def discover(self) -> list[str]: ...
    def connect(self, gateway_id: str) -> bool: ...
    def send(self, frame: bytes) -> bool: ...
    def receive(self, timeout_seconds: float) -> bytes | None: ...
    def signal(self) -> float | None: ...
    def battery(self) -> float | None: ...
    def disconnect(self) -> None: ...


@dataclass
class RadioGatewayStatus:
    connected: bool
    gateway_id: Optional[str]
    signal: Optional[float]
    battery: Optional[float]
    detail: str


class UnconnectedRadioTransport:
    """Default transport: reports no hardware. Never claims delivery."""

    def discover(self) -> list[str]:
        return []

    def connect(self, gateway_id: str) -> bool:
        return False

    def send(self, frame: bytes) -> bool:
        return False

    def receive(self, timeout_seconds: float) -> bytes | None:
        return None

    def signal(self) -> float | None:
        return None

    def battery(self) -> float | None:
        return None

    def disconnect(self) -> None:
        return None


class RadioAdapter:
    channel = ChannelId.RADIO

    def __init__(self, transport: RadioTransport | None = None, enabled: bool = False):
        self.transport = transport or UnconnectedRadioTransport()
        self.enabled = enabled
        self._gateway: str | None = None

    def discoverGateway(self) -> list[str]:
        if not self.enabled:
            return []
        return self.transport.discover()

    def connectGateway(self, gateway_id: str) -> bool:
        ok = self.enabled and self.transport.connect(gateway_id)
        self._gateway = gateway_id if ok else None
        return ok

    def getSignalStatus(self) -> RadioGatewayStatus:
        return RadioGatewayStatus(
            connected=bool(self._gateway),
            gateway_id=self._gateway,
            signal=self.transport.signal() if self._gateway else None,
            battery=self.transport.battery() if self._gateway else None,
            detail="Radio gateway not connected" if not self._gateway else "Gateway connected",
        )

    def getBatteryStatus(self) -> float | None:
        return self.transport.battery() if self._gateway else None

    def disconnectGateway(self) -> None:
        self.transport.disconnect()
        self._gateway = None

    def capabilities(self) -> AdapterCapabilities:
        gateways = self.discoverGateway() if self.enabled else []
        available = bool(self._gateway or gateways)
        return AdapterCapabilities(
            channel=self.channel,
            available=available,
            reason="Emergency radio gateway connected" if available else "No radio gateway detected. External hardware required.",
            requires_hardware=True,
            battery_cost=0.4,
        )

    def sendMessage(self, envelope: RelayEnvelope) -> SendResult:
        return self.send(envelope)

    def send(self, envelope: RelayEnvelope) -> SendResult:
        if not self._gateway:
            found = self.discoverGateway()
            if found:
                self.connectGateway(found[0])
        if not self._gateway:
            return SendResult(
                ok=False,
                channel=self.channel,
                delivery_state=DeliveryState.FAILED,
                acknowledgement=False,
                status_message="Radio gateway not available.",
            )
        frame = envelope.model_dump_json().encode("utf-8")
        sent = self.transport.send(frame)
        if not sent:
            return SendResult(False, self.channel, DeliveryState.FAILED, False, "Radio gateway rejected the frame.")
        ack = self.transport.receive(8.0)
        if not ack:
            return SendResult(
                False,
                self.channel,
                DeliveryState.AWAITING_ACK,
                False,
                "Radio frame handed to gateway; gateway acknowledgement has not been received.",
            )
        return SendResult(
            True,
            self.channel,
            DeliveryState.ACKNOWLEDGED,
            True,
            "SOS delivered through emergency radio gateway.",
        )

    def receiveMessage(self, timeout_seconds: float = 5.0) -> bytes | None:
        return self.transport.receive(timeout_seconds)
