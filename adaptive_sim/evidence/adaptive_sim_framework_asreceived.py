"""
Adaptive Simulation Framework for Scientific Claim Testing
==========================================================
A self-contained framework for running simulations, testing claims,
logging provenance, and allowing an AI agent to modify experiments
based on results.

Supports:
  - Forest metabolic scaling model (spatially explicit)
  - Fluctuating population dynamics (multi-state switching Moran process)
  - Extensible to other models

Usage:
  python adaptive_sim_framework.py --model forest --iterations 5
  python adaptive_sim_framework.py --model fluctuating --iterations 5
"""

import numpy as np
import json
import hashlib
import time
import copy
import argparse
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Callable, Optional, Tuple, Any
from collections import defaultdict

# =============================================================================
# PROVENANCE & LOGGING
# =============================================================================

@dataclass
class ReasoningStep:
    """A single step in the chain of reasoning."""
    step_id: str
    timestamp: float
    agent_name: str
    observation: str
    hypothesis: str
    action: str
    parameters_changed: Dict[str, Any]
    expected_outcome: str
    parent_step_id: Optional[str] = None

@dataclass
class SimulationRecord:
    """Record of a single simulation run."""
    run_id: str
    model_name: str
    parameters: Dict[str, Any]
    random_seed: int
    timestamp: float
    duration_seconds: float
    outcomes: Dict[str, Any]
    claim_results: Dict[str, str]
    reasoning_chain: List[ReasoningStep]

    def to_dict(self):
        return asdict(self)

class ProvenanceLogger:
    """Logs all simulation runs, reasoning, and claim tests with full provenance."""

    def __init__(self, log_file: str = "provenance_log.jsonl"):
        self.log_file = log_file
        self.records: List[SimulationRecord] = []
        self.claim_history: Dict[str, List[Dict]] = defaultdict(list)

    def log_run(self, record: SimulationRecord):
        self.records.append(record)
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(record.to_dict(), default=str) + '\n')

    def log_claim_result(self, claim_id: str, result: Dict):
        self.claim_history[claim_id].append(result)

    def get_run_by_id(self, run_id: str) -> Optional[SimulationRecord]:
        for r in self.records:
            if r.run_id == run_id:
                return r
        return None

    def get_chain_for_claim(self, claim_id: str) -> List[SimulationRecord]:
        return [r for r in self.records if claim_id in r.claim_results]

    def summary(self) -> Dict:
        return {
            'total_runs': len(self.records),
            'claims_tested': list(self.claim_history.keys()),
            'models_used': list(set(r.model_name for r in self.records))
        }

# =============================================================================
# CLAIM SYSTEM
# =============================================================================

@dataclass
class Claim:
    """A falsifiable claim about model behavior."""
    claim_id: str
    description: str
    model_type: str
    test_function: Callable[[Dict[str, Any]], Tuple[bool, str, Dict]]
    priority: int = 1
    max_retries: int = 3
    status: str = "untested"
    evidence: List[Dict] = field(default_factory=list)

    def test(self, outcomes: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        try:
            passed, message, details = self.test_function(outcomes)
            self.evidence.append({
                'passed': passed,
                'message': message,
                'details': details,
                'timestamp': time.time()
            })
            if passed:
                self.status = "passed"
            else:
                self.status = "failed"
            return passed, message, details
        except Exception as e:
            self.status = "inconclusive"
            return False, f"Test error: {str(e)}", {}

# =============================================================================
# ADAPTIVE AGENT
# =============================================================================

class AdaptiveAgent:
    """
    An agent that analyzes simulation results, proposes parameter modifications,
    generates new claims, and logs its reasoning chain.
    """

    def __init__(self, name: str = "AdaptiveAgent", exploration_rate: float = 0.3):
        self.name = name
        self.exploration_rate = exploration_rate
        self.reasoning_chain: List[ReasoningStep] = []
        self.step_counter = 0

    def _new_step_id(self) -> str:
        self.step_counter += 1
        return f"{self.name}_step_{self.step_counter}_{int(time.time()*1000)}"

    def analyze(self, outcomes, failed_claims, current_params, model_type):
        observation = self._generate_observation(outcomes, failed_claims, model_type)
        hypothesis = self._generate_hypothesis(outcomes, failed_claims, model_type)
        new_params, action_desc = self._propose_action(current_params, hypothesis, model_type, outcomes)
        new_claims = self._generate_claims(outcomes, model_type, new_params)

        step = ReasoningStep(
            step_id=self._new_step_id(),
            timestamp=time.time(),
            agent_name=self.name,
            observation=observation,
            hypothesis=hypothesis,
            action=action_desc,
            parameters_changed=self._param_diff(current_params, new_params),
            expected_outcome="Retest with modified parameters to verify hypothesis"
        )
        self.reasoning_chain.append(step)
        return new_params, new_claims, step

    def _generate_observation(self, outcomes, failed_claims, model_type):
        obs_parts = []
        if model_type == 'forest':
            if 'size_distribution' in outcomes:
                sd = outcomes['size_distribution']
                obs_parts.append(f"Size distribution slope: {sd.get('slope', 'N/A'):.3f}")
                obs_parts.append(f"R² of power-law fit: {sd.get('r_squared', 'N/A'):.3f}")
            if 'species_richness' in outcomes:
                obs_parts.append(f"Species richness: {outcomes['species_richness']}")
        elif model_type == 'fluctuating':
            if 'fixation_probability' in outcomes:
                fp = outcomes['fixation_probability']
                obs_parts.append(f"Fixation prob (slow strain): {fp.get('slow_strain', 'N/A'):.4f}")
            if 'mean_fixation_time' in outcomes:
                obs_parts.append(f"Mean fixation time: {outcomes['mean_fixation_time']:.2f}")
        if failed_claims:
            obs_parts.append(f"Failed claims: {[c.claim_id for c in failed_claims]}")
        return " | ".join(obs_parts) if obs_parts else "No significant observations."

    def _generate_hypothesis(self, outcomes, failed_claims, model_type):
        if not failed_claims:
            if model_type == 'forest':
                return "Exploring parameter space: testing sensitivity to competition strength and dispersal range."
            else:
                return "Exploring parameter space: testing sensitivity to switching rates and carrying capacity distribution."
        hypotheses = []
        for claim in failed_claims:
            if claim.claim_id == "forest_power_law":
                if outcomes.get('size_distribution', {}).get('r_squared', 0) < 0.8:
                    hypotheses.append("Power-law fit poor; hypothesis: competition too weak or simulation not at steady state.")
                else:
                    hypotheses.append("Power-law slope outside predicted range; hypothesis: seed injection rate or metabolic exponent needs adjustment.")
            elif claim.claim_id == "fluctuating_fixation":
                hypotheses.append("Fixation probability deviates from theory; hypothesis: switching too fast relative to demographic rates, or population size too large for drift.")
            elif claim.claim_id == "fluctuating_slow_persistence":
                hypotheses.append("Slow strain fixation too low; hypothesis: growth rate ratio too unfavorable or switching too fast.")
        return " ".join(hypotheses) if hypotheses else "Investigating unexpected behavior."

    def _propose_action(self, params, hypothesis, model_type, outcomes):
        new_params = copy.deepcopy(params)
        actions = []
        if model_type == 'forest':
            if "competition too weak" in hypothesis:
                new_params['competition_strength'] = min(params.get('competition_strength', 1.0) * 1.5, 5.0)
                actions.append(f"Increased competition_strength to {new_params['competition_strength']:.3f}")
            elif "not at steady state" in hypothesis:
                new_params['num_steps'] = int(params.get('num_steps', 1000) * 1.5)
                actions.append(f"Increased num_steps to {new_params['num_steps']}")
            elif "seed injection" in hypothesis:
                new_params['seed_rate'] = params.get('seed_rate', 0.1) * 1.5
                actions.append(f"Increased seed_rate to {new_params['seed_rate']:.3f}")
            else:
                if np.random.rand() < 0.5:
                    new_params['metabolic_exponent'] = np.clip(params.get('metabolic_exponent', 0.75) + np.random.normal(0, 0.05), 0.5, 1.0)
                    actions.append(f"Perturbed metabolic_exponent to {new_params['metabolic_exponent']:.3f}")
                else:
                    new_params['dispersal_range'] = max(1, params.get('dispersal_range', 5) + np.random.randint(-2, 3))
                    actions.append(f"Perturbed dispersal_range to {new_params['dispersal_range']}")
        elif model_type == 'fluctuating':
            if "switching too fast" in hypothesis:
                new_params['switching_rate'] = params.get('switching_rate', 0.1) * 0.7
                actions.append(f"Decreased switching_rate to {new_params['switching_rate']:.4f}")
            elif "growth rate ratio" in hypothesis:
                new_params['growth_rate_ratio'] = min(0.99, params.get('growth_rate_ratio', 0.95) + 0.02)
                actions.append(f"Increased growth_rate_ratio to {new_params['growth_rate_ratio']:.3f}")
            elif "population size too large" in hypothesis:
                new_params['carrying_capacities'] = [max(10, int(k * 0.8)) for k in params.get('carrying_capacities', [100])]
                actions.append(f"Decreased carrying capacities to {new_params['carrying_capacities']}")
            else:
                if np.random.rand() < 0.5:
                    new_params['switching_rate'] = params.get('switching_rate', 0.1) * 1.3
                    actions.append(f"Perturbed switching_rate to {new_params['switching_rate']:.4f}")
                else:
                    new_params['num_replicates'] = params.get('num_replicates', 50) + 20
                    actions.append(f"Increased num_replicates to {new_params['num_replicates']}")
        action_str = "; ".join(actions) if actions else "No parameter changes (exploration complete)."
        return new_params, action_str

    def _generate_claims(self, outcomes, model_type, params):
        new_claims = []
        if model_type == 'forest':
            if outcomes.get('size_distribution', {}).get('r_squared', 0) > 0.85:
                new_claims.append(Claim(
                    claim_id=f"forest_slope_seedrate_{int(time.time())}",
                    description="Power-law slope is negatively correlated with seed injection rate",
                    model_type='forest',
                    test_function=lambda o: ('size_distribution' in o and o['size_distribution'].get('slope', 0) < -1.5, "Slope check", {'slope': o.get('size_distribution', {}).get('slope')}),
                    priority=2
                ))
        elif model_type == 'fluctuating':
            if outcomes.get('fixation_probability', {}).get('slow_strain', 0) > 0.3:
                new_claims.append(Claim(
                    claim_id=f"fluct_slow_persistence_{int(time.time())}",
                    description="Slow strain can persist when switching rate is comparable to growth rate",
                    model_type='fluctuating',
                    test_function=lambda o: (o.get('fixation_probability', {}).get('slow_strain', 0) > 0.2, "Slow strain persistence check", {'fp_slow': o.get('fixation_probability', {}).get('slow_strain')}),
                    priority=2
                ))
        return new_claims

    def _param_diff(self, old, new):
        diff = {}
        for k in set(old.keys()) | set(new.keys()):
            if old.get(k) != new.get(k):
                diff[k] = (old.get(k), new.get(k))
        return diff

# =============================================================================
# FOREST METABOLIC SCALING MODEL
# =============================================================================

class ForestScalingSim:
    """
    Spatially explicit forest model with metabolic scaling.
    Trees occupy cells on a 2D grid. Growth follows metabolic scaling.
    Competition is local (light shading by neighbors).
    Seeds disperse probabilistically.
    """

    def __init__(self, params):
        self.params = params
        self.grid_size = params.get('grid_size', 100)
        self.metabolic_exponent = params.get('metabolic_exponent', 0.75)
        self.competition_strength = params.get('competition_strength', 1.0)
        self.dispersal_range = params.get('dispersal_range', 5)
        self.seed_rate = params.get('seed_rate', 0.1)
        self.mortality_base = params.get('mortality_base', 0.01)
        self.num_steps = params.get('num_steps', 1000)
        self.initial_density = params.get('initial_density', 0.1)
        self.min_size = params.get('min_size', 1.0)
        self.num_species = params.get('num_species', 3)
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.float64)
        self.species_grid = np.zeros((self.grid_size, self.grid_size), dtype=np.int32)
        self._initialize()

    def _initialize(self):
        n_trees = int(self.grid_size**2 * self.initial_density)
        indices = np.random.choice(self.grid_size**2, n_trees, replace=False)
        rows, cols = np.unravel_index(indices, (self.grid_size, self.grid_size))
        self.grid[rows, cols] = np.random.lognormal(2, 1, n_trees)
        self.species_grid[rows, cols] = np.random.randint(1, self.num_species + 1, n_trees)

    def _local_competition(self, i, j):
        r = self.dispersal_range // 2
        i0, i1 = max(0, i-r), min(self.grid_size, i+r+1)
        j0, j1 = max(0, j-r), min(self.grid_size, j+r+1)
        neighborhood = self.grid[i0:i1, j0:j1]
        total_comp = np.sum(neighborhood) - self.grid[i, j]
        return total_comp * self.competition_strength

    def step(self):
        new_grid = self.grid.copy()
        new_species = self.species_grid.copy()
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i, j] > 0:
                    comp = self._local_competition(i, j)
                    growth = self.grid[i, j] ** self.metabolic_exponent * 0.1
                    growth = max(0, growth - comp * 0.001)
                    new_grid[i, j] += growth
                    stress = comp / (self.grid[i, j] + 1)
                    mort_prob = self.mortality_base + stress * 0.001
                    if np.random.rand() < mort_prob:
                        new_grid[i, j] = 0
                        new_species[i, j] = 0
        n_seeds = int(np.sum(self.grid > 0) * self.seed_rate)
        for _ in range(n_seeds):
            parents = np.argwhere(self.grid > 0)
            if len(parents) == 0:
                break
            pi, pj = parents[np.random.randint(len(parents))]
            parent_species = self.species_grid[pi, pj]
            di = np.random.randint(-self.dispersal_range, self.dispersal_range + 1)
            dj = np.random.randint(-self.dispersal_range, self.dispersal_range + 1)
            ni, nj = pi + di, pj + dj
            if 0 <= ni < self.grid_size and 0 <= nj < self.grid_size:
                if new_grid[ni, nj] == 0:
                    local_light = 1.0 - min(1.0, self._local_competition(ni, nj) * 0.0001)
                    if np.random.rand() < local_light:
                        new_grid[ni, nj] = self.min_size * (1 + np.random.exponential(0.5))
                        new_species[ni, nj] = parent_species
        self.grid = new_grid
        self.species_grid = new_species

    def run(self):
        for _ in range(self.num_steps):
            self.step()
        return self.analyze()

    def analyze(self):
        sizes = self.grid[self.grid > 0]
        outcomes = {
            'num_trees': len(sizes),
            'mean_size': float(np.mean(sizes)) if len(sizes) > 0 else 0,
            'max_size': float(np.max(sizes)) if len(sizes) > 0 else 0,
            'species_richness': len(np.unique(self.species_grid[self.species_grid > 0])),
        }
        if len(sizes) > 100:
            log_bins = np.logspace(np.log10(max(self.min_size, sizes.min())), 
                                   np.log10(sizes.max()), 30)
            hist, edges = np.histogram(sizes, bins=log_bins)
            centers = np.sqrt(edges[:-1] * edges[1:])
            mask = hist > 0
            if np.sum(mask) > 5:
                log_c = np.log(centers[mask])
                log_h = np.log(hist[mask])
                coeffs = np.polyfit(log_c, log_h, 1)
                slope = coeffs[0]
                pred = np.polyval(coeffs, log_c)
                ss_res = np.sum((log_h - pred)**2)
                ss_tot = np.sum((log_h - np.mean(log_h))**2)
                r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                outcomes['size_distribution'] = {
                    'slope': float(slope),
                    'r_squared': float(r_squared),
                }
        return outcomes

# =============================================================================
# FLUCTUATING POPULATION MODEL (MORAN PROCESS)
# =============================================================================

class FluctuatingPopSim:
    """
    Multi-state switching environment with Moran process.
    Fixed population size N (carrying capacity of current environment state).
    Two strains compete. One individual dies, one reproduces each step.
    """

    def __init__(self, params):
        self.params = params
        self.num_states = params.get('num_states', 5)
        self.carrying_capacities = params.get('carrying_capacities', [50, 100, 200, 300, 400])
        self.switching_rate = params.get('switching_rate', 0.1)
        self.growth_rate_fast = params.get('growth_rate_fast', 1.0)
        self.growth_rate_ratio = params.get('growth_rate_ratio', 0.95)
        self.growth_rate_slow = self.growth_rate_fast * self.growth_rate_ratio
        self.initial_population = params.get('initial_population', 100)
        self.num_steps = params.get('num_steps', 100000)
        self.num_replicates = params.get('num_replicates', 100)
        while len(self.carrying_capacities) < self.num_states:
            self.carrying_capacities.append(self.carrying_capacities[-1] * 1.2)
        self.carrying_capacities = self.carrying_capacities[:self.num_states]

    def _make_transition_matrix(self):
        Q = np.zeros((self.num_states, self.num_states))
        for i in range(self.num_states):
            if i > 0:
                Q[i, i-1] = self.switching_rate * 0.5
            if i < self.num_states - 1:
                Q[i, i+1] = self.switching_rate * 0.5
            Q[i, i] = -np.sum(Q[i, :])
        return Q

    def _run_replicate(self, seed):
        np.random.seed(seed)
        env_state = self.num_states // 2
        N = self.carrying_capacities[env_state]
        n_fast = N // 2
        n_slow = N - n_fast
        Q = self._make_transition_matrix()
        t = 0
        max_steps = self.num_steps

        for step in range(max_steps):
            env_rates = -Q[env_state, env_state]
            if env_rates > 0:
                if np.random.rand() < env_rates:
                    probs = Q[env_state, :] / env_rates
                    probs[env_state] = 0
                    probs = np.maximum(probs, 0)
                    if np.sum(probs) > 0:
                        probs = probs / np.sum(probs)
                        env_state = np.random.choice(self.num_states, p=probs)
                        N = self.carrying_capacities[env_state]
                        total = n_fast + n_slow
                        if total > N:
                            excess = total - N
                            for _ in range(excess):
                                if np.random.rand() < n_fast / total:
                                    n_fast = max(0, n_fast - 1)
                                else:
                                    n_slow = max(0, n_slow - 1)
                                total = n_fast + n_slow
                        elif total < N:
                            deficit = N - total
                            for _ in range(deficit):
                                if np.random.rand() < n_fast / max(1, total):
                                    n_fast += 1
                                else:
                                    n_slow += 1
                                total = n_fast + n_slow

            total = n_fast + n_slow
            if total == 0:
                break

            w_fast = self.growth_rate_fast
            w_slow = self.growth_rate_slow

            if np.random.rand() < n_fast / total:
                n_fast = max(0, n_fast - 1)
            else:
                n_slow = max(0, n_slow - 1)

            total_w = n_fast * w_fast + n_slow * w_slow
            if total_w > 0:
                if np.random.rand() < (n_fast * w_fast) / total_w:
                    n_fast += 1
                else:
                    n_slow += 1

            t += 1
            if n_fast == 0 or n_slow == 0:
                break

        return {
            'n_fast_final': n_fast, 'n_slow_final': n_slow, 'fixation_time': t,
            'fast_fixes': n_fast > 0 and n_slow == 0,
            'slow_fixes': n_slow > 0 and n_fast == 0,
            'coexistence': n_fast > 0 and n_slow > 0,
        }

    def run(self):
        results = []
        for rep in range(self.num_replicates):
            res = self._run_replicate(seed=rep + self.params.get('base_seed', 42))
            results.append(res)
        fast_fixes = sum(r['fast_fixes'] for r in results)
        slow_fixes = sum(r['slow_fixes'] for r in results)
        coex = sum(r['coexistence'] for r in results)
        total = len(results)
        fix_times = [r['fixation_time'] for r in results if not r['coexistence']]
        return {
            'num_replicates': total,
            'fixation_probability': {
                'fast_strain': fast_fixes / total if total > 0 else 0,
                'slow_strain': slow_fixes / total if total > 0 else 0,
                'coexistence': coex / total if total > 0 else 0
            },
            'mean_fixation_time': float(np.mean(fix_times)) if fix_times else 0,
            'std_fixation_time': float(np.std(fix_times)) if fix_times else 0,
        }

# =============================================================================
# SIMULATION RUNNER
# =============================================================================

class SimulationRunner:
    def __init__(self, model_type, logger, agent):
        self.model_type = model_type
        self.logger = logger
        self.agent = agent
        self.claims = []

    def register_claim(self, claim):
        self.claims.append(claim)

    def run_adaptive_loop(self, initial_params, max_iterations=5, random_seed=42):
        np.random.seed(random_seed)
        current_params = copy.deepcopy(initial_params)
        current_params['base_seed'] = random_seed
        iteration_results = []

        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"ITERATION {iteration + 1}/{max_iterations} | Model: {self.model_type}")
            print(f"{'='*60}")

            run_id = hashlib.sha256(f"{self.model_type}_{iteration}_{time.time()}".encode()).hexdigest()[:12]
            t0 = time.time()

            if self.model_type == 'forest':
                sim = ForestScalingSim(current_params)
                outcomes = sim.run()
            elif self.model_type == 'fluctuating':
                sim = FluctuatingPopSim(current_params)
                outcomes = sim.run()
            else:
                raise ValueError(f"Unknown model type: {self.model_type}")

            duration = time.time() - t0

            claim_results = {}
            failed_claims = []
            for claim in sorted(self.claims, key=lambda c: -c.priority):
                if claim.model_type == self.model_type:
                    passed, msg, details = claim.test(outcomes)
                    claim_results[claim.claim_id] = {'status': 'passed' if passed else 'failed', 'message': msg, 'details': details}
                    if not passed:
                        failed_claims.append(claim)
                    print(f"  Claim [{claim.claim_id}]: {'PASS' if passed else 'FAIL'} - {msg}")

            record = SimulationRecord(
                run_id=run_id, model_name=self.model_type,
                parameters=copy.deepcopy(current_params),
                random_seed=random_seed + iteration,
                timestamp=time.time(), duration_seconds=duration,
                outcomes=outcomes,
                claim_results={k: v['status'] for k, v in claim_results.items()},
                reasoning_chain=[]
            )

            if failed_claims and iteration < max_iterations - 1:
                new_params, new_claims, reasoning_step = self.agent.analyze(
                    outcomes, failed_claims, current_params, self.model_type
                )
                record.reasoning_chain = [reasoning_step]
                current_params = new_params
                for nc in new_claims:
                    self.register_claim(nc)
                    print(f"  New claim generated: {nc.claim_id}")
            else:
                if not failed_claims:
                    print(f"  All claims passed! Stopping early.")
                reasoning_step = ReasoningStep(
                    step_id=f"final_{iteration}", timestamp=time.time(),
                    agent_name=self.agent.name,
                    observation="Final iteration or all claims passed.",
                    hypothesis="N/A", action="Terminate loop",
                    parameters_changed={}, expected_outcome="N/A"
                )
                record.reasoning_chain = [reasoning_step]

            self.logger.log_run(record)
            iteration_results.append({
                'iteration': iteration, 'run_id': run_id,
                'params': copy.deepcopy(current_params),
                'outcomes': outcomes,
                'claim_results': claim_results,
                'failed_claims': [c.claim_id for c in failed_claims]
            })

            if not failed_claims:
                break

        return {
            'model_type': self.model_type,
            'total_iterations': len(iteration_results),
            'final_params': current_params,
            'iteration_results': iteration_results,
            'logger_summary': self.logger.summary()
        }

# =============================================================================
# DEFAULT CLAIMS
# =============================================================================

def get_forest_claims():
    return [
        Claim(
            claim_id="forest_power_law",
            description="Tree-size distribution follows a power law with R² > 0.6",
            model_type="forest",
            test_function=lambda o: (
                'size_distribution' in o and o['size_distribution'].get('r_squared', 0) > 0.6,
                f"R² = {o.get('size_distribution', {}).get('r_squared', 'N/A'):.3f}",
                o.get('size_distribution', {})
            )
        ),
        Claim(
            claim_id="forest_species_coexistence",
            description="Multiple species persist (richness > 1)",
            model_type="forest",
            test_function=lambda o: (
                o.get('species_richness', 0) > 1,
                f"Richness = {o.get('species_richness', 'N/A')}",
                {'richness': o.get('species_richness')}
            )
        )
    ]

def get_fluctuating_claims():
    return [
        Claim(
            claim_id="fluctuating_fixation",
            description="Fixation occurs in >50% of replicates (populations don't coexist indefinitely)",
            model_type="fluctuating",
            test_function=lambda o: (
                o.get('fixation_probability', {}).get('coexistence', 1.0) < 0.5,
                f"Coexistence prob = {o.get('fixation_probability', {}).get('coexistence', 'N/A'):.3f}",
                o.get('fixation_probability', {})
            )
        ),
        Claim(
            claim_id="fluctuating_slow_persistence",
            description="Slow strain has non-zero fixation probability (>5%)",
            model_type="fluctuating",
            test_function=lambda o: (
                o.get('fixation_probability', {}).get('slow_strain', 0) > 0.05,
                f"Slow strain fixation = {o.get('fixation_probability', {}).get('slow_strain', 'N/A'):.4f}",
                o.get('fixation_probability', {})
            )
        )
    ]

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Adaptive Simulation Framework")
    parser.add_argument('--model', choices=['forest', 'fluctuating'], required=True)
    parser.add_argument('--iterations', type=int, default=5)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--log', type=str, default='provenance_log.jsonl')
    args = parser.parse_args()

    logger = ProvenanceLogger(log_file=args.log)
    agent = AdaptiveAgent(name="AutoAgent", exploration_rate=0.3)
    runner = SimulationRunner(args.model, logger, agent)

    if args.model == 'forest':
        initial_params = {
            'grid_size': 60,
            'metabolic_exponent': 0.75,
            'competition_strength': 0.8,
            'dispersal_range': 4,
            'seed_rate': 0.15,
            'mortality_base': 0.01,
            'num_steps': 500,
            'initial_density': 0.15,
            'num_species': 3,
            'min_size': 1.0
        }
        for claim in get_forest_claims():
            runner.register_claim(claim)
    elif args.model == 'fluctuating':
        initial_params = {
            'num_states': 5,
            'carrying_capacities': [50, 100, 200, 300, 400],
            'switching_rate': 0.1,
            'growth_rate_fast': 1.0,
            'growth_rate_ratio': 0.95,
            'initial_population': 100,
            'num_steps': 100000,
            'num_replicates': 50
        }
        for claim in get_fluctuating_claims():
            runner.register_claim(claim)

    result = runner.run_adaptive_loop(
        initial_params=initial_params,
        max_iterations=args.iterations,
        random_seed=args.seed
    )

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Model: {result['model_type']}")
    print(f"Total iterations: {result['total_iterations']}")
    print(f"Final parameters: {json.dumps(result['final_params'], indent=2)}")
    print(f"\nProvenance log saved to: {args.log}")
    print(f"Logger summary: {result['logger_summary']}")

if __name__ == "__main__":
    main()
