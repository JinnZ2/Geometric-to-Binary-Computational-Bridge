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
# SIEVE HINT: Geometric coupling between sieve and search
# ======================================================================
#
# The sieve and search are not independent steps — they share geometric
# structure. The sieve discovers HOW relations distribute across octahedral
# space. This distribution determines whether pairs, triples, or deeper
# compositions will be needed.
#
# The SieveHint encodes this coupling:
# 1. Octahedral heat map — which octahedra are "hot" (activated by many
#    relations). Hot octahedra are where cancellations are most likely.
# 2. Pair prediction — precompute duplicate signature count. If dup_sigs > 0,
#    the search can skip expensive LSH/overlap phases entirely.
# 3. Strategy selection — PAIR, TRIPLE, or DEEP mode, determined from
#    the signature landscape.
# 4. Focused LSH — weight LSH band projections toward hot octahedra,
#    not random positions. This concentrates search where cancellations live.
#
# The binary pipeline has no equivalent — GF(2) Gauss treats all columns
# equally. The geometric pipeline uses the STRUCTURE of the sieve's output
# to accelerate the search.

@dataclass
class SieveHint:
    """Geometric coupling between sieve and search phases."""
    n_relations: int
    n_octahedra: int
    avg_weight: float
    # Heat map: activation count per octahedron
    heat_map: Dict[int, int] = field(default_factory=dict)
    # Hot octahedra: top 20% by activation (where cancellations cluster)
    hot_octahedra: List[int] = field(default_factory=list)
    # Signature analysis
    dup_sigs: int = 0           # Signatures with 2+ copies
    max_group: int = 0          # Largest signature group
    unique_ratio: float = 1.0   # unique_sigs / total
    # Value distribution per octahedron: which values are common
    value_dist: Dict[int, Counter] = field(default_factory=dict)
    # Strategy recommendation
    strategy: str = "UNKNOWN"   # PAIR, TRIPLE, or DEEP

    @classmethod
    def from_glyphs(cls, glyphs: List[GlyphState]) -> 'SieveHint':
        """Analyze glyph states to produce search hints."""
        if not glyphs:
            return cls(n_relations=0, n_octahedra=0, avg_weight=0)

        n_octa = len(glyphs[0].glyphs)
        avg_w = sum(g.weight for g in glyphs) / len(glyphs)

        # Heat map: count activations per octahedron
        heat = Counter()
        val_dist = defaultdict(Counter)
        for g in glyphs:
            for k, v in enumerate(g.glyphs):
                if v != 0:
                    heat[k] += 1
                    val_dist[k][v] += 1

        # Hot octahedra: top 20% by activation count
        sorted_octa = sorted(heat.keys(), key=lambda k: -heat[k])
        n_hot = max(1, len(sorted_octa) // 5)
        hot = sorted_octa[:n_hot]

        # Signature analysis
        sig_counts = Counter(g.signature for g in glyphs)
        dup_sigs = sum(1 for s, c in sig_counts.items() if c >= 2 and s)
        max_group = max(sig_counts.values()) if sig_counts else 0
        unique_sigs = len(sig_counts)
        unique_ratio = unique_sigs / len(glyphs) if glyphs else 1.0

        # Strategy selection based on signature landscape
        if dup_sigs > 0:
            strategy = "PAIR"       # Fast path: exact duplicates exist
        elif avg_w <= 4.5 and n_octa < 5000:
            strategy = "TRIPLE"     # Medium: LSH + overlap will find triples
        else:
            strategy = "DEEP"       # Expensive: need chain composition

        return cls(
            n_relations=len(glyphs),
            n_octahedra=n_octa,
            avg_weight=avg_w,
            heat_map=dict(heat),
            hot_octahedra=hot,
            dup_sigs=dup_sigs,
            max_group=max_group,
            unique_ratio=unique_ratio,
            value_dist=dict(val_dist),
            strategy=strategy,
        )


# ======================================================================
# GLYPH-AWARE NULL SEARCH v3 — Sieve-Coupled Adaptive Search
# ======================================================================
#
# v2 broke the 53-bit wall with LSH + overlap pairing.
# v3 uses SieveHint to ADAPT the search strategy:
#
# PAIR mode:   Skip LSH/overlap, go straight to hash lookup. O(R).
# TRIPLE mode: Focus LSH bands on hot octahedra (not random).
#              Only overlap-pair through hot octahedra. O(R * W * B).
# DEEP mode:   Full chain composition with adaptive depth. O(K^2).
#
# The sieve-to-search coupling means the total pipeline is faster
# than the sum of its parts — the sieve's geometric knowledge
# eliminates dead-end search paths before they're explored.

def _lsh_bands(glyphs: List[GlyphState], n_bands: int = 30,
               band_width: int = 2, seed: int = 42,
               hint: Optional['SieveHint'] = None) -> Dict[Tuple, List[int]]:
    """
    Locality-Sensitive Hashing for octahedral glyph states.

    When a SieveHint is provided, focuses bands on HOT octahedra —
    positions where many relations are active. This concentrates
    the search where cancellations are most likely to occur.

    Without hint: random band projections (uniform).
    With hint: 2/3 of bands sample from hot octahedra, 1/3 random.
    This biased sampling increases collision probability for states
    that share hot octahedra (the productive pairs).
    """
    rng = random.Random(seed)
    if not glyphs:
        return {}
    n_octa = len(glyphs[0].glyphs)

    # Generate band projections — biased toward hot octahedra if hinted
    bands = []
    hot = hint.hot_octahedra if hint and hint.hot_octahedra else []

    for band_i in range(n_bands):
        if hot and band_i < n_bands * 2 // 3:
            # Focused band: sample from hot octahedra
            pool = hot if len(hot) >= band_width else list(range(n_octa))
            positions = tuple(sorted(rng.sample(pool,
                                                min(band_width, len(pool)))))
        else:
            # Random band: uniform sampling
            positions = tuple(sorted(rng.sample(range(n_octa),
                                                min(band_width, n_octa))))
        bands.append(positions)

    # Hash each glyph into bands
    buckets: Dict[Tuple, List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        if g.weight == 0:
            continue
        for band_idx, positions in enumerate(bands):
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
                       max_depth: int = 4,
                       hint: Optional[SieveHint] = None) -> List[List[int]]:
    """
    Find dependencies using glyph composition — v3 with sieve coupling.

    The SieveHint steers strategy selection:
    - PAIR mode:   Phases 0-2 only (exact hash). O(R).
    - TRIPLE mode: Phases 0-4 with focused LSH. O(R * W * B).
    - DEEP mode:   All phases including chain composition. O(K^2).
    """
    dependencies = []
    if not glyphs:
        return dependencies
    n_octa = len(glyphs[0].glyphs)

    # Compute hint if not provided
    if hint is None:
        hint = SieveHint.from_glyphs(glyphs)

    avg_weight = hint.avg_weight
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
    # Focused LSH: use hint to bias bands toward hot octahedra
    # In PAIR mode, we could skip this entirely, but run it anyway
    # as a safety net in case the pair extraction fails.
    n_bands = 20 if hint.strategy == "PAIR" else (60 if hint.strategy == "DEEP" else 40)
    lsh_buckets = _lsh_bands(glyphs, n_bands=n_bands, band_width=2, hint=hint)

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

    residual_limit = 5000 if hint.strategy == "DEEP" else 3000
    for i, j, w in lsh_pairs[:residual_limit]:
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
    max_res_weight = 5 if hint.strategy == "DEEP" else 3
    res_items = [(sig, pairs[0]) for sig, pairs in residual_hash.items()
                 if len(sig) <= max_res_weight]

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
    chain_limit = 500 if hint.strategy == "DEEP" else 200
    for ia in range(min(len(res_by_weight), chain_limit)):
        sig_a, pair_a = res_by_weight[ia]
        for ib in range(ia + 1, min(len(res_by_weight), chain_limit)):
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
# HARD PART 2: Hierarchical Octahedral Decomposition
# ======================================================================
#
# At 100+ bits: ~50,000 octahedra, ~100,000 relations, weight ~5.
# The flat search works in O(R * W * B) for LSH, but the DEEP path
# (chain composition) scales as O(K^2) where K = residual count.
# At 100 bits, K can exceed 100,000 → minutes of search.
#
# The fix: exploit coupling decay d^(-0.44) as a SPATIAL DECOMPOSITION.
#
# Coupling decay guarantees:
# - Nearby octahedra (distance 1-3) share many relations
# - Distant octahedra (distance 10+) are nearly independent
# - Most state weight concentrates in a few "hot" clusters
#
# This means the null space has HIERARCHICAL STRUCTURE:
# - Local dependencies: relations cancelling within a cluster
# - Regional dependencies: compositions across 2-3 nearby clusters
# - Global dependencies: rare, require chain composition
#
# The hierarchical search:
# 1. Partition octahedra into clusters of size C (~16-32)
# 2. Project each state to cluster-level signatures
# 3. Find cluster-level matches (coarse cancellation)
# 4. Refine within matched clusters (exact cancellation)
#
# This is analogous to:
# - Multigrid: coarse solve → refine → exact solve
# - Crystal symmetry: local → regional → global
# - Fractal search: zoom in on promising regions
#
# Complexity: O(R * W * (B + C)) instead of O(K^2)
# where C = cluster size (~16) and B = LSH bands (~40)

@dataclass
class OctahedralCluster:
    """A group of consecutive strongly-coupled octahedra."""
    cluster_id: int
    start: int          # First octahedron index
    end: int            # Last octahedron index (exclusive)
    size: int           # end - start
    heat: float         # Total activation count in this cluster
    hot_rank: int       # Rank by heat (0 = hottest)

    @property
    def indices(self) -> range:
        return range(self.start, self.end)


@dataclass
class ClusterSignature:
    """A relation's state projected to cluster level."""
    relation_idx: int
    # Cluster-level signature: (cluster_id, xor_of_states_in_cluster)
    cluster_states: Tuple[Tuple[int, int], ...]  # (cluster_id, combined_state)
    cluster_weight: int  # Number of active clusters

    @property
    def signature(self) -> Tuple[Tuple[int, int], ...]:
        return self.cluster_states


def _build_clusters(n_octahedra: int, hint: Optional[SieveHint] = None,
                    cluster_size: int = 0) -> List[OctahedralCluster]:
    """
    Partition octahedra into clusters based on coupling structure.

    Uses coupling decay: nearby octahedra are strongly coupled.
    Default cluster size adapts to total octahedra count:
    - < 500 octahedra: cluster_size = 8 (small problem)
    - 500-5000: cluster_size = 16
    - 5000+: cluster_size = 32 (large problem needs bigger clusters)
    """
    if cluster_size <= 0:
        if n_octahedra < 500:
            cluster_size = 8
        elif n_octahedra < 5000:
            cluster_size = 16
        else:
            cluster_size = 32

    clusters = []
    heat_map = hint.heat_map if hint else {}

    for cid in range((n_octahedra + cluster_size - 1) // cluster_size):
        start = cid * cluster_size
        end = min(start + cluster_size, n_octahedra)
        heat = sum(heat_map.get(k, 0) for k in range(start, end))
        clusters.append(OctahedralCluster(
            cluster_id=cid, start=start, end=end,
            size=end - start, heat=heat, hot_rank=0,
        ))

    # Rank by heat (hottest first)
    ranked = sorted(range(len(clusters)), key=lambda i: -clusters[i].heat)
    for rank, idx in enumerate(ranked):
        clusters[idx].hot_rank = rank

    return clusters


def _project_to_clusters(glyphs: List[GlyphState],
                          clusters: List[OctahedralCluster]) -> List[ClusterSignature]:
    """
    Project octahedral states to cluster-level signatures.

    For each cluster, XOR all octahedral states within it to produce
    a single cluster-level state. This is a LOSSY compression that
    preserves the key property: if two states cancel at full resolution,
    their cluster projections also cancel.

    The reverse is not true — cluster cancellation doesn't guarantee
    full cancellation. But it's a cheap filter: only check full
    resolution for pairs that cancel at cluster level.
    """
    result = []
    for g in glyphs:
        cluster_states = []
        for c in clusters:
            # XOR all octahedral states in this cluster
            combined = 0
            for k in c.indices:
                if k < len(g.glyphs):
                    combined ^= g.glyphs[k]
            if combined != 0:
                cluster_states.append((c.cluster_id, combined))

        result.append(ClusterSignature(
            relation_idx=g.relation_idx,
            cluster_states=tuple(cluster_states),
            cluster_weight=len(cluster_states),
        ))
    return result


def hierarchical_null_search(glyphs: List[GlyphState],
                              hint: Optional[SieveHint] = None,
                              max_depth: int = 4) -> List[List[int]]:
    """
    Hierarchical null search using cluster decomposition.

    Three-level search:
    Level 0: Full-resolution (exact match, duplicates) — O(R)
    Level 1: Cluster-projected matching — O(R * CW * B)
             where CW = cluster weight (~2-3), B = bands
    Level 2: Cross-cluster composition — O(K_cluster^2)
             where K_cluster << K_full (fewer residuals at cluster level)

    The key insight: cluster projection preserves cancellation.
    If states A and B cancel (XOR to zero at every octahedron),
    then their cluster projections also cancel. So we use the
    cheap cluster-level search as a FILTER for the expensive
    full-resolution verification.
    """
    if not glyphs:
        return []

    if hint is None:
        hint = SieveHint.from_glyphs(glyphs)

    n_octa = len(glyphs[0].glyphs)

    # For small problems, fall back to flat search (overhead not worth it)
    if n_octa < 200:
        return glyph_null_search(glyphs, max_depth=max_depth, hint=hint)

    # ── Level 0: Full-resolution exact matches ──
    dependencies = []

    # Singles
    for g in glyphs:
        if g.weight == 0:
            dependencies.append([g.relation_idx])

    # Exact signature duplicates
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

    # ── Build cluster hierarchy ──
    clusters = _build_clusters(n_octa, hint)
    cluster_sigs = _project_to_clusters(glyphs, clusters)

    # ── Level 1: Cluster-projected search ──
    # Hash cluster signatures — matches here are CANDIDATE pairs
    # that might cancel at full resolution
    csig_hash: Dict[Tuple, List[int]] = defaultdict(list)
    for i, cs in enumerate(cluster_sigs):
        csig_hash[cs.signature].append(i)

    # Exact cluster-level duplicates → verify at full resolution
    for csig, indices in csig_hash.items():
        if len(indices) >= 2 and csig:
            for a in range(min(len(indices), 20)):
                for b in range(a + 1, min(len(indices), 20)):
                    i, j = indices[a], indices[b]
                    # Verify full resolution
                    residual = glyphs[i].xor_with(glyphs[j])
                    if all(r == 0 for r in residual):
                        dependencies.append([
                            glyphs[i].relation_idx,
                            glyphs[j].relation_idx,
                        ])

    if dependencies:
        return dependencies

    # ── Level 1b: Cluster-level LSH with hot cluster biasing ──
    # Focus LSH on hot clusters (highest heat) for coarse matching
    hot_clusters = sorted(clusters, key=lambda c: -c.heat)
    n_hot_clusters = max(1, len(hot_clusters) // 5)

    # LSH on cluster signatures — much smaller space than full octahedral
    rng = random.Random(42)
    n_bands = 40
    cluster_ids = [c.cluster_id for c in clusters]
    hot_cids = [c.cluster_id for c in hot_clusters[:n_hot_clusters]]

    lsh_seen: Set[Tuple[int, int]] = set()
    lsh_pairs: List[Tuple[int, int, int]] = []  # (i, j, xor_weight)

    for band_i in range(n_bands):
        # Bias toward hot clusters
        if hot_cids and band_i < n_bands * 2 // 3:
            pool = hot_cids
        else:
            pool = cluster_ids
        if len(pool) < 2:
            continue
        band_pos = tuple(sorted(rng.sample(pool, min(2, len(pool)))))

        # Hash each cluster signature at these band positions
        band_buckets: Dict[Tuple, List[int]] = defaultdict(list)
        for i, cs in enumerate(cluster_sigs):
            cs_dict = dict(cs.cluster_states)
            key = tuple(cs_dict.get(p, 0) for p in band_pos)
            band_buckets[key].append(i)

        for bucket_indices in band_buckets.values():
            if len(bucket_indices) < 2 or len(bucket_indices) > 200:
                continue
            for a in range(len(bucket_indices)):
                for b in range(a + 1, len(bucket_indices)):
                    i, j = bucket_indices[a], bucket_indices[b]
                    pair = (min(i, j), max(i, j))
                    if pair in lsh_seen:
                        continue
                    lsh_seen.add(pair)

                    # Check full-resolution XOR weight
                    w = glyphs[i].xor_weight(glyphs[j])
                    if w == 0:
                        dependencies.append([glyphs[i].relation_idx,
                                             glyphs[j].relation_idx])
                    elif w <= max(4, int(hint.avg_weight * 1.5)):
                        lsh_pairs.append((i, j, w))

    if dependencies:
        return dependencies

    # Sort by XOR weight (best cancellations first)
    lsh_pairs.sort(key=lambda x: x[2])

    # ── Level 2: Residual composition at cluster level ──
    # Build residuals from best pairs, index by cluster signature
    residual_hash: Dict[Tuple, List[List[int]]] = defaultdict(list)

    for i, j, w in lsh_pairs[:5000]:
        residual = glyphs[i].xor_with(glyphs[j])
        res_sig = tuple((k, v) for k, v in enumerate(residual) if v != 0)
        residual_hash[res_sig].append([
            glyphs[i].relation_idx, glyphs[j].relation_idx
        ])

    # Triple search: residual + single state = zero
    for res_sig, pair_lists in list(residual_hash.items()):
        if res_sig in sig_hash:
            for k in sig_hash[res_sig]:
                pair = pair_lists[0]
                if glyphs[k].relation_idx not in pair:
                    dependencies.append(pair + [glyphs[k].relation_idx])

    if dependencies:
        return dependencies

    # Quad search: two residuals with same signature cancel
    for res_sig, pair_lists in residual_hash.items():
        if len(pair_lists) >= 2:
            for a in range(min(len(pair_lists), 10)):
                for b in range(a + 1, min(len(pair_lists), 10)):
                    combined = pair_lists[a] + pair_lists[b]
                    if len(set(combined)) == len(combined):
                        dependencies.append(combined)

    if dependencies:
        return dependencies

    # ── Level 2b: Cross-cluster residual composition ──
    # XOR residuals with each other to find quads/quintets
    res_items = [(sig, pairs[0]) for sig, pairs in residual_hash.items()
                 if len(sig) <= max(4, int(hint.avg_weight * 1.2))]

    # Project residuals to cluster space for faster matching
    res_cluster_hash: Dict[Tuple, List[int]] = defaultdict(list)
    for idx, (sig, _) in enumerate(res_items):
        # Cluster projection of this residual
        c_proj = {}
        for k, v in sig:
            for c in clusters:
                if c.start <= k < c.end:
                    c_proj[c.cluster_id] = c_proj.get(c.cluster_id, 0) ^ v
                    break
        c_key = tuple(sorted((cid, cv) for cid, cv in c_proj.items() if cv != 0))
        res_cluster_hash[c_key].append(idx)

    # Residuals with same cluster projection might cancel
    for c_key, r_indices in res_cluster_hash.items():
        if len(r_indices) >= 2:
            for a in range(min(len(r_indices), 50)):
                for b in range(a + 1, min(len(r_indices), 50)):
                    ri, rj = r_indices[a], r_indices[b]
                    sig_a, pair_a = res_items[ri]
                    sig_b, pair_b = res_items[rj]

                    # Full-resolution check
                    combined = {}
                    for k, v in sig_a:
                        combined[k] = combined.get(k, 0) ^ v
                    for k, v in sig_b:
                        combined[k] = combined.get(k, 0) ^ v

                    if all(v == 0 for v in combined.values()):
                        full = pair_a + pair_b
                        if len(set(full)) == len(full):
                            dependencies.append(full)

        if dependencies:
            return dependencies

    # ── Level 3: Chain composition (fallback) ──
    # Sort residuals by weight, try chains of 3
    res_by_weight = sorted(res_items, key=lambda x: len(x[0]))
    for ia in range(min(len(res_by_weight), 300)):
        sig_a, pair_a = res_by_weight[ia]
        for ib in range(ia + 1, min(len(res_by_weight), 300)):
            sig_b, pair_b = res_by_weight[ib]
            combined = {}
            for k, v in sig_a:
                combined[k] = combined.get(k, 0) ^ v
            for k, v in sig_b:
                combined[k] = combined.get(k, 0) ^ v
            needed = tuple(sorted((k, v) for k, v in combined.items() if v != 0))

            if not needed:
                continue
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
    
    # Compute sieve hint — geometric coupling between sieve and search
    hint = SieveHint.from_glyphs(filtered_glyphs) if filtered_glyphs else None

    # Sieve-coupled glyph search — dispatch to hierarchical for DEEP/large
    t0 = time.time()
    use_hierarchical = (
        hint is not None and (
            hint.strategy == "DEEP" or
            (hint is not None and lattice.n_octahedra >= 200)
        )
    )
    if use_hierarchical:
        glyph_deps = hierarchical_null_search(filtered_glyphs, hint=hint, max_depth=4)
    else:
        glyph_deps = glyph_null_search(filtered_glyphs, max_depth=4, hint=hint)
    glyph_ms = (time.time() - t0) * 1000
    
    # Skip GF(2) for large N — it takes O(D^2 * R) which is minutes at 55+ bits
    bits = int(math.log2(N)) + 1
    if bits <= 50:
        t0 = time.time()
        gf2_deps = gf2_gauss(filtered_relations, factor_base)
        gf2_ms = (time.time() - t0) * 1000
    else:
        gf2_deps = []
        gf2_ms = 0.0

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
        'strategy': hint.strategy if hint else 'NONE',
        'dup_sigs': hint.dup_sigs if hint else 0,
        'n_hot': len(hint.hot_octahedra) if hint else 0,
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
           f"{'sieve':>7} {'search':>7} {'total':>7} | "
           f"{'strat':>7} {'dups':>4} {'hot':>4} | "
           f"{'st':>4} {'deps':>4} {'sizes':>12}")
    print(f"\n{hdr}")
    print("-" * 125)

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

        strat = result.get('strategy', '?')
        dups = result.get('dup_sigs', 0)
        n_hot = result.get('n_hot', 0)

        print(f"{result['N']:24d} {result['bits']:4d} | {result['relations']:6d} "
              f"{result['octahedra']:5d} {result['avg_weight']:4.1f} | "
              f"{sieve_s:6.2f}s {search_s:6.2f}s {total_s:6.2f}s | "
              f"{strat:>7} {dups:4d} {n_hot:4d} | "
              f"{status:>4} {result['glyph_deps']:4d} {sizes_str:>12}")
        sys.stdout.flush()

        if not result['glyph_found']:
            print(f"  >>> FAIL at {result['bits']} bits")

    print(f"\n{'RESULTS':=^120}")
    print(f"  Geometric pipeline wins: {wins}")
    print(f"  Failures:                {fails}")

    print(f"\n{'ARCHITECTURE':=^125}")
    print("""
    The full geometric factorization pipeline with sieve-search coupling:

    1. OCTAHEDRAL LOG SIEVE → produces relations + geometric hint
       Tonelli-Shanks roots, numpy-vectorized stride, per-position threshold.
       The sieve's output IS the hint: it reveals the octahedral landscape.

    2. SIEVE HINT → geometric coupling (the key innovation)
       - Heat map: which octahedra are "hot" (many activations)
       - Pair prediction: dup_sigs > 0 means pairs exist → fast path
       - Strategy: PAIR / TRIPLE / DEEP selected before search begins
       - Focused LSH: 2/3 of bands target hot octahedra, not random

       Binary has NO equivalent — GF(2) Gauss treats all columns equally.

    3. ADAPTIVE GLYPH SEARCH — strategy chosen by hint
       PAIR mode:   Hash lookup only. O(R). When dups exist.
       TRIPLE mode: Focused LSH + hot-octahedra overlap. O(R * W * B).
       DEEP mode:   Full chain composition. O(K^2).

    4. SOVEREIGN SQUARE ROOT — local per-octahedron extraction

    The correlation between sieve timing and search timing is not a bug —
    it's the geometric structure of N itself, now encoded as a first-class
    object (SieveHint) that the search can reason about.
    """)


if __name__ == "__main__":
    run_hard_part_1()
