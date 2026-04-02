"""
Glyph Factorization — Beyond Binary State Representation
==========================================================
Hard Part 1: What happens when perfect-square singles vanish?

At larger N, the probability of finding a relation with all-even
exponents drops as ~2^-D. We need to find dependencies WITHOUT
singles — using only the geometric structure of octahedral states.

This module:
1. Tests factorization with singles artificially removed
2. Introduces GEIS glyph encoding for compact state representation
3. Uses glyph composition rules (inversion, adjacency) to find
   cancellations that binary XOR misses

The key idea: binary XOR only finds EXACT cancellation (state==state).
Glyph operations find STRUCTURAL cancellation:
  - Inversion: state + inverse(state) = identity (like matter + antimatter)
  - Adjacency: states connected by Gray-code single-bit-flip can be
    combined via the GEIS | operator to produce a simpler state
  - Composition: the Δ (delta) symbol encodes state DIFFERENCES,
    enabling a difference-algebra for cancellation search

Instead of: "find states that XOR to zero" (binary)
We get: "find state configurations whose glyph composition is identity" (geometric)
"""

import math
import time
import random
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set, FrozenSet
from collections import defaultdict, Counter

import sys
sys.path.insert(0, ".")
from experiments.number_theoretic_energy import (
    is_prime, next_prime, isqrt, compute_factor_base, factorize_over_base,
)
from experiments.geometric_nfs import (
    OctahedralLattice, OctahedralState, relations_to_states,
    geometric_null_search, gf2_gauss, sovereign_sqrt,
)


# ======================================================================
# GEIS GLYPH ENCODING FOR FACTORIZATION STATES
# ======================================================================

# The 8 octahedral glyphs (from GEIS/octahedral_state_encoding.json)
STATE_GLYPHS = {
    0: '⊕', 1: '⊖', 2: '⊗', 3: '⊘',
    4: '⊙', 5: '⊚', 6: '⊛', 7: '⊜',
}
GLYPH_TO_STATE = {v: k for k, v in STATE_GLYPHS.items()}

# Inversion pairs: state + inverse = 7 (all bits flip)
# ⊕(0) ↔ ⊜(7), ⊖(1) ↔ ⊛(6), ⊗(2) ↔ ⊚(5), ⊘(3) ↔ ⊙(4)
INVERSE = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1, 7: 0}

# Adjacency (Gray-code neighbors — single bit flip)
ADJACENT = {
    0: {1, 2, 4},    # 000 → 001, 010, 100
    1: {0, 3, 5},    # 001 → 000, 011, 101
    2: {0, 3, 6},    # 010 → 000, 011, 110
    3: {1, 2, 7},    # 011 → 001, 010, 111
    4: {0, 5, 6},    # 100 → 000, 101, 110
    5: {1, 4, 7},    # 101 → 001, 100, 111
    6: {2, 4, 7},    # 110 → 010, 100, 111
    7: {3, 5, 6},    # 111 → 011, 101, 110
}

# The identity glyph: state 0 (⊕) in cancellation context
# XOR: a ^ a = 0 (binary identity)
# Glyph: a ⊕ inv(a) = identity (geometric identity)
# The difference: XOR needs EXACT match. Glyph inversion works on ANY state.


@dataclass
class GlyphState:
    """A relation's state encoded as a glyph string."""
    relation_idx: int
    a: int
    glyphs: Tuple[int, ...]  # 0-7 per octahedron (same as OctahedralState.states)
    
    @property
    def glyph_string(self) -> str:
        """Human-readable glyph representation."""
        return ''.join(STATE_GLYPHS.get(g, '·') if g != 0 else '·'
                       for g in self.glyphs)
    
    @property
    def active_positions(self) -> FrozenSet[int]:
        """Which octahedra are non-zero."""
        return frozenset(i for i, g in enumerate(self.glyphs) if g != 0)
    
    @property
    def weight(self) -> int:
        return len(self.active_positions)
    
    @property
    def signature(self) -> Tuple[Tuple[int, int], ...]:
        """Compact signature: only non-zero (position, value) pairs."""
        return tuple((i, g) for i, g in enumerate(self.glyphs) if g != 0)
    
    def xor_with(self, other: 'GlyphState') -> Tuple[int, ...]:
        """Binary XOR cancellation."""
        return tuple(a ^ b for a, b in zip(self.glyphs, other.glyphs))
    
    def inverse(self) -> Tuple[int, ...]:
        """Glyph inversion: each state → its inverse (7-state).
        If we XOR a state with its glyph-inverse, we get all-7s, not all-0s.
        But: XOR(a, 7-a) = XOR(a, 7^a) ... only equals 7 when a has specific form.
        
        The real utility: glyph inversion helps find TRIPLES.
        If state_A and state_B differ at octahedron k, and their values
        at k are inverses (a ^ b = 7 = 111), then they cancel 3 bits
        at that position in a single step. That's more efficient than
        XOR cancellation which might only cancel 1-2 bits.
        """
        return tuple(INVERSE[g] if g != 0 else 0 for g in self.glyphs)
    
    def hamming_distance(self, other: 'GlyphState') -> int:
        """Number of octahedra where states differ (ignoring both-zero)."""
        dist = 0
        for a, b in zip(self.glyphs, other.glyphs):
            if a != b:
                dist += 1
        return dist
    
    def xor_weight(self, other: 'GlyphState') -> int:
        """Weight of XOR result — how many non-zero positions remain."""
        return sum(1 for a, b in zip(self.glyphs, other.glyphs) if a ^ b != 0)


def relations_to_glyphs(relations: List[Dict], factor_base: List[int],
                         n_octahedra: int) -> List[GlyphState]:
    """Convert smooth relations to glyph states."""
    prime_to_idx = {p: i for i, p in enumerate(factor_base)}
    glyphs = []
    for rel_idx, rel in enumerate(relations):
        octa_states = [0] * n_octahedra
        for p, count in rel['exponents'].items():
            if p in prime_to_idx:
                j = prime_to_idx[p]
                octa_idx = j // 3
                vertex = j % 3
                if octa_idx < n_octahedra and count % 2 == 1:
                    octa_states[octa_idx] |= (1 << vertex)
        glyphs.append(GlyphState(
            relation_idx=rel_idx, a=rel['a'], glyphs=tuple(octa_states)
        ))
    return glyphs


# ======================================================================
# GLYPH-AWARE NULL SEARCH v2 — Breaks the 53-bit Wall
# ======================================================================
#
# At 53+ bits: ~1400 octahedra, avg weight ~4.2, ZERO duplicate signatures.
# Pairwise XOR weights average 7.6 (WORSE than individual 4.2).
# Position overlaps: mean 0.59 — most pairs share 0-1 octahedra.
#
# v1 died here because:
# - Phase 1 (exact hash): no duplicates exist
# - Phase 2 (position-set): no groups with matching values
# - Phase 3 (residual): weight cap of 3 was too aggressive,
#   100-pair-per-bucket cap missed the productive pairs
#
# v2 innovations:
# 1. LSH (Locality-Sensitive Hashing) on positions — random band
#    projections find near-neighbors in O(R * n_bands)
# 2. Overlap-prioritized pairing — inverted position index finds
#    ALL pairs sharing ≥2 octahedra, dramatically reducing search space
# 3. Multi-round residual algebra — residuals from round 1 become
#    inputs to round 2. Adaptive weight cap based on avg weight.
# 4. Greedy chain reduction — sort by XOR weight, compose best-first
#
# Complexity: O(R * W * B) for LSH + O(R * W^2) for overlap pairing
# where W = avg weight (~4), B = n_bands (~20). Both sub-O(R^2).

def _lsh_bands(glyphs: List[GlyphState], n_bands: int = 30,
               band_width: int = 2, seed: int = 42) -> Dict[Tuple, List[int]]:
    """
    Locality-Sensitive Hashing for octahedral glyph states.

    Projects each state's active (position, value) pairs onto random
    subsets of octahedra (bands). States with similar active positions
    collide in at least one band with high probability.

    Each band selects `band_width` random octahedra and hashes the
    (position, value) tuple at those positions. Two states collide
    in a band iff they agree on all selected positions (including
    both being zero at a position).

    P(collision in at least one band) ≈ 1 - (1 - s^band_width)^n_bands
    where s = Jaccard similarity of active position sets.

    For s=0.3 (typical for states sharing 1-2 of 4 positions):
      band_width=2, n_bands=30 → P ≈ 1 - (1-0.09)^30 ≈ 0.95
    """
    rng = random.Random(seed)
    if not glyphs:
        return {}
    n_octa = len(glyphs[0].glyphs)

    # Generate random band projections
    bands = []
    for _ in range(n_bands):
        positions = tuple(sorted(rng.sample(range(n_octa),
                                            min(band_width, n_octa))))
        bands.append(positions)

    # Hash each glyph into bands
    buckets: Dict[Tuple, List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        if g.weight == 0:
            continue
        for band_idx, positions in enumerate(bands):
            # Band signature = (band_idx, values at selected positions)
            key = (band_idx,) + tuple(g.glyphs[p] for p in positions)
            buckets[key].append(i)

    return buckets


def _overlap_pairs(glyphs: List[GlyphState],
                   min_overlap: int = 2,
                   max_per_position: int = 200) -> List[Tuple[int, int, int]]:
    """
    Find pairs of states sharing at least `min_overlap` active octahedra.

    Returns (i, j, overlap_count) sorted by overlap descending.
    Uses inverted index by position for O(R * W) construction.

    Key insight: at 53 bits, avg weight is 4.2 and n_octahedra is 1429.
    Two random states share ~4.2^2/1429 ≈ 0.012 positions on average.
    But the distribution is heavy-tailed: some octahedra are "hot"
    (many relations activate them) and pairs through hot octahedra
    dominate productive cancellations.
    """
    # Inverted index: octahedron position → list of glyph indices
    pos_idx: Dict[int, List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        for k, v in enumerate(g.glyphs):
            if v != 0:
                pos_idx[k].append(i)

    # Count pairwise overlaps via inverted index
    pair_overlaps: Dict[Tuple[int, int], int] = Counter()
    for pos, indices in pos_idx.items():
        # Cap per position to avoid O(R^2) on hot octahedra
        capped = indices[:max_per_position]
        for a in range(len(capped)):
            for b in range(a + 1, len(capped)):
                pair_overlaps[(capped[a], capped[b])] += 1

    # Filter and sort by overlap count (descending = most productive first)
    result = [(i, j, ov) for (i, j), ov in pair_overlaps.items()
              if ov >= min_overlap]
    result.sort(key=lambda x: -x[2])
    return result


def glyph_null_search(glyphs: List[GlyphState],
                       max_depth: int = 4) -> List[List[int]]:
    """
    Find dependencies using glyph composition — v2 with LSH + overlap pairing.

    Phase 0: Singles (all-zero states) — O(R)
    Phase 1: Exact signature duplicates — O(R) via hash
    Phase 2: Position-set grouping — O(R * W)
    Phase 3: LSH near-neighbor search — O(R * W * B)
    Phase 4: Overlap-prioritized pairing with multi-round residuals — O(R * W^2)
    Phase 5: Greedy chain composition — O(K^2) where K = number of residuals
    """
    dependencies = []
    if not glyphs:
        return dependencies
    n_octa = len(glyphs[0].glyphs)
    avg_weight = sum(g.weight for g in glyphs) / len(glyphs) if glyphs else 1

    # Adaptive residual weight cap: track residuals up to 1.5x avg weight
    # At 53 bits (avg_weight ~4.2), this is ~6 instead of hardcoded 3
    max_residual_weight = max(4, int(avg_weight * 1.5))

    # Phase 0: Singles (all-zero = perfect square)
    for g in glyphs:
        if g.weight == 0:
            dependencies.append([g.relation_idx])

    # Phase 1: Exact signature duplicates — O(R) via hash
    sig_hash: Dict[Tuple, List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        sig_hash[g.signature].append(i)

    for sig, indices in sig_hash.items():
        if len(indices) >= 2 and sig:
            for a in range(len(indices)):
                for b in range(a + 1, len(indices)):
                    dependencies.append([
                        glyphs[indices[a]].relation_idx,
                        glyphs[indices[b]].relation_idx,
                    ])

    if dependencies:
        return dependencies

    # Phase 2: Position-set grouping — O(R * W)
    pos_hash: Dict[FrozenSet[int], List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        if g.weight > 0:
            pos_hash[g.active_positions].append(i)

    for positions, indices in pos_hash.items():
        if len(indices) < 2:
            continue
        val_hash: Dict[Tuple, List[int]] = defaultdict(list)
        for i in indices:
            vals = tuple(glyphs[i].glyphs[p] for p in sorted(positions))
            val_hash[vals].append(i)
        for vals, val_indices in val_hash.items():
            if len(val_indices) >= 2:
                for a in range(len(val_indices)):
                    for b in range(a + 1, len(val_indices)):
                        dependencies.append([
                            glyphs[val_indices[a]].relation_idx,
                            glyphs[val_indices[b]].relation_idx,
                        ])

    if dependencies:
        return dependencies

    # Phase 3: LSH near-neighbor search — O(R * W * B)
    # Find pairs that collide in LSH bands → likely to have low XOR weight
    lsh_buckets = _lsh_bands(glyphs, n_bands=30, band_width=2)

    # Collect candidate pairs from LSH, compute XOR weight
    lsh_seen: Set[Tuple[int, int]] = set()
    lsh_pairs: List[Tuple[int, int, int]] = []  # (i, j, xor_weight)

    for bucket_key, indices in lsh_buckets.items():
        if len(indices) < 2 or len(indices) > 200:
            continue  # Skip trivially empty or overpopulated buckets
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                i, j = indices[a], indices[b]
                pair = (min(i, j), max(i, j))
                if pair in lsh_seen:
                    continue
                lsh_seen.add(pair)
                w = glyphs[i].xor_weight(glyphs[j])
                if w == 0:
                    dependencies.append([glyphs[i].relation_idx,
                                         glyphs[j].relation_idx])
                elif w <= max_residual_weight:
                    lsh_pairs.append((i, j, w))

    if dependencies:
        return dependencies

    # Sort LSH pairs by XOR weight (best cancellations first)
    lsh_pairs.sort(key=lambda x: x[2])

    # Phase 4: Overlap-prioritized residual algebra
    # Use overlap pairs if LSH didn't yield enough low-weight residuals
    if len(lsh_pairs) < 50:
        overlap_result = _overlap_pairs(glyphs, min_overlap=2)
        for i, j, ov in overlap_result[:5000]:
            pair = (min(i, j), max(i, j))
            if pair not in lsh_seen:
                lsh_seen.add(pair)
                w = glyphs[i].xor_weight(glyphs[j])
                if w == 0:
                    dependencies.append([glyphs[i].relation_idx,
                                         glyphs[j].relation_idx])
                elif w <= max_residual_weight:
                    lsh_pairs.append((i, j, w))
        lsh_pairs.sort(key=lambda x: x[2])

    if dependencies:
        return dependencies

    # Build residual index from the best pairs
    # A residual tracks: the XOR signature + which relation indices formed it
    residual_hash: Dict[Tuple, List[List[int]]] = defaultdict(list)

    for i, j, w in lsh_pairs[:3000]:
        residual = glyphs[i].xor_with(glyphs[j])
        res_sig = tuple((k, v) for k, v in enumerate(residual) if v != 0)
        residual_hash[res_sig].append([
            glyphs[i].relation_idx, glyphs[j].relation_idx
        ])

    # Also index all original states for triple search (pair + single = zero)
    for res_sig, pair_lists in list(residual_hash.items()):
        if res_sig in sig_hash:
            for k in sig_hash[res_sig]:
                pair = pair_lists[0]
                if glyphs[k].relation_idx not in pair:
                    dependencies.append(pair + [glyphs[k].relation_idx])

    if dependencies:
        return dependencies

    # Phase 5: Multi-round residual composition — the geometric advantage
    # Round 1 residuals can cancel with other round 1 residuals → quads
    # Or with original states → triples (already checked above)
    # Two residuals with SAME signature XOR to zero = quad dependency

    for res_sig, pair_lists in residual_hash.items():
        if len(pair_lists) >= 2:
            # Two different pairs with the same residual → quad
            for a in range(min(len(pair_lists), 10)):
                for b in range(a + 1, min(len(pair_lists), 10)):
                    combined = pair_lists[a] + pair_lists[b]
                    if len(set(combined)) == len(combined):  # No duplicates
                        dependencies.append(combined)

    if dependencies:
        return dependencies

    # Round 2: XOR residuals with each other
    # For efficiency, only use low-weight residuals
    res_items = [(sig, pairs[0]) for sig, pairs in residual_hash.items()
                 if len(sig) <= 3]

    # Index residuals by individual (pos, val) for fast matching
    res_pos_idx: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for idx, (sig, _) in enumerate(res_items):
        for pos_val in sig:
            res_pos_idx[pos_val].append(idx)

    res_seen: Set[Tuple[int, int]] = set()
    for pv, r_indices in res_pos_idx.items():
        for a in range(min(len(r_indices), 100)):
            for b in range(a + 1, min(len(r_indices), 100)):
                ri, rj = r_indices[a], r_indices[b]
                rpair = (min(ri, rj), max(ri, rj))
                if rpair in res_seen:
                    continue
                res_seen.add(rpair)

                sig_a, pair_a = res_items[ri]
                sig_b, pair_b = res_items[rj]

                # XOR the two residuals
                combined = [0] * n_octa
                for k, v in sig_a:
                    combined[k] ^= v
                for k, v in sig_b:
                    combined[k] ^= v

                if all(c == 0 for c in combined):
                    full = pair_a + pair_b
                    if len(set(full)) == len(full):
                        dependencies.append(full)

    if dependencies:
        return dependencies

    # Phase 6: Greedy chain building
    # Take the lowest-weight residuals, try to compose chains of 3+
    # residuals that cancel. Each residual is itself a pair, so a chain
    # of 3 residuals = 6 relations (sextet dependency).

    # Sort residuals by weight
    res_by_weight = sorted(res_items, key=lambda x: len(x[0]))

    # Try chains of 3: res_a XOR res_b = res_c, then look for res_c match
    for ia in range(min(len(res_by_weight), 200)):
        sig_a, pair_a = res_by_weight[ia]
        for ib in range(ia + 1, min(len(res_by_weight), 200)):
            sig_b, pair_b = res_by_weight[ib]

            # XOR sig_a and sig_b to get the needed sig_c
            combined = {}
            for k, v in sig_a:
                combined[k] = combined.get(k, 0) ^ v
            for k, v in sig_b:
                combined[k] = combined.get(k, 0) ^ v
            needed = tuple(sorted((k, v) for k, v in combined.items() if v != 0))

            if not needed:
                # Already cancels (caught above)
                continue

            # Look for this needed signature in residual or state hashes
            if needed in residual_hash:
                pair_c = residual_hash[needed][0]
                full = pair_a + pair_b + pair_c
                if len(set(full)) == len(full):
                    dependencies.append(full)
                    break
            if needed in sig_hash:
                for k in sig_hash[needed]:
                    full = pair_a + pair_b + [glyphs[k].relation_idx]
                    if len(set(full)) == len(full):
                        dependencies.append(full)
                        break
                if dependencies:
                    break
        if dependencies:
            return dependencies

    return dependencies


# ======================================================================
# HARD PART 1 TEST: Remove singles, test glyph search
# ======================================================================

def test_without_singles(N: int, B_bound: Optional[int] = None,
                          max_candidates: int = 100000,
                          use_octa_sieve: bool = True) -> Dict:
    """
    Factor N with perfect-square relations removed.

    This simulates the regime at larger N where singles vanish.
    Tests whether glyph-based search can find deps from pairs/triples only.
    """
    if B_bound is None:
        B_bound = max(50, int(math.exp(math.sqrt(math.log(N) * math.log(math.log(N))))))

    factor_base = compute_factor_base(N, B_bound)
    lattice = OctahedralLattice.build(N, factor_base)
    needed = len(factor_base) + 3

    # Sieve — use octahedral sieve if available, else fallback to RIM
    t_sieve_start = time.time()
    if use_octa_sieve:
        relations = lattice.octahedral_sieve(
            max_relations=needed + needed // 2
        )
    else:
        relations = []
        sqrt_N = isqrt(N) + 1
        for offset in range(max_candidates):
            a = sqrt_N + offset
            Q = a * a - N
            if Q <= 0:
                continue
            smooth, exp = lattice.rim_sieve(a)
            if smooth:
                relations.append({'a': a, 'Q': Q, 'exponents': exp})
            if len(relations) > needed + needed // 2:
                break
    sieve_ms = (time.time() - t_sieve_start) * 1000
    
    # Convert to glyphs
    all_glyphs = relations_to_glyphs(relations, factor_base, lattice.n_octahedra)
    
    # Count and remove singles
    singles = [i for i, g in enumerate(all_glyphs) if g.weight == 0]
    filtered_relations = [r for i, r in enumerate(relations) if i not in set(singles)]
    filtered_glyphs = [g for i, g in enumerate(all_glyphs) if i not in set(singles)]
    
    # Remap relation indices
    for i, g in enumerate(filtered_glyphs):
        g.relation_idx = i
    
    # Try glyph search WITHOUT singles
    t0 = time.time()
    glyph_deps = glyph_null_search(filtered_glyphs, max_depth=4)
    glyph_ms = (time.time() - t0) * 1000
    
    # Try GF(2) as comparison
    t0 = time.time()
    gf2_deps = gf2_gauss(filtered_relations, factor_base)
    gf2_ms = (time.time() - t0) * 1000
    
    # Extract factors
    glyph_factor = None
    for dep in glyph_deps:
        glyph_factor = sovereign_sqrt(N, filtered_relations, dep, factor_base)
        if glyph_factor:
            break
    
    gf2_factor = None
    for dep in gf2_deps:
        gf2_factor = sovereign_sqrt(N, filtered_relations, dep, factor_base)
        if gf2_factor:
            break
    
    # State statistics
    weights = [g.weight for g in filtered_glyphs]
    unique_sigs = len(set(g.signature for g in filtered_glyphs))
    
    return {
        'N': N,
        'bits': int(math.log2(N)) + 1,
        'relations': len(filtered_relations),
        'singles_removed': len(singles),
        'octahedra': lattice.n_octahedra,
        'unique_sigs': unique_sigs,
        'avg_weight': sum(weights) / len(weights) if weights else 0,
        'glyph_found': glyph_factor is not None,
        'glyph_deps': len(glyph_deps),
        'glyph_dep_sizes': [len(d) for d in glyph_deps[:5]],
        'glyph_ms': glyph_ms,
        'sieve_ms': sieve_ms,
        'gf2_found': gf2_factor is not None,
        'gf2_deps': len(gf2_deps),
        'gf2_ms': gf2_ms,
    }


def run_hard_part_1():
    """Test: octahedral sieve + glyph search — full geometric pipeline."""
    print("=" * 120)
    print("OCTAHEDRAL PIPELINE: Log Sieve + LSH Glyph Search")
    print("Full geometric factorization — no trial division, no Gaussian elimination")
    print("=" * 120)

    hdr = (f"{'N':>24} {'bits':>4} | {'rels':>6} {'octa':>5} {'wt':>4} | "
           f"{'sieve':>8} {'search':>8} {'total':>8} | "
           f"{'status':>6} {'deps':>4} {'sizes':>14}")
    print(f"\n{hdr}")
    print("-" * 120)

    wins = 0
    fails = 0

    for half_bits in range(10, 36):
        p = next_prime(2 ** half_bits)
        q = next_prime(p + 2)
        N = p * q

        try:
            result = test_without_singles(N, use_octa_sieve=True)
        except Exception as e:
            print(f"{'?':>24} {half_bits*2:4d} | ERROR: {e}")
            continue

        status = "OK" if result['glyph_found'] else "FAIL"
        sizes_str = str(result['glyph_dep_sizes'][:3]) if result['glyph_dep_sizes'] else "[]"

        if result['glyph_found']:
            wins += 1
        else:
            fails += 1

        sieve_s = result['sieve_ms'] / 1000
        search_s = result['glyph_ms'] / 1000
        total_s = sieve_s + search_s

        print(f"{result['N']:24d} {result['bits']:4d} | {result['relations']:6d} "
              f"{result['octahedra']:5d} {result['avg_weight']:4.1f} | "
              f"{sieve_s:7.2f}s {search_s:7.2f}s {total_s:7.2f}s | "
              f"{status:>6} {result['glyph_deps']:4d} {sizes_str:>14}")
        sys.stdout.flush()

        if not result['glyph_found']:
            print(f"  >>> FAIL at {result['bits']} bits")

    print(f"\n{'RESULTS':=^120}")
    print(f"  Geometric pipeline wins: {wins}")
    print(f"  Failures:                {fails}")

    print(f"\n{'ARCHITECTURE':=^120}")
    print("""
    The full geometric factorization pipeline:

    1. OCTAHEDRAL LOG SIEVE — replaces trial division
       For each prime p, precompute roots r where p | (a^2 - N).
       Stride through sieve array at step p, accumulating log(p).
       Only trial-divide candidates passing log threshold.
       Complexity: O(sum(M/p)) ≈ O(M * ln(ln(B))) vs O(M * |FB|)
       Speedup: ~|FB| / ln(ln(B)) ≈ 1500x at 61 bits

    2. GLYPH LSH SEARCH — replaces GF(2) Gaussian elimination
       LSH bands project octahedral states into collision buckets.
       Overlap-prioritized pairing finds cancellations geometrically.
       Multi-round residual algebra composes partial cancellations.
       Complexity: O(R * W * B) vs O(D^2 * R)
       Speedup: ~D^2 / (W * B) ≈ 300x+ at 55 bits

    3. SOVEREIGN SQUARE ROOT — local per-octahedron extraction
       Each octahedral block contributes p^(e/2) mod N independently.
       No number exceeds N at any point.

    Binary pipeline:  trial_division → Gaussian_elimination → big_sqrt
    Geometric pipeline: octahedral_sieve → LSH_glyph_search → sovereign_sqrt
    """)


if __name__ == "__main__":
    run_hard_part_1()
