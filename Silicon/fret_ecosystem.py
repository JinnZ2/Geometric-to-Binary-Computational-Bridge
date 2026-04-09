# STATUS: infrastructure — FRET ecosystem coupling models
"""
FRET Ecosystem Coupling Framework — energy transfer models for biological systems.

Extracted from Silicon/FRET.md.
Implements FRET coupling equations, electromagnetic spectrum organism database,
multi-hop cascade models, spectral overlap integrals, error/crosstalk estimation,
and extreme-environment energy data structures.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# 1.  FRET Coupling Fundamentals
# ============================================================================

def fret_efficiency(r0: float, r: float | np.ndarray) -> float | np.ndarray:
    """Classical Forster resonance energy transfer efficiency.

    E = R0^6 / (R0^6 + r^6)

    Parameters
    ----------
    r0 : float
        Forster radius (nm).
    r : float or ndarray
        Donor-acceptor distance (nm).

    Returns
    -------
    float or ndarray
        Transfer efficiency (0-1).
    """
    r = np.asarray(r, dtype=float)
    r0_6 = r0 ** 6
    return r0_6 / (r0_6 + r ** 6)


def effective_forster_radius(r0_single: float,
                             n_emitters: int,
                             q_cavity: float = 1.0) -> float:
    """Extended Forster radius for coherent resonance networks.

    R0_effective = R0_single * N^(1/6) * Q_cavity

    Parameters
    ----------
    r0_single : float
        Single-pair Forster radius (nm).
    n_emitters : int
        Number of coherently coupled emitters.
    q_cavity : float
        Electromagnetic cavity enhancement factor.

    Returns
    -------
    float
        Effective Forster radius (nm).
    """
    return r0_single * (n_emitters ** (1.0 / 6.0)) * q_cavity


def forster_radius_from_components(kappa_sq: float,
                                   phi_d: float,
                                   j_lambda: float,
                                   n_refr: float = 1.4) -> float:
    """Calculate Forster radius from physical components.

    R0 proportional to (kappa^2 * Phi_D * J(lambda) / n^4)^(1/6)

    Uses the standard Forster formula with SI-consistent prefactor.
    R0 = 0.2108 * (kappa^2 * phi_d * J / n^4)^(1/6)  (nm, with J in nm^4 / (M cm))

    Parameters
    ----------
    kappa_sq : float
        Orientation factor (0-4, often 2/3 for random).
    phi_d : float
        Donor quantum yield.
    j_lambda : float
        Spectral overlap integral (M^-1 cm^-1 nm^4).
    n_refr : float
        Refractive index of medium.

    Returns
    -------
    float
        Forster radius in nm.
    """
    return 0.2108 * (kappa_sq * phi_d * j_lambda / n_refr ** 4) ** (1.0 / 6.0)


# ---------------------------------------------------------------------------
# Orientation Factor
# ---------------------------------------------------------------------------

def orientation_factor(theta_t: float,
                       theta_d: float,
                       theta_a: float) -> float:
    """Compute the orientation factor kappa^2.

    kappa^2 = (cos(theta_T) - 3 cos(theta_D) cos(theta_A))^2

    Parameters
    ----------
    theta_t : float
        Angle between donor emission and acceptor absorption dipoles (rad).
    theta_d : float
        Angle between donor dipole and donor-acceptor vector (rad).
    theta_a : float
        Angle between acceptor dipole and donor-acceptor vector (rad).

    Returns
    -------
    float
        kappa^2 value (0-4).
    """
    kappa = np.cos(theta_t) - 3.0 * np.cos(theta_d) * np.cos(theta_a)
    return float(kappa ** 2)


# ============================================================================
# 2.  Multi-Hop FRET Cascades
# ============================================================================

def multihop_efficiency(efficiency_per_hop: float, n_hops: int) -> float:
    """Cumulative efficiency of an N-hop FRET cascade (no amplification).

    Parameters
    ----------
    efficiency_per_hop : float
        Transfer efficiency per hop (0-1).
    n_hops : int
        Number of hops.

    Returns
    -------
    float
        Cumulative efficiency.
    """
    return efficiency_per_hop ** n_hops


def multihop_with_amplification(efficiency_per_hop: float,
                                n_hops: int,
                                amplification: float = 1.0) -> float:
    """Multi-hop FRET with metabolic amplification at each step.

    Effective per-hop efficiency is capped at 1.0.

    Parameters
    ----------
    efficiency_per_hop : float
        Base transfer efficiency per hop.
    n_hops : int
        Number of hops.
    amplification : float
        Metabolic amplification factor per hop (>=1.0).

    Returns
    -------
    float
        Cumulative efficiency (can exceed 1.0 if amplification is large).
    """
    eff = min(efficiency_per_hop * amplification, 1.0)
    return eff ** n_hops


# Reference table from the document
MULTIHOP_REFERENCE = [
    {"hops": 1,   "distance_per_hop_nm": 5, "total_nm": 5,   "efficiency": 0.90},
    {"hops": 10,  "distance_per_hop_nm": 5, "total_nm": 50,  "efficiency": 0.35},
    {"hops": 100, "distance_per_hop_nm": 5, "total_nm": 500, "efficiency": 0.00003},
]


# ============================================================================
# 3.  Spectral Overlap & Resonance
# ============================================================================

def spectral_overlap_integral(wavelengths: np.ndarray,
                              f_donor: np.ndarray,
                              eps_acceptor: np.ndarray) -> float:
    """Compute the spectral overlap integral J(lambda).

    J(lambda) = integral F_D(lambda) * eps_A(lambda) * lambda^4 d(lambda)

    Parameters
    ----------
    wavelengths : ndarray
        Wavelength array (nm).
    f_donor : ndarray
        Normalised donor emission spectrum (same length as wavelengths).
    eps_acceptor : ndarray
        Acceptor molar extinction coefficient spectrum (M^-1 cm^-1).

    Returns
    -------
    float
        Overlap integral (M^-1 cm^-1 nm^4).
    """
    integrand = f_donor * eps_acceptor * wavelengths ** 4
    return float(np.trapz(integrand, wavelengths))


# ============================================================================
# 4.  Competition & Branching
# ============================================================================

def fret_branching_efficiency(k_fret: float,
                              k_radiative: float,
                              k_nonradiative: float,
                              k_metabolic: float = 0.0) -> float:
    """FRET efficiency from rate competition.

    Phi_FRET = k_FRET / (k_FRET + k_radiative + k_nonradiative + k_metabolic)

    Parameters
    ----------
    k_fret : float
        FRET transfer rate (s^-1).
    k_radiative : float
        Radiative decay rate.
    k_nonradiative : float
        Non-radiative decay rate.
    k_metabolic : float
        Metabolic process rate.

    Returns
    -------
    float
        FRET efficiency (0-1).
    """
    k_total = k_fret + k_radiative + k_nonradiative + k_metabolic
    if k_total <= 0:
        return 0.0
    return k_fret / k_total


# ============================================================================
# 5.  Error, Crosstalk & Isolation
# ============================================================================

def isolation_radius(r0: float, factor: float = 3.0) -> float:
    """Minimum distance for <1% crosstalk.

    Isolation_radius = factor * R0  (at 3*R0, E < 1%)
    """
    return factor * r0


def multihop_error_rate(efficiency_per_hop: float,
                        crosstalk_per_hop: float,
                        n_hops: int) -> float:
    """Error rate for a multi-hop FRET cascade.

    Error = 1 - (eff_per_hop)^N * (1 - crosstalk)^N

    Parameters
    ----------
    efficiency_per_hop : float
        Transfer efficiency per hop (0-1).
    crosstalk_per_hop : float
        Probability of crosstalk per hop (0-1).
    n_hops : int
        Number of hops.

    Returns
    -------
    float
        Cumulative error rate (0-1).
    """
    return 1.0 - (efficiency_per_hop ** n_hops) * ((1.0 - crosstalk_per_hop) ** n_hops)


# ============================================================================
# 6.  Electromagnetic Cavity / Resonance
# ============================================================================

def cavity_resonance_frequency(lx: float, ly: float, lz: float,
                               m: int = 1, n: int = 1, p: int = 1,
                               c: float = 3e8,
                               n_refr: float = 1.33) -> float:
    """Resonance frequency of an ecosystem treated as an EM cavity.

    omega = (c/n) * sqrt((m*pi/Lx)^2 + (n_mode*pi/Ly)^2 + (p*pi/Lz)^2)

    Parameters
    ----------
    lx, ly, lz : float
        Cavity dimensions (m).
    m, n, p : int
        Mode numbers.
    c : float
        Speed of light (m/s).
    n_refr : float
        Refractive index of medium.

    Returns
    -------
    float
        Angular resonance frequency (rad/s).
    """
    return (c / n_refr) * np.sqrt(
        (m * np.pi / lx) ** 2 +
        (n * np.pi / ly) ** 2 +
        (p * np.pi / lz) ** 2
    )


# ============================================================================
# 7.  Electromagnetic Spectrum — Organism Database
# ============================================================================

@dataclass
class OrganismEMEntry:
    """One organism's electromagnetic spectrum utilisation."""

    name: str
    spectrum_band: str          # "infrared", "visible", "uv", etc.
    wavelength_range_nm: Optional[tuple[float, float]] = None
    detection_capability: str = ""
    sensor_type: str = ""
    sensitivity: str = ""
    fret_candidate: bool = False
    notes: str = ""


# Infrared-sensing organisms
PIT_VIPER = OrganismEMEntry(
    name="Pit Vipers",
    spectrum_band="infrared",
    wavelength_range_nm=(5000.0, 30000.0),  # mid-to-far IR
    detection_capability="3D thermal imaging",
    sensor_type="pit organ (loreal pit)",
    sensitivity="0.003 degC temperature difference",
    fret_candidate=True,
    notes="Heat detection via TRPA1 ion channels",
)

VAMPIRE_BAT = OrganismEMEntry(
    name="Vampire Bats",
    spectrum_band="infrared",
    wavelength_range_nm=(8000.0, 14000.0),
    detection_capability="Blood-rich area location",
    sensor_type="nose leaf TRPV1 receptors",
    sensitivity="Blood vessel localisation",
)

FIRE_BEETLE = OrganismEMEntry(
    name="Fire Beetles (Melanophila)",
    spectrum_band="infrared",
    wavelength_range_nm=(2500.0, 4000.0),
    detection_capability="Forest fire detection up to 50 miles",
    sensor_type="thorax infrared sensors",
    fret_candidate=True,
)

MOSQUITO = OrganismEMEntry(
    name="Mosquitoes",
    spectrum_band="infrared",
    detection_capability="Host location via heat + CO2 coupling",
    sensor_type="antenna heat detection",
    notes="CO2 gradient coupling with thermal detection",
)

# Bioluminescence / visible-range organisms
AEQUOREA = OrganismEMEntry(
    name="Aequorea victoria (jellyfish)",
    spectrum_band="visible",
    wavelength_range_nm=(430.0, 510.0),
    detection_capability="Bioluminescence (blue, 470 nm emission)",
    sensor_type="aequorin + GFP",
    fret_candidate=True,
    notes="Classic FRET pair: aequorin -> GFP",
)

DINOFLAGELLATE = OrganismEMEntry(
    name="Dinoflagellates",
    spectrum_band="visible",
    wavelength_range_nm=(460.0, 500.0),
    detection_capability="Bioluminescence (480 nm emission)",
    notes="Medium spectral overlap with surrounding organisms",
    fret_candidate=True,
)

DEEP_SEA_FISH = OrganismEMEntry(
    name="Deep-sea fish (dragonfish)",
    spectrum_band="visible",
    wavelength_range_nm=(630.0, 700.0),
    detection_capability="Red bioluminescence (650 nm) — invisible to prey",
    notes="Low spectral overlap is intentional (private channel)",
)

# Full database
EM_ORGANISM_DATABASE: list[OrganismEMEntry] = [
    PIT_VIPER,
    VAMPIRE_BAT,
    FIRE_BEETLE,
    MOSQUITO,
    AEQUOREA,
    DINOFLAGELLATE,
    DEEP_SEA_FISH,
]


def fret_candidate_organisms() -> list[OrganismEMEntry]:
    """Return organisms flagged as FRET coupling candidates."""
    return [o for o in EM_ORGANISM_DATABASE if o.fret_candidate]


# Bioluminescence spectral pairing table (from FRET.md Section 3)
BIOLUMINESCENCE_PAIRS: list[dict] = [
    {
        "organism": "Aequorea (blue)",
        "emission_peak_nm": 470,
        "absorption_partner": "GFP (green)",
        "spectral_overlap": "high",
    },
    {
        "organism": "Dinoflagellates",
        "emission_peak_nm": 480,
        "absorption_partner": "Surrounding organisms",
        "spectral_overlap": "medium",
    },
    {
        "organism": "Deep-sea fish (red)",
        "emission_peak_nm": 650,
        "absorption_partner": "Invisible to prey",
        "spectral_overlap": "low (intentional)",
    },
]


# ============================================================================
# 8.  Extreme-Environment Energy Data
# ============================================================================

@dataclass
class EcosystemEnergyZone:
    """Energy measurement for an extreme-environment coupling zone."""

    location: str
    sample_type: str
    energy_output_uw_per_g: float    # micro-watts per gram
    sulfur_umol_per_g: float         # micro-mol per gram
    notes: str = ""


# Movile Cave data (Section 3 of FRET.md)
MOVILE_CAVE_MICROBIAL_MAT = EcosystemEnergyZone(
    location="Movile Cave, Romania",
    sample_type="microbial mat",
    energy_output_uw_per_g=1200.0,
    sulfur_umol_per_g=500.0,
    notes="Energy concentrated in coupling zones rather than lost as heat",
)

MOVILE_CAVE_BACKGROUND = EcosystemEnergyZone(
    location="Movile Cave, Romania",
    sample_type="background",
    energy_output_uw_per_g=50.0,   # midpoint of 40-60
    sulfur_umol_per_g=2.5,
    notes="Background sample for comparison",
)

EXTREME_ENVIRONMENT_DATA: list[EcosystemEnergyZone] = [
    MOVILE_CAVE_MICROBIAL_MAT,
    MOVILE_CAVE_BACKGROUND,
]


def energy_concentration_ratio() -> float:
    """Ratio of microbial-mat energy output to background in Movile Cave."""
    return (MOVILE_CAVE_MICROBIAL_MAT.energy_output_uw_per_g /
            MOVILE_CAVE_BACKGROUND.energy_output_uw_per_g)


# ============================================================================
# 9.  Thermophile Energy Transfer Models
# ============================================================================

@dataclass
class ThermophileEvidence:
    """Summary of thermophile energy-transfer anomaly evidence."""

    horizontal_gene_transfer_pct: float = 24.0
    description: str = (
        "24% horizontal gene transfer between thermophilic archaea and bacteria "
        "sharing energy transfer mechanisms. Extracellular electron transfer through "
        "unknown pathways. Enhanced magnetite crystallisation increasing energy "
        "conservation. Some exoelectrogens lack cytochromes — alternative energy "
        "transfer required."
    )


THERMOPHILE_EVIDENCE = ThermophileEvidence()


# ============================================================================
# 10. Energy Transfer Mechanism Comparison
# ============================================================================

@dataclass
class TransferMechanism:
    """An energy transfer mechanism with its physical parameters."""

    name: str
    distance_range: str
    timescale: str
    biological_evidence: str


TRANSFER_MECHANISMS: list[TransferMechanism] = [
    TransferMechanism("FRET (Forster)", "1-10 nm", "ps-ns",
                      "Photosynthesis, GFP systems"),
    TransferMechanism("Dexter (exchange)", "<2 nm", "ps",
                      "Chloroplast energy transfer"),
    TransferMechanism("Radiative", "Unlimited", "ns-us",
                      "Bioluminescence signalling"),
    TransferMechanism("Exciton migration", "10-100 nm", "ps-ns",
                      "Bacterial light-harvesting"),
    TransferMechanism("Waveguide/plasmon", "um-mm", "ps-ns",
                      "Hypothesised in microbial mats"),
]


# ============================================================================
# 11. Trophic-Level Energy Budget (10% rule revision)
# ============================================================================

def revised_energy_budget(e_biomass: float,
                          e_metabolic: float,
                          e_fret_coupling: float,
                          e_heat: float) -> dict:
    """Revised trophic-level energy budget.

    E_in = E_biomass + E_metabolic + E_FRET_coupling + E_heat

    Traditional models set E_FRET_coupling = 0 and attribute ~90% to E_heat.
    The FRET hypothesis redistributes that energy.

    Returns
    -------
    dict
        Budget breakdown and total.
    """
    total = e_biomass + e_metabolic + e_fret_coupling + e_heat
    return {
        "e_biomass": e_biomass,
        "e_metabolic": e_metabolic,
        "e_fret_coupling": e_fret_coupling,
        "e_heat": e_heat,
        "e_total": total,
        "fret_fraction": e_fret_coupling / total if total > 0 else 0.0,
        "heat_fraction": e_heat / total if total > 0 else 0.0,
    }


# ============================================================================
# 12. FRET Integration Term (links to energy_framework.py)
# ============================================================================

def fret_coupling_energy(eta: np.ndarray,
                         f_donor: np.ndarray,
                         eps_acceptor: np.ndarray,
                         dv: float = 1.0,
                         d_lambda: float = 1.0) -> float:
    """Compute FRET coupling energy for insertion into the total energy budget.

    E_FRET = integral eta(r, lambda) * F_D(lambda) * eps_A(lambda) dV d(lambda)

    Simplified discrete version: sum over grid points.

    Parameters
    ----------
    eta : ndarray
        Spatially-resolved transfer efficiency grid.
    f_donor : ndarray
        Donor emission values (broadcastable with eta).
    eps_acceptor : ndarray
        Acceptor absorption values (broadcastable with eta).
    dv : float
        Volume element.
    d_lambda : float
        Wavelength element.

    Returns
    -------
    float
        Total FRET coupling energy (arbitrary units; scale with physical constants).
    """
    return float(np.sum(eta * f_donor * eps_acceptor) * dv * d_lambda)


# ============================================================================
# CLI self-test
# ============================================================================

if __name__ == "__main__":
    print("=== FRET Ecosystem Framework Self-Test ===\n")

    # Classical FRET
    r0 = 5.0  # nm
    distances = np.array([2.5, 5.0, 10.0, 15.0])
    effs = fret_efficiency(r0, distances)
    print(f"FRET efficiency at r={distances} nm (R0={r0}): {np.round(effs, 4)}")

    # Effective radius
    r_eff = effective_forster_radius(5.0, 1000, q_cavity=1.5)
    print(f"Effective R0 (1000 emitters, Q=1.5): {r_eff:.2f} nm")

    # Orientation factor
    k2 = orientation_factor(0.0, np.pi / 4, np.pi / 4)
    print(f"kappa^2 (theta_T=0, theta_D=pi/4, theta_A=pi/4): {k2:.4f}")

    # Multi-hop
    eff_10 = multihop_efficiency(0.90, 10)
    print(f"10-hop cascade (90% per hop): {eff_10:.4f}")

    # Error rate
    err = multihop_error_rate(0.80, 0.05, 10)
    print(f"10-hop error rate (80% eff, 5% crosstalk): {err:.4f}")

    # Cavity resonance
    omega = cavity_resonance_frequency(0.1, 0.1, 0.1, m=1, n=1, p=1)
    freq_ghz = omega / (2 * np.pi * 1e9)
    print(f"Cavity resonance (10cm cube, water): {freq_ghz:.2f} GHz")

    # Branching efficiency
    phi = fret_branching_efficiency(1e9, 1e8, 5e8, 0)
    print(f"FRET branching efficiency: {phi:.4f}")

    # Isolation radius
    r_iso = isolation_radius(5.0)
    print(f"Isolation radius (R0=5nm): {r_iso} nm")

    # Organism database
    candidates = fret_candidate_organisms()
    print(f"\nFRET candidate organisms ({len(candidates)}):")
    for o in candidates:
        print(f"  - {o.name} ({o.spectrum_band})")

    # Energy concentration
    ratio = energy_concentration_ratio()
    print(f"\nMovile Cave energy concentration ratio: {ratio:.0f}x")

    # Revised budget
    budget = revised_energy_budget(10, 30, 40, 20)
    print(f"Revised budget: FRET fraction={budget['fret_fraction']:.0%}, "
          f"heat fraction={budget['heat_fraction']:.0%}")

    print("\nAll checks passed.")
