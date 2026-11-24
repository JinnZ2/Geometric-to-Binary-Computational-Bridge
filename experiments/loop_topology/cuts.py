# SPDX-License-Identifier: CC0-1.0
"""T1 cuts: what a cut through a system reads, and what it cannot.
Co-authored.  Stdlib only.

    python experiments/loop_topology/cuts.py

A 4-spin open Ising chain read through three cuts and four observables,
and a driven 3-ring read by an observer who cannot tell two of its states
apart.  Numbers are compared with DECLARED.json by run_all.py.
"""
import itertools
import math

import ctmc

J = [2.0, 0.2, 1.5]
T = 1.0
RING_FWD, RING_BACK = 3.0, 0.5
DT = 0.05


def chain():
    states = list(itertools.product((-1, 1), repeat=4))
    w = [math.exp(sum(J[i] * s[i] * s[i + 1] for i in range(3)) / T) for s in states]
    z = math.fsum(w)
    return {s: x / z for s, x in zip(states, w)}


def entropy(p):
    return -math.fsum(x * math.log(x) for x in p.values() if x > 0)


def marginal(P, f):
    out = {}
    for s, p in P.items():
        out[f(s)] = out.get(f(s), 0.0) + p
    return out


def mutual_information(P, k):
    left = marginal(P, lambda s: s[:k])
    right = marginal(P, lambda s: s[k:])
    return entropy(left) + entropy(right) - entropy(P)


def kl_observable(P, Q, f):
    p, q = marginal(P, f), marginal(Q, f)
    return math.fsum(x * math.log(x / q[k]) for k, x in p.items() if x > 0)


def sign(x):
    return (x > 0) - (x < 0)


def numbers():
    P = chain()
    single = [marginal(P, lambda s, i=i: s[i]) for i in range(4)]
    Q = {s: math.prod(single[i][s[i]] for i in range(4)) for s in P}
    out = {"T1.I.cut%d" % k: mutual_information(P, k) for k in (1, 2, 3)}
    out["T1.D.full"] = kl_observable(P, Q, lambda s: s)
    out["T1.D.pairs"] = kl_observable(P, Q, lambda s: (s[0] * s[1], s[2] * s[3]))
    out["T1.D.magnetization"] = kl_observable(P, Q, sum)
    out["T1.D.sign"] = kl_observable(P, Q, lambda s: sign(sum(s)))
    W = ctmc.ring(3, RING_FWD, RING_BACK)
    out["T1.ring.sigma"] = ctmc.sigma(W)
    for w in range(2, 7):
        out["T1.ring.KL.w%d" % w] = ctmc.window_kl(W, [0, 1, 1], DT, w)
    return out


if __name__ == "__main__":
    for k, v in numbers().items():
        print("%-22s %.6f" % (k, v))
