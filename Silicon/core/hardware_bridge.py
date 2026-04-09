# STATUS: infrastructure — closes physics gaps between DFT, FRET, and bridge pipeline
"""
hardware_bridge.py — First-principles physics bridge
=====================================================
Connects three previously disconnected layers:

    DFT formation energy (eV)  →  k_well (eV/Å²)  →  T₂ (ms)
    FRET coupling (1/r⁶)       →  k_well contribution
    Tensor eigenvalues (dimless) →  physical magnetic energy (eV)

GAP 1 (dft_to_kwell): DFT produces E_f(ε, d) in eV. The confinement
    stiffness k_well is the *curvature* of the energy landscape at
    equilibrium: k = ∂²E_f/∂x². Given DFT results at multiple strains,
    this is a finite-difference second derivative.

GAP 2 (physical_magnetic_energy): octahedral_tensor.py normalises T so
    trace(T)=1 (dimensionless geometry). The physical magnetic coupling
    energy is E_mag = -μ_B × g × (B^T T B), with units of eV.

GAP 3 (fret_confinement): FRET dipole-dipole coupling at the Er-P
    separation creates a restoring force that contributes to k_well.
    At inter-site distance d, U_fret ∝ (R₀/d)⁶, and the curvature
    of that potential is ∂²U/∂d² = 42 × ΔE × R₀⁶ / d⁸.

All functions use SI-derived units (eV, Å, T) matching existing modules.
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Physical constants (consistent with octahedral_sim.py & magnetic_bridge_protocol.py)
# ---------------------------------------------------------------------------

MU_BOHR   = 5.7883818012e-5   # eV/T   Bohr magneton
G_FACTOR  = 2.0023193          # electron g-factor
K_B       = 8.617333e-5        # eV/K   Boltzmann constant
H_PLANCK  = 4.135667696e-15   # eV·s   Planck constant

# FRET parameters (from fret_coulomb_analysis.py, converted to Å/eV)
R_0_FRET_ANG   = 15.0          # Å   Förster radius (~1.5 nm)
NU_TRANSITION  = 1.0e12        # Hz  octahedral state transition frequency
DELTA_E_TRANS  = H_PLANCK * NU_TRANSITION  # eV  ≈ 4.1 meV


# =========================================================================
# GAP 1: DFT Formation Energy → Confinement Stiffness (k_well)
# =========================================================================

@dataclass
class DFTPoint:
    """A single DFT calculation result at one strain/displacement."""
    strain_pct: float       # biaxial strain (%)
    displacement_ang: float # Er displacement from ideal site (Å)
    total_energy_eV: float  # total system energy (eV)


def dft_to_kwell(points: List[DFTPoint],
                 strain_pct: Optional[float] = None) -> Tuple[float, float, float]:
    """
    Extract confinement stiffness k_well from DFT total energies.

    Uses finite-difference second derivative of total energy with respect
    to Er displacement at a given strain:

        k_well = ∂²E_total / ∂x²  evaluated at equilibrium

    This is the harmonic approximation to the confining potential —
    the same quantity that determines phonon-mediated dephasing via
    σ_T² = k_B T / k_well  (octahedral_sim.py line 88).

    Parameters
    ----------
    points : list of DFTPoint
        DFT results. Must include at least 3 points at the same strain
        with different displacements (for parabolic fit).
    strain_pct : float, optional
        Filter to points at this strain. If None, uses all points.

    Returns
    -------
    k_well : float
        Confinement stiffness (eV/Å²)
    x_eq : float
        Equilibrium displacement (Å) — minimum of fitted parabola
    E_min : float
        Energy at equilibrium (eV)

    Raises
    ------
    ValueError
        If fewer than 3 points available for fitting.
    """
    if strain_pct is not None:
        pts = [p for p in points if abs(p.strain_pct - strain_pct) < 1e-6]
    else:
        pts = list(points)

    if len(pts) < 3:
        raise ValueError(
            f"Need ≥3 DFT points for parabolic fit, got {len(pts)}. "
            f"Run DFT at multiple Er displacements for the same strain."
        )

    x = np.array([p.displacement_ang for p in pts])
    E = np.array([p.total_energy_eV for p in pts])

    # Fit parabola: E(x) = a*x² + b*x + c
    # k_well = 2a (curvature), x_eq = -b/(2a), E_min = c - b²/(4a)
    coeffs = np.polyfit(x, E, 2)
    a, b, c = coeffs

    if a <= 0:
        raise ValueError(
            f"Negative curvature (a={a:.4f} eV/Å²): energy landscape is not "
            f"confining at this strain. Check DFT convergence."
        )

    k_well = 2.0 * a
    x_eq = -b / (2.0 * a)
    E_min = c - b**2 / (4.0 * a)

    return k_well, x_eq, E_min


def dft_strain_scan_to_kwell(points: List[DFTPoint],
                              strains: List[float]) -> List[Tuple[float, float]]:
    """
    Compute k_well at each strain from a set of DFT displacement scans.

    Parameters
    ----------
    points : list of DFTPoint
        Full DFT dataset across multiple strains and displacements.
    strains : list of float
        Strain values (%) to evaluate.

    Returns
    -------
    List of (strain_pct, k_well) tuples.
    """
    results = []
    for eps in strains:
        try:
            kw, _, _ = dft_to_kwell(points, strain_pct=eps)
            results.append((eps, kw))
        except ValueError:
            # Not enough points at this strain — skip
            pass
    return results


# =========================================================================
# GAP 2: Physical Magnetic Energy (dimensioned)
# =========================================================================

def physical_magnetic_energy(
    eigenvalues: Tuple[float, float, float],
    B_vec: np.ndarray,
) -> float:
    """
    Physical magnetic coupling energy from tensor eigenvalues.

    Closes the gap between octahedral_tensor.py (normalised, dimensionless T)
    and magnetic_bridge_protocol.py (energy measurements in eV).

    The octahedral tensor T is a geometric projection (trace=1).
    The physical magnetic energy at each site is:

        E_mag = -μ_B × g × Σ_i λ_i × B_i²

    where λ_i are the eigenvalues and B_i are the field components
    along the principal axes.

    Parameters
    ----------
    eigenvalues : (λ₁, λ₂, λ₃)
        Normalised tensor eigenvalues (dimensionless, from octahedral_tensor.py).
    B_vec : (3,) array
        External magnetic field vector (T).

    Returns
    -------
    E_mag : float
        Magnetic energy (eV). Negative = favoured alignment.
    """
    lam = np.array(eigenvalues, dtype=np.float64)
    B = np.asarray(B_vec, dtype=np.float64)

    # Sort B components to align with eigenvalue ordering (descending)
    B_sq = np.sort(B**2)[::-1]

    return -MU_BOHR * G_FACTOR * float(np.dot(lam, B_sq))


def measurement_energy_to_eigenvalue(
    E_measured: float,
    B_field: float,
) -> float:
    """
    Invert a single magnetic energy measurement to recover one eigenvalue.

    This is the equation used in magnetic_bridge_protocol.py
    reconstruct_tensor(), but made explicit with physical units:

        λ_i = -E_measured / (μ_B × g × B²)

    Parameters
    ----------
    E_measured : float
        Energy measurement (eV) from probe pulse along axis i.
    B_field : float
        Probe field magnitude (T).

    Returns
    -------
    lambda_i : float
        Recovered eigenvalue (dimensionless).
    """
    denom = MU_BOHR * G_FACTOR * B_field**2
    return -E_measured / denom


# =========================================================================
# GAP 3: FRET Confinement Contribution to k_well
# =========================================================================

def fret_coupling_energy(d_ang: float,
                         R_0: float = R_0_FRET_ANG,
                         delta_E: float = DELTA_E_TRANS) -> float:
    """
    FRET coupling energy between adjacent octahedral sites.

        U_fret(d) = ΔE × (R₀/d)⁶

    Parameters
    ----------
    d_ang : float
        Inter-site distance (Å).
    R_0 : float
        Förster radius (Å). Default: 15 Å (~1.5 nm).
    delta_E : float
        Transition energy (eV). Default: ~4.1 meV.

    Returns
    -------
    U : float
        Coupling energy (eV).
    """
    if d_ang <= 0:
        raise ValueError(f"Distance must be positive, got {d_ang}")
    return delta_E * (R_0 / d_ang) ** 6


def fret_confinement_stiffness(d_ang: float,
                                R_0: float = R_0_FRET_ANG,
                                delta_E: float = DELTA_E_TRANS) -> float:
    """
    FRET contribution to confinement stiffness (k_fret).

    The restoring force from FRET coupling creates an effective
    potential well around the equilibrium distance. The stiffness is
    the second derivative of U_fret(d):

        ∂U/∂d  = -6 × ΔE × R₀⁶ / d⁷
        ∂²U/∂d² = 42 × ΔE × R₀⁶ / d⁸

    This is the FRET contribution to the total k_well:

        k_well_total = k_well_DFT + k_fret

    Parameters
    ----------
    d_ang : float
        Er-P separation distance (Å).
    R_0 : float
        Förster radius (Å).
    delta_E : float
        Transition energy (eV).

    Returns
    -------
    k_fret : float
        FRET confinement stiffness (eV/Å²).
    """
    if d_ang <= 0:
        raise ValueError(f"Distance must be positive, got {d_ang}")
    return 42.0 * delta_E * R_0**6 / d_ang**8


def total_kwell(k_dft: float, d_ang: float,
                R_0: float = R_0_FRET_ANG,
                delta_E: float = DELTA_E_TRANS) -> float:
    """
    Total confinement stiffness: DFT lattice term + FRET coupling term.

        k_total = k_DFT + k_FRET(d)

    This connects er_dft_framework.py (→ k_DFT via dft_to_kwell)
    and fret_coulomb_analysis.py (→ k_FRET) into a single
    quantity that feeds octahedral_sim.py's decoherence model.

    Parameters
    ----------
    k_dft : float
        DFT-derived stiffness (eV/Å²), from dft_to_kwell().
    d_ang : float
        Er-P separation distance (Å).

    Returns
    -------
    k_total : float
        Total confinement stiffness (eV/Å²).
    """
    return k_dft + fret_confinement_stiffness(d_ang, R_0, delta_E)


# =========================================================================
# Convenience: full pipeline from DFT results to T₂
# =========================================================================

def dft_to_T2(points: List[DFTPoint],
              strain_pct: float,
              d_ang: float,
              temperature: float = 300.0,
              isotope_fraction: float = 0.047) -> dict:
    """
    Full physics chain: DFT results → k_well → T₂.

    Closes the loop from first-principles quantum chemistry through to
    the coherence time that determines computational fidelity.

    Parameters
    ----------
    points : list of DFTPoint
        DFT total energies at multiple displacements for the given strain.
    strain_pct : float
        Biaxial strain (%).
    d_ang : float
        Er-P separation distance (Å).
    temperature : float
        Temperature (K). Default 300 K.
    isotope_fraction : float
        ²⁹Si fraction. Default 0.047 (natural abundance).

    Returns
    -------
    dict with:
        k_dft      : DFT-derived stiffness (eV/Å²)
        k_fret     : FRET contribution (eV/Å²)
        k_total    : combined stiffness (eV/Å²)
        sigma_T    : RMS thermal displacement (Å)
        gamma_total: total decoherence rate (Hz)
        T2_ms      : coherence time (ms)
        x_eq       : equilibrium displacement (Å)
    """
    # GAP 1: DFT → k_well
    k_dft, x_eq, E_min = dft_to_kwell(points, strain_pct=strain_pct)

    # GAP 3: FRET → k_well contribution
    k_fret = fret_confinement_stiffness(d_ang)

    # Total confinement
    k_total = k_dft + k_fret

    # Thermal displacement: σ_T = √(k_B T / k_well)
    sigma_T = np.sqrt(K_B * temperature / k_total)

    # Decoherence rates (same model as octahedral_sim.py)
    # Phonon: Γ_ph ∝ k_B T / k_well (∝ σ_T²)
    # Calibrated: Γ_ph = 4.99 Hz at k_well = 8.5 eV/Å², T = 300 K
    K_WELL_REF = 8.5    # eV/Å² (reference point)
    GAMMA_PH_0 = 4.99   # Hz at reference
    GAMMA_BAT_0 = 0.90  # Hz (²⁹Si bath)
    GAMMA_TH_0 = 0.12   # Hz (thermal/readout)

    gamma_ph = GAMMA_PH_0 * (K_WELL_REF / k_total) * (temperature / 300.0)
    gamma_bat = GAMMA_BAT_0 * (isotope_fraction / 0.047)
    gamma_th = GAMMA_TH_0

    gamma_total = gamma_ph + gamma_bat + gamma_th
    T2_ms = 1000.0 / gamma_total

    return {
        'k_dft': k_dft,
        'k_fret': k_fret,
        'k_total': k_total,
        'sigma_T_ang': sigma_T,
        'gamma_phonon_Hz': gamma_ph,
        'gamma_bath_Hz': gamma_bat,
        'gamma_thermal_Hz': gamma_th,
        'gamma_total_Hz': gamma_total,
        'T2_ms': T2_ms,
        'x_eq_ang': x_eq,
        'E_min_eV': E_min,
    }


# =========================================================================
# Demo / self-test
# =========================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("Hardware Bridge: First-Principles Physics Chain")
    print("DFT → k_well → T₂, with FRET + magnetic coupling")
    print("=" * 70)

    # --- GAP 1 demo: synthetic DFT data ---
    print("\n--- GAP 1: DFT → k_well ---")
    # Simulate DFT displacement scan at optimal strain (1.2%)
    # Parabolic potential: E(x) = E_0 + ½ k x² with k=8.5 eV/Å²
    np.random.seed(42)
    k_true = 8.5  # eV/Å²
    E_0 = -1000.0  # eV (typical DFT total energy)
    displacements = np.linspace(-0.3, 0.3, 7)  # Å
    energies = E_0 + 0.5 * k_true * displacements**2
    # Add small DFT noise
    energies += np.random.normal(0, 0.001, len(energies))

    points = [DFTPoint(strain_pct=1.2, displacement_ang=x, total_energy_eV=E)
              for x, E in zip(displacements, energies)]

    k_recovered, x_eq, E_min = dft_to_kwell(points, strain_pct=1.2)
    print(f"  True k_well:      {k_true:.3f} eV/Å²")
    print(f"  Recovered k_well: {k_recovered:.3f} eV/Å²")
    print(f"  Equilibrium x:    {x_eq:.4f} Å")
    print(f"  Error:            {abs(k_recovered - k_true)/k_true*100:.2f}%")

    # --- GAP 3 demo: FRET confinement ---
    print("\n--- GAP 3: FRET confinement contribution ---")
    for d in [3.0, 4.8, 6.0, 8.0, 10.0]:
        k_f = fret_confinement_stiffness(d)
        U_f = fret_coupling_energy(d)
        print(f"  d = {d:.1f} Å: U_fret = {U_f*1e3:.4f} meV, "
              f"k_fret = {k_f:.4f} eV/Å²")

    # --- Full chain demo ---
    print("\n--- Full chain: DFT + FRET → T₂ ---")
    d_ErP = 4.8  # Å
    result = dft_to_T2(points, strain_pct=1.2, d_ang=d_ErP)
    print(f"  k_DFT   = {result['k_dft']:.3f} eV/Å²")
    print(f"  k_FRET  = {result['k_fret']:.4f} eV/Å²")
    print(f"  k_total = {result['k_total']:.3f} eV/Å²")
    print(f"  σ_T     = {result['sigma_T_ang']*100:.2f} pm")
    print(f"  Γ_total = {result['gamma_total_Hz']:.2f} Hz")
    print(f"  T₂      = {result['T2_ms']:.1f} ms")

    # --- GAP 2 demo: physical magnetic energy ---
    print("\n--- GAP 2: Physical magnetic energy ---")
    from Silicon.core.octahedral_sim import STATES
    B_probe = np.array([0.0, 0.0, 1.0])  # 1T along z

    print(f"  {'State':>5} {'Gray':>4} {'Eigenvalues':>15} {'E_mag (μeV)':>12}")
    for gray, eigs, E_meV in STATES:
        E_mag = physical_magnetic_energy(eigs, B_probe)
        lam_recovered = measurement_energy_to_eigenvalue(E_mag, 1.0)
        print(f"  {gray:>5b} {gray:>4} {str(eigs):>15} {E_mag*1e6:>12.3f}")

    print("\n" + "=" * 70)
    print("Chain complete: DFT (eV) → k_well (eV/Å²) → T₂ (ms)")
    print("               FRET (1/r⁶) → k_fret (eV/Å²) → k_total")
    print("               Eigenvalues → μ_B × g × λ → E_mag (eV)")
    print("=" * 70)
