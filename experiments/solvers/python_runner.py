"""python_runner — pure-Python factoring runner.

Strategy: small-prime trial sweep (catches tiny n like the n=15 warmup),
then Pollard's rho for everything bigger. Trial division alone would be
unusable here — the 60-bit demo input has a ~30-bit smallest factor.
"""
from __future__ import annotations

import random
import time
from math import gcd

from dispatcher import Problem, register_runner


def _pollard_rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    while True:
        x = random.randrange(2, n)
        y = x
        c = random.randrange(1, n)
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)
        if d != n:
            return d


def _factor(n: int) -> tuple[int, int]:
    if n <= 1:
        return (1, n)
    if n % 2 == 0:
        return (2, n // 2)
    p = 3
    while p < 1000 and p * p <= n:
        if n % p == 0:
            return (p, n // p)
        p += 2
    f = _pollard_rho(n)
    g = n // f
    return (min(f, g), max(f, g))


@register_runner("python")
def run(problem: Problem) -> tuple[bool, str, float]:
    n = problem.payload["n"]
    t0 = time.perf_counter()
    p, q = _factor(n)
    elapsed = time.perf_counter() - t0
    ok = (p > 1 and q > 1 and p * q == n)
    return ok, f"{n} = {p} * {q}", elapsed
