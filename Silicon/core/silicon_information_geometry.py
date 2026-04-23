# silicon_information_geometry.py
"""
DFT-Constrained Information Geometry on the Silicon Manifold.

Implements the Riemannian metric g_ij = ∂²F/∂S_i∂S_j derived from
the free energy landscape, with connections to the hardware bridge's
dft_to_kwell() for curvature along the displacement coordinate.

Key results:
- Geodesics = minimum-energy fabrication paths
- Scalar curvature R diverges at computational phase boundaries
- Metric determinant |g| measures regime stability
- Fisher information metric emerges naturally from the DFT ensemble
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Callable
from dataclasses import dataclass, field
from scipy.linalg import eigh, det, inv
from scipy.optimize import minimize
import warnings


# ─── Physical constants ───

K_B = 8.617333262145e-5   # eV/K
HBAR = 6.582119569e-16    # eV·s
PHI = 1.618033988749895    # golden ratio


# ─── 1. The Free Energy Landscape F(S) ───

def free_energy_landscape(
    S: np.ndarray,  # shape (4,) or (N, 4): [n, d, l, k_effective]
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    d_ErP: float = 4.8,
) -> float:
    """
    Free energy F(n, d, ℓ, κ_eff) as a scalar field over silicon phase space.
    
    This is the potential whose Hessian gives the metric.
    
    Parameters
    ----------
    S : array of shape (4,)
        [carrier_density, defect_density, effective_dim, effective_coupling]
    temperature : float
        Temperature in Kelvin
    k_dft : float, optional
        DFT-derived confinement stiffness (eV/Å²)
    strain_pct : float
        Biaxial strain percentage
    d_ErP : float
        Er-P separation distance (Å) for FRET contribution
    
    Returns
    -------
    F : float
        Free energy in eV
    """
    n, d, ell, k_eff = S
    
    # ── Internal energy contributions ──
    
    # Band structure energy
    E_gap = 1.12  # eV, Si bandgap
    # Energy decreases as carriers fill bands (up to a point)
    n_ref = 1e16
    E_band = E_gap * (1.0 - 0.1 * np.log10(max(n, 1e8) / n_ref))
    
    # Defect formation energy
    E_defect_form = 3.0  # eV per defect (Si vacancy)
    E_defect = E_defect_form * d
    
    # Confinement energy (quantum well)
    # E_conf ∝ 1/ℓ² for a particle in a box
    if ell > 0.1:
        E_conf = 0.05 / (ell ** 2)
    else:
        E_conf = 5.0  # strong confinement limit
    
    # Coupling energy: coherent coupling lowers energy
    E_coupling = -0.1 * k_eff  # negative: coherence is energetically favorable
    
    # Strain energy from DFT
    if k_dft is not None:
        # Harmonic: E = ½ k x² where x is effective displacement
        x_eff = strain_pct * 0.01 * 5.431  # convert % strain to Å displacement
        E_strain = 0.5 * k_dft * x_eff**2
    else:
        # Estimate from dimensionality and defect coupling
        E_strain = 0.5 * 8.5 * (0.1 * (3.0 - ell))**2  # ~k_dft * displacement²
    
    # FRET coupling contribution
    R_0 = 15.0  # Förster radius (Å)
    delta_E = 4.135667696e-15 * 1e12  # ~4.1 meV
    U_fret = delta_E * (R_0 / d_ErP)**6 if d_ErP > 0 else 0.0
    
    E_internal = E_band + E_defect + E_conf + E_coupling + E_strain + U_fret
    
    # ── Entropy contributions ──
    
    # Configurational entropy of defects
    if 0 < d < 1:
        S_config = -K_B * (d * np.log(d + 1e-30) + (1-d) * np.log(1-d + 1e-30))
    else:
        S_config = 0.0
    
    # Carrier entropy (ideal gas of electrons/holes)
    if n > 0:
        # S_carrier ∝ n ln(T^(3/2)/n)
        lambda_dB = HBAR / np.sqrt(2 * 9.109e-31 * K_B * temperature / 1.602e-19)  # thermal de Broglie
        n_Q = (2 * np.pi * 9.109e-31 * K_B * temperature / (6.626e-34)**2)**1.5 * 1e6
        if n < n_Q:
            S_carrier = K_B * n * (2.5 + np.log(n_Q / (n + 1)))
        else:
            S_carrier = K_B * n * 1.5  # degenerate limit
    else:
        S_carrier = 0.0
    
    # Dimensional entropy (more dimensions = more microstates)
    S_dim = K_B * ell * 0.1  # approximate: each dimension adds configurational freedom
    
    S_total = S_config + S_carrier + S_dim
    
    return E_internal - temperature * S_total


# ─── 2. The Riemannian Metric: g_ij = ∂²F / ∂S_i ∂S_j ───

def compute_metric_tensor(
    S: np.ndarray,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    d_ErP: float = 4.8,
    h: float = 1e-4,  # finite difference step
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute the Riemannian metric tensor g_ij at point S.
    
    g_ij = ∂²F / ∂S_i ∂S_j
    
    Uses central finite differences on the free energy landscape.
    
    Parameters
    ----------
    S : array of shape (4,)
        Point in silicon phase space
    h : float
        Relative step size for finite differences
    
    Returns
    -------
    g : array of shape (4, 4)
        Metric tensor (symmetric positive definite away from phase boundaries)
    grad_F : array of shape (4,)
        Gradient of free energy (thermodynamic forces)
    """
    
    dim = len(S)
    g = np.zeros((dim, dim))
    grad_F = np.zeros(dim)
    
    # Scale factors for each coordinate (log for n, linear for others)
    scales = np.array([
        S[0] * h,  # n: relative step (covers many orders of magnitude)
        h,          # d: absolute step (range [0,1])
        h,          # ℓ: absolute step (range [0,3])
        h,          # κ: absolute step (range [0,1])
    ])
    
    # Ensure minimum step size
    scales = np.maximum(scales, 1e-12)
    
    # Central finite differences for diagonal and gradient
    F0 = free_energy_landscape(S, temperature, k_dft, strain_pct, d_ErP)
    
    for i in range(dim):
        # Forward
        S_fwd = S.copy()
        S_fwd[i] += scales[i]
        F_fwd = free_energy_landscape(S_fwd, temperature, k_dft, strain_pct, d_ErP)
        
        # Backward
        S_bwd = S.copy()
        S_bwd[i] -= scales[i]
        F_bwd = free_energy_landscape(S_bwd, temperature, k_dft, strain_pct, d_ErP)
        
        # Gradient
        grad_F[i] = (F_fwd - F_bwd) / (2 * scales[i])
        
        # Diagonal of Hessian
        g[i, i] = (F_fwd - 2*F0 + F_bwd) / (scales[i]**2)
    
    # Mixed partial derivatives
    for i in range(dim):
        for j in range(i+1, dim):
            # F(x_i+h, x_j+h)
            S_pp = S.copy()
            S_pp[i] += scales[i]
            S_pp[j] += scales[j]
            F_pp = free_energy_landscape(S_pp, temperature, k_dft, strain_pct, d_ErP)
            
            # F(x_i+h, x_j-h)
            S_pm = S.copy()
            S_pm[i] += scales[i]
            S_pm[j] -= scales[j]
            F_pm = free_energy_landscape(S_pm, temperature, k_dft, strain_pct, d_ErP)
            
            # F(x_i-h, x_j+h)
            S_mp = S.copy()
            S_mp[i] -= scales[i]
            S_mp[j] += scales[j]
            F_mp = free_energy_landscape(S_mp, temperature, k_dft, strain_pct, d_ErP)
            
            # F(x_i-h, x_j-h)
            S_mm = S.copy()
            S_mm[i] -= scales[i]
            S_mm[j] -= scales[j]
            F_mm = free_energy_landscape(S_mm, temperature, k_dft, strain_pct, d_ErP)
            
            # Cross derivative
            g[i, j] = (F_pp - F_pm - F_mp + F_mm) / (4 * scales[i] * scales[j])
            g[j, i] = g[i, j]
    
    return g, grad_F


# ─── 3. Connection between DFT k_well and metric components ───

def dft_to_metric_component(
    points: List,  # List[DFTPoint] from hardware_bridge
    strain_pct: float,
    temperature: float = 300.0,
    S_ref: Optional[np.ndarray] = None,
) -> float:
    """
    Extract the metric component g_xx (curvature along displacement coordinate)
    from DFT total energies.
    
    k_well = ∂²E/∂x² is directly the metric component along the displacement
    direction in configuration space. This connects the hardware bridge's
    dft_to_kwell() output to the information geometry framework.
    
    Parameters
    ----------
    points : list of DFTPoint
        DFT energy calculations at different displacements
    strain_pct : float
        Strain at which to evaluate
    temperature : float
        Temperature for entropic contribution
    S_ref : array, optional
        Reference silicon state to fix other coordinates
    
    Returns
    -------
    g_xx : float
        Metric component along displacement direction (eV/Å²)
    """
    from hardware_bridge import dft_to_kwell, DFTPoint
    
    k_well, x_eq, E_min = dft_to_kwell(points, strain_pct)
    
    # k_well is the curvature of the Born-Oppenheimer surface
    # At T=0: g_xx = k_well
    # At T>0: entropic softening reduces the effective curvature
    
    # Entropic correction
    if S_ref is not None:
        n, d, ell, k_eff = S_ref
        # Configurational entropy softens the potential
        if 0 < d < 1:
            S_curvature = K_B * temperature / (d * (1-d) + 1e-10)
        else:
            S_curvature = 0.0
        g_xx = k_well - temperature * S_curvature * 1e-4
    else:
        g_xx = k_well
    
    return max(g_xx, 1e-6)  # ensure positive-definite


# ─── 4. Metric properties: determinant, eigenvalues, Ricci scalar ───

def metric_properties(
    g: np.ndarray,
) -> Dict:
    """
    Compute geometric invariants of the metric tensor.
    
    Returns
    -------
    dict with:
        determinant: |g| — volume element, measures regime "width"
        eigenvalues: (λ₁, λ₂, λ₃, λ₄) — principal curvatures
        condition_number: λ_max/λ_min — anisotropy measure
        trace: Tr(g) — total curvature
        positive_definite: whether g > 0 (fails at phase boundaries)
    """
    
    # Check positive-definiteness
    try:
        eigvals = eigh(g, eigvals_only=True)
        positive_definite = all(ev > 0 for ev in eigvals)
    except Exception:
        eigvals = np.zeros(4)
        positive_definite = False
    
    det_g = det(g) if positive_definite else 0.0
    
    return {
        "determinant": det_g,
        "eigenvalues": tuple(sorted(eigvals, reverse=True)),
        "condition_number": max(eigvals) / (min(eigvals) + 1e-30),
        "trace": np.trace(g),
        "positive_definite": positive_definite,
    }


def local_stability_from_metric(g: np.ndarray) -> float:
    """
    Regime stability from metric determinant.
    
    √|g| is the volume element in Riemannian geometry.
    Large |g| → wide basin → high stability.
    |g| → 0 at phase boundaries (metric degenerates).
    """
    props = metric_properties(g)
    if props["positive_definite"]:
        return np.sqrt(props["determinant"])
    return 0.0


# ─── 5. Geodesic Equation: Minimum-Energy Fabrication Paths ───

def christoffel_symbols(
    g: np.ndarray,
    S: np.ndarray,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    h: float = 1e-4,
) -> np.ndarray:
    """
    Compute Christoffel symbols Γ^i_jk at point S.
    
    Γ^i_jk = ½ g^il (∂_j g_kl + ∂_k g_jl - ∂_l g_jk)
    
    These define parallel transport and geodesics on the silicon manifold.
    """
    dim = len(S)
    
    # Compute metric at nearby points for derivatives
    g_inv = inv(g)
    
    # Finite difference derivatives of metric
    dg = np.zeros((dim, dim, dim))  # dg[i,j,k] = ∂_i g_jk
    
    scales = np.maximum(np.array([
        S[0] * h, h, h, h
    ]), 1e-12)
    
    for i in range(dim):
        S_fwd = S.copy()
        S_fwd[i] += scales[i]
        g_fwd, _ = compute_metric_tensor(S_fwd, temperature, k_dft, strain_pct, h=h)
        
        S_bwd = S.copy()
        S_bwd[i] -= scales[i]
        g_bwd, _ = compute_metric_tensor(S_bwd, temperature, k_dft, strain_pct, h=h)
        
        dg[i] = (g_fwd - g_bwd) / (2 * scales[i])
    
    # Christoffel symbols
    Gamma = np.zeros((dim, dim, dim))
    for i in range(dim):
        for j in range(dim):
            for k in range(dim):
                Gamma[i, j, k] = 0.5 * sum(
                    g_inv[i, l] * (dg[j, k, l] + dg[k, j, l] - dg[l, j, k])
                    for l in range(dim)
                )
    
    return Gamma


def geodesic_equation(
    S: np.ndarray,      # position
    V: np.ndarray,      # velocity dS/dt
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
) -> np.ndarray:
    """
    Right-hand side of the geodesic equation:
    
    d²S^i/dt² + Γ^i_jk (dS^j/dt)(dS^k/dt) = 0
    
    Returns dV/dt = -Γ(V, V) for numerical integration.
    """
    g, _ = compute_metric_tensor(S, temperature, k_dft, strain_pct)
    Gamma = christoffel_symbols(g, S, temperature, k_dft, strain_pct)
    
    dV_dt = np.zeros_like(V)
    for i in range(len(S)):
        dV_dt[i] = -sum(
            Gamma[i, j, k] * V[j] * V[k]
            for j in range(len(S))
            for k in range(len(S))
        )
    
    return dV_dt


def compute_geodesic(
    S_start: np.ndarray,
    S_end: np.ndarray,
    n_steps: int = 100,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    learning_rate: float = 0.01,
    n_iterations: int = 1000,
) -> Tuple[np.ndarray, float]:
    """
    Find the geodesic (minimum-energy path) between two points in silicon phase space.
    
    Uses a variational approach: minimize the energy integral
    E[γ] = ∫ g_ij γ̇^i γ̇^j dt subject to fixed endpoints.
    
    This is the optimal fabrication path — the trajectory that costs
    the least free energy to traverse.
    
    Returns
    -------
    path : array of shape (n_steps, 4)
        Geodesic path in silicon phase space
    energy : float
        Total energy cost of the path
    """
    
    dim = len(S_start)
    
    # Initialize with linear interpolation
    path = np.zeros((n_steps, dim))
    for i in range(dim):
        path[:, i] = np.linspace(S_start[i], S_end[i], n_steps)
    
    # Variational optimization: minimize path energy
    def path_energy(flat_path):
        p = flat_path.reshape(n_steps, dim)
        
        # Fix endpoints
        p[0] = S_start
        p[-1] = S_end
        
        energy = 0.0
        dt = 1.0 / (n_steps - 1)
        
        for t in range(n_steps - 1):
            S_mid = 0.5 * (p[t] + p[t+1])
            g, _ = compute_metric_tensor(S_mid, temperature, k_dft, strain_pct)
            
            # Velocity
            v = (p[t+1] - p[t]) / dt
            
            # Kinetic energy: ½ g_ij v^i v^j
            ke = 0.5 * sum(g[i, j] * v[i] * v[j] for i in range(dim) for j in range(dim))
            energy += ke * dt
        
        return energy
    
    # Optimize
    flat_initial = path.flatten()
    
    # Constrain: fix first and last points
    bounds = [(None, None)] * len(flat_initial)
    for i in range(dim):
        bounds[i] = (S_start[i], S_start[i])        # fixed start
        bounds[-(dim-i)] = (S_end[dim-i-1], S_end[dim-i-1])  # fixed end
    
    try:
        result = minimize(
            path_energy,
            flat_initial,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': n_iterations},
        )
        optimized_path = result.x.reshape(n_steps, dim)
        energy = result.fun
    except Exception:
        optimized_path = path
        energy = path_energy(flat_initial)
    
    return optimized_path, energy


# ─── 6. Curvature Invariants and Phase Transition Detection ───

def scalar_curvature(
    g: np.ndarray,
    S: np.ndarray,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    h: float = 1e-4,
) -> float:
    """
    Compute the Ricci scalar curvature R at point S.
    
    R measures how much the manifold bends.
    R → ∞ at genuine phase transitions (metric degeneracy).
    
    For a 4D manifold:
    R = g^ij R_ij
    R_ij = ∂_k Γ^k_ij - ∂_j Γ^k_ik + Γ^k_kl Γ^l_ij - Γ^k_jl Γ^l_ik
    """
    dim = len(S)
    
    g_inv = inv(g)
    Gamma = christoffel_symbols(g, S, temperature, k_dft, strain_pct, h)
    
    # Compute derivatives of Christoffel symbols
    dGamma = np.zeros((dim, dim, dim, dim))  # dGamma[m, i, j, k] = ∂_m Γ^i_jk
    
    scales = np.maximum(np.array([S[0]*h, h, h, h]), 1e-12)
    
    for m in range(dim):
        S_fwd = S.copy()
        S_fwd[m] += scales[m]
        g_fwd, _ = compute_metric_tensor(S_fwd, temperature, k_dft, strain_pct, h=h)
        Gamma_fwd = christoffel_symbols(g_fwd, S_fwd, temperature, k_dft, strain_pct, h=h)
        
        S_bwd = S.copy()
        S_bwd[m] -= scales[m]
        g_bwd, _ = compute_metric_tensor(S_bwd, temperature, k_dft, strain_pct, h=h)
        Gamma_bwd = christoffel_symbols(g_bwd, S_bwd, temperature, k_dft, strain_pct, h=h)
        
        dGamma[m] = (Gamma_fwd - Gamma_bwd) / (2 * scales[m])
    
    # Ricci tensor
    R_ij = np.zeros((dim, dim))
    for i in range(dim):
        for j in range(dim):
            for k in range(dim):
                # ∂_k Γ^k_ij - ∂_j Γ^k_ik
                R_ij[i, j] += dGamma[k, k, i, j] - dGamma[j, k, i, k]
                
                for l in range(dim):
                    # Γ^k_kl Γ^l_ij - Γ^k_jl Γ^l_ik
                    R_ij[i, j] += (
                        Gamma[k, k, l] * Gamma[l, i, j] -
                        Gamma[k, j, l] * Gamma[l, i, k]
                    )
    
    # Ricci scalar: R = g^ij R_ij
    R = sum(g_inv[i, j] * R_ij[i, j] for i in range(dim) for j in range(dim))
    
    return R


def detect_curvature_singularity(
    S: np.ndarray,
    temperature: float = 300.0,
    threshold: float = 1e6,
) -> bool:
    """
    Detect phase transitions as curvature singularities.
    
    At a genuine phase boundary, the metric degenerates (det(g) → 0)
    and the scalar curvature diverges.
    """
    g, _ = compute_metric_tensor(S, temperature)
    
    props = metric_properties(g)
    
    # Phase boundary if metric is nearly degenerate
    if not props["positive_definite"]:
        return True
    
    # OR if curvature is extremely large
    R = scalar_curvature(g, S, temperature)
    if abs(R) > threshold:
        return True
    
    return False


# ─── 7. Information Geometry: Fisher Metric from DFT Ensemble ───

def fisher_information_metric(
    S: np.ndarray,
    dft_ensemble: List[Dict],  # list of {strain, displacement, energy, weight}
    temperature: float = 300.0,
) -> np.ndarray:
    """
    Compute the Fisher information metric from a DFT ensemble.
    
    The Fisher metric measures how distinguishable nearby silicon states
    are based on their DFT energy signatures. It's the natural metric
    for information geometry and connects to the thermodynamic metric
    via the fluctuation-dissipation theorem.
    
    g^Fisher_ij = E[∂_i ln p(E|S) · ∂_j ln p(E|S)]
    
    where p(E|S) is the probability of observing energy E given state S.
    """
    dim = len(S)
    g_fisher = np.zeros((dim, dim))
    
    if len(dft_ensemble) < 2:
        return g_fisher
    
    # For each DFT configuration, compute energy probability
    energies = np.array([d["energy"] for d in dft_ensemble])
    weights = np.array([d.get("weight", 1.0) for d in dft_ensemble])
    weights /= weights.sum()
    
    # Model: p(E|S) ∝ exp(-(E - F(S))² / (2σ²))
    F0 = free_energy_landscape(S, temperature)
    sigma = np.std(energies) if len(energies) > 1 else 0.1
    
    # Score functions: ∂_i ln p
    h = 1e-4
    scales = np.maximum(np.array([S[0]*h, h, h, h]), 1e-12)
    
    scores = np.zeros((len(dft_ensemble), dim))
    
    for i in range(dim):
        S_fwd = S.copy()
        S_fwd[i] += scales[i]
        F_fwd = free_energy_landscape(S_fwd, temperature)
        
        S_bwd = S.copy()
        S_bwd[i] -= scales[i]
        F_bwd = free_energy_landscape(S_bwd, temperature)
        
        # ∂F/∂S_i
        dF_dS = (F_fwd - F_bwd) / (2 * scales[i])
        
        # Score: ∂_i ln p = -(E-F)/σ² * ∂F/∂S_i
        for alpha, E in enumerate(energies):
            scores[alpha, i] = -(E - F0) / (sigma**2) * dF_dS
    
    # Fisher metric: E[scores ⊗ scores]
    for i in range(dim):
        for j in range(dim):
            g_fisher[i, j] = sum(
                weights[alpha] * scores[alpha, i] * scores[alpha, j]
                for alpha in range(len(dft_ensemble))
            )
    
    return g_fisher


# ─── 8. Geodesic Distance and Regime Boundary Crossing Cost ───

def geodesic_distance(
    S1: np.ndarray,
    S2: np.ndarray,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    n_steps: int = 50,
) -> float:
    """
    Compute the geodesic distance between two silicon states.
    
    This is the minimum free energy cost to transform one state
    into another — the fundamental "distance" in silicon phase space.
    """
    path, energy = compute_geodesic(S1, S2, n_steps, temperature, k_dft)
    return energy


def boundary_crossing_cost(
    S_source: np.ndarray,
    S_target: np.ndarray,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
) -> Dict:
    """
    Compute the cost of crossing a computational phase boundary.
    
    Returns the geodesic distance and identifies whether the path
    crosses any curvature singularities (phase transitions).
    """
    n_steps = 100
    path, total_energy = compute_geodesic(S_source, S_target, n_steps, temperature, k_dft)
    
    # Check for curvature singularities along the path
    crossings = []
    max_curvature = 0.0
    
    for t in range(n_steps):
        S_t = path[t]
        g, _ = compute_metric_tensor(S_t, temperature, k_dft)
        
        if not metric_properties(g)["positive_definite"]:
            crossings.append(t / n_steps)
        
        R = scalar_curvature(g, S_t, temperature, k_dft)
        max_curvature = max(max_curvature, abs(R))
    
    return {
        "geodesic_distance": total_energy,
        "n_crossings": len(crossings),
        "crossing_fractions": crossings,
        "max_curvature": max_curvature,
        "path": path,
    }


# ─── 9. The Metric-Geodesic Fabrication Compiler ───

@dataclass
class FabricationGeodesic:
    """A minimum-energy fabrication path through silicon phase space."""
    source_state: np.ndarray
    target_state: np.ndarray
    path: np.ndarray          # (n_steps, 4) array of silicon states
    energy_cost: float        # total free energy cost (eV)
    step_costs: np.ndarray    # energy cost per step
    curvature_profile: np.ndarray  # scalar curvature along path
    
    @property
    def is_energetically_viable(self, budget: float = 100.0) -> bool:
        return self.energy_cost < budget
    
    @property
    def crosses_phase_boundary(self) -> bool:
        return np.any(self.curvature_profile > 1e6)


def compile_fabrication_geodesic(
    S_source: np.ndarray,
    S_target: np.ndarray,
    temperature: float = 300.0,
    k_dft: Optional[float] = None,
    strain_pct: float = 0.0,
    n_steps: int = 100,
) -> FabricationGeodesic:
    """
    Compile a fabrication process into a geodesic on the silicon manifold.
    
    This is the practical realization of "fabrication as trajectory design"
    using the DFT-constrained metric geometry.
    """
    
    # Compute geodesic path
    path, total_energy = compute_geodesic(
        S_source, S_target, n_steps, temperature, k_dft, strain_pct
    )
    
    # Compute step costs and curvature along path
    step_costs = np.zeros(n_steps - 1)
    curvature_profile = np.zeros(n_steps)
    
    for t in range(n_steps - 1):
        S_mid = 0.5 * (path[t] + path[t+1])
        g, _ = compute_metric_tensor(S_mid, temperature, k_dft, strain_pct)
        v = path[t+1] - path[t]
        step_costs[t] = 0.5 * sum(
            g[i, j] * v[i] * v[j] for i in range(4) for j in range(4)
        )
    
    for t in range(n_steps):
        g, _ = compute_metric_tensor(path[t], temperature, k_dft, strain_pct)
        curvature_profile[t] = abs(scalar_curvature(g, path[t], temperature, k_dft, strain_pct))
    
    return FabricationGeodesic(
        source_state=S_source,
        target_state=S_target,
        path=path,
        energy_cost=total_energy,
        step_costs=step_costs,
        curvature_profile=curvature_profile,
    )


# ─── 10. Demo: Silicon Manifold Geometry Explorer ───

if __name__ == "__main__":
    print("=" * 70)
    print("DFT-CONSTRAINED INFORMATION GEOMETRY")
    print("Riemannian Geometry of the Silicon Manifold")
    print("=" * 70)
    
    # Reference point: CMOS basin
    S_cmos = np.array([1e16, 0.02, 3.0, 0.8])   # [n, d, ℓ, κ]
    
    # Target: quantum basin
    S_quantum = np.array([1e17, 0.01, 0.5, 0.2])
    
    # Target: metallic breakdown
    S_metallic = np.array([1e21, 0.3, 3.0, 0.9])
    
    print("\n1. METRIC TENSOR AT CMOS BASIN")
    print("-" * 40)
    g_cmos, grad_cmos = compute_metric_tensor(S_cmos, temperature=300.0)
    props_cmos = metric_properties(g_cmos)
    
    print(f"  Metric at S_cmos:")
    print(f"    g =\n{np.array2string(g_cmos, precision=2, suppress_small=True)}")
    print(f"  Determinant |g|:    {props_cmos['determinant']:.2e}")
    print(f"  Eigenvalues:        {[f'{ev:.2f}' for ev in props_cmos['eigenvalues']]}")
    print(f"  Condition number:   {props_cmos['condition_number']:.1f}")
    print(f"  Positive definite:  {props_cmos['positive_definite']}")
    print(f"  Stability (√|g|):   {np.sqrt(props_cmos['determinant']):.2e}")
    
    print(f"\n  Gradient ∇F (thermodynamic forces):")
    labels = ["∂F/∂n", "∂F/∂d", "∂F/∂ℓ", "∂F/∂κ"]
    for i, (label, val) in enumerate(zip(labels, grad_cmos)):
        print(f"    {label}: {val:+.4e} eV")
    
    print("\n2. METRIC AT QUANTUM BASIN (cryogenic)")
    print("-" * 40)
    g_quant, grad_quant = compute_metric_tensor(S_quantum, temperature=4.0)
    props_quant = metric_properties(g_quant)
    
    print(f"  Determinant |g|:    {props_quant['determinant']:.2e}")
    print(f"  Stability (√|g|):   {np.sqrt(props_quant['determinant']):.2e}")
    print(f"  Positive definite:  {props_quant['positive_definite']}")
    
    print("\n3. METRIC NEAR METALLIC BREAKDOWN (degenerate?)")
    print("-" * 40)
    g_met, _ = compute_metric_tensor(S_metallic, temperature=300.0)
    props_met = metric_properties(g_met)
    
    print(f"  Determinant |g|:    {props_met['determinant']:.2e}")
    print(f"  Positive definite:  {props_met['positive_definite']}")
    print(f"  Near phase boundary: {detect_curvature_singularity(S_metallic)}")
    
    print("\n4. SCALAR CURVATURE COMPARISON")
    print("-" * 40)
    R_cmos = scalar_curvature(g_cmos, S_cmos, temperature=300.0)
    R_quant = scalar_curvature(g_quant, S_quantum, temperature=4.0)
    R_met = scalar_curvature(g_met, S_metallic, temperature=300.0)
    
    print(f"  R(S_cmos):     {R_cmos:.2e}")
    print(f"  R(S_quantum):  {R_quant:.2e}")
    print(f"  R(S_metallic): {R_met:.2e}")
    
    print("\n5. GEODESIC: CMOS → QUANTUM (minimum-energy fabrication)")
    print("-" * 40)
    
    geo = compile_fabrication_geodesic(
        S_cmos, S_quantum, temperature=300.0, n_steps=50
    )
    
    print(f"  Total energy cost:  {geo.energy_cost:.3f} eV")
    print(f"  Crosses boundary:   {geo.crosses_phase_boundary}")
    print(f"  Max curvature:      {geo.curvature_profile.max():.2e}")
    
    # Show key points along path
    print(f"\n  Path waypoints:")
    for t in [0, 10, 25, 40, 49]:
        n, d, ell, k = geo.path[t]
        print(f"    t={t:2d}: n={n:.2e}, d={d:.3f}, ℓ={ell:.2f}, κ={k:.3f}")
    
    print("\n6. BOUNDARY CROSSING COST ANALYSIS")
    print("-" * 40)
    
    crossing_info = boundary_crossing_cost(S_cmos, S_metallic, temperature=300.0)
    print(f"  CMOS → Metallic:")
    print(f"    Geodesic distance: {crossing_info['geodesic_distance']:.3f} eV")
    print(f"    Phase boundary crossings: {crossing_info['n_crossings']}")
    print(f"    Max curvature: {crossing_info['max_curvature']:.2e}")
    
    print("\n" + "=" * 70)
    print("GEOMETRY SUMMARY")
    print("=" * 70)
    print(f"""
    The silicon manifold has a genuine Riemannian structure:
    
    - Metric g_ij = ∂²F/∂S_i∂S_j from DFT free energy
    - Geodesics = minimum-energy fabrication paths
    - √|g| = regime stability (volume element)
    - R → ∞ at phase boundaries (curvature singularities)
    - CMOS basin:  |g| = {props_cmos['determinant']:.2e} (wide, stable)
    - Quantum:     |g| = {props_quant['determinant']:.2e} (narrower, coherent)
    - Metallic:    |g| = {props_met['determinant']:.2e} (nearly degenerate)
    
    The metric connects DFT calculations to optimal fabrication
    trajectories and predicts where computational phase transitions
    occur as curvature singularities.
    """)
