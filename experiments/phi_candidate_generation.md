def golden_candidates(limit, start=0):
    """
    Yield integers in [1, limit] in golden ratio order.
    Uses the fractional part of n * φ to permute the range.
    """
    phi = (1 + 5**0.5) / 2
    n = start
    seen = set()
    while len(seen) < limit:
        # Map n to an integer in 1..limit using the golden ratio as a low‑discrepancy sequence
        # Classic: x = (n * phi) % 1, then a = floor(x * limit) + 1
        x = (n * phi) % 1
        a = int(x * limit) + 1
        if a not in seen:
            seen.add(a)
            yield a
        n += 1


        # Instead of:
# for offset in range(max_candidates):
#     a = sqrt_N + offset

# Use:
for a in golden_candidates(max_candidates, start=sieve_offset):
    a = sqrt_N + a   # shift to start from sqrt_N
    # ... rest of sieve


    
