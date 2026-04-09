# Geometric NFS — C Acceleration Library

Optional C implementation of the hot-path routines from `experiments/geometric_nfs.py`.
For users with a C compiler who want more performance on larger factorizations.

## Build

```bash
cd experiments/c
make            # builds libgeometric_nfs.so (Linux) or .dylib (macOS)
make test       # builds + runs 36 smoke tests
make clean      # removes build artifacts
```

Requires: GCC or Clang with C11 support, `math.h`.

## What it accelerates

| Component | Function | What it does |
|-----------|----------|--------------|
| Sieve | `sieve_block()` | Log-accumulation sieve over a block of `a` values |
| Trial division | `trial_divide()` | Factor `a^2 - N` over the factor base |
| Geometric search | `geometric_search()` | Octahedral null space search (phases 0-3) |
| GF(2) fallback | `gf2_fallback()` / `gf2_fallback_wide()` | Gaussian elimination over GF(2) |

The sieve and trial division are the innermost loops — pure Python spends most of
its time here. The C versions use `__int128` for overflow-safe arithmetic and
tight stride loops.

## Python integration

```python
from experiments.c.gnfs_ctypes import get_accelerator

accel = get_accelerator()
if accel.available:
    ctx = accel.create_context(N, factor_base)
    candidates = accel.sieve_block(ctx, start_a, block_size, slack)
    for idx in candidates:
        rel = accel.trial_divide(ctx, start_a + idx, len(factor_base))
        if rel:
            # rel = {'a': ..., 'Q': ..., 'exponents': {prime_idx: count}}
            ...
    deps = accel.gf2_solve(parity_rows, n_cols)
    accel.free_context(ctx)
else:
    # Fall back to pure Python (experiments/geometric_nfs.py)
    ...
```

If `libgeometric_nfs.so` isn't built, `accel.available` is `False` and the
Python NFS continues to work unchanged.

## Architecture

```
geometric_nfs_core.h    Public API + inline octahedral state helpers
geometric_nfs_core.c    Implementation (sieve, trial div, geometric search, GF(2))
Makefile                Build system
test_nfs.c              C smoke tests (36 assertions)
gnfs_ctypes.py          Python ctypes wrapper
__init__.py             Package marker
```

### Octahedral state packing

Factor-base primes are grouped in triples (3 primes = 1 octahedron = 8 states = 3 bits).
Each relation's exponent parity is packed as one 3-bit state per octahedron, two states
per byte (low nibble + high nibble). Inline helpers `octa_get`/`octa_set`/`octa_xor_row`
operate on this packed format.

### Geometric null space search phases

0. **Singles** — relations with all-zero states (already a perfect square)
1. **Hash duplicates** — identical state vectors cancel via XOR
2. **Near-duplicates** — states differing in 1 octahedron, found via delete-one signatures
3. **Iterative cancellation** — partial XOR pairs extended to triples

## License

CC-BY-4.0 (same as parent project)
