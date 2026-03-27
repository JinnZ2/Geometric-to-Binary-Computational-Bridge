"""
Magnetic Bridge Comparator
==========================
Runs both modes of MagneticBridgeEncoder on the same magnetic source
and measures consistency between the macroscopic geometry and spin-wave
physics representations.

The diversity signal
--------------------
Geometric mode encodes *shape* (field-line curvature, Biot-Savart geometry).
Magnonic mode encodes *dynamics* (group velocity, thermal occupation, damping).
These are genuinely different views of the same physical source.

  Consistent    → macroscopic geometry predicts spin-wave physics correctly.
                  Stable, well-characterised magnetic state.
  Minor divergence → one dimension disagrees.  Interesting but not anomalous.
  Major divergence → two or more dimensions disagree.  Possible phase
                  transition, topological defect, or non-equilibrium state.
                  Trigger the emotion/consciousness drill loop.

Compared dimensions
-------------------
  B field (weight 0.5)  — geometric B_mean vs magnonic B_eff(k_dipolar)
                          Both encoded with _B_BANDS Gray codes → direct
                          band-level and Hamming comparison.
  Pressure (weight 0.3) — geometric magnetic pressure (B²/2μ₀) vs
                          magnonic energy density (n_thermal · ℏω).
                          Both are J/m³; compared via _PRESSURE_BANDS.
  Resonance/thermal (weight 0.2) — geometric resonance_map sign vs
                          magnonic thermal regime.  Classical (many magnons)
                          → expect constructive resonance; quantum (few)
                          → expect destructive.  Neutral 0.5 if no resonance_map.

Pressure section — two branches
--------------------------------
  P_applied branch  — compare geometric B_mean pressure vs magnonic H0 pressure.
    Both use P = B²/2μ₀ with their respective B values.  Direct apples-to-apples
    check: did the geometric field-line encoder see the same applied field that
    drove the magnonic mode?

  E_density branch  — compare geometric pressure vs volumetric magnon energy
    density E_density = n_thermal · ℏω / l_ex³  (J/m³ = Pa).
    Normalising by 1/l_ex³ converts "energy per mode" to "energy per unit volume"
    using the exchange length as the natural mode volume scale.
    This branch asks: is the thermal magnon energy density significant relative
    to the field energy density?  Near a phase transition / KT crossing it will
    be; deep in the ordered phase it will be many orders of magnitude smaller.
    A P_thermal_band_match=True is therefore a proximity-to-transition signal.

KT / φ flag
-----------
When the dimensionless exchange ratio J* = A_ex · l_ex / (k_B · T) is within
15 % of φ ≈ 1.618 the system sits near the golden-ratio KT resonance point —
the same attractor that the KT annealer in Engine/kt_annealer.py stabilises.
For typical materials this only occurs near the Curie temperature, so kt_phi_match
is a proximity-to-phase-transition indicator, not a room-temperature signal.
This flag is reported but does not alter the consistency score.

Usage
-----
  from bridges.magnetic_comparator import MagneticBridgeComparator

  cmp = MagneticBridgeComparator()
  result = cmp.compare(
      geometric_geometry = {
          "field_lines": [{"direction": "N", "curvature": 0.3, "magnitude": 0.05}],
          "resonance_map": [0.6, -0.2],
      },
      magnonic_geometry = {"material": "YIG", "H0": 0.05, "T": 300.0},
  )
  print(result["consistency_score"], result["interpretation"])
"""

import math
from bridges.magnetic_encoder import (
    MagneticBridgeEncoder,
    _gray_bits, _B_BANDS, _PRESSURE_BANDS, _GAMMA,
    magnetic_pressure,
)

_PHI    = (1.0 + math.sqrt(5.0)) / 2.0
_MU_0   = 4 * math.pi * 1e-7
_HBAR   = 1.0545718e-34
_K_B    = 1.380649e-23
_TWO_PI = 2.0 * math.pi


def _band_index(value: float, bands: list) -> int:
    """Return the Gray band index for a value (mirrors _gray_bits logic)."""
    idx = 0
    for i in range(len(bands) - 1, -1, -1):
        if value >= bands[i]:
            idx = i
            break
    return idx


def _hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def _resolve_magnonic_params(geo: dict) -> dict:
    """Extract material parameters from a magnonic geometry dict."""
    from Engine.magnonic_sublayer import MATERIALS
    if "material" in geo:
        p = MATERIALS[geo["material"]]
        return dict(
            M_s=p["M_s"], A_ex=p["A_ex"], alpha=p["alpha"],
            conductivity=p["conductivity"], c_sound=p["c_sound"],
            H0=float(geo.get("H0", 0.1)),
            T=float(geo.get("T", 300.0)),
            theta_deg=float(geo.get("theta_deg", 90.0)),
            thickness=float(geo.get("thickness", 1e-6)),
            n_e=float(geo.get("n_e", 0.0)),
        )
    return dict(
        M_s=float(geo.get("M_s", 1.4e5)),
        A_ex=float(geo.get("A_ex", 3.65e-12)),
        alpha=float(geo.get("alpha", 3e-5)),
        conductivity=float(geo.get("conductivity", 0.0)),
        c_sound=float(geo.get("c_sound", 5000.0)),
        H0=float(geo.get("H0", 0.1)),
        T=float(geo.get("T", 300.0)),
        theta_deg=float(geo.get("theta_deg", 90.0)),
        thickness=float(geo.get("thickness", 1e-6)),
        n_e=float(geo.get("n_e", 0.0)),
    )


class MagneticBridgeComparator:
    """
    Runs geometric and magnonic encoding on the same source and returns
    a consistency score plus per-dimension divergence flags.
    """

    def compare(self, geometric_geometry: dict,
                magnonic_geometry: dict) -> dict:
        """
        Parameters
        ----------
        geometric_geometry : dict
            Input for MagneticBridgeEncoder(mode="geometric").
        magnonic_geometry : dict
            Input for MagneticBridgeEncoder(mode="magnonic").
            Should describe the same physical source.

        Returns
        -------
        dict with keys:
          geometric_bits             str   — variable-length geometric encoding
          magnonic_bits              str   — 43-bit magnonic encoding
          B_geometric_T              float — mean |B| from field lines
          B_magnonic_dipolar_T       float — B_eff at dipolar k (ω_dip/γ)
          B_magnonic_bottom_T        float — B_eff at band bottom (ω₀/γ)
          B_band_match               bool  — same _B_BANDS Gray band
          B_hamming                  int   — 0–3 bit difference on B encoding
          P_geometric_Pa             float — magnetic pressure B_geo²/2μ₀
          P_magnonic_applied_Pa      float — magnetic pressure H0²/2μ₀ (applied field)
          E_magnonic_density_Pa      float — volumetric magnon energy n·ℏω/l_ex³  (J/m³)
          P_applied_band_match       bool  — P_geo vs P_H0 in same _PRESSURE_BANDS band
          P_applied_hamming          int   — 0–3 bit difference (applied field check)
          P_thermal_band_match       bool  — P_geo vs E_density in same band
          P_thermal_hamming          int   — 0–3 bit difference (thermal energy check)
          resonance_thermal_alignment float — [0,1]; 0.5 if no resonance_map
          thermal_regime             str   — quantum/crossover/classical/gapless
          n_thermal_exchange         float — Bose-Einstein occupation (exchange k)
          J_star                     float — dimensionless A_ex·l_ex/(k_B·T)
          kt_phi_match               bool  — |J* - φ| / φ < 0.15  (near Curie point)
          consistency_score          float — weighted [0,1]
          divergence_flags           list  — human-readable divergence descriptions
          interpretation             str   — consistent / minor_divergence / major_divergence
                                             (+ KT_phi_resonance tag if applicable)
        """
        from Engine.magnonic_sublayer import magnonic_coupling_state

        # ── Run both encoders ─────────────────────────────────────────────
        geo_enc = MagneticBridgeEncoder(mode="geometric")
        geo_enc.from_geometry(geometric_geometry)
        geo_bits = geo_enc.to_binary()

        mag_enc = MagneticBridgeEncoder(mode="magnonic")
        mag_enc.from_geometry(magnonic_geometry)
        mag_bits = mag_enc.to_binary()

        # ── Resolve parameters and compute full magnonic state ─────────────
        params = _resolve_magnonic_params(magnonic_geometry)
        state  = magnonic_coupling_state(**params)

        M_s  = params["M_s"]
        A_ex = params["A_ex"]
        T    = params["T"]

        # ── B field comparison ─────────────────────────────────────────────
        field_lines = geometric_geometry.get("field_lines", [])
        if field_lines:
            B_geo = (sum(abs(float(l.get("magnitude", 0.0))) for l in field_lines)
                     / len(field_lines))
        else:
            B_geo = 0.0

        B_mag_dipolar = (_TWO_PI * state["magnon_freq_dipolar_Hz"]) / _GAMMA
        B_mag_bottom  = (_TWO_PI * state["magnon_band_bottom_Hz"])  / _GAMMA

        geo_B_bits = _gray_bits(B_geo,         _B_BANDS)
        # Section A of magnonic bits: [bottom(3), dipolar(3), exchange(3), deep(3)]
        mag_B_bits = mag_bits[3:6]   # bits 3-5 = H_dipolar
        hamming_B  = _hamming(geo_B_bits, mag_B_bits)
        B_band_match = (
            _band_index(B_geo, _B_BANDS) == _band_index(B_mag_dipolar, _B_BANDS)
        )

        # ── Pressure section — two branches ──────────────────────────────
        H0   = params["H0"]
        l_ex = state["exchange_length_m"]

        # Branch 1: applied field pressure — direct apples-to-apples
        # Both sides use P = B²/2μ₀; compares geometric B_mean vs driven H0
        P_geo           = magnetic_pressure(B_geo)
        P_mag_applied   = magnetic_pressure(H0)

        geo_P_bits       = _gray_bits(P_geo,         _PRESSURE_BANDS)
        mag_Pa_bits      = _gray_bits(P_mag_applied, _PRESSURE_BANDS)
        hamming_P_applied = _hamming(geo_P_bits, mag_Pa_bits)
        P_applied_band_match = (
            _band_index(P_geo, _PRESSURE_BANDS) == _band_index(P_mag_applied, _PRESSURE_BANDS)
        )

        # Branch 2: volumetric magnon energy density — proximity-to-transition signal
        # E_density = n_thermal · ℏω / l_ex³  (J/m³ = Pa)
        # Near KT/Curie crossing this approaches P_geo; deep in ordered phase it is tiny
        E_density = state["magnon_energy_density_J"] / max(l_ex ** 3, 1e-30)
        mag_Pe_bits      = _gray_bits(E_density, _PRESSURE_BANDS)
        hamming_P_thermal = _hamming(geo_P_bits, mag_Pe_bits)
        P_thermal_band_match = (
            _band_index(P_geo, _PRESSURE_BANDS) == _band_index(E_density, _PRESSURE_BANDS)
        )

        # ── Resonance / thermal alignment ─────────────────────────────────
        resonance_map = geometric_geometry.get("resonance_map", [])
        n_therm       = state["thermal_occupation_exchange"]
        t_regime      = state["thermal_regime"]

        if resonance_map:
            mean_res     = sum(resonance_map) / len(resonance_map)
            # Classical / many magnons excited → expect constructive (positive) resonance
            # Quantum / few magnons → expect destructive or neutral
            thermal_high = t_regime in ("classical",)
            res_positive = mean_res > 0
            resonance_thermal_alignment = 1.0 if (thermal_high == res_positive) else 0.0
        else:
            resonance_thermal_alignment = 0.5   # no data — neutral

        # ── J* / KT-φ connection ──────────────────────────────────────────
        # Dimensionless exchange ratio: J* = A_ex · l_ex / (k_B · T)
        # Units: (J/m · m) / J = dimensionless ✓
        # J* ≈ φ signals proximity to the golden-ratio KT resonance point;
        # for typical materials this occurs near the Curie temperature.
        if l_ex > 0 and T > 0:
            J_star = (A_ex * l_ex) / (_K_B * T)
        else:
            J_star = 0.0
        kt_phi_match = (J_star > 0 and abs(J_star - _PHI) / _PHI < 0.15)

        # ── Consistency score (weighted sum) ─────────────────────────────
        # B (0.40): primary physical signal
        # P_applied (0.30): applied-field consistency
        # P_thermal (0.10): thermal energy proximity (bonus signal, lower weight)
        # RT (0.20): resonance/thermal alignment
        B_score       = (3 - hamming_B)         / 3.0
        P_app_score   = (3 - hamming_P_applied)  / 3.0
        P_therm_score = (3 - hamming_P_thermal)  / 3.0
        RT_score      = resonance_thermal_alignment

        consistency_score = (0.40 * B_score
                             + 0.30 * P_app_score
                             + 0.10 * P_therm_score
                             + 0.20 * RT_score)

        # ── Divergence flags ──────────────────────────────────────────────
        divergence_flags = []
        if not B_band_match:
            divergence_flags.append(
                f"B field: geometric {B_geo:.3e} T vs magnonic {B_mag_dipolar:.3e} T"
            )
        if not P_applied_band_match:
            divergence_flags.append(
                f"applied pressure: geometric {P_geo:.3e} Pa vs H0-driven {P_mag_applied:.3e} Pa"
            )
        if P_thermal_band_match:
            # This is the phase-transition signal — thermal energy ≈ field energy
            divergence_flags.append(
                f"thermal/field parity: E_density {E_density:.3e} Pa ≈ P_geo {P_geo:.3e} Pa"
                f" (near transition)"
            )
        if resonance_map and resonance_thermal_alignment < 0.5:
            divergence_flags.append(
                f"resonance/thermal: mean_res={sum(resonance_map)/len(resonance_map):.2f}"
                f" vs regime={t_regime}"
            )

        # ── Interpretation ────────────────────────────────────────────────
        n_div = len(divergence_flags)
        if n_div == 0:
            interpretation = "consistent"
        elif n_div == 1:
            interpretation = "minor_divergence"
        else:
            interpretation = "major_divergence"

        if kt_phi_match:
            interpretation += "+KT_phi_resonance"

        return {
            # Raw encodings
            "geometric_bits":          geo_bits,
            "magnonic_bits":           mag_bits,
            # B field
            "B_geometric_T":           B_geo,
            "B_magnonic_dipolar_T":    B_mag_dipolar,
            "B_magnonic_bottom_T":     B_mag_bottom,
            "B_band_match":            B_band_match,
            "B_hamming":               hamming_B,
            # Pressure — branch 1: applied field (apples-to-apples)
            "P_geometric_Pa":          P_geo,
            "P_magnonic_applied_Pa":   P_mag_applied,
            "P_applied_band_match":    P_applied_band_match,
            "P_applied_hamming":       hamming_P_applied,
            # Pressure — branch 2: volumetric magnon energy density (transition signal)
            "E_magnonic_density_Pa":   E_density,
            "P_thermal_band_match":    P_thermal_band_match,
            "P_thermal_hamming":       hamming_P_thermal,
            # Resonance / thermal
            "resonance_thermal_alignment": resonance_thermal_alignment,
            "thermal_regime":          t_regime,
            "n_thermal_exchange":      n_therm,
            # KT / φ
            "J_star":                  J_star,
            "kt_phi_match":            kt_phi_match,
            # Summary
            "consistency_score":       consistency_score,
            "divergence_flags":        divergence_flags,
            "interpretation":          interpretation,
        }
