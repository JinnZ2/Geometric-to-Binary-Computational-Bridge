"""
Holographic Smoothness Testing via Octahedral Hierarchy
========================================================
Can octahedral geometry accelerate the sieving step of
the quadratic sieve?

Hypothesis: Organize the factor base into an octahedral hierarchy
(8 states per level = 3 bits). Test smoothness coarse-to-fine,
rejecting non-smooth candidates early at low resolution.

The honest test: compare this against naive smoothness testing
and standard sieve methods. Measure actual speedup.

Key insight from the QS analysis:
  - The bottleneck is finding B-smooth values of Q(a) = a^2 mod N
  - Standard QS sieve marks positions divisible by each prime
  - Octahedral hierarchy could enable early rejection AND vectorization
"""

import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

import sys
sys.path.insert(0, '.')
from experiments.number_theoretic_energy import (
    is_prime, next_prime, isqrt, compute_factor_base,
    factorize_over_base, smoothness_score,
)


# ═══════════════════════════════════════════════════════════════════════
# OCTAHEDRAL HIERARCHY: Group primes into 8-state clusters
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class OctahedralLevel:
    """One level of the octahedral hierarchy."""
    level: int
    primes: List[int]           # Primes at this level
    product: int                # Product of primes at this level
    residue_classes: int        # Number of valid residue classes


@dataclass
class OctahedralHierarchy:
    """
    Multi-level octahedral organization of the factor base.

    Level 0: First few small primes (coarsest filter)
    Level 1: Medium primes
    Level 2: Larger primes (finest resolution)

    At each level, we check divisibility by the primes at that level.
    If the remaining cofactor is already too large to be smooth,
    we reject early.
    """
    levels: List[OctahedralLevel]
    factor_base: List[int]
    N: int

    @classmethod
    def build(cls, N: int, B_bound: Optional[int] = None,
              primes_per_level: int = 3) -> 'OctahedralHierarchy':
        """
        Build the hierarchy from a factor base.

        primes_per_level: how many primes per octahedral cluster.
        Using 3 gives 8 divisibility states (2^3) per level — matching
        the octahedral vertex count exactly.
        """
        fb = compute_factor_base(N, B_bound)

        levels = []
        for i in range(0, len(fb), primes_per_level):
            chunk = fb[i:i + primes_per_level]
            product = 1
            for p in chunk:
                product *= p
            # Number of residue classes: product of (1 - 1/p) * product
            # (values coprime to all primes in chunk)
            residue_classes = product
            for p in chunk:
                residue_classes = residue_classes * (p - 1) // p

            levels.append(OctahedralLevel(
                level=i // primes_per_level,
                primes=chunk,
                product=product,
                residue_classes=residue_classes,
            ))

        return cls(levels=levels, factor_base=fb, N=N)

    @property
    def depth(self) -> int:
        return len(self.levels)

    @property
    def dimension(self) -> int:
        return len(self.factor_base)


# ═══════════════════════════════════════════════════════════════════════
# COARSE-TO-FINE SMOOTHNESS TEST
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class SmoothnessResult:
    """Result of a smoothness test."""
    is_smooth: bool
    exponents: Optional[List[int]]
    rejection_level: int    # -1 if smooth, else the level that rejected
    divisions_performed: int  # Actual division operations counted


def naive_smoothness_test(n: int, factor_base: List[int]) -> SmoothnessResult:
    """
    Baseline: try dividing by every prime in the factor base.
    Count every division operation.
    """
    if n == 0:
        return SmoothnessResult(False, None, -1, 0)

    exponents = [0] * len(factor_base)
    remaining = abs(n)
    divisions = 0

    for i, p in enumerate(factor_base):
        while remaining % p == 0:
            divisions += 1
            exponents[i] += 1
            remaining //= p
        if remaining > 1:
            divisions += 1  # Count the failed test too

    if remaining == 1:
        return SmoothnessResult(True, exponents, -1, divisions)
    return SmoothnessResult(False, None, -1, divisions)


def hierarchical_smoothness_test(n: int,
                                  hierarchy: OctahedralHierarchy) -> SmoothnessResult:
    """
    Coarse-to-fine smoothness test using octahedral hierarchy.

    At each level:
    1. Divide out primes at this level
    2. Check if cofactor is small enough to possibly be smooth
       over remaining levels
    3. If cofactor is too large → REJECT EARLY

    The key optimization: early rejection saves all the divisions
    at deeper levels.
    """
    if n == 0:
        return SmoothnessResult(False, None, 0, 0)

    exponents = [0] * len(hierarchy.factor_base)
    remaining = abs(n)
    divisions = 0
    prime_idx = 0

    for level in hierarchy.levels:
        # Divide out primes at this level
        for p in level.primes:
            while remaining % p == 0:
                divisions += 1
                exponents[prime_idx] += 1
                remaining //= p
            if remaining > 1:
                divisions += 1  # Count failed test
            prime_idx += 1

        if remaining == 1:
            # Fully factored — smooth!
            return SmoothnessResult(True, exponents, -1, divisions)

        # EARLY REJECTION: Is the cofactor possibly smooth over remaining primes?
        # The largest prime we haven't tried yet bounds what's possible.
        if level.level < hierarchy.depth - 1:
            remaining_primes = []
            for future_level in hierarchy.levels[level.level + 1:]:
                remaining_primes.extend(future_level.primes)

            if remaining_primes:
                max_remaining_prime = max(remaining_primes)
                # If cofactor > max_remaining_prime^2 and cofactor has no
                # small factors left, it can't be smooth
                # More precisely: if cofactor is prime and > max_remaining_prime,
                # it's definitely not smooth
                if remaining > max_remaining_prime * max_remaining_prime:
                    # Could still have two large factors, keep going
                    pass
                elif remaining > max_remaining_prime and is_prime(remaining):
                    # Definitely not smooth — early reject!
                    return SmoothnessResult(False, None, level.level, divisions)

    # After all levels
    if remaining == 1:
        return SmoothnessResult(True, exponents, -1, divisions)
    return SmoothnessResult(False, None, hierarchy.depth - 1, divisions)


def octahedral_state_test(n: int,
                           hierarchy: OctahedralHierarchy) -> SmoothnessResult:
    """
    Enhanced hierarchical test using octahedral state encoding.

    At each level, compute the "octahedral state" — a 3-bit vector
    encoding divisibility by the 3 primes at that level:

        state = (n%p1==0, n%p2==0, n%p3==0)  → 8 possible states

    State (1,1,1) = divisible by all 3 → most promising
    State (0,0,0) = divisible by none → least promising at this level

    The state determines the SEARCH STRATEGY at the next level:
    - High-weight states (many 1s): likely smooth, invest more
    - Low-weight states (many 0s): less likely, check quickly

    This is the octahedral vertex interpretation:
    - 8 vertices of the octahedron = 8 divisibility patterns
    - Adjacent vertices (Gray code) = single prime difference
    - Vertex weight = number of primes dividing n at this level
    """
    if n == 0:
        return SmoothnessResult(False, None, 0, 0)

    exponents = [0] * len(hierarchy.factor_base)
    remaining = abs(n)
    divisions = 0
    prime_idx = 0
    total_weight = 0  # Accumulated octahedral weight

    for level in hierarchy.levels:
        level_state = []

        for p in level.primes:
            divisible = (remaining % p == 0)
            divisions += 1
            level_state.append(divisible)

            if divisible:
                while remaining % p == 0:
                    divisions += 1
                    exponents[prime_idx] += 1
                    remaining //= p
            prime_idx += 1

        if remaining == 1:
            return SmoothnessResult(True, exponents, -1, divisions)

        # Octahedral state weight = number of primes that divided
        weight = sum(level_state)
        total_weight += weight

        # ADAPTIVE REJECTION based on accumulated octahedral state
        # If we've gone through several levels with low weight,
        # the number likely has large prime factors → reject
        levels_checked = level.level + 1
        if levels_checked >= 2:
            avg_weight = total_weight / (levels_checked * len(level.primes))

            # If average weight is very low AND cofactor is large
            if avg_weight < 0.15 and remaining > hierarchy.factor_base[-1]:
                return SmoothnessResult(False, None, level.level, divisions)

        # Hard rejection: cofactor is prime and larger than any remaining prime
        if level.level < hierarchy.depth - 1:
            max_future = max(p for lev in hierarchy.levels[level.level + 1:]
                            for p in lev.primes)
            if remaining > max_future and is_prime(remaining):
                return SmoothnessResult(False, None, level.level, divisions)

    if remaining == 1:
        return SmoothnessResult(True, exponents, -1, divisions)
    return SmoothnessResult(False, None, hierarchy.depth - 1, divisions)


# ═══════════════════════════════════════════════════════════════════════
# BENCHMARKS: Measure actual speedup
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class BenchmarkResult:
    N: int
    method: str
    candidates_tested: int
    smooth_found: int
    total_divisions: int
    divisions_per_candidate: float
    wall_time_ms: float
    rejection_distribution: Dict[int, int]  # level → count


def benchmark_sieving(N: int, n_candidates: int = 5000,
                       B_bound: Optional[int] = None) -> List[BenchmarkResult]:
    """
    Compare naive vs hierarchical vs octahedral smoothness testing.
    Tests n_candidates values of Q(a) = a^2 mod N near sqrt(N).
    """
    hierarchy = OctahedralHierarchy.build(N, B_bound)
    fb = hierarchy.factor_base
    sqrt_N = isqrt(N) + 1

    # Generate candidate values
    candidates = []
    for offset in range(n_candidates):
        a = sqrt_N + offset
        Q = (a * a) % N
        if Q > 0:
            candidates.append((a, Q))

    results = []

    # Method 1: Naive
    t0 = time.time()
    naive_smooth = 0
    naive_divs = 0
    for a, Q in candidates:
        r = naive_smoothness_test(Q, fb)
        naive_divs += r.divisions_performed
        if r.is_smooth:
            naive_smooth += 1
    t1 = time.time()

    results.append(BenchmarkResult(
        N=N, method="naive",
        candidates_tested=len(candidates),
        smooth_found=naive_smooth,
        total_divisions=naive_divs,
        divisions_per_candidate=naive_divs / max(len(candidates), 1),
        wall_time_ms=(t1 - t0) * 1000,
        rejection_distribution={},
    ))

    # Method 2: Hierarchical
    t0 = time.time()
    hier_smooth = 0
    hier_divs = 0
    hier_rejections = {}
    for a, Q in candidates:
        r = hierarchical_smoothness_test(Q, hierarchy)
        hier_divs += r.divisions_performed
        if r.is_smooth:
            hier_smooth += 1
        elif r.rejection_level >= 0:
            hier_rejections[r.rejection_level] = hier_rejections.get(r.rejection_level, 0) + 1
    t1 = time.time()

    results.append(BenchmarkResult(
        N=N, method="hierarchical",
        candidates_tested=len(candidates),
        smooth_found=hier_smooth,
        total_divisions=hier_divs,
        divisions_per_candidate=hier_divs / max(len(candidates), 1),
        wall_time_ms=(t1 - t0) * 1000,
        rejection_distribution=hier_rejections,
    ))

    # Method 3: Octahedral state
    t0 = time.time()
    oct_smooth = 0
    oct_divs = 0
    oct_rejections = {}
    for a, Q in candidates:
        r = octahedral_state_test(Q, hierarchy)
        oct_divs += r.divisions_performed
        if r.is_smooth:
            oct_smooth += 1
        elif r.rejection_level >= 0:
            oct_rejections[r.rejection_level] = oct_rejections.get(r.rejection_level, 0) + 1
    t1 = time.time()

    results.append(BenchmarkResult(
        N=N, method="octahedral",
        candidates_tested=len(candidates),
        smooth_found=oct_smooth,
        total_divisions=oct_divs,
        divisions_per_candidate=oct_divs / max(len(candidates), 1),
        wall_time_ms=(t1 - t0) * 1000,
        rejection_distribution=oct_rejections,
    ))

    return results


def run_benchmark():
    """Run the full benchmark comparison."""
    print("=" * 80)
    print("HOLOGRAPHIC SMOOTHNESS: OCTAHEDRAL HIERARCHY BENCHMARK")
    print("Can coarse-to-fine octahedral testing beat naive sieving?")
    print("=" * 80)

    test_cases = [
        (221, 30),
        (1517, 30),
        (5767, 50),
        (17947, 50),
        (67591, 80),
        (281861, 80),
        (1071209, 100),
    ]

    print()
    print("{:>10} {:>12} {:>6} {:>8} {:>10} {:>8} {:>8}".format(
        "N", "method", "found", "divs", "divs/cand", "time_ms", "speedup"))
    print("-" * 72)

    for N, B_bound in test_cases:
        results = benchmark_sieving(N, n_candidates=2000, B_bound=B_bound)
        naive_divs = results[0].total_divisions

        for r in results:
            speedup = naive_divs / max(r.total_divisions, 1)
            sp_str = "{:.2f}x".format(speedup) if r.method != "naive" else "  base"
            print("{:10d} {:>12} {:6d} {:8d} {:10.1f} {:8.1f} {:>8}".format(
                r.N, r.method, r.smooth_found, r.total_divisions,
                r.divisions_per_candidate, r.wall_time_ms, sp_str))

        # Show rejection distribution for octahedral
        oct = results[2]
        if oct.rejection_distribution:
            rej_str = ", ".join("L{}:{}".format(k, v)
                                for k, v in sorted(oct.rejection_distribution.items()))
            print("{:>10} {:>12} {}".format("", "rejections:", rej_str))

        print()

    # Summary
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print("""
    What the octahedral hierarchy does:
      1. Groups factor base primes into 3-prime clusters (8 states each)
      2. Tests divisibility level-by-level (coarse to fine)
      3. Rejects non-smooth candidates early if cofactor is provably too large
      4. Tracks "octahedral weight" (how many primes divide at each level)
         to adaptively reject low-weight candidates

    What this tests:
      - Does early rejection save significant work?
      - Does the hierarchical structure reduce total divisions?
      - Is there measurable wall-clock speedup?

    What would make this MORE powerful:
      - SIMD: process 8 residue classes simultaneously per octahedral unit
      - Geometric sieving: use octahedral symmetry to sieve in parallel
      - Lattice structure: the GF(2) exponent space has lattice structure
        that octahedral geometry could exploit for faster null space search
    """)


if __name__ == "__main__":
    run_benchmark()
