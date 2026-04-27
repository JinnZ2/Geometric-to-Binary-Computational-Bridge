"""
DS18B20 — 1-wire digital temperature sensor.

Real-hardware path expects the standard Linux ``w1-gpio``/``w1-therm``
kernel modules (``cat /sys/bus/w1/devices/<addr>/w1_slave``). On any
other platform — or whenever those device files are missing — the
driver falls back to mock mode automatically.

Mock readings:
  * baseline picked per channel (``surface``, ``10cm``, ``30cm``, ``50cm``)
    — deeper channels track surface less aggressively.
  * a smooth diurnal swing on the surface channel, attenuated with depth.
  * small Gaussian-ish noise so consecutive samples differ.

Confidence grade for downstream epi classification: 0.95
(thermal mass and a digital comm protocol make this one of the most
trustworthy sensors in the kit).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorUnavailableError,
    diurnal_phase,
    jittered_baseline,
)

# Per-channel surface-baseline temperature (Celsius). Tweak when
# calibrating to a new climate; defaults are picked for a temperate
# spring deployment.
_BASELINE_C = {
    "surface": 12.0,
    "10cm":    10.0,
    "30cm":     8.0,
    "50cm":     7.0,
}
# Depth attenuation of the diurnal swing.
_DIURNAL_AMPLITUDE_C = {
    "surface": 6.0,
    "10cm":    3.0,
    "30cm":    1.0,
    "50cm":    0.3,
}
_W1_BUS_DIR = Path("/sys/bus/w1/devices")


class DS18B20Driver(SensorDriver):
    """Driver for one DS18B20 attached to the system 1-wire bus."""

    device_name = "DS18B20"
    confidence_grade = 0.95

    def __init__(
        self,
        channel: str = "surface",
        device_address: str | None = None,
        mock: bool | None = None,
        seed: int | None = None,
    ) -> None:
        self._device_address = device_address
        self._w1_path: Path | None = None
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if not _W1_BUS_DIR.exists():
            raise SensorUnavailableError(
                f"{_W1_BUS_DIR} not found — kernel 1-wire modules unloaded?"
            )
        if self._device_address is None:
            # Pick the first w1_slave device that looks like a DS18B20
            # (its 1-wire family code is 0x28).
            candidates = [
                p for p in _W1_BUS_DIR.iterdir()
                if p.name.startswith("28-")
            ]
            if not candidates:
                raise SensorUnavailableError(
                    "no DS18B20 devices found under /sys/bus/w1/devices"
                )
            self._device_address = candidates[0].name
        self._w1_path = _W1_BUS_DIR / self._device_address / "w1_slave"
        if not self._w1_path.exists():
            raise SensorUnavailableError(
                f"device file {self._w1_path} missing"
            )

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        assert self._w1_path is not None
        try:
            text = self._w1_path.read_text()
        except OSError as exc:
            raise SensorUnavailableError(str(exc)) from exc
        # The kernel format is two lines:
        #   xx xx xx xx xx xx xx xx xx : crc=xx YES
        #   xx xx xx xx xx xx xx xx xx t=12345
        if "YES" not in text or "t=" not in text:
            raise SensorUnavailableError(f"malformed w1 reading: {text!r}")
        milli_c = int(text.split("t=", 1)[1].strip())
        celsius = milli_c / 1000.0
        return ({"celsius": celsius}, {"milli_c": float(milli_c)}, "")

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        baseline = _BASELINE_C.get(self.channel, 12.0)
        amplitude = _DIURNAL_AMPLITUDE_C.get(self.channel, 4.0)
        # Diurnal: warmest at noon (-cos), coolest at midnight (+cos).
        diurnal = -amplitude * diurnal_phase()
        celsius = jittered_baseline(self._rng, baseline + diurnal, 0.2)
        return (
            {"celsius": round(celsius, 3)},
            {"milli_c": round(celsius * 1000.0, 1)},
            "",
        )


__all__ = ["DS18B20Driver"]
