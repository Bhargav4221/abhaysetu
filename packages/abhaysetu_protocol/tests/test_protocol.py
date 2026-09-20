import pytest
from nacl.signing import SigningKey

from abhaysetu_protocol.ai_local import classify_text
from abhaysetu_protocol.comms import CommunicationManager, AdapterCapabilities, SendResult, apply_relay_rules, backoff_seconds
from abhaysetu_protocol.crypto import encode_public_key, hash_payload, sign_payload, verify_signature
from abhaysetu_protocol.enums import ChannelId, DeliveryState, EmergencyCategory, RelayOutcome
from abhaysetu_protocol.ids import generate_sos_id
from abhaysetu_protocol.messages import RelayEnvelope, SosPayload


class FakeAdapter:
    def __init__(self, channel: ChannelId, available: bool, ack: bool = True):
        self.channel = channel
        self._available = available
        self._ack = ack

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(channel=self.channel, available=self._available, reason="test")

    def send(self, envelope: RelayEnvelope) -> SendResult:
        if not self._available:
            return SendResult(False, self.channel, DeliveryState.FAILED, False, "unavailable")
        return SendResult(True, self.channel, DeliveryState.ACKNOWLEDGED, self._ack, "ok")


def test_signature_roundtrip():
    key = SigningKey.generate()
    payload = SosPayload(device_id="DEV-1", origin_public_key=encode_public_key(key))
    sig = sign_payload(payload.signing_dict(), key)
    assert verify_signature(payload.signing_dict(), sig, encode_public_key(key))
    assert hash_payload(payload.signing_dict())


def test_manager_skips_unavailable_and_uses_next():
    mgr = CommunicationManager(
        [
            FakeAdapter(ChannelId.INTERNET, False),
            FakeAdapter(ChannelId.LOCAL_NETWORK, True),
            FakeAdapter(ChannelId.STORE_AND_FORWARD, True),
        ]
    )
    assert mgr.select_channel() == ChannelId.LOCAL_NETWORK


def test_manager_offline_falls_to_store():
    mgr = CommunicationManager(
        [
            FakeAdapter(ChannelId.INTERNET, False),
            FakeAdapter(ChannelId.STORE_AND_FORWARD, True),
        ]
    )
    assert mgr.select_channel() == ChannelId.STORE_AND_FORWARD


def test_no_ack_is_not_success():
    mgr = CommunicationManager([FakeAdapter(ChannelId.INTERNET, True, ack=False)])
    key = SigningKey.generate()
    payload = SosPayload(device_id="DEV-1", origin_public_key=encode_public_key(key))
    env = RelayEnvelope(
        sos_id=payload.sos_id,
        origin_device_id=payload.device_id,
        timestamp=payload.timestamp,
        message_hash="x",
        digital_signature="y",
        origin_public_key=payload.origin_public_key,
        payload=payload,
    )
    result = mgr.transmit(env)
    assert result.acknowledgement is False
    assert result.ok is False


def test_relay_duplicate_and_ttl():
    key = SigningKey.generate()
    payload = SosPayload(device_id="DEV-1", origin_public_key=encode_public_key(key))
    env = RelayEnvelope(
        sos_id=payload.sos_id,
        origin_device_id="DEV-1",
        timestamp=payload.timestamp,
        ttl=1,
        message_hash="x",
        digital_signature="y",
        origin_public_key=payload.origin_public_key,
        payload=payload,
        relay_path=["A"],
    )
    outcome, forwarded = apply_relay_rules(env, "B", set())
    assert outcome == RelayOutcome.FORWARDED
    assert forwarded.ttl == 0
    outcome2, _ = apply_relay_rules(forwarded, "C", set())
    assert outcome2 == RelayOutcome.TTL_EXHAUSTED
    outcome3, _ = apply_relay_rules(env, "A", set())
    assert outcome3 == RelayOutcome.DUPLICATE


def test_classify_mixed_language():
    cat, prio, _ = classify_text("help आग in building")
    assert cat == EmergencyCategory.FIRE


def test_backoff():
    assert backoff_seconds(1) == 2
    assert backoff_seconds(5) == 32


def test_sos_id_format():
    sos_id = generate_sos_id()
    assert sos_id.startswith("SOS-")
