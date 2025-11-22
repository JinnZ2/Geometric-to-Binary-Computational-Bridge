#!/usr/bin/env python3
“””
phi_enhancement_statistical_test.py

Statistical Framework for Testing Phi-Enhancement Hypothesis

This module provides rigorous statistical tests to determine whether
energy transfer rates show enhancement at phi-ratio distances.

Primary Test: LHC-II pigment pair analysis
Methods: t-test, permutation test, correlation, bootstrap CI

MIT License
“””

import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, NamedTuple

# =============================================================================

# CONSTANTS

# =============================================================================

PHI = (np.sqrt(5) - 1) / 2  # ≈ 0.618034
PHI_POWERS = [PHI**n for n in range(1, 8)]
R0_CHLOROPHYLL = 2.5e-9  # Förster radius for Chl-Chl (m)

# =============================================================================

# DATA STRUCTURES

# =============================================================================

class PigmentPair(NamedTuple):
pair_id: str
distance: float
distance_normalized: float
transfer_rate: float
transfer_efficiency: float
is_phi_distance: bool
closest_phi_power: float
phi_deviation: float

class StatisticalResult(NamedTuple):
test_name: str
n_phi_pairs: int
n_control_pairs: int
phi_mean: float
control_mean: float
effect_size: float
p_value: float
confidence_interval: Tuple[float, float]
is_significant: bool
power: float

# =============================================================================

# CLASSIFICATION

# =============================================================================

def classify_phi_distance(r_normalized: float, tolerance: float = 0.05) -> Tuple[bool, float, float]:
“”“Classify if distance is close to phi-ratio.”””
deviations = [abs(r_normalized - phi_power) for phi_power in PHI_POWERS]
min_deviation = min(deviations)
closest_phi = PHI_POWERS[deviations.index(min_deviation)]
is_phi = min_deviation <= tolerance
return is_phi, closest_phi, min_deviation

def expected_classical_rate(r: float, R0: float, tau_D: float = 1e-9) -> float:
“”“Classical FRET rate: k_T = (1/τ_D) × (R0/r)^6”””
if r <= 0:
return float(‘inf’)
return (1.0 / tau_D) * (R0 / r) ** 6

# =============================================================================

# DATA GENERATION (PLACEHOLDER FOR REAL DATA)

# =============================================================================

def generate_lhcii_pigment_data(seed: int = 42, embed_signal: bool = True) -> List[PigmentPair]:
“””
Generate simulated LHC-II data.

```
Set embed_signal=True to test detection capability
Set embed_signal=False to test null hypothesis
"""
np.random.seed(seed)

n_molecules = 14  # LHC-II has ~14 chlorophylls
pairs = []

for i in range(n_molecules):
    for j in range(i + 1, n_molecules):
        distance = np.random.uniform(0.5e-9, 4.0e-9)
        r_norm = distance / R0_CHLOROPHYLL
        is_phi, closest_phi, deviation = classify_phi_distance(r_norm)
        k_classical = expected_classical_rate(distance, R0_CHLOROPHYLL)
        
        if embed_signal and is_phi:
            enhancement = 1.0 + (0.3 / (1 + deviation * 10))
        else:
            enhancement = 1.0 + np.random.normal(0, 0.1)
        
        k_observed = max(0, k_classical * enhancement)
        efficiency = min(1.0, (1.0 / (1.0 + (distance / R0_CHLOROPHYLL) ** 6)) * enhancement)
        
        pairs.append(PigmentPair(
            pair_id=f"Chl{i:02d}-Chl{j:02d}",
            distance=distance,
            distance_normalized=r_norm,
            transfer_rate=k_observed,
            transfer_efficiency=efficiency,
            is_phi_distance=is_phi,
            closest_phi_power=closest_phi,
            phi_deviation=deviation
        ))

return pairs
```

# =============================================================================

# STATISTICAL TESTS

# =============================================================================

def perform_t_test(pairs: List[PigmentPair], metric: str = ‘transfer_rate’) -> StatisticalResult:
“”“Primary t-test for phi-enhancement.”””
phi_pairs = [p for p in pairs if p.is_phi_distance]
control_pairs = [p for p in pairs if not p.is_phi_distance]

```
phi_values = [getattr(p, metric) for p in phi_pairs]
control_values = [getattr(p, metric) for p in control_pairs]

phi_mean = np.mean(phi_values)
control_mean = np.mean(control_values)

# Effect size (Cohen's d)
pooled_std = np.sqrt(((len(phi_values) - 1) * np.var(phi_values, ddof=1) + 
                     (len(control_values) - 1) * np.var(control_values, ddof=1)) / 
                    (len(phi_values) + len(control_values) - 2))
effect_size = (phi_mean - control_mean) / pooled_std if pooled_std > 0 else 0.0

# One-tailed t-test
t_stat, p_two_tail = stats.ttest_ind(phi_values, control_values)
p_value = p_two_tail / 2 if t_stat > 0 else 1 - p_two_tail / 2

# 95% CI for difference
diff_se = np.sqrt(np.var(phi_values, ddof=1) / len(phi_values) + 
                 np.var(control_values, ddof=1) / len(control_values))
ci_low = (phi_mean - control_mean) - 1.96 * diff_se
ci_high = (phi_mean - control_mean) + 1.96 * diff_se

# Power estimate
n_harmonic = 2 * len(phi_values) * len(control_values) / (len(phi_values) + len(control_values))
ncp = effect_size * np.sqrt(n_harmonic)
df = len(phi_values) + len(control_values) - 2
critical_t = stats.t.ppf(0.95, df)
power = 1 - stats.nct.cdf(critical_t, df, ncp) if ncp > 0 else 0.05

return StatisticalResult(
    test_name=f"Phi-Enhancement T-Test ({metric})",
    n_phi_pairs=len(phi_pairs),
    n_control_pairs=len(control_pairs),
    phi_mean=phi_mean,
    control_mean=control_mean,
    effect_size=effect_size,
    p_value=p_value,
    confidence_interval=(ci_low, ci_high),
    is_significant=p_value < 0.01,
    power=power
)
```

def perform_correlation_test(pairs: List[PigmentPair]) -> Dict:
“”“Test correlation between phi-deviation and enhancement.”””
deviations = []
enhancements = []

```
for p in pairs:
    expected = expected_classical_rate(p.distance, R0_CHLOROPHYLL)
    if expected > 0:
        enhancement = (p.transfer_rate - expected) / expected
        deviations.append(p.phi_deviation)
        enhancements.append(enhancement)

r_pearson, p_pearson = stats.pearsonr(deviations, enhancements)
r_spearman, p_spearman = stats.spearmanr(deviations, enhancements)

return {
    'pearson_r': r_pearson,
    'pearson_p': p_pearson,
    'spearman_r': r_spearman,
    'spearman_p': p_spearman,
    'n_pairs': len(deviations),
    'supports_hypothesis': r_pearson < -0.2 and p_pearson < 0.05
}
```

def perform_permutation_test(pairs: List[PigmentPair], n_permutations: int = 10000,
metric: str = ‘transfer_rate’) -> Dict:
“”“Non-parametric permutation test.”””
phi_values = [getattr(p, metric) for p in pairs if p.is_phi_distance]
control_values = [getattr(p, metric) for p in pairs if not p.is_phi_distance]

```
observed_diff = np.mean(phi_values) - np.mean(control_values)

all_values = phi_values + control_values
n_phi = len(phi_values)

count_extreme = 0
for _ in range(n_permutations):
    np.random.shuffle(all_values)
    perm_diff = np.mean(all_values[:n_phi]) - np.mean(all_values[n_phi:])
    if perm_diff >= observed_diff:
        count_extreme += 1

p_value = count_extreme / n_permutations

return {
    'observed_difference': observed_diff,
    'permutation_p_value': p_value,
    'n_permutations': n_permutations,
    'is_significant': p_value < 0.01,
    'percentile': 100 * (1 - p_value)
}
```

def perform_bootstrap(pairs: List[PigmentPair], n_bootstrap: int = 5000,
metric: str = ‘transfer_rate’) -> Dict:
“”“Bootstrap CI for effect size.”””
phi_values = [getattr(p, metric) for p in pairs if p.is_phi_distance]
control_values = [getattr(p, metric) for p in pairs if not p.is_phi_distance]

```
effect_sizes = []

for _ in range(n_bootstrap):
    phi_sample = np.random.choice(phi_values, size=len(phi_values), replace=True)
    control_sample = np.random.choice(control_values, size=len(control_values), replace=True)
    
    diff = np.mean(phi_sample) - np.mean(control_sample)
    pooled_std = np.sqrt((np.var(phi_sample, ddof=1) + np.var(control_sample, ddof=1)) / 2)
    
    if pooled_std > 0:
        effect_sizes.append(diff / pooled_std)

return {
    'effect_size_mean': np.mean(effect_sizes),
    'ci_95_low': np.percentile(effect_sizes, 2.5),
    'ci_95_high': np.percentile(effect_sizes, 97.5),
    'probability_positive': np.mean([e > 0 for e in effect_sizes]),
    'ci_excludes_zero': np.percentile(effect_sizes, 2.5) > 0
}
```

# =============================================================================

# COMPLETE ANALYSIS

# =============================================================================

def run_complete_analysis(pairs: List[PigmentPair]) -> Dict:
“”“Run all statistical tests.”””
results = {
‘n_total’: len(pairs),
‘n_phi’: sum(1 for p in pairs if p.is_phi_distance),
‘n_control’: sum(1 for p in pairs if not p.is_phi_distance)
}

```
results['t_test'] = perform_t_test(pairs)
results['correlation'] = perform_correlation_test(pairs)
results['permutation'] = perform_permutation_test(pairs)
results['bootstrap'] = perform_bootstrap(pairs)

# Verdict
tests_passed = sum([
    results['t_test'].is_significant,
    results['permutation']['is_significant'],
    results['correlation']['supports_hypothesis'],
    results['bootstrap']['ci_excludes_zero']
])

results['verdict'] = {
    'tests_passed': tests_passed,
    'total_tests': 4,
    'conclusion': 'SUPPORTS PHI-ENHANCEMENT' if tests_passed >= 3 else 
                 'INCONCLUSIVE' if tests_passed >= 2 else 'DOES NOT SUPPORT'
}

return results
```

def print_report(results: Dict):
“”“Print analysis report.”””
print(”=” * 70)
print(“PHI-ENHANCEMENT HYPOTHESIS: STATISTICAL ANALYSIS”)
print(”=” * 70)

```
print(f"\nDATA: {results['n_total']} pairs ({results['n_phi']} phi, {results['n_control']} control)")

t = results['t_test']
print(f"\n1. T-TEST")
print(f"   Phi mean: {t.phi_mean:.4e}, Control mean: {t.control_mean:.4e}")
print(f"   Effect size (Cohen's d): {t.effect_size:.3f}")
print(f"   P-value: {t.p_value:.4f}")
print(f"   SIGNIFICANT: {'YES' if t.is_significant else 'NO'}")

c = results['correlation']
print(f"\n2. CORRELATION (deviation vs enhancement)")
print(f"   Pearson r: {c['pearson_r']:.3f} (p = {c['pearson_p']:.4f})")
print(f"   SUPPORTS: {'YES' if c['supports_hypothesis'] else 'NO'}")

p = results['permutation']
print(f"\n3. PERMUTATION TEST")
print(f"   Observed diff: {p['observed_difference']:.4e}")
print(f"   P-value: {p['permutation_p_value']:.4f}")
print(f"   SIGNIFICANT: {'YES' if p['is_significant'] else 'NO'}")

b = results['bootstrap']
print(f"\n4. BOOTSTRAP")
print(f"   Effect size: {b['effect_size_mean']:.3f}")
print(f"   95% CI: [{b['ci_95_low']:.3f}, {b['ci_95_high']:.3f}]")
print(f"   CI EXCLUDES ZERO: {'YES' if b['ci_excludes_zero'] else 'NO'}")

v = results['verdict']
print(f"\n" + "=" * 70)
print(f"VERDICT: {v['tests_passed']}/{v['total_tests']} tests passed")
print(f">>> {v['conclusion']} <<<")
print("=" * 70)
```

# =============================================================================

# DEMO

# =============================================================================

if **name** == “**main**”:
print(“Testing with embedded signal (should detect)…”)
pairs_signal = generate_lhcii_pigment_data(seed=42, embed_signal=True)
results_signal = run_complete_analysis(pairs_signal)
print_report(results_signal)

```
print("\n\nTesting null hypothesis (no signal)...")
pairs_null = generate_lhcii_pigment_data(seed=42, embed_signal=False)
results_null = run_complete_analysis(pairs_null)
print_report(results_null)
```
