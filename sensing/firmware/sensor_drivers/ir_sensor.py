"""
MLX90614 — non-contact infrared thermometer.

Reads object temperature ``T_obj`` and ambient/sensor-die temperature
``T_amb``. The difference ``T_obj − T_amb`` is the headline signal —
it drops sharply when the sensor is pointed at a cold canopy under a
warm sky, or rises during animal-body or solar-warmed-rock pass.

Real-hardware path: I²C bus, default address 0x5A. The driver expects
an ``i2c_read_word(register) -> int`` callable so it stays free of
any specific I²C library.

Mock readings:
  * ``T_amb`` tracks the diurnal envelope.
  * ``T_obj`` is ``T_amb`` minus a positive offset (sky-cold) plus a
    rare warm pulse simulating an animal body in frame.

Confidence grade: 0.90.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorUnavailableError,
    diurnal_phase,
    jittered_baseline,
)

_REG_T_AMB = 0x06
_REG_T_OBJ1 = 0x07


def _word_to_celsius(word: int) -> float:
    # Datasheet conversion: T_K = word * 0.02; T_C = T_K - 273.15.
    return word * 0.02 - 273.15


class MLX90614Driver(SensorDriver):
    """Driver for one MLX90614 IR thermometer."""

    device_name = "MLX90614"
    confidence_grade = 0.90

    def __init__(
        self,
        channel: str = "canopy",
        i2c_read_word: Optional[Callable[[int], int]] = None,
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        self._i2c_read_word = i2c_read_word
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if self._i2c_read_word is None:
            raise SensorUnavailableError(
                "no i2c_read_word callable supplied — pass one or set mock=True"
            )

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        try:
            assert self._i2c_read_word is not None
            t_amb = _word_to_celsius(self._i2c_read_word(_REG_T_AMB))
            t_obj = _word_to_celsius(self._i2c_read_word(_REG_T_OBJ1))
        except Exception as exc:  # noqa: BLE001
            raise SensorUnavailableError(str(exc)) from exc
        return (
            {
                "t_obj_c": round(t_obj, 3),
                "t_amb_c": round(t_amb, 3),
                "delta_c": round(t_obj - t_amb, 3),
            },
            {},
            "",
        )

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        # Diurnal: warmest at noon (-cos), coolest at midnight (+cos).
        ambient_baseline = 12.0 - 6.0 * diurnal_phase()
        t_amb = jittered_baseline(self._rng, ambient_baseline, 0.3)
        # Sky / canopy is typically 5–15 C colder than ambient air.
        t_obj = t_amb - jittered_baseline(self._rng, 8.0, 1.5)

        # 2% chance of a warm-body pass (deer / bear / human).
        note = ""
        if self._rng.random() < 0.02:
            t_obj = t_amb + jittered_baseline(self._rng, 18.0, 4.0)
            note = "warm_pass_event"

        return (
            {
                "t_obj_c": round(t_obj, 3),
                "t_amb_c": round(t_amb, 3),
                "delta_c": round(t_obj - t_amb, 3),
            },
            {},
            note,
        )


__all__ = ["MLX90614Driver"]
