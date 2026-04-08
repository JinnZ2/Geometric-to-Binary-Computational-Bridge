#!/usr/bin/env python3
"""
Geometric NFS Solver
====================
Replaces sparse GF(2) Gaussian elimination with octahedral state cancellation.
Uses the geometric null search (phases 0-3) to find dependencies among relations.
Falls back to sparse GF(2) if geometric search fails.
"""

import time
import math
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

# Import your existing modules
from experiments.number_theoretic_energy import compute_factor_base
from experiments.geometric_nfs import (
    OctahedralLattice, ScentTrail, sovereign_sqrt,
    relations_to_states, geometric_null_search
)

# ----------------------------------------------------------------------
# Sparse GF(2) Gaussian elimination (original, for fallback)
# ----------------------------------------------------------------------
def sparse_gf2_gauss(relations, factor_base):
    """Original sparse GF(2) elimination (set-based)."""
    prime_idx = {p: i for i, p in enumerate(factor_base)}
    pivots = {}
    deps = []

    for i, rel in enumerate(relations):
        cols = set()
        for p, c in rel['exponents'].items():
            if c % 2 == 1 and p in prime_idx:
                cols.add(prime_idx[p])
        track = {i}

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
            deps.append(sorted(track))
            if len(deps) >= 100:
                break
        else:
            lead = min(cols)
            pivots[lead] = (cols, track)

        if i % 100000 == 0 and i > 0:
            print(f'  [gf2] processed {i:,}/{len(relations):,} rels, '
                  f'{len(pivots):,} pivots, {len(deps)} deps', flush=True)

    return deps


# ----------------------------------------------------------------------
# 3D Cube Hashing (advanced geometric method)
# ----------------------------------------------------------------------
def build_cube(states, side=4):
    """
    Build a 3D cube (list of lists) from a list of octahedral states.
    Each state is an OctahedralState object (has .states tuple of ints).
    We pack the 3-bit values of the first `side**3` octahedra? Wait, the cube is over relations, not octahedra.
    Actually, a cube of relations: each relation has many octahedral states.
    To make a cube of octahedral states, we need to take a slice of the state vector across a fixed octahedron index.
    Simpler: treat each relation's full state vector as a row in a 3D array? That's messy.
    For now, we skip cube hashing and rely on geometric_null_search.
    """
    # Placeholder – not used in this version
    return None


# ----------------------------------------------------------------------
# Main geometric solver
# ----------------------------------------------------------------------
def geometric_nfs_solver(relations, factor_base, n_octahedra, use_fallback=True):
    """
    Find dependencies using geometric null search (phases 0-3).
    If none found and use_fallback=True, fall back to sparse GF(2).
    Returns (deps, method_name, time_seconds).
    """
    # Convert relations to octahedral states
    print("  Converting relations to octahedral states...", flush=True)
    t0 = time.time()
    states = relations_to_states(relations, factor_base, n_octahedra)
    conv_time = time.time() - t0
    print(f"    Converted {len(states)} states in {conv_time:.1f}s", flush=True)

    # Geometric null search
    print("  Running geometric null search (phases 0-3)...", flush=True)
    t0 = time.time()
    deps = geometric_null_search(states, max_depth=4)
    geo_time = time.time() - t0
    print(f"    Geometric search found {len(deps)} dependencies in {geo_time:.1f}s", flush=True)

    if deps:
        return deps, "geometric", geo_time + conv_time
    elif use_fallback:
        print("  Geometric search found nothing, falling back to sparse GF(2)...", flush=True)
        t0 = time.time()
        deps = sparse_gf2_gauss(relations, factor_base)
        gf2_time = time.time() - t0
        print(f"    GF(2) found {len(deps)} dependencies in {gf2_time:.1f}s", flush=True)
        return deps, "gf2_fallback", gf2_time + conv_time
    else:
        return [], "geometric_none", geo_time + conv_time


# ----------------------------------------------------------------------
# Standalone test (if run directly)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # This part is for testing – you would normally import and call.
    # For demonstration, we simulate loading a trail and running the solver.
    import sys
    import math

    # Example: factor a 71-bit number quickly (for testing)
    from experiments.number_theoretic_energy import next_prime
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

    # Sieve for relations (small example)
    print("Sieving for relations (small scale)...")
    rels = lattice.octahedral_sieve(max_relations=len(fb) + 10, sieve_size=50000)
    print(f"Found {len(rels)} relations")

    # Run geometric solver
    deps, method, elapsed = geometric_nfs_solver(rels, fb, lattice.n_octahedra, use_fallback=True)
    print(f"\nMethod: {method}, time: {elapsed:.1f}s, dependencies: {len(deps)}")
    if deps:
        print("First dependency indices:", deps[0][:10])
        # Try to extract factor (optional)
        factor = sovereign_sqrt(N, rels, deps[0], fb)
        if factor and 1 < factor < N:
            print(f"Factor found: {factor}")
        else:
            print("No factor extracted from first dependency")
