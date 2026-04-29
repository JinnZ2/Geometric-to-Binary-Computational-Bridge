"""
Polarization driver — rotating-polarizer + photodiode.

The point of this driver, separate from :mod:`light_spectrum`, is
**hidden-channel awareness**. Multispectral photometry tells you
*how much light* hits the sensor at each wavelength — it operates
purely on the amplitude (Stokes S₀) channel. Polarization tells you
*what direction the field oscillates*, which is information
orthogonal to amplitude.

The recognition note in ``docs/hidden_channel_pattern.md`` flags
this as one of three known instances of the substrate-as-signal
pattern: scalar photometry collapses the polarization channel even
though it is right there in the field. This driver explicitly
declares its hidden channel via
:meth:`shape_channels` so the audit engine in
:mod:`bridges.hidden_channel_detector` can recognise it.

Hardware abstraction
--------------------
Two practical implementations:

* Rotating polarizer + photodiode + stepper — the driver requests
  intensity at four angles (0°, 45°, 90°, 135°), computes Stokes
  S₀ / S₁ / S₂, and derives DoLP and angle-of-polarization (AoP).
* DoFP polarization camera (Sony IMX250MZR or similar) — the
  driver is given a four-pixel polarizer-on-CMOS reading and
  computes the same Stokes parameters with no moving parts.

The interface is the same: a callable ``intensity_at_angle(theta)``
that returns a scalar. Mock mode generates a partially-polarised
beam and returns the corresponding intensities.

Mock readings
-------------
The mock signal is a partially-polarised source whose **degree of
linear polarization (DoLP)** drifts slowly through the day and
whose **angle of polarization (AoP)** rotates with the sun. This is
not a precise atmospheric model — it's a plausible diurnal pattern
so a co-located node sees coherent polarization data alongside
spectral data.

Confidence grade: 0.70 — DoLP / AoP are derived from four scalar
intensities; calibration matters. Lower than AS7341's 0.80 because
mechanical alignment on the rotating-polarizer setup is a real
source of error.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from sensing.firmware.sensor_drivers.base import (
    SensorDriver,
    SensorUnavailableError,
    diurnal_phase,
    jittered_baseline,
)
from bridges.hidden_channel_detector import (
    SHAPE_CHANNEL_REGISTRY,
    ShapeChannel,
)


# Default sampling angles for a rotating-polarizer scan. Four angles
# at 45° steps is the minimum that uniquely determines the linear
# Stokes parameters {S₀, S₁, S₂} (omitting S₃ — circular — which
# would require a quarter-wave plate).
_DEFAULT_SAMPLE_ANGLES_DEG: Tuple[float, ...] = (0.0, 45.0, 90.0, 135.0)


def _stokes_from_intensities(
    intensities: Sequence[float],
    angles_rad: Sequence[float],
) -> Tuple[float, float, float]:
    """Compute (S₀, S₁, S₂) from a set of polarizer-rotation
    intensities ``I(theta) = (S₀ + S₁ cos 2θ + S₂ sin 2θ) / 2``.

    Uses a least-squares fit so the same code handles three or more
    sample angles (more samples = lower noise sensitivity)."""
    if len(intensities) < 3:
        raise ValueError(
            "need at least three intensity samples to recover S₀..S₂"
        )

    n = len(intensities)
    s0_sum = 0.0
    s1_num = 0.0
    s1_den = 0.0
    s2_num = 0.0
    s2_den = 0.0
    for I, theta in zip(intensities, angles_rad):
        s0_sum += 2.0 * I  # I = (S₀ + …)/2  → 2I = S₀ + S₁cos2θ + S₂sin2θ
        c2 = math.cos(2.0 * theta)
        s2 = math.sin(2.0 * theta)
        s1_num += 2.0 * I * c2
        s2_num += 2.0 * I * s2
        s1_den += c2 * c2
        s2_den += s2 * s2

    s0 = s0_sum / n
    s1 = s1_num / s1_den if s1_den > 0 else 0.0
    s2 = s2_num / s2_den if s2_den > 0 else 0.0
    return s0, s1, s2


def _dolp_aop(s0: float, s1: float, s2: float) -> Tuple[float, float]:
    """Degree of linear polarization and angle of polarization in
    radians. DoLP ∈ [0, 1]; AoP ∈ [-π/2, π/2]."""
    if s0 <= 0:
        return 0.0, 0.0
    dolp = math.sqrt(s1 * s1 + s2 * s2) / s0
    dolp = max(0.0, min(1.0, dolp))
    aop = 0.5 * math.atan2(s2, s1)
    return dolp, aop


class RotatingPolarizerDriver(SensorDriver):
    """Driver for a rotating-polarizer + photodiode stack."""

    device_name = "RotatingPolarizer"
    confidence_grade = 0.70

    def __init__(
        self,
        channel: str = "primary",
        intensity_at_angle: Optional[Callable[[float], float]] = None,
        sample_angles_deg: Sequence[float] = _DEFAULT_SAMPLE_ANGLES_DEG,
        peak_intensity: float = 1.0,
        mock: Optional[bool] = None,
        seed: Optional[int] = None,
    ) -> None:
        """
        Parameters
        ----------
        intensity_at_angle
            Callable returning the photodiode reading at one
            polarizer angle (in *radians*). The driver rotates and
            samples; ``None`` forces mock mode.
        sample_angles_deg
            Sequence of polarizer angles in *degrees*. Default
            (0, 45, 90, 135) is the minimum 4-point scan that
            recovers S₀, S₁, S₂ uniquely.
        peak_intensity
            Calibration: noon-time beam intensity for mock mode.
        """
        self._intensity_at_angle = intensity_at_angle
        self._sample_angles_deg = tuple(sample_angles_deg)
        self._peak_intensity = peak_intensity
        super().__init__(channel=channel, mock=mock, seed=seed)

    def _open(self) -> None:
        if self._intensity_at_angle is None:
            raise SensorUnavailableError(
                "no intensity_at_angle callable supplied — pass one or set mock=True"
            )

    # ------------------------------------------------------------------
    # SupportsShapeChannels — tell the audit engine what we expose
    # ------------------------------------------------------------------

    def shape_channels(self) -> List[ShapeChannel]:
        """This driver advertises the *linear* polarization channel
        (S₀ + S₁ + S₂ — three DoFs). The full Stokes 4-DoF channel
        is reserved for a quarter-wave-plate setup that this driver
        does not measure."""
        return [SHAPE_CHANNEL_REGISTRY["polarization_linear"]]

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def _sample_intensities(self) -> List[float]:
        if self.mock:
            return self._mock_intensities()
        try:
            assert self._intensity_at_angle is not None
            return [
                float(self._intensity_at_angle(math.radians(theta)))
                for theta in self._sample_angles_deg
            ]
        except Exception as exc:  # noqa: BLE001
            raise SensorUnavailableError(str(exc)) from exc

    def _mock_intensities(self) -> List[float]:
        # Diurnal envelope identical to the spectrum driver.
        envelope = max(0.0, 0.5 * (1.0 - diurnal_phase()))
        envelope = envelope * envelope * (3.0 - 2.0 * envelope)

        # Synthetic polarization state: DoLP varies sinusoidally
        # through the day, AoP rotates with the sun.
        dolp_target = 0.20 + 0.40 * envelope
        aop_target = math.radians(180.0 * envelope - 90.0)

        s0 = self._peak_intensity * envelope
        s1 = s0 * dolp_target * math.cos(2.0 * aop_target)
        s2 = s0 * dolp_target * math.sin(2.0 * aop_target)

        intensities: List[float] = []
        for theta in self._sample_angles_deg:
            theta_rad = math.radians(theta)
            ideal = 0.5 * (
                s0
                + s1 * math.cos(2.0 * theta_rad)
                + s2 * math.sin(2.0 * theta_rad)
            )
            intensities.append(
                jittered_baseline(self._rng, ideal, abs(ideal) * 0.02 + 0.001)
            )
        return intensities

    def _read_real(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        intensities = self._sample_intensities()
        return self._summarise(intensities)

    def _read_mock(self) -> Tuple[Dict[str, float], Dict[str, float], str]:
        intensities = self._mock_intensities()
        return self._summarise(intensities)

    def _summarise(
        self, intensities: Sequence[float],
    ) -> Tuple[Dict[str, float], Dict[str, float], str]:
        angles_rad = tuple(math.radians(d) for d in self._sample_angles_deg)
        s0, s1, s2 = _stokes_from_intensities(intensities, angles_rad)
        dolp, aop_rad = _dolp_aop(s0, s1, s2)
        values = {
            "intensity":   round(s0, 4),
            "dolp":        round(dolp, 4),
            "aop_degrees": round(math.degrees(aop_rad), 3),
        }
        raw = {
            "S0": round(s0, 6),
            "S1": round(s1, 6),
            "S2": round(s2, 6),
            **{
                f"I_{int(d)}deg": round(I, 6)
                for d, I in zip(self._sample_angles_deg, intensities)
            },
        }
        # Note carries the shape-channel name so downstream code that
        # only reads the line-format Primitive (no in-memory readings)
        # can still tell this measurement carries hidden-channel info.
        return values, raw, "shape_channel=polarization_linear"


__all__ = [
    "RotatingPolarizerDriver",
    "_stokes_from_intensities",
    "_dolp_aop",
]
