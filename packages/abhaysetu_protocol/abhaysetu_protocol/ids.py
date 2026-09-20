from __future__ import annotations

import secrets
from datetime import datetime, timezone


def generate_sos_id(now: datetime | None = None) -> str:
    """Offline-safe unique SOS identifier.

    Format: SOS-YYYY-XXXXXXXX (8 hex chars). Sequential IDs like SOS-2026-000184
    are assigned only by a hub/server sequence when the message is ingested;
    clients never invent a global counter.
    """
    year = (now or datetime.now(timezone.utc)).year
    return f"SOS-{year}-{secrets.token_hex(4).upper()}"


def generate_device_id() -> str:
    return f"DEV-{secrets.token_hex(8).upper()}"


def generate_event_id() -> str:
    return f"EVT-{secrets.token_hex(8).upper()}"


def generate_canonical_sequence_id(year: int, sequence: int) -> str:
    return f"SOS-{year}-{sequence:06d}"
