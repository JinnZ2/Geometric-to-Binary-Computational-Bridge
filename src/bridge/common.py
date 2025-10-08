"""
Common utilities for the Geometric-to-Binary Computational Bridge.
Used by magnetic.py, light.py, sound.py, etc.
"""

def gray_code(n: int) -> int:
    """
    Convert integer → Gray code integer.
    
    Example:
        0 → 0
        1 → 1
        2 → 3
        3 → 2
    """
    return n ^ (n >> 1)

def bits_from_int(n: int, width: int) -> str:
    """
    Return a binary string of length `width` representing integer n.
    
    Example:
        bits_from_int(5, 4) → "0101"
    """
    return format(n, f'0{width}b')

def hamming_distance(a: str, b: str) -> int:
    """
    Compute Hamming distance between two equal-length bitstrings.
    
    Example:
        hamming_distance("1010", "0011") → 2
    """
    if len(a) != len(b):
        raise ValueError("Bitstrings must be the same length")
    return sum(ch1 != ch2 for ch1, ch2 in zip(a, b))
