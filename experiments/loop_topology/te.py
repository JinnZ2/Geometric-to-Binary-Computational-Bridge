# SPDX-License-Identifier: CC0-1.0
"""T4 te: transfer entropy on the collision model.  Co-authored.  Stdlib only.

    python experiments/loop_topology/te.py

Transfer entropy rate at history length 1 on the chain read every tau:
I(target at t + tau ; source at t | target at t) / tau.  The
Horowitz-Esposito information flow and the Schnakenberg form beside it.
"""
import math

import collision
import ctmc

TAU = 0.1
TAUS = [0.02, 0.05, 0.1, 0.3, 1.0]


def transfer_entropy(c, tau, source, target):
    """source, target: 0 for x, 1 for y."""
    W = collision.model(c)
    pi = ctmc.stationary(W)
    P = ctmc.expm(ctmc.generator(W), tau)
    S = collision.ORDER
    joint = {}                                   # (source_t, target_t, target_next)
    for i in range(4):
        for j in range(4):
            key = (S[i][source], S[i][target], S[j][target])
            joint[key] = joint.get(key, 0.0) + pi[i] * P[i][j]
    te = 0.0
    for (s, t, t2), p in joint.items():
        if p <= 0:
            continue
        p_st = sum(v for (a, b, _), v in joint.items() if a == s and b == t)
        p_t = sum(v for (_, b, _), v in joint.items() if b == t)
        p_tt2 = sum(v for (_, b, d), v in joint.items() if b == t and d == t2)
        te += p * math.log((p / p_st) / (p_tt2 / p_t))
    return te / tau


def he_flow(c, mover):
    """Rate of change of I(x;y) due to jumps of `mover` (0 = x, 1 = y)."""
    W = collision.model(c)
    pi = ctmc.stationary(W)
    S = collision.ORDER
    other = 1 - mover
    p_other = [sum(p for p, s in zip(pi, S) if s[other] == v) for v in (0, 1)]
    flow = 0.0
    for i in range(4):
        for j in range(4):
            if W[i][j] > 0 and S[i][other] == S[j][other]:
                cond_i = pi[i] / p_other[S[i][other]]
                cond_j = pi[j] / p_other[S[j][other]]
                flow += pi[i] * W[i][j] * math.log(cond_j / cond_i)
    return flow


def numbers():
    out = {}
    worst = 0.0
    for c in collision.CS:
        xy, yx = transfer_entropy(c, TAU, 0, 1), transfer_entropy(c, TAU, 1, 0)
        out["T4.TE.c%s" % c] = xy
        worst = max(worst, abs(xy - yx))
    out["_TE_xy_minus_yx_max"] = worst
    out["T4.HE_flow"] = max(abs(he_flow(c, m)) for c in collision.CS for m in (0, 1))
    for tau in TAUS:
        out["T4.TE.tau%s" % tau] = transfer_entropy(0.5, tau, 0, 1)
    c = 0.5
    affinity = 4 * math.log((1 + c) / (1 - c))
    out["T4.J.c0.5"] = c / 2
    out["T4.sigma.c0.5"] = (c / 2) * affinity
    out["_sigma_from_generator"] = ctmc.sigma(collision.model(c))
    return out


if __name__ == "__main__":
    for k, v in numbers().items():
        print("%-26s %s" % (k, v))
