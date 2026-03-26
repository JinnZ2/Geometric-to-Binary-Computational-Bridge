"""
Kosterlitz-Thouless Annealer for φ-Lattice Phase Optimization
==============================================================
Replaces heuristic gradient flow for the phase degrees of freedom in
the geometric engine with a thermodynamically-grounded optimization.

Physics background
------------------
The Kosterlitz-Thouless (KT) transition is a 2D topological phase transition
in the XY model.  Below T_KT, vortex-antivortex pairs are bound; the field is
phase-coherent.  Above T_KT, free vortices proliferate and destroy long-range
order.  The critical temperature for coupling constant J is:

    T_KT = π J / 2

For the φ-lattice (J = φ ≈ 1.618):

    T_KT ≈ π φ / 2 ≈ 2.54

Annealing from T_start > T_KT to T_final < T_KT using exponential cooling
drives the system through the KT transition, binding all free vortices and
minimizing phase decoherence.  This is the correct physical mechanism for
the "topological defect cleavage" described in Intelligence-engine.md —
instead of detecting persistent defects and manually resetting nodes, the
annealer finds the minimum-energy configuration by thermodynamic descent.

Energy functional (XY model)
-----------------------------
    E = -J Σ_{⟨i,j⟩} cos(θᵢ - θⱼ)

Minimum at E_min = -(number of edges) × J  (all phases aligned).

Vortex count
------------
A topological defect exists on a closed loop when the total phase winding
is ±2π.  We use triangles (3-cycles) as the smallest closed loops in the
adjacency graph.  The vortex count is a topological invariant: it can only
decrease by pair annihilation, which requires T < T_KT.

Dependencies: numpy only.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PHI: float = (1.0 + 5.0 ** 0.5) / 2.0


# ─── Configuration ────────────────────────────────────────────────────────────

@dataclass
class KTConfig:
    """
    Configuration for the KT annealer.

    Attributes
    ----------
    J               : coupling constant  (φ for φ-lattice)
    T_start         : initial temperature (should be > T_KT)
    T_final         : final temperature   (should be < T_KT)
    n_steps         : number of cooling steps
    n_sweeps_per_step: Metropolis sweeps per temperature step
    max_delta       : max phase perturbation magnitude (radians)
    seed            : RNG seed (None for random)
    """
    J:                 float          = PHI
    T_start:           float          = 4.0    # > T_KT ≈ 2.54
    T_final:           float          = 0.4    # << T_KT
    n_steps:           int            = 1000
    n_sweeps_per_step: int            = 1
    max_delta:         float          = math.pi
    seed:              Optional[int]  = None

    @property
    def T_KT(self) -> float:
        """Kosterlitz-Thouless critical temperature: T_KT = π J / 2."""
        return math.pi * self.J / 2.0


# ─── Annealing state snapshot ─────────────────────────────────────────────────

@dataclass
class AnnealStep:
    """Snapshot of the annealer state at one temperature."""
    step:            int
    temperature:     float
    energy:          float
    phase_coherence: float   # |⟨e^{iθ}⟩| ∈ [0, 1]
    vortex_count:    int
    acceptance_rate: float


# ─── Core annealer ────────────────────────────────────────────────────────────

class KTAnnealer:
    """
    Kosterlitz-Thouless annealer for φ-lattice phase optimization.

    Operates on the phase degrees of freedom of a geometric network.
    Intended as a drop-in replacement for the gradient-flow phase repair
    in ``GeometricProtectionEngine.apply_gradient_flow``.

    Usage
    -----
    >>> phases = np.random.uniform(0, 2*np.pi, n_nodes)
    >>> adj    = [[1, 2], [0, 2], [0, 1]]   # triangle
    >>> ann    = KTAnnealer(phases, adj)
    >>> optimized = ann.anneal()
    >>> print(ann.final_coherence())
    """

    def __init__(
            self,
            phases:    np.ndarray,
            adjacency: List[List[int]],
            config:    Optional[KTConfig] = None,
    ) -> None:
        """
        Parameters
        ----------
        phases    : 1-D float array of initial phase values (radians).
        adjacency : list of neighbor index lists (one per node).
        config    : KTConfig; uses defaults if None.
        """
        self.phases: np.ndarray = phases.copy().astype(float) % (2 * math.pi)
        self.adj:    List[List[int]] = adjacency
        self.cfg:    KTConfig        = config or KTConfig()
        self._rng:   np.random.Generator = np.random.default_rng(self.cfg.seed)
        self.history: List[AnnealStep] = []

    # ── Energy ────────────────────────────────────────────────────────────────

    def _edge_energy(self, phases: np.ndarray) -> float:
        """Total XY-model energy: E = -J Σ_{⟨i,j⟩} cos(θᵢ - θⱼ)."""
        J = self.cfg.J
        total = 0.0
        seen: set = set()
        for i, neighbors in enumerate(self.adj):
            for j in neighbors:
                edge = (min(i, j), max(i, j))
                if edge not in seen:
                    seen.add(edge)
                    total -= J * math.cos(phases[i] - phases[j])
        return total

    def _node_delta_energy(self, i: int, old_phase: float, new_phase: float) -> float:
        """Change in energy when node i moves from old_phase to new_phase."""
        J = self.cfg.J
        dE = 0.0
        for j in self.adj[i]:
            dE += J * math.cos(old_phase - self.phases[j])
            dE -= J * math.cos(new_phase - self.phases[j])
        return dE

    # ── Order parameter ───────────────────────────────────────────────────────

    def _phase_coherence(self, phases: np.ndarray) -> float:
        """
        XY order parameter: R = |⟨e^{iθ}⟩| ∈ [0, 1].

        R = 1 → fully phase-locked (zero-vortex ground state).
        R = 0 → completely disordered.
        """
        if len(phases) == 0:
            return 0.0
        return float(abs(np.mean(np.exp(1j * phases))))

    # ── Vortex detection ──────────────────────────────────────────────────────

    def _count_vortices(self, phases: np.ndarray) -> int:
        """
        Count topological defects (vortices) on triangular plaquettes.

        A vortex exists on a 3-cycle i→j→k→i when the accumulated phase
        winding around the loop is ±π or more (rounded to nearest 2π wind).
        """
        count = 0
        n = len(phases)
        for i in range(n):
            nbrs_i = set(self.adj[i])
            for j in self.adj[i]:
                if j <= i:
                    continue
                for k in self.adj[j]:
                    if k <= j or k not in nbrs_i:
                        continue
                    # Triangle i → j → k → i
                    w = (phases[j] - phases[i]) + (phases[k] - phases[j]) + (phases[i] - phases[k])
                    # Wrap to (-π, π]
                    w = (w + math.pi) % (2 * math.pi) - math.pi
                    if abs(w) > 0.5 * math.pi:
                        count += 1
        return count

    # ── Metropolis sweep ──────────────────────────────────────────────────────

    def _metropolis_sweep(self, T: float) -> float:
        """
        One Metropolis-Hastings sweep over all nodes in random order.

        Proposal: uniform phase shift in [−max_delta·(T/T_KT), +max_delta·(T/T_KT)].
        Returns acceptance rate.
        """
        T_KT = self.cfg.T_KT
        max_delta = self.cfg.max_delta * min(1.0, T / T_KT)
        accepted = 0
        n = len(self.phases)

        for i in self._rng.permutation(n):
            old = self.phases[i]
            delta = self._rng.uniform(-max_delta, max_delta)
            new = (old + delta) % (2 * math.pi)

            dE = self._node_delta_energy(i, old, new)

            if dE <= 0.0 or self._rng.random() < math.exp(-dE / max(T, 1e-12)):
                self.phases[i] = new
                accepted += 1

        return accepted / max(1, n)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def anneal(self) -> np.ndarray:
        """
        Run KT annealing from T_start → T_final.

        Uses exponential cooling: T(t) = T_start · (T_final / T_start)^{t/N}.

        Returns the optimized phase array.  History is stored in ``self.history``.
        """
        cfg = self.cfg
        T = cfg.T_start
        N = max(1, cfg.n_steps - 1)
        ratio = (cfg.T_final / cfg.T_start) ** (1.0 / N)

        for step in range(cfg.n_steps):
            accept_rate = 0.0
            for _ in range(cfg.n_sweeps_per_step):
                accept_rate = self._metropolis_sweep(T)

            # Record snapshot
            E = self._edge_energy(self.phases)
            coh = self._phase_coherence(self.phases)
            vortices = self._count_vortices(self.phases)

            self.history.append(AnnealStep(
                step=step,
                temperature=T,
                energy=E,
                phase_coherence=coh,
                vortex_count=vortices,
                acceptance_rate=accept_rate,
            ))

            T *= ratio

        return self.phases.copy()

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def final_coherence(self) -> float:
        """Phase coherence of the current (post-anneal) phase configuration."""
        return self._phase_coherence(self.phases)

    def final_vortex_count(self) -> int:
        """Vortex count of the current phase configuration."""
        return self._count_vortices(self.phases)

    def kt_transition_step(self) -> Optional[int]:
        """
        Locate the annealing step where the system crosses T_KT.

        Returns the step with the largest single-step drop in vortex count,
        which corresponds to the onset of vortex-antivortex binding.
        Returns None if no clear transition is observed.
        """
        if len(self.history) < 4:
            return None
        counts = [s.vortex_count for s in self.history]
        drops = [counts[i] - counts[i + 1] for i in range(len(counts) - 1)]
        if not drops or max(drops) <= 0:
            return None
        best = drops.index(max(drops))
        return best

    def coherence_at_T_KT(self) -> Optional[float]:
        """
        Interpolated phase coherence at the estimated KT transition temperature.
        """
        step = self.kt_transition_step()
        if step is None or step >= len(self.history):
            return None
        return self.history[step].phase_coherence

    def summary(self) -> Dict[str, Any]:
        """Return a dict summarising the annealing run."""
        if not self.history:
            return {}
        start = self.history[0]
        end = self.history[-1]
        kt_step = self.kt_transition_step()
        return {
            "T_KT":                self.cfg.T_KT,
            "T_start":             start.temperature,
            "T_final":             end.temperature,
            "n_steps":             len(self.history),
            "energy_start":        start.energy,
            "energy_final":        end.energy,
            "energy_improvement":  start.energy - end.energy,
            "coherence_start":     start.phase_coherence,
            "coherence_final":     end.phase_coherence,
            "vortices_start":      start.vortex_count,
            "vortices_final":      end.vortex_count,
            "kt_transition_step":  kt_step,
            "kt_transition_T":     self.history[kt_step].temperature if kt_step is not None else None,
        }


# ─── Convenience factory ──────────────────────────────────────────────────────

def anneal_network_phases(
        phases:    np.ndarray,
        adjacency: List[List[int]],
        config:    Optional[KTConfig] = None,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Anneal phase array and return (optimized_phases, summary_dict).

    Convenience wrapper for ``KTAnnealer``.
    """
    annealer = KTAnnealer(phases, adjacency, config)
    optimized = annealer.anneal()
    return optimized, annealer.summary()


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 65)
    print("KT Annealer Demo — φ-lattice (J = φ ≈ 1.618)")
    print(f"T_KT = π·φ/2 ≈ {math.pi * PHI / 2:.4f}")
    print("=" * 65)

    rng = np.random.default_rng(42)
    N = 16
    # 4×4 torus topology
    adj: List[List[int]] = []
    for row in range(4):
        for col in range(4):
            i = row * 4 + col
            neighbors = [
                row * 4 + (col + 1) % 4,
                row * 4 + (col - 1) % 4,
                ((row + 1) % 4) * 4 + col,
                ((row - 1) % 4) * 4 + col,
            ]
            adj.append(neighbors)

    # Random initial phases (above T_KT → many free vortices)
    phases_init = rng.uniform(0, 2 * math.pi, N)

    cfg = KTConfig(J=PHI, T_start=5.0, T_final=0.3, n_steps=500, seed=42)
    ann = KTAnnealer(phases_init.copy(), adj, cfg)
    optimized = ann.anneal()

    s = ann.summary()
    print(f"\nEnergy:    {s['energy_start']:+.3f} → {s['energy_final']:+.3f}"
          f"  (Δ={s['energy_improvement']:+.3f})")
    print(f"Coherence: {s['coherence_start']:.3f} → {s['coherence_final']:.3f}")
    print(f"Vortices:  {s['vortices_start']} → {s['vortices_final']}")
    if s["kt_transition_step"] is not None:
        print(f"KT step:   {s['kt_transition_step']}  "
              f"(T ≈ {s['kt_transition_T']:.3f}, T_KT = {s['T_KT']:.3f})")
    print("\nAnnealing complete.")
