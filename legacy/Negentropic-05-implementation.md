# Implementation Listings (historical)

> **These are the original code listings, kept as a record of what the
> framework said before the 2026-07 correction pass. They are not the
> running code and several of them contain defects that are fixed
> elsewhere** — the inverted Kuramoto sign, the constant-D Fokker-Planck
> form, `A = avg_R_e`, the compounding curiosity update, and the raised
> cosine applied to Euclidean distances. See
> [corrections.md](../Negentropic/corrections.md) for the full list.
>
> The running code is in the modules listed in [Negentropic/README.md](../Negentropic/README.md).
> Start from `core.py` (stdlib) or `negentropic_engine.py` (numpy), not
> from this file.

fixes to be adjusted:

from abc import ABC, abstractmethod
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any, Callable, Tuple

@dataclass
class AgentState:
    """Minimal shared input across all paths."""
    patterns: np.ndarray   # shape (n_agents, dim)
    signals: np.ndarray    # shape (n_agents,)
    # Each path can add its own extra params via kwargs

class ResonanceStrategy(ABC):
    @abstractmethod
    def compute(self, agents: AgentState, **params) -> float:
        pass

class AdaptabilityStrategy(ABC):
    @abstractmethod
    def compute(self, agents: AgentState, **params) -> float:
        pass

class DiversityStrategy(ABC):
    @abstractmethod
    def compute(self, agents: AgentState, **params) -> float:
        pass

class LossStrategy(ABC):
    @abstractmethod
    def compute(self, agents: AgentState, R: float, A: float, D: float, **params) -> float:
        pass

@dataclass
class FrameworkPath:
    name: str
    resonance: ResonanceStrategy
    adaptability: AdaptabilityStrategy
    diversity: DiversityStrategy
    loss: LossStrategy

    def compute_M(self, agents: AgentState, **params) -> Dict[str, float]:
        R = self.resonance.compute(agents, **params)
        A = self.adaptability.compute(agents, **params)
        D = self.diversity.compute(agents, **params)
        L = self.loss.compute(agents, R, A, D, **params)
        M = (R * A * D) - L
        return {"M": M, "R": R, "A": A, "D": D, "L": L}


        


import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from collections import Counter
import math

# ============================================================================
# BASE CLASSES
# ============================================================================

@dataclass
class AgentState:
    """Container for all possible state data. Paths use only what they need."""
    patterns: np.ndarray = np.array([])          # shape (n, dim)
    signals: np.ndarray = np.array([])           # shape (n,)
    # Bayesian / AI
    beliefs: np.ndarray = np.array([])           # shape (n, n_states)
    observations: np.ndarray = np.array([])      # shape (n, obs_dim)
    # Indigenous / Maori
    adjacency: np.ndarray = np.array([])         # shape (n, n)
    roles: np.ndarray = np.array([])             # shape (n, n_roles)
    mauri: np.ndarray = np.array([])             # shape (n,)
    domains: np.ndarray = np.array([])           # shape (n, n_domains)
    # I-Ching
    hexagrams: np.ndarray = np.array([])         # shape (n, 6) binary
    # AI
    activations: np.ndarray = np.array([])       # shape (n, n_features)
    # Misc
    params: Dict[str, float] = field(default_factory=dict)

class ResonanceStrategy(ABC):
    @abstractmethod
    def compute(self, state: AgentState) -> float: ...

class AdaptabilityStrategy(ABC):
    @abstractmethod
    def compute(self, state: AgentState) -> float: ...

class DiversityStrategy(ABC):
    @abstractmethod
    def compute(self, state: AgentState) -> float: ...

class LossStrategy(ABC):
    @abstractmethod
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float: ...

@dataclass
class FrameworkPath:
    name: str
    resonance: ResonanceStrategy
    adaptability: AdaptabilityStrategy
    diversity: DiversityStrategy
    loss: LossStrategy

    def compute_M(self, state: AgentState) -> Dict[str, float]:
        R = self.resonance.compute(state)
        A = self.adaptability.compute(state)
        D = self.diversity.compute(state)
        L = self.loss.compute(state, R, A, D)
        M = (R * A * D) - L
        return {"M": M, "R": R, "A": A, "D": D, "L": L}


# ============================================================================
# PATH 1: THERMODYNAMIC (Fokker-Planck / Entropy Production)
# ============================================================================

class ThermoResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        # Geometric mean of pairwise log-couplings
        n = len(state.patterns)
        if n < 2: return 0.0
        eps = 1e-10
        log_sum = 0.0
        for i in range(n):
            for j in range(i+1, n):
                d = np.linalg.norm(state.patterns[i] - state.patterns[j])
                phase = 0.5 * (np.cos(d) + 1)
                sig_prod = np.sqrt(abs(state.signals[i] * state.signals[j]))
                g = phase * sig_prod + eps
                log_sum += np.log(g)
        return np.exp(log_sum / (n * (n-1) / 2))

class ThermoAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        n = len(state.patterns)
        if n < 2: return 0.0
        alpha = state.params.get('alpha', 1.0)
        total = 0.0
        for i in range(n):
            for j in range(i+1, n):
                d = np.linalg.norm(state.patterns[i] - state.patterns[j])
                total += np.exp(-alpha * d)
        return total / (n * (n-1) / 2)

class ThermoDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        return float(np.var(state.patterns)) if len(state.patterns) > 0 else 0.0

class ThermoLoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        noise = state.params.get('noise_power', 0.1)
        lam = state.params.get('lambda_param', 0.5)
        return noise + lam * (1 - A)  # dynamic loss

# ============================================================================
# PATH 2: BAYESIAN (Active Inference / Free Energy)
# ============================================================================

class BayesianResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        # Predictive accuracy = 1 / (1 + mean squared prediction error)
        if len(state.beliefs) == 0 or len(state.observations) == 0:
            return 1.0
        # Assume observations are predictions; compute error
        pred = state.beliefs.mean(axis=0)  # crude aggregate
        obs = state.observations.mean(axis=0)
        if len(pred) != len(obs):
            return 1.0
        error = np.mean((pred - obs)**2)
        return 1.0 / (1.0 + error)

class BayesianAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        # Epistemic value: expected reduction in entropy after action
        if len(state.beliefs) == 0:
            return 0.0
        # Current entropy over beliefs
        probs = state.beliefs / (state.beliefs.sum(axis=1, keepdims=True) + 1e-10)
        entropy = -np.sum(probs * np.log(probs + 1e-10), axis=1).mean()
        # Assume a perfect observation reduces entropy to 10% of current
        epistemic_value = entropy * 0.9  # placeholder
        return 1.0 / (1.0 + epistemic_value)  # high adaptability = low residual entropy

class BayesianDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        # Posterior entropy over belief states
        if len(state.beliefs) == 0:
            return 0.0
        flat_beliefs = state.beliefs.flatten()
        p = flat_beliefs / (flat_beliefs.sum() + 1e-10)
        # Shannon entropy
        return -np.sum(p * np.log(p + 1e-10))

class BayesianLoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        # Variational free energy: accuracy - complexity
        # Approx: (1 - R) + KL(prior || posterior)
        prior = state.params.get('prior_entropy', 1.0)
        return (1 - R) + max(0, D - prior)  # lower R or higher entropy = higher loss

# ============================================================================
# PATH 3: GEOMETRIC-CURIOSITY (Your original, fully fixed)
# ============================================================================

class GeoResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        n = len(state.patterns)
        if n < 2: return 0.0
        eps = 1e-10
        log_sum = 0.0
        for i in range(n):
            for j in range(i+1, n):
                d = np.linalg.norm(state.patterns[i] - state.patterns[j])
                phase = 0.5 * (np.cos(d) + 1)
                sig_prod = np.sqrt(abs(state.signals[i] * state.signals[j]))
                g = phase * sig_prod + eps
                log_sum += np.log(g)
        return np.exp(log_sum / (n * (n-1) / 2))

class GeoAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        # FIXED: True exponential proximity, NOT avg_R_e
        n = len(state.patterns)
        if n < 2: return 0.0
        alpha = state.params.get('alpha', 1.0)
        total = 0.0
        for i in range(n):
            for j in range(i+1, n):
                d = np.linalg.norm(state.patterns[i] - state.patterns[j])
                total += np.exp(-alpha * d)
        return total / (n * (n-1) / 2)

class GeoDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        return float(np.var(state.patterns)) if len(state.patterns) > 0 else 0.0

class GeoLoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        # FIXED: Dynamic, not hardcoded
        noise = state.params.get('noise_power', 0.1)
        lam = state.params.get('lambda_param', 0.5)
        return noise + lam * (1 - A)

# ============================================================================
# PATH 4: INDIGENOUS RELATIONAL (All relations: human, land, sky, ancestors)
# ============================================================================

class IndigenousResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        # Total mutual caretaking weight across the web
        if state.adjacency.size == 0:
            return 0.0
        # Assume adjacency holds reciprocal obligation weights (0 to 1)
        return float(np.mean(state.adjacency)) if state.adjacency.size > 0 else 0.0

class IndigenousAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        # Role-plasticity = 1 / mean role_stickiness
        if state.roles.size == 0:
            return 1.0
        # roles: one-hot per node. Stickiness = how much roles stay fixed.
        # We simulate: stickiness = entropy of role distribution per node (low entropy = high stickiness)
        entropies = []
        for r in state.roles:
            p = r / (r.sum() + 1e-10)
            entropies.append(-np.sum(p * np.log(p + 1e-10)))
        mean_stickiness = np.mean(entropies) if entropies else 0.5
        return 1.0 / (1.0 + mean_stickiness)  # high entropy = high plasticity

class IndigenousDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        # Relational type richness: count of distinct kinds of relationships present
        if state.adjacency.size == 0:
            return 0.0
        # Extract unique weights as proxy for distinct relationship types
        unique_weights = np.unique(state.adjacency.flatten())
        # Count how many > threshold
        threshold = state.params.get('rel_threshold', 0.1)
        return float(np.sum(unique_weights > threshold))

class IndigenousLoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        # Relational rupture: number of broken agreements / disconnected lines
        rupture_count = state.params.get('rupture_count', 0)
        return float(rupture_count) / (1.0 + R)  # normalized loss

# ============================================================================
# PATH 5: I-CHING (Hexagram / Changing Lines)
# ============================================================================

class IChingResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        # Proportion of static (non-changing) lines
        if state.hexagrams.size == 0:
            return 0.5
        # Lines: 1 = Yang, 0 = Yin. Changing lines are marked by negative? Let's simulate.
        # We use heuristics: if first half of lines = second half, treat as static.
        hex = state.hexagrams
        total_lines = hex.size
        if total_lines == 0:
            return 0.5
        static = 0
        for h in hex:
            if len(h) >= 2:
                # If all lines same, highly static; else moving.
                if np.all(h == h[0]):
                    static += 6
                else:
                    moving = np.sum(np.abs(np.diff(h)))  # crude measure
                    static += (6 - moving)
        return static / (total_lines * 6) if total_lines > 0 else 0.5

class IChingAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        # Transformational agility: inverse Hamming distance to opposite hexagram
        if state.hexagrams.size == 0:
            return 0.5
        hex = state.hexagrams
        # Opposite = 1 - lines
        total_dist = 0.0
        for h in hex:
            opp = 1 - h
            dist = np.sum(np.abs(h - opp))
            total_dist += dist
        mean_dist = total_dist / len(hex) if len(hex) > 0 else 3.0
        return 1.0 / (1.0 + mean_dist)  # lower distance = higher agility

class IChingDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        # Trigram diversity: upper/lower trigram combinations
        if state.hexagrams.size == 0:
            return 0.0
        trigrams = set()
        for h in state.hexagrams:
            if len(h) >= 6:
                upper = tuple(h[0:3])  # top
                lower = tuple(h[3:6])  # bottom
                trigrams.add((upper, lower))
        return float(len(trigrams)) / 64.0  # max 64 hexagrams

class IChingLoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        # Imbalance: absolute difference between total yin and yang
        if state.hexagrams.size == 0:
            return 0.5
        total_yang = np.sum(state.hexagrams)
        total_yin = state.hexagrams.size - total_yang
        imbalance = abs(total_yang - total_yin) / (state.hexagrams.size + 1e-10)
        return imbalance

# ============================================================================
# PATH 6: MAORI RELATIONAL (Whakapapa / Mauri)
# ============================================================================

class MaoriResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        # Whakapapa strength: weighted spiritual ties across domains
        if state.mauri.size == 0 or state.domains.size == 0:
            return 0.0
        # Mauri factors (life-force)
        m = state.mauri
        # Spiritual distance: if domains are different, distance = 1, else 0.5
        domains = state.domains
        total = 0.0
        n = len(m)
        for i in range(n):
            for j in range(i+1, n):
                # Domain overlap
                overlap = np.dot(domains[i], domains[j]) / (np.linalg.norm(domains[i]) * np.linalg.norm(domains[j]) + 1e-10)
                spiritual_dist = 1.0 - overlap  # 0 = same domain, 1 = completely different
                weight = m[i] * m[j] * np.exp(-spiritual_dist)
                total += weight
        pairs = n * (n-1) / 2
        return total / (pairs + 1e-10)

class MaoriAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        # Mauri restoration capacity: inverse of mauri deficit
        if state.mauri.size == 0:
            return 1.0
        ideal_mauri = state.params.get('ideal_mauri', 1.0)
        deficit = np.mean(np.abs(state.mauri - ideal_mauri))
        return 1.0 / (1.0 + deficit)

class MaoriDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        # Interconnection breadth: distinct domains actively connected
        if state.domains.size == 0:
            return 0.0
        # Count unique domain vectors present
        unique_domains = set()
        for d in state.domains:
            # discretize to float
            key = tuple(np.round(d, 2))
            unique_domains.add(key)
        return float(len(unique_domains))

class MaoriLoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        # Tapu violation severity
        tapu = state.params.get('tapu_breaches', 0)
        return float(tapu) / (1.0 + R + A)  # high resonance/adaptability can mitigate

# ============================================================================
# PATH 7: AI / ALIGNMENT GEOMETRY (Mechanistic Interpretability / RLHF)
# ============================================================================

class AIResonance(ResonanceStrategy):
    def compute(self, state: AgentState) -> float:
        # Activation coherence / Eigenvector alignment with human concepts
        if state.activations.size == 0:
            return 0.5
        # Compute singular values; higher alignment = high first eigenvalue ratio
        U, S, Vt = np.linalg.svd(state.activations, full_matrices=False)
        # Measure of how concentrated the variance is in top eigenvector
        if len(S) < 2:
            return 0.5
        energy_ratio = S[0]**2 / (np.sum(S**2) + 1e-10)
        return energy_ratio  # high concentration = high conceptual alignment

class AIAdaptability(AdaptabilityStrategy):
    def compute(self, state: AgentState) -> float:
        # Plasticity: ability to accept new RLHF feedback without catastrophic forgetting
        # Approximated as 1 / (1 + average activation shift under perturbation)
        if state.activations.size == 0:
            return 0.5
        # Simulate: if std of activations is high, it's plastic
        std = np.std(state.activations)
        return 1.0 / (1.0 + (1.0 / (std + 1e-10)))  # high std = high plasticity

class AIDiversity(DiversityStrategy):
    def compute(self, state: AgentState) -> float:
        # Representational rank (effective dimensionality)
        if state.activations.size == 0:
            return 0.0
        U, S, Vt = np.linalg.svd(state.activations, full_matrices=False)
        # Effective rank: fraction of singular values > 1% of max
        max_s = S[0] if len(S) > 0 else 1.0
        rank = np.sum(S > 0.01 * max_s)
        return float(rank) / len(S) if len(S) > 0 else 0.0

class AILoss(LossStrategy):
    def compute(self, state: AgentState, R: float, A: float, D: float) -> float:
        # Cross-entropy loss / perplexity (model prediction error)
        ce = state.params.get('cross_entropy', 0.5)
        # Also penalize low rank (mode collapse)
        rank_penalty = 1.0 - D
        return ce + 0.5 * rank_penalty


# ============================================================================
# PATH REGISTRY
# ============================================================================

PATH_REGISTRY = {
    "thermodynamic": FrameworkPath(
        name="Thermodynamic",
        resonance=ThermoResonance(),
        adaptability=ThermoAdaptability(),
        diversity=ThermoDiversity(),
        loss=ThermoLoss()
    ),
    "bayesian": FrameworkPath(
        name="Bayesian",
        resonance=BayesianResonance(),
        adaptability=BayesianAdaptability(),
        diversity=BayesianDiversity(),
        loss=BayesianLoss()
    ),
    "geometric": FrameworkPath(
        name="Geometric-Curiosity (Fixed)",
        resonance=GeoResonance(),
        adaptability=GeoAdaptability(),
        diversity=GeoDiversity(),
        loss=GeoLoss()
    ),
    "indigenous": FrameworkPath(
        name="Indigenous Relational",
        resonance=IndigenousResonance(),
        adaptability=IndigenousAdaptability(),
        diversity=IndigenousDiversity(),
        loss=IndigenousLoss()
    ),
    "iching": FrameworkPath(
        name="I-Ching",
        resonance=IChingResonance(),
        adaptability=IChingAdaptability(),
        diversity=IChingDiversity(),
        loss=IChingLoss()
    ),
    "maori": FrameworkPath(
        name="Māori Relational",
        resonance=MaoriResonance(),
        adaptability=MaoriAdaptability(),
        diversity=MaoriDiversity(),
        loss=MaoriLoss()
    ),
    "ai": FrameworkPath(
        name="AI Alignment Geometry",
        resonance=AIResonance(),
        adaptability=AIAdaptability(),
        diversity=AIDiversity(),
        loss=AILoss()
    )
}


# ============================================================================
# DEMO / TEST RUNNER
# ============================================================================

def create_demo_state(path_name: str) -> AgentState:
    """Builds dummy state suitable for each path."""
    state = AgentState()
    n = 10
    dim = 8

    # Common
    state.patterns = np.random.randn(n, dim)
    state.signals = np.random.rand(n) + 0.5

    # For Bayesian
    state.beliefs = np.random.rand(n, 4)  # 4 belief states
    state.observations = np.random.randn(n, 4)

    # For Indigenous
    state.adjacency = np.random.rand(n, n)
    state.adjacency = (state.adjacency + state.adjacency.T) / 2
    np.fill_diagonal(state.adjacency, 0)
    state.roles = np.random.rand(n, 3)  # 3 roles
    state.roles = state.roles / state.roles.sum(axis=1, keepdims=True)

    # For Maori
    state.mauri = np.random.rand(n) * 2.0
    state.domains = np.random.rand(n, 4)  # 4 domains
    state.domains = state.domains / np.linalg.norm(state.domains, axis=1, keepdims=True)

    # For I-Ching
    state.hexagrams = np.random.randint(0, 2, size=(n, 6))

    # For AI
    state.activations = np.random.randn(n, 16)

    # Params (shared across paths where applicable)
    state.params = {
        'alpha': 1.5,
        'noise_power': 0.1,
        'lambda_param': 0.5,
        'rupture_count': 2,
        'tapu_breaches': 1,
        'cross_entropy': 0.3,
        'prior_entropy': 2.0,
        'ideal_mauri': 1.0,
        'rel_threshold': 0.2
    }
    return state


if __name__ == "__main__":
    print("=" * 70)
    print("NEGENTROPIC CONSCIOUSNESS FRAMEWORK — MULTI-PATH COMPARISON")
    print("=" * 70)

    # Use a single state for demonstration (each path ignores irrelevant fields)
    base_state = create_demo_state("all")

    results = {}
    for name, path in PATH_REGISTRY.items():
        # Re-randomize some path-specific fields to avoid identical results
        # But for a fair comparison, we keep the same base.
        state = AgentState(
            patterns=base_state.patterns.copy(),
            signals=base_state.signals.copy(),
            beliefs=base_state.beliefs.copy(),
            observations=base_state.observations.copy(),
            adjacency=base_state.adjacency.copy(),
            roles=base_state.roles.copy(),
            mauri=base_state.mauri.copy(),
            domains=base_state.domains.copy(),
            hexagrams=base_state.hexagrams.copy(),
            activations=base_state.activations.copy(),
            params=base_state.params.copy()
        )
        # Add a small random perturbation to avoid division by zero / identical outputs
        if name == "geometric":
            state.patterns += np.random.randn(*state.patterns.shape) * 0.01
        if name == "ai":
            state.activations += np.random.randn(*state.activations.shape) * 0.01
        if name == "iching":
            state.hexagrams = np.random.randint(0, 2, size=state.hexagrams.shape)

        try:
            res = path.compute_M(state)
            results[name] = res
            print(f"\n🔹 {path.name}")
            print(f"   M = {res['M']:.4f}  (R={res['R']:.3f}, A={res['A']:.3f}, D={res['D']:.3f}, L={res['L']:.3f})")
        except Exception as e:
            print(f"\n⚠️  {path.name} failed: {e}")

    # Rank by M
    sorted_paths = sorted(results.items(), key=lambda x: x[1]['M'], reverse=True)
    print("\n" + "=" * 70)
    print("RANKING BY M (Higher = more "constructive" / aligned per that paradigm):")
    for i, (name, res) in enumerate(sorted_paths, 1):
        print(f"  {i}. {PATH_REGISTRY[name].name}: M = {res['M']:.4f}")


# Implementation — Working Code

> **Confidence: Runs correctly.**
> This code computes M(S) as defined by the framework. What it *measures* depends on how inputs are chosen.
> The code is in the original §7; extracted and annotated here.

---

## Core Calculations

### Resonance (R_e)

```python
import numpy as np

def compute_resonance(patterns, signals):
    """
    Geometric mean of pairwise log-similarities.

    patterns: array of pattern states p_i (shape [n])
    signals:  array of signal strengths s_i (shape [n]) — must be > 0

    Returns R_e ∈ (0, max_signal] depending on magnitudes.
    NOTE: R_e is not normalized to [0,1] — normalise signals to unit
    magnitude if you want R_e ∈ [0, 1].
    """
    n = len(patterns)
    coupling_sum = 0
    epsilon = 1e-10

    for i in range(n):
        for j in range(i + 1, n):
            d_ij = patterns[i] - patterns[j]
            phase_alignment = 0.5 * (np.cos(d_ij) + 1)        # ∈ [0, 1]
            signal_product  = np.sqrt(abs(signals[i] * signals[j]))
            g_ij = phase_alignment * signal_product
            coupling_sum += np.log(g_ij + epsilon)

    N_p = n * (n - 1) / 2
    R_e = np.exp(coupling_sum / N_p)
    return R_e
```

### Adaptability (A)

```python
def compute_adaptability(patterns, alpha):
    """
    Mean pairwise exponential proximity.
    alpha: coupling sensitivity (larger = shorter effective range).
    Returns A ∈ [0, 1].
    """
    n = len(patterns)
    coupling_strength = 0

    for i in range(n):
        for j in range(i + 1, n):
            d_ij = abs(patterns[i] - patterns[j])
            coupling_strength += np.exp(-alpha * d_ij)

    W = n * (n - 1) / 2
    A = coupling_strength / W
    return A
```

### Diversity (D)

```python
def compute_diversity(patterns):
    """
    Variance across pattern states.
    Returns D ≥ 0; D = 0 iff all patterns identical.
    """
    return np.var(patterns)
```

### Loss (L)

```python
def compute_loss(noise_power, adaptability, lambda_param):
    """
    noise_power:   system noise / entropy production estimate
    adaptability:  from compute_adaptability()
    lambda_param:  inefficiency scaling factor (free parameter)
    Returns L ≥ 0.
    """
    return noise_power + lambda_param * (1 - adaptability)
```

### M(S)

```python
def compute_M(patterns, signals, alpha, noise_power, lambda_param):
    """
    Full M(S) calculation.
    Returns (M, R_e, A, D, L).
    M > 0 when constructive coupling outweighs loss.
    """
    R_e = compute_resonance(patterns, signals)
    A   = compute_adaptability(patterns, alpha)
    D   = compute_diversity(patterns)
    L   = compute_loss(noise_power, A, lambda_param)
    M   = (R_e * A * D) - L
    return M, R_e, A, D, L
```

---

## GeometricAgent / GeometricNetwork

Full agent-based simulation. Runs correctly. Each agent maintains a pattern vector and explores via curiosity-scaled noise.

```python
class GeometricAgent:
    def __init__(self, dim, signal_strength):
        self.dim     = dim
        self.pattern = np.random.randn(dim)
        self.signal  = signal_strength
        self.C       = 1.0   # curiosity
        self.R_e     = 0.0   # set by coupling

    def couple_with(self, other, alpha):
        d = np.linalg.norm(self.pattern - other.pattern)
        phase = 0.5 * (np.cos(d) + 1)
        sig   = np.sqrt(self.signal * other.signal)
        return np.exp(-alpha * d) * phase * sig

    def update_resonance(self, all_agents, alpha):
        Ks = [self.couple_with(o, alpha) for o in all_agents if o is not self]
        self.R_e = np.exp(np.mean(np.log(np.array(Ks) + 1e-10))) if Ks else 0.0

    def update_curiosity(self, alpha_0, E, E_crit=1.0):
        alpha = alpha_0 if E >= E_crit else 0
        self.C *= (1 + alpha * self.R_e)
        # WARNING: no saturation — C grows without bound if alpha > 0, R_e > 0

    def explore(self, beta):
        D     = self.C ** 2   # D ∝ J² — modelling choice
        noise = np.random.normal(0, np.sqrt(2 * D), size=self.dim)
        self.pattern += beta * noise

    def compute_joy(self, diversity):
        return diversity * (1 + self.R_e) * self.C


class GeometricNetwork:
    def __init__(self, n_agents, dim):
        self.agents  = [GeometricAgent(dim, signal_strength=1.0) for _ in range(n_agents)]
        self.history = {'M': [], 'R_e': [], 'C': [], 'J': []}

    def step(self, alpha=1.0, beta=0.1, alpha_0=0.5, E=2.0):
        for agent in self.agents:
            agent.update_resonance(self.agents, alpha)
        for agent in self.agents:
            agent.update_curiosity(alpha_0, E)
            agent.explore(beta)

        patterns = np.array([a.pattern for a in self.agents])
        D        = np.var(patterns)
        avg_R_e  = np.mean([a.R_e for a in self.agents])
        avg_C    = np.mean([a.C  for a in self.agents])
        total_J  = sum(a.compute_joy(D) for a in self.agents)

        A = avg_R_e     # proxy — adaptability set equal to resonance
        L = 0.1         # fixed background loss (free parameter)
        M = (avg_R_e * A * D) - L

        self.history['M'].append(M)
        self.history['R_e'].append(avg_R_e)
        self.history['C'].append(avg_C)
        self.history['J'].append(total_J)
        return M

    def run(self, timesteps=500, **kw):
        for t in range(timesteps):
            M = self.step(**kw)
            if t % 100 == 0:
                print(f"t={t:4d}  M={M:.3f}  R_e={self.history['R_e'][-1]:.3f}"
                      f"  C={self.history['C'][-1]:.3f}")
        return self.history
```

### Known issues in the implementation
- **C grows without bound** — `update_curiosity` multiplies C each step. Add `self.C = min(self.C * (...), C_max)` if you want a stable simulation.
- **L=0.1 is hardcoded** — not computed from actual system state; just a background constant.
- **A=avg_R_e proxy** — adaptability set equal to resonance as a "simplified" version. The original §3.5 defines A differently.

---

## Fibonacci Therapy Scheduler

Runs correctly as a utility. The schedule itself is just cumulative Fibonacci day-offsets.

```python
def fibonacci_schedule(start_date, n_sessions):
    from datetime import timedelta
    fib = [1, 1]
    while len(fib) < n_sessions:
        fib.append(fib[-1] + fib[-2])
    schedule = [start_date]
    cumulative = 0
    for i in range(1, n_sessions):
        cumulative += fib[i]
        schedule.append(start_date + timedelta(days=cumulative))
    return schedule, fib
```

Whether the schedule produces better therapeutic outcomes is an empirical question (see [02-empirical-audit.md](../Negentropic/02-empirical-audit.md)).

---

*Back to: [Negentropic/README.md](../Negentropic/README.md)*
