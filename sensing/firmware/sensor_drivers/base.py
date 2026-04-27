"""
Common base for every sensor driver.

The contract is intentionally tiny: every driver returns a
:class:`SensorReading` dict from ``read()``, releases hardware handles
in ``close()``, and self-describes via ``driver.metadata``. Mock mode
is a default fallback so the entire pipeline runs in environments
without the underlying hardware library — useful for CI, for
designing the field deployment from a laptop, and for anyone
following the build incrementally.
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

LOG = logging.getLogger(__name__)


class SensorUnavailableError(RuntimeError):
    """Raised when a driver in real (non-mock) mode cannot reach hardware."""


@dataclass
class SensorReading:
    """One sample from a sensor.

    Attributes
    ----------
    timestamp_iso
        UTC ISO-8601 string. Always set by :meth:`SensorDriver.read`.
    sensor_id
        Stable identifier — usually ``f"{driver_class}.{channel}"``.
    values
        Dict of named scalar measurements (e.g.
        ``{"celsius": 12.5}``). Units belong in the key name; if you
        need richer typing, add a sibling ``"<key>_unit"`` field.
    raw
        Optional unprocessed values (raw counts, ohms, etc.) for
        downstream calibration. Empty for already-converted readings.
    is_mock
        ``True`` when the value came from mock mode rather than real
        hardware.
    note
        Free-form annotation — driver may surface a transient hardware
        quirk here without polluting ``values``.
    """

    timestamp_iso: str
    sensor_id: str
    values: Dict[str, float]
    raw: Dict[str, float] = field(default_factory=dict)
    is_mock: bool = False
    note: str = ""


class SensorDriver(ABC):
    """
    Abstract base for every sensor driver.

    Subclasses implement:

    * :attr:`device_name` — human-readable name (DS18B20, MLX90614…).
    * :meth:`_open` / :meth:`_close` — real-hardware lifecycle.
    * :meth:`_read_real` — one sample from real hardware.
    * :meth:`_read_mock` — one plausible synthetic sample.

    The base class handles timestamping, mock-mode fallback, and the
    one-shot warning when a real driver fails to open.
    """

    device_name: str = "<unset>"

    def __init__(
        self,
        channel: str = "default",
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        self.channel = channel
        self._rng = random.Random(seed)
        self._mock_warned = False

        if mock is None:
            try:
                self._open()
                self.mock = False
            except SensorUnavailableError as exc:
                self._mock_first_warning(str(exc))
                self.mock = True
        elif mock:
            self.mock = True
        else:
            self._open()
            self.mock = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def sensor_id(self) -> str:
        return f"{self.device_name}.{self.channel}"

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "device": self.device_name,
            "channel": self.channel,
            "mode": "mock" if self.mock else "real",
        }

    def read(self) -> SensorReading:
        """Take one timestamped sample."""
        if self.mock:
            values, raw, note = self._read_mock()
        else:
            try:
                values, raw, note = self._read_real()
            except SensorUnavailableError as exc:
                # Hardware vanished mid-run — degrade to mock so the
                # node keeps producing data rather than crashing.
                self._mock_first_warning(
                    f"hardware lost mid-run: {exc} (degrading to mock)"
                )
                self.mock = True
                values, raw, note = self._read_mock()

        return SensorReading(
            timestamp_iso=_now_iso(),
            sensor_id=self.sensor_id,
            values=values,
            raw=raw,
            is_mock=self.mock,
            note=note,
        )

    def close(self) -> None:
        if not self.mock:
            try:
                self._close()
            except Exception as exc:  # noqa: BLE001 — best effort
                LOG.debug("%s close raised %s", self.sensor_id, exc)

    # ------------------------------------------------------------------
    # Subclass hooks
    # ------------------------------------------------------------------

    @abstractmethod
    def _read_mock(self) -> tuple[Dict[str, float], Dict[str, float], str]:
        ...

    def _read_real(self) -> tuple[Dict[str, float], Dict[str, float], str]:
        raise SensorUnavailableError(
            f"{self.device_name} has no real-hardware implementation; "
            f"construct with mock=True to use synthetic data."
        )

    def _open(self) -> None:
        raise SensorUnavailableError(
            f"{self.device_name} hardware support not implemented yet."
        )

    def _close(self) -> None:
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _mock_first_warning(self, reason: str) -> None:
        if not self._mock_warned:
            LOG.warning(
                "%s starting in mock mode: %s", self.sensor_id, reason,
            )
            self._mock_warned = True


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _now_iso() -> str:
    """UTC ISO-8601 timestamp with second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def jittered_baseline(rng: random.Random, base: float, jitter: float) -> float:
    """Return ``base + small noise`` — used by mock readings."""
    return base + rng.uniform(-jitter, jitter)


def diurnal_phase() -> float:
    """0.0 at solar noon, ±1.0 at midnight, smooth in between.

    Used by mock drivers to make synthetic temperature / light data
    look like a real day-night cycle rather than flat noise.
    """
    seconds_into_day = time.time() % 86400.0
    # Cosine wave: 1 at midnight, -1 at noon, smooth.
    import math
    return math.cos(2.0 * math.pi * seconds_into_day / 86400.0)
