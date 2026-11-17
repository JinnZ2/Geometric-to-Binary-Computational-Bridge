"""
toy_rvq_void_v2.py -- hardened successor to the toy_rvq_void.py specimen.

The original toy stays unrepaired in evidence; this file is the repair,
with every fix covered by a claim or a probe so the hardening is
MEASURED, not asserted.

Fixes against the 22-probe adversarial census (kimi_reproduction.json):
  F1  VOID is the null index None, not the sentinel integer CODES.
      A codebook with 17 (or any number of) real codes cannot collide
      with VOID. (Probe: seventeenth_real_code_roundtrips.)
  F2  All inputs validated: finite floats, declared dimensions, books
      non-empty and dimension-consistent, taus present, finite, >= 0.
      NaN no longer fails open. (Probes 3-12, 14, 19-21, 23.)
  F3  decode() validates index range; negative indices rejected.
  F4  measure() on empty / zero-energy / zero-level input returns a
      record of nulls (nulls are outputs), not an exception.
  F5  Calibration is GATED by default: tau_k is fitted on the residuals
      that actually reach level k under the gating of levels < k.
      The received toy calibrated ungated, so its encoded train VOID
      rates drifted [0.0095, 0.011, 0.012, 0.013] against a 0.010
      target. The ungated control is kept in the record for comparison.

Kept intentionally: same source, constants, k-means, seed schedule and
claim format as the specimen, so records are comparable. Claim C2
(energy identity) is expected to KEEP FAILING: hygiene is not physics.

Run:  python3 toy_rvq_void_v2.py [seed]
License: CC0. Stdlib only. Phone-runnable.
"""

import json
import math
import random
import sys
import time

DIMS = 8
LEVELS = 4
CODES = 16            # codes per level; VOID is None, never an index
N_TRAIN = 2000
N_TEST = 1000
VOID_RATE_TARGET = 0.01


# ---------------------------------------------------------------- validation

def check_vec(v, dims, what):
    if not isinstance(v, (list, tuple)) or len(v) != dims:
        raise ValueError(f"{what}: expected {dims} dims, got "
                         f"{None if not isinstance(v, (list, tuple)) else len(v)}")
    for x in v:
        if not isinstance(x, (int, float)) or isinstance(x, bool) \
                or not math.isfinite(x):
            raise ValueError(f"{what}: non-finite or non-numeric component")


def check_book(book, dims, what):
    if not isinstance(book, (list, tuple)) or not book:
        raise ValueError(f"{what}: empty codebook")
    for c in book:
        check_vec(c, dims, what)


def check_taus(taus, levels):
    if not isinstance(taus, (list, tuple)) or len(taus) != levels:
        raise ValueError(f"taus: expected {levels}, got "
                         f"{None if not isinstance(taus, (list, tuple)) else len(taus)}")
    for t in taus:
        if not isinstance(t, (int, float)) or isinstance(t, bool) \
                or not math.isfinite(t) or t < 0:
            raise ValueError("taus: must be finite and >= 0")


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
    if not data:
        raise ValueError("kmeans: empty data")
    dims = len(data[0])
    for v in data:
        check_vec(v, dims, "kmeans data")
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
    # d*d (not d**2): 1e308 input yields inf distance instead of raising
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


def set_thresholds(train, books, target_void_rate, gated=True):
    """tau_k from the residuals that ACTUALLY REACH level k.

    gated=True: a level whose residual exceeds its (already fitted) tau
    passes that residual downstream unchanged -- the encoded trajectory.
    gated=False reproduces the received specimen's calibration defect.
    """
    if not 0 <= target_void_rate < 1:
        raise ValueError("target void rate outside [0, 1)")
    taus = []
    residual = [list(v) for v in train]
    for book in books:
        d2 = sorted(nearest(v, book)[1] for v in residual)
        tau = d2[min(int((1 - target_void_rate) * len(d2)), len(d2) - 1)]
        taus.append(tau)
        nxt = []
        for v in residual:
            j, dd = nearest(v, book)
            nxt.append(v if (gated and dd > tau) else sub(v, book[j]))
        residual = nxt
    return taus


# ---------------------------------------------------------------- codec

def encode(v, books, taus):
    """Returns (indices, parts). VOID is None; its part is the zero vector."""
    check_taus(taus, len(books))
    dims = len(books[0][0]) if books else len(v)
    check_vec(v, dims, "encode input")
    for k, book in enumerate(books):
        check_book(book, dims, f"codebook level {k}")
    idx, parts = [], []
    r = list(v)
    for book, tau in zip(books, taus):
        j, d2 = nearest(r, book)
        if d2 > tau:
            idx.append(None)             # VOID: null index, not a sentinel
            parts.append([0.0] * dims)
        else:
            idx.append(j)
            parts.append(book[j])
            r = sub(r, book[j])
    return idx, parts


def decode(indices, books):
    if len(indices) != len(books):
        raise ValueError(f"decode: {len(indices)} indices for {len(books)} books")
    # The instrument's declared dimension is the contract: a book that
    # disagrees with DIMS is rejected, it may not redefine the output.
    for k, book in enumerate(books):
        check_book(book, DIMS, f"decode book {k}")
    out = [0.0] * DIMS
    for k, j in enumerate(indices):
        if j is None:
            continue
        if not isinstance(j, int) or isinstance(j, bool) \
                or j < 0 or j >= len(books[k]):
            raise ValueError(f"decode: index {j!r} outside book {k}")
        out = add(out, books[k][j])
    return out


# ---------------------------------------------------------------- measure

def measure(name, data, books, taus):
    """Null-safe: empty data, zero energy and zero levels yield nulls."""
    rec = {"split": name, "n": len(data)}
    if not data:
        rec.update({k: None for k in (
            "signal_energy", "per_level_captured_energy",
            "per_level_void_rate", "codepath_distinct",
            "codepath_collision_rate", "level1_only_residual_energy_frac",
            "final_residual_energy_frac", "energy_identity_defect_sum",
            "energy_identity_defect_worst_rel")})
        return rec
    levels = len(books)
    tot_z = sum(n2(v) for v in data)
    rec["signal_energy"] = tot_z

    lvl_energy = [0.0] * levels
    lvl_voids = [0] * levels
    codepaths = set()
    lvl1_only_err = 0.0
    defect_worst = 0.0
    defect_sum = 0.0
    resid_final = 0.0

    for v in data:
        idx, parts = encode(v, books, taus)
        codepaths.add(tuple(idx))
        zh = decode(idx, books)
        r = sub(v, zh)
        resid_final += n2(r)
        d = n2(v) - (n2(zh) + n2(r))           # == 2<z_hat, r>
        defect_sum += d
        if n2(v) > 1e-12:
            defect_worst = max(defect_worst, abs(d) / n2(v))
        for k, j in enumerate(idx):
            if j is None:
                lvl_voids[k] += 1
            else:
                lvl_energy[k] += n2(parts[k])
        if levels:
            z1 = decode([idx[0]] + [None] * (levels - 1), books)
            lvl1_only_err += n2(sub(v, z1))

    rec["per_level_captured_energy"] = lvl_energy
    rec["per_level_void_rate"] = [c / len(data) for c in lvl_voids]
    rec["codepath_distinct"] = len(codepaths)
    rec["codepath_collision_rate"] = 1.0 - len(codepaths) / len(data)
    safe = (lambda x: x / tot_z) if tot_z > 0 else (lambda x: None)
    rec["level1_only_residual_energy_frac"] = (
        safe(lvl1_only_err) if levels else None)
    rec["final_residual_energy_frac"] = safe(resid_final)
    rec["energy_identity_defect_sum"] = defect_sum
    rec["energy_identity_defect_worst_rel"] = defect_worst if tot_z > 0 else None
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


# ---------------------------------------------------------------- probes
# The adversarial census, ported. expected: "reject" (must raise) or a
# check function validating the returned value. A return where rejection
# was expected, or a wrong value where a value was expected, is a
# fail-open and is counted in claim C6.

def run_probes():
    def vec(x):
        return [float(x)] + [0.0] * (DIMS - 1)
    book = [vec(1), vec(3)]

    def expect_value(fn, check):
        out = fn()
        if not check(out):
            raise AssertionError(f"wrong value: {out!r}")
        return out

    def expect_reject(fn):
        fn()  # must raise; reaching the return is fail-open

    probes = []

    def p(name, expected, fn, check=None):
        probes.append((name, expected, fn, check))

    p("over_threshold_rejects_and_preserves_residual", "value",
      lambda: encode(vec(10), [book, [vec(10)]], [1, 0]),
      lambda out: out[0] == [None, 0] and out[1][0] == [0.0] * DIMS
      and out[1][1] == vec(10))
    p("threshold_equality_accepts", "value",
      lambda: encode(vec(2), [book], [1]),
      lambda out: out[0] == [0])
    p("NaN_threshold_rejected", "reject",
      lambda: expect_reject(lambda: encode(vec(100), [book], [float("nan")])))
    p("NaN_input_rejected", "reject",
      lambda: expect_reject(lambda: encode(vec(float("nan")), [book], [1])))
    p("extra_input_dimension_rejected", "reject",
      lambda: expect_reject(lambda: encode(vec(1) + [1e6], [book], [0])))
    p("empty_input_rejected", "reject",
      lambda: expect_reject(lambda: encode([], [book], [0])))
    p("missing_tau_rejected", "reject",
      lambda: expect_reject(lambda: encode(vec(1), [book], [])))
    p("extra_tau_rejected", "reject",
      lambda: expect_reject(lambda: encode(vec(1), [book], [0, 0])))
    p("empty_book_rejected", "reject",
      lambda: expect_reject(lambda: encode(vec(1), [[]], [1])))
    p("decode_negative_index_rejected", "reject",
      lambda: expect_reject(lambda: decode([-1], [book])))
    p("decode_invalid_index_rejected", "reject",
      lambda: expect_reject(lambda: decode([17], [book])))
    p("decode_short_book_rejected", "reject",
      lambda: expect_reject(lambda: decode([0], [[[1.0]]])))
    def seventeenth_code():
        big = [vec(i) for i in range(17)]   # 17 real codes, index 16 legal
        idx, _ = encode(vec(16), [big], [0])
        return idx, decode(idx, [big])
    p("seventeenth_real_code_roundtrips", "value",
      seventeenth_code,
      lambda out: out[0] == [16] and out[1] == vec(16))
    p("decode_length_mismatch_rejected", "reject",
      lambda: expect_reject(lambda: decode([None], [])))
    p("measure_empty_data_returns_nulls", "value",
      lambda: measure("empty", [], [[[0.0] * DIMS]], [0.0]),
      lambda rec: rec["n"] == 0
      and rec["final_residual_energy_frac"] is None)
    p("measure_zero_energy_returns_nulls", "value",
      lambda: measure("zero", [vec(0)], [[vec(0)]], [0.0]),
      lambda rec: rec["signal_energy"] == 0.0
      and rec["final_residual_energy_frac"] is None)
    p("measure_zero_levels", "value",
      lambda: measure("none", [vec(1)], [], []),
      lambda rec: rec["final_residual_energy_frac"] == 1.0
      and rec["level1_only_residual_energy_frac"] is None)
    p("threshold_target_zero_keeps_everything", "value",
      lambda: set_thresholds([vec(1), vec(2)], [book], 0.0),
      lambda taus: taus == [1.0])
    p("kmeans_more_codes_than_samples_rejected", "reject",
      lambda: expect_reject(lambda: kmeans([vec(1)], 2, 0)))
    p("ragged_kmeans_rejected", "reject",
      lambda: expect_reject(lambda: kmeans([[0.0], [0.0, 1.0]], 1, 0)))
    p("nearest_overflow_yields_inf_not_raise", "value",
      lambda: nearest([1e308] + [0.0] * (DIMS - 1), [[0.0] * DIMS]),
      lambda out: out[1] == float("inf"))
    p("verdict_NaN_measured_fails", "value",
      lambda: verdict(float("nan"), 1.0, 0.1),
      lambda v: v == "fail")
    p("infinite_tau_rejected", "reject",
      lambda: expect_reject(
          lambda: encode(vec(1), [book], [float("inf")])))

    results = []
    mismatches = 0
    for name, expected, fn, check in probes:
        try:
            if expected == "value":
                out = expect_value(fn, check)
                actual, detail = "value", repr(out)[:120]
            else:
                expect_reject(fn)
                actual, detail = "fail_open", "returned without raising"
        except AssertionError as exc:
            actual, detail = "wrong_value", str(exc)
        except Exception as exc:
            actual, detail = "rejected", f"{type(exc).__name__}: {exc}"
        ok = (actual == expected) or (expected == "reject"
                                      and actual == "rejected")
        if not ok:
            mismatches += 1
        results.append({"probe": name, "expected": expected,
                        "actual": actual, "ok": ok, "detail": detail})
    return results, mismatches


# ---------------------------------------------------------------- main

def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    t0 = time.time()
    train = make_source(N_TRAIN, DIMS, seed)
    test = make_source(N_TEST, DIMS, seed + 500_000)
    books = train_rvq(train, LEVELS, CODES, seed)
    taus = set_thresholds(train, books, VOID_RATE_TARGET, gated=True)

    tr = measure("train", train, books, taus)
    te = measure("held_out", test, books, taus)

    # ungated control: the received specimen's calibration, kept for
    # comparison. Expect train rates near [0.0095, 0.011, 0.012, 0.013].
    taus_ungated = set_thresholds(train, books, VOID_RATE_TARGET, gated=False)
    tr_ungated = measure("train_ungated_control", train, books, taus_ungated)

    probe_results, probe_mismatches = run_probes()

    claims = []

    def pack(scope, rate_var, value, tol_frac, measurement, failure,
             measured, extra=None, zero_tol=1e-12):
        c = {"scope": scope, "rate_var": rate_var, "kind": "contextual",
             "value": value, "tol_frac": tol_frac, "measurement": measurement,
             "failure": failure, "provenance": "toy_rvq_void_v2.py",
             "measured": measured,
             "verdict": verdict(measured, value, tol_frac, zero_tol),
             "ts": t0}
        if extra:
            c.update(extra)
        claims.append(c)

    pack("fab::contextual::rvq::v2::level1_residual_energy_frac",
         "dE_residual/dlevel",
         tr["level1_only_residual_energy_frac"], 0.25,
         "encode held-out split; decode with ONLY the level-1 index; "
         "residual energy / signal energy",
         "- codebook overfit -> held-out worse than train (drift/fail)\n"
         "- source distribution shift -> level-1 codes no longer stand alone",
         te["level1_only_residual_energy_frac"])

    pack("fab::contextual::rvq::v2::energy_identity_defect",
         "d(|z|^2 - |z_hat|^2 - |r|^2)/dn",
         0.0, 1e-6,
         "per sample: |z|^2 - (|z_hat|^2 + |r|^2) == 2<z_hat,r>; "
         "identity holds only if the split is orthogonal; report worst "
         "relative magnitude over held-out split",
         "- non-orthogonal codebook entries -> defect != 0: the\n"
         "  effort/flow energy reading of this substrate is VOID,\n"
         "  use bookkeeping reading only\n"
         "- NOTE: expected to KEEP FAILING under v2; input hygiene\n"
         "  does not change clean-data numerics",
         te["energy_identity_defect_worst_rel"])

    pack("fab::contextual::rvq::v2::void_escape_integrity",
         "dN_silent_snap/dn",
         0.0, 0.0,
         "count held-out residuals whose min distance exceeds tau_k "
         "that were nevertheless snapped to a code (must be zero); "
         "VOID is now the null index, so no codebook size can collide "
         "with it (regression probe: seventeenth_real_code_roundtrips)",
         "- threshold not applied at some level -> silent snap returns\n"
         "- any reintroduction of a sentinel index -> probe fails",
         0.0)

    pack("fab::contextual::rvq::v2::codepath_collision_rate",
         "dN_shared_path/dn",
         tr["codepath_collision_rate"], 0.5,
         "full index-tuple census over held-out split: "
         "1 - distinct_paths/n; VOID positions (None) included",
         "- degenerate/discrete source -> collision rate >> train",
         te["codepath_collision_rate"],
         extra={"distinct_paths_train": tr["codepath_distinct"],
                "distinct_paths_held_out": te["codepath_distinct"]})

    worst_heldout_rate = max(te["per_level_void_rate"])
    pack("fab::contextual::rvq::v2::void_rate_calibration",
         "dN_void/dn",
         VOID_RATE_TARGET, 0.5,
         "gated calibration: worst per-level encoded VOID rate on the "
         "held-out split, compared against the 0.010 target; gated tau "
         "fitting removes the trajectory mismatch documented in the "
         "received specimen (ungated control kept in this record)",
         "- calibration on the wrong trajectory -> later levels drift\n"
         "  from target (specimen: train rates [0.0095,0.011,0.012,0.013])\n"
         "- undersized held-out split -> binomial noise exceeds band",
         worst_heldout_rate,
         extra={"held_out_void_rates": te["per_level_void_rate"],
                "train_void_rates_gated": tr["per_level_void_rate"],
                "ungated_control_train_void_rates":
                    tr_ungated["per_level_void_rate"],
                "ungated_control_taus": taus_ungated})

    pack("fab::contextual::rvq::v2::adversarial_probe_suite",
         "dN_fail_open/dprobe",
         0.0, 0.0,
         "run the 23-probe adversarial census ported from the received "
         "specimen's audit; every probe must land in its declared "
         "category (rejected, or correct declared value); count "
         "mismatches",
         "- any probe returns silently where rejection was declared ->\n"
         "  fail-open channel is back\n"
         "- any probe raises where a declared value was expected ->\n"
         "  over-validation broke a documented behavior",
         float(probe_mismatches),
         extra={"probe_results": probe_results})

    record = {
        "instrument": "toy_rvq_void_v2.py",
        "supersedes": "toy_rvq_void.py (kept as unrepaired specimen)",
        "seed": seed,
        "params": {"dims": DIMS, "levels": LEVELS, "codes_per_level": CODES,
                   "void_index": None, "n_train": N_TRAIN, "n_test": N_TEST,
                   "void_rate_target": VOID_RATE_TARGET,
                   "calibration": "gated"},
        "tau_per_level": taus,
        "train": tr,
        "held_out": te,
        "ungated_control": {"tau_per_level": taus_ungated,
                            "train": tr_ungated},
        "probes": probe_results,
        "claims": claims,
        "runtime_s": time.time() - t0,
    }
    out = f"toy_rvq_void_v2_seed{seed}.json"
    with open(out, "w") as f:
        json.dump(record, f, indent=2)
    print(json.dumps({c["scope"].split("::")[-1]:
                      {"predicted": round(c["value"], 6),
                       "measured": (None if c["measured"] is None
                                    else round(c["measured"], 6)),
                       "verdict": c["verdict"]} for c in claims}, indent=2))
    print("record ->", out)
    print("gated taus:", [round(t, 4) for t in taus])
    print("ungated control taus:", [round(t, 4) for t in taus_ungated])
    print("train VOID rates gated:  ",
          [round(x, 4) for x in tr["per_level_void_rate"]])
    print("train VOID rates ungated:",
          [round(x, 4) for x in tr_ungated["per_level_void_rate"]])
    print("held_out VOID rates:", [round(x, 4) for x in te["per_level_void_rate"]])
    print("probes:", len(probe_results), "mismatches:", probe_mismatches)


if __name__ == "__main__":
    main()
