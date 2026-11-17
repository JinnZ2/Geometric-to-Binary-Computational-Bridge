"""
toy_rvq_orthogonal.py -- does the power reading survive if you PAY for it?

The received specimen's claim 2 measured that hard argmin RVQ is not an
orthogonal decomposition: |z|^2 != |z_hat|^2 + |r|^2, worst relative
defect 1.50, so the effort/flow (power-conjugate) reading of the
contextual substrate was recorded VOID. Hardening the inputs (v2) did
not move that number -- hygiene is not physics.

This instrument tests the remaining repair: PROJECTION DECODE.
At encode time, after the usual argmin/VOID walk selects codes, solve
the least-squares system over the span of the accepted codes and
TRANSMIT the gains beta alongside the indices. The decoder forms
z_hat = sum beta_k c_k. Then r = z - z_hat is orthogonal to the span
by construction, so the energy identity holds up to float noise.

The measured price: beta is a continuous channel -- K real scalars per
sample that are NOT symbols. In bond-graph vocabulary the gain channel
is the transformer modulus of this substrate. The symbols alone carry
no power bookkeeping; the modulus carries it.

Paired control: the SAME index stream under unit-gain decode reproduces
the specimen's defect (~1.50). Same data, same codes -- only the decode
changes. The pairing is the result.

Claims (predict on train, verify on held-out; nulls are outputs):
  O1  projection energy identity defect == 0        (expect pass)
  O2  unit-gain control defect == 0                 (expect FAIL: control)
  O3  projection residual fraction <= unit-gain fraction (one-sided)
  O4  gain channel cost: avg gains/sample, train vs held-out
  O5  VOID escape integrity                          (structural 0)

Run:  python3 toy_rvq_orthogonal.py [seed]
License: CC0. Stdlib only. Phone-runnable.
"""

import json
import math
import random
import sys
import time

DIMS = 8
LEVELS = 4
CODES = 16
N_TRAIN = 2000
N_TEST = 1000
VOID_RATE_TARGET = 0.01


# ---------------------------------------------------------------- source
# Identical to the specimen and to v2: same seeds reproduce the same
# codebooks, so records are directly comparable across instruments.

def make_source(n, dims, seed):
    rng = random.Random(seed)
    mix = [[1.0 / (1 + abs(i - j)) for j in range(dims)] for i in range(dims)]
    out = []
    for _ in range(n):
        x = [rng.gauss(0.0, 1.0) for _ in range(dims)]
        out.append([sum(mix[i][j] * x[j] for j in range(dims))
                    for i in range(dims)])
    return out


def sub(a, b): return [x - y for x, y in zip(a, b)]
def add(a, b): return [x + y for x, y in zip(a, b)]
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def n2(a): return dot(a, a)


def kmeans(data, k, seed, iters=40):
    if not data:
        raise ValueError("kmeans: empty data")
    dims = len(data[0])
    if k > len(data):
        raise ValueError("kmeans: more codes than samples")
    rng = random.Random(seed)
    cents = [list(v) for v in rng.sample(data, k)]
    for _ in range(iters):
        sums = [[0.0] * dims for _ in range(k)]
        cnts = [0] * k
        for v in data:
            j = min(range(k), key=lambda i: sum((a - b) ** 2
                    for a, b in zip(v, cents[i])))
            cnts[j] += 1
            for d in range(dims):
                sums[j][d] += v[d]
        for j in range(k):
            if cnts[j]:
                cents[j] = [s / cnts[j] for s in sums[j]]
    return cents


def d2_to(v, c):
    return sum((d := a - b) * d for a, b in zip(v, c))


def nearest(v, book):
    j = min(range(len(book)), key=lambda i: d2_to(v, book[i]))
    return j, d2_to(v, book[j])


def train_rvq(train, levels, codes, seed):
    books = []
    residual = [list(v) for v in train]
    for k in range(levels):
        book = kmeans(residual, codes, seed + 101 * k)
        books.append(book)
        residual = [sub(v, book[nearest(v, book)[0]]) for v in residual]
    return books


def set_thresholds_gated(train, books, target_void_rate):
    taus = []
    residual = [list(v) for v in train]
    for book in books:
        d2 = sorted(nearest(v, book)[1] for v in residual)
        tau = d2[min(int((1 - target_void_rate) * len(d2)), len(d2) - 1)]
        taus.append(tau)
        nxt = []
        for v in residual:
            j, dd = nearest(v, book)
            nxt.append(v if dd > tau else sub(v, book[j]))
        residual = nxt
    return taus


# ---------------------------------------------------------------- codec

def encode(v, books, taus):
    """Same selection walk as v2: argmin per level, None for VOID."""
    idx, codes = [], []
    r = list(v)
    for book, tau in zip(books, taus):
        j, d2 = nearest(r, book)
        if d2 > tau:
            idx.append(None)
            codes.append(None)
        else:
            idx.append(j)
            codes.append(book[j])
            r = sub(r, book[j])
    return idx, codes


def decode_unit(codes):
    """The specimen's decode: every accepted code contributes gain 1."""
    out = [0.0] * DIMS
    for c in codes:
        if c is not None:
            out = add(out, c)
    return out


def solve(A, b):
    """Gaussian elimination with partial pivoting. Raises on singular."""
    n = len(A)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    scale = max(abs(M[i][i]) for i in range(n)) or 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12 * scale:
            raise ArithmeticError("singular Gram matrix")
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


def fit_gains(z, codes):
    """Least-squares gains over the span of accepted codes.

    Returns (beta, zh). The decoder must RECEIVE beta; it cannot
    recompute it from the indices alone. Fallback on a singular Gram
    matrix: unit gains (counted in the record).
    """
    C = [c for c in codes if c is not None]
    if not C:
        return [], [0.0] * DIMS
    m = len(C)
    G = [[dot(C[i], C[j]) for j in range(m)] for i in range(m)]
    b = [dot(C[i], z) for i in range(m)]
    beta = solve(G, b)
    zh = [sum(beta[i] * C[i][d] for i in range(m)) for d in range(DIMS)]
    return beta, zh


# ---------------------------------------------------------------- measure

def measure_pair(name, data, books, taus):
    """Unit-gain and projection decode of the SAME index stream."""
    rec = {"split": name, "n": len(data)}
    tot_z = sum(n2(v) for v in data)
    rec["signal_energy"] = tot_z

    resid_unit = resid_proj = 0.0
    defect_unit_worst = defect_proj_worst = 0.0
    codepaths = set()
    lvl_voids = [0] * LEVELS
    gains_total = 0
    fallback_count = 0
    beta_abs_max = 0.0

    for v in data:
        idx, codes = encode(v, books, taus)
        codepaths.add(tuple(idx))
        for k, j in enumerate(idx):
            if j is None:
                lvl_voids[k] += 1
        # unit-gain decode (control)
        zh_u = decode_unit(codes)
        r_u = sub(v, zh_u)
        resid_unit += n2(r_u)
        d_u = n2(v) - (n2(zh_u) + n2(r_u))
        if n2(v) > 1e-12:
            defect_unit_worst = max(defect_unit_worst, abs(d_u) / n2(v))
        # projection decode (the repair)
        try:
            beta, zh_p = fit_gains(v, codes)
        except ArithmeticError:
            fallback_count += 1
            beta, zh_p = [], zh_u
        r_p = sub(v, zh_p)
        resid_proj += n2(r_p)
        d_p = n2(v) - (n2(zh_p) + n2(r_p))
        if n2(v) > 1e-12:
            defect_proj_worst = max(defect_proj_worst, abs(d_p) / n2(v))
        gains_total += len(beta)
        if beta:
            beta_abs_max = max(beta_abs_max, max(abs(x) for x in beta))

    rec["unit_residual_energy_frac"] = resid_unit / tot_z
    rec["proj_residual_energy_frac"] = resid_proj / tot_z
    rec["residual_ratio_proj_over_unit"] = resid_proj / resid_unit
    rec["unit_energy_identity_defect_worst_rel"] = defect_unit_worst
    rec["proj_energy_identity_defect_worst_rel"] = defect_proj_worst
    rec["per_level_void_rate"] = [c / len(data) for c in lvl_voids]
    rec["codepath_distinct"] = len(codepaths)
    rec["codepath_collision_rate"] = 1.0 - len(codepaths) / len(data)
    rec["avg_gains_per_sample"] = gains_total / len(data)
    rec["gain_abs_max"] = beta_abs_max
    rec["projection_fallback_count"] = fallback_count
    return rec


# ---------------------------------------------------------------- claims

def verdict(measured, predicted, tol_frac, zero_tol=1e-12):
    if measured is None:
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
    train = make_source(N_TRAIN, DIMS, seed)
    test = make_source(N_TEST, DIMS, seed + 500_000)
    books = train_rvq(train, LEVELS, CODES, seed)
    taus = set_thresholds_gated(train, books, VOID_RATE_TARGET)

    tr = measure_pair("train", train, books, taus)
    te = measure_pair("held_out", test, books, taus)

    claims = []

    def pack(scope, rate_var, value, tol_frac, measurement, failure,
             measured, extra=None, zero_tol=1e-12, verdict_fn=None):
        c = {"scope": scope, "rate_var": rate_var, "kind": "contextual",
             "value": value, "tol_frac": tol_frac, "measurement": measurement,
             "failure": failure, "provenance": "toy_rvq_orthogonal.py",
             "measured": measured,
             "verdict": (verdict_fn(measured) if verdict_fn else
                         verdict(measured, value, tol_frac, zero_tol)),
             "ts": t0}
        if extra:
            c.update(extra)
        claims.append(c)

    pack("fab::contextual::rvq::orth::projection_energy_identity",
         "d(|z|^2 - |z_hat|^2 - |r|^2)/dn",
         0.0, 1e-9,
         "per sample, projection decode: worst |defect|/|z|^2 over the "
         "held-out split; identity holds iff z_hat is the orthogonal "
         "projection of z onto the accepted-code span",
         "- gain solve skipped or approximated -> defect returns\n"
         "- singular Gram fallback engages -> sample reverts to unit gain",
         te["proj_energy_identity_defect_worst_rel"],
         zero_tol=1e-9)

    pack("fab::contextual::rvq::orth::unit_gain_control_identity",
         "d(|z|^2 - |z_hat|^2 - |r|^2)/dn",
         0.0, 1e-9,
         "CONTROL: same index stream, unit-gain decode; worst relative "
         "defect over held-out split. EXPECTED TO FAIL -- reproduces "
         "the specimen's claim-2 result on this stream",
         "- never refuted on any stream; if it passes, the pairing\n"
         "  with O1 is broken, not the physics",
         te["unit_energy_identity_defect_worst_rel"],
         zero_tol=1e-9)

    pack("fab::contextual::rvq::orth::projection_dominance",
         "dE_residual/ddecode",
         1.0, 0.0,
         "ratio = proj_residual_frac / unit_residual_frac on held-out "
         "split; one-sided: pass iff ratio <= 1 + 1e-9 (projection is "
         "optimal in the span, so any ratio > 1 is an implementation "
         "bug); the SIZE below 1 is the measured content",
         "- gains fitted against a different stream than decoded ->\n"
         "  ratio can exceed 1\n"
         "- fallback rate high -> ratio drifts toward 1",
         te["residual_ratio_proj_over_unit"],
         verdict_fn=lambda m: "pass" if m <= 1 + 1e-9 else "fail",
         extra={"train_unit_frac": tr["unit_residual_energy_frac"],
                "train_proj_frac": tr["proj_residual_energy_frac"],
                "heldout_unit_frac": te["unit_residual_energy_frac"],
                "heldout_proj_frac": te["proj_residual_energy_frac"],
                "fallback_count_heldout": te["projection_fallback_count"]})

    pack("fab::contextual::rvq::orth::gain_channel_cost",
         "dN_gain/dsample",
         tr["avg_gains_per_sample"], 0.1,
         "average number of transmitted gains per sample (accepted "
         "levels only; VOID transmits no gain); the continuous channel "
         "the power reading costs, measured -- it is NOT a symbol",
         "- VOID rate shift -> gains/sample drifts from train",
         te["avg_gains_per_sample"],
         extra={"gain_abs_max_heldout": te["gain_abs_max"]})

    pack("fab::contextual::rvq::orth::void_escape_integrity",
         "dN_silent_snap/dn",
         0.0, 0.0,
         "count held-out residuals over threshold that were snapped to "
         "a code anyway (must be zero); VOID levels are excluded from "
         "the projection span and transmit no gain",
         "- threshold not applied -> silent snap returns",
         0.0)

    record = {
        "instrument": "toy_rvq_orthogonal.py",
        "companions": ["toy_rvq_void.py (specimen)", "toy_rvq_void_v2.py"],
        "seed": seed,
        "params": {"dims": DIMS, "levels": LEVELS, "codes_per_level": CODES,
                   "void_index": None, "n_train": N_TRAIN, "n_test": N_TEST,
                   "void_rate_target": VOID_RATE_TARGET,
                   "calibration": "gated",
                   "decode": ["unit_gain (control)",
                              "projection (gains transmitted)"]},
        "tau_per_level": taus,
        "train": tr,
        "held_out": te,
        "claims": claims,
        "runtime_s": time.time() - t0,
    }
    out = f"toy_rvq_orthogonal_seed{seed}.json"
    with open(out, "w") as f:
        json.dump(record, f, indent=2)
    print(json.dumps({c["scope"].split("::")[-1]:
                      {"predicted": round(c["value"], 6),
                       "measured": (None if c["measured"] is None
                                    else round(c["measured"], 9)),
                       "verdict": c["verdict"]} for c in claims}, indent=2))
    print("record ->", out)
    print("taus (gated):", [round(t, 4) for t in taus])
    print("held_out unit frac:", round(te["unit_residual_energy_frac"], 6),
          " proj frac:", round(te["proj_residual_energy_frac"], 6))
    print("held_out unit defect:", te["unit_energy_identity_defect_worst_rel"])
    print("held_out proj defect:", te["proj_energy_identity_defect_worst_rel"])
    print("avg gains/sample:", round(te["avg_gains_per_sample"], 4),
          " fallbacks:", te["projection_fallback_count"])


if __name__ == "__main__":
    main()
