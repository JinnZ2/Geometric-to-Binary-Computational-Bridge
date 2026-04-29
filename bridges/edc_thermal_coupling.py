"""
edc_thermal_coupling — endocrine-disruption × thermal amplifier.

The recognition note in ``docs/hidden_channel_pattern.md`` flags this
as instance #2 of the substrate-as-signal pattern: an environmental
endocrine-disrupting compound (EDC) at sub-physiological
concentration redirects a hormone signaling cascade by mimicking the
hormone's binding *geometry* — concentration-as-scalar misses it.
Climate warming amplifies the effect by raising the lipid-tissue
partition coefficient, lowering the apparent Kd, and pushing
previously-safe environmental concentrations onto the steep part of
the dose-response curve.

This module wires that physics into runtime code. Three layers:

* **Static physics** — :func:`partition_coefficient`, :func:`apparent_Kd`,
  :func:`receptor_occupancy`, :func:`cascade_leverage`. The leverage
  is the "whisper redirects hurricane" scalar — the d(occupancy)/
  d(log [EDC]) sensitivity that peaks near Kd. Pure functions, no
  state.

* **Coupled ODE** — :func:`step_forward` and :func:`simulate`. The
  evolving variable is the lipid-tissue EDC concentration; the
  forcing terms are the environmental concentration profile and a
  time-varying ambient temperature. Steady state recovers the
  partition relation analytically; the ODE is what catches the
  *transient* — a heat wave or a pulse release that lifts tissue
  burden before the population can adapt.

* **Hidden-channel hookup** — :class:`EDCThermalCouplingDiagnostic`
  implements the
  :class:`~bridges.hidden_channel_detector.SupportsShapeChannels`
  protocol, returning the ``hormone_geometry`` channel. Any audit
  pass over a system that ingests this diagnostic will flag the
  scalar-concentration model as insufficient automatically.

The module produces a :class:`EDCThermalCouplingDiagnostic` rather
than a :class:`~sensing.processing.primitives_encoder.Primitive`
because the natural input here is a model, not a sensor — but a
node measuring [EDC]_tissue can build Primitives that feed back
into ``simulate``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

from bridges.hidden_channel_detector import (
    SHAPE_CHANNEL_REGISTRY,
    ShapeChannel,
)


# Universal gas constant (J / mol·K). Local to keep the module
# self-contained; importing scipy.constants would pull a dep we
# don't need here.
_R_GAS = 8.314_462_618


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class EDCConfig:
    """Parameters of one endocrine-disrupting compound.

    Defaults are deliberately blank so an EDC must be characterised
    by name and explicit parameters — the failure mode this module
    is built to catch is *unnamed* compounds slipping into the
    pipeline at "safe" doses.

    Attributes
    ----------
    name
        Short identifier (``"BPA"``, ``"DDT"``, ``"PFOA"``).
    Kd_intrinsic_M
        Intrinsic dissociation constant of the EDC at the receptor,
        measured under reference conditions, in molar units. Pulled
        from in-vitro biochemistry data.
    log_P
        Octanol-water partition coefficient (log10) — the standard
        lipophilicity scale. log_P = 0 means equal partitioning;
        log_P > 4 means strong tissue accumulation.
    enthalpy_partition_kJ_per_mol
        ΔH for partitioning into lipid (kJ/mol). Positive values
        mean partitioning *increases* with temperature (the climate
        amplifier the recognition note flags).
    receptor_target
        Free-form label for the target receptor
        (``"estrogen"``, ``"thyroid"``, ``"androgen"``).
    """

    name: str
    Kd_intrinsic_M: float
    log_P: float
    enthalpy_partition_kJ_per_mol: float = 25.0
    receptor_target: str = "unspecified"


@dataclass(frozen=True)
class ThermalContext:
    """Environmental thermal state at a moment.

    ``temperature_K`` is the body-tissue temperature (mammalian
    constant ≈ 310 K, ectotherm tracks ambient). ``ambient_K`` is
    the environmental temperature; for ectotherms they're the same,
    for endotherms they decouple but the partition shift still
    happens because the *environmental* compartment of the
    partition equilibrium follows ambient.
    """

    temperature_K: float
    ambient_K: float
    reference_K: float = 298.15  # 25 °C — standard EDC characterisation T


@dataclass
class EDCThermalCouplingState:
    """Mutable state evolved by the ODE."""

    edc: EDCConfig
    thermal: ThermalContext
    env_concentration_M: float
    """Ambient (environmental) EDC concentration."""

    tissue_concentration_M: float = 0.0
    """Lipid-tissue EDC concentration. Evolves under :func:`step_forward`."""

    tissue_volume_fraction_lipid: float = 0.10
    """Fraction of total tissue volume that is lipid (default 10 %
    for typical mammalian, higher for cetaceans)."""

    k_in_per_s: float = 1e-4
    """Forward-rate constant for environment → tissue partitioning,
    at reference T. The temperature scaling lives in
    :func:`partition_coefficient`."""

    k_out_per_s: float = 1e-4
    """Reverse-rate constant for tissue → environment. Together with
    ``k_in_per_s`` this sets the time-to-equilibrium (~ 1 / k_out)."""


# ----------------------------------------------------------------------
# Static physics
# ----------------------------------------------------------------------

def partition_coefficient(
    edc: EDCConfig, thermal: ThermalContext,
) -> float:
    """Tissue-to-water partition coefficient with thermal correction.

    Van't Hoff relation:

      P(T) = P_ref · exp(- ΔH / R · (1/T − 1/T_ref))

    A positive ΔH (the EDC default) means the partition coefficient
    *grows* with temperature — the climate amplifier from the
    recognition note. Returns the dimensionless ratio
    [tissue]/[water] at thermodynamic equilibrium.
    """
    p_ref = 10 ** float(edc.log_P)
    delta_h_j = edc.enthalpy_partition_kJ_per_mol * 1000.0
    one_over_t = 1.0 / thermal.temperature_K - 1.0 / thermal.reference_K
    return p_ref * math.exp(-delta_h_j / _R_GAS * one_over_t)


def apparent_Kd(
    edc: EDCConfig, thermal: ThermalContext,
) -> float:
    """Effective Kd from the receptor's perspective.

    Higher partition → more EDC reaches the receptor at a given
    environmental concentration → the *apparent* dose-response curve
    shifts left, even though the molecular Kd hasn't changed::

        Kd_apparent = Kd_intrinsic / P(T)
    """
    p = partition_coefficient(edc, thermal)
    if p <= 0:
        return float("inf")
    return edc.Kd_intrinsic_M / p


def receptor_occupancy(state: EDCThermalCouplingState) -> float:
    """Hill equation with cooperativity n=1 (simplest case).

    Occupancy ∈ [0, 1]; 0.5 sits at apparent Kd.
    """
    L = max(0.0, state.tissue_concentration_M)
    Kd = apparent_Kd(state.edc, state.thermal)
    if math.isinf(Kd):
        return 0.0
    return L / (Kd + L)


def cascade_leverage(state: EDCThermalCouplingState) -> float:
    """The "whisper redirects hurricane" sensitivity.

    Mathematically: d(occupancy) / d(log10 [EDC]_env). For a Hill-1
    response this peaks at occupancy = 0.5 with the analytic value::

        ln(10) · occ · (1 − occ)
        max ≈ 0.5757 at occ = 0.5

    A high leverage means a small change in environmental
    concentration produces a large change in cascade firing. This
    is the regime where "previously safe" concentrations become
    biologically active, and what the recognition note calls out as
    a low-amplitude / high-leverage marker the audit engine should
    surface automatically.
    """
    occ = receptor_occupancy(state)
    return math.log(10) * occ * (1.0 - occ)


def steady_state_tissue_concentration(state: EDCThermalCouplingState) -> float:
    """Closed-form tissue concentration at thermal/transport equilibrium.

    Setting ``dC_tissue/dt = 0`` in the ODE below recovers::

        C_tissue_ss = (k_in / k_out) · P(T) · φ_lipid · C_env
    """
    if state.k_out_per_s <= 0:
        return float("inf")
    p = partition_coefficient(state.edc, state.thermal)
    return (
        state.k_in_per_s
        / state.k_out_per_s
        * p
        * state.tissue_volume_fraction_lipid
        * state.env_concentration_M
    )


# ----------------------------------------------------------------------
# Coupled ODE
# ----------------------------------------------------------------------

def step_forward(
    state: EDCThermalCouplingState,
    dt_seconds: float,
    *,
    env_at_time: Optional[Callable[[float, EDCThermalCouplingState], float]] = None,
    temperature_at_time: Optional[Callable[[float, EDCThermalCouplingState], float]] = None,
    t_seconds: float = 0.0,
) -> EDCThermalCouplingState:
    """One forward-Euler step of the coupled ODE.

    The evolving variable is ``state.tissue_concentration_M``.
    The forcing terms are the (possibly time-varying) environmental
    concentration and ambient temperature::

        dC_tissue/dt = k_in · P(T(t)) · φ_lipid · C_env(t)
                     − k_out · C_tissue

    For a one-shot snapshot pass ``env_at_time = None`` and
    ``temperature_at_time = None`` — the state's current values are
    held constant for the step. For a heat-wave or pulse-release
    simulation pass closures over your scenario.

    Returns a new :class:`EDCThermalCouplingState`; the input is
    not mutated.
    """
    if dt_seconds <= 0:
        raise ValueError(f"dt_seconds must be > 0; got {dt_seconds!r}")

    if env_at_time is not None:
        new_env = float(env_at_time(t_seconds, state))
    else:
        new_env = state.env_concentration_M

    if temperature_at_time is not None:
        new_temp = float(temperature_at_time(t_seconds, state))
        thermal = ThermalContext(
            temperature_K=new_temp,
            ambient_K=new_temp,
            reference_K=state.thermal.reference_K,
        )
    else:
        thermal = state.thermal

    p = partition_coefficient(state.edc, thermal)
    flux_in = (
        state.k_in_per_s * p
        * state.tissue_volume_fraction_lipid * new_env
    )
    flux_out = state.k_out_per_s * state.tissue_concentration_M
    new_tissue = max(
        0.0,
        state.tissue_concentration_M + dt_seconds * (flux_in - flux_out),
    )

    return EDCThermalCouplingState(
        edc=state.edc,
        thermal=thermal,
        env_concentration_M=new_env,
        tissue_concentration_M=new_tissue,
        tissue_volume_fraction_lipid=state.tissue_volume_fraction_lipid,
        k_in_per_s=state.k_in_per_s,
        k_out_per_s=state.k_out_per_s,
    )


def simulate(
    initial: EDCThermalCouplingState,
    *,
    t_total_seconds: float,
    dt_seconds: float = 60.0,
    env_at_time: Optional[Callable[[float, EDCThermalCouplingState], float]] = None,
    temperature_at_time: Optional[Callable[[float, EDCThermalCouplingState], float]] = None,
) -> "EDCThermalCouplingDiagnostic":
    """Integrate the coupled ODE forward and return a diagnostic.

    The diagnostic carries the trajectory (per-step states +
    occupancy + leverage) plus summary statistics, plus the
    ``hormone_geometry`` shape-channel declaration.
    """
    if t_total_seconds <= 0 or dt_seconds <= 0:
        raise ValueError("t_total_seconds and dt_seconds must be > 0")

    n_steps = int(round(t_total_seconds / dt_seconds))

    state = initial
    times: List[float] = []
    states: List[EDCThermalCouplingState] = []
    occupancies: List[float] = []
    leverages: List[float] = []

    t = 0.0
    for _ in range(n_steps):
        times.append(t)
        states.append(state)
        occupancies.append(receptor_occupancy(state))
        leverages.append(cascade_leverage(state))

        state = step_forward(
            state, dt_seconds,
            env_at_time=env_at_time,
            temperature_at_time=temperature_at_time,
            t_seconds=t,
        )
        t += dt_seconds

    # Final point
    times.append(t)
    states.append(state)
    occupancies.append(receptor_occupancy(state))
    leverages.append(cascade_leverage(state))

    return EDCThermalCouplingDiagnostic(
        edc=initial.edc,
        times_seconds=tuple(times),
        states=tuple(states),
        occupancies=tuple(occupancies),
        leverages=tuple(leverages),
    )


# ----------------------------------------------------------------------
# Diagnostic + hidden-channel hookup
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class EDCThermalCouplingDiagnostic:
    """Full result of an :func:`simulate` run."""

    edc: EDCConfig
    times_seconds: Tuple[float, ...]
    states: Tuple[EDCThermalCouplingState, ...]
    occupancies: Tuple[float, ...]
    leverages: Tuple[float, ...]

    # ------------------------------------------------------------------
    # SupportsShapeChannels — flag the hidden channel
    # ------------------------------------------------------------------

    def shape_channels(self) -> List[ShapeChannel]:
        """Advertise the ``hormone_geometry`` channel so a hidden-
        channel audit over this diagnostic flags scalar-concentration
        models as insufficient."""
        return [SHAPE_CHANNEL_REGISTRY["hormone_geometry"]]

    # ------------------------------------------------------------------
    # Summary statistics
    # ------------------------------------------------------------------

    @property
    def peak_occupancy(self) -> float:
        return max(self.occupancies) if self.occupancies else 0.0

    @property
    def peak_leverage(self) -> float:
        return max(self.leverages) if self.leverages else 0.0

    @property
    def time_in_high_leverage_regime_seconds(self) -> float:
        """Total time spent with leverage > 0.4 (i.e. occupancy in
        roughly the steepest 40 % of the dose-response curve)."""
        if len(self.times_seconds) < 2:
            return 0.0
        dt_seconds = self.times_seconds[1] - self.times_seconds[0]
        return sum(dt_seconds for L in self.leverages if L > 0.4)

    def summary(self) -> str:
        if not self.states:
            return "EDCThermalCouplingDiagnostic(<empty>)"
        first = self.states[0]
        last = self.states[-1]
        return (
            f"EDC: {self.edc.name} (target={self.edc.receptor_target}, "
            f"Kd={self.edc.Kd_intrinsic_M:.2e} M, log_P={self.edc.log_P})\n"
            f"  T span: {first.thermal.temperature_K:.1f} K → "
            f"{last.thermal.temperature_K:.1f} K\n"
            f"  [EDC]_env span: {first.env_concentration_M:.2e} → "
            f"{last.env_concentration_M:.2e} M\n"
            f"  [EDC]_tissue: {first.tissue_concentration_M:.2e} → "
            f"{last.tissue_concentration_M:.2e} M\n"
            f"  Peak occupancy: {self.peak_occupancy:.3f}\n"
            f"  Peak leverage:  {self.peak_leverage:.3f}\n"
            f"  Time in high-leverage regime: "
            f"{self.time_in_high_leverage_regime_seconds:.0f} s\n"
            f"  Hidden channel: hormone_geometry "
            f"(scalar [EDC] model insufficient)"
        )


__all__ = [
    "EDCConfig",
    "ThermalContext",
    "EDCThermalCouplingState",
    "EDCThermalCouplingDiagnostic",
    "partition_coefficient",
    "apparent_Kd",
    "receptor_occupancy",
    "cascade_leverage",
    "steady_state_tissue_concentration",
    "step_forward",
    "simulate",
]
