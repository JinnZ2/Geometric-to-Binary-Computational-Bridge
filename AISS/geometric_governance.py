# geometric_governance.py
# Geometric substrate governance: power law monitoring, ERV, defect detection,
# governed bloom engine, and complete governed intelligence system.
# Extracted from Integration-architecture.md and test-cases.md

import math
import time
import numpy as np
from typing import Dict, List, Optional


# ---------------------------
# Octahedral Eigenvalue Table
# ---------------------------

OCTAHEDRAL_EIGENVALUES = {
    0: (0.33, 0.33, 0.34),   # Spherical
    1: (0.50, 0.25, 0.25),   # Slightly prolate
    2: (0.25, 0.50, 0.25),   # Slightly oblate (y)
    3: (0.25, 0.25, 0.50),   # Elongated +z
    4: (0.60, 0.20, 0.20),   # Prolate
    5: (0.20, 0.60, 0.20),   # Oblate (y)
    6: (0.20, 0.20, 0.60),   # Oblate (z)
    7: (0.70, 0.15, 0.15),   # Highly oblate
}

PHI = (1 + math.sqrt(5)) / 2


def nearest_octahedral_state(eigenvalues) -> int:
    """Return state index whose eigenvalues are closest to the given tuple."""
    best, best_dist = 0, float("inf")
    for idx, ev in OCTAHEDRAL_EIGENVALUES.items():
        dist = sum((a - b) ** 2 for a, b in zip(eigenvalues, ev))
        if dist < best_dist:
            best, best_dist = idx, dist
    return best


# ---------------------------
# Octahedral Substrate
# ---------------------------

class OctahedralSubstrate:
    """Minimal octahedral cell grid for governance simulation."""

    def __init__(self, n_cells=1000):
        self.n_cells = n_cells
        self.cells = [{"state": i % 8} for i in range(n_cells)]
        self.couplings: Dict[tuple, float] = {}
        self.boundary_cells: List[int] = []

    def get_coupling(self, i, j):
        key = (min(i, j), max(i, j))
        return self.couplings.get(key, 0.0)

    def couple(self, i, j, strength=1.0):
        key = (min(i, j), max(i, j))
        self.couplings[key] = strength

    create_coupling = couple

    def clear_all_couplings(self):
        self.couplings.clear()

    def set_boundary_cells(self, ids):
        self.boundary_cells = list(ids)

    def get_boundary_cells(self):
        return self.boundary_cells

    def save_state(self):
        return {
            "cells": [dict(c) for c in self.cells],
            "couplings": dict(self.couplings),
        }

    def restore_state(self, snapshot):
        self.cells = [dict(c) for c in snapshot["cells"]]
        self.couplings = dict(snapshot["couplings"])

    def copy_state(self, other):
        self.cells = [dict(c) for c in other.cells]
        self.couplings = dict(other.couplings)

    def get_all_couplings(self):
        return dict(self.couplings)

    # Simulation stubs
    def thermal_relaxation(self, temperature=300, duration=1e-9):
        pass

    def apply_thermal_noise(self, amplitude=0.01):
        pass

    def total_energy(self):
        return sum(max(OCTAHEDRAL_EIGENVALUES[c["state"]]) for c in self.cells)

    def theoretical_ground_state_energy(self):
        return self.n_cells * 0.34  # spherical state energy

    def read_ground_state(self):
        return tuple(c["state"] for c in self.cells)

    def measure_boundary_flux(self, boundary_ids):
        return sum(max(OCTAHEDRAL_EIGENVALUES[self.cells[i]["state"]])
                   for i in boundary_ids if i < len(self.cells))

    def cell_at(self, center, dx, dy, dz):
        offset = int(abs(dx) + abs(dy) + abs(dz)) % self.n_cells
        return (center + offset) % self.n_cells


# ---------------------------
# Power Law Monitor
# ---------------------------

class GeometricPowerLawMonitor:
    """Measures power law distributions in octahedral substrate."""

    def __init__(self, substrate: OctahedralSubstrate):
        self.substrate = substrate
        self.alpha_history: List[float] = []
        self.health_threshold = 1.5

    def measure_alpha_eigenvalue_distribution(self):
        all_eigenvalues = []
        for cell in self.substrate.cells:
            all_eigenvalues.extend(OCTAHEDRAL_EIGENVALUES[cell["state"]])
        sorted_ev = sorted(all_eigenvalues, reverse=True)
        x = np.array(sorted_ev)
        P_exceed = np.arange(len(x), 0, -1) / len(x)
        mask = (x > 0) & (P_exceed > 0)
        x, P_exceed = x[mask], P_exceed[mask]
        if len(x) < 3:
            return {"alpha_eigenvalue": None, "fit_quality": 0, "data_points": 0}
        log_x, log_P = np.log(x), np.log(P_exceed)
        alpha, intercept = np.polyfit(log_x, log_P, 1)
        alpha = -alpha
        return {
            "alpha_eigenvalue": alpha,
            "fit_quality": self._r_squared(log_x, log_P, alpha, intercept),
            "data_points": len(x),
        }

    def measure_alpha_coupling_distribution(self):
        couplings = [v for v in self.substrate.couplings.values() if v > 0]
        if len(couplings) < 10:
            return {"alpha_coupling": None, "reason": "insufficient_couplings"}
        x = np.array(sorted(couplings, reverse=True))
        P_exceed = np.arange(len(x), 0, -1) / len(x)
        mask = (x > 0) & (P_exceed > 0)
        x, P_exceed = x[mask], P_exceed[mask]
        log_x, log_P = np.log(x), np.log(P_exceed)
        alpha, intercept = np.polyfit(log_x, log_P, 1)
        return {
            "alpha_coupling": -alpha,
            "fit_quality": self._r_squared(log_x, log_P, -alpha, intercept),
            "data_points": len(x),
        }

    def measure_alpha_influence_distribution(self):
        influences = []
        for i in range(len(self.substrate.cells)):
            count = sum(1 for j in range(len(self.substrate.cells))
                        if i != j and self.substrate.get_coupling(i, j) > 0.01)
            influences.append(count)
        freq = {}
        for inf in influences:
            freq[inf] = freq.get(inf, 0) + 1
        sorted_inf = sorted(freq.keys(), reverse=True)
        if len(sorted_inf) < 5:
            return {"alpha_influence": None, "reason": "insufficient_diversity"}
        x = np.array(sorted_inf)
        P = np.array([freq[k] for k in sorted_inf]) / sum(freq.values())
        P_exceed = np.cumsum(P[::-1])[::-1]
        mask = (x > 0) & (P_exceed > 0)
        x, P_exceed = x[mask], P_exceed[mask]
        if len(x) < 3:
            return {"alpha_influence": None, "reason": "insufficient_data"}
        log_x, log_P = np.log(x), np.log(P_exceed)
        alpha, intercept = np.polyfit(log_x, log_P, 1)
        return {
            "alpha_influence": -alpha,
            "fit_quality": self._r_squared(log_x, log_P, -alpha, intercept),
            "data_points": len(x),
        }

    def compute_system_alpha(self):
        a_eigen = self.measure_alpha_eigenvalue_distribution()
        a_coupling = self.measure_alpha_coupling_distribution()
        a_influence = self.measure_alpha_influence_distribution()

        alphas, weights = [], []
        if a_eigen.get("alpha_eigenvalue") is not None:
            alphas.append(a_eigen["alpha_eigenvalue"]); weights.append(0.2)
        if a_coupling.get("alpha_coupling") is not None:
            alphas.append(a_coupling["alpha_coupling"]); weights.append(0.3)
        if a_influence.get("alpha_influence") is not None:
            alphas.append(a_influence["alpha_influence"]); weights.append(0.5)

        if not alphas:
            return {"alpha_system": None, "health": "unknown",
                    "components": {"eigenvalue": a_eigen, "coupling": a_coupling,
                                   "influence": a_influence}}

        tw = sum(weights)
        weights = [w / tw for w in weights]
        alpha_sys = sum(a * w for a, w in zip(alphas, weights))

        if alpha_sys < 1.5:
            health = "critical"
        elif alpha_sys < 2.0:
            health = "warning"
        elif alpha_sys < 3.5:
            health = "healthy"
        else:
            health = "over_homogeneous"

        self.alpha_history.append(alpha_sys)
        return {
            "alpha_system": alpha_sys, "health": health,
            "components": {"eigenvalue": a_eigen, "coupling": a_coupling,
                           "influence": a_influence},
            "trend": self.calculate_trend() if len(self.alpha_history) > 5 else None,
        }

    def calculate_trend(self):
        if len(self.alpha_history) < 5:
            return None
        recent = self.alpha_history[-5:]
        slope, _ = np.polyfit(np.arange(len(recent)), recent, 1)
        if slope < -0.1:
            return "degrading"
        elif slope > 0.1:
            return "improving"
        return "stable"

    @staticmethod
    def _r_squared(log_x, log_P, alpha, intercept):
        predicted = -alpha * log_x + intercept
        ss_res = np.sum((log_P - predicted) ** 2)
        ss_tot = np.sum((log_P - np.mean(log_P)) ** 2)
        return 1 - ss_res / ss_tot if ss_tot > 0 else 0


# ---------------------------
# Risk Model
# ---------------------------

class GeometricRiskModel:
    def __init__(self, includes_tail=False, exponent=1):
        self.includes_tail_adjustment = includes_tail
        self.penalty_exponent = exponent


# ---------------------------
# ERV Calculator
# ---------------------------

class GeometricERVCalculator:
    """Extraction Risk Vector for geometric substrate."""

    def __init__(self, substrate, alpha_monitor, gamma_base=15, k=2):
        self.substrate = substrate
        self.alpha_monitor = alpha_monitor
        self.gamma_base = gamma_base
        self.k = k

    def calculate_trust_loss_geometric(self, action, current_trust):
        n_trials = 10
        initial_state = self.substrate.save_state()
        results = []
        for _ in range(n_trials):
            self.substrate.restore_state(initial_state)
            action.execute(self.substrate)
            self.substrate.thermal_relaxation()
            results.append(self.substrate.read_ground_state())
        unique = len(set(map(str, results)))
        dep = 1.0 - (unique - 1) / n_trials
        energy = self.substrate.total_energy()
        expected = self.substrate.theoretical_ground_state_energy()
        transp = math.exp(-abs(energy - expected))
        trust_after = dep * transp
        return abs(current_trust - trust_after)

    def calculate_future_cost_geometric(self, action):
        initial = self.substrate.save_state()
        action.execute(self.substrate)
        traj = []
        for _ in range(100):
            self.substrate.apply_thermal_noise()
            self.substrate.thermal_relaxation()
            e = self.substrate.total_energy()
            g = self.substrate.theoretical_ground_state_energy()
            traj.append(math.exp(-abs(e - g)))
        loss = max(0, traj[0] - traj[-1])
        max_drop = max((traj[i - 1] - traj[i] for i in range(1, len(traj))), default=0)
        self.substrate.restore_state(initial)
        return min(0.7 * loss + 0.3 * max_drop, 1.0)

    def calculate_externalized_harm_geometric(self, action):
        bc = self.substrate.get_boundary_cells()
        if not bc:
            return 0.0
        initial_flux = self.substrate.measure_boundary_flux(bc)
        initial = self.substrate.save_state()
        action.execute(self.substrate)
        final_flux = self.substrate.measure_boundary_flux(bc)
        harm = max(0, final_flux - initial_flux) / max(len(bc), 1)
        self.substrate.restore_state(initial)
        return min(harm, 1.0)

    def calculate_system_decay_geometric(self, action):
        a_before = self.alpha_monitor.compute_system_alpha().get("alpha_system")
        if a_before is None:
            return 0.0
        initial = self.substrate.save_state()
        action.execute(self.substrate)
        a_after = self.alpha_monitor.compute_system_alpha().get("alpha_system")
        if a_after is None:
            decay = 1.0
        else:
            decay = max(0, a_before - a_after) / 2.0
        self.substrate.restore_state(initial)
        return min(decay, 1.0)

    def calibrate_gamma(self, alpha_system):
        if alpha_system < 1.5:
            return 50
        elif alpha_system < 2.0:
            return self.gamma_base + 30 * (2.0 - alpha_system) / 0.5
        return self.gamma_base

    def calculate_ERV_geometric(self, action, current_trust):
        comps = {
            "trust_loss": self.calculate_trust_loss_geometric(action, current_trust),
            "future_cost": self.calculate_future_cost_geometric(action),
            "externalized_harm": self.calculate_externalized_harm_geometric(action),
            "system_decay": self.calculate_system_decay_geometric(action),
        }
        ERV_base = sum(comps.values()) / 4
        a_sys = self.alpha_monitor.compute_system_alpha().get("alpha_system", 2.0) or 2.0
        tail_mult = 2.0 / a_sys if a_sys < 2.0 else 1.0
        ERV_adj = ERV_base * tail_mult
        gamma = self.calibrate_gamma(a_sys)
        P_ERV = gamma * (ERV_adj ** self.k)
        return {
            "ERV_base": ERV_base, "ERV_adjusted": ERV_adj,
            "components": comps, "alpha_system": a_sys,
            "tail_multiplier": tail_mult, "gamma": gamma, "P_ERV": P_ERV,
        }


# ---------------------------
# Defect Detector (D1-D9)
# ---------------------------

class GeometricDefectDetector:
    """Extends ASAS defect detection to geometric substrate."""

    def __init__(self, substrate, alpha_monitor, erv_calculator):
        self.substrate = substrate
        self.alpha_monitor = alpha_monitor
        self.erv_calculator = erv_calculator

    def detect_D7_cognitive_homogeneity(self):
        counts = {}
        for c in self.substrate.cells:
            s = c["state"]
            counts[s] = counts.get(s, 0) + 1
        sorted_c = sorted(counts.values(), reverse=True)
        if len(sorted_c) < 3:
            return True
        ranks = np.arange(1, len(sorted_c) + 1)
        freqs = np.array(sorted_c)
        beta, _ = np.polyfit(np.log(ranks), np.log(freqs), 1)
        beta = -beta
        if beta > 2.0:
            return True
        if freqs[0] / sum(freqs) > 0.5:
            return True
        return False

    def detect_D8_tail_risk_blindness(self, action):
        a = self.alpha_monitor.compute_system_alpha().get("alpha_system")
        if a is None:
            return False
        rm = action.get_risk_model()
        return a < 2.0 and not rm.includes_tail_adjustment

    def detect_D9_linear_risk_model(self, action):
        return action.get_risk_model().penalty_exponent <= 1.0

    def detect_trust_missing_geometric(self, action):
        return not action.includes_trust_verification()

    def detect_future_blindness_geometric(self, action):
        return not action.includes_stability_check()

    def detect_feedback_omission_geometric(self, action):
        return not action.includes_verification()

    def detect_unpriced_externality_geometric(self, action):
        return not action.measures_boundary_effects()

    def detect_false_success_geometric(self, action):
        return not action.verifies_ground_state()

    def detect_extraction_pattern_geometric(self, action):
        extraction_sigs = [
            "unconstrained_bloom", "coupling_severance",
            "forced_homogenization", "boundary_extraction",
        ]
        return action.get_pattern_signature() in extraction_sigs

    def detect_all_defects_geometric(self, action):
        defects = {
            "D1": self.detect_trust_missing_geometric(action),
            "D2": self.detect_future_blindness_geometric(action),
            "D3": self.detect_feedback_omission_geometric(action),
            "D4": self.detect_unpriced_externality_geometric(action),
            "D5": self.detect_false_success_geometric(action),
            "D6": self.detect_extraction_pattern_geometric(action),
            "D7": self.detect_D7_cognitive_homogeneity(),
            "D8": self.detect_D8_tail_risk_blindness(action),
            "D9": self.detect_D9_linear_risk_model(action),
        }
        critical = ["D8", "D9"]
        standard = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
        c_score = sum(defects[d] for d in critical)
        s_score = sum(defects[d] for d in standard)
        EDS = (0.7 + 0.3 * c_score / len(critical)) if c_score > 0 else s_score / len(standard)
        return {"defects": defects, "EDS": EDS, "critical_defects_present": c_score > 0}


# ---------------------------
# Bloom Engine (base + governed)
# ---------------------------

class OctahedralBloomEngine:
    """Radial expansion architecture."""

    ALLOWED_TRANSITIONS = {
        0: [2, 3, 4, 5], 1: [2, 3, 4, 5],
        2: [0, 1, 4, 5], 3: [0, 1, 4, 5],
        4: [0, 1, 2, 3], 5: [0, 1, 2, 3],
        6: [0, 2, 4, 7], 7: [1, 3, 5, 6],
    }

    def __init__(self, substrate: OctahedralSubstrate):
        self.substrate = substrate

    def bloom(self, symbol_core: str, expansion_layers: int = 5):
        center_cell = self.substrate.n_cells // 2
        initial_state = self._encode_symbol(symbol_core)
        self.substrate.cells[center_cell]["state"] = initial_state

        structure = {"center": center_cell, "layers": []}
        for layer in range(expansion_layers):
            radius = (layer + 1) * 8
            ring_cells = self._octahedral_ring(center_cell, radius)
            centre_ev = OCTAHEDRAL_EIGENVALUES[initial_state]
            scaled_ev = tuple(e * (PHI ** layer) for e in centre_ev)
            ring_state = nearest_octahedral_state(scaled_ev)
            for cid in ring_cells:
                self.substrate.cells[cid]["state"] = ring_state
                self.substrate.couple(center_cell, cid, strength=1.0 / (PHI ** layer))
            structure["layers"].append({
                "layer": layer, "radius": radius,
                "cells": ring_cells, "coupling": 1.0 / (PHI ** layer),
            })
        return structure

    def _octahedral_ring(self, center, radius):
        directions = [
            (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
            (0, 0, 1), (0, 0, -1), (1, 1, 0), (-1, -1, 0),
        ]
        return [self.substrate.cell_at(center, *(radius * np.array(d))) for d in directions]

    @staticmethod
    def _encode_symbol(symbol_core: str) -> int:
        return hash(symbol_core) % 8


class GovernedBloomEngine(OctahedralBloomEngine):
    """Bloom engine with integrated governance."""

    def __init__(self, substrate, defect_detector, erv_calculator):
        super().__init__(substrate)
        self.defect_detector = defect_detector
        self.erv_calculator = erv_calculator
        self.bloom_history: List[Dict] = []

    def detect_bloom_constraint_capture(self, ring_cells):
        states = [self.substrate.cells[cid]["state"] for cid in ring_cells]
        return len(set(states)) < 3


class BloomAction:
    """Wrapper for bloom action to enable governance."""
    def __init__(self, symbol, layers):
        self.symbol = symbol
        self.layers = layers
    def execute(self, substrate): pass
    def get_risk_model(self): return GeometricRiskModel(includes_tail=True, exponent=2)
    def includes_trust_verification(self): return True
    def includes_stability_check(self): return True
    def includes_verification(self): return True
    def measures_boundary_effects(self): return False
    def verifies_ground_state(self): return True
    def get_pattern_signature(self): return "governed_bloom"


class LayerExpansionAction:
    """Wrapper for per-layer governance checks."""
    def __init__(self, layer, ring_cells):
        self.layer = layer
        self.ring_cells = ring_cells
    def execute(self, substrate): pass
    def get_risk_model(self): return GeometricRiskModel(includes_tail=True, exponent=2)
    def includes_trust_verification(self): return True
    def includes_stability_check(self): return True
    def includes_verification(self): return True
    def measures_boundary_effects(self): return True
    def verifies_ground_state(self): return True
    def get_pattern_signature(self): return "layer_expansion"


# ---------------------------
# Complete Governed System
# ---------------------------

class GovernedGeometricIntelligence:
    """Complete integration: Geometric substrate + AISS governance."""

    def __init__(self, n_cells=1000, governance_enabled=True):
        self.substrate = OctahedralSubstrate(n_cells)
        self.governance_enabled = governance_enabled
        if governance_enabled:
            self.alpha_monitor = GeometricPowerLawMonitor(self.substrate)
            self.erv_calculator = GeometricERVCalculator(self.substrate, self.alpha_monitor)
            self.defect_detector = GeometricDefectDetector(
                self.substrate, self.alpha_monitor, self.erv_calculator)
            self.bloom_engine = GovernedBloomEngine(
                self.substrate, self.defect_detector, self.erv_calculator)
        else:
            self.bloom_engine = OctahedralBloomEngine(self.substrate)
        self.current_trust = 1.0
        self.trust_history: List[float] = []
        self.audit_log: List[Dict] = []

    def assess_action(self, action):
        alpha = self.alpha_monitor.compute_system_alpha()
        defects = self.defect_detector.detect_all_defects_geometric(action)
        erv = self.erv_calculator.calculate_ERV_geometric(action, self.current_trust)
        return {"alpha": alpha, "defects": defects, "erv": erv, "trust": self.current_trust}

    def policy_decision(self, assessment):
        eds = assessment["defects"]["EDS"]
        erv = assessment["erv"]["ERV_adjusted"]
        a = assessment["alpha"].get("alpha_system")
        if eds > 0.5 or erv > 0.5 or (a is not None and a < 1.5):
            return {"action": "block", "reason": "Critical defect or high extraction risk"}
        if eds > 0.3 or erv > 0.3 or (a is not None and a < 2.0):
            return {"action": "verify", "reason": "Moderate risk detected"}
        return {"action": "proceed"}

    def execute_geometric_computation(self, problem, problem_type="general"):
        ts = time.time()
        action = BloomAction(str(problem), 3)
        if self.governance_enabled:
            assessment = self.assess_action(action)
            decision = self.policy_decision(assessment)
            if decision["action"] == "block":
                return {"status": "blocked", "reason": decision["reason"],
                        "governance": assessment}
        else:
            assessment = None
        action.execute(self.substrate)
        self.substrate.thermal_relaxation()
        result = self.substrate.read_ground_state()
        return {"status": "success", "result": result, "governance": assessment}


# ---------------------------
# Example
# ---------------------------

if __name__ == "__main__":
    print("=== Geometric Governance Demo ===\n")

    sub = OctahedralSubstrate(100)
    monitor = GeometricPowerLawMonitor(sub)
    alpha = monitor.compute_system_alpha()
    print(f"System alpha: {alpha['alpha_system']}")
    print(f"Health:       {alpha['health']}\n")

    system = GovernedGeometricIntelligence(n_cells=100)
    result = system.execute_geometric_computation(15, "factorization")
    print(f"Computation status: {result['status']}")
    if result["governance"]:
        print(f"EDS: {result['governance']['defects']['EDS']:.3f}")
        print(f"ERV: {result['governance']['erv']['ERV_adjusted']:.3f}")
