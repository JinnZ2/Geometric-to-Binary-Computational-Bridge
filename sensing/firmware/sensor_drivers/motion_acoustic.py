"""
PIR motion + USB-microphone drivers.

Two thin drivers in one module because they tend to deploy together
(cheap PIR triggers a microphone capture when motion is detected, so
the audio stream only records when something is happening — saves
storage and battery).

PIR (Passive Infrared) — real hardware path: GPIO pin reading from a
HC-SR501 or AM312 module. The driver expects a ``gpio_read(pin)``
callable returning 0 or 1.

Microphone — real hardware path: ``arecord``-style capture to a WAV
file. The driver expects a ``capture_seconds(out_path, seconds)``
callable so any backend (alsaaudio, sounddevice, sox) can be wired in.
The WAV is hashed (SHA-256) so the manifest and the recording can be
verified independently. Audio bytes are NOT carried in the
:class:`SensorReading` — only metadata + hash + path.

Confidence grades:
  PIR        : 0.75 (motion only — no species ID)
  Microphone : 0.55 (raw audio; species ID needs an inference layer
                     and lives in ``processing/``, not here)
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorUnavailableError,
    diurnal_phase,
)


# ----------------------------------------------------------------------
# PIR
# ----------------------------------------------------------------------

class PIRMotionDriver(SensorDriver):
    """Driver for one PIR motion sensor on a GPIO pin."""

    device_name = "PIRMotion"
    confidence_grade = 0.75

    def __init__(
        self,
        channel: str = "primary",
        gpio_read: Optional[Callable[[int], int]] = None,
        gpio_pin: int = 17,
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        self._gpio_read = gpio_read
        self._gpio_pin = gpio_pin
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if self._gpio_read is None:
            raise SensorUnavailableError(
                "no gpio_read callable supplied — pass one or set mock=True"
            )

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        try:
            assert self._gpio_read is not None
            level = int(self._gpio_read(self._gpio_pin))
        except Exception as exc:  # noqa: BLE001
            raise SensorUnavailableError(str(exc)) from exc
        return ({"motion": float(level)}, {}, "")

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        # Crepuscular activity: more events near dawn/dusk (when
        # |diurnal_phase| ≈ 0.5).  Active probability ranges roughly
        # 0.5 % at solar noon to 6 % at twilight.
        import math
        twilight_factor = 1.0 - abs(diurnal_phase())
        # Stretch toward 0/1: low base rate + sharp twilight peak.
        prob = 0.005 + 0.06 * (twilight_factor ** 4)
        triggered = self._rng.random() < prob
        return ({"motion": 1.0 if triggered else 0.0}, {}, "")


# ----------------------------------------------------------------------
# Microphone
# ----------------------------------------------------------------------

class MicrophoneDriver(SensorDriver):
    """Driver that captures a short audio clip on demand.

    Mock mode writes a tiny placeholder file (so downstream code paths
    that hash the recording or check its existence work end-to-end)
    and returns the same metadata shape a real capture would.
    """

    device_name = "Microphone"
    confidence_grade = 0.55

    def __init__(
        self,
        channel: str = "ambient",
        capture_seconds: Optional[
            Callable[[Path, float], None]
        ] = None,
        record_seconds: float = 5.0,
        out_dir: Path = Path("./audio_captures"),
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        self._capture_seconds = capture_seconds
        self._record_seconds = record_seconds
        self._out_dir = Path(out_dir)
        self._out_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if self._capture_seconds is None:
            raise SensorUnavailableError(
                "no capture_seconds callable supplied — pass one or set mock=True"
            )

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        from datetime import datetime, timezone

        out_path = self._out_dir / (
            f"{self.channel}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.wav"
        )
        try:
            assert self._capture_seconds is not None
            self._capture_seconds(out_path, self._record_seconds)
        except Exception as exc:  # noqa: BLE001
            raise SensorUnavailableError(str(exc)) from exc
        return self._summarise(out_path)

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        from datetime import datetime, timezone

        out_path = self._out_dir / (
            f"{self.channel}_mock_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_"
            f"{self._rng.randrange(1_000_000):06d}.wav"
        )
        # Write a tiny placeholder so the hash is real.
        out_path.write_bytes(b"MOCK\x00" + os.urandom(64))
        return self._summarise(out_path)

    def _summarise(
        self, out_path: Path,
    ) -> Tuple[Dict[str, float], Dict[str, float], str]:
        size_bytes = out_path.stat().st_size
        sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
        return (
            {"recorded_seconds": float(self._record_seconds)},
            {"size_bytes": float(size_bytes)},
            f"path={out_path};sha256={sha}",
        )


__all__ = ["PIRMotionDriver", "MicrophoneDriver"]
