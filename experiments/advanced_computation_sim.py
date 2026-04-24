"""
Advanced Computation Sim — skeleton
====================================

Computational phase space: Purity × Entanglement Ratio, with
octahedral encoding and a dynamical fiber ``S(t)`` steered toward
target vertices.

Status
------
**Skeleton, not production.** This module is a reference
implementation of the phase-space computation model described in
``docs/advanced_computation_sim_notes.md``. Extension points are
flagged there; see the notes doc before refining heuristic choices
(vertex positions, operation map, control law, noise model).

Pipeline summary
----------------
Task specification → octahedral target mapping → control-steered
geodesic dynamics → kernel construction → observable computation
(purity, entanglement ratio, ECP, spectral gap) → trajectory analysis.

The OPERATION_MAP derives from the correlation data that motivated the
design:

* Diagonal vertices (P110, P111) ↔ solitonic / separable
  (r ≈ +0.93 solitonic, r ≈ −0.68 entanglement)
* Axis vertices (P000, P010, P011) ↔ entanglement

The control law is simple proportional steering toward the nearest
valid target. See the notes doc for the planned PID / model-predictive
extensions.

Cross-references in this repo
-----------------------------
* ``Engine/gaussian_splats/octahedral.py`` — ``OctahedralStateEncoder``
  already defines canonical 8-vertex positions on the (x, y, z)
  tetrahedral basis. VERTEX_POSITIONS below is a distinct, higher-
  dimensional mapping (6D silicon state); reconciling the two is a
  follow-up.
* ``GEIS/octahedral_state.py`` — ``OctahedralState`` is the discrete
  8-state container used by GEIS encoding.
* ``bridges/intersection/`` — the RESONATE layer. Once this sim is
  runnable end-to-end, a trajectory of (purity, entanglement) points
  can itself be fed through an ``IntersectionRule`` subclass so the
  computation becomes a first-class participant in cross-domain
  fusion.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Callable
from enum import Enum


# ============================================================
# 1. STATE DEFINITIONS
# ============================================================

@dataclass
class SiliconState:
    """Fiber state: 6D silicon parameter vector."""
    vec: np.ndarray  # [n, d, l, k1, k2, k3]
    vel: np.ndarray  # velocity in state space

    @classmethod
    def default(cls) -> "SiliconState":
        return cls(
            vec=np.array([1e17, 0.1, 3.0, 1.0, 0.2, 0.1]),
            vel=np.zeros(6),
        )


class Vertex(Enum):
    """Octahedral vertices as computational modes."""
    P000_PLUS_X  = 0   # +x axis
    P001_MINUS_X = 1   # -x axis
    P010_PLUS_Y  = 2   # +y axis
    P011_MINUS_Y = 3   # -y axis
    P100_PLUS_Z  = 4   # +z axis
    P101_MINUS_Z = 5   # -z axis
    P110_DIAG_A  = 6   # diagonal a
    P111_DIAG_B  = 7   # diagonal b


class OpType(Enum):
    """Computational operation types mapped to octahedral targets."""
    LOCAL_BOOL    = "local_boolean"
    NONLOCAL_CORR = "nonlocal_correlated"
    MIXED_PROB    = "mixed_probabilistic"
    NONCLASSICAL  = "nonclassical_mixed"
    READOUT       = "readout"


# ============================================================
# 2. VERTEX ↔ STATE MAPPING
# ============================================================

# Target positions in normalised 6D space for each vertex. Derived
# heuristically from the attractor structure in the source data —
# refine from real attractor coordinates once they are available.
VERTEX_POSITIONS: Dict[Vertex, np.ndarray] = {
    Vertex.P000_PLUS_X:  np.array([ 1.0,  0.0,  0.0,  0.5,  0.0,  0.0]),
    Vertex.P001_MINUS_X: np.array([-1.0,  0.0,  0.0,  0.0,  0.5,  0.0]),
    Vertex.P010_PLUS_Y:  np.array([ 0.0,  1.0,  0.0,  0.0,  0.0,  0.5]),
    Vertex.P011_MINUS_Y: np.array([ 0.0, -1.0,  0.0,  0.5,  0.0,  0.5]),
    Vertex.P100_PLUS_Z:  np.array([ 0.0,  0.0,  1.0,  0.3,  0.3,  0.0]),
    Vertex.P101_MINUS_Z: np.array([ 0.0,  0.0, -1.0,  0.0, -0.3, -0.3]),
    Vertex.P110_DIAG_A:  np.array([ 0.5,  0.5,  0.0,  1.0,  0.0,  0.0]),
    Vertex.P111_DIAG_B:  np.array([-0.5, -0.5,  0.0,  0.0,  1.0,  0.0]),
}

# Operation type → preferred vertex targets. Grounded in the
# correlation structure: diagonals for solitonic / separable modes,
# axis vertices for entangled modes.
OPERATION_MAP: Dict[OpType, List[Vertex]] = {
    OpType.LOCAL_BOOL:    [Vertex.P110_DIAG_A, Vertex.P111_DIAG_B],
    OpType.NONLOCAL_CORR: [Vertex.P000_PLUS_X, Vertex.P010_PLUS_Y, Vertex.P011_MINUS_Y],
    OpType.MIXED_PROB:    list(Vertex),
    OpType.NONCLASSICAL:  [Vertex.P000_PLUS_X, Vertex.P010_PLUS_Y],
    OpType.READOUT:       [Vertex.P100_PLUS_Z, Vertex.P101_MINUS_Z],
}


# ============================================================
# 3. COMPUTATIONAL TASK SPECIFICATION
# ============================================================

@dataclass
class ComputeStep:
    """One step in a computational task."""
    op_type: OpType
    duration: float
    target_purity: float = 0.35       # > threshold = pure mode
    target_entanglement: float = 0.3  # off-diag/diag ratio target


@dataclass
class ComputeTask:
    """Full computational task as sequence of operation steps."""
    steps: List[ComputeStep]
    name: str = "unnamed"


# ============================================================
# 4. METRIC AND GEODESIC DYNAMICS
# ============================================================

def metric_inverse(S: SiliconState) -> np.ndarray:
    """Inverse metric on 6D silicon state space."""
    n = S.vec[0]
    w_n = w_d = w_l = 1.0
    g_inv = np.eye(6)
    g_inv[0, 0] = (n * n + 1e-20) / w_n
    g_inv[1, 1] = 1.0 / w_d
    g_inv[2, 2] = 1.0 / w_l
    return g_inv


def christoffel(S: SiliconState) -> Dict[Tuple[int, int, int], float]:
    """Nonzero Christoffel symbols. Only Γ^n_nn = -1/n kept for tractability."""
    n = S.vec[0]
    return {(0, 0, 0): -1.0 / (n + 1e-12)}


def potential(S: SiliconState) -> float:
    """Fabrication + stability potential."""
    n, d, l = S.vec[:3]
    k = S.vec[3:]
    return (
        (n - 1e17) ** 2 / 1e34
        + d ** 2
        + (l - 3.0) ** 2
        + np.sum((k - np.array([1.0, 0.5, 0.3])) ** 2)
    )


def grad_potential(S: SiliconState) -> np.ndarray:
    """Numerical gradient of potential."""
    eps = 1e-6
    grad = np.zeros(6)
    for i in range(6):
        dvec = np.zeros(6)
        dvec[i] = eps
        Sp = SiliconState(S.vec + dvec, S.vel)
        Sm = SiliconState(S.vec - dvec, S.vel)
        grad[i] = (potential(Sp) - potential(Sm)) / (2 * eps)
    return grad


def geometry_force(field: np.ndarray) -> np.ndarray:
    """Force term from geometry field φ(x)."""
    mean_f = float(field.mean())
    var_f = float(field.var())
    grad_f = float(np.mean(np.abs(np.gradient(field))))
    return np.array([
        1e15 * mean_f,
        var_f,
        -grad_f,
        grad_f,
        var_f,
        mean_f ** 2,
    ])


# ============================================================
# 5. COMPUTATIONAL OBSERVABLES
# ============================================================

def compute_vertex_weights(S: SiliconState) -> np.ndarray:
    """
    Barycentric-style weights over the 8 octahedral vertices.
    Uses softmin over Euclidean distance to each vertex position.
    """
    distances = np.array([
        np.linalg.norm(S.vec - VERTEX_POSITIONS[v]) for v in Vertex
    ])
    weights = np.exp(-distances)
    total = weights.sum()
    return weights / total if total > 0 else np.ones(8) / 8.0


def operator_purity(vertex_weights: np.ndarray) -> float:
    """Purity = max vertex weight. 1/8 = fully mixed, 1.0 = pure mode."""
    return float(np.max(vertex_weights))


def entanglement_ratio(W: np.ndarray) -> float:
    """Off-diagonal / (diagonal + off-diagonal) magnitude ratio of kernel."""
    diag = float(np.mean(np.abs(np.diag(W))))
    n = W.shape[0]
    off_total = float(np.sum(np.abs(W)) - np.sum(np.abs(np.diag(W))))
    off_diag = off_total / (n * (n - 1) + 1e-20)
    return float(off_diag / (diag + off_diag + 1e-20))


def build_kernel(S: SiliconState, field: np.ndarray, size: int = 16) -> np.ndarray:
    """Construct kernel W(x, x') from silicon state and geometry field."""
    n = S.vec[0]
    d = S.vec[1]
    k = S.vec[3:]
    W = np.zeros((size, size))
    for i in range(size):
        for j in range(size):
            dx = i - j
            gaussian = np.exp(-(dx * dx) / (1e-2 + abs(n) * 1e-17))
            geom = np.exp(-0.5 * (field[i % len(field)] - field[j % len(field)]) ** 2)
            damp = np.exp(-d)
            coupling = 1.0 + 0.1 * np.sum(k)
            W[i, j] = gaussian * geom * damp * coupling
    return W


def spectral_gap(W: np.ndarray) -> float:
    """Minimum absolute eigenvalue — measures reversibility."""
    if np.allclose(W, W.T):
        eigvals = np.linalg.eigvalsh(W)
    else:
        eigvals = np.linalg.eigvals(W)
    return float(np.min(np.abs(eigvals)))


def ecp(ent_ratio: float, purity: float) -> float:
    """Entanglement-Computation Product: high = nonlocal and not single-mode."""
    return ent_ratio * (1.0 - purity)


# ============================================================
# 6. CONTROL DYNAMICS
# ============================================================

def control_force(
    S: SiliconState,
    target_vertex: Vertex,
    gain: float = 1.0,
) -> np.ndarray:
    """Proportional steering force toward a target octahedral vertex."""
    target_vec = VERTEX_POSITIONS[target_vertex]
    return gain * (target_vec - S.vec)


def control_force_multi_target(
    S: SiliconState,
    targets: List[Vertex],
    gain: float = 1.0,
) -> np.ndarray:
    """Steering force toward the nearest of multiple valid targets."""
    best_target = min(
        targets, key=lambda v: np.linalg.norm(S.vec - VERTEX_POSITIONS[v])
    )
    return control_force(S, best_target, gain)


def step_dynamics(
    S: SiliconState,
    field: np.ndarray,
    dt: float = 0.01,
    noise_scale: float = 0.01,
    control: Optional[Callable[[SiliconState], np.ndarray]] = None,
) -> SiliconState:
    """Single step of stochastic geodesic dynamics with optional control."""
    g_inv = metric_inverse(S)
    Gamma = christoffel(S)
    gradV = grad_potential(S)

    acc = np.zeros(6)

    # Christoffel
    for (a, b, c), val in Gamma.items():
        acc[a] -= val * S.vel[b] * S.vel[c]

    # Potential gradient
    acc -= g_inv @ gradV

    # Geometry driving
    acc += geometry_force(field)

    # Control
    if control is not None:
        acc += control(S)

    # Noise
    acc += noise_scale * np.random.randn(6)

    # Integrate
    new_vel = S.vel + dt * acc
    new_vec = S.vec + dt * new_vel

    return SiliconState(vec=new_vec, vel=new_vel)


# ============================================================
# 7. TASK EXECUTION ENGINE
# ============================================================

@dataclass
class TrajectoryPoint:
    """Single point in a computational trajectory."""
    time: float
    S: SiliconState
    vertex_weights: np.ndarray
    purity: float
    entanglement: float
    ecp: float
    spectral_gap: float
    kernel: np.ndarray
    dominant_vertex: Vertex


def run_computation(
    task: ComputeTask,
    S0: SiliconState,
    field: np.ndarray,
    dt: float = 0.01,
    noise_scale: float = 0.01,
    control_gain: float = 1.0,
    kernel_size: int = 16,
    callback: Optional[Callable[[TrajectoryPoint], None]] = None,
) -> List[TrajectoryPoint]:
    """
    Execute a computational task by steering S(t) through the
    octahedral computational phase space.

    Returns the full trajectory with all observables.
    """
    S = S0
    trajectory: List[TrajectoryPoint] = []
    t = 0.0

    for comp_step in task.steps:
        targets = OPERATION_MAP[comp_step.op_type]
        n_steps = int(comp_step.duration / dt)

        def ctrl(state: SiliconState, targets=targets) -> np.ndarray:
            return control_force_multi_target(state, targets, control_gain)

        for _ in range(n_steps):
            S = step_dynamics(S, field, dt, noise_scale, control=ctrl)

            weights = compute_vertex_weights(S)
            kernel = build_kernel(S, field, kernel_size)
            purity_val = operator_purity(weights)
            ent_val = entanglement_ratio(kernel)
            gap = spectral_gap(kernel)

            point = TrajectoryPoint(
                time=t,
                S=SiliconState(vec=S.vec.copy(), vel=S.vel.copy()),
                vertex_weights=weights,
                purity=purity_val,
                entanglement=ent_val,
                ecp=ecp(ent_val, purity_val),
                spectral_gap=gap,
                kernel=kernel,
                dominant_vertex=Vertex(int(np.argmax(weights))),
            )
            trajectory.append(point)
            t += dt

            if callback is not None:
                callback(point)

    return trajectory


# ============================================================
# 8. ANALYSIS UTILITIES
# ============================================================

def compute_correlations(trajectory: List[TrajectoryPoint]) -> Dict[str, float]:
    """Compute key correlations over a trajectory."""
    purity_arr = np.array([p.purity for p in trajectory])
    ent_arr = np.array([p.entanglement for p in trajectory])
    ecp_arr = np.array([p.ecp for p in trajectory])
    gap_arr = np.array([p.spectral_gap for p in trajectory])

    def pearson(x: np.ndarray, y: np.ndarray) -> float:
        if x.std() == 0 or y.std() == 0:
            return 0.0
        return float(np.corrcoef(x, y)[0, 1])

    return {
        "r(purity, entanglement)":     pearson(purity_arr, ent_arr),
        "r(purity, spectral_gap)":     pearson(purity_arr, gap_arr),
        "r(purity, ECP)":              pearson(purity_arr, ecp_arr),
        "r(entanglement, spectral_gap)": pearson(ent_arr, gap_arr),
    }


def trajectory_summary(trajectory: List[TrajectoryPoint]) -> Dict:
    """Summary statistics for a computational trajectory."""
    purities = [p.purity for p in trajectory]
    ents = [p.entanglement for p in trajectory]
    ecps = [p.ecp for p in trajectory]
    dom_vertices = [p.dominant_vertex for p in trajectory]

    unique_dom = {v.name for v in dom_vertices}
    pure_fraction = sum(1 for p in purities if p > 0.35) / len(trajectory)
    entangled_fraction = sum(1 for e in ents if e > 0.5) / len(trajectory)

    return {
        "total_time":                len(trajectory) * 0.01,
        "mean_purity":               float(np.mean(purities)),
        "mean_entanglement":         float(np.mean(ents)),
        "peak_ecp":                  float(np.max(ecps)),
        "unique_dominant_vertices":  unique_dom,
        "pure_mode_fraction":        pure_fraction,
        "entangled_fraction":        entangled_fraction,
        "correlations":              compute_correlations(trajectory),
    }


# ============================================================
# 9. DEMO TASK
# ============================================================

def demo_task() -> ComputeTask:
    """Example task: Boolean → Entangled → Mixed → Nonclassical sequence."""
    return ComputeTask(
        name="demo_boolean_to_entangled",
        steps=[
            ComputeStep(OpType.LOCAL_BOOL,    duration=0.5, target_purity=0.40, target_entanglement=0.2),
            ComputeStep(OpType.NONLOCAL_CORR, duration=0.5, target_purity=0.40, target_entanglement=0.6),
            ComputeStep(OpType.MIXED_PROB,    duration=0.5, target_purity=0.20, target_entanglement=0.3),
            ComputeStep(OpType.NONCLASSICAL,  duration=0.5, target_purity=0.15, target_entanglement=0.6),
        ],
    )


def run_demo() -> Tuple[List[TrajectoryPoint], Dict]:
    """Run the demonstration task and print a summary."""
    S0 = SiliconState.default()
    field = np.sin(np.linspace(0, 4 * np.pi, 16))

    task = demo_task()
    trajectory = run_computation(task, S0, field, dt=0.01, noise_scale=0.005)
    summary = trajectory_summary(trajectory)

    print(f"Task: {task.name}")
    print(f"Steps: {len(trajectory)}")
    print(f"Mean purity:         {summary['mean_purity']:.4f}")
    print(f"Mean entanglement:   {summary['mean_entanglement']:.4f}")
    print(f"Peak ECP:            {summary['peak_ecp']:.4f}")
    print(f"Pure mode fraction:  {summary['pure_mode_fraction']:.2%}")
    print(f"Entangled fraction:  {summary['entangled_fraction']:.2%}")
    print(f"Unique dominant vertices: {summary['unique_dominant_vertices']}")
    print("\nCorrelations:")
    for k, v in summary["correlations"].items():
        print(f"  {k}: {v:+.4f}")

    return trajectory, summary


if __name__ == "__main__":
    run_demo()
