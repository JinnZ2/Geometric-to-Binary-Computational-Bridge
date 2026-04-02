"""
Number-Theoretic Energy Functions for Factorization
=====================================================
Encodes algebraic structure from modern factorization algorithms
(Fermat, quadratic sieve) into energy landscapes, then tests whether
geometric/dimensional approaches can exploit that structure.

The core idea:
  Naive:   E = (ab - N)^2              → 2D, no number theory, = trial division
  Fermat:  E = penalty(a^2 - N != b^2) → encodes perfect-square structure
  QS:      E = smoothness penalties     → encodes prime factor distribution
                in D-dimensional space where D = |factor base|

Each successive encoding adds DIMENSION — more structure to exploit.

References:
  - Fermat's factorization method (1643)
  - Quadratic sieve (Pomerance, 1981)
  - Relation to lattice problems: Schnorr (1993)
"""

import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from collections import Counter

from experiments.factorization_landscape import (
    is_prime, next_prime, trial_division, generate_semiprimes,
)


# ═══════════════════════════════════════════════════════════════════════
# LEVEL 0: Naive energy (2D, no number theory)
# ═══════════════════════════════════════════════════════════════════════

def energy_naive(a: int, b: int, N: int) -> int:
    """E = (a*b - N)^2. The baseline — equivalent to trial division."""
    return (a * b - N) ** 2


# ═══════════════════════════════════════════════════════════════════════
# LEVEL 1: Fermat energy (2D, encodes perfect-square structure)
# ═══════════════════════════════════════════════════════════════════════
#
# Fermat's insight: N = a^2 - b^2 = (a+b)(a-b)
# So: find a such that a^2 - N = b^2 (a perfect square)
#
# The energy function penalizes deviation from perfect-square-ness.
# This encodes MORE structure than (ab-N)^2 because it uses the
# algebraic identity of difference of squares.

def isqrt(n: int) -> int:
    """Integer square root."""
    if n < 0:
        return 0
    x = int(math.isqrt(n))
    return x


def perfect_square_residual(n: int) -> int:
    """
    How far is n from being a perfect square?
    Returns min(n - floor(sqrt(n))^2, ceil(sqrt(n))^2 - n).
    """
    if n < 0:
        return abs(n)  # Negative numbers are never perfect squares
    s = isqrt(n)
    low = s * s
    high = (s + 1) * (s + 1)
    return min(n - low, high - n)


def energy_fermat(a: int, N: int) -> int:
    """
    Fermat energy: E = perfect_square_residual(a^2 - N)

    Ground state: E = 0 when a^2 - N = b^2, meaning N = (a-b)(a+b).
    This is a 1D search (over a) that encodes number-theoretic structure.

    Fermat's method finds factors in O((p-q)^2 / (4*sqrt(N))) steps
    for N = pq — fast when factors are close, slow when far apart.
    """
    val = a * a - N
    if val < 0:
        return abs(val)  # Below sqrt(N), a^2 < N
    return perfect_square_residual(val)


# ═══════════════════════════════════════════════════════════════════════
# LEVEL 2: Smoothness energy (D-dimensional, encodes prime distribution)
# ═══════════════════════════════════════════════════════════════════════
#
# The quadratic sieve's key insight:
#   1. Pick a "factor base" B = {p1, p2, ..., pk} (small primes)
#   2. Find values a where Q(a) = a^2 mod N is "B-smooth"
#      (all prime factors of Q(a) are in B)
#   3. When you have enough smooth relations, solve a linear system
#      over GF(2) to find a congruence x^2 ≡ y^2 (mod N)
#   4. Then gcd(x-y, N) gives a factor
#
# The DIMENSION is |B| — the size of the factor base.
# Each smooth relation is a POINT in this |B|-dimensional space.
# Finding enough points to span a null vector is the actual problem.

def compute_factor_base(N: int, B_bound: Optional[int] = None) -> List[int]:
    """
    Build the factor base: primes p <= B where N is a quadratic
    residue mod p (Legendre symbol (N/p) = 1).

    B_bound: smoothness bound. Default: exp(sqrt(ln N * ln ln N) / 2)
    (the theoretically optimal bound for quadratic sieve).
    """
    if B_bound is None:
        ln_N = math.log(max(N, 2))
        ln_ln_N = math.log(max(ln_N, 1))
        B_bound = max(10, int(math.exp(math.sqrt(ln_N * ln_ln_N) / 2)))

    factor_base = [2]  # 2 is always included
    p = 3
    while p <= B_bound:
        if is_prime(p):
            # Check if N is a quadratic residue mod p (Euler criterion)
            if pow(N % p, (p - 1) // 2, p) == 1:
                factor_base.append(p)
        p += 2

    return factor_base


def factorize_over_base(n: int, factor_base: List[int]) -> Optional[List[int]]:
    """
    Try to express n as a product of primes in the factor base.
    Returns exponent vector if n is B-smooth, None otherwise.

    The exponent vector has length |factor_base|.
    Entry i = exponent of factor_base[i] in the factorization of n.
    """
    if n == 0:
        return None

    exponents = [0] * len(factor_base)
    remaining = abs(n)

    for i, p in enumerate(factor_base):
        while remaining % p == 0:
            exponents[i] += 1
            remaining //= p

    if remaining == 1:
        return exponents  # Fully factored over the base → B-smooth!
    return None  # Not B-smooth


def smoothness_score(n: int, factor_base: List[int]) -> float:
    """
    How "smooth" is n over the factor base?

    Returns a score in [0, 1]:
      1.0 = fully B-smooth (all factors in base)
      0.0 = no factors from base divide n

    This is the key energy term — it rewards configurations
    where a^2 mod N has small prime factors.
    """
    if n == 0:
        return 1.0

    remaining = abs(n)
    original = remaining

    for p in factor_base:
        while remaining % p == 0:
            remaining //= p

    if remaining == 1:
        return 1.0  # Fully smooth

    # Partial smoothness: fraction of n that was removed
    if original == 0:
        return 0.0
    return 1.0 - math.log(remaining) / math.log(max(original, 2))


def energy_smoothness(a: int, N: int, factor_base: List[int]) -> float:
    """
    Smoothness energy: penalizes non-smooth residues.

    E = -smoothness_score(a^2 mod N, factor_base)

    Lower energy = smoother residue = closer to a useful QS relation.
    Ground state: E = -1.0 (fully B-smooth residue).
    """
    Q = (a * a) % N
    if Q == 0:
        return -1.0
    return -smoothness_score(Q, factor_base)


# ═══════════════════════════════════════════════════════════════════════
# LEVEL 3: Relation-matrix energy (D-dimensional lattice problem)
# ═══════════════════════════════════════════════════════════════════════
#
# The full QS works by collecting smooth relations, then solving
# a system of linear equations over GF(2). The "energy" of the
# system decreases as we approach a null vector in the exponent matrix.
#
# This is where DIMENSION truly matters:
#   - Each relation is a point in Z^|B| (exponent space)
#   - We need |B|+1 relations to guarantee a dependency
#   - Finding the dependency is linear algebra, not search
#   - The SEARCH is for smooth values; the ALGEBRA is polynomial

@dataclass
class SmoothRelation:
    """A relation: a, Q(a) = a^2 mod N, and its exponent vector."""
    a: int
    Q: int              # a^2 mod N
    exponents: List[int]  # Factorization over the base


@dataclass
class RelationMatrix:
    """
    The collection of smooth relations found so far.
    When we have enough, we can find a GF(2) null vector
    and extract the factorization.
    """
    N: int
    factor_base: List[int]
    relations: List[SmoothRelation] = field(default_factory=list)

    @property
    def dimension(self) -> int:
        """The dimension of the search space = |factor base|."""
        return len(self.factor_base)

    @property
    def n_relations(self) -> int:
        return len(self.relations)

    @property
    def enough_relations(self) -> bool:
        """Need |B|+1 relations to guarantee a GF(2) dependency."""
        return self.n_relations > self.dimension

    def add_if_smooth(self, a: int) -> bool:
        """
        Check if a^2 mod N is B-smooth.
        If yes, add the relation. Returns True if smooth.
        """
        Q = (a * a) % self.N
        if Q == 0:
            return False

        exponents = factorize_over_base(Q, self.factor_base)
        if exponents is not None:
            self.relations.append(SmoothRelation(a=a, Q=Q, exponents=exponents))
            return True
        return False

    def exponent_matrix_mod2(self) -> np.ndarray:
        """Build the exponent matrix mod 2 for GF(2) null space."""
        if not self.relations:
            return np.array([])
        return np.array([r.exponents for r in self.relations]) % 2

    def find_dependency(self) -> Optional[List[int]]:
        """
        Find a GF(2) null vector in the exponent matrix.
        Returns indices of relations whose exponent sum is all-even.

        This is Gaussian elimination over GF(2).
        """
        if not self.enough_relations:
            return None

        mat = self.exponent_matrix_mod2().astype(int)
        n_rows, n_cols = mat.shape

        # Augment with identity to track row combinations
        augmented = np.hstack([mat, np.eye(n_rows, dtype=int)])

        # Gaussian elimination mod 2
        pivot_row = 0
        for col in range(n_cols):
            # Find pivot
            found = False
            for row in range(pivot_row, n_rows):
                if augmented[row, col] == 1:
                    # Swap
                    augmented[[pivot_row, row]] = augmented[[row, pivot_row]]
                    found = True
                    break

            if not found:
                continue

            # Eliminate
            for row in range(n_rows):
                if row != pivot_row and augmented[row, col] == 1:
                    augmented[row] = (augmented[row] + augmented[pivot_row]) % 2

            pivot_row += 1

        # Find a zero row in the left part (= dependency)
        for row in range(n_rows):
            if np.sum(augmented[row, :n_cols]) == 0:
                # This row is a dependency
                combination = augmented[row, n_cols:]
                indices = list(np.where(combination == 1)[0])
                if indices:
                    return indices

        return None

    def extract_factor(self, dependency_indices: List[int]) -> Optional[int]:
        """
        Given a GF(2) dependency, compute x^2 ≡ y^2 (mod N)
        and try gcd(x-y, N).
        """
        # x = product of a_i
        # y^2 = product of Q(a_i) — which is a perfect square by construction
        x = 1
        combined_exponents = [0] * self.dimension

        for idx in dependency_indices:
            rel = self.relations[idx]
            x = (x * rel.a) % self.N
            for j in range(self.dimension):
                combined_exponents[j] += rel.exponents[j]

        # y = product of p_j^(e_j/2)
        y = 1
        for j, exp in enumerate(combined_exponents):
            y = (y * pow(self.factor_base[j], exp // 2)) % self.N

        # gcd(x - y, N)
        factor = math.gcd(abs(x - y), self.N)
        if 1 < factor < self.N:
            return factor

        # Try x + y
        factor = math.gcd(abs(x + y), self.N)
        if 1 < factor < self.N:
            return factor

        return None


# ═══════════════════════════════════════════════════════════════════════
# COMBINED ENERGY: multi-term landscape
# ═══════════════════════════════════════════════════════════════════════

def combined_energy(a: int, N: int, factor_base: List[int],
                     w_fermat: float = 0.3,
                     w_smooth: float = 0.7) -> float:
    """
    Multi-objective energy combining Fermat and smoothness terms.

    E = w_fermat * E_fermat(a) + w_smooth * E_smooth(a)

    Lower = better. The smoothness term encodes QS structure.
    The Fermat term encodes perfect-square structure.
    """
    e_f = energy_fermat(a, N) / max(N, 1)  # Normalize
    e_s = energy_smoothness(a, N, factor_base)  # Already in [-1, 0]
    return w_fermat * e_f + w_smooth * e_s


# ═══════════════════════════════════════════════════════════════════════
# SOLVER: Quadratic sieve via energy minimization
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class QSResult:
    N: int
    found: bool
    factor: int
    other_factor: int
    smooth_relations_found: int
    smooth_relations_needed: int
    total_candidates_tested: int
    factor_base_size: int
    method: str  # "QS" or "Fermat" or "trial"


def qs_energy_solver(N: int, max_candidates: int = 100000,
                      B_bound: Optional[int] = None) -> QSResult:
    """
    Factorize N using quadratic-sieve-style energy minimization.

    The search is for smooth values of Q(a) = a^2 mod N.
    When enough smooth relations accumulate, linear algebra
    over GF(2) extracts the factorization.

    This is a real implementation of the algebraic structure,
    not a heuristic.
    """
    if N < 4:
        return QSResult(N, False, 0, 0, 0, 0, 0, 0, "trivial")

    # Build factor base
    factor_base = compute_factor_base(N, B_bound)
    matrix = RelationMatrix(N=N, factor_base=factor_base)
    needed = len(factor_base) + 1

    # Sieving: test candidates near sqrt(N)
    sqrt_N = isqrt(N) + 1
    candidates_tested = 0

    for offset in range(max_candidates):
        # Alternate above and below sqrt(N)
        if offset % 2 == 0:
            a = sqrt_N + offset // 2
        else:
            a = sqrt_N - (offset + 1) // 2
            if a < 2:
                continue

        candidates_tested += 1
        matrix.add_if_smooth(a)

        # Check if we have enough relations
        if matrix.enough_relations:
            dep = matrix.find_dependency()
            if dep is not None:
                factor = matrix.extract_factor(dep)
                if factor is not None:
                    return QSResult(
                        N=N, found=True,
                        factor=factor,
                        other_factor=N // factor,
                        smooth_relations_found=matrix.n_relations,
                        smooth_relations_needed=needed,
                        total_candidates_tested=candidates_tested,
                        factor_base_size=len(factor_base),
                        method="QS",
                    )

    return QSResult(
        N=N, found=False, factor=0, other_factor=0,
        smooth_relations_found=matrix.n_relations,
        smooth_relations_needed=needed,
        total_candidates_tested=candidates_tested,
        factor_base_size=len(factor_base),
        method="QS_failed",
    )


def fermat_solver(N: int, max_steps: int = 100000) -> QSResult:
    """
    Fermat factorization: search for a where a^2 - N = b^2.
    Uses the Fermat energy function.
    """
    a = isqrt(N) + 1
    for step in range(max_steps):
        b2 = a * a - N
        b = isqrt(b2)
        if b * b == b2:
            p = a + b
            q = a - b
            if q > 1 and p > 1:
                return QSResult(
                    N=N, found=True,
                    factor=q, other_factor=p,
                    smooth_relations_found=0,
                    smooth_relations_needed=0,
                    total_candidates_tested=step + 1,
                    factor_base_size=0,
                    method="Fermat",
                )
        a += 1

    return QSResult(
        N=N, found=False, factor=0, other_factor=0,
        smooth_relations_found=0, smooth_relations_needed=0,
        total_candidates_tested=max_steps,
        factor_base_size=0,
        method="Fermat_failed",
    )


# ═══════════════════════════════════════════════════════════════════════
# DIMENSIONAL ANALYSIS: compare 2D vs multi-D approaches
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DimensionalComparison:
    N: int
    bits: int
    p: int
    q: int
    trial_steps: int        # O(sqrt(N)) = 2D brute force
    fermat_steps: int       # 2D with algebra (fast when p≈q)
    qs_steps: int           # D-dimensional (D = |factor base|)
    qs_dimensions: int      # Size of factor base = dimension
    qs_relations_needed: int
    qs_relations_found: int
    winner: str


def dimensional_comparison(semiprimes: List[Tuple[int, int, int]]) -> List[DimensionalComparison]:
    """
    Compare factorization approaches across dimensionalities.
    Shows how adding DIMENSION (number-theoretic structure)
    changes the scaling.
    """
    results = []

    for N, p, q in semiprimes:
        bits = int(math.log2(N)) + 1

        # Trial division (2D, no structure)
        td = trial_division(N)

        # Fermat (2D, algebraic structure)
        fr = fermat_solver(N, max_steps=100000)

        # Quadratic sieve (D-dimensional)
        qs = qs_energy_solver(N, max_candidates=100000)

        # Determine winner
        steps = {
            "trial": td.divisions,
            "Fermat": fr.total_candidates_tested if fr.found else 999999,
            "QS": qs.total_candidates_tested if qs.found else 999999,
        }
        winner = min(steps, key=steps.get)

        results.append(DimensionalComparison(
            N=N, bits=bits, p=p, q=q,
            trial_steps=td.divisions,
            fermat_steps=fr.total_candidates_tested if fr.found else -1,
            qs_steps=qs.total_candidates_tested if qs.found else -1,
            qs_dimensions=qs.factor_base_size,
            qs_relations_needed=qs.smooth_relations_needed,
            qs_relations_found=qs.smooth_relations_found,
            winner=winner,
        ))

    return results


# ═══════════════════════════════════════════════════════════════════════
# MAIN: Run the full dimensional analysis
# ═══════════════════════════════════════════════════════════════════════

def run_dimensional_analysis():
    """
    The core experiment: show how adding number-theoretic DIMENSION
    to the energy function changes factorization scaling.
    """
    print("=" * 85)
    print("NUMBER-THEORETIC ENERGY: DIMENSIONAL ANALYSIS")
    print("How adding algebraic structure (dimension) changes scaling")
    print("=" * 85)

    # Generate balanced semiprimes
    semiprimes = []
    for half_bits in range(3, 14):
        p = next_prime(2**half_bits)
        q = next_prime(p + 2)
        semiprimes.append((p * q, p, q))

    # Also add some with DISTANT factors (where Fermat is slow)
    for half_bits in range(3, 10):
        p = next_prime(2**half_bits)
        q = next_prime(2**(half_bits + 2))  # q >> p
        semiprimes.append((p * q, p, q))

    semiprimes.sort(key=lambda x: x[0])

    # Run comparison
    data = dimensional_comparison(semiprimes)

    # Print results
    print(f"\n{'N':>14} {'bits':>4} {'p':>7}x{'q':>7} "
          f"{'trial':>6} {'Fermat':>7} {'QS':>6} {'dim':>4} {'winner':>7}")
    print("-" * 82)

    for d in data:
        fermat_str = f"{d.fermat_steps:7d}" if d.fermat_steps > 0 else "  FAIL"
        qs_str = f"{d.qs_steps:6d}" if d.qs_steps > 0 else " FAIL"

        print(f"{d.N:14d} {d.bits:4d} {d.p:7d}x{d.q:>7d} "
              f"{d.trial_steps:6d} {fermat_str} {qs_str} {d.qs_dimensions:4d} "
              f"{d.winner:>7}")

    # Analysis
    print(f"\n{'DIMENSIONAL INSIGHT':=^85}")
    print("""
    LEVEL 0 — Trial division (2D search, no structure):
      Searches all (a,b) pairs. O(sqrt(N)) = O(2^(n/2)). Exponential in bits.

    LEVEL 1 — Fermat (2D search, algebraic structure):
      Uses N = a^2 - b^2. Fast when p ≈ q (O(1) steps!), slow when p << q.
      Still exponential worst-case, but exploits ONE algebraic identity.

    LEVEL 2 — Quadratic Sieve (D-dimensional, D = |factor base|):
      Each smooth relation is a point in D-dimensional exponent space.
      Finding D+1 points guarantees a linear dependency → factorization.
      D ≈ exp(sqrt(ln N * ln ln N) / 2) — SUB-EXPONENTIAL.

    The dimension IS the structure. Moving from 2D to D-dimensional
    search space is what converts exponential → sub-exponential.

    For your geometric framework:
      - Octahedral states (8 = 2^3) could encode 3-bit exponent components
      - Factor base primes map to octahedral vertices
      - Smooth relations = geometric configurations with aligned vertices
      - The GF(2) null space = a GEOMETRIC SYMMETRY in the octahedral lattice
    """)

    return data


if __name__ == "__main__":
    run_dimensional_analysis()
