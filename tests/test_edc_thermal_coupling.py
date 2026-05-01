"""
tests/test_edc_thermal_coupling.py
==================================

Covers the EDC × heat coupled-ODE module — the recognition note's
instance #2 of the substrate-as-signal pattern, now wired into
runtime code.

Three test groupings:

* **Static physics** — Van't Hoff thermal correction, Hill-equation
  occupancy, leverage analytic peak.
* **Coupled ODE** — steady-state recovery, transient under a
  heat-wave temperature ramp, mass conservation under no forcing.
* **Hidden-channel hookup** — the diagnostic advertises
  ``hormone_geometry`` and the detector flags scalar-model
  insufficiency. End-to-end: a Primitive ``claim_ref="edc_thermal"``
  verifies cleanly against the shipped CLAIM_TABLE.
"""

from __future__ import annotations

import math
import unittest
from typing import Optional

from bridges.edc_thermal_coupling import (
    EDCConfig,
    EDCThermalCouplingDiagnostic,
    EDCThermalCouplingState,
    ThermalContext,
    apparent_Kd,
    cascade_leverage,
    partition_coefficient,
    receptor_occupancy,
    simulate,
    steady_state_tissue_concentration,
    step_forward,
)
from bridges.hidden_channel_detector import (
    detect_hidden_channels,
    shape_channels_of,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bpa(log_P: float = 3.3, dh: float = 20.0, kd: float = 1e-7) -> EDCConfig:
    """Bisphenol-A-shaped representative EDC."""
    return EDCConfig(
        name="BPA",
        Kd_intrinsic_M=kd,
        log_P=log_P,
        enthalpy_partition_kJ_per_mol=dh,
        receptor_target="estrogen",
    )


def _state_at(
    edc: EDCConfig,
    temperature_K: float,
    env_M: float,
    *,
    initial_tissue_M: Optional[float] = None,
    k_in: float = 1e-4,
    k_out: float = 1e-4,
) -> EDCThermalCouplingState:
    thermal = ThermalContext(temperature_K=temperature_K, ambient_K=temperature_K)
    state = EDCThermalCouplingState(
        edc=edc, thermal=thermal,
        env_concentration_M=env_M,
        k_in_per_s=k_in, k_out_per_s=k_out,
    )
    if initial_tissue_M is not None:
        state.tissue_concentration_M = initial_tissue_M
    return state


# ---------------------------------------------------------------------------
# Static physics
# ---------------------------------------------------------------------------

class TestStaticPhysics(unittest.TestCase):

    def test_partition_grows_with_temperature_when_dh_positive(self):
        edc = _bpa(dh=20.0)
        cool = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        warm = ThermalContext(temperature_K=308.15, ambient_K=308.15)
        self.assertGreater(
            partition_coefficient(edc, warm),
            partition_coefficient(edc, cool),
        )

    def test_partition_shrinks_with_temperature_when_dh_negative(self):
        # Some compounds have negative ΔH — partition decreases as
        # T rises. The model should respect the sign without special-
        # casing; this catches a sign bug if anyone "fixes" the
        # exponent direction.
        edc = _bpa(dh=-20.0)
        cool = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        warm = ThermalContext(temperature_K=308.15, ambient_K=308.15)
        self.assertLess(
            partition_coefficient(edc, warm),
            partition_coefficient(edc, cool),
        )

    def test_partition_at_reference_T_equals_10_to_logP(self):
        edc = _bpa(log_P=4.0)
        ref = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        self.assertAlmostEqual(
            partition_coefficient(edc, ref), 10000.0, places=2,
        )

    def test_occupancy_is_one_half_at_apparent_Kd(self):
        edc = _bpa()
        thermal = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        Kd = apparent_Kd(edc, thermal)
        state = _state_at(
            edc, thermal.temperature_K, env_M=0.0,
            initial_tissue_M=Kd,
        )
        self.assertAlmostEqual(receptor_occupancy(state), 0.5, places=6)

    def test_occupancy_in_zero_one(self):
        edc = _bpa()
        for tissue in (0.0, 1e-15, 1e-10, 1.0, 1e3):
            state = _state_at(
                edc, 298.15, env_M=0.0, initial_tissue_M=tissue,
            )
            occ = receptor_occupancy(state)
            self.assertGreaterEqual(occ, 0.0)
            self.assertLessEqual(occ, 1.0)


class TestCascadeLeverage(unittest.TestCase):
    """The "whisper redirects hurricane" sensitivity peaks at
    occupancy = 0.5 with the analytic value ln(10)/4 ≈ 0.5757."""

    def test_leverage_peaks_at_half_occupancy(self):
        edc = _bpa()
        thermal = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        Kd = apparent_Kd(edc, thermal)

        # Sample tissue concentrations spanning Kd × 1e-3 to Kd × 1e3.
        max_lev = 0.0
        max_occ = -1.0
        for log_factor in range(-30, 31):
            tissue = Kd * math.pow(10.0, log_factor / 10.0)
            state = _state_at(
                edc, thermal.temperature_K, env_M=0.0,
                initial_tissue_M=tissue,
            )
            lev = cascade_leverage(state)
            if lev > max_lev:
                max_lev = lev
                max_occ = receptor_occupancy(state)

        # Analytic peak: ln(10) * 0.5 * 0.5 = ln(10) / 4 ≈ 0.5757
        self.assertAlmostEqual(max_lev, math.log(10) / 4.0, places=4)
        self.assertAlmostEqual(max_occ, 0.5, places=2)

    def test_leverage_low_in_saturation(self):
        # Far above Kd → occupancy → 1 → leverage → 0.
        edc = _bpa()
        Kd = apparent_Kd(
            edc, ThermalContext(temperature_K=298.15, ambient_K=298.15),
        )
        state = _state_at(
            edc, 298.15, env_M=0.0, initial_tissue_M=Kd * 10_000,
        )
        self.assertLess(cascade_leverage(state), 1e-3)

    def test_leverage_low_below_threshold(self):
        # Far below Kd → occupancy → 0 → leverage → 0.
        edc = _bpa()
        Kd = apparent_Kd(
            edc, ThermalContext(temperature_K=298.15, ambient_K=298.15),
        )
        state = _state_at(
            edc, 298.15, env_M=0.0, initial_tissue_M=Kd / 10_000,
        )
        self.assertLess(cascade_leverage(state), 1e-3)


# ---------------------------------------------------------------------------
# Coupled ODE
# ---------------------------------------------------------------------------

class TestCoupledODE(unittest.TestCase):

    def test_steady_state_recovers_partition_relation(self):
        edc = _bpa()
        thermal = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        env = 1e-10
        state = EDCThermalCouplingState(
            edc=edc, thermal=thermal, env_concentration_M=env,
            tissue_volume_fraction_lipid=0.10,
            k_in_per_s=1e-3, k_out_per_s=1e-3,
        )
        # Run for 8 τ (τ = 1/k_out = 1000 s) so the forward-Euler
        # transient is well decayed (1 - e^-8 ≈ 99.97 % approach).
        result = simulate(
            state, t_total_seconds=8000, dt_seconds=5.0,
        )
        analytic = steady_state_tissue_concentration(state)
        final = result.states[-1].tissue_concentration_M
        self.assertAlmostEqual(final / analytic, 1.0, places=2)

    def test_heat_wave_raises_tissue_burden(self):
        edc = _bpa(dh=25.0)  # solid positive ΔH
        state = _state_at(edc, 298.15, env_M=1e-10)
        state.tissue_concentration_M = steady_state_tissue_concentration(state)
        baseline = state.tissue_concentration_M

        # Ramp ambient from 25 °C to 35 °C linearly over 1 day.
        def temp_ramp(t, _state):
            return 298.15 + 10.0 * (t / 86400.0)

        result = simulate(
            state, t_total_seconds=86400, dt_seconds=600.0,
            temperature_at_time=temp_ramp,
        )
        warmed = result.states[-1].tissue_concentration_M
        self.assertGreater(warmed, baseline)

    def test_no_forcing_no_drift(self):
        # With env=0 and tissue=0, nothing should happen.
        edc = _bpa()
        state = _state_at(edc, 298.15, env_M=0.0, initial_tissue_M=0.0)
        result = simulate(state, t_total_seconds=3600, dt_seconds=60.0)
        for s in result.states:
            self.assertEqual(s.tissue_concentration_M, 0.0)

    def test_negative_dt_rejected(self):
        edc = _bpa()
        state = _state_at(edc, 298.15, env_M=1e-10)
        with self.assertRaises(ValueError):
            step_forward(state, -1.0)
        with self.assertRaises(ValueError):
            simulate(state, t_total_seconds=-1, dt_seconds=1)
        with self.assertRaises(ValueError):
            simulate(state, t_total_seconds=10, dt_seconds=-1)

    def test_step_forward_does_not_mutate_input(self):
        edc = _bpa()
        state = _state_at(edc, 298.15, env_M=1e-10, initial_tissue_M=1e-12)
        before = state.tissue_concentration_M
        _ = step_forward(state, 1.0)
        self.assertEqual(state.tissue_concentration_M, before)


# ---------------------------------------------------------------------------
# Hidden-channel hookup
# ---------------------------------------------------------------------------

class TestHiddenChannelHookup(unittest.TestCase):

    def test_diagnostic_advertises_hormone_geometry(self):
        edc = _bpa()
        state = _state_at(edc, 298.15, env_M=1e-10)
        result = simulate(state, t_total_seconds=600, dt_seconds=60.0)
        channels = shape_channels_of(result)
        names = [c.name for c in channels]
        self.assertIn("hormone_geometry", names)

    def test_detector_flags_scalar_concentration_insufficient(self):
        edc = _bpa()
        state = _state_at(edc, 298.15, env_M=1e-10)
        result = simulate(state, t_total_seconds=600, dt_seconds=60.0)
        report = detect_hidden_channels(result, claimed_channel="concentration")
        self.assertFalse(report.scalar_sufficient)
        self.assertIn(
            "hormone_geometry",
            [c.name for c in report.hidden_channels],
        )


# ---------------------------------------------------------------------------
# CLAIM_SCHEMA bridge
# ---------------------------------------------------------------------------

class TestEDCClaim(unittest.TestCase):

    def test_edc_thermal_claim_present_in_shipped_table(self):
        import CLAIM_SCHEMA as cs
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent
        claims = cs.read_claims(repo_root / ".claims")
        ids = {c["id"] for c in claims}
        self.assertIn("edc_thermal", ids)

    def test_edc_thermal_claim_lists_hormone_geometry_in_cond(self):
        import CLAIM_SCHEMA as cs
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent
        claim = next(
            c for c in cs.read_claims(repo_root / ".claims")
            if c["id"] == "edc_thermal"
        )
        self.assertIn("shape_channel_hormone_geometry", claim["cond"])

    def test_edc_thermal_claim_uses_generational_cycle(self):
        # Cross-generational reach is one of the recognition note's
        # specific signatures of the EDC pattern. The cycle enum
        # value 4 = "generational".
        import CLAIM_SCHEMA as cs
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent
        claim = next(
            c for c in cs.read_claims(repo_root / ".claims")
            if c["id"] == "edc_thermal"
        )
        self.assertEqual(claim["cyc"], 4)


# ---------------------------------------------------------------------------
# Whisper-redirects-hurricane: dose-response sweep at fixed T
# ---------------------------------------------------------------------------

class TestWhisperRegime(unittest.TestCase):
    """The recognition note's headline phenomenon: a small change in
    environmental concentration produces a *large* change in cascade
    output, but only when the operating point sits near apparent Kd.
    Demonstrates that the leverage scalar correctly identifies that
    regime."""

    def test_doubling_env_in_whisper_regime_doubles_occupancy_response(self):
        edc = _bpa()
        thermal = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        Kd = apparent_Kd(edc, thermal)

        # Deep linear regime: tissue ≪ Kd so Hill-1 is approximately
        # linear in [L]/Kd. At 0.01 × Kd vs 0.02 × Kd the doubling
        # is preserved to within 1 %.
        state_low = _state_at(
            edc, thermal.temperature_K, env_M=0.0,
            initial_tissue_M=0.01 * Kd,
        )
        state_double = _state_at(
            edc, thermal.temperature_K, env_M=0.0,
            initial_tissue_M=0.02 * Kd,
        )
        ratio = (
            receptor_occupancy(state_double)
            / receptor_occupancy(state_low)
        )
        # Should be very close to 2.
        self.assertAlmostEqual(ratio, 2.0, delta=0.05)

    def test_doubling_env_in_saturation_barely_moves_occupancy(self):
        # In saturation (tissue ≫ Kd), doubling concentration barely
        # changes occupancy.
        edc = _bpa()
        thermal = ThermalContext(temperature_K=298.15, ambient_K=298.15)
        Kd = apparent_Kd(edc, thermal)

        occ_a = receptor_occupancy(_state_at(
            edc, thermal.temperature_K, env_M=0.0,
            initial_tissue_M=Kd * 1000,
        ))
        occ_b = receptor_occupancy(_state_at(
            edc, thermal.temperature_K, env_M=0.0,
            initial_tissue_M=Kd * 2000,
        ))
        # Both ≈ 1; the difference is < 0.001.
        self.assertLess(abs(occ_a - occ_b), 0.001)


if __name__ == "__main__":
    unittest.main()
