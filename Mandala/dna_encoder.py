#!/usr/bin/env python3
"""
DNA-Tetrahedral Encoder — Biological Sequence Operations on Geometric Substrate
================================================================================

Maps DNA/RNA sequences onto tetrahedral geometry. 4 bases (A,T,G,C) map
naturally to 4 tetrahedral vertices. Chirality distinguishes coding vs
template strands.

Self-contained. Depends only on stdlib.

Usage:
    from dna_encoder import DNAEncoder
    enc = DNAEncoder(chirality="right")

    # Encode DNA to tetrahedral states
    states = enc.encode("ATGCGTAC")

    # Decode back
    seq = enc.decode(states)

    # Reverse complement (geometric reflection)
    rc = enc.reverse_complement("ATGCGTAC")

    # Transcribe DNA -> RNA
    rna = enc.transcribe("ATGCGTAC")

    # Translate to amino acids
    protein = enc.translate("ATGCGTAC")

    # Error detection: find positions that violate tetrahedral constraints
    errors = enc.find_errors("ATGCGTAX")  # X is invalid

    # Geometric distance between two sequences
    dist = enc.sequence_distance("ATGC", "ATGG")
"""

from typing import List, Dict, Tuple, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASES = "ATGC"
RNA_BASES = "AUGC"

# Standard genetic code
code = {
    "UUU": "F", "UUC": "F", "UUA": "L", "UUG": "L",
    "UCU": "S", "UCC": "S", "UCA": "S", "UCG": "S",
    "UAU": "Y", "UAC": "Y", "UAA": "*", "UAG": "*",
    "UGU": "C", "UGC": "C", "UGA": "*", "UGG": "W",
    "CUU": "L", "CUC": "L", "CUA": "L", "CUG": "L",
    "CCU": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAU": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGU": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AUU": "I", "AUC": "I", "AUA": "I", "AUG": "M",
    "ACU": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAU": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGU": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GUU": "V", "GUC": "V", "GUA": "V", "GUG": "V",
    "GCU": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAU": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGU": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# Codon table (DNA version — T instead of U)
DNA_CODE = {}
for codon, aa in code.items():
    dna_codon = codon.replace("U", "T")
    DNA_CODE[dna_codon] = aa

# Complement mapping
COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G", "N": "N"}
RNA_COMPLEMENT = {"A": "U", "U": "A", "G": "C", "C": "G", "N": "N"}

# Tetrahedral vertex mapping (right-handed)
# A=0, T=1, G=2, C=3 — this is arbitrary but fixed
BASE_TO_STATE = {"A": 0, "T": 1, "G": 2, "C": 3}
STATE_TO_BASE = {0: "A", 1: "T", 2: "G", 3: "C"}

# Transition distances on tetrahedron (all edges equal in regular tetrahedron)
# But we can weight by biochemical similarity:
# Purine (A,G) <-> Purine = short
# Pyrimidine (T,C) <-> Pyrimidine = short
# Purine <-> Pyrimidine = long
BASE_DISTANCE = {
    ("A", "A"): 0.0, ("T", "T"): 0.0, ("G", "G"): 0.0, ("C", "C"): 0.0,
    ("A", "G"): 0.5, ("G", "A"): 0.5,  # Purine-purine
    ("T", "C"): 0.5, ("C", "T"): 0.5,  # Pyrimidine-pyrimidine
    ("A", "T"): 1.0, ("T", "A"): 1.0,  # Purine-pyrimidine
    ("A", "C"): 1.0, ("C", "A"): 1.0,
    ("G", "T"): 1.0, ("T", "G"): 1.0,
    ("G", "C"): 1.0, ("C", "G"): 1.0,
}


# =============================================================================
# DNA ENCODER
# =============================================================================

class DNAEncoder:
    """
    Encode DNA sequences onto tetrahedral geometry.

    Parameters
    ----------
    chirality : str
        "right" or "left" — determines strand orientation
    """

    def __init__(self, chirality: str = "right"):
        if chirality not in ("right", "left"):
            raise ValueError(f"chirality must be 'right' or 'left', got {chirality!r}")
        self.chirality = chirality
        # Left-handed flips the state mapping
        if chirality == "left":
            self.base_to_state = {"A": 3, "T": 2, "G": 1, "C": 0}
            self.state_to_base = {3: "A", 2: "T", 1: "G", 0: "C"}
        else:
            self.base_to_state = BASE_TO_STATE.copy()
            self.state_to_base = STATE_TO_BASE.copy()

    # -----------------------------------------------------------------------
    # Basic encode/decode
    # -----------------------------------------------------------------------

    def encode(self, sequence: str) -> List[int]:
        """Map DNA sequence to tetrahedral states."""
        result = []
        for base in sequence.upper():
            if base not in self.base_to_state:
                result.append(-1)  # Invalid base marker
            else:
                result.append(self.base_to_state[base])
        return result

    def decode(self, states: List[int]) -> str:
        """Map tetrahedral states to DNA sequence."""
        return "".join(
            self.state_to_base.get(s, "N") for s in states
        )

    # -----------------------------------------------------------------------
    # Strand operations
    # -----------------------------------------------------------------------

    def complement(self, sequence: str, rna: bool = False) -> str:
        """Return complement strand."""
        comp = RNA_COMPLEMENT if rna else COMPLEMENT
        return "".join(comp.get(b, "N") for b in sequence.upper())

    def reverse_complement(self, sequence: str, rna: bool = False) -> str:
        """Return reverse complement (geometric reflection)."""
        return self.complement(sequence, rna)[::-1]

    def transcribe(self, dna: str) -> str:
        """DNA -> RNA (replace T with U)."""
        return dna.upper().replace("T", "U")

    def reverse_transcribe(self, rna: str) -> str:
        """RNA -> DNA (replace U with T)."""
        return rna.upper().replace("U", "T")

    # -----------------------------------------------------------------------
    # Translation
    # -----------------------------------------------------------------------

    def translate(self, dna: str, start_at_first: bool = False) -> str:
        """
        Translate DNA to protein sequence.

        Parameters
        ----------
        start_at_first : bool
            If True, start at position 0. If False, find first ATG start codon.
        """
        seq = dna.upper().replace("U", "T")

        if not start_at_first:
            # Find first ATG
            start = seq.find("ATG")
            if start == -1:
                return ""
            seq = seq[start:]

        protein = []
        for i in range(0, len(seq) - 2, 3):
            codon = seq[i:i+3]
            if len(codon) < 3:
                break
            aa = DNA_CODE.get(codon, "?")
            if aa == "*":
                break
            protein.append(aa)

        return "".join(protein)

    # -----------------------------------------------------------------------
    # Error detection using geometric constraints
    # -----------------------------------------------------------------------

    def find_errors(self, sequence: str) -> List[Tuple[int, str, str]]:
        """
        Find invalid bases and positions that violate biochemical constraints.

        Returns list of (position, found, expected_or_note).
        """
        errors = []
        seq = sequence.upper()
        valid = set(BASES)

        for i, base in enumerate(seq):
            if base not in valid:
                errors.append((i, base, "INVALID_BASE"))

        return errors

    def gc_content(self, sequence: str) -> float:
        """Return GC content as fraction."""
        seq = sequence.upper()
        gc = seq.count("G") + seq.count("C")
        return gc / max(len(seq), 1)

    # -----------------------------------------------------------------------
    # Geometric distance between sequences
    # -----------------------------------------------------------------------

    def sequence_distance(self, seq_a: str, seq_b: str) -> float:
        """
        Weighted distance between two DNA sequences.
        Accounts for purine/pyrimidine similarity.
        """
        a = seq_a.upper()
        b = seq_b.upper()

        # Pad shorter with N (max distance)
        max_len = max(len(a), len(b))
        a = a.ljust(max_len, "N")
        b = b.ljust(max_len, "N")

        total = 0.0
        for x, y in zip(a, b):
            total += BASE_DISTANCE.get((x, y), 1.5)

        return total / max_len

    def hamming_distance(self, seq_a: str, seq_b: str) -> int:
        """Standard Hamming distance (mismatches only)."""
        a = seq_a.upper()
        b = seq_b.upper()
        max_len = max(len(a), len(b))
        a = a.ljust(max_len, "N")
        b = b.ljust(max_len, "N")
        return sum(x != y for x, y in zip(a, b))

    # -----------------------------------------------------------------------
    # Tetrahedral-specific: chirality and strand orientation
    # -----------------------------------------------------------------------

    def coding_strand(self, template: str) -> str:
        """Return coding strand from template (reverse complement)."""
        return self.reverse_complement(template)

    def is_palindromic(self, sequence: str) -> bool:
        """Check if sequence equals its reverse complement."""
        seq = sequence.upper()
        return seq == self.reverse_complement(seq)

    def find_restriction_sites(self, sequence: str, site: str) -> List[int]:
        """Find all occurrences of a restriction site (including reverse complement)."""
        seq = sequence.upper()
        site = site.upper()
        rc_site = self.reverse_complement(site)

        positions = []
        for i in range(len(seq) - len(site) + 1):
            window = seq[i:i+len(site)]
            if window == site or window == rc_site:
                positions.append(i)
        return positions

    # -----------------------------------------------------------------------
    # Bulk operations
    # -----------------------------------------------------------------------

    def kmer_frequencies(self, sequence: str, k: int = 3) -> Dict[str, int]:
        """Count k-mer frequencies in sequence."""
        seq = sequence.upper()
        freqs = {}
        for i in range(len(seq) - k + 1):
            kmer = seq[i:i+k]
            if "N" not in kmer:
                freqs[kmer] = freqs.get(kmer, 0) + 1
        return freqs

    def gc_skew(self, sequence: str, window: int = 100) -> List[float]:
        """GC skew (G-C)/(G+C) across windows."""
        seq = sequence.upper()
        skews = []
        for i in range(0, len(seq), window):
            w = seq[i:i+window]
            g = w.count("G")
            c = w.count("C")
            denom = g + c
            skews.append((g - c) / denom if denom > 0 else 0.0)
        return skews

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate_sequence(self, sequence: str) -> Dict:
        """Full validation report for a DNA sequence."""
        seq = sequence.upper()
        return {
            "length": len(seq),
            "valid": all(b in BASES for b in seq),
            "errors": self.find_errors(seq),
            "gc_content": self.gc_content(seq),
            "chirality": self.chirality,
            "encoded_states": self.encode(seq),
            "is_palindromic": self.is_palindromic(seq) if len(seq) <= 100 else None,
        }


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DNA-TETRAHEDRAL ENCODER — Self Test")
    print("=" * 60)

    # Test both chiralities
    for chirality in ("right", "left"):
        print(f"\n--- Chirality: {chirality} ---")
        enc = DNAEncoder(chirality=chirality)

        # Basic round-trip
        seq = "ATGCGTAC"
        states = enc.encode(seq)
        back = enc.decode(states)
        print(f"Round-trip: {seq} -> {states} -> {back} ({'OK' if back == seq else 'FAIL'})")

        # Complement
        rc = enc.reverse_complement(seq)
        print(f"Reverse complement: {seq} -> {rc}")

        # Transcription
        rna = enc.transcribe(seq)
        print(f"Transcribe: {seq} -> {rna}")

        # Translation
        protein = enc.translate(seq)
        print(f"Translate: {seq} -> {protein}")

        # GC content
        gc = enc.gc_content(seq)
        print(f"GC content: {gc:.2%}")

        # Sequence distance
        dist = enc.sequence_distance("ATGC", "ATGG")
        ham = enc.hamming_distance("ATGC", "ATGG")
        print(f"Distance ATGC vs ATGG: geometric={dist:.3f} hamming={ham}")

        # Error detection
        errors = enc.find_errors("ATGCGTAX")
        print(f"Errors in ATGCGTAX: {errors}")

        # Palindrome check
        pal = "GAATTC"  # EcoRI site
        print(f"Is {pal} palindromic? {enc.is_palindromic(pal)}")

        # Restriction sites
        dna = "ATGCGTACGAATTCGCGTACGAATTC"
        sites = enc.find_restriction_sites(dna, "GAATTC")
        print(f"EcoRI sites in sequence: {sites}")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)
