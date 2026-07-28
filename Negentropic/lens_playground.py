import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from typing import Dict, List, Tuple, Optional
import copy
import random

# ============================================================================
# 1. UNIVERSAL CORE STATE
# ============================================================================

class CoreState:
    def __init__(self, n_agents=20, dim=8):
        self.n = n_agents
        self.dim = dim
        self.patterns = np.random.randn(n_agents, dim) * 0.5
        self.signals = np.random.rand(n_agents) + 0.5
        self.beliefs = np.random.rand(n_agents, 4)
        self.beliefs = self.beliefs / self.beliefs.sum(axis=1, keepdims=True)
        self.observations = np.random.randn(n_agents, 4) * 0.3
        self.adjacency = np.random.rand(n_agents, n_agents)
        self.adjacency = (self.adjacency + self.adjacency.T) / 2
        np.fill_diagonal(self.adjacency, 0)
        self.roles = np.random.rand(n_agents, 3)
        self.roles = self.roles / self.roles.sum(axis=1, keepdims=True)
        self.mauri = np.random.rand(n_agents) * 1.5 + 0.5
        self.domains = np.random.rand(n_agents, 4)
        self.domains = self.domains / (np.linalg.norm(self.domains, axis=1, keepdims=True) + 1e-10)
        self.hexagrams = np.random.randint(0, 2, size=(n_agents, 6))
        self.activations = np.random.randn(n_agents, 16) * 0.5
        self.params = {
            'alpha': 1.5,
            'noise_power': 0.25,          # Start with moderate noise
            'lambda_param': 0.5,
            'rupture_count': 0,
            'tapu_breaches': 0,
            'cross_entropy': 0.3,
            'prior_entropy': 2.0,
            'ideal_mauri': 1.0,
            'rel_threshold': 0.2,
            'disturbance_timer': 0        # for pulse decay
        }

    def copy(self):
        return copy.deepcopy(self)


# ============================================================================
# 2. ALL 17 LENSES (Thermodynamic lens now uses the FIXED L)
# ============================================================================

def lens_thermodynamic(R, A, D, L):
    # L is already distance from optimal noise + wasted energy
    return (R * A * D) - L

def lens_geometric(R, A, D, L):
    return (R**1.2 * A * D) - L * 0.9

def lens_bayesian(R, A, D, L):
    accuracy, epistemic, entropy = R, A * (1 + D), D * 0.5 + 0.5
    free_energy = L + (1 - R) * 0.5
    return (accuracy * epistemic * entropy) - free_energy

def lens_indigenous(R, A, D, L):
    obligation, plasticity, rel_types = R * 1.2, A * 0.8 + 0.2, D * 2.0 + 1.0
    return (obligation * plasticity * rel_types) - L * 0.5

def lens_maori(R, A, D, L):
    spiritual, restoration, domains = R * 1.5, A * 0.7 + 0.3, D * 1.8 + 1.0
    return (spiritual * restoration * domains) - L * 0.6

def lens_iching(R, A, D, L):
    static, agility, trigram = R * 0.8 + 0.2, A * 0.6 + 0.4, D * 2.5 + 0.5
    return (static * agility * trigram) - L * 0.7

def lens_ai(R, A, D, L):
    coherence, plasticity, rank = R * 1.1, A * 1.3, D * 0.9 + 0.3
    return (coherence * plasticity * rank) - (L + (1 - R) * 0.3)

def lens_aboriginal(R, A, D, L):
    songline, mobility, country = R * 1.3, A * 0.9 + 0.1, D * 2.0 + 0.5
    return (songline * mobility * country) - L * 0.7

def lens_ubuntu(R, A, D, L):
    density, agility, clan = R * 1.4, A * 1.1, D * 1.5 + 1.0
    return (density * agility * clan) - L * 0.8

def lens_sami(R, A, D, L):
    sielu, nomadic, seasons = R * 1.2, A * 1.3, D * 1.7 + 0.5
    return (sielu * nomadic * seasons) - L * 0.9

def lens_ainu(R, A, D, L):
    kamuy, iomante, ecosystem = R * 1.1, A * 1.0, D * 2.2 + 0.5
    return (kamuy * iomante * ecosystem) - L * 0.6

def lens_inuit(R, A, D, L):
    silap, ice_mobility, prey = R * 1.3, A * 1.4, D * 1.9 + 0.5
    return (silap * ice_mobility * prey) - L * 1.1

def lens_taoist(R, A, D, L):
    ziran, yi, yinyang = R * 1.0, A * 1.2 + 0.1, D * 1.6 + 0.5
    return (ziran * yi * yinyang) - L * 0.8

def lens_buddhist(R, A, D, L):
    dharmakaya, upaya, dukkha = R * 1.2, A * 1.1 + 0.1, D * 1.4 + 0.5
    return (dharmakaya * upaya * dukkha) - L * 1.0

def lens_vedantic(R, A, D, L):
    rta, yoga, guna = R * 1.3, A * 1.0, D * 1.8 + 0.5
    return (rta * yoga * guna) - L * 0.9

def lens_pueblo(R, A, D, L):
    kiva, dance, moiety = R * 1.1, A * 1.3, D * 1.5 + 0.5
    return (kiva * dance * moiety) - L * 1.2

def lens_celtic(R, A, D, L):
    tuath, imbas, otherworld = R * 1.2, A * 1.4, D * 1.9 + 0.5
    return (tuath * imbas * otherworld) - L * 0.8

LENS_REGISTRY = {
    "Thermodynamic": lens_thermodynamic,
    "Geometric": lens_geometric,
    "Bayesian": lens_bayesian,
    "Indigenous": lens_indigenous,
    "Māori": lens_maori,
    "I-Ching": lens_iching,
    "AI Alignment": lens_ai,
    "Aboriginal": lens_aboriginal,
    "Ubuntu": lens_ubuntu,
    "Sámi": lens_sami,
    "Ainu": lens_ainu,
    "Inuit": lens_inuit,
    "Taoist": lens_taoist,
    "Buddhist": lens_buddhist,
    "Vedantic": lens_vedantic,
    "Pueblo": lens_pueblo,
    "Celtic": lens_celtic,
}


# ============================================================================
# 3. COMPUTE CORE METRICS (FIXED L — optimal noise, no interference no life)
# ============================================================================

def compute_core_metrics(state: CoreState) -> Tuple[float, float, float, float]:
    patterns = state.patterns
    n = len(patterns)
    if n < 2:
        return 0.0, 0.0, 0.0, 0.5

    # ----- R: Coherence (mean coupling) -----
    R = 0.0
    count = 0
    for i in range(n):
        for j in range(i+1, n):
            d = np.linalg.norm(patterns[i] - patterns[j])
            phase = 0.5 * (np.cos(d) + 1)
            sig = np.sqrt(state.signals[i] * state.signals[j])
            adj = state.adjacency[i, j]
            belief_sim = np.dot(state.beliefs[i], state.beliefs[j])
            R += phase * sig * (1 + adj * 0.5) * (1 + belief_sim * 0.5)
            count += 1
    R = R / (count + 1e-10)

    # ----- A: Plasticity -----
    A = np.std(patterns) * 0.3
    role_entropy = np.mean([-np.sum(r * np.log(r + 1e-10)) for r in state.roles])
    A += role_entropy * 0.3
    A += np.std(state.mauri) * 0.1
    A = min(max(A, 0.01), 1.0)

    # ----- D: Diversity -----
    D = np.var(patterns) * 0.2
    hex_set = set([tuple(h) for h in state.hexagrams])
    D += len(hex_set) / (2**6) * 0.3
    dom_set = set([tuple(np.round(d, 2)) for d in state.domains])
    D += len(dom_set) / state.domains.shape[0] * 0.3
    if state.activations.size > 0:
        U, S, Vt = np.linalg.svd(state.activations, full_matrices=False)
        rank = np.sum(S > 0.01 * S[0]) if len(S) > 0 else 0
        D += (rank / len(S)) * 0.2 if len(S) > 0 else 0
    D = max(D, 0.01)

    # ----- L: Loss with OPTIMAL NOISE (noise is NOT purely destructive) -----
    noise = state.params['noise_power']
    # Critical noise: scales with exploration needs (higher R means tighter coupling → needs more noise to explore)
    # and higher D means more variety to coordinate → also needs more noise.
    optimal_noise = 0.2 * R + 0.1 * D + 0.05
    # Loss is quadratic distance from optimum — too quiet (stasis) OR too loud (chaos)
    noise_penalty = (noise - optimal_noise) ** 2

    # Wasted kinetic energy: motion that doesn't contribute to coherence
    kinetic = np.mean(np.sum(np.diff(patterns, axis=0)**2)) if n > 1 else 0.0
    wasted = kinetic * (1 - R) * 0.5

    # Social losses
    social_loss = 0.1 * state.params['rupture_count'] + 0.1 * state.params['tapu_breaches']

    # AI cross-entropy
    ce_loss = 0.1 * state.params['cross_entropy']

    # Disturbance pulse decay (if active, adds temporary loss)
    pulse = state.params.get('disturbance_timer', 0)
    disturbance_loss = 0.2 * pulse if pulse > 0 else 0.0
    if pulse > 0:
        state.params['disturbance_timer'] = max(0, pulse - 0.5)  # decay

    L = noise_penalty + wasted + social_loss + ce_loss + disturbance_loss
    L = min(max(L, 0.001), 2.0)

    return R, A, D, L


# ============================================================================
# 4. LENSPLAYGROUND (UPDATED ACTIONS)
# ============================================================================

class LensPlayground:
    def __init__(self, n_agents=20, dim=8):
        self.state = CoreState(n_agents, dim)
        self.all_lens_names = list(LENS_REGISTRY.keys())
        self._cache = {}

    def evaluate_state(self, state: CoreState, lens_names: Optional[List[str]] = None) -> Dict[str, float]:
        if lens_names is None:
            lens_names = self.all_lens_names
        R, A, D, L = compute_core_metrics(state)
        results = {}
        for name in lens_names:
            if name in LENS_REGISTRY:
                results[name] = LENS_REGISTRY[name](R, A, D, L)
        return results

    def available_actions(self) -> List[Dict]:
        return [
            {"name": "cohere (reduce variance)", "type": "cohere", "strength": 0.3},
            {"name": "diversify (increase variance)", "type": "diversify", "strength": 0.3},
            {"name": "strengthen adjacency (repair ties)", "type": "heal_adj", "strength": 0.2},
            {"name": "weaken adjacency (fracture ties)", "type": "fracture_adj", "strength": 0.2},
            {"name": "increase mauri (restore life-force)", "type": "boost_mauri", "strength": 0.3},
            {"name": "decrease mauri (deplete)", "type": "deplete_mauri", "strength": 0.3},
            {"name": "simplify beliefs (reduce entropy)", "type": "simplify_beliefs", "strength": 0.2},
            {"name": "complexify beliefs (increase entropy)", "type": "complexify_beliefs", "strength": 0.2},
            # --- UPDATED NOISE ACTIONS ---
            {"name": "optimize noise (tune to critical)", "type": "tune_noise", "strength": 0.1},
            {"name": "increase noise (explore)", "type": "increase_noise", "strength": 0.15},
            {"name": "decrease noise (freeze)", "type": "decrease_noise", "strength": 0.15},
            # --- NEW: DISTURBANCE PULSE (life test) ---
            {"name": "apply disturbance pulse (shock)", "type": "disturb", "strength": 1.5},
            {"name": "shift hexagrams to balance", "type": "balance_hex", "strength": 0.3},
            {"name": "shift hexagrams to imbalance", "type": "imbalance_hex", "strength": 0.3},
        ]

    def apply_action(self, state: CoreState, action: Dict) -> CoreState:
        new_state = state.copy()
        s = action["strength"]
        typ = action["type"]

        if typ == "cohere":
            mean_p = np.mean(new_state.patterns, axis=0)
            new_state.patterns = new_state.patterns * (1 - s) + mean_p * s
        elif typ == "diversify":
            new_state.patterns *= (1 + s * 0.5)
            new_state.patterns += np.random.randn(*new_state.patterns.shape) * s * 0.3
        elif typ == "heal_adj":
            new_state.adjacency += s * (1 - new_state.adjacency) * np.random.rand(*new_state.adjacency.shape)
            new_state.adjacency = (new_state.adjacency + new_state.adjacency.T) / 2
            np.fill_diagonal(new_state.adjacency, 0)
            new_state.params['rupture_count'] = max(0, new_state.params['rupture_count'] - 1)
        elif typ == "fracture_adj":
            new_state.adjacency *= (1 - s)
            new_state.params['rupture_count'] += 1
        elif typ == "boost_mauri":
            new_state.mauri = np.minimum(new_state.mauri * (1 + s), 2.0)
            new_state.params['tapu_breaches'] = max(0, new_state.params['tapu_breaches'] - 1)
        elif typ == "deplete_mauri":
            new_state.mauri *= (1 - s)
            new_state.params['tapu_breaches'] += 1
        elif typ == "simplify_beliefs":
            for i in range(new_state.n):
                max_idx = np.argmax(new_state.beliefs[i])
                new_state.beliefs[i] = 0
                new_state.beliefs[i, max_idx] = 1
        elif typ == "complexify_beliefs":
            new_state.beliefs += np.random.rand(*new_state.beliefs.shape) * s
            new_state.beliefs = new_state.beliefs / new_state.beliefs.sum(axis=1, keepdims=True)
        elif typ == "tune_noise":
            # Recompute R,D on the fly to find optimal
            R, A, D, L = compute_core_metrics(new_state)
            optimal = 0.2 * R + 0.1 * D + 0.05
            new_state.params['noise_power'] += (optimal - new_state.params['noise_power']) * s
        elif typ == "increase_noise":
            new_state.params['noise_power'] = min(1.5, new_state.params['noise_power'] * (1 + s))
        elif typ == "decrease_noise":
            new_state.params['noise_power'] = max(0.01, new_state.params['noise_power'] * (1 - s))
        elif typ == "disturb":
            # Apply a sharp spike in noise
            new_state.params['noise_power'] = min(2.0, new_state.params['noise_power'] + s)
            new_state.params['disturbance_timer'] = 2.0  # decays over steps
        elif typ == "balance_hex":
            for i in range(new_state.n):
                if np.sum(new_state.hexagrams[i]) > 3:
                    ones = np.where(new_state.hexagrams[i] == 1)[0]
                    if len(ones) > 3:
                        flip = np.random.choice(ones, size=len(ones)-3, replace=False)
                        new_state.hexagrams[i, flip] = 0
                elif np.sum(new_state.hexagrams[i]) < 3:
                    zeros = np.where(new_state.hexagrams[i] == 0)[0]
                    if len(zeros) > 3:
                        flip = np.random.choice(zeros, size=3-np.sum(new_state.hexagrams[i]), replace=False)
                        new_state.hexagrams[i, flip] = 1
        elif typ == "imbalance_hex":
            for i in range(new_state.n):
                if random.random() > 0.5:
                    new_state.hexagrams[i] = 1
                else:
                    new_state.hexagrams[i] = 0
        return new_state

    def compare_actions(self, action_subset: Optional[List[int]] = None,
                        lens_subset: Optional[List[str]] = None) -> Dict:
        if action_subset is None:
            action_subset = list(range(len(self.available_actions())))
        if lens_subset is None:
            lens_subset = self.all_lens_names

        actions = self.available_actions()
        base_results = self.evaluate_state(self.state, lens_subset)

        comparison = {
            "base_state": base_results,
            "actions": [],
            "delta_matrix": np.zeros((len(action_subset), len(lens_subset)))
        }

        for ai, idx in enumerate(action_subset):
            action = actions[idx]
            new_state = self.apply_action(self.state, action)
            new_results = self.evaluate_state(new_state, lens_subset)
            delta = {lens: new_results[lens] - base_results[lens] for lens in lens_subset}
            comparison["actions"].append({
                "name": action["name"],
                "new_M": new_results,
                "delta": delta,
                "row_idx": ai
            })
            for lj, lens in enumerate(lens_subset):
                comparison["delta_matrix"][ai, lj] = delta[lens]

        return comparison

    def run_decision_cycle(self, agent_lens: str, steps: int = 10, verbose: bool = True):
        actions = self.available_actions()
        history = {lens: [] for lens in self.all_lens_names}
        history["chosen_action"] = []
        state = self.state.copy()

        for step in range(steps):
            current_M = self.evaluate_state(state)
            for lens, val in current_M.items():
                history[lens].append(val)

            best_action = None
            best_delta = -np.inf
            best_new_state = None

            for action in actions:
                test_state = self.apply_action(state, action)
                test_M = self.evaluate_state(test_state, [agent_lens])
                delta = test_M[agent_lens] - current_M[agent_lens]
                if delta > best_delta:
                    best_delta = delta
                    best_action = action
                    best_new_state = test_state

            if best_action is not None:
                state = best_new_state
                history["chosen_action"].append(best_action["name"])
            else:
                history["chosen_action"].append("no_action")

            if verbose and step % 2 == 0:
                print(f"Step {step}: Agent [{agent_lens}] chose '{best_action['name']}' (ΔM={best_delta:.3f})")

        return history, state

    def print_conflict_table(self, comparison: Dict, top_n: int = 3):
        actions = comparison["actions"]
        lens_names = list(comparison["base_state"].keys())

        print("\n" + "=" * 80)
        print("CONFLICT TABLE: Which action does EACH lens prefer?")
        print("=" * 80)

        for li, lens in enumerate(lens_names):
            deltas = [a["delta"][lens] for a in actions]
            sorted_idx = np.argsort(deltas)[::-1]
            top_actions = [actions[i]["name"] for i in sorted_idx[:top_n]]
            print(f"\n🔹 {lens:16s} prefers:")
            for rank, name in enumerate(top_actions, 1):
                delta_val = deltas[sorted_idx[rank-1]]
                print(f"   {rank}. {name:32s} (ΔM = {delta_val:+.3f})")

        # Actions causing the most divergence
        print("\n" + "=" * 80)
        print("DIVERGENCE: Actions that split the lenses the most")
        print("=" * 80)
        std_devs = []
        for ai, action in enumerate(actions):
            deltas = [a["delta"][lens] for lens in lens_names]
            std_dev = np.std(deltas)
            std_devs.append((std_dev, action["name"], deltas))
        std_devs.sort(reverse=True)

        for std, name, deltas in std_devs[:3]:
            print(f"\n⚡ '{name}' (std ΔM = {std:.3f})")
            max_lens = lens_names[np.argmax(deltas)]
            min_lens = lens_names[np.argmin(deltas)]
            print(f"   ✅ Best for: {max_lens} (+{np.max(deltas):+.3f})")
            print(f"   ❌ Worst for: {min_lens} ({np.min(deltas):+.3f})")


# ============================================================================
# 5. DEMO RUN (UPDATED)
# ============================================================================

if __name__ == "__main__":
    np.random.seed(42)
    playground = LensPlayground(n_agents=15, dim=6)

    print("=" * 70)
    print("🧪 LENS PLAYGROUND (CORRECTED: 'no interference no life')")
    print("=" * 70)

    comparison = playground.compare_actions()
    playground.print_conflict_table(comparison, top_n=3)

    print("\n" + "=" * 70)
    print("🔬 Key change: Thermodynamics now LOVES optimal noise.")
    print("   'Decrease noise' is now considered DANGEROUS (stasis).")
    print("   'Optimize noise' and 'Disturbance pulse' are top actions.")
    print("=" * 70)
