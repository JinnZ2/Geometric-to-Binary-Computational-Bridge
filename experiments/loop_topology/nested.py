# SPDX-License-Identifier: CC0-1.0
"""T6 nested: a figure-eight of a fast loop and a slow loop sharing a hub.
Co-authored.  Stdlib only.

    python experiments/loop_topology/nested.py

Fast ring 0 -> 1 -> 2 -> 0 at 10 (reverse 4); slow ring 0 -> 3 -> 4 -> 0
at 0.4 (reverse 0.1).  State cuts merge states; time cuts read the chain
every tau.  ledger.py holds the heat side.
"""
import math

import ctmc

FAST = [(0, 1), (1, 2), (2, 0)]
SLOW = [(0, 3), (3, 4), (4, 0)]
FAST_FWD, FAST_BACK = 10.0, 4.0
SLOW_FWD, SLOW_BACK = 0.4, 0.1
CUTS = {"none": [], "collapse_fast": [{1, 2}], "collapse_slow": [{3, 4}],
        "across": [{1, 3}], "hub": [{0, 1}], "both": [{1, 2}, {3, 4}]}
TAUS = [0.01, 0.05, 0.2, 1.0, 5.0]


def graph(fast=(FAST_FWD, FAST_BACK), slow=(SLOW_FWD, SLOW_BACK)):
    edges = [(i, j, fast[0], fast[1]) for i, j in FAST] + [(i, j, slow[0], slow[1]) for i, j in SLOW]
    return ctmc.rates_from_edges(5, edges)


def loop_sigma(W, loop):
    pi = ctmc.stationary(W)
    i, j = loop[0]
    flux = pi[i] * W[i][j] - pi[j] * W[j][i]
    affinity = math.fsum(math.log(W[a][b] / W[b][a]) for a, b in loop)
    return flux * affinity


def cut_fraction(W, merges):
    return ctmc.semi_markov(W, ctmc.groups_for(len(W), merges))["total"] / ctmc.sigma(W)


def numbers():
    W = graph()
    total = ctmc.sigma(W)
    out = {"T6.sigma.fast": loop_sigma(W, FAST), "T6.sigma.slow": loop_sigma(W, SLOW),
           "T6.sigma.total": total}
    for name, merges in CUTS.items():
        out["T6.cut.%s" % name] = cut_fraction(W, merges)
    for tau in TAUS:
        out["T6.time.tau%s" % ("%g" % tau)] = ctmc.sampled_sigma(W, tau) / total
    return out


if __name__ == "__main__":
    for k, v in numbers().items():
        print("%-26s %.6f" % (k, v))
