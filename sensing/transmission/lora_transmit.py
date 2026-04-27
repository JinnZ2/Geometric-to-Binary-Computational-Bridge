"""
lora_transmit — wrap a LoRa send() callable into a Primitive transmitter.

Default behaviour is *no-op* — the transmitter logs the line it
*would* have sent and returns ``False`` (caller queues the Primitive
for later). Pass a real ``send_bytes(payload: bytes) -> bool``
callable wired to pyLoRa, RadioHead, or whatever radio module you
have on the target board.

Why no built-in radio binding: every LoRa stack has different setup
(SPI pins, frequency, sync word, spreading factor). Pinning a
specific library here would force every node to depend on it. The
deployment guide in ``hardware/tier1_minimal.md`` documents the
two most common bindings; pull whichever fits your hardware.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from sensing.processing.primitives_encoder import (
    Primitive,
    primitive_to_obs_line,
)

LOG = logging.getLogger(__name__)


@dataclass
class LoRaTransmitter:
    """Stub LoRa transmitter; pass ``send_bytes`` to make it real."""

    send_bytes: Optional[Callable[[bytes], bool]] = None
    max_payload_bytes: int = 240
    """Conservative SF7 / BW125 / CR4-5 single-packet limit minus
    header. Larger Primitives are split into continuation packets
    by :meth:`__call__` and reassembled on the receiver."""

    def __call__(self, primitive: Primitive) -> bool:
        line = primitive_to_obs_line(primitive)
        payload = line.encode("utf-8")

        if self.send_bytes is None:
            # Log only the byte count — never the payload prefix.
            # Primitive payloads include timestamp + location bounds,
            # which would broadcast the deployment site to anyone with
            # log read access.
            LOG.info(
                "LoRaTransmitter no-op: would send %d bytes",
                len(payload),
            )
            return False

        # Single-packet path
        if len(payload) <= self.max_payload_bytes:
            try:
                return bool(self.send_bytes(payload))
            except Exception as exc:  # noqa: BLE001
                LOG.warning("LoRa send raised: %s", exc)
                return False

        # Continuation path: chunk + simple "MORE\x1f" / "END\x1f" marker
        chunks = [
            payload[i : i + self.max_payload_bytes]
            for i in range(0, len(payload), self.max_payload_bytes)
        ]
        for i, chunk in enumerate(chunks):
            tag = b"END\x1f" if i == len(chunks) - 1 else b"MORE\x1f"
            try:
                ok = bool(self.send_bytes(tag + chunk))
            except Exception as exc:  # noqa: BLE001
                LOG.warning("LoRa send raised on chunk %d: %s", i, exc)
                return False
            if not ok:
                return False
        return True


__all__ = ["LoRaTransmitter"]
