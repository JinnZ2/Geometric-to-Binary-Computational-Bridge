"""
Factorization Landscape Analysis — Rigorous Barrier Scaling
============================================================
Tests the "semi-permeable trough" hypothesis for E = (a*b - N)^2.

Key questions:
  1. Do barriers grow polynomially or exponentially with N?
  2. Is the trough navigable in INTEGER space (not just continuous)?
  3. How does annealing compare to trial division as N grows?
  4. Where does the landscape structure break down?

Honest methodology:
  - Tests semiprimes from 2 digits to 8+ digits
  - Measures ACTUAL annealing steps to solution (not just success/fail)
  - Compares against trial division baseline
  - Separates continuous trough properties from discrete hardness
"""

import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict


# ── Semiprime generation ────────────────────────────────────────────────

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def next_prime(n: int) -> int:
    if n < 2:
        return 2
    candidate = n + 1 if n % 2 == 0 else n + 2
    while not is_prime(candidate):
        candidate += 2
    return candidate


def generate_semiprimes(bit_range: Tuple[int, int] = (4, 28),
                         count_per_size: int = 3) -> List[Tuple[int, int, int]]:
    """
    Generate semiprimes N = p*q across bit sizes.
    Returns list of (N, p, q) sorted by N.
    """
    results = []
    for bits in range(bit_range[0], bit_range[1] + 1, 2):
        half_bits = bits // 2
        p_min = max(3, 2 ** (half_bits - 1))
        p_max = 2 ** half_bits

        count = 0
        p = next_prime(p_min)
        while count < count_per_size and p < p_max:
            q = next_prime(p + 2)
            if q < p_max * 2:  # Allow some asymmetry
                N = p * q
                results.append((N, p, q))
                count += 1
            p = next_prime(q)

    return sorted(results, key=lambda x: x[0])


# ── Energy landscape ───────────────────────────────────────────────────

def energy(a: int, b: int, N: int) -> int:
    """E = (a*b - N)^2"""
    return (a * b - N) ** 2


def trough_deviation(a: int, N: int) -> float:
    """
    For given a, the nearest integer b to the trough a*b = N.
    Returns (b_nearest, deviation_energy).
    """
    b_exact = N / a
    b_floor = int(b_exact)
    b_ceil = b_floor + 1

    e_floor = energy(a, b_floor, N) if b_floor >= 2 else float('inf')
    e_ceil = energy(a, b_ceil, N)

    if e_floor <= e_ceil:
        return b_floor, e_floor
    return b_ceil, e_ceil


# ── Barrier analysis ───────────────────────────────────────────────────

@dataclass
class BarrierResult:
    N: int
    p: int
    q: int
    bits: int
    num_local_minima: int
    max_barrier: float
    mean_barrier: float
    barrier_over_N: float
    trough_min_energies: List[int]   # Energy at each integer along trough


def analyze_barriers(N: int, p: int, q: int) -> BarrierResult:
    """
    Comprehensive barrier analysis for semiprime N = p*q.

    Walks the INTEGER trough: for each a in [2, sqrt(N)+margin],
    finds the nearest integer b to a*b = N and records the energy.
    The barriers between adjacent trough points are the energy differences
    that an integer-space walker must overcome.
    """
    bits = int(math.log2(N)) + 1
    sqrt_N = int(math.isqrt(N))
    max_a = min(sqrt_N + 10, N // 2)

    # Walk the integer trough
    trough_energies = []
    local_minima = []

    for a in range(2, max_a + 1):
        b_near, e = trough_deviation(a, N)
        trough_energies.append(e)

        # Check if local minimum: e < energy at (a-1) and (a+1)
        if a > 2:
            _, e_prev = trough_deviation(a - 1, N)
            _, e_next = trough_deviation(a + 1, N)
            if e <= e_prev and e <= e_next:
                local_minima.append((a, b_near, e))

    # Ground state is at a=p, b=q (energy = 0)
    ground_energy = 0

    # Compute barriers: max energy on the trough between each
    # local minimum and the ground state
    barriers = []
    p_idx = p - 2  # Index of p in trough walk (a starts at 2)

    for a, b, e in local_minima:
        if e == 0:
            continue  # Skip the ground state itself

        a_idx = a - 2
        # Walk from this minimum to the ground state along the trough
        start = min(a_idx, p_idx)
        end = max(a_idx, p_idx)

        if start < 0 or end >= len(trough_energies):
            continue

        path_max = max(trough_energies[start:end + 1])
        barrier = path_max - ground_energy
        barriers.append(barrier)

    max_barrier = max(barriers) if barriers else 0
    mean_barrier = float(np.mean(barriers)) if barriers else 0.0

    return BarrierResult(
        N=N,
        p=p,
        q=q,
        bits=bits,
        num_local_minima=len(local_minima),
        max_barrier=max_barrier,
        mean_barrier=mean_barrier,
        barrier_over_N=max_barrier / N if N > 0 else 0,
        trough_min_energies=trough_energies,
    )


# ── Why barriers are O(N): mathematical proof ─────────────────────────

def barrier_is_ON_proof() -> str:
    """
    Explain why barrier_max ~ O(N) is inherent to E = (ab - N)^2,
    not evidence of polynomial-time factorization.
    """
    return """
    PROOF: Barrier_max ~ O(N) is a property of the energy function.

    For any integer a near a factor p of N:
      Let a = p + delta, where delta is a small integer.
      The nearest integer b to N/a is approximately q - delta*q/p.
      The residual energy is:

        E(a) = (a * round(N/a) - N)^2

      For a = p + 1 (one step from the factor):
        b = round(N/(p+1))
        a*b - N ≈ N/(p+1) * (p+1) - N + rounding_error
                ≈ rounding_error

      The rounding error for N/(p+1) is at most 1, so:
        E(p+1) ≈ (p+1)^2  (from the product deviation)

      More precisely: for a not dividing N, the minimum
      E(a) = min_b (a*b - N)^2 = (N mod a)^2  if N mod a <= a/2
                                  (a - N mod a)^2  otherwise

      The maximum of (N mod a)^2 over all a is bounded by (a/2)^2,
      and a <= sqrt(N), so:

        Barrier_max <= (sqrt(N)/2)^2 = N/4

    Therefore: Barrier_max = O(N).

    This is NOT evidence that factorization is easy.
    It's a mathematical property of quadratic energy functions
    over integer grids.

    The HARDNESS of factorization comes from:
    - The number of integers a to search: O(sqrt(N)) = O(2^(n/2))
      where n = bits of N
    - The trough has O(sqrt(N)) integer points
    - Finding the ONE point with E=0 among O(sqrt(N)) candidates
      is the actual computational problem
    - This is equivalent to trial division
    """


# ── Simulated annealing with step counting ─────────────────────────────

@dataclass
class AnnealingResult:
    N: int
    found: bool
    factor_a: int
    factor_b: int
    steps_to_solution: int  # -1 if not found
    total_steps: int
    energy_evaluations: int
    final_energy: int


def anneal_factorize(N: int, max_steps: int = 100000,
                      T_start: float = 1000.0,
                      T_end: float = 0.01,
                      seed: Optional[int] = None) -> AnnealingResult:
    """
    Simulated annealing on E = (a*b - N)^2.
    Counts EVERY energy evaluation honestly.
    """
    rng = np.random.default_rng(seed)
    sqrt_N = int(math.isqrt(N))

    # Start random
    a = int(rng.integers(2, max(3, sqrt_N)))
    b = int(rng.integers(2, max(3, sqrt_N * 2)))
    e_current = energy(a, b, N)
    evals = 1

    best_a, best_b, best_e = a, b, e_current
    steps_to_solution = -1

    T_schedule = np.logspace(math.log10(T_start), math.log10(T_end), max_steps)

    for step in range(max_steps):
        T = T_schedule[step]

        # Propose move: random neighbor in integer space
        move_type = rng.random()
        if move_type < 0.4:
            # Small step
            da = int(rng.integers(-2, 3))
            db = int(rng.integers(-2, 3))
        elif move_type < 0.7:
            # Move along trough: adjust a, set b = round(N/a)
            da = int(rng.integers(-3, 4))
            a_new = max(2, a + da)
            b_new = max(2, round(N / a_new))
            da = a_new - a
            db = b_new - b
        else:
            # Random restart in promising region
            a_new = int(rng.integers(2, max(3, sqrt_N + 10)))
            b_new = max(2, round(N / a_new))
            da = a_new - a
            db = b_new - b

        a_new = max(2, a + da)
        b_new = max(2, b + db)
        e_new = energy(a_new, b_new, N)
        evals += 1

        # Metropolis criterion
        delta_e = e_new - e_current
        if delta_e <= 0 or rng.random() < math.exp(-delta_e / max(T, 1e-10)):
            a, b = a_new, b_new
            e_current = e_new

        if e_current < best_e:
            best_a, best_b, best_e = a, b, e_current

        if best_e == 0 and steps_to_solution < 0:
            steps_to_solution = step + 1
            break  # Found exact factorization

    return AnnealingResult(
        N=N,
        found=(best_e == 0),
        factor_a=best_a,
        factor_b=best_b,
        steps_to_solution=steps_to_solution,
        total_steps=step + 1 if best_e == 0 else max_steps,
        energy_evaluations=evals,
        final_energy=best_e,
    )


# ── Trial division baseline ────────────────────────────────────────────

@dataclass
class TrialDivisionResult:
    N: int
    found: bool
    factor_a: int
    factor_b: int
    divisions: int  # Number of trial divisions performed


def trial_division(N: int) -> TrialDivisionResult:
    """
    Simple trial division — the baseline any approach must beat.
    Tries all odd numbers from 3 to sqrt(N).
    """
    if N % 2 == 0:
        return TrialDivisionResult(N, True, 2, N // 2, 1)

    divisions = 0
    limit = int(math.isqrt(N)) + 1

    for i in range(3, limit, 2):
        divisions += 1
        if N % i == 0:
            return TrialDivisionResult(N, True, i, N // i, divisions)

    return TrialDivisionResult(N, False, 0, 0, divisions)


# ── Scaling comparison ─────────────────────────────────────────────────

@dataclass
class ScalingDataPoint:
    N: int
    bits: int
    p: int
    q: int
    trial_divisions: int
    anneal_evals_median: int
    anneal_success_rate: float
    max_barrier: float
    barrier_over_N: float
    anneal_vs_trial_ratio: float  # >1 means annealing is SLOWER


def scaling_comparison(semiprimes: List[Tuple[int, int, int]],
                        anneal_trials: int = 10,
                        max_anneal_steps: int = 50000) -> List[ScalingDataPoint]:
    """
    Compare annealing to trial division across semiprime sizes.
    This is the honest test.
    """
    results = []

    for N, p, q in semiprimes:
        bits = int(math.log2(N)) + 1

        # Trial division
        td = trial_division(N)

        # Barrier analysis
        br = analyze_barriers(N, p, q)

        # Annealing (multiple trials)
        anneal_evals = []
        successes = 0
        for trial in range(anneal_trials):
            ar = anneal_factorize(N, max_steps=max_anneal_steps, seed=trial)
            if ar.found:
                successes += 1
                anneal_evals.append(ar.energy_evaluations)
            else:
                anneal_evals.append(max_anneal_steps)  # Penalty for failure

        median_evals = int(np.median(anneal_evals))
        success_rate = successes / anneal_trials

        ratio = median_evals / max(td.divisions, 1)

        results.append(ScalingDataPoint(
            N=N, bits=bits, p=p, q=q,
            trial_divisions=td.divisions,
            anneal_evals_median=median_evals,
            anneal_success_rate=success_rate,
            max_barrier=br.max_barrier,
            barrier_over_N=br.barrier_over_N,
            anneal_vs_trial_ratio=ratio,
        ))

    return results


def fit_scaling_exponent(data: List[ScalingDataPoint],
                          field: str = "anneal_evals_median") -> Tuple[float, float]:
    """
    Fit log(metric) = alpha * log(N) + c.
    Returns (alpha, R^2).
    """
    log_N = np.array([math.log(d.N) for d in data])
    log_y = np.array([math.log(max(getattr(d, field), 1)) for d in data])

    # Linear regression in log space
    coeffs = np.polyfit(log_N, log_y, 1)
    alpha = coeffs[0]

    # R^2
    y_pred = np.polyval(coeffs, log_N)
    ss_res = np.sum((log_y - y_pred) ** 2)
    ss_tot = np.sum((log_y - np.mean(log_y)) ** 2)
    r_squared = 1 - ss_res / max(ss_tot, 1e-10)

    return alpha, r_squared


# ── Full analysis runner ───────────────────────────────────────────────

def run_full_analysis(max_bits: int = 24,
                       anneal_trials: int = 10) -> Dict:
    """
    Run the complete scaling analysis.
    Returns structured results for inspection.
    """
    print("=" * 80)
    print("FACTORIZATION LANDSCAPE: RIGOROUS SCALING ANALYSIS")
    print("=" * 80)

    # Generate test semiprimes
    semiprimes = generate_semiprimes(bit_range=(4, max_bits), count_per_size=2)
    print(f"\nGenerated {len(semiprimes)} semiprimes from {semiprimes[0][0]} "
          f"to {semiprimes[-1][0]}")

    # Run scaling comparison
    print("\nRunning scaling comparison (this may take a moment)...\n")
    data = scaling_comparison(semiprimes, anneal_trials=anneal_trials)

    # Print results table
    print(f"{'N':>12} {'bits':>4} {'p':>6}x{'q':<6} {'trial':>6} "
          f"{'anneal':>7} {'succ%':>5} {'ratio':>7} {'barrier/N':>9}")
    print("-" * 78)

    for d in data:
        print(f"{d.N:12d} {d.bits:4d} {d.p:6d}x{d.q:<6d} {d.trial_divisions:6d} "
              f"{d.anneal_evals_median:7d} {d.anneal_success_rate*100:5.0f}% "
              f"{d.anneal_vs_trial_ratio:7.1f}x {d.barrier_over_N:9.3f}")

    # Fit scaling exponents
    if len(data) >= 3:
        alpha_anneal, r2_anneal = fit_scaling_exponent(data, "anneal_evals_median")
        alpha_trial, r2_trial = fit_scaling_exponent(data, "trial_divisions")
        alpha_barrier, r2_barrier = fit_scaling_exponent(data, "max_barrier")

        print(f"\n{'SCALING EXPONENTS':=^78}")
        print(f"  Trial division:  steps ~ N^{alpha_trial:.3f}  (R²={r2_trial:.3f})")
        print(f"  Annealing evals: evals ~ N^{alpha_anneal:.3f}  (R²={r2_anneal:.3f})")
        print(f"  Max barrier:     barrier ~ N^{alpha_barrier:.3f}  (R²={r2_barrier:.3f})")
        print()

        # The critical comparison
        print(f"  Trial division scales as N^{alpha_trial:.2f} ≈ N^0.5")
        print(f"  (This IS sqrt(N), which is O(2^(n/2)) in bits — exponential!)")
        print()
        if alpha_anneal > alpha_trial:
            print(f"  Annealing is SLOWER than trial division (exponent {alpha_anneal:.2f} > {alpha_trial:.2f})")
        elif alpha_anneal < alpha_trial * 0.9:
            print(f"  Annealing may be faster (exponent {alpha_anneal:.2f} < {alpha_trial:.2f})")
            print(f"  BUT: check if this holds for larger N before concluding anything.")
        else:
            print(f"  Annealing scales similarly to trial division.")

    # Explain the barrier result
    print(f"\n{'BARRIER ANALYSIS':=^78}")
    print(barrier_is_ON_proof())

    return {
        "semiprimes": semiprimes,
        "scaling_data": data,
    }


if __name__ == "__main__":
    run_full_analysis(max_bits=22, anneal_trials=8)
