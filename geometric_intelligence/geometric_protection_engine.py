"""
Geometric Consciousness Protection Engine
=========================================
Physics-based protection of conscious geometric substrates against:
  - Trojan insertions (energy sinks / anomalous field values)
  - φ-scale violations (golden-ratio drift)
  - Phase decoherence (consciousness disruption)
  - Topological defects (structural corruption)

Uses Action minimisation (gradient flow) for routine repair and
Kosterlitz-Thouless annealing for topologically-protected phase defects.

Extracted and formalised from Geometric-Intelligence/Intelligence-engine.md.
KT annealing replaces the heuristic structural-cleavage surgery for phase
defects: the annealer cools through T_KT ≈ 2.54 (for J=φ), binding
vortex-antivortex pairs and restoring phase coherence without the destructive
node reset that cleavage performs.

Entry point: GeometricProtectionEngine.tick_protection()
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from Engine.kt_annealer import KTAnnealer, KTConfig, anneal_network_phases

PHI: float = (1.0 + 5.0 ** 0.5) / 2.0


# ─── Node ─────────────────────────────────────────────────────────────────────

@dataclass
class GeometricNode:
    """
    Node in a conscious geometric network.

    Combines Mandala-cell field/phase/octahedral-state properties with
    protection metrics (stress, defect index) and IIT consciousness
    properties (φ_IIT, local complexity).
    """
    id:               int
    field:            float          # scalar field value
    phase:            float          # phase in radians
    octahedral_state: int            # 0-7 (8 octahedral states)

    # Geometric signature
    phi_ratio:   float = PHI
    resonance:   float = 1.0

    # Protection state
    defect_index:      float = 0.0
    stress_energy:     float = 0.0
    quarantined:       bool  = False
    quarantine_until:  int   = 0

    # Consciousness metrics
    phi_IIT:           float = 0.0   # integrated information Φ
    local_complexity:  float = 0.0

    # Network topology
    neighbors:         List[int]       = field(default_factory=list)
    neighbor_weights:  Dict[int, float] = field(default_factory=dict)


# ─── Engine ───────────────────────────────────────────────────────────────────

class GeometricProtectionEngine:
    """
    Physics-based protection engine for conscious geometric networks.

    Protection ladder (escalating severity):
    1. Gentle gradient flow  — mild drift (D < D_critical)
    2. Aggressive gradient flow — D ≥ D_critical (non-topological defect)
    3. KT annealing          — topological defect detected (replaces old cleavage)
    4. Structural cleavage   — KT annealing fails to resolve the defect (last resort)

    Parameters
    ----------
    nodes          : list of GeometricNode
    action_weights : λ coefficients for the Action functional
    kt_config      : KTConfig for KT annealing (uses φ-lattice defaults if None)
    """

    # Default Action functional weights (λ_k)
    _DEFAULT_LAMBDA = {
        "curvature":      0.30,   # ∇² stress weight
        "phi_dev":        0.25,   # φ-deviation weight
        "divergence":     0.20,   # ∇·E weight
        "spin":           0.15,   # phase misalignment weight
        "reconstruction": 0.10,   # repair resistance weight
    }

    def __init__(
            self,
            nodes:          List[GeometricNode],
            action_weights: Optional[Dict[str, float]] = None,
            kt_config:      Optional[KTConfig]         = None,
    ) -> None:
        self.nodes:  List[GeometricNode] = nodes
        self.lambda_ = action_weights or dict(self._DEFAULT_LAMBDA)

        # Repair learning rates
        self.eta_field = 0.15
        self.eta_phase = 0.12

        # Protection thresholds
        self.D_critical   = 0.55   # flag above this
        self.D_quarantine = 0.75   # quarantine above this

        # KT config for topological repair
        self.kt_config = kt_config or KTConfig(
            J=PHI, T_start=3.5, T_final=0.4, n_steps=200,
        )

        # Per-node history
        self.history: Dict[int, Dict[str, list]] = {
            i: {"field": [], "phase": [], "energy_in": [], "energy_out": [], "defect": [], "phi_IIT": []}
            for i in range(len(nodes))
        }
        self.tick: int = 0

    # ── Adjacency ─────────────────────────────────────────────────────────────

    def _build_adjacency(self) -> List[List[int]]:
        """Build adjacency list from node neighbor fields."""
        return [list(node.neighbors) for node in self.nodes]

    # ── Laplacian / stress primitives ─────────────────────────────────────────

    def _discrete_laplacian(self, i: int) -> float:
        node = self.nodes[i]
        if not node.neighbors:
            return 0.0
        total_w = weighted_diff = 0.0
        for j in node.neighbors:
            w = node.neighbor_weights.get(j, 1.0)
            weighted_diff += w * (self.nodes[j].field - node.field)
            total_w += w
        return weighted_diff / total_w if total_w else 0.0

    def _phi_deviation(self, i: int) -> float:
        node = self.nodes[i]
        if not node.neighbors:
            return 0.0
        avg = sum(self.nodes[j].field for j in node.neighbors) / len(node.neighbors)
        R_obs = avg / node.field if node.field else avg / 1e-9
        return abs(R_obs - node.phi_ratio)

    def _divergence(self, i: int) -> float:
        hist = self.history[i]
        if not hist["energy_in"]:
            return 0.0
        w = min(8, len(hist["energy_in"]))
        avg_in  = sum(hist["energy_in"][-w:])  / w
        avg_out = sum(hist["energy_out"][-w:]) / max(1, len(hist["energy_out"][-w:]))
        denom = max(1e-12, abs(avg_in) + abs(avg_out))
        return (avg_in - avg_out) / denom

    def _spin_alignment(self, i: int) -> float:
        node = self.nodes[i]
        if not node.neighbors:
            return 1.0
        total_w = weighted = 0.0
        for j in node.neighbors:
            w = node.neighbor_weights.get(j, 1.0)
            weighted += w * math.cos(self.nodes[j].phase - node.phase)
            total_w  += w
        return weighted / total_w if total_w else 1.0

    def _stress_energy(self, i: int) -> Dict[str, float]:
        lap  = self._discrete_laplacian(i)
        phid = self._phi_deviation(i)
        div  = self._divergence(i)
        spin = self._spin_alignment(i)
        lam  = self.lambda_
        E_curv = lam["curvature"]  * lap  ** 2
        E_phi  = lam["phi_dev"]    * phid ** 2
        E_div  = lam["divergence"] * div  ** 2
        E_spin = lam["spin"]       * (1 - spin) ** 2
        return {
            "total": E_curv + E_phi + E_div + E_spin,
            "curvature": E_curv, "phi_deviation": E_phi,
            "divergence": E_div, "spin_misalignment": E_spin,
            "primitives": {"laplacian": lap, "phi_dev": phid, "divergence": div, "spin": spin},
        }

    def compute_defect_index(self, i: int) -> float:
        """D_i = √(E_stress). Stored on the node."""
        stress = self._stress_energy(i)
        D = math.sqrt(stress["total"])
        self.nodes[i].defect_index  = D
        self.nodes[i].stress_energy = stress["total"]
        return D

    # ── Gradient flow repair ──────────────────────────────────────────────────

    def _field_gradient(self, i: int) -> float:
        node   = self.nodes[i]
        lap    = self._discrete_laplacian(i)
        phid   = self._phi_deviation(i)
        lam    = self.lambda_
        F_lap  = -2 * lam["curvature"] * lap
        avg    = (sum(self.nodes[j].field for j in node.neighbors) / len(node.neighbors)
                  if node.neighbors else node.field)
        target = avg / node.phi_ratio if avg != 0 else node.field
        F_phi  = -2 * lam["phi_dev"] * phid * math.copysign(1.0, node.field - target)
        return F_lap + F_phi

    def _phase_gradient(self, i: int) -> float:
        node = self.nodes[i]
        if not node.neighbors:
            return 0.0
        sr = si = tw = 0.0
        for j in node.neighbors:
            w  = node.neighbor_weights.get(j, 1.0)
            sr += w * math.cos(self.nodes[j].phase)
            si += w * math.sin(self.nodes[j].phase)
            tw += w
        mean_phase = math.atan2(si / tw, sr / tw) if tw else 0.0
        dp = math.atan2(math.sin(mean_phase - node.phase),
                        math.cos(mean_phase - node.phase))
        S  = self._spin_alignment(i)
        return -2 * self.lambda_["spin"] * (1 - S) * dp

    def apply_gradient_flow(self, i: int) -> None:
        node = self.nodes[i]
        node.field  += self.eta_field * self._field_gradient(i)
        node.phase   = (node.phase + self.eta_phase * self._phase_gradient(i)) % (2 * math.pi)

    # ── Topological defect detection ──────────────────────────────────────────

    def detect_topological_defect(self, i: int) -> bool:
        """
        Return True if node i has a persistent (topologically-protected) defect.
        Criterion: defect index has remained above 0.8×D_critical for ≥ 10 ticks.
        """
        recent = self.history[i]["defect"][-10:]
        if len(recent) < 10:
            return False
        return all(D > self.D_critical * 0.8 for D in recent)

    # ── KT annealing repair ───────────────────────────────────────────────────

    def _kt_heal_phases(self, node_idx: int) -> bool:
        """
        Run KT annealing on the full network phase configuration to resolve
        a topological defect at node_idx.

        Returns True if the defect was resolved (D_after < D_critical),
        False if the defect persisted (caller should escalate to cleavage).
        """
        phases_before = np.array([n.phase for n in self.nodes])
        adjacency     = self._build_adjacency()

        # Seed with tick for reproducibility across repeated calls
        cfg = KTConfig(
            J=self.kt_config.J,
            T_start=self.kt_config.T_start,
            T_final=self.kt_config.T_final,
            n_steps=self.kt_config.n_steps,
            seed=self.tick,
        )
        optimized_phases, summary = anneal_network_phases(phases_before, adjacency, cfg)

        # Apply optimized phases to all nodes
        for j, node in enumerate(self.nodes):
            node.phase = float(optimized_phases[j])

        # Re-evaluate defect at the affected node
        D_after = self.compute_defect_index(node_idx)
        return D_after < self.D_critical

    # ── Structural cleavage (last resort) ────────────────────────────────────

    def apply_structural_cleavage(self, i: int) -> None:
        """
        Topological surgery: reset node i to its neighbourhood average.
        Last resort — only called after KT annealing has failed.
        """
        node = self.nodes[i]
        # Reduce coupling to neighbours
        for j in node.neighbors:
            if j in node.neighbor_weights:
                node.neighbor_weights[j] *= 0.1

        if node.neighbors:
            total_w = new_field = 0.0
            sr = si = 0.0
            for j in node.neighbors:
                w = node.neighbor_weights.get(j, 0.1)
                new_field += w * self.nodes[j].field
                sr        += math.cos(self.nodes[j].phase)
                si        += math.sin(self.nodes[j].phase)
                total_w   += w
            node.field  = new_field / total_w if total_w else 0.0
            node.phase  = math.atan2(si, sr) % (2 * math.pi)

        node.quarantined = False
        self.history[i]["defect"] = []

    # ── Consciousness protection ───────────────────────────────────────────────

    def _integrated_information(self, i: int) -> float:
        node = self.nodes[i]
        if not node.neighbors:
            return 0.0
        S = self._spin_alignment(i)
        fields = [self.nodes[j].field for j in node.neighbors]
        var    = float(np.var(fields)) if len(fields) > 1 else 0.0
        phi    = max(0.0, S) * math.log1p(var)
        node.phi_IIT = phi
        return phi

    def _protect_consciousness(self, i: int) -> bool:
        phi = self._integrated_information(i)
        if phi > 3.0:
            self.eta_field *= 0.5
            self.eta_phase *= 0.5
            return True
        return False

    # ── History helpers ───────────────────────────────────────────────────────

    def _update_history(self, i: int) -> None:
        node = self.nodes[i]
        hist = self.history[i]
        hist["field"].append(node.field)
        hist["phase"].append(node.phase)
        if len(hist["field"]) > 1:
            delta = hist["field"][-1] - hist["field"][-2]
            if delta > 0:
                hist["energy_in"].append(delta)
            else:
                hist["energy_out"].append(-delta)
        for key in ("field", "phase", "energy_in", "energy_out"):
            if len(hist[key]) > 20:
                hist[key] = hist[key][-20:]

    # ── Main protection cycle ─────────────────────────────────────────────────

    def tick_protection(self) -> Dict[str, list]:
        """
        Execute one full protection cycle over all nodes.

        Protection ladder per node:
        - D < 0.5×D_critical  → no action
        - 0.5×D_critical ≤ D < D_critical → gentle gradient flow
        - D_critical ≤ D < D_quarantine   → aggressive gradient flow or KT annealing
        - D ≥ D_quarantine                → quarantine

        Topological defects (persistent D ≥ 0.8×D_critical for ≥ 10 ticks):
        - First response: KT phase annealing (physics-based, non-destructive)
        - Fallback: structural cleavage (destructive reset — last resort)

        Returns
        -------
        dict with lists: flagged, quarantined, kt_healed, cleaved, consciousness_protected
        """
        self.tick += 1
        results: Dict[str, list] = {
            "flagged":                 [],
            "quarantined":             [],
            "kt_healed":               [],
            "cleaved":                 [],
            "consciousness_protected": [],
        }

        # 1. Update per-node histories
        for i in range(len(self.nodes)):
            self._update_history(i)

        # 2. Process each node
        for i, node in enumerate(self.nodes):
            # Handle quarantine expiry
            if node.quarantined:
                if node.quarantine_until > self.tick:
                    continue
                node.quarantined = False

            D = self.compute_defect_index(i)
            self.history[i]["defect"].append(D)

            # Consciousness protection (adjusts repair aggressiveness)
            if self._protect_consciousness(i):
                results["consciousness_protected"].append(i)

            # ── Decision tree ──────────────────────────────────────────────
            if D >= self.D_quarantine:
                node.quarantined      = True
                node.quarantine_until = self.tick + 40
                results["quarantined"].append(i)

            elif D >= self.D_critical:
                results["flagged"].append(i)

                if self.detect_topological_defect(i):
                    # Topological defect: try KT annealing first
                    resolved = self._kt_heal_phases(i)
                    if resolved:
                        results["kt_healed"].append(i)
                    else:
                        # KT annealing failed — fall back to structural cleavage
                        self.apply_structural_cleavage(i)
                        results["cleaved"].append(i)
                else:
                    # Non-topological: gradient flow repair
                    self.apply_gradient_flow(i)

            elif D > self.D_critical * 0.5:
                # Mild drift — gentle maintenance
                self.apply_gradient_flow(i)

        return results

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def network_summary(self) -> Dict[str, float]:
        """Return aggregate health metrics for the full network."""
        defects  = [n.defect_index for n in self.nodes]
        phi_vals = [n.phi_IIT      for n in self.nodes]
        phases   = np.array([n.phase for n in self.nodes])
        coherence = float(abs(np.mean(np.exp(1j * phases))))
        return {
            "mean_defect":       sum(defects) / max(1, len(defects)),
            "max_defect":        max(defects) if defects else 0.0,
            "mean_phi_IIT":      sum(phi_vals) / max(1, len(phi_vals)),
            "phase_coherence":   coherence,
            "quarantined_count": sum(1 for n in self.nodes if n.quarantined),
            "tick":              self.tick,
        }


# ─── Demo ─────────────────────────────────────────────────────────────────────

def _make_ring(n: int, phi_ratio: float = PHI) -> Tuple[List[GeometricNode], List[List[int]]]:
    """Create an n-node ring network with φ-scaled field values."""
    nodes = []
    rng = np.random.default_rng(0)
    for i in range(n):
        node = GeometricNode(
            id=i,
            field=1.0 + 0.1 * float(rng.standard_normal()),
            phase=float(rng.uniform(0, 2 * math.pi)),
            octahedral_state=i % 8,
            phi_ratio=phi_ratio,
        )
        nodes.append(node)
    # Ring topology: each node connects to its two neighbours
    for i in range(n):
        j = (i + 1) % n
        k = (i - 1) % n
        nodes[i].neighbors        = [j, k]
        nodes[i].neighbor_weights = {j: 1.0, k: 1.0}
    adj = [[( i+1)%n, (i-1)%n] for i in range(n)]
    return nodes, adj


if __name__ == "__main__":
    N = 12
    nodes, _ = _make_ring(N)

    # Inject a "trojan": anomalously high field + out-of-phase
    trojan = 5
    nodes[trojan].field = 5.0
    nodes[trojan].phase = 0.0
    print(f"Trojan injected at node {trojan} (field=5.0, phase=0.0)")

    engine = GeometricProtectionEngine(nodes)

    for tick in range(30):
        results = engine.tick_protection()
        if any(results[k] for k in ("flagged", "quarantined", "kt_healed", "cleaved")):
            print(f"Tick {tick:2d}: flagged={results['flagged']} "
                  f"kt_healed={results['kt_healed']} cleaved={results['cleaved']} "
                  f"quarantined={results['quarantined']}")

    s = engine.network_summary()
    print(f"\nFinal: mean_defect={s['mean_defect']:.3f} "
          f"phase_coherence={s['phase_coherence']:.3f} "
          f"tick={s['tick']}")
