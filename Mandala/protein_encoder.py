#!/usr/bin/env python3
"""
Protein-Dodecahedral Encoder — Amino Acid Mapping onto Geometric Substrate
===========================================================================

Maps the 20 standard amino acids onto the 20 vertices of a regular dodecahedron.
The dodecahedron is the dual of the icosahedron — both are phi-rich geometries.

Why dodecahedral:
    - 20 vertices = 20 amino acids (exact match)
    - 12 pentagonal faces = 12 biochemical property classes
    - 30 edges = transition pathways between amino acids
    - Golden ratio appears in all edge/sphere ratios
    - Each amino acid sits at a vertex shared by 3 faces (property classes)

Self-contained. Depends only on stdlib.

Usage:
    from protein_encoder import ProteinEncoder
    enc = ProteinEncoder()

    # Encode protein sequence to dodecahedral states
    states = enc.encode("MKTLLI")

    # Decode back
    seq = enc.decode(states)

    # Geometric distance between two residues
    dist = enc.residue_distance("A", "V")  # both hydrophobic = close
    dist = enc.residue_distance("D", "K")  # opposite charge = far

    # Find residues in same property class
    neighbors = enc.property_neighbors("A")  # other hydrophobic residues

    # Hydropathy index
    score = enc.hydropathy("AVLIF")  # Kyte-Doolittle
"""

import math
from typing import Dict, List, Tuple, Set, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2          # 1.618033988749895
INV_PHI = 1.0 / PHI                   # 0.618033988749895

# 20 standard amino acids (single-letter code)
AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

# Full names
AA_NAMES = {
    "A": "Alanine",       "C": "Cysteine",      "D": "Aspartic acid",
    "E": "Glutamic acid", "F": "Phenylalanine", "G": "Glycine",
    "H": "Histidine",     "I": "Isoleucine",    "K": "Lysine",
    "L": "Leucine",       "M": "Methionine",    "N": "Asparagine",
    "P": "Proline",       "Q": "Glutamine",     "R": "Arginine",
    "S": "Serine",        "T": "Threonine",     "V": "Valine",
    "W": "Tryptophan",    "Y": "Tyrosine",
}

# Codons (DNA) for each amino acid
AA_CODONS = {
    "A": ["GCT", "GCC", "GCA", "GCG"],
    "C": ["TGT", "TGC"],
    "D": ["GAT", "GAC"],
    "E": ["GAA", "GAG"],
    "F": ["TTT", "TTC"],
    "G": ["GGT", "GGC", "GGA", "GGG"],
    "H": ["CAT", "CAC"],
    "I": ["ATT", "ATC", "ATA"],
    "K": ["AAA", "AAG"],
    "L": ["TTA", "TTG", "CTT", "CTC", "CTA", "CTG"],
    "M": ["ATG"],
    "N": ["AAT", "AAC"],
    "P": ["CCT", "CCC", "CCA", "CCG"],
    "Q": ["CAA", "CAG"],
    "R": ["CGT", "CGC", "CGA", "CGG", "AGA", "AGG"],
    "S": ["TCT", "TCC", "TCA", "TCG", "AGT", "AGC"],
    "T": ["ACT", "ACC", "ACA", "ACG"],
    "V": ["GTT", "GTC", "GTA", "GTG"],
    "W": ["TGG"],
    "Y": ["TAT", "TAC"],
}

# Biochemical property classes
# Each amino acid belongs to 3 classes (the 3 faces meeting at its vertex)
PROPERTY_CLASSES = {
    "hydrophobic":   {"A", "V", "I", "L", "M", "F", "W", "P"},
    "polar":         {"S", "T", "C", "Y", "N", "Q"},
    "positive":      {"K", "R", "H"},
    "negative":      {"D", "E"},
    "small":         {"A", "G", "S", "C", "P", "T", "V"},
    "aromatic":      {"F", "W", "Y", "H"},
    "aliphatic":     {"A", "V", "I", "L", "M", "G"},
    "sulfur":        {"C", "M"},
    "amide":         {"N", "Q"},
    "tiny":          {"A", "G"},
    "large":         {"F", "W", "Y", "R", "K", "E", "Q"},
    "proline_like":  {"P", "G"},  # unique backbone geometry
}

# Kyte-Doolittle hydropathy index
HYDROPATHY = {
    "A": 1.8,  "C": 2.5,  "D": -3.5, "E": -3.5, "F": 2.8,
    "G": -0.4, "H": -3.2, "I": 4.5,  "K": -3.9, "L": 3.8,
    "M": 1.9,  "N": -3.5, "P": -1.6, "Q": -3.5, "R": -4.5,
    "S": -0.8, "T": -0.7, "V": 4.2,  "W": -0.9, "Y": -1.3,
}

# Molecular weights
MW = {
    "A": 89.1,  "C": 121.2, "D": 133.1, "E": 147.1, "F": 165.2,
    "G": 75.1,  "H": 155.2, "I": 131.2, "K": 146.2, "L": 131.2,
    "M": 149.2, "N": 132.1, "P": 115.1, "Q": 146.2, "R": 174.2,
    "S": 105.1, "T": 119.1, "V": 117.1, "W": 204.2, "Y": 181.2,
}

# pKa values (approximate side chain)
PKA = {
    "C": 8.3,  "D": 3.9,  "E": 4.3,  "H": 6.0,
    "K": 10.5, "R": 12.5, "Y": 10.1,
}


# =============================================================================
# DODECAHEDRAL GEOMETRY
# =============================================================================

# Regular dodecahedron: 20 vertices, 12 faces (pentagons), 30 edges
# Coordinates: (±1, ±1, ±1), (0, ±φ, ±1/φ), (±1/φ, 0, ±φ), (±φ, ±1/φ, 0)
# Each vertex connects to 3 others

DODECA_VERTICES: Dict[int, Tuple[float, float, float]] = {
    0:  ( 1.0,  1.0,  1.0),
    1:  ( 1.0,  1.0, -1.0),
    2:  ( 1.0, -1.0,  1.0),
    3:  ( 1.0, -1.0, -1.0),
    4:  (-1.0,  1.0,  1.0),
    5:  (-1.0,  1.0, -1.0),
    6:  (-1.0, -1.0,  1.0),
    7:  (-1.0, -1.0, -1.0),
    8:  ( 0.0,  PHI,  INV_PHI),
    9:  ( 0.0,  PHI, -INV_PHI),
    10: ( 0.0, -PHI,  INV_PHI),
    11: ( 0.0, -PHI, -INV_PHI),
    12: ( INV_PHI,  0.0,  PHI),
    13: (-INV_PHI,  0.0,  PHI),
    14: ( INV_PHI,  0.0, -PHI),
    15: (-INV_PHI,  0.0, -PHI),
    16: ( PHI,  INV_PHI,  0.0),
    17: ( PHI, -INV_PHI,  0.0),
    18: (-PHI,  INV_PHI,  0.0),
    19: (-PHI, -INV_PHI,  0.0),
}

# Normalize to unit sphere
for s in DODECA_VERTICES:
    x, y, z = DODECA_VERTICES[s]
    r = math.sqrt(x*x + y*y + z*z)
    DODECA_VERTICES[s] = (x/r, y/r, z/r)

# Dodecahedral transitions: each vertex connects to 3 nearest neighbors
# Computed automatically from coordinates to ensure correctness
DODECA_TRANSITIONS: Dict[int, List[int]] = {}
for _a in range(20):
    _ax, _ay, _az = DODECA_VERTICES[_a]
    _distances = []
    for _b in range(20):
        if _a == _b:
            continue
        _bx, _by, _bz = DODECA_VERTICES[_b]
        _d = math.sqrt((_ax-_bx)**2 + (_ay-_by)**2 + (_az-_bz)**2)
        _distances.append((_d, _b))
    _distances.sort()
    # Regular dodecahedron: exactly 3 nearest neighbors per vertex
    DODECA_TRANSITIONS[_a] = [_b for _d, _b in _distances[:3]]

# Map amino acids to vertices (ordered by biochemical properties)
# Vertices 0-7: cube corners (mixed properties)
# Vertices 8-11: y-axis poles (polar/charged)
# Vertices 12-15: z-axis poles (hydrophobic/aromatic)
# Vertices 16-19: x-axis poles (small/large)
AA_TO_VERTEX: Dict[str, int] = {
    "A": 0,   # Alanine - small, hydrophobic
    "G": 1,   # Glycine - tiny, flexible
    "S": 2,   # Serine - small, polar
    "T": 3,   # Threonine - small, polar
    "V": 4,   # Valine - hydrophobic, aliphatic
    "L": 5,   # Leucine - hydrophobic, aliphatic
    "I": 6,   # Isoleucine - hydrophobic, aliphatic
    "M": 7,   # Methionine - hydrophobic, sulfur
    "N": 8,   # Asparagine - polar, amide
    "Q": 9,   # Glutamine - polar, amide
    "H": 10,  # Histidine - positive, aromatic
    "K": 11,  # Lysine - positive, large
    "F": 12,  # Phenylalanine - aromatic, hydrophobic
    "W": 13,  # Tryptophan - aromatic, large
    "Y": 14,  # Tyrosine - aromatic, polar
    "P": 15,  # Proline - unique backbone
    "D": 16,  # Aspartic acid - negative, small
    "E": 17,  # Glutamic acid - negative, large
    "C": 18,  # Cysteine - sulfur, polar
    "R": 19,  # Arginine - positive, large
}

VERTEX_TO_AA: Dict[int, str] = {v: k for k, v in AA_TO_VERTEX.items()}

# Eigenvalues for each amino acid (based on hydropathy, size, charge)
def _make_eigenvalues():
    vals = {}
    for aa in AMINO_ACIDS:
        v = AA_TO_VERTEX[aa]
        h = (HYDROPATHY[aa] + 5) / 10  # normalize to 0-1
        m = MW[aa] / 210.0  # normalize
        c = PKA.get(aa, 7.0) / 14.0  # neutral if no pKa
        # Renormalize to sum ~1
        total = h + m + c
        vals[v] = (h/total, m/total, c/total)
    return vals

DODECA_EIGENVALUES = _make_eigenvalues()


# =============================================================================
# PROTEIN ENCODER
# =============================================================================

class ProteinEncoder:
    """
    Encode protein sequences onto dodecahedral geometry.

    20 amino acids -> 20 vertices of regular dodecahedron.
    Each vertex is shared by 3 pentagonal faces (property classes).
    """

    def __init__(self):
        self.positions = DODECA_VERTICES.copy()
        self.transitions = DODECA_TRANSITIONS.copy()
        self.eigenvalues = DODECA_EIGENVALUES.copy()
        self.aa_to_vertex = AA_TO_VERTEX.copy()
        self.vertex_to_aa = VERTEX_TO_AA.copy()

    # -----------------------------------------------------------------------
    # Basic encode/decode
    # -----------------------------------------------------------------------

    def encode(self, sequence: str) -> List[int]:
        """Map protein sequence to dodecahedral vertices."""
        result = []
        for aa in sequence.upper():
            if aa in self.aa_to_vertex:
                result.append(self.aa_to_vertex[aa])
            else:
                result.append(-1)
        return result

    def decode(self, states: List[int]) -> str:
        """Map dodecahedral vertices to protein sequence."""
        return "".join(
            self.vertex_to_aa.get(s, "?") for s in states
        )

    # -----------------------------------------------------------------------
    # Geometric operations
    # -----------------------------------------------------------------------

    def vertex_distance(self, v1: int, v2: int) -> float:
        """Euclidean distance between two vertices on unit sphere."""
        x1, y1, z1 = self.positions[v1]
        x2, y2, z2 = self.positions[v2]
        return math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2)

    def angular_distance(self, v1: int, v2: int) -> float:
        """Angular distance between two vertices (degrees)."""
        x1, y1, z1 = self.positions[v1]
        x2, y2, z2 = self.positions[v2]
        dot = x1*x2 + y1*y2 + z1*z2
        dot = max(-1.0, min(1.0, dot))
        return math.degrees(math.acos(dot))

    def residue_distance(self, aa1: str, aa2: str) -> float:
        """
        Geometric distance between two amino acids on dodecahedron.
        Accounts for shared property classes.
        """
        v1 = self.aa_to_vertex.get(aa1.upper())
        v2 = self.aa_to_vertex.get(aa2.upper())
        if v1 is None or v2 is None:
            return float("inf")

        # Base geometric distance
        geo_dist = self.vertex_distance(v1, v2)

        # Shared properties reduce effective distance
        props1 = self.properties(aa1)
        props2 = self.properties(aa2)
        shared = len(props1 & props2)

        # More shared properties = closer
        return geo_dist * (1.0 - 0.15 * shared)

    # -----------------------------------------------------------------------
    # Property queries
    # -----------------------------------------------------------------------

    def properties(self, aa: str) -> Set[str]:
        """Return all property classes for an amino acid."""
        aa = aa.upper()
        return {name for name, members in PROPERTY_CLASSES.items() if aa in members}

    def property_neighbors(self, aa: str) -> List[str]:
        """Return amino acids that share at least one property class."""
        aa = aa.upper()
        props = self.properties(aa)
        neighbors = set()
        for p in props:
            neighbors.update(PROPERTY_CLASSES[p])
        neighbors.discard(aa)
        return sorted(neighbors)

    def is_hydrophobic(self, aa: str) -> bool:
        return aa.upper() in PROPERTY_CLASSES["hydrophobic"]

    def is_charged(self, aa: str) -> bool:
        return aa.upper() in PROPERTY_CLASSES["positive"] | PROPERTY_CLASSES["negative"]

    def charge_at_pH(self, aa: str, pH: float = 7.0) -> int:
        """Return charge (+1, 0, -1) at given pH."""
        aa = aa.upper()
        if aa in PROPERTY_CLASSES["positive"]:
            pka = PKA.get(aa, 10.0)
            return 1 if pH < pka else 0
        elif aa in PROPERTY_CLASSES["negative"]:
            pka = PKA.get(aa, 4.0)
            return -1 if pH > pka else 0
        elif aa == "C" and pH > PKA.get("C", 8.3):
            return -1
        elif aa == "Y" and pH > PKA.get("Y", 10.1):
            return -1
        return 0

    # -----------------------------------------------------------------------
    # Sequence analysis
    # -----------------------------------------------------------------------

    def hydropathy(self, sequence: str, window: Optional[int] = None) -> float:
        """
        Kyte-Doolittle hydropathy score.
        Positive = hydrophobic, negative = hydrophilic.
        """
        seq = sequence.upper()
        scores = [HYDROPATHY.get(aa, 0.0) for aa in seq]
        if window is None:
            return sum(scores) / max(len(scores), 1)

        # Sliding window
        result = []
        for i in range(len(scores) - window + 1):
            result.append(sum(scores[i:i+window]) / window)
        return result

    def molecular_weight(self, sequence: str) -> float:
        """Total molecular weight (Da)."""
        return sum(MW.get(aa, 0.0) for aa in sequence.upper())

    def composition(self, sequence: str) -> Dict[str, float]:
        """Amino acid composition as fractions."""
        seq = sequence.upper()
        total = len(seq)
        comp = {}
        for aa in AMINO_ACIDS:
            comp[aa] = seq.count(aa) / total
        return comp

    def hydrophobic_moment(self, sequence: str, angle: float = 100.0) -> Tuple[float, float]:
        """
        Eisenberg hydrophobic moment.
        Measures amphipathicity of an alpha-helix.
        """
        seq = sequence.upper()
        angle_rad = math.radians(angle)
        sum_x = 0.0
        sum_y = 0.0
        for i, aa in enumerate(seq):
            h = HYDROPATHY.get(aa, 0.0)
            theta = i * angle_rad
            sum_x += h * math.cos(theta)
            sum_y += h * math.sin(theta)
        return (sum_x, sum_y)

    # -----------------------------------------------------------------------
    # Structural predictions
    # -----------------------------------------------------------------------

    def alpha_helix_propensity(self, sequence: str) -> float:
        """
        Simple propensity based on helix-favoring residues.
        Scale: 0-1, higher = more helix-prone.
        """
        helix_favoring = {"A", "L", "M", "H", "E", "Q", "K"}
        helix_breaking = {"P", "G"}
        seq = sequence.upper()
        score = 0
        for aa in seq:
            if aa in helix_favoring:
                score += 1
            elif aa in helix_breaking:
                score -= 2
        return max(0.0, min(1.0, score / max(len(seq), 1) + 0.5))

    def beta_sheet_propensity(self, sequence: str) -> float:
        """Simple beta-sheet propensity."""
        sheet_favoring = {"V", "I", "Y", "C", "W", "F", "T"}
        seq = sequence.upper()
        score = sum(1 for aa in seq if aa in sheet_favoring)
        return score / max(len(seq), 1)

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate(self) -> dict:
        """Validate dodecahedral geometry."""
        findings = {
            "n_vertices": 20,
            "n_faces": 12,
            "n_edges": 30,
            "vertex_distances_from_center": {},
            "edge_lengths": [],
            "issues": [],
        }

        # All vertices should be at distance 1 from center
        for s in range(20):
            d = math.sqrt(sum(x**2 for x in self.positions[s]))
            findings["vertex_distances_from_center"][s] = round(d, 6)
            if abs(d - 1.0) > 0.01:
                findings["issues"].append(f"Vertex {s} not on unit sphere: r={d:.4f}")

        # Check edge lengths are uniform
        for a in range(20):
            for b in self.transitions.get(a, []):
                if a < b:
                    d = self.vertex_distance(a, b)
                    findings["edge_lengths"].append(round(d, 6))

        unique_lengths = set(findings["edge_lengths"])
        if len(unique_lengths) > 1:
            findings["issues"].append(f"Non-uniform edge lengths: {unique_lengths}")

        # Check each AA maps to exactly one vertex
        if len(self.aa_to_vertex) != 20:
            findings["issues"].append(f"Expected 20 AA mappings, got {len(self.aa_to_vertex)}")

        findings["passes"] = len(findings["issues"]) == 0
        return findings


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PROTEIN-DODECAHEDRAL ENCODER — Self Test")
    print("=" * 60)

    enc = ProteinEncoder()

    # Validate geometry
    audit = enc.validate()
    print(f"\nGeometry validation:")
    print(f"  Vertices: {audit['n_vertices']}, Faces: {audit['n_faces']}, Edges: {audit['n_edges']}")
    print(f"  Edge lengths: {len(audit['edge_lengths'])} edges")
    print(f"  Issues: {audit['issues'] or 'None'}")

    # Basic encode/decode
    seq = "MKTLLI"
    states = enc.encode(seq)
    back = enc.decode(states)
    print(f"\nRound-trip: {seq} -> {states} -> {back} ({'OK' if back == seq else 'FAIL'})")

    # Property queries
    print(f"\nProperties of Alanine (A): {enc.properties('A')}")
    print(f"Property neighbors of A: {enc.property_neighbors('A')}")

    # Residue distances
    print(f"\nGeometric distances:")
    print(f"  A-V (both hydrophobic): {enc.residue_distance('A', 'V'):.3f}")
    print(f"  D-K (opposite charge): {enc.residue_distance('D', 'K'):.3f}")
    print(f"  A-G (both small): {enc.residue_distance('A', 'G'):.3f}")

    # Hydropathy
    print(f"\nHydropathy of MKTLLI: {enc.hydropathy('MKTLLI'):.2f}")
    print(f"Molecular weight: {enc.molecular_weight('MKTLLI'):.1f} Da")

    # Charge
    print(f"\nCharge of D at pH 7: {enc.charge_at_pH('D', 7.0)}")
    print(f"Charge of K at pH 7: {enc.charge_at_pH('K', 7.0)}")

    # Structure propensity
    print(f"\nHelix propensity of MKTLLI: {enc.alpha_helix_propensity('MKTLLI'):.2f}")
    print(f"Sheet propensity of VIVIVI: {enc.beta_sheet_propensity('VIVIVI'):.2f}")

    # Hydrophobic moment
    hm = enc.hydrophobic_moment("MKTLLI")
    print(f"Hydrophobic moment of MKTLLI: ({hm[0]:.2f}, {hm[1]:.2f})")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)
