"""
Capacitive soil-moisture sensor.

Capacitive sensors are durable (no electrolytic corrosion of probes),
read out as an analog voltage proportional to dielectric constant of
surrounding medium, and need a per-soil calibration to convert
voltage → volumetric water content (VWC).

Real-hardware path: ADC channel on a USB DAQ. The driver expects an
``adc_read(channel) -> float`` callable to be passed in at
construction; this avoids hard-coding any specific DAQ library so the
same driver works with MCP3008 (SPI), ADS1115 (I²C), or a USB ADC.

Mock readings:
  * baseline VWC drifts slowly toward a target (rain pulse vs. dry-down).
  * raw "ohms" derived from VWC via a coarse Topp equation
    so downstream calibration code can be exercised.

Confidence grade: 0.85
(robust hardware, but soil-specific calibration is always a source of
moderate error).
"""

from __future__ import annotations

import time
from typing import Callable, Dict, Optional, Tuple

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorUnavailableError,
    jittered_baseline,
)


def _vwc_to_ohms(vwc: float) -> float:
    """
    Coarse Topp-equation-style inverse: drier soil → higher resistance.

    Real calibrations span 1e3 (saturated) to 1e6+ (bone dry); the
    mapping below is plausible enough for synthetic data and lets the
    downstream encoder produce an "inferred_water_content" the way the
    spec asks for.
    """
    vwc = max(0.0, min(0.6, vwc))
    return 1e3 * (10 ** (3.0 * (0.5 - vwc)))


class CapacitiveSoilMoistureDriver(SensorDriver):
    """Driver for a capacitive soil-moisture probe."""

    device_name = "CapacitiveSoilMoisture"
    confidence_grade = 0.85

    def __init__(
        self,
        channel: str = "primary",
        adc_read: Optional[Callable[[int], float]] = None,
        adc_channel: int = 0,
        v_dry: float = 3.0,
        v_wet: float = 1.2,
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        """
        Parameters
        ----------
        adc_read
            Callable that returns the channel voltage. Pass ``None``
            to force mock mode regardless of ``mock``.
        v_dry / v_wet
            Calibration endpoints in volts; voltage between them is
            linearly interpolated to a 0–1 saturation fraction, then
            scaled to a 0–0.5 VWC range. Recalibrate per soil.
        """
        self._adc_read = adc_read
        self._adc_channel = adc_channel
        self._v_dry = v_dry
        self._v_wet = v_wet
        self._mock_state = 0.30  # starting VWC for the random walk
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if self._adc_read is None:
            raise SensorUnavailableError(
                "no adc_read callable supplied — pass one or set mock=True"
            )

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        try:
            assert self._adc_read is not None
            voltage = float(self._adc_read(self._adc_channel))
        except Exception as exc:  # noqa: BLE001
            raise SensorUnavailableError(str(exc)) from exc
        # Linear interpolation across calibration endpoints.
        span = (self._v_dry - self._v_wet)
        if span == 0.0:
            saturation = 0.5
        else:
            saturation = max(0.0, min(1.0, (self._v_dry - voltage) / span))
        vwc = 0.5 * saturation  # cap mock-physical range at 50% VWC
        ohms = _vwc_to_ohms(vwc)
        return (
            {"vwc": round(vwc, 4), "saturation": round(saturation, 4)},
            {"voltage": voltage, "inferred_ohms": ohms},
            "",
        )

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        # Drift the synthetic VWC by a small random step so consecutive
        # readings tell a coherent story (slow drying / rewetting).
        step = self._rng.uniform(-0.002, 0.002)
        # Diurnal evaporation pull: dries slightly during "day".
        from sensing.firmware.sensor_drivers.base import diurnal_phase
        evap = -0.0005 * (1.0 - diurnal_phase())
        self._mock_state = max(0.05, min(0.55, self._mock_state + step + evap))

        vwc = jittered_baseline(self._rng, self._mock_state, 0.005)
        saturation = vwc / 0.5
        ohms = _vwc_to_ohms(vwc)
        voltage = self._v_dry - saturation * (self._v_dry - self._v_wet)
        return (
            {"vwc": round(vwc, 4), "saturation": round(saturation, 4)},
            {"voltage": round(voltage, 4), "inferred_ohms": round(ohms, 1)},
            "",
        )

    def _close(self) -> None:
        # Caller owns the ADC handle — nothing to release here.
        return None


__all__ = ["CapacitiveSoilMoistureDriver"]
