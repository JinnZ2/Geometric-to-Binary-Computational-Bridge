"""
AS7341 — 11-channel ambient-light + spectral sensor.

Visible channels at 415 / 445 / 480 / 515 / 555 / 590 / 630 / 680 nm
plus one near-IR (~ 855 nm), one clear (no filter), and one flicker
detection channel. Reads via I²C — pass an
``i2c_read_word(register: int) -> int`` callable to wire to your
specific bus library.

Mock readings:
  * baseline diurnal envelope (warmest at noon, coolest at midnight)
  * realistic relative ratios (green / red dominant in vegetation,
    blue dominant near zenith)
  * small Gaussian noise per channel

Confidence grade: 0.80 — multispectral readings carry frequency
information that the binary encoder's intensity-only cap cannot
expose, but the AS7341 is amplitude-only — it does NOT advertise a
shape channel. Polarization information lives in the sister driver
``light_polarization.py``.

Why no shape channel here: multispectral decomposition is just
amplitude-with-frequency-decomposition. Each band is still a
scalar; nothing in this driver's output requires a basis change to
recover. See ``docs/hidden_channel_pattern.md`` for the distinction.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, Optional, Tuple

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorUnavailableError,
    diurnal_phase,
    jittered_baseline,
)


# AS7341 channel centre wavelengths (nm). The flicker-detection
# channel is reported separately; "clear" has no filter.
AS7341_CHANNELS_NM = (
    ("F1", 415),
    ("F2", 445),
    ("F3", 480),
    ("F4", 515),
    ("F5", 555),
    ("F6", 590),
    ("F7", 630),
    ("F8", 680),
    ("NIR", 855),
)
"""Channel name → centre wavelength in nm."""

# Plausible relative spectrum for a sunny-day reading. These are
# *intensity ratios*, not absolute irradiance — the driver scales
# them by the diurnal envelope so the per-channel mock magnitude
# stays in a believable range.
_DEFAULT_SPECTRUM_RATIO = {
    "F1": 0.45, "F2": 0.55, "F3": 0.62, "F4": 0.70,
    "F5": 0.78, "F6": 0.71, "F7": 0.62, "F8": 0.55,
    "NIR": 0.35,
}


class AS7341Driver(SensorDriver):
    """Driver for one AS7341 spectral sensor on the I²C bus."""

    device_name = "AS7341"
    confidence_grade = 0.80

    def __init__(
        self,
        channel: str = "primary",
        i2c_read_word: Optional[Callable[[int], int]] = None,
        peak_lux: float = 50_000.0,
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        """
        Parameters
        ----------
        peak_lux
            Calibration: the synthetic intensity at solar noon, before
            the per-channel ratio is applied. Real AS7341 readings
            are 16-bit ADC counts; pass your calibrated lux equivalent
            to keep mock magnitudes plausible.
        """
        self._i2c_read_word = i2c_read_word
        self._peak_lux = peak_lux
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if self._i2c_read_word is None:
            raise SensorUnavailableError(
                "no i2c_read_word callable supplied — pass one or set mock=True"
            )

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        try:
            assert self._i2c_read_word is not None
            # AS7341 stores 16-bit channel data in pairs of registers.
            # Register addresses depend on the datasheet's CFG bank;
            # the driver leaves the layout to the caller's
            # ``i2c_read_word`` implementation. The expected return is
            # a raw count which we pass through unchanged.
            base_reg = 0x95
            values: Dict[str, float] = {}
            for i, (name, _wl) in enumerate(AS7341_CHANNELS_NM):
                values[name] = float(self._i2c_read_word(base_reg + i))
        except Exception as exc:  # noqa: BLE001
            raise SensorUnavailableError(str(exc)) from exc
        return values, {}, ""

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        # Diurnal envelope: 0 at midnight, 1 at noon. Use the same
        # phase helper as the temperature drivers so a co-located
        # node tells a coherent story across sensors.
        envelope = max(0.0, 0.5 * (1.0 - diurnal_phase()))
        # Smooth the night→day transition.
        envelope = envelope * envelope * (3.0 - 2.0 * envelope)

        values: Dict[str, float] = {}
        peak = self._peak_lux
        for name, _wl in AS7341_CHANNELS_NM:
            ratio = _DEFAULT_SPECTRUM_RATIO[name]
            base = peak * envelope * ratio
            values[name] = round(jittered_baseline(self._rng, base, base * 0.05), 2)

        return values, {"envelope": round(envelope, 4)}, ""


__all__ = ["AS7341Driver", "AS7341_CHANNELS_NM"]
