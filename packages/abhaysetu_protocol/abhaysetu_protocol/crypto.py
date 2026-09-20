from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=_json_default).encode(
        "utf-8"
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Unserializable type: {type(value)}")


def hash_payload(payload: dict[str, Any]) -> str:
    import hashlib

    return hashlib.sha256(canonical_json(payload)).hexdigest()


def generate_signing_key() -> SigningKey:
    return SigningKey.generate()


def encode_public_key(key: SigningKey) -> str:
    return key.verify_key.encode(encoder=Base64Encoder).decode("ascii")


def sign_payload(payload: dict[str, Any], signing_key: SigningKey) -> str:
    signed = signing_key.sign(canonical_json(payload), encoder=Base64Encoder)
    return signed.signature.decode("ascii")


def verify_signature(payload: dict[str, Any], signature_b64: str, public_key_b64: str) -> bool:
    try:
        verify_key = VerifyKey(public_key_b64.encode("ascii"), encoder=Base64Encoder)
        verify_key.verify(canonical_json(payload), signature_b64.encode("ascii"), encoder=Base64Encoder)
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False
