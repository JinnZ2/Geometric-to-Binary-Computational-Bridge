# SPDX-License-Identifier: CC0-1.0
"""Pipeline on a planted toy.  Co-authored.  Stdlib only.

    python experiments/loop_topology/pipeline.py

simulate a jump trajectory from the T6 graph -> recover rates
(counts / dwell) -> rate graph -> cycle decomposition -> sigma per cycle
-> recovered fraction per cut.

Seed, length, gates and the null are declared in DECLARED.json and read
from there.  Under a state cut the merged trajectory is read as if it
were Markov; under a time cut the trajectory is read every tau.  A loop is
FLAGGED when a recovered cycle carries sigma above the null gate.
"""
import json
import math
import os
import random

import ctmc
import nested

HERE = os.path.dirname(os.path.abspath(__file__))
SEED, TOTAL_TIME = 20261124, 50000.0
RATE_GATE, SIGMA_GATE, NULL_GATE = 0.10, 0.10, 0.01
NULL_FAST, NULL_SLOW = (7.0, 7.0), (0.25, 0.25)


def simulate(W, seed=SEED, total=TOTAL_TIME):
    """Gillespie.  Returns [(state, dwell)], in order."""
    rng = random.Random(seed)
    n = len(W)
    out_rate = [sum(W[i]) for i in range(n)]
    targets = [[j for j in range(n) if W[i][j] > 0] for i in range(n)]
    weights = [[W[i][j] for j in targets[i]] for i in range(n)]
    state, t, path = 0, 0.0, []
    while t < total:
        dwell = rng.expovariate(out_rate[state])
        path.append((state, min(dwell, total - t)))
        t += dwell
        state = rng.choices(targets[state], weights[state])[0]
    return path


def merge_path(path, groups):
    label = {s: g for g, members in enumerate(groups) for s in members}
    out = []
    for s, d in path:
        g = label[s]
        if out and out[-1][0] == g:
            out[-1] = (g, out[-1][1] + d)
        else:
            out.append((g, d))
    return out


def recover(path, n):
    """rate i -> j = count(i -> j) / dwell(i)."""
    dwell = [0.0] * n
    count = [[0] * n for _ in range(n)]
    for k, (s, d) in enumerate(path):
        dwell[s] += d
        if k + 1 < len(path):
            count[s][path[k + 1][0]] += 1
    K = [[count[i][j] / dwell[i] if dwell[i] > 0 else 0.0 for j in range(n)] for i in range(n)]
    return K, count, dwell


def cycles(K):
    """Fundamental cycles of the rate graph (edges with both directions seen),
    from a breadth-first spanning tree.  Returns lists of directed edges."""
    n = len(K)
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if K[i][j] > 0 and K[j][i] > 0]
    parent, order, seen = {}, [], set()
    for root in range(n):
        if root in seen:
            continue
        seen.add(root)
        parent[root] = None
        queue = [root]
        while queue:
            a = queue.pop(0)
            order.append(a)
            for i, j in edges:
                for x, y in ((i, j), (j, i)):
                    if x == a and y not in seen:
                        seen.add(y)
                        parent[y] = a
                        queue.append(y)
    tree = {frozenset((c, p)) for c, p in parent.items() if p is not None}

    def to_root(x):
        out = [x]
        while parent[out[-1]] is not None:
            out.append(parent[out[-1]])
        return out

    found = []
    for i, j in edges:
        if frozenset((i, j)) in tree:
            continue
        pi_, pj = to_root(i), to_root(j)
        common = next(x for x in pj if x in pi_)
        loop = [i, j] + pj[1:pj.index(common) + 1] + pi_[1:pi_.index(common)][::-1]
        found.append([(loop[k], loop[(k + 1) % len(loop)]) for k in range(len(loop))])
    return found


def cycle_sigma(K, dwell, loop):
    """Chord net flux (first edge of the loop, the non-tree edge) * affinity."""
    total = sum(dwell)
    p = [d / total for d in dwell]
    i, j = loop[0]
    flux = p[i] * K[i][j] - p[j] * K[j][i]
    return flux * math.fsum(math.log(K[a][b] / K[b][a]) for a, b in loop)


def read(path, n):
    K, count, dwell = recover(path, n)
    loops = cycles(K)
    return K, count, dwell, [(sorted({a for a, _ in lp}), cycle_sigma(K, dwell, lp)) for lp in loops]


def sampled_sigma(path, n, tau):
    """Trajectory read every tau; transition matrix from counts."""
    count = [[0] * n for _ in range(n)]
    t_next, t, prev = 0.0, 0.0, None
    for s, d in path:
        while t_next < t + d:
            if prev is not None:
                count[prev][s] += 1
            prev = s
            t_next += tau
        t += d
    total = sum(map(sum, count))
    s_ = 0.0
    for i in range(n):
        for j in range(n):
            if i != j and count[i][j] and count[j][i]:
                s_ += count[i][j] / total * math.log(count[i][j] / count[j][i])
    return s_ / tau, total


def main():
    declared = json.load(open(os.path.join(HERE, "DECLARED.json")))["pipeline"]
    W = nested.graph()
    true_total = ctmc.sigma(W)
    true_loop = {"fast": nested.loop_sigma(W, nested.FAST), "slow": nested.loop_sigma(W, nested.SLOW)}
    path = simulate(W)
    print("planted: T6 graph; %s" % declared["simulation"])
    print("trajectory: %d jumps over time %g" % (len(path) - 1, TOTAL_TIME))
    K, count, dwell, loops = read(path, 5)

    print("\nRECOVERED RATES (gate: within %.2f relative)" % RATE_GATE)
    print("  edge    planted   recovered   rel err   count   gate")
    worst = 0.0
    for i in range(5):
        for j in range(5):
            if W[i][j] > 0:
                rel = K[i][j] / W[i][j] - 1.0
                worst = max(worst, abs(rel))
                print("  %d->%d  %8.3f  %10.4f  %+8.4f  %6d   %s"
                      % (i, j, W[i][j], K[i][j], rel, count[i][j],
                         "inside" if abs(rel) <= RATE_GATE else "OUTSIDE"))
    print("  largest |rel err| %.4f" % worst)

    print("\nSIGMA PER CYCLE (gate: within %.2f relative of T6)" % SIGMA_GATE)
    print("  cycle states   T6 value   recovered   rel err   gate")
    for states, s in loops:
        name = "fast" if set(states) == {0, 1, 2} else "slow" if set(states) == {0, 3, 4} else "other"
        ref = true_loop.get(name)
        rel = s / ref - 1.0 if ref else float("nan")
        print("  %-12s  %9.4f  %10.4f  %+8.4f   %s"
              % ("%s %s" % (name, states), ref or float("nan"), s, rel,
                 "inside" if ref and abs(rel) <= SIGMA_GATE else "OUTSIDE"))
    print("  total: T6 %.4f, recovered %.4f" % (true_total, sum(s for _, s in loops)))

    null_W = nested.graph(NULL_FAST, NULL_SLOW)
    _, _, _, null_loops = read(simulate(null_W), 5)
    null_total = sum(s for _, s in null_loops)
    print("\nNULL: detailed-balance graph (fast %g / %g, slow %g / %g), same seed and length"
          % (NULL_FAST + NULL_SLOW))
    print("  planted sigma %.6f; recovered per cycle %s; total %.6f; gate <= %.2f: %s"
          % (ctmc.sigma(null_W), ", ".join("%.6f" % s for _, s in null_loops), null_total,
             NULL_GATE, "inside" if null_total <= NULL_GATE else "OUTSIDE"))

    print("\nSTATE CUTS: merged trajectory read as Markov (flag: a cycle with sigma > %.2f)" % NULL_GATE)
    print("  cut             groups                 cycles found   recovered sigma   fraction"
          "   T6 Markov heat   T6 dwell fraction   fast loop   slow loop")
    exact = nested.numbers()
    import ledger
    heat = ledger.numbers()["_markov_heat_all_cuts"]
    for name, merges in nested.CUTS.items():
        groups = ctmc.groups_for(5, merges)
        mp = merge_path(path, groups)
        _, _, _, lps = read(mp, len(groups))
        rec = sum(s for _, s in lps)
        flagged = {"fast": "hidden", "slow": "hidden"}
        for states, s in lps:
            micro = set(x for g in states for x in groups[g])
            for loop_name, members in (("fast", {0, 1, 2}), ("slow", {0, 3, 4})):
                if members <= micro and s > NULL_GATE and len(micro - members) <= 1 + (name == "across"):
                    flagged[loop_name] = "FLAGGED"
        print("  %-14s  %-21s  %12d   %15.4f   %8.3f   %14.4f   %17.4f   %-9s   %s"
              % (name, "|".join("".join(map(str, g)) for g in groups), len(lps), rec,
                 rec / true_total, heat[name], exact["T6.cut.%s" % name],
                 flagged["fast"], flagged["slow"]))

    print("\nTIME CUTS: trajectory read every tau, transition counts")
    print("  tau     samples   recovered sigma   fraction   T6 fraction   flagged (sigma > %.2f)" % NULL_GATE)
    for tau in nested.TAUS:
        s, m = sampled_sigma(path, 5, tau)
        print("  %-5g  %8d   %15.4f   %8.3f   %11.3f   %s"
              % (tau, m, s, s / true_total, exact["T6.time.tau%g" % tau],
                 "yes" if s > NULL_GATE else "no"))
    ns, nm = sampled_sigma(simulate(null_W), 5, 5.0)
    print("  null graph at tau 5: recovered sigma %.4f over %d samples" % (ns, nm))


if __name__ == "__main__":
    main()
