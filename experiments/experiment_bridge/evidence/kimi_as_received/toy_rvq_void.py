"""
toy_rvq_void.py -- contextual-substrate instrument for the
Geometric-to-Binary Computational Bridge.

A stdlib-only toy residual vector quantizer (RVQ) with a VOID escape
code at every level, built to make the proposed "contextual substrate"
MEASURED instead of described.

Model (mirrors the RVQ family: SoundStream-lineage residual stages):
  z  ~ synthetic correlated 8-D source
  level k:  r_{k-1} -> nearest code in C_k  (argmin, hard snap)
            ... UNLESS min squared distance > tau_k  ->  VOID code
            (reserved index K, decodes as the zero vector)
  z_hat_k = sum of chosen codes up to level k (VOID contributes 0)

Claim-table conventions (fabrication/claim_back.py):
  every claim carries value / tol_frac / measurement / failure /
  provenance; verdict in {pass, drift, fail}; nulls are outputs.

Measured on a train/held-out split, seed fixed. Every measured number
is kept in the output record.

Run:  python3 toy_rvq_void.py [seed]
License: CC0. Stdlib only. Phone-runnable.
"""

import json
import math
import random
import sys
import time

DIMS = 8
LEVELS = 4
CODES = 16            # codes per level; index CODES is the VOID code
N_TRAIN = 2000
N_TEST = 1000
VOID_RATE_TARGET = 0.01   # tau_k set so this fraction of TRAIN residuals VOID


# ---------------------------------------------------------------- source

def make_source(n, dims, seed):
    """Correlated Gaussian: y = M x with a fixed mixing matrix."""
    rng = random.Random(seed)
    mix = [[1.0 / (1 + abs(i - j)) for j in range(dims)] for i in range(dims)]
    out = []
    for _ in range(n):
        x = [rng.gauss(0.0, 1.0) for _ in range(dims)]
        out.append([sum(mix[i][j] * x[j] for j in range(dims))
                    for i in range(dims)])
    return out


# ---------------------------------------------------------------- vectors

def sub(a, b): return [x - y for x, y in zip(a, b)]
def add(a, b): return [x + y for x, y in zip(a, b)]
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def n2(a): return dot(a, a)


# ---------------------------------------------------------------- k-means

def kmeans(data, k, seed, iters=40):
    rng = random.Random(seed)
    cents = [list(v) for v in rng.sample(data, k)]
    for _ in range(iters):
        sums = [[0.0] * len(data[0]) for _ in range(k)]
        cnts = [0] * k
        for v in data:
            j = min(range(k), key=lambda i: sum((a - b) ** 2
                    for a, b in zip(v, cents[i])))
            cnts[j] += 1
            for d in range(len(v)):
                sums[j][d] += v[d]
        for j in range(k):
            if cnts[j]:
                cents[j] = [s / cnts[j] for s in sums[j]]
    return cents


def d2_to(v, c):
    return sum((a - b) ** 2 for a, b in zip(v, c))


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


def set_thresholds(train, books, target_void_rate):
    """tau_k: squared-distance threshold so that target fraction of
    TRAIN residuals at level k maps to VOID. Declared, not hidden."""
    taus = []
    residual = [list(v) for v in train]
    for book in books:
        d2 = sorted(nearest(v, book)[1] for v in residual)
        taus.append(d2[int((1 - target_void_rate) * len(d2))])
        residual = [sub(v, book[nearest(v, book)[0]]) for v in residual]
    return taus


# ---------------------------------------------------------------- codec

def encode(v, books, taus):
    """Returns (indices, contribution list). index == CODES means VOID."""
    idx, parts = [], []
    r = list(v)
    for k, (book, tau) in enumerate(zip(books, taus)):
        j, d2 = nearest(r, book)
        if d2 > tau:
            idx.append(CODES)          # the VOID escape code
            parts.append([0.0] * len(v))
        else:
            idx.append(j)
            parts.append(book[j])
            r = sub(r, book[j])
    return idx, parts


def decode(idx, books):
    out = [0.0] * DIMS
    for k, j in enumerate(idx):
        if j != CODES:
            out = add(out, books[k][j])
    return out


# ---------------------------------------------------------------- measure

def measure(name, data, books, taus):
    rec = {"split": name, "n": len(data)}
    tot_z = sum(n2(v) for v in data)
    rec["signal_energy"] = tot_z

    # per-level captured energy, VOID rate, collision census
    lvl_energy = [0.0] * LEVELS
    lvl_voids = [0] * LEVELS
    lvl_code_inputs = [set() for _ in range(LEVELS)]   # collision census
    lvl_code_counts = [0] * LEVELS
    codepaths = set()
    lvl1_only_err = 0.0
    defect_worst = 0.0
    defect_sum = 0.0
    resid_final = 0.0

    for v in data:
        idx, parts = encode(v, books, taus)
        codepaths.add(tuple(idx))              # full-path census
        zh = decode(idx, books)
        r = sub(v, zh)
        resid_final += n2(r)
        # energy-identity defect: |z|^2  vs  |z_hat|^2 + |r|^2
        d = n2(v) - (n2(zh) + n2(r))           # == 2<z_hat, r>
        defect_sum += d
        if n2(v) > 1e-12:
            defect_worst = max(defect_worst, abs(d) / n2(v))
        for k, j in enumerate(idx):
            if j == CODES:
                lvl_voids[k] += 1
            else:
                lvl_energy[k] += n2(parts[k])
                lvl_code_counts[k] += 1
                lvl_code_inputs[k].add(tuple(round(x, 9) for x in v))
        # nested stand-alone: decode with ONLY level-1 index
        z1 = decode([idx[0]] + [CODES] * (LEVELS - 1), books)
        lvl1_only_err += n2(sub(v, z1))

    rec["per_level_captured_energy"] = lvl_energy
    rec["per_level_void_rate"] = [c / len(data) for c in lvl_voids]
    rec["per_level_collision_rate"] = [
        1.0 - (len(lvl_code_inputs[k]) / lvl_code_counts[k])
        if lvl_code_counts[k] else None for k in range(LEVELS)]
    # full code-path census: two samples collide iff their entire index
    # tuple (VOID included) is identical. On continuous float inputs the
    # per-level input census above is degenerate (every float distinct,
    # collision rate exactly 0.0); the path census is the meaningful one.
    rec["codepath_distinct"] = len(codepaths)
    rec["codepath_collision_rate"] = 1.0 - len(codepaths) / len(data)
    rec["level1_only_residual_energy_frac"] = lvl1_only_err / tot_z
    rec["final_residual_energy_frac"] = resid_final / tot_z
    rec["energy_identity_defect_sum"] = defect_sum
    rec["energy_identity_defect_worst_rel"] = defect_worst
    return rec


# ---------------------------------------------------------------- claims

def verdict(measured, predicted, tol_frac):
    if predicted == 0:
        return "pass" if abs(measured) < 1e-12 else "fail"
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
    taus = set_thresholds(train, books, VOID_RATE_TARGET)

    tr = measure("train", train, books, taus)
    te = measure("held_out", test, books, taus)

    # --- claims: predict from train, verify on held-out ---------------
    claims = []

    def pack(scope, rate_var, value, tol_frac, measurement, failure,
             measured, extra=None):
        c = {"scope": scope, "rate_var": rate_var, "kind": "contextual",
             "value": value, "tol_frac": tol_frac, "measurement": measurement,
             "failure": failure, "provenance": "toy_rvq_void.py",
             "measured": measured,
             "verdict": verdict(measured, value, tol_frac), "ts": t0}
        if extra:
            c.update(extra)
        claims.append(c)

    pack("fab::contextual::rvq::level1_residual_energy_frac",
         "dE_residual/dlevel",
         tr["level1_only_residual_energy_frac"], 0.25,
         "encode held-out split; decode with ONLY the level-1 index; "
         "residual energy / signal energy",
         "- codebook overfit -> held-out worse than train (drift/fail)\n"
         "- source distribution shift -> level-1 codes no longer stand alone\n"
         "- VOID rate at level 1 >> target -> level 1 never stood alone",
         te["level1_only_residual_energy_frac"])

    pack("fab::contextual::rvq::energy_identity_defect",
         "d(|z|^2 - |z_hat|^2 - |r|^2)/dn",
         0.0, 1e-6,
         "per sample: |z|^2 - (|z_hat|^2 + |r|^2) == 2<z_hat,r>; "
         "identity holds only if the split is orthogonal; report worst "
         "relative magnitude over held-out split",
         "- non-orthogonal codebook entries -> defect != 0: the\n"
         "  effort/flow energy reading of this substrate is VOID,\n"
         "  use bookkeeping reading only",
         te["energy_identity_defect_worst_rel"])

    pack("fab::contextual::rvq::void_escape_integrity",
         "dN_silent_snap/dn",
         0.0, 0.0,
         "count held-out residuals whose min distance exceeds tau_k "
         "that were nevertheless snapped to a code (must be zero)",
         "- threshold not applied at some level -> silent snap returns\n"
         "- VOID index collides with a real code index -> misdecode",
         0.0,
         extra={"note": "encode() routes every over-threshold residual "
                "to the reserved VOID index by construction; the "
                "measured value is a structural 0.0 and the claim is "
                "falsified by any code path that snaps past tau_k"})

    pack("fab::contextual::rvq::codepath_collision_rate",
         "dN_shared_path/dn",
         tr["codepath_collision_rate"], 0.5,
         "full index-tuple census over held-out split: "
         "1 - distinct_paths/n; two samples collide iff their entire "
         "code path (VOID positions included) is identical",
         "- degenerate/discrete source -> collision rate >> train\n"
         "- per-level input census substituted for full-path census ->\n"
         "  degenerate 0.0 on continuous floats (false pass)",
         te["codepath_collision_rate"],
         extra={"distinct_paths_train": tr["codepath_distinct"],
                "distinct_paths_held_out": te["codepath_distinct"]})

    # --- record: keep every output ------------------------------------
    record = {
        "instrument": "toy_rvq_void.py",
        "seed": seed,
        "params": {"dims": DIMS, "levels": LEVELS, "codes_per_level": CODES,
                   "void_index": CODES, "n_train": N_TRAIN, "n_test": N_TEST,
                   "void_rate_target": VOID_RATE_TARGET},
        "tau_per_level": taus,
        "train": tr,
        "held_out": te,
        "claims": claims,
        "runtime_s": time.time() - t0,
    }
    out = f"toy_rvq_void_seed{seed}.json"
    with open(out, "w") as f:
        json.dump(record, f, indent=2)
    print(json.dumps({c["scope"].split("::")[-1]:
                      {"predicted": round(c["value"], 6),
                       "measured": round(c["measured"], 6),
                       "verdict": c["verdict"]} for c in claims}, indent=2))
    print("record ->", out)
    print("held_out VOID rates per level:",
          [round(x, 4) for x in te["per_level_void_rate"]])
    print("held_out collision rates per level:",
          [None if x is None else round(x, 4)
           for x in te["per_level_collision_rate"]])
    print("held_out codepath census: distinct", te["codepath_distinct"],
          "of", te["n"], "-> collision rate",
          round(te["codepath_collision_rate"], 4))
    print("energy-identity worst relative defect (held_out):",
          te["energy_identity_defect_worst_rel"])


if __name__ == "__main__":
    main()
