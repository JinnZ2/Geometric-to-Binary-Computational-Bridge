"""
equation_search.py -- a mini equation searcher, measured.

Given data, hunt through FOUR FAMILIES of equations and report which
structures generated it -- or abstain. The searcher is a ranking and
falsification engine, not a finder: infinitely many equations fit any
finite dataset, so every candidate pays a complexity penalty (BIC /
MDL), and the instrument ships three kinds of claims:

  RECOVERY: planted ground truth must come back within tolerance.
            We own all four ground truths (Fibonacci counts, the sink,
            Lorenz, the logistic map) -- fail means the search is
            broken, not the physics.
  NULL:     pure noise must NOT be "discovered". The abstention rate
            is a measured output; nulls are outputs.
  VOID:     data from a type outside the grammar must be answered
            "no adequate equation in this grammar", never a confident
            bad fit. Identifiability limits are first-class outputs.

Families (grammar = small integer/rational coefficients over a term
library; same four types as the instruments that made the data):
  F1 exact linear recurrence   x_{n+1} = a x_n + b x_{n-1}   (a,b in Z)
  F2 linear ODE spiral         x' = lam x - ome y, y' = ome x + lam y
  F3 polynomial ODE            x' = sparse subset of {1,x,y,z,xy,xz,yz,x^2,...}
  F4 nonlinear map             x_{n+1} = r x (1 - x), r real

Measured warnings priced in (from snapshot_delta.py, seed 0):
  - chaotic trajectories amplify fitting error (~+0.35/s measured):
    F3 is scored on SHORT one-step predictions from on-trajectory
    states, never on long free runs. The error floor is a claim input.
  - many-to-one summaries stay VOID: fitting counts recovers the
    count recurrence; the word is not recoverable (10^56800 words
    share one count vector). Not re-litigated here.

Claim format: value / tol_frac / measurement / failure / provenance;
verdict in {pass, drift, fail, void}. Nulls are outputs.
Run:  python3 equation_search.py [seed]
License: CC0. Stdlib only. Phone-runnable.
"""

import json
import math
import random
import sys
import time

# ------------------------------------------------------------------ params

NOISE_LEVELS = [0.0, 0.001, 0.01]       # relative, for recovery bands
NULL_TRIALS = 40                        # noise datasets per family
BIC_REJECTION_SLACK = 0.0               # winner must beat runner-up by this
MAX_TERMS_F3 = 3                        # sparsity cap for the poly-ODE search

# F4 logistic map ground truth
LOGISTIC_R = 3.7
LOGISTIC_X0 = 0.31
LOGISTIC_N = 400


# ------------------------------------------------------------------ algebra

def solve(A, b):
    """Gaussian elimination, partial pivoting. Raises on singular."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    scale = max(abs(M[i][i]) for i in range(n)) or 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-13 * scale:
            raise ArithmeticError("singular")
        M[col], M[piv] = M[piv], M[col]
        for r in range(col + 1, n):
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (M[i][n] - sum(M[i][j] * x[j] for j in range(i + 1, n))) \
            / M[i][i]
    return x

def lstsq(Phi, y, ridge=1e-10):
    """min |Phi beta - y|^2 + ridge|beta|^2 -> (beta, rss)."""
    m = len(Phi[0])
    G = [[sum(row[i] * row[j] for row in Phi) for j in range(m)]
         for i in range(m)]
    for i in range(m):
        G[i][i] += ridge
    b = [sum(row[i] * v for row, v in zip(Phi, y)) for i in range(m)]
    beta = solve(G, b)
    rss = sum((sum(row[i] * beta[i] for i in range(m)) - v) ** 2
              for row, v in zip(Phi, y))
    return beta, rss

def bic(rss, n, k):
    """Bayesian information criterion; lower is better."""
    if rss <= 0:
        rss = 1e-300
    return n * math.log(rss / n) + k * math.log(n)


# ================================================================== FAMILY 1
# exact linear recurrence  x_{n+1} = a x_n + b x_{n-1}, a,b small ints
# Verification is EXACT: a candidate must reproduce every term.

def f1_search(seq, coeff_range=range(-4, 5)):
    """Returns list of (a, b) that reproduce the sequence EXACTLY."""
    hits = []
    for a in coeff_range:
        for b in coeff_range:
            ok = all(seq[n + 1] == a * seq[n] + b * seq[n - 1]
                     for n in range(1, len(seq) - 1))
            if ok:
                hits.append((a, b))
    return hits

def f1_family():
    fib = [1, 1]
    while len(fib) < 30:
        fib.append(fib[-1] + fib[-2])
    pell = [0, 1]
    while len(pell) < 30:
        pell.append(2 * pell[-1] + pell[-2])
    const = [3] * 30          # order-1 recurrence; outside order-2 view?
    return {
        "fibonacci": {"seq": fib, "planted": (1, 1)},
        "pell": {"seq": pell, "planted": (2, 1)},
        "constant": {"seq": const, "planted": None},
    }


# ================================================================== FAMILY 2
# linear ODE spiral: estimate lambda, omega from a trajectory.
# Ground truth from snapshot_delta.py: lambda=-0.1, omega=2*pi.

def sink_rhs_gen(lam, ome):
    def f(s):
        return [lam * s[0] - ome * s[1], ome * s[0] + lam * s[1]]
    return f

def rk4(f, s, dt):
    k1 = f(s)
    k2 = f([s[i] + 0.5 * dt * k1[i] for i in range(len(s))])
    k3 = f([s[i] + 0.5 * dt * k2[i] for i in range(len(s))])
    k4 = f([s[i] + dt * k3[i] for i in range(len(s))])
    return [s[i] + dt * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0
            for i in range(len(s))]

def integrate(f, s0, dt, n):
    traj = [list(s0)]
    s = list(s0)
    for _ in range(n):
        s = rk4(f, s, dt)
        traj.append(s)
    return traj

def f2_fit(traj, dt):
    """Least squares for [x'; y'] = [lam -ome; ome lam] [x; y]."""
    Phi, Y = [], [[], []]
    for i in range(1, len(traj) - 1):
        x, y = traj[i]
        dx = (traj[i + 1][0] - traj[i - 1][0]) / (2 * dt)
        dy = (traj[i + 1][1] - traj[i - 1][1]) / (2 * dt)
        Phi.append([x, y])
        Y[0].append(dx)
        Y[1].append(dy)
    # dx = lam x - ome y ; dy = ome x + lam y
    bl, rss_l = lstsq(Phi, Y[0])
    bo, rss_o = lstsq(Phi, Y[1])
    lam = 0.5 * (bl[0] + bo[1])
    ome = 0.5 * (-bl[1] + bo[0])
    return lam, ome, rss_l + rss_o


# ================================================================== FAMILY 3
# polynomial ODE library, SINDy-style, one-step scoring ONLY.

F3_TERMS = ["1", "x", "y", "z", "xy", "xz", "yz", "x2", "y2", "z2"]

def f3_phi(s):
    x, y, z = s
    return [1.0, x, y, z, x * y, x * z, y * z, x * x, y * y, z * z]

def f3_search(traj, dt, max_terms=MAX_TERMS_F3):
    """Per-component sparse fit over the term library.

    Greedy forward selection by BIC up to max_terms terms. Returns
    (chosen_terms_per_component, beta_per_component, bic_total).
    Scoring is ONE-STEP from on-trajectory states: chaotic free-run
    error amplification (~+0.35/s measured) never enters the fit.
    """
    ders = [[] for _ in range(3)]
    phis = []
    for i in range(1, len(traj) - 1):
        phis.append(f3_phi(traj[i]))
        for c in range(3):
            ders[c].append((traj[i + 1][c] - traj[i - 1][c]) / (2 * dt))
    n = len(phis)
    chosen_all, beta_all, bic_total = [], [], 0.0
    for c in range(3):
        chosen, betas = [], []
        best_bic = bic(sum(v * v for v in ders[c]), n, 0)
        for _ in range(max_terms):
            best = None
            for t in range(len(F3_TERMS)):
                if t in chosen:
                    continue
                trial = chosen + [t]
                Phi = [[row[j] for j in trial] for row in phis]
                try:
                    beta, rss = lstsq(Phi, ders[c])
                except ArithmeticError:
                    continue
                score = bic(rss, n, len(trial))
                if best is None or score < best[0]:
                    best = (score, trial, beta, rss)
            if best is None or best[0] >= best_bic - BIC_REJECTION_SLACK:
                break
            best_bic, chosen, betas = best[0], best[1], best[2]
        chosen_all.append([F3_TERMS[j] for j in chosen])
        beta_all.append(betas)
        bic_total += best_bic
    return chosen_all, beta_all, bic_total


# ================================================================== FAMILY 4
# nonlinear map x_{n+1} = r x (1 - x): fit r by least squares.

def f4_fit(seq):
    Phi = [[x * (1.0 - x)] for x in seq[:-1]]
    y = seq[1:]
    beta, rss = lstsq(Phi, y)
    return beta[0], rss

def f4_null_guard(seq):
    """Fit a LINEAR map too; the logistic must win by BIC."""
    beta_l, rss_l = lstsq([[x] for x in seq[:-1]], seq[1:])
    beta_q, rss_q = f4_fit(seq)
    n = len(seq) - 1
    return beta_q, bic(rss_q, n, 1), bic(rss_l, n, 1), beta_l[0]


# ------------------------------------------------------------------ claims

def verdict(measured, predicted, tol_frac, zero_tol=1e-12):
    if measured is None or predicted is None:
        return "void"
    if predicted == 0:
        return "pass" if abs(measured) <= zero_tol else "fail"
    rel = abs(measured - predicted) / abs(predicted)
    if rel <= tol_frac:
        return "pass"
    if rel <= 3 * tol_frac:
        return "drift"
    return "fail"


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    t0 = time.time()
    rng = random.Random(seed)
    claims = []
    record_notes = {}

    def pack(scope, rate_var, value, tol_frac, measurement, failure,
             measured, extra=None, verdict_fn=None, zero_tol=1e-12):
        c = {"scope": scope, "rate_var": rate_var, "kind": "equation_search",
             "value": value, "tol_frac": tol_frac, "measurement": measurement,
             "failure": failure, "provenance": "equation_search.py",
             "measured": measured,
             "verdict": (verdict_fn(measured) if verdict_fn else
                         verdict(measured, value, tol_frac, zero_tol)),
             "ts": t0}
        if extra:
            c.update(extra)
        claims.append(c)

    # ---------------- F1: exact recurrence recovery -------------------
    fam1 = f1_family()
    f1_results = {}
    for name, d in fam1.items():
        hits = f1_search(d["seq"])
        f1_results[name] = {"planted": d["planted"], "hits": hits}
    fib_ok = f1_results["fibonacci"]["hits"] == [(1, 1)]
    pell_ok = f1_results["pell"]["hits"] == [(2, 1)]
    pack("fab::eqsearch::f1::exact_recovery",
         "dN_structure/dquery",
         0.0, 0.0,
         "search order-2 integer recurrences a,b in [-4,4] over the "
         "planted Fibonacci and Pell sequences; count cases where the "
         "UNIQUE exact hit is not the planted pair (must be zero); "
         "verification is exact integer equality over all 30 terms",
         "- grammar too narrow -> planted pair absent from candidates\n"
         "- verification not exact -> spurious hits flood the list",
         0.0 if (fib_ok and pell_ok) else 1.0,
         extra=f1_results)
    # null: noise must abstain
    f1_false = 0
    for _ in range(NULL_TRIALS):
        noise = [rng.randrange(-50, 50) for _ in range(12)]
        if f1_search(noise):
            f1_false += 1
    pack("fab::eqsearch::f1::null_abstention",
         "dN_false_discovery/dtrial",
         0.0, 0.0,
         "feed 40 random integer sequences (12 terms, values in "
         "[-50,50]) to the order-2 exact search; count datasets with "
         "ANY exact hit (must be zero; exact verification is the bar)",
         "- short sequences + wide coefficient range -> accidental\n"
         "  exact fits; if measured > 0 the grammar window is too wide",
         float(f1_false),
         extra={"trials": NULL_TRIALS})

    # ---------------- F2: linear ODE parameter recovery ---------------
    lam_true, ome_true = -0.1, 2.0 * math.pi
    dt = 0.01
    traj = integrate(sink_rhs_gen(lam_true, ome_true), [1.0, 0.0], dt, 5000)
    f2_rows = []
    for nl in NOISE_LEVELS:
        noisy = [[x + nl * rng.gauss(0, 1) for x in s] for s in traj] \
            if nl else traj
        lam, ome, rss = f2_fit(noisy, dt)
        f2_rows.append({"noise": nl, "lam": lam, "ome": ome,
                        "lam_err": abs(lam - lam_true),
                        "ome_rel_err": abs(ome - ome_true) / ome_true})
    worst_lam = max(r["lam_err"] for r in f2_rows)
    worst_ome = max(r["ome_rel_err"] for r in f2_rows)
    pack("fab::eqsearch::f2::parameter_recovery",
         "d(param)/dnoise",
         0.0, 0.0,
         "recover (lambda, omega) of the planted spiral from 5000-step "
         "trajectories at relative noise 0, 1e-3, 1e-2; worst absolute "
         "lambda error and worst relative omega error, each <= 0.05",
         "- finite-difference derivative noise -> drift/fail at the\n"
         "  1e-2 noise level (that is a measured band, not a bug)\n"
         "- wrong structural family -> errors O(1)",
         max(worst_lam, worst_ome),
         zero_tol=0.05,
         extra={"rows": f2_rows, "planted": {"lam": lam_true,
                                             "ome": ome_true}})

    # ---------------- F3: polynomial ODE structure recovery -----------
    def lorenz_rhs(s):
        return [10.0 * (s[1] - s[0]),
                s[0] * (28.0 - s[2]) - s[1],
                s[0] * s[1] - (8.0 / 3.0) * s[2]]
    ltraj = integrate(lorenz_rhs, [1.0, 1.0, 1.0], 0.005, 11000)[1000:]
    chosen, betas, bic_total = f3_search(ltraj, 0.005)
    # planted structure: dx={x,y}, dy={x,y,xz}, dz={xy,z}
    truth = [{"x", "y"}, {"x", "y", "xz"}, {"xy", "z"}]
    struct_hits = sum(1 for c in range(3) if set(chosen[c]) == truth[c])
    pack("fab::eqsearch::f3::structure_recovery",
         "dN_component/dsystem",
         3.0, 0.0,
         "SINDy-style greedy BIC over the 10-term polynomial library, "
         "ONE-STEP scoring only (chaotic free-run error amplification "
         "never enters the fit); count components whose recovered term "
         "set equals the planted Lorenz set (target 3 of 3, band: all)",
         "- greedy selection swaps correlated terms (x vs y on the\n"
         "  attractor) -> measured < 3 declares the identifiability\n"
         "  limit instead of hiding it\n"
         "- long-horizon scoring would fail by construction: measured\n"
         "  amplification +0.35/s (snapshot_delta seed 0)",
         float(struct_hits),
         verdict_fn=lambda m: "pass" if m >= 3.0 else
         ("drift" if m >= 2.0 else "fail"),
         extra={"chosen": chosen, "betas": betas,
                "planted": [sorted(t) for t in truth]})

    # ---------------- F4: nonlinear map recovery + guard --------------
    lseq = [LOGISTIC_X0]
    for _ in range(LOGISTIC_N):
        lseq.append(LOGISTIC_R * lseq[-1] * (1.0 - lseq[-1]))
    r_hat, bic_q, bic_l, slope_l = f4_null_guard(lseq)
    pack("fab::eqsearch::f4::map_recovery",
         "d(r)/dseries",
         LOGISTIC_R, 0.02,
         "fit x_{n+1} = r x (1 - x) to a 400-step logistic series "
         "(planted r=3.7, chaotic regime); report r_hat; BIC of the "
         "quadratic map must beat a linear-map guard (kept in extra)",
         "- chaotic regime: the one-step map is exact but parameter\n"
         "  sensitivity means noise floors appear fast; band is 2%\n"
         "- linear guard wins BIC -> the nonlinear structure is not\n"
         "  identifiable at this series length",
         r_hat,
         extra={"bic_quadratic": bic_q, "bic_linear_guard": bic_l,
                "linear_slope": slope_l,
                "guard_margin": bic_l - bic_q})

    # ---------------- VOID: outside-grammar abstention ----------------
    # The word-from-counts limit is structural; here the probe is
    # empirical: ask the order-2 EXACT integer search to explain the
    # real-valued logistic series. No exact integer (a,b) can.
    void_hits = f1_search([int(round(x * 1000)) for x in lseq[:12]])
    pack("fab::eqsearch::cross::outside_grammar_abstention",
         "dN_invented_structure/dquery",
         0.0, 0.0,
         "feed a real-valued (chaotic map) series, scaled to integers, "
         "to the exact order-2 recurrence search; an honest searcher "
         "returns no structure (VOID), never an invented recurrence "
         "with silent error",
         "- any hit here is a fabricated structure: the grammar is\n"
         "  answering outside its jurisdiction",
         float(len(void_hits)),
         extra={"hits": void_hits})

    # ---------------- record -------------------------------------------
    record = {
        "instrument": "equation_search.py",
        "seed": seed,
        "params": {"noise_levels": NOISE_LEVELS, "null_trials": NULL_TRIALS,
                   "max_terms_f3": MAX_TERMS_F3,
                   "logistic_r": LOGISTIC_R, "logistic_n": LOGISTIC_N},
        "f1": f1_results,
        "f2": {"rows": f2_rows},
        "f3": {"chosen": chosen, "betas": betas, "bic_total": bic_total},
        "f4": {"r_hat": r_hat, "bic_quadratic": bic_q,
               "bic_linear_guard": bic_l},
        "claims": claims,
        "runtime_s": time.time() - t0,
    }
    out = f"equation_search_seed{seed}.json"
    with open(out, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps({c["scope"].split("::")[-2] + "::" + c["scope"].split("::")[-1]:
                      {"predicted": c["value"],
                       "measured": c["measured"],
                       "verdict": c["verdict"]} for c in claims}, indent=2))
    print("record ->", out)
    print("f1 hits:", {k: v["hits"] for k, v in f1_results.items()})
    print("f2 worst:", worst_lam, worst_ome)
    print("f3 chosen:", chosen)
    print("f4 r_hat:", r_hat, " guard margin BIC:", bic_l - bic_q)


if __name__ == "__main__":
    main()
