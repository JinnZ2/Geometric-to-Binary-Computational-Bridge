#!/usr/bin/env python3
# STATUS: infrastructure -- linear vs golden-ratio candidate ordering benchmark
"""
Benchmark: Linear vs Golden‑ratio candidate ordering for NFS relation collection.
Uses an existing OctahedralLattice and tests both orders for a fixed time.
"""

import time
import math
from experiments.number_theoretic_energy import next_prime, compute_factor_base
from experiments.geometric_nfs import OctahedralLattice

# ----------------------------------------------------------------------
# Candidate generators
# ----------------------------------------------------------------------
def linear_candidates(limit):
    """Simple 1,2,3,...,limit"""
    for a in range(1, limit + 1):
        yield a

def golden_candidates(limit):
    """
    Permutation of 1..limit using low‑discrepancy golden ratio sequence.
    Uses the fractional part of n * φ to map to [1, limit].
    Precomputes the permutation once per limit to avoid collisions.
    """
    phi = (1 + math.sqrt(5)) / 2
    # Pre‑compute the ordering (O(limit log limit) due to collisions, but acceptable for small limits)
    # More efficient: generate and deduplicate until we have limit numbers.
    seen = set()
    order = []
    n = 0
    while len(order) < limit:
        n += 1
        x = (n * phi) % 1
        a = int(x * limit) + 1
        if a not in seen:
            seen.add(a)
            order.append(a)
    for a in order:
        yield a

# ----------------------------------------------------------------------
# Sieve wrapper using a candidate generator
# ----------------------------------------------------------------------
def sieve_with_order(lattice, candidate_gen, max_relations, time_limit_sec):
    """
    Collect relations by testing candidates from candidate_gen using lattice.rim_sieve().
    Stops when either max_relations reached or time_limit exceeded.
    Returns (relations, elapsed_time, candidates_tested).
    """
    relations = []
    candidates_tested = 0
    start = time.time()
    sqrt_N = lattice.N
    # We need an offset? The generator yields a values directly, not offsets.
    # We'll assume candidate_gen yields integers starting from 1, and we set a = sqrt_N + offset
    # But to make it fair, we'll let the generator yield absolute a values? That would require knowing the range.
    # Simpler: the generator yields offsets from sqrt_N.
    # Let's adapt golden_candidates to yield offsets in the range 0..max_offset.
    # We'll regenerate the generator with limit = max_offset.
    max_offset = 1000000  # generous upper bound
    # Re‑create generator with correct limit
    if candidate_gen == linear_candidates:
        gen = linear_candidates(max_offset)
    else:
        gen = golden_candidates(max_offset)

    for offset in gen:
        if time.time() - start > time_limit_sec:
            break
        if len(relations) >= max_relations:
            break
        a = sqrt_N + offset
        Q = a * a - lattice.N
        if Q <= 0:
            continue
        candidates_tested += 1
        smooth, exponents = lattice.rim_sieve(a)
        if smooth:
            relations.append({'a': a, 'Q': Q, 'exponents': exponents})
    elapsed = time.time() - start
    return relations, elapsed, candidates_tested

# ----------------------------------------------------------------------
# Benchmark
# ----------------------------------------------------------------------
def main():
    # Create a test semiprime (71 bits for quick testing)
    p = next_prime(2**35)
    q = next_prime(p + 2)
    N = p * q
    bits = int(math.log2(N)) + 1
    print(f"Test N = {N} ({bits} bits)")

    # Build factor base
    B = max(50, int(math.exp(math.sqrt(math.log(N) * math.log(math.log(N))))))
    fb = compute_factor_base(N, B)
    print(f"Factor base size: {len(fb)}")

    # Build octahedral lattice
    lattice = OctahedralLattice.build(N, fb)
    print(f"Octahedra: {lattice.n_octahedra}")

    # Parameters
    MAX_RELATIONS = len(fb) + 10
    TIME_LIMIT = 30.0  # seconds

    # Run linear order
    print("\n--- Linear order ---")
    rels_lin, elapsed_lin, cand_lin = sieve_with_order(lattice, linear_candidates, MAX_RELATIONS, TIME_LIMIT)
    print(f"Relations: {len(rels_lin)} in {elapsed_lin:.2f}s, candidates tested: {cand_lin}")

    # Run golden order
    print("\n--- Golden ratio order ---")
    rels_gold, elapsed_gold, cand_gold = sieve_with_order(lattice, golden_candidates, MAX_RELATIONS, TIME_LIMIT)
    print(f"Relations: {len(rels_gold)} in {elapsed_gold:.2f}s, candidates tested: {cand_gold}")

    # Compare
    if elapsed_lin > 0 and elapsed_gold > 0:
        rate_lin = len(rels_lin) / elapsed_lin
        rate_gold = len(rels_gold) / elapsed_gold
        print("\n--- Summary ---")
        print(f"Linear rate: {rate_lin:.2f} rels/sec")
        print(f"Golden rate: {rate_gold:.2f} rels/sec")
        if rate_gold > rate_lin:
            print("Golden ratio order is faster for this test.")
        else:
            print("Linear order is faster for this test.")

if __name__ == "__main__":
    main()
