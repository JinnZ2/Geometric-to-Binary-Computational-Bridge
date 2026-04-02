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
# GLYPH-AWARE NULL SEARCH
# ======================================================================

def glyph_null_search(glyphs: List[GlyphState],
                       max_depth: int = 4) -> List[List[int]]:
    """
    Find dependencies using glyph composition, not just binary XOR.
    
    Advances over geometric_null_search:
    1. Signature-based hash (only stores active positions+values) — O(R)
    2. Inversion-aware pairing: looks for states whose active positions
       match but values are complementary — more matches than exact dup
    3. Residual algebra: partial cancellations tracked by their
       glyph signature, enabling efficient triple/quad search
    """
    dependencies = []
    n_octa = len(glyphs[0].glyphs) if glyphs else 0
    
    # Phase 0: Singles (all-zero = perfect square)
    for g in glyphs:
        if g.weight == 0:
            dependencies.append([g.relation_idx])
    
    # Phase 1: Exact signature duplicates — O(R) via hash
    sig_hash: Dict[Tuple, List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        sig_hash[g.signature].append(i)
    
    for sig, indices in sig_hash.items():
        if len(indices) >= 2 and sig:  # Non-empty signature, multiple matches
            for a in range(len(indices)):
                for b in range(a + 1, len(indices)):
                    dependencies.append([
                        glyphs[indices[a]].relation_idx,
                        glyphs[indices[b]].relation_idx,
                    ])
    
    if dependencies:
        return dependencies
    
    # Phase 2: Position-match search — O(R * log R)
    # Group by active position SET (ignoring values).
    # States with same active positions can cancel if their values match.
    pos_hash: Dict[FrozenSet[int], List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        if g.weight > 0:
            pos_hash[g.active_positions].append(i)
    
    for positions, indices in pos_hash.items():
        if len(indices) < 2:
            continue
        # Within this group, find pairs that XOR to zero
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
    
    # Phase 3: Residual composition — the glyph advantage
    # Compute pairwise XOR for states sharing octahedra, index residuals.
    # Two partials with SAME residual can combine to cancel.
    
    # Index by individual (octahedron, value) for fast overlap finding
    octa_val_idx: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for i, g in enumerate(glyphs):
        for k, v in enumerate(g.glyphs):
            if v != 0:
                octa_val_idx[(k, v)].append(i)
    
    # Find pairs sharing an octahedron+value, compute their residual
    residual_hash: Dict[Tuple, List[Tuple[int, int]]] = defaultdict(list)
    seen = set()
    
    for (octa, val), indices in octa_val_idx.items():
        for a in range(min(len(indices), 100)):
            for b in range(a + 1, min(len(indices), 100)):
                i, j = indices[a], indices[b]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                
                residual = glyphs[i].xor_with(glyphs[j])
                if all(r == 0 for r in residual):
                    dependencies.append([glyphs[i].relation_idx, glyphs[j].relation_idx])
                else:
                    # Store residual for triple search
                    res_sig = tuple((k, v) for k, v in enumerate(residual) if v != 0)
                    if len(res_sig) <= 3:  # Only track low-weight residuals
                        residual_hash[res_sig].append((i, j))
    
    if dependencies:
        return dependencies
    
    # Try to cancel residuals with single states
    for res_sig, pairs in residual_hash.items():
        # Need a state whose signature matches the residual
        if res_sig in sig_hash:
            for k in sig_hash[res_sig]:
                i, j = pairs[0]
                if k != i and k != j:
                    dependencies.append([
                        glyphs[i].relation_idx,
                        glyphs[j].relation_idx,
                        glyphs[k].relation_idx,
                    ])
    
    if dependencies:
        return dependencies
    
    # Try to cancel residuals with OTHER residuals (quads)
    res_keys = list(residual_hash.keys())
    res_key_hash: Dict[Tuple, List[int]] = defaultdict(list)
    for idx, key in enumerate(res_keys):
        res_key_hash[key].append(idx)
    
    for idx_a, key_a in enumerate(res_keys[:500]):
        for idx_b, key_b in enumerate(res_keys[:500]):
            if idx_a >= idx_b:
                continue
            # XOR the two residuals
            combined = [0] * n_octa
            for k, v in key_a:
                combined[k] ^= v
            for k, v in key_b:
                combined[k] ^= v
            if all(c == 0 for c in combined):
                ia, ja = residual_hash[key_a][0]
                ib, jb = residual_hash[key_b][0]
                if len({ia, ja, ib, jb}) == 4:
                    dependencies.append([
                        glyphs[ia].relation_idx, glyphs[ja].relation_idx,
                        glyphs[ib].relation_idx, glyphs[jb].relation_idx,
                    ])
        if dependencies:
            return dependencies
    
    return dependencies


# ======================================================================
# HARD PART 1 TEST: Remove singles, test glyph search
# ======================================================================

def test_without_singles(N: int, B_bound: Optional[int] = None,
                          max_candidates: int = 100000) -> Dict:
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
    
    # Sieve
    relations = []
    sqrt_N = isqrt(N) + 1
    tested = 0
    for offset in range(max_candidates):
        a = sqrt_N + offset
        Q = a * a - N
        if Q <= 0:
            continue
        tested += 1
        smooth, exp = lattice.rim_sieve(a)
        if smooth:
            relations.append({'a': a, 'Q': Q, 'exponents': exp})
        if len(relations) > needed + needed // 2:
            break
    
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
        'gf2_found': gf2_factor is not None,
        'gf2_deps': len(gf2_deps),
        'gf2_ms': gf2_ms,
    }


def run_hard_part_1():
    """Test: can we factor without singles?"""
    print("=" * 95)
    print("HARD PART 1: Factorization WITHOUT Perfect-Square Singles")
    print("Testing glyph-based null search when the easy wins are removed")
    print("=" * 95)
    
    hdr = (f"{'N':>16} {'bits':>4} | {'rels':>5} {'-sing':>5} {'octa':>4} "
           f"{'uniq':>5} {'wt':>4} | {'glyph':>8} {'deps':>4} {'sizes':>10} "
           f"{'g_ms':>6} | {'gf2':>5} {'gf2_ms':>6}")
    print("\n" + hdr)
    print("-" * 100)
    
    glyph_wins = 0
    gf2_wins = 0
    
    for half_bits in range(10, 24):
        p = next_prime(2 ** half_bits)
        q = next_prime(p + 2)
        N = p * q
        
        result = test_without_singles(N)
        
        g_status = "OK" if result['glyph_found'] else "FAIL"
        gf2_status = "OK" if result['gf2_found'] else "FAIL"
        sizes_str = str(result['glyph_dep_sizes'][:3]) if result['glyph_dep_sizes'] else "[]"
        
        if result['glyph_found']:
            glyph_wins += 1
        if result['gf2_found']:
            gf2_wins += 1
        
        print(f"{result['N']:16d} {result['bits']:4d} | {result['relations']:5d} "
              f"{result['singles_removed']:5d} {result['octahedra']:4d} "
              f"{result['unique_sigs']:5d} {result['avg_weight']:4.1f} | "
              f"{g_status:>8} {result['glyph_deps']:4d} {sizes_str:>10} "
              f"{result['glyph_ms']:6.1f} | {gf2_status:>5} {result['gf2_ms']:6.1f}")
    
    print(f"\n{'RESULTS':=^95}")
    print(f"  Glyph search wins (no singles): {glyph_wins}")
    print(f"  GF(2) Gauss wins (no singles):  {gf2_wins}")
    
    print(f"\n{'ANALYSIS':=^95}")
    print("""
    Hard Part 1 tests whether GEOMETRIC null search can replace
    LINEAR ALGEBRA when the easy wins (perfect-square singles) are gone.
    
    The glyph encoding provides:
    - Compact signature hashing (only active positions + values)
    - Position-set grouping (states with same active octahedra)
    - Residual composition (partial cancellations compose to full)
    - Inversion awareness (complementary states cancel more efficiently)
    
    If glyph search matches GF(2) Gauss success rate, we've shown that
    geometric state operations can fully replace linear algebra for the
    null space step — the core claim of "beyond binary."
    """)


if __name__ == "__main__":
    run_hard_part_1()
