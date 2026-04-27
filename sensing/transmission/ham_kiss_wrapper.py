"""
ham_kiss_wrapper — frame a Primitive for KISS-over-TNC packet radio.

KISS is the standard TNC-to-host protocol; AX.25 packet radio is the
common air protocol. This wrapper produces a KISS-encapsulated frame
ready for a TNC; transmitting it is the operator's responsibility
(Direwolf, hostmode, ARDOP — all wire-protocol-compatible).

Operational note: HAM transmission is licensed. The transmitter
defaults to no-op; only set ``write_kiss`` when you have a callsign
and a license that authorises the band you intend to use.

Frame format produced::

    KISS data frame (port 0):
      0xC0 0x00 <payload> 0xC0

Payload is the Primitive ``.obs`` line, prefixed with the operator
callsign + " > " so the receiver knows whose station emitted it.
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

# KISS framing constants
FEND  = 0xC0
FESC  = 0xDB
TFEND = 0xDC
TFESC = 0xDD
DATA_FRAME = 0x00


def kiss_encode(payload: bytes) -> bytes:
    """Wrap ``payload`` in one KISS data frame on port 0."""
    out = bytearray([FEND, DATA_FRAME])
    for b in payload:
        if b == FEND:
            out.extend([FESC, TFEND])
        elif b == FESC:
            out.extend([FESC, TFESC])
        else:
            out.append(b)
    out.append(FEND)
    return bytes(out)


def kiss_decode(frame: bytes) -> bytes:
    """Strip framing + escapes and return the inner payload."""
    if not frame or frame[0] != FEND or frame[-1] != FEND:
        raise ValueError("frame not bracketed by FEND bytes")
    body = frame[1:-1]
    if not body or body[0] != DATA_FRAME:
        raise ValueError("first inner byte must be the data-frame marker (0x00)")
    out = bytearray()
    i = 1
    while i < len(body):
        b = body[i]
        if b == FESC and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt == TFEND:
                out.append(FEND)
            elif nxt == TFESC:
                out.append(FESC)
            else:
                raise ValueError(f"invalid escape sequence: {nxt:#x}")
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)


@dataclass
class HamKissTransmitter:
    """Stub HAM-packet transmitter; pass ``write_kiss`` to make it real."""

    callsign: str = "NOCALL"
    write_kiss: Optional[Callable[[bytes], bool]] = None

    def __post_init__(self) -> None:
        if self.write_kiss is not None and self.callsign == "NOCALL":
            raise ValueError(
                "HamKissTransmitter must be initialised with a real "
                "callsign before write_kiss is wired up — transmitting "
                "without a callsign is a regulatory violation."
            )

    def __call__(self, primitive: Primitive) -> bool:
        line = primitive_to_obs_line(primitive)
        payload = f"{self.callsign} > {line}".encode("utf-8")
        frame = kiss_encode(payload)

        if self.write_kiss is None:
            LOG.info(
                "HamKissTransmitter no-op: would send KISS frame "
                "(%d bytes, %s …)",
                len(frame), payload[:48].decode("utf-8", errors="replace"),
            )
            return False
        try:
            return bool(self.write_kiss(frame))
        except Exception as exc:  # noqa: BLE001
            LOG.warning("HAM KISS write raised: %s", exc)
            return False


__all__ = ["HamKissTransmitter", "kiss_encode", "kiss_decode"]
