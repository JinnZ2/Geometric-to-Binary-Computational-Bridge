"""c_runner — C-backed factoring runner.

Embeds a tiny self-contained C program, compiles it on first call (cached
in a temp dir), and invokes it via subprocess. Same algorithm as
python_runner (small-prime sweep + Pollard's rho) so timing comparisons
isolate the language/runtime, not the algorithm. uint64_t bound: inputs
must fit in 63 bits.
"""
from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

from dispatcher import Problem, register_runner


_C_SRC = r"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

typedef unsigned __int128 u128;

static uint64_t mulmod(uint64_t a, uint64_t b, uint64_t m) {
    return (uint64_t)(((u128)a * b) % m);
}

static uint64_t gcd64(uint64_t a, uint64_t b) {
    while (b) { uint64_t t = a % b; a = b; b = t; }
    return a;
}

static uint64_t pollard_rho(uint64_t n) {
    if (n % 2 == 0) return 2;
    for (;;) {
        uint64_t x = (uint64_t)rand() % (n - 2) + 2;
        uint64_t y = x;
        uint64_t c = (uint64_t)rand() % (n - 1) + 1;
        uint64_t d = 1;
        while (d == 1) {
            x = (mulmod(x, x, n) + c) % n;
            y = (mulmod(y, y, n) + c) % n;
            y = (mulmod(y, y, n) + c) % n;
            uint64_t diff = x > y ? x - y : y - x;
            d = gcd64(diff, n);
        }
        if (d != n) return d;
    }
}

int main(int argc, char **argv) {
    if (argc != 2) return 1;
    uint64_t n = strtoull(argv[1], NULL, 10);
    if (n <= 1) { printf("1 %llu\n", (unsigned long long)n); return 0; }
    if (n % 2 == 0) { printf("2 %llu\n", (unsigned long long)(n / 2)); return 0; }
    for (uint64_t p = 3; p < 1000 && p * p <= n; p += 2) {
        if (n % p == 0) {
            printf("%llu %llu\n", (unsigned long long)p, (unsigned long long)(n / p));
            return 0;
        }
    }
    uint64_t f = pollard_rho(n);
    uint64_t g = n / f;
    if (f > g) { uint64_t t = f; f = g; g = t; }
    printf("%llu %llu\n", (unsigned long long)f, (unsigned long long)g);
    return 0;
}
"""

_BIN_PATH = Path(tempfile.gettempdir()) / "polyglot_factor_c"


def _ensure_compiled() -> None:
    if _BIN_PATH.exists():
        return
    src_path = _BIN_PATH.with_suffix(".c")
    src_path.write_text(_C_SRC)
    for compiler in ("cc", "gcc", "clang"):
        try:
            subprocess.run(
                [compiler, "-O2", "-o", str(_BIN_PATH), str(src_path)],
                check=True, capture_output=True,
            )
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("no C compiler found (tried cc, gcc, clang)")


@register_runner("c")
def run(problem: Problem) -> tuple[bool, str, float]:
    n = problem.payload["n"]
    if n.bit_length() > 63:
        return False, f"C runner only handles n < 2^63 (got {n.bit_length()} bits)", 0.0
    _ensure_compiled()
    t0 = time.perf_counter()
    res = subprocess.run(
        [str(_BIN_PATH), str(n)],
        capture_output=True, text=True, check=True,
    )
    elapsed = time.perf_counter() - t0
    parts = res.stdout.strip().split()
    if len(parts) != 2:
        return False, f"unexpected output: {res.stdout!r}", elapsed
    p, q = int(parts[0]), int(parts[1])
    ok = (p > 1 and q > 1 and p * q == n)
    return ok, f"{n} = {p} * {q}", elapsed
