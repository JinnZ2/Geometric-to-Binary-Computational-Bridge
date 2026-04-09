# STATUS: speculative — soliton antenna coherent transport framework
"""
Soliton Antenna — Supramolecular Coherent Transport Framework
=============================================================
Self-assembled exciton conduits: J-aggregate strong coupling,
ballistic transport, defect tolerance, vibronic fuel.

Extracted from Silicon/FRET/FRET-soliton.md
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class SolitonTransportProperties:
    """Transport properties of a J-aggregate soliton antenna."""
    coupling_strength_cm: float    # J coupling (cm^-1)
    coherence_length_nm: float     # L_coh (nm)
    transport_velocity_ms: float   # m/s
    transport_range_nm: float      # range before decay (nm)
    interwall_transfer_fs: float   # inter-wall transfer time (fs)


# Reference values from DWNT architecture
DWNT_REFERENCE = SolitonTransportProperties(
    coupling_strength_cm=2000.0,    # J ~ 2000 cm^-1
    coherence_length_nm=30.0,       # 10-50 nm typical
    transport_velocity_ms=1e5,      # ~10^5 m/s
    transport_range_nm=1000.0,      # ~1 μm before decay
    interwall_transfer_fs=150.0,    # ~150 fs
)


def fret_efficiency(r: float, R0: float) -> float:
    """
    FRET efficiency in the linear (weak coupling) regime:
    E = 1 / (1 + (r/R0)^6)

    r: donor-acceptor distance (nm)
    R0: Förster radius (nm)
    """
    if R0 <= 0:
        return 0.0
    return 1.0 / (1.0 + (r / R0) ** 6)


def forster_radius(kappa2: float, phi_D: float, J_overlap: float,
                    n: float) -> float:
    """
    Förster radius:
    R0 ~ (kappa^2 * Phi_D * J * n^-4)^(1/6)

    kappa2: orientation factor (2/3 isotropic, up to 4 aligned)
    phi_D: donor quantum yield (0-1)
    J_overlap: spectral overlap integral (M^-1 cm^-1 nm^4)
    n: refractive index of medium

    Returns R0 in arbitrary units (proportional, not absolute).
    """
    if n <= 0 or any(v < 0 for v in [kappa2, phi_D, J_overlap]):
        return 0.0
    return (kappa2 * phi_D * J_overlap * n ** (-4)) ** (1.0 / 6.0)


def is_strong_coupling(J_coupling: float, disorder: float) -> bool:
    """
    Check if system is in strong coupling (soliton) regime:
    J >> Delta (coupling >> disorder)

    When this holds: κ² averaging automatic, distance irrelevant,
    transport ballistic not diffusive.
    """
    return J_coupling > 3.0 * disorder


def effective_diffusion_length(L0: float, n_defects: float,
                                n_crit: float) -> float:
    """
    Effective diffusion length under defect accumulation:
    L_eff = L0 * exp(-n_defects / n_crit)

    Soliton system degrades gracefully (leaf, not fuse).
    Monitor L_eff as primary health metric.
    """
    if n_crit <= 0:
        return 0.0
    return L0 * np.exp(-n_defects / n_crit)


def superradiance_rate(N_coherent: int, k_rad_single: float) -> float:
    """
    Superradiance: k_rad scales with coherent molecule count N.
    k_rad_collective = N * k_rad_single

    In J-aggregates under stress:
    - Excitons accumulate → coherent N increases
    - System becomes super-emitter → dumps excess as photon burst (<100 ps)
    - Prioritizes survival over efficiency
    """
    return N_coherent * k_rad_single


def quantum_bridge_tunneling(L_coh: float, d_defect: float) -> bool:
    """
    Defect tolerance via quantum bridge:
    If defect size < coherence length, wave packet tunnels through.

    L_coh >> d_defect → defect invisible to transport.
    """
    return L_coh > 3.0 * d_defect


def cascade_fidelity(efficiencies: List[float]) -> float:
    """
    Information-theoretic fidelity of a FRET cascade:
    F_C = product(E_i) for i in 1..N

    Total survival probability of excitation through all steps.
    Bottleneck = step with lowest efficiency.
    """
    if not efficiencies:
        return 0.0
    return float(np.prod(efficiencies))


def impedance_match(k_arrival: float, k_cat: float) -> str:
    """
    Check antenna-catalyst impedance matching.

    k_arrival: exciton arrival rate
    k_cat: catalyst turnover frequency (TOF)

    Risk: k_arrival >> k_cat → exciton-exciton annihilation
    """
    ratio = k_arrival / max(k_cat, 1e-30)
    if ratio > 10:
        return "OVERLOADED"    # Superradiance bleed valve activates
    elif ratio > 2:
        return "STRESSED"      # Some back-pressure
    elif ratio > 0.5:
        return "MATCHED"       # Optimal impedance
    else:
        return "UNDERUTILIZED"  # Antenna too small for catalyst


# ── Health metrics ──────────────────────────────────────────────────────

@dataclass
class AntennaHealth:
    """Health metrics for a soliton antenna system."""
    L_eff_nm: float              # Effective diffusion length (target > 500 nm)
    interwall_transfer_fs: float  # Inter-wall transfer time (~150 fs)
    superrad_lifetime_ps: float   # Superradiance lifetime (< 100 ps under stress)
    bundle_intact: bool           # Fascicle coherence

    @property
    def healthy(self) -> bool:
        return (self.L_eff_nm > 200 and
                self.interwall_transfer_fs < 500 and
                self.bundle_intact)


HEALTH_TARGETS = {
    "L_eff_nm": (">", 500),
    "interwall_transfer_fs": ("~", 150),
    "superrad_lifetime_ps": ("<", 100),
    "bundle_intact": ("=", True),
}

SYNTHESIS_TARGETS = {
    "tube_width_cv": ("<", 0.10),     # CV < 10%
    "tube_length_nm": ("range", (500, 1000)),
    "bundle_percolation": ("=", True),
    "endcap_coverage": (">", 0.90),
}
