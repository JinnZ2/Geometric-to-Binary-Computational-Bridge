"""
build_claims.py — generate CLAIM_TABLE.json + .claims + .claims.bin
==================================================================

Run from the repo root:

    python scripts/build_claims.py

Reads the curated claim list at the bottom of this file, builds the
shared lookup table, writes the human-readable line file and the
binary blob, and validates that line ↔ dict and dict ↔ binary
round-trip cleanly.

Each claim carries an inline ``# provenance:`` comment pointing at
the file (and where useful, line) where the underlying differential
or physical law lives. Add a claim by adding a dict with the same
shape — no other code changes required.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so ``import CLAIM_SCHEMA`` works
# whether this script is invoked as ``python scripts/build_claims.py``
# or as a module.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import CLAIM_SCHEMA as cs  # noqa: E402


# ============================================================
# Curated claim list. Every entry traces to real code — see
# the inline ``# provenance:`` comments.
# ============================================================

CLAIMS = [
    # provenance: bridges/electric_encoder.py:70 (ohms_law) + :77 (power_dissipation)
    {
        "id":     "ohmic_dissip",
        "rate":   "dE/dt=V*I",
        "bounds": "ohmic_circuit,steady_state,lab_scale",
        "cond":   ["I_nonzero", "R_finite", "V_bounded"],
        "rel":    ["skin_depth", "ac_zero_cross"],
        "fail":   ["superconductor", "dielectric_breakdown"],
        "meas":   ["VI_probes", "calorimetry"],
        "cyc":    0,
    },

    # provenance: bridges/electric_encoder.py:82 (coulomb_force) + :89 (electric_field_magnitude)
    {
        "id":     "coulomb_field",
        "rate":   "dF/dr=-2*k*q1*q2/r^3",
        "bounds": "vacuum,classical,far_field",
        "cond":   ["r_positive", "classical_regime"],
        "rel":    ["skin_depth", "ohmic_dissip"],
        "fail":   ["r_to_zero", "quantum_regime"],
        "meas":   ["torsion_balance", "electrometer"],
        "cyc":    0,
    },

    # provenance: bridges/electric_encoder.py:96 (skin_depth)
    {
        "id":     "skin_depth",
        "rate":   "dJ/dr=-J/delta",
        "bounds": "cylindrical_conductor,AC_steady",
        "cond":   ["f_positive", "sigma_positive", "delta_lt_radius"],
        "rel":    ["ohmic_dissip", "ac_zero_cross"],
        "fail":   ["DC_limit", "perfect_conductor"],
        "meas":   ["four_wire_AC", "eddy_probe"],
        "cyc":    0,
    },

    # provenance: bridges/electric_alternative_compute.py (analyze_ac_zero_crossings)
    {
        "id":     "ac_zero_cross",
        "rate":   "dI/dt@I=0=omega*I_peak",
        "bounds": "AC_circuit,sample_window",
        "cond":   ["AC_excitation", "above_nyquist"],
        "rel":    ["skin_depth", "ohmic_dissip"],
        "fail":   ["DC_offset_dominant", "sub_nyquist"],
        "meas":   ["zero_crossing_detector", "FFT"],
        "cyc":    0,
    },

    # provenance: bridges/magnetic_encoder.py:141 (biot_savart_magnitude)
    {
        "id":     "biot_savart",
        "rate":   "dB/dl=mu0*I*(dl_x_rhat)/(4pi*r^2)",
        "bounds": "vacuum,magnetostatic,line_current",
        "cond":   ["current_steady", "no_displacement"],
        "rel":    ["larmor_precess", "magnonic_disp"],
        "fail":   ["rapidly_varying", "relativistic"],
        "meas":   ["hall_probe", "fluxgate"],
        "cyc":    0,
    },

    # provenance: bridges/magnetic_encoder.py:204 (larmor_frequency)
    {
        "id":     "larmor_precess",
        "rate":   "dphi/dt=gamma*B",
        "bounds": "spin_in_field,classical_to_quantum",
        "cond":   ["B_static", "T2_long"],
        "rel":    ["biot_savart", "magnonic_disp"],
        "fail":   ["B_zero", "T2_short", "RF_resonance"],
        "meas":   ["NMR", "ESR", "ODMR"],
        "cyc":    0,
    },

    # provenance: bridges/wave_encoder.py (Schrödinger evolution)
    {
        "id":     "psi_evolve",
        "rate":   "dpsi/dt=(-i*H/hbar)*psi",
        "bounds": "closed_quantum_system",
        "cond":   ["H_hermitian", "no_decoherence"],
        "rel":    ["born_density"],
        "fail":   ["open_system", "measurement_collapse"],
        "meas":   ["state_tomography", "interferometry"],
        "cyc":    0,
    },

    # provenance: bridges/wave_encoder.py:68 (probability_density)
    {
        "id":     "born_density",
        "rate":   "dP/dx=d_abs(psi)^2/dx",
        "bounds": "normalised_state,position_basis",
        "cond":   ["norm_unity", "finite_support"],
        "rel":    ["psi_evolve"],
        "fail":   ["unnormalised", "momentum_basis_only"],
        "meas":   ["photon_counting", "spatial_imaging"],
        "cyc":    0,
    },

    # provenance: bridges/sound_encoder.py:123 (doppler_shift)
    {
        "id":     "doppler_shift",
        "rate":   "df/dv=f_source/v_sound",
        "bounds": "subsonic_observer,classical",
        "cond":   ["v_lt_v_sound", "line_of_sight"],
        "rel":    ["beat_freq", "harmonic_ratio"],
        "fail":   ["sonic_boom", "transverse_motion"],
        "meas":   ["spectrogram", "phase_locked_loop"],
        "cyc":    0,
    },

    # provenance: bridges/sound_encoder.py:104 (beat_frequency)
    {
        "id":     "beat_freq",
        "rate":   "df_beat/dt=abs(f1-f2)",
        "bounds": "two_tone_superposition",
        "cond":   ["near_unison", "linear_medium"],
        "rel":    ["doppler_shift", "harmonic_ratio"],
        "fail":   ["nonlinear_medium", "chaotic_phase"],
        "meas":   ["zero_crossing_detector", "FFT"],
        "cyc":    0,
    },

    # provenance: bridges/sound_encoder.py:109 (harmonic_ratio)
    {
        "id":     "harmonic_ratio",
        "rate":   "dh/dt=f1/f2",
        "bounds": "stable_pitches,linear_medium",
        "cond":   ["f1_finite", "f2_nonzero"],
        "rel":    ["beat_freq", "doppler_shift"],
        "fail":   ["chaotic_pitch", "pitch_zero"],
        "meas":   ["pitch_tracker", "FFT"],
        "cyc":    0,
    },

    # provenance: bridges/thermal_encoder.py:69 (stefan_boltzmann_radiance)
    {
        "id":     "thermal_rad",
        "rate":   "dM/dT=4*epsilon*sigma*T^3",
        "bounds": "blackbody_or_grey,thermal_equilibrium",
        "cond":   ["T_positive", "epsilon_in_0_1", "LTE"],
        "rel":    ["fourier_heat", "newton_cool"],
        "fail":   ["non_LTE", "plasma", "cosmological"],
        "meas":   ["bolometer", "IR_spectrometer"],
        "cyc":    0,
    },

    # provenance: bridges/thermal_encoder.py:78 (heat_flux_fourier)
    {
        "id":     "fourier_heat",
        "rate":   "dT/dt=alpha*d2T/dx2",
        "bounds": "solid_or_static_fluid,isotropic",
        "cond":   ["k_constant", "no_radiation", "no_convection"],
        "rel":    ["thermal_rad", "newton_cool"],
        "fail":   ["plasma", "anisotropic", "phase_change"],
        "meas":   ["thermocouple_array", "IR_camera"],
        "cyc":    0,
    },

    # provenance: bridges/thermal_encoder.py:89 (newton_cooling_rate)
    {
        "id":     "newton_cool",
        "rate":   "dQ/dt=h*(T_obj-T_env)",
        "bounds": "convective,small_dT",
        "cond":   ["h_constant", "T_obj_gt_T_env"],
        "rel":    ["thermal_rad", "fourier_heat"],
        "fail":   ["large_dT", "phase_change"],
        "meas":   ["thermocouple", "IR_camera"],
        "cyc":    0,
    },

    # provenance: bridges/gravity_encoder.py:69 (gravitational_acceleration)
    {
        "id":     "grav_accel",
        "rate":   "dv/dt=-G*M/r^2",
        "bounds": "weak_field,point_mass",
        "cond":   ["r_gt_r_s", "classical_regime"],
        "rel":    ["tidal_grad", "orbital_v"],
        "fail":   ["near_horizon", "multi_body"],
        "meas":   ["gravimeter", "free_fall"],
        "cyc":    0,
    },

    # provenance: bridges/gravity_encoder.py:97 (tidal_acceleration)
    {
        "id":     "tidal_grad",
        "rate":   "da/dr=-2*G*M/r^3",
        "bounds": "extended_body,weak_field",
        "cond":   ["d_lt_r", "rigid_body"],
        "rel":    ["grav_accel", "orbital_v"],
        "fail":   ["roche_disrupt", "BH_horizon"],
        "meas":   ["torsion_pendulum", "gradient_satellite"],
        "cyc":    0,
    },

    # provenance: bridges/gravity_encoder.py:83 (orbital_velocity)
    {
        "id":     "orbital_v",
        "rate":   "dv_orb/dr=-(1/2)*sqrt(G*M)/r^(3/2)",
        "bounds": "circular_orbit,bound_state",
        "cond":   ["E_negative", "no_drag"],
        "rel":    ["grav_accel", "tidal_grad"],
        "fail":   ["unbound", "drag_dominant"],
        "meas":   ["orbit_tracking", "doppler_shift"],
        "cyc":    3,
    },

    # provenance: Engine/kt_annealer.py + bridges/magnetic_encoder.py (KT phase transition)
    {
        "id":     "kt_phase",
        "rate":   "dn_v/dT@T_KT_diverges",
        "bounds": "2D_XY_model,near_T_KT",
        "cond":   ["lattice_size_gt_core", "equil_anneal"],
        "rel":    ["magnonic_disp", "larmor_precess"],
        "fail":   ["long_range_order", "3D_system"],
        "meas":   ["helicity_modulus", "spin_correl"],
        "cyc":    0,
    },

    # provenance: Engine/magnonic_sublayer.py:37 (dispersion_relation) + :75 (group_velocity)
    {
        "id":     "magnonic_disp",
        "rate":   "domega/dk=v_g(k,H0,Ms,Aex,theta)",
        "bounds": "thin_magnetic_film,exchange_dominated",
        "cond":   ["k_positive", "low_damping", "in_plane"],
        "rel":    ["larmor_precess", "biot_savart"],
        "fail":   ["bulk_3D", "high_damping"],
        "meas":   ["brillouin_light_scatt", "propagating_sw"],
        "cyc":    0,
    },

    # provenance: Silicon/modules/dynamics.py (evolve_deterministic / evolve_stochastic)
    {
        "id":     "si_geodesic",
        "rate":   "d2S/dt2=-Gamma*dS/dt-ginv*gradV",
        "bounds": "9D_silicon_manifold,fab_pipeline",
        "cond":   ["g_pos_def", "smooth_V"],
        "rel":    ["regime_omega2", "octahedral_col"],
        "fail":   ["signature_change", "constraint_viol"],
        "meas":   ["state_trajectory", "regime_weights"],
        "cyc":    4,
    },

    # provenance: Silicon/modules/regime.py:93 (log_omega2) + Octahedral_Integration.md Step 4
    {
        "id":     "regime_omega2",
        "rate":   "dOmega2/dt@Omega2=0=signature_flip",
        "bounds": "silicon_manifold,near_face",
        "cond":   ["smooth_metric", "rim_to_lor_transition"],
        "rel":    ["si_geodesic", "octahedral_col"],
        "fail":   ["pure_riemannian", "pure_lorentzian"],
        "meas":   ["kernel_eigval_sign", "omega2_sign_log"],
        "cyc":    0,
    },

    # provenance: Engine/gaussian_splats/octahedral.py + bridges/probability_collapse.py
    {
        "id":     "octahedral_col",
        "rate":   "dH/dt=d(-sum p_i*log p_i)/dt",
        "bounds": "8_state_octahedral_basis",
        "cond":   ["positive_probabilities", "normalised"],
        "rel":    ["si_geodesic", "regime_omega2"],
        "fail":   ["sub_8_state", "basis_change"],
        "meas":   ["vertex_argmax", "distribution_collapse"],
        "cyc":    0,
    },

    # provenance: bridges/intersection/resonate.py (resonate / resonate_many)
    {
        "id":     "resonate",
        "rate":   "dC/dt=mean(cos(theta_ij))",
        "bounds": "multi_domain_basin_signatures",
        "cond":   ["vector_normalisable", "regime_classified"],
        "rel":    ["octahedral_col"],
        "fail":   ["empty_vector", "single_domain"],
        "meas":   ["pairwise_dot", "agreement_regime"],
        "cyc":    0,
    },
]


# ============================================================
# Build pipeline
# ============================================================

def _canonicalise(
    claims: list,
    table: dict,
) -> list:
    """
    Return a copy of ``claims`` where each multi-valued field is
    sorted by its position in ``table``. This makes the line-format
    output deterministic and identical to what the binary codec
    yields on round-trip (which sorts by mask bit, i.e. table index).
    """
    out = []
    for c in claims:
        canon = dict(c)
        for table_field, claim_field in (
            ("cond", "cond"), ("rel", "rel"),
            ("fail", "fail"), ("meas", "meas"),
        ):
            arr = table[table_field]
            canon[claim_field] = sorted(
                c.get(claim_field, []),
                key=lambda v, _arr=arr: _arr.index(v),
            )
        out.append(canon)
    return out


def build(repo_root: Path = _ROOT) -> dict:
    table = cs.build_table(CLAIMS)

    # Validate the per-mask cap before writing — better to fail early
    # than emit a file the codec rejects.
    for field in ("cond", "rel", "fail", "meas"):
        if len(table[field]) > cs.MASK_BITS:
            raise SystemExit(
                f"CLAIM_TABLE[{field!r}] has {len(table[field])} entries; "
                f"the binary codec only supports up to {cs.MASK_BITS} per "
                f"field. Consolidate values or expand MASK_BITS in "
                f"CLAIM_SCHEMA.py."
            )

    canon = _canonicalise(CLAIMS, table)

    cs.write_table(repo_root / "CLAIM_TABLE.json", table)
    cs.write_claims(repo_root / ".claims", canon)
    cs.write_claims_binary(repo_root / ".claims.bin", canon, table)

    # Round-trip check (line and binary share the canonical form)
    line_back = cs.read_claims(repo_root / ".claims")
    for orig, got in zip(canon, line_back):
        if orig != got:
            raise SystemExit(
                f".claims round-trip mismatch on {orig['id']}: "
                f"{orig} != {got}"
            )

    id_lookup = cs.id_lookup_from_claims(canon)
    bin_back = cs.read_claims_binary(
        repo_root / ".claims.bin", table, id_lookup=id_lookup,
    )
    for orig, got in zip(canon, bin_back):
        if orig != got:
            raise SystemExit(
                f".claims.bin round-trip mismatch on {orig['id']}: "
                f"{orig} != {got}"
            )

    return {
        "claims":        len(canon),
        "table_entries": {f: len(table[f]) for f in cs.TABLE_FIELDS},
        "bin_bytes":     len(canon) * cs.BIN_CLAIM_BYTES,
    }


if __name__ == "__main__":
    stats = build()
    print(f"Wrote CLAIM_TABLE.json, .claims, .claims.bin "
          f"({stats['claims']} claims, {stats['bin_bytes']} bytes binary)")
    for f, n in stats["table_entries"].items():
        print(f"  table[{f!r:8s}]: {n} entries")
