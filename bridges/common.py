"""
Common utilities for the Geometric-to-Binary Computational Bridge.
Used by all bridge encoders.
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


def gray_bits(value: float, bands: list, n_bits: int = 3) -> str:
    """
    Map a non-negative scalar to a Gray-coded binary string.

    Canonical highest-edge scan: iterates band edges from highest to lowest
    and returns the index of the highest edge the value meets or exceeds,
    encoded as an n_bits Gray code.

    Gray-code property: adjacent bands differ by exactly 1 bit, so a value
    near a band boundary never causes more than a 1-bit change.

    Args:
        value  : non-negative scalar to encode
        bands  : list of 2^n_bits monotonically increasing lower-bound edges
        n_bits : bits per symbol (default 3 → 8 bands)

    Examples:
        gray_bits(0.0,  [0, 1, 2, 3, 4, 5, 6, 7]) → "000"  (band 0)
        gray_bits(0.5,  [0, 1, 2, 3, 4, 5, 6, 7]) → "000"  (band 0)
        gray_bits(1.0,  [0, 1, 2, 3, 4, 5, 6, 7]) → "001"  (band 1)
        gray_bits(3.0,  [0, 1, 2, 3, 4, 5, 6, 7]) → "010"  (band 3 → Gray=2)
    """
    band = 0
    for i in range(len(bands) - 1, -1, -1):
        if value >= bands[i]:
            band = i
            break
    return format(gray_code(band), f'0{n_bits}b')
