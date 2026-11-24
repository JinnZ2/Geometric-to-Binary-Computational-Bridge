# SPDX-License-Identifier: CC0-1.0
"""Shared arithmetic for the loop-topology toys.  Co-authored.  Stdlib only.

Continuous-time Markov chains on a handful of states, exact from the
generator: stationary distribution, entropy production rate (sigma),
matrix exponential, the window KL of a sampled and merged chain, and the
second-order semi-Markov estimator used by dwell.py and nested.py.

Units: nats; rates per unit time.  Definitions are the ones declared in
DECLARED.json before any of this was run.
"""
import itertools
import math


def rates_from_edges(n, edges):
    """edges: (i, j, forward rate, backward rate).  Returns W[i][j]."""
    W = [[0.0] * n for _ in range(n)]
    for i, j, f, b in edges:
        W[i][j] += f
        W[j][i] += b
    return W


def ring(n, fwd, back):
    f = fwd if isinstance(fwd, (list, tuple)) else [fwd] * n
    b = back if isinstance(back, (list, tuple)) else [back] * n
    return rates_from_edges(n, [(i, (i + 1) % n, f[i], b[i]) for i in range(n)])


def generator(W):
    n = len(W)
    return [[W[i][j] if i != j else -sum(W[i][k] for k in range(n) if k != i)
             for j in range(n)] for i in range(n)]


def solve(A, b):
    """Gaussian elimination with partial pivoting.  A: rows.  b: vector."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(c + 1, n):
            f = M[r][c] / M[c][c]
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for c in range(n - 1, -1, -1):
        x[c] = (M[c][n] - sum(M[c][k] * x[k] for k in range(c + 1, n))) / M[c][c]
    return x


def stationary(W):
    n = len(W)
    Q = generator(W)
    A = [[Q[j][i] for j in range(n)] for i in range(n)]      # transpose: pi Q = 0
    A[-1] = [1.0] * n
    return solve(A, [0.0] * (n - 1) + [1.0])


def sigma(W, pi=None):
    """Entropy production rate: sum over ordered pairs of flux * log ratio."""
    pi = stationary(W) if pi is None else pi
    s = 0.0
    for i in range(len(W)):
        for j in range(len(W)):
            if i != j and W[i][j] > 0:
                if W[j][i] <= 0:
                    return math.inf
                s += pi[i] * W[i][j] * math.log(pi[i] * W[i][j] / (pi[j] * W[j][i]))
    return s


def matmul(A, B):
    return [[math.fsum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))]
            for i in range(len(A))]


def expm(Q, t):
    """exp(Q t) by scaling and squaring with a Taylor series."""
    n = len(Q)
    norm = max(sum(abs(x) for x in row) for row in Q) * abs(t)
    s = max(0, int(math.ceil(math.log(max(norm, 1e-300), 2))) + 4) if norm > 0 else 0
    A = [[Q[i][j] * t / (2 ** s) for j in range(n)] for i in range(n)]
    E = [[float(i == j) for j in range(n)] for i in range(n)]
    term = [row[:] for row in E]
    for k in range(1, 25):
        term = matmul(term, A)
        term = [[x / k for x in row] for row in term]
        E = [[E[i][j] + term[i][j] for j in range(n)] for i in range(n)]
    for _ in range(s):
        E = matmul(E, E)
    return E


def sampled_sigma(W, tau, pi=None):
    """(1/tau) sum pi_i P_ij ln(P_ij / P_ji) for the chain read every tau."""
    pi = stationary(W) if pi is None else pi
    P = expm(generator(W), tau)
    n = len(W)
    s = 0.0
    for i in range(n):
        for j in range(n):
            if i != j and P[i][j] > 1e-300 and P[j][i] > 1e-300:
                s += pi[i] * P[i][j] * math.log(P[i][j] / P[j][i])
    return s / tau


def window_kl(W, label, tau, w):
    """KL between length-w windows of the observed symbol sequence and their
    reversals.  label[i] = symbol the observer reads in state i.  Exact
    (hidden-Markov forward sum over every window)."""
    pi = stationary(W)
    P = expm(generator(W), tau)
    n = len(W)
    symbols = sorted(set(label))

    def prob(seq):
        v = [pi[i] if label[i] == seq[0] else 0.0 for i in range(n)]
        for s in seq[1:]:
            v = [math.fsum(v[i] * P[i][j] for i in range(n)) if label[j] == s else 0.0
                 for j in range(n)]
        return math.fsum(v)

    kl = 0.0
    for seq in itertools.product(symbols, repeat=w):
        p = prob(seq)
        if p > 1e-300:
            q = prob(seq[::-1])
            kl += p * math.log(p / q) if q > 1e-300 else math.inf
    return kl


def merged_markov(W, groups):
    """Markov chain on the merged states: k_AB = sum pi_a w_ab / pi_A."""
    pi = stationary(W)
    g = len(groups)
    K = [[0.0] * g for _ in range(g)]
    for A in range(g):
        pa = math.fsum(pi[a] for a in groups[A])
        for B in range(g):
            if A != B:
                K[A][B] = math.fsum(pi[a] * W[a][b] for a in groups[A] for b in groups[B]) / pa
    return K


def groups_for(n, merges):
    """merges: list of sets of micro states read as one.  Returns the groups."""
    used = set(x for m in merges for x in m)
    return [sorted(m) for m in merges] + [[i] for i in range(n) if i not in used]


def semi_markov(W, groups, conditional=True, steps=4000):
    """Second-order semi-Markov estimate of sigma on the merged process.

    Returns dict(affinity, waiting, total, irreversible).  'irreversible'
    counts triples i->j->k that occur while k->j->i cannot; they are left
    out of the sums and reported.
    conditional=False is the known wrong form: joint triple probabilities
    in the affinity term in place of the conditional ones."""
    pi = stationary(W)
    g = len(groups)
    aff = wait = 0.0
    irreversible = 0
    for j in range(g):
        G = groups[j]
        m = len(G)
        Qg = [[W[a][b] if a != b else -math.fsum(W[a][c] for c in range(len(W)) if c != a)
               for b in G] for a in G]
        others = [i for i in range(g) if i != j]
        a_in = {i: [math.fsum(pi[x] * W[x][y] for x in groups[i]) for y in G] for i in others}
        r_out = {k: [math.fsum(W[y][x] for x in groups[k]) for y in G] for k in others}
        negQT = [[-Qg[b][a] for b in range(m)] for a in range(m)]
        occ = {i: solve(negQT, a_in[i]) for i in others}     # a_i (-Q)^-1
        R = {(i, k): math.fsum(occ[i][y] * r_out[k][y] for y in range(m))
             for i in others for k in others}
        flux = {i: math.fsum(a_in[i]) for i in others}
        for i in others:
            for k in others:
                if R[i, k] <= 1e-300:
                    continue
                if R[k, i] <= 1e-300:
                    irreversible += 1
                    continue
                if conditional:
                    aff += R[i, k] * math.log((R[i, k] / flux[i]) / (R[k, i] / flux[k]))
                else:
                    aff += R[i, k] * math.log(R[i, k] / R[k, i])
        if m > 1:
            wait += _waiting(Qg, a_in, r_out, R, others, steps)
    return {"affinity": aff, "waiting": wait, "total": aff + wait, "irreversible": irreversible}


def _waiting(Qg, a_in, r_out, R, others, steps):
    """sum R(ijk) * KL[psi(t | ijk) || psi(t | kji)], Simpson on a time grid."""
    m = len(Qg)
    slow = min(abs(Qg[a][a]) for a in range(m))
    fast = max(abs(Qg[a][a]) for a in range(m))
    t_max = 60.0 / max(slow * 0.02, 1e-9) if m > 1 else 0.0
    t_max = min(t_max, 4000.0 / fast * 50)
    # the escape from the group is at least as fast as its slowest joint mode;
    # find a horizon where the survival mass is negligible
    dt = 0.02 / fast
    P = expm(Qg, dt)
    v = {i: list(a_in[i]) for i in others}
    dens = {key: [] for key in R}
    n_steps = 0
    while True:
        for i in others:
            for k in others:
                dens[i, k].append(math.fsum(v[i][y] * r_out[k][y] for y in range(m)))
        mass = max(math.fsum(v[i]) for i in others)
        if (mass < 1e-13 * max(math.fsum(a_in[i]) for i in others) and n_steps % 2 == 0
                and n_steps > 0) or n_steps >= 2000000:
            break
        v = {i: [math.fsum(v[i][x] * P[x][y] for x in range(m)) for y in range(m)] for i in others}
        n_steps += 1
    total = 0.0
    for (i, k), d in dens.items():
        if R[i, k] <= 1e-300 or R[k, i] <= 1e-300:
            continue
        back = dens[k, i]
        f = []
        for x, y in zip(d, back):
            p, q = x / R[i, k], y / R[k, i]
            f.append(p * math.log(p / q) if p > 1e-300 and q > 1e-300 else 0.0)
        n = len(f) - 1
        simpson = f[0] + f[n] + 4 * math.fsum(f[1:n:2]) + 2 * math.fsum(f[2:n:2])
        total += R[i, k] * simpson * dt / 3.0
    return total
