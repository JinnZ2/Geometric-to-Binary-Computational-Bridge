#!/usr/bin/env python3
"""Run 99-bit factorization with scent trail resume.

Uses sparse GF(2) Gaussian elimination instead of dense matrix
(which would require 778K × 708K = 69 GB).
"""
import time, math, sys
sys.path.insert(0, '.')
from experiments.number_theoretic_energy import next_prime, compute_factor_base
from experiments.geometric_nfs import (
    OctahedralLattice, ScentTrail, sovereign_sqrt,
)

def sparse_gf2_gauss(relations, factor_base):
    """
    Sparse GF(2) Gaussian elimination.

    Each relation's parity vector has ~17 nonzero entries out of 708K.
    Uses set-based row operations: XOR = symmetric_difference.

    Memory: O(R * D) where D = avg weight ≈ 17. ~200 MB, not 69 GB.
    Time: O(R * D * reductions) ≈ O(R * D²) ≈ 225M ops. Seconds.
    """
    prime_idx = {p: i for i, p in enumerate(factor_base)}

    pivots = {}  # column_index → (cols_set, track_set)
    deps = []

    for i, rel in enumerate(relations):
        # Build sparse parity vector
        cols = set()
        for p, c in rel['exponents'].items():
            if c % 2 == 1 and p in prime_idx:
                cols.add(prime_idx[p])
        track = {i}

        # Reduce against existing pivots
        changed = True
        while changed and cols:
            changed = False
            lead = min(cols)
            if lead in pivots:
                p_cols, p_track = pivots[lead]
                cols.symmetric_difference_update(p_cols)
                track.symmetric_difference_update(p_track)
                changed = True

        if not cols:
            # Dependency found!
            deps.append(sorted(track))
            if len(deps) >= 100:  # enough deps to find a factor
                break
        else:
            # New pivot
            lead = min(cols)
            pivots[lead] = (cols, track)

        if i % 100000 == 0 and i > 0:
            print(f'  [gauss] processed {i:,}/{len(relations):,} rels, '
                  f'{len(pivots):,} pivots, {len(deps)} deps', flush=True)

    return deps

p = next_prime(2**49)
q = next_prime(p + 2)
N = p * q
bits = int(math.log2(N)) + 1

# Check trail
trail = ScentTrail.follow(N)
if trail:
    print(f'RESUMING: {len(trail["relations"]):,} rels, {trail["elapsed_s"]:.0f}s cached, '
          f'dir_offsets={trail["dir_offsets"]}')
else:
    print('No trail — starting fresh')
sys.stdout.flush()

# Build factor base + lattice
print('Building factor base...')
sys.stdout.flush()
B = max(50, int(math.exp(math.sqrt(math.log(N) * math.log(math.log(N))))))
t0 = time.time()
fb = compute_factor_base(N, B)
print(f'Factor base: {len(fb):,} primes in {time.time()-t0:.1f}s')
sys.stdout.flush()

t0 = time.time()
lattice = OctahedralLattice.build(N, fb)
print(f'Lattice: {lattice.n_octahedra:,} octahedra in {time.time()-t0:.1f}s')
sys.stdout.flush()

needed = len(fb) + 3

# Stage 1: Sieve
print(f'Need {needed:,} relations. Sieving...')
sys.stdout.flush()
t0 = time.time()
rels = lattice.octahedral_sieve(max_relations=needed + needed // 10)
sieve_time = time.time() - t0
full = sum(1 for r in rels if 'combined_a' not in r)
partial = sum(1 for r in rels if 'combined_a' in r)
print(f'Sieve: {sieve_time:.1f}s | full={full:,} partial={partial:,} total={len(rels):,}')
sys.stdout.flush()

# Stage 2: Sparse GF(2) Gaussian elimination
print('Sparse GF(2) Gauss...')
sys.stdout.flush()
t0 = time.time()
deps = sparse_gf2_gauss(rels, fb)
search_time = time.time() - t0
print(f'Found {len(deps)} dependencies in {search_time:.1f}s')
sys.stdout.flush()

if not deps:
    print('No dependencies found!')
    sys.exit(1)

# Stage 3: Extract factors
print(f'Extracting factors from {len(deps)} dependencies...')
sys.stdout.flush()
t0 = time.time()
factor = None
for dep_idx, dep in enumerate(deps):
    factor = sovereign_sqrt(N, rels, dep, fb)
    if factor is not None and 1 < factor < N:
        print(f'  Found factor on dep #{dep_idx} (weight {len(dep)})')
        break

sqrt_time = time.time() - t0

if factor and 1 < factor < N:
    p_found = min(factor, N // factor)
    q_found = N // p_found
    ScentTrail.clear(N)
    print(f'=== FACTORED {bits}b ===')
    print(f'  p = {p_found}')
    print(f'  q = {q_found}')
    print(f'  sieve={sieve_time:.1f}s search={search_time:.1f}s sqrt={sqrt_time:.1f}s')
else:
    print(f'FAILED after sieve={sieve_time:.1f}s search={search_time:.1f}s sqrt={sqrt_time:.1f}s')
    print(f'deps tried: {len(deps)}, factor: {factor}')
