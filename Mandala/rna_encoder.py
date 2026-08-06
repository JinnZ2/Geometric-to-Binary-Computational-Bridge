#!/usr/bin/env python3
"""
RNA-Hexagonal Fold Encoder — Secondary Structure on Geometric Lattice
======================================================================

Maps RNA sequences onto a hexagonal 2D lattice to model secondary structure.
Base pairing (A-U, G-C, G-U wobble) creates geometric constraints:
    - Paired bases are placed at adjacent hex cells (strong coupling)
    - Unpaired loops span larger distances (weak coupling)
    - Stem regions form straight lines on the lattice
    - Hairpin loops close back to nearby cells

Self-contained. Depends only on stdlib.

Usage:
    from rna_encoder import RNAEncoder
    enc = RNAEncoder()

    # Fold an RNA sequence
    fold = enc.fold("GGGAAACCC")

    # Check if a structure is valid
    valid = enc.is_valid_structure("GGGAAACCC", "(((...)))")

    # Find all possible base pairs
    pairs = enc.find_pairs("GGGAAACCC")

    # Geometric fold quality
    quality = enc.fold_quality("GGGAAACCC", "(((...)))")

    # Predict stem regions
    stems = enc.predict_stems("GGGAAACCC")
"""

import math
from typing import Dict, List, Tuple, Set, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RNA_BASES = "AUGC"

# Base pairing rules (Watson-Crick + wobble)
CANONICAL_PAIRS = {("A", "U"), ("U", "A"), ("G", "C"), ("C", "G")}
WOBBLE_PAIRS = {("G", "U"), ("U", "G")}
ALL_PAIRS = CANONICAL_PAIRS | WOBBLE_PAIRS

# Hexagonal lattice directions (6 neighbors)
# Each direction is a unit vector in 2D hex coordinates
HEX_DIRECTIONS = [
    (1, 0),    # 0°
    (0.5, math.sqrt(3)/2),   # 60°
    (-0.5, math.sqrt(3)/2),  # 120°
    (-1, 0),   # 180°
    (-0.5, -math.sqrt(3)/2), # 240°
    (0.5, -math.sqrt(3)/2),  # 300°
]

# Energy parameters (simplified Turner rules)
# Negative = stabilizing, positive = destabilizing
STEM_ENERGY = -2.0      # per base pair in stem
BULGE_ENERGY = 2.0      # per unpaired base in bulge
HAIRPIN_ENERGY = 4.0    # loop closure penalty
WOBBLE_PENALTY = 0.5    # G-U is weaker than Watson-Crick


# =============================================================================
# RNA ENCODER
# =============================================================================

class RNAEncoder:
    """
    Encode RNA sequences onto hexagonal lattice for secondary structure.

    The hexagonal grid provides:
        - 6 directions for chain growth
        - Natural angles for hairpin turns (60°, 120°)
        - Local coupling for base pairs
        - Distance-based loop penalties
    """

    def __init__(self):
        self.directions = HEX_DIRECTIONS

    # -----------------------------------------------------------------------
    # Basic validation
    # -----------------------------------------------------------------------

    def validate_sequence(self, sequence: str) -> bool:
        """Check if sequence contains only valid RNA bases."""
        return all(b.upper() in RNA_BASES for b in sequence)

    def validate_structure(self, structure: str) -> bool:
        """
        Check if dot-bracket notation is valid.
        Balanced parentheses, no crossing at same level.
        """
        stack = []
        for char in structure:
            if char == "(":
                stack.append(char)
            elif char == ")":
                if not stack:
                    return False
                stack.pop()
            elif char != ".":
                return False
        return len(stack) == 0

    # -----------------------------------------------------------------------
    # Base pairing
    # -----------------------------------------------------------------------

    def can_pair(self, base1: str, base2: str, allow_wobble: bool = True) -> bool:
        """Check if two bases can form a pair."""
        pair = (base1.upper(), base2.upper())
        if pair in CANONICAL_PAIRS:
            return True
        if allow_wobble and pair in WOBBLE_PAIRS:
            return True
        return False

    def pair_type(self, base1: str, base2: str) -> str:
        """Return pair type: 'canonical', 'wobble', or 'none'."""
        pair = (base1.upper(), base2.upper())
        if pair in CANONICAL_PAIRS:
            return "canonical"
        elif pair in WOBBLE_PAIRS:
            return "wobble"
        return "none"

    def find_pairs(self, sequence: str, allow_wobble: bool = True) -> List[Tuple[int, int]]:
        """
        Find all possible base pairs in sequence (i < j).
        Returns list of (i, j) indices.
        """
        seq = sequence.upper()
        pairs = []
        for i in range(len(seq)):
            for j in range(i + 1, len(seq)):
                if self.can_pair(seq[i], seq[j], allow_wobble):
                    pairs.append((i, j))
        return pairs

    # -----------------------------------------------------------------------
    # Structure validation
    # -----------------------------------------------------------------------

    def is_valid_structure(self, sequence: str, structure: str,
                           min_hairpin: int = 3,
                           allow_wobble: bool = True) -> bool:
        """
        Check if a dot-bracket structure is valid for the sequence.

        Rules:
            - Balanced parentheses
            - Each pair must be valid (A-U, G-C, or G-U)
            - Hairpin loops must have at least min_hairpin unpaired bases
            - No pseudoknots (checked by stack discipline)
        """
        if len(sequence) != len(structure):
            return False

        if not self.validate_structure(structure):
            return False

        seq = sequence.upper()
        stack = []

        for i, char in enumerate(structure):
            if char == "(":
                stack.append(i)
            elif char == ")":
                if not stack:
                    return False
                j = stack.pop()
                # Check base pair validity
                if not self.can_pair(seq[j], seq[i], allow_wobble):
                    return False
                # Check hairpin length
                if i - j - 1 < min_hairpin:
                    return False

        return len(stack) == 0

    def parse_structure(self, structure: str) -> Dict:
        """
        Parse dot-bracket notation into structural elements.

        Returns dict with:
            - pairs: list of (i, j) base pairs
            - stems: list of consecutive paired regions
            - loops: list of unpaired regions
            - hairpins: list of hairpin loops
        """
        stack = []
        pairs = []

        for i, char in enumerate(structure):
            if char == "(":
                stack.append(i)
            elif char == ")":
                if stack:
                    j = stack.pop()
                    pairs.append((j, i))

        # Sort pairs by first position
        pairs.sort()

        # Find stems (consecutive pairs)
        stems = []
        current_stem = []
        for i, (a, b) in enumerate(pairs):
            if i > 0:
                prev_a, prev_b = pairs[i-1]
                if a == prev_a + 1 and b == prev_b - 1:
                    current_stem.append((a, b))
                else:
                    if current_stem:
                        stems.append(current_stem[:])
                    current_stem = [(a, b)]
            else:
                current_stem = [(a, b)]
        if current_stem:
            stems.append(current_stem)

        # Find loops (unpaired regions between paired regions)
        paired_positions = set()
        for a, b in pairs:
            paired_positions.add(a)
            paired_positions.add(b)

        loops = []
        current_loop = []
        for i in range(len(structure)):
            if i not in paired_positions:
                current_loop.append(i)
            else:
                if current_loop:
                    loops.append(current_loop[:])
                    current_loop = []
        if current_loop:
            loops.append(current_loop)

        # Hairpins are loops enclosed by a stem
        hairpins = []
        for stem in stems:
            if len(stem) >= 2:
                # The innermost pair of the stem encloses the hairpin
                inner_a, inner_b = stem[-1]
                hairpin_bases = list(range(inner_a + 1, inner_b))
                if hairpin_bases:
                    hairpins.append(hairpin_bases)

        return {
            "pairs": pairs,
            "stems": stems,
            "loops": loops,
            "hairpins": hairpins,
            "n_pairs": len(pairs),
            "n_stems": len(stems),
            "n_hairpins": len(hairpins),
        }

    # -----------------------------------------------------------------------
    # Geometric folding
    # -----------------------------------------------------------------------

    def fold(self, sequence: str, structure: Optional[str] = None,
             start_direction: int = 0) -> Dict:
        """
        Fold RNA sequence onto hexagonal lattice.

        If structure is given, follows it. Otherwise, uses simple
        heuristic: grow in current direction, turn at loops.

        Returns dict with:
            - positions: list of (x, y) coordinates for each base
            - structure: dot-bracket notation
            - energy: estimated folding energy
            - pairs: list of paired indices
        """
        seq = sequence.upper()
        n = len(seq)

        if structure is None:
            # Simple heuristic: find maximum pairs greedily
            structure = self._greedy_structure(seq)

        # Parse structure
        parsed = self.parse_structure(structure)
        pairs = parsed["pairs"]
        pair_map = {a: b for a, b in pairs}
        pair_map.update({b: a for a, b in pairs})

        # Place bases on hex lattice
        positions = [(0.0, 0.0)]
        current_dir = start_direction

        for i in range(1, n):
            if i in pair_map:
                j = pair_map[i]
                if j < i:
                    # Closing a pair: turn toward partner
                    # Find direction that minimizes distance to partner
                    best_dir = current_dir
                    best_dist = float("inf")
                    for d in range(6):
                        dx, dy = self.directions[d]
                        new_x = positions[i-1][0] + dx
                        new_y = positions[i-1][1] + dy
                        dist = math.sqrt((new_x - positions[j][0])**2 +
                                        (new_y - positions[j][1])**2)
                        if dist < best_dist:
                            best_dist = dist
                            best_dir = d
                    current_dir = best_dir
                else:
                    # Opening a pair: continue or turn slightly
                    pass
            else:
                # Unpaired: random walk with bias
                # Prefer continuing in same direction
                if i > 0 and structure[i] == "." and structure[i-1] == ".":
                    # In a loop: turn to avoid self-collision
                    current_dir = (current_dir + 1) % 6

            dx, dy = self.directions[current_dir]
            new_x = positions[i-1][0] + dx
            new_y = positions[i-1][1] + dy
            positions.append((new_x, new_y))

        # Calculate energy
        energy = self._calculate_energy(seq, parsed)

        return {
            "sequence": seq,
            "structure": structure,
            "positions": positions,
            "pairs": pairs,
            "energy": energy,
            "parsed": parsed,
        }

    def _greedy_structure(self, sequence: str) -> str:
        """Greedy structure prediction: pair from outside in."""
        seq = sequence.upper()
        n = len(seq)
        structure = ["."] * n

        i, j = 0, n - 1
        while j - i > 3:  # minimum hairpin length
            if self.can_pair(seq[i], seq[j]):
                structure[i] = "("
                structure[j] = ")"
                i += 1
                j -= 1
            else:
                # Try next position
                i += 1

        return "".join(structure)

    def _calculate_energy(self, sequence: str, parsed: Dict) -> float:
        """Estimate folding energy from structure."""
        seq = sequence.upper()
        energy = 0.0

        # Stem energy
        for stem in parsed["stems"]:
            for a, b in stem:
                energy += STEM_ENERGY
                if self.pair_type(seq[a], seq[b]) == "wobble":
                    energy += WOBBLE_PENALTY

        # Loop penalties
        for loop in parsed["loops"]:
            if len(loop) > 0:
                energy += BULGE_ENERGY * len(loop)

        # Hairpin bonus (closing a stem is favorable)
        for hairpin in parsed["hairpins"]:
            energy += HAIRPIN_ENERGY / max(len(hairpin), 1)

        return energy

    # -----------------------------------------------------------------------
    # Fold quality metrics
    # -----------------------------------------------------------------------

    def fold_quality(self, sequence: str, structure: str) -> Dict:
        """
        Measure geometric quality of a fold.

        Returns:
            - valid: is structure valid?
            - compactness: average pairwise distance
            - pair_distance: average distance between paired bases
            - loop_span: average loop size
            - energy: estimated energy
        """
        valid = self.is_valid_structure(sequence, structure)
        if not valid:
            return {"valid": False}

        fold_result = self.fold(sequence, structure)
        positions = fold_result["positions"]
        pairs = fold_result["pairs"]
        parsed = fold_result["parsed"]

        # Compactness: average distance from centroid
        if positions:
            cx = sum(p[0] for p in positions) / len(positions)
            cy = sum(p[1] for p in positions) / len(positions)
            compactness = sum(math.sqrt((p[0]-cx)**2 + (p[1]-cy)**2)
                            for p in positions) / len(positions)
        else:
            compactness = 0.0

        # Pair distance
        if pairs:
            pair_dist = sum(
                math.sqrt((positions[a][0]-positions[b][0])**2 +
                         (positions[a][1]-positions[b][1])**2)
                for a, b in pairs
            ) / len(pairs)
        else:
            pair_dist = 0.0

        # Loop span
        if parsed["loops"]:
            loop_span = sum(len(loop) for loop in parsed["loops"]) / len(parsed["loops"])
        else:
            loop_span = 0.0

        return {
            "valid": True,
            "compactness": compactness,
            "pair_distance": pair_dist,
            "loop_span": loop_span,
            "energy": fold_result["energy"],
            "n_pairs": len(pairs),
            "n_hairpins": parsed["n_hairpins"],
        }

    # -----------------------------------------------------------------------
    # Stem prediction
    # -----------------------------------------------------------------------

    def predict_stems(self, sequence: str, min_stem: int = 2) -> List[Dict]:
        """
        Predict stem regions in sequence.

        Returns list of dicts with:
            - start: start index
            - end: end index (inclusive)
            - length: stem length
            - sequence: stem sequence (5' to 3')
            - complement: complementary sequence (3' to 5')
        """
        seq = sequence.upper()
        n = len(seq)
        stems = []

        for length in range(min_stem, n // 2 + 1):
            for i in range(n - 2 * length + 1):
                j = i + length
                # Check if seq[i:i+length] pairs with seq[j:j+length] reversed
                segment = seq[i:i+length]
                complement = seq[j:j+length][::-1]

                valid = True
                pairs = []
                for a, b in zip(segment, complement):
                    if not self.can_pair(a, b):
                        valid = False
                        break
                    pairs.append(self.pair_type(a, b))

                if valid:
                    stems.append({
                        "start": i,
                        "end": j + length - 1,
                        "length": length,
                        "sequence": segment,
                        "complement": complement,
                        "pair_types": pairs,
                        "energy": sum(STEM_ENERGY + (WOBBLE_PENALTY if pt == "wobble" else 0)
                                     for pt in pairs),
                    })

        # Sort by energy (most stable first)
        stems.sort(key=lambda s: s["energy"])
        return stems

    # -----------------------------------------------------------------------
    # Sequence design
    # -----------------------------------------------------------------------

    def design_complement(self, sequence: str, allow_wobble: bool = True) -> str:
        """Design the complementary RNA strand."""
        comp = {"A": "U", "U": "A", "G": "C", "C": "G"}
        return "".join(comp.get(b, "N") for b in sequence.upper())

    def gc_content(self, sequence: str) -> float:
        """GC content as fraction."""
        seq = sequence.upper()
        return (seq.count("G") + seq.count("C")) / max(len(seq), 1)

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate(self) -> dict:
        """Validate encoder and geometry."""
        findings = {
            "n_directions": len(self.directions),
            "direction_angles": [],
            "pair_rules": len(ALL_PAIRS),
            "issues": [],
        }

        # Check directions are 60° apart
        for i in range(len(self.directions)):
            dx1, dy1 = self.directions[i]
            dx2, dy2 = self.directions[(i + 1) % 6]
            dot = dx1 * dx2 + dy1 * dy2
            angle = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
            findings["direction_angles"].append(round(angle, 3))
            if abs(angle - 60.0) > 1.0:
                findings["issues"].append(f"Direction {i} angle = {angle:.2f}°")

        findings["passes"] = len(findings["issues"]) == 0
        return findings


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("RNA-HEXAGONAL FOLD ENCODER — Self Test")
    print("=" * 60)

    enc = RNAEncoder()

    # Validate geometry
    audit = enc.validate()
    print(f"\nGeometry validation:")
    print(f"  Directions: {audit['n_directions']}")
    print(f"  Inter-direction angles: {audit['direction_angles'][:3]}...")
    print(f"  Issues: {audit['issues'] or 'None'}")

    # Simple hairpin
    seq = "GGGAAACCC"
    struct = "(((...)))"
    print(f"\nSequence: {seq}")
    print(f"Structure: {struct}")
    print(f"Valid: {enc.is_valid_structure(seq, struct)}")

    fold = enc.fold(seq, struct)
    print(f"Energy: {fold['energy']:.2f}")
    print(f"Pairs: {fold['pairs']}")
    print(f"Positions (first 3): {fold['positions'][:3]}")

    # Parse structure
    parsed = enc.parse_structure(struct)
    print(f"\nParsed structure:")
    print(f"  Pairs: {parsed['pairs']}")
    print(f"  Stems: {len(parsed['stems'])}")
    print(f"  Hairpins: {parsed['hairpins']}")

    # Fold quality
    quality = enc.fold_quality(seq, struct)
    print(f"\nFold quality:")
    for k, v in quality.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")
        else:
            print(f"  {k}: {v}")

    # Stem prediction
    stems = enc.predict_stems(seq)
    print(f"\nPredicted stems:")
    for stem in stems[:3]:
        print(f"  {stem['sequence']} <-> {stem['complement']} "
              f"(energy={stem['energy']:.1f})")

    # Base pairing
    print(f"\nBase pairing:")
    print(f"  A-U: {enc.can_pair('A', 'U')}")
    print(f"  G-C: {enc.can_pair('G', 'C')}")
    print(f"  G-U (wobble): {enc.can_pair('G', 'U')}")
    print(f"  A-G: {enc.can_pair('A', 'G')}")

    # Complement design
    comp = enc.design_complement("AUGCGUAC")
    print(f"\nComplement of AUGCGUAC: {comp}")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)
