# SPDX-License-Identifier: CC0-1.0
"""T3 collision: two bits driven round a cycle, each bit alone unbiased.
Co-authored.  Stdlib only.

    python experiments/loop_topology/collision.py

States (x, y).  Cycle 00 -> 01 -> 11 -> 10 -> 00 at rate 1 + c, reverse at
1 - c.  An observer of x alone, of y alone, and of both, each reading the
chain every TAU and comparing length-WINDOW windows with their reversals.
"""
import math

import ctmc

ORDER = [(0, 0), (0, 1), (1, 1), (1, 0)]
CS = [0.05, 0.2, 0.5, 0.9]
TAU, WINDOW = 0.1, 4


def model(c):
    return ctmc.ring(4, 1.0 + c, 1.0 - c)


def mutual_information_xy(c):
    pi = ctmc.stationary(model(c))
    px = [sum(p for p, s in zip(pi, ORDER) if s[0] == v) for v in (0, 1)]
    py = [sum(p for p, s in zip(pi, ORDER) if s[1] == v) for v in (0, 1)]
    return math.fsum(p * math.log(p / (px[s[0]] * py[s[1]])) for p, s in zip(pi, ORDER) if p > 0)


def observed_rate(c, label):
    return ctmc.window_kl(model(c), label, TAU, WINDOW) / ((WINDOW - 1) * TAU)


def numbers():
    out, both = {}, {}
    for c in CS:
        s = ctmc.sigma(model(c))
        out["T3.sigma.c%s" % c] = s
        both[c] = observed_rate(c, [0, 1, 2, 3]) / s
    out["T3.I_xy"] = max(abs(mutual_information_xy(c)) for c in CS)
    out["T3.obs_x"] = max(abs(observed_rate(c, [s[0] for s in ORDER])) for c in CS)
    out["T3.obs_y"] = max(abs(observed_rate(c, [s[1] for s in ORDER])) for c in CS)
    out["T3.obs_both_over_sigma"] = both[0.5]
    out["_obs_both_each_c"] = both
    return out


if __name__ == "__main__":
    for k, v in numbers().items():
        print("%-26s %s" % (k, v))
