from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .enums import ChannelId

DEFAULT_COMMUNICATION_ORDER: tuple[ChannelId, ...] = (
    ChannelId.INTERNET,
    ChannelId.LOCAL_NETWORK,
    ChannelId.PEER_RELAY,
    ChannelId.RADIO,
    ChannelId.SATELLITE,
    ChannelId.STORE_AND_FORWARD,
)


@dataclass(frozen=True)
class CommunicationPolicy:
    """Configurable channel preference. Unavailable channels are skipped immediately."""

    order: Sequence[ChannelId] = DEFAULT_COMMUNICATION_ORDER
    default_ttl_hops: int = 8
    max_ttl_hops: int = 16
    peer_scan_budget_seconds: float = 8.0
    transmit_timeout_seconds: float = 12.0
    retry_base_seconds: float = 2.0
    retry_max_seconds: float = 120.0

    @classmethod
    def from_csv(cls, csv: str) -> "CommunicationPolicy":
        ids = []
        for raw in csv.split(","):
            token = raw.strip()
            if not token:
                continue
            ids.append(ChannelId(token))
        if ChannelId.STORE_AND_FORWARD not in ids:
            ids.append(ChannelId.STORE_AND_FORWARD)
        return cls(order=tuple(ids))
