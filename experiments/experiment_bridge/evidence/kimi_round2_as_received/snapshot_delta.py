"""
snapshot_delta.py -- checkpoint + delta computation, measured.

The idea (user's): run the equations to a point, take a snapshot, then
do the calculations BETWEEN snapshots -- the difference -- instead of
redoing the whole prefix every time. This instrument measures when
that is exact, when it drifts, and what the refresh costs.

The codec mapping carries over from toy_rvq_void*.py word for word:
    snapshot      = level-k reconstruction z_hat_k
    delta         = residual r_k
    refresh (VOID escape) = resync when the delta crosses tau

Two systems, three failure modes, nine claims.

SYSTEM A -- exact Fibonacci word inflation (substitution L->LS, S->L).
  The stepper is context-free: the next word depends ONLY on the
  current word. Resume from a word snapshot is exact integer/string
  work; drift cannot exist. The hidden-state refuter lives here too:
  the letter-count chain (L,S)->(L+S,L) resumes COUNTS exactly, but
  counts are a many-to-one summary -- the word cannot be resumed from
  its counts (the same many-to-one species as the RVQ codepath
  census). Note on state depth: the substitution view needs depth 1
  (Markov); the concatenation view w_{n+1} = w_n . w_{n-1} needs
  depth 2. Same system, different snapshot content. (Kept output:
  both views verified against each other.)

SYSTEM B -- float ODEs, RK4.
  B-sink:   spiral x' = lambda*x - omega*y, y' = omega*x + lambda*y,
            lambda < 0. Exact reference known; perturbations DECAY.
  B-lorenz: sigma=10, rho=28, beta=8/3. Chaotic; perturbations grow
            ~exp(Lambda*t). Lossy-snapshot resume is expected to FAIL
            here -- a designed fail, like the specimen's claim 2.
  Claims cover: bitwise resume from an EXACT snapshot (no new error),
  drift after a QUANTIZED snapshot (sink bounded, Lorenz VOID),
  adaptive refresh = dead-reckoning with a cheap Euler receiver and
  resync when |delta| > tau (the escape code; refresh count is the
  bitrate), and random-access speedup vs storage paid.

Claim format follows fabrication/claim_back.py: value / tol_frac /
measurement / failure / provenance; verdict in {pass, drift, fail,
void}. Nulls are outputs. Every measured number is kept in the record.

Run:  python3 snapshot_delta.py [seed]
License: CC0. Stdlib only. Phone-runnable.
"""

import hashlib
import json
import math
import random
import sys
import time

# ------------------------------------------------------------------ params

FIB_LEVELS = 25          # |w_25| = F(27) = 196418 letters
FIB_SNAP_EVERY = 5

SINK_LAMBDA = -0.1
SINK_OMEGA = 2.0 * math.pi
SINK_DT = 0.01
SINK_T = 50.0            # 5000 steps

LOR_SIGMA = 10.0
LOR_RHO = 28.0
LOR_BETA = 8.0 / 3.0
LOR_DT = 0.005
LOR_T0_DISCARD = 5.0     # transient; measurements start on-attractor
LOR_T = 55.0             # window: t in [5, 55] -> 10000 steps

Q_DIGITS = 3             # quantized snapshots: round(state, 3)
TAU_SWEEP_SINK = [0.5, 0.1, 0.01]
TAU_SWEEP_LOR = [2.0, 0.5, 0.1]
RA_SNAPSHOT_EVERY = 100  # random-access workload: snapshot every K steps
RA_QUERIES = 200


# ================================================================== SYSTEM A

SUBST = str.maketrans({"L": "LS", "S": "L"})

def fib_step(word):
    return word.translate(SUBST)

def fib_chain(levels):
    """Full recompute from seed. Returns list of words."""
    ws = ["L"]
    for _ in range(levels):
        ws.append(fib_step(ws[-1]))
    return ws

def fib_resume(snapshot_word, steps):
    w = snapshot_word
    for _ in range(steps):
        w = fib_step(w)
    return w

def count_chain(levels):
    """Exact count chain: (L, S) -> (L+S, L)."""
    cs = [(1, 0)]
    for _ in range(levels):
        L, S = cs[-1]
        cs.append((L + S, L))
    return cs

def count_resume(snapshot_count, steps):
    L, S = snapshot_count
    for _ in range(steps):
        L, S = L + S, L
    return (L, S)

def system_a():
    out = {}
    words = fib_chain(FIB_LEVELS)
    counts = count_chain(FIB_LEVELS)

    # --- S1: resume from word snapshots is exact ----------------------
    snaps = {k: words[k] for k in range(0, FIB_LEVELS + 1, FIB_SNAP_EVERY)}
    mismatches = 0
    for n in range(FIB_LEVELS + 1):
        k = (n // FIB_SNAP_EVERY) * FIB_SNAP_EVERY
        if fib_resume(snaps[k], n - k) != words[n]:
            mismatches += 1
    out["word_resume"] = {"snapshot_levels": sorted(snaps),
                          "levels_checked": FIB_LEVELS + 1,
                          "mismatched_levels": mismatches}

    # --- S2: resume from count snapshots is exact (for counts) --------
    csnaps = {k: counts[k] for k in range(0, FIB_LEVELS + 1, FIB_SNAP_EVERY)}
    cmismatches = 0
    for n in range(FIB_LEVELS + 1):
        k = (n // FIB_SNAP_EVERY) * FIB_SNAP_EVERY
        if count_resume(csnaps[n - k] if False else csnaps[k], n - k) != counts[n]:
            cmismatches += 1
    out["count_resume"] = {"levels_checked": FIB_LEVELS + 1,
                           "mismatched_levels": cmismatches}
    # cross-check counts against actual letters
    actual_mismatch = sum(
        1 for n, w in enumerate(words)
        if (w.count("L"), w.count("S")) != counts[n])
    out["count_vs_actual_letters_mismatch"] = actual_mismatch

    # --- S3: counts do NOT determine the word (many-to-one, VOID) -----
    L, S = counts[FIB_LEVELS]
    total = L + S
    same_count_words = math.comb(total, L)
    out["word_from_counts"] = {
        "level": FIB_LEVELS, "letter_counts": [L, S],
        "distinct_words_with_same_counts_log10":
            math.log10(same_count_words),
        "small_case": {"level": 8,
                       "counts": list(counts[8]),
                       "distinct_words_exact":
                           math.comb(counts[8][0] + counts[8][1],
                                     counts[8][0])},
        "reading": "the count snapshot is a codebook of size 1 in "
                   "log10 ~ %.1f / log2 of the language; decoding a "
                   "word from counts is VOID" % math.log10(same_count_words)}

    # --- S9: random-access work, exact side ---------------------------
    # Work = letters visited. Full access to level n: sum |w_i|, i<=n.
    # Delta access: from snapshot at k, sum |w_i|, k<i<=n.
    lens = [len(w) for w in words]
    full_work = sum(sum(lens[:n + 1]) for n in range(FIB_LEVELS + 1))
    delta_work = 0
    for n in range(FIB_LEVELS + 1):
        k = (n // FIB_SNAP_EVERY) * FIB_SNAP_EVERY
        delta_work += sum(lens[k:n + 1]) if n > k else lens[n]
    # predicted ratio from the closed-form lengths F(i+2)
    F = [0, 1]
    while len(F) < FIB_LEVELS + 3:
        F.append(F[-1] + F[-2])
    plen = [F[i + 2] for i in range(FIB_LEVELS + 1)]
    p_full = sum(sum(plen[:n + 1]) for n in range(FIB_LEVELS + 1))
    p_delta = 0
    for n in range(FIB_LEVELS + 1):
        k = (n // FIB_SNAP_EVERY) * FIB_SNAP_EVERY
        p_delta += sum(plen[k:n + 1]) if n > k else plen[n]
    out["exact_random_access"] = {
        "queries": FIB_LEVELS + 1, "snapshot_every": FIB_SNAP_EVERY,
        "full_work_letters": full_work, "delta_work_letters": delta_work,
        "predicted_ratio_from_closed_form": p_full / p_delta,
        "measured_ratio": full_work / delta_work,
        "snapshot_storage_letters": sum(lens[k] for k in snaps),
        "full_storage_letters": sum(lens)}

    # --- kept cross-checks ---------------------------------------------
    # concatenation view (depth-2): w_{n+1} == w_n + w_{n-1}
    concat_mismatch = sum(
        1 for n in range(1, FIB_LEVELS)
        if words[n] + words[n - 1] != words[n + 1])
    out["concatenation_view_mismatches"] = concat_mismatch
    out["word_sha256"] = {n: hashlib.sha256(w.encode()).hexdigest()[:16]
                          for n, w in enumerate(words)}
    out["level_lengths"] = lens
    return out


# ================================================================== SYSTEM B

def rk4(f, s, dt):
    k1 = f(s)
    k2 = f([s[i] + 0.5 * dt * k1[i] for i in range(len(s))])
    k3 = f([s[i] + 0.5 * dt * k2[i] for i in range(len(s))])
    k4 = f([s[i] + dt * k3[i] for i in range(len(s))])
    return [s[i] + dt * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6.0
            for i in range(len(s))]

def euler(f, s, dt):
    k = f(s)
    return [s[i] + dt * k[i] for i in range(len(s))]

def sink_rhs(s):
    return [SINK_LAMBDA * s[0] - SINK_OMEGA * s[1],
            SINK_OMEGA * s[0] + SINK_LAMBDA * s[1]]

def lorenz_rhs(s):
    return [LOR_SIGMA * (s[1] - s[0]),
            s[0] * (LOR_RHO - s[2]) - s[1],
            s[0] * s[1] - LOR_BETA * s[2]]

def integrate(f, s0, dt, n_steps):
    traj = [list(s0)]
    s = list(s0)
    for _ in range(n_steps):
        s = rk4(f, s, dt)
        traj.append(s)
    return traj

def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

def quantize(s, digits):
    return [round(x, digits) for x in s]

def fit_slope(ts, errs, floor, ceil):
    """Least-squares slope of log(err) over the growing phase.
    Nulls are outputs: insufficient points -> None."""
    pts = [(t, math.log(e)) for t, e in zip(ts, errs)
           if floor < e < ceil]
    if len(pts) < 10:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    num = sum((p[0] - mx) * (p[1] - my) for p in pts)
    den = sum((p[0] - mx) ** 2 for p in pts)
    return num / den if den else None


def drift_case(name, f, s0, dt, n_total, perturb_at, attractor_scale):
    """Exact-snapshot bitwise resume + quantized-snapshot drift."""
    traj = integrate(f, s0, dt, n_total)
    snap_exact = traj[perturb_at]

    # bitwise resume: same integrator, same state -> identical floats
    s = list(snap_exact)
    bit_mismatch = 0
    for i in range(perturb_at + 1, n_total + 1):
        s = rk4(f, s, dt)
        if s != traj[i]:
            bit_mismatch += 1

    # quantized snapshot drift
    snap_q = quantize(snap_exact, Q_DIGITS)
    delta = dist(snap_q, snap_exact)
    s = list(snap_q)
    errs, ts = [], []
    for i in range(perturb_at + 1, n_total + 1):
        s = rk4(f, s, dt)
        errs.append(dist(s, traj[i]))
        ts.append((i - perturb_at) * dt)
    horizon_ratio = errs[-1] / delta
    slope = fit_slope(ts, errs, delta * 10.0, 0.1 * attractor_scale)
    return {
        "case": name, "dt": dt, "steps": n_total,
        "perturb_at_step": perturb_at,
        "horizon_s": (n_total - perturb_at) * dt,
        "bitwise_resume_mismatches": bit_mismatch,
        "injected_delta": delta,
        "horizon_error": errs[-1],
        "horizon_error_over_delta": horizon_ratio,
        "log_error_slope_per_s": slope,
        "snapshots_kept": {"exact_state": snap_exact,
                           "quantized_state": snap_q},
    }


def adaptive_case(name, f, s0, dt, n_warm, n_total, tau_sweep):
    """Dead-reckoning: sender RK4 truth; receiver cheap Euler between
    refreshes; resync when |receiver - sender| > tau (the escape code)."""
    traj = integrate(f, s0, dt, n_total)
    runs = []
    for tau in tau_sweep:
        s = list(traj[n_warm])          # synced at window start
        refreshes = 0
        max_dev = 0.0
        for i in range(n_warm + 1, n_total + 1):
            s = euler(f, s, dt)
            d = dist(s, traj[i])
            max_dev = max(max_dev, d)
            if d > tau:
                s = list(traj[i])       # refresh = transmit snapshot
                refreshes += 1
        steps = n_total - n_warm
        runs.append({
            "tau": tau,
            "refreshes": refreshes,
            "refresh_frac": refreshes / steps,
            "mean_steps_between_refreshes":
                steps / refreshes if refreshes else None,
            "max_deviation": max_dev,
            "channel_bytes_state3_float8": refreshes * len(s0) * 8,
            "full_channel_bytes": steps * len(s0) * 8,
        })
    return {"case": name, "dt": dt, "window_steps": n_total - n_warm,
            "runs": runs}


def random_access_case(f, s0, dt, n_warm, n_total, k_snap, n_queries, rng):
    """Query arbitrary times: restart from t0 vs resume from snapshot."""
    traj = integrate(f, s0, dt, n_total)
    queries = sorted(rng.randrange(n_warm, n_total + 1)
                     for _ in range(n_queries))
    full_steps = sum(queries)
    delta_steps = sum(q - (q // k_snap) * k_snap for q in queries)
    n_states = n_total + 1
    n_snaps = len(range(0, n_total + 1, k_snap))
    return {"queries": n_queries, "snapshot_every": k_snap,
            "full_restart_steps": full_steps,
            "delta_resume_steps": delta_steps,
            "speedup": full_steps / delta_steps,
            "predicted_speedup_n_over_k":
                (n_total / 2.0) / (k_snap / 2.0),
            "snapshot_states_stored": n_snaps,
            "storage_frac_of_full_traj": n_snaps / n_states}


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

    A = system_a()

    sink_steps = int(SINK_T / SINK_DT)
    lor_warm = int(LOR_T0_DISCARD / LOR_DT)
    lor_steps = int(LOR_T / LOR_DT)
    sink = drift_case("sink", sink_rhs, [1.0, 0.0], SINK_DT,
                      sink_steps, perturb_at=2 * sink_steps // 5,
                      attractor_scale=1.0)
    lor = drift_case("lorenz", lorenz_rhs, [1.0, 1.0, 1.0], LOR_DT,
                     lor_steps, perturb_at=lor_warm + 2 * (lor_steps - lor_warm) // 5,
                     attractor_scale=25.0)
    ad_sink = adaptive_case("sink", sink_rhs, [1.0, 0.0], SINK_DT,
                            0, sink_steps, TAU_SWEEP_SINK)
    ad_lor = adaptive_case("lorenz", lorenz_rhs, [1.0, 1.0, 1.0], LOR_DT,
                           lor_warm, lor_steps, TAU_SWEEP_LOR)
    ra = random_access_case(lorenz_rhs, [1.0, 1.0, 1.0], LOR_DT,
                            lor_warm, lor_steps,
                            RA_SNAPSHOT_EVERY, RA_QUERIES, rng)

    claims = []

    def pack(scope, rate_var, value, tol_frac, measurement, failure,
             measured, extra=None, verdict_fn=None):
        c = {"scope": scope, "rate_var": rate_var, "kind": "snapshot_delta",
             "value": value, "tol_frac": tol_frac, "measurement": measurement,
             "failure": failure, "provenance": "snapshot_delta.py",
             "measured": measured,
             "verdict": (verdict_fn(measured) if verdict_fn else
                         verdict(measured, value, tol_frac)),
             "ts": t0}
        if extra:
            c.update(extra)
        claims.append(c)

    pack("fab::snapshot::fib::word_resume_exact",
         "dN_mismatch/dlevel",
         0.0, 0.0,
         "resume every level 0..25 from the nearest snapshot (every 5 "
         "levels) via the substitution stepper; count levels whose "
         "resumed word differs from full recompute (must be zero)",
         "- stepper not Markov (hidden state) -> mismatches appear\n"
         "- snapshot stored lossily -> mismatch count > 0",
         float(A["word_resume"]["mismatched_levels"]),
         extra={"note": "the substitution view needs depth-1 state; the "
                "concatenation view w_{n+1}=w_n.w_{n-1} needs depth-2. "
                "Same system: snapshot content depends on which "
                "equation you step."})

    pack("fab::snapshot::fib::count_resume_exact",
         "dN_mismatch/dlevel",
         0.0, 0.0,
         "resume the letter-count chain (L,S)->(L+S,L) from count "
         "snapshots; count mismatches vs full chain (must be zero)",
         "- count arithmetic not exact -> mismatch > 0",
         float(A["count_resume"]["mismatched_levels"]),
         extra={"count_vs_actual_letters_mismatch":
                A["count_vs_actual_letters_mismatch"]})

    pack("fab::snapshot::fib::word_from_counts",
         "dN_decodings/dcount",
         None, 0.0,
         "VOID by construction: letter counts are a many-to-one "
         "summary. Measured: distinct words consistent with the "
         "level-25 count vector (log10), and the exact count for the "
         "level-8 small case",
         "- never refuted: counts forget order (hidden state), the "
         "  decoder is underdetermined",
         None,
         extra=A["word_from_counts"])

    pack("fab::snapshot::float::bitwise_resume",
         "dN_mismatch/dstep",
         0.0, 0.0,
         "resume RK4 from an EXACT stored snapshot state and compare "
         "floats bitwise against uninterrupted integration over the "
         "remaining horizon, both systems; count mismatched states",
         "- any reordering of float operations -> mismatch > 0\n"
         "- snapshot not full state -> mismatch > 0",
         float(sink["bitwise_resume_mismatches"]
               + lor["bitwise_resume_mismatches"]),
         extra={"sink": sink["bitwise_resume_mismatches"],
                "lorenz": lor["bitwise_resume_mismatches"],
                "note": "resume itself adds zero error; all drift "
                "below comes from what the snapshot FORGOT (quantization)"})

    pack("fab::snapshot::sink::lossy_snapshot_drift",
         "d|err|/dt",
         1.0, 2.0,
         "quantize the mid-trajectory snapshot to 3 decimals, resume "
         "with the same RK4; report horizon_error/injected_delta for "
         "the stable spiral (lambda=-0.1). Band: ratio within [0, 3]",
         "- positive local exponents -> ratio exceeds band\n"
         "- declared refuter is measured, not assumed: see the "
         "  paired Lorenz claim",
         sink["horizon_error_over_delta"],
         extra={"injected_delta": sink["injected_delta"],
                "horizon_s": sink["horizon_s"],
                "log_error_slope_per_s": sink["log_error_slope_per_s"]})

    pack("fab::snapshot::lorenz::lossy_snapshot_drift",
         "d|err|/dt",
         1.0, 99.0,
         "same procedure on the Lorenz attractor. Band: ratio <= 100. "
         "EXPECTED TO FAIL: chaotic divergence saturates at attractor "
         "size, so lossy-snapshot continuation is VOID past the "
         "horizon -- refresh is mandatory, not optional",
         "- Lyapunov growth e^(Lambda t) with Lambda ~ 0.9 /s:\n"
         "  delta = 5e-4 saturates the attractor in ~15 s\n"
         "- if this passes, the pairing with the sink claim is broken",
         lor["horizon_error_over_delta"],
         extra={"injected_delta": lor["injected_delta"],
                "horizon_s": lor["horizon_s"],
                "horizon_error": lor["horizon_error"],
                "log_error_slope_per_s": lor["log_error_slope_per_s"]})

    for name, ad, tau_star in (("sink", ad_sink, 0.1),
                               ("lorenz", ad_lor, 0.5)):
        star = next(r for r in ad["runs"] if r["tau"] == tau_star)
        pack(f"fab::snapshot::{name}::adaptive_refresh_bound",
             "dN_refresh/dstep",
             tau_star, 0.5,
             "dead-reckoning with a cheap Euler receiver; resync when "
             "|receiver - sender| > tau; report max deviation over the "
             "window (band: <= 1.5*tau, covering one-step overshoot); "
             "refresh count is the channel cost, kept per tau",
             "- receiver model error unbounded between refreshes ->\n"
             "  max deviation exceeds band (chaotic case watches this)\n"
             "- refresh logic inverted -> deviation never bounded",
             star["max_deviation"],
             extra={"runs": ad["runs"]})

    pack("fab::snapshot::lorenz::random_access_speedup",
         "dN_step/dquery",
         ra["predicted_speedup_n_over_k"], 0.25,
         "200 random time queries over the on-attractor window: total "
         "integrator steps restarting from t0 vs resuming from "
         "snapshots every 100 steps; ratio measured vs the N/K "
         "prediction; snapshot storage paid is kept alongside",
         "- queries cluster near t0 -> speedup collapses (measured\n"
         "  distribution would show it)\n"
         "- snapshot storage not accounted -> speedup is decoration",
         ra["speedup"],
         extra={"full_restart_steps": ra["full_restart_steps"],
                "delta_resume_steps": ra["delta_resume_steps"],
                "storage_frac_of_full_traj":
                    ra["storage_frac_of_full_traj"]})

    pack("fab::snapshot::fib::random_access_work_ratio",
         "dN_letter/dquery",
         A["exact_random_access"]["predicted_ratio_from_closed_form"],
         0.01,
         "random access to all 26 levels: letter-visits from seed vs "
         "from snapshots every 5 levels; predicted ratio from the "
         "closed-form lengths F(i+2), measured ratio from the actual "
         "generated words",
         "- word lengths drift from F(i+2) -> the two ratios part",
         A["exact_random_access"]["measured_ratio"],
         extra={"snapshot_storage_letters":
                A["exact_random_access"]["snapshot_storage_letters"],
                "full_storage_letters":
                A["exact_random_access"]["full_storage_letters"]})

    record = {
        "instrument": "snapshot_delta.py",
        "seed": seed,
        "params": {
            "fib_levels": FIB_LEVELS, "fib_snap_every": FIB_SNAP_EVERY,
            "sink": {"lambda": SINK_LAMBDA, "omega": SINK_OMEGA,
                     "dt": SINK_DT, "T": SINK_T},
            "lorenz": {"sigma": LOR_SIGMA, "rho": LOR_RHO,
                       "beta": LOR_BETA, "dt": LOR_DT,
                       "discard": LOR_T0_DISCARD, "T": LOR_T},
            "q_digits": Q_DIGITS,
            "tau_sweep_sink": TAU_SWEEP_SINK,
            "tau_sweep_lorenz": TAU_SWEEP_LOR,
            "ra_snapshot_every": RA_SNAPSHOT_EVERY,
            "ra_queries": RA_QUERIES},
        "system_a": A,
        "drift_sink": sink,
        "drift_lorenz": lor,
        "adaptive_sink": ad_sink,
        "adaptive_lorenz": ad_lor,
        "random_access": ra,
        "claims": claims,
        "runtime_s": time.time() - t0,
    }
    out = f"snapshot_delta_seed{seed}.json"
    with open(out, "w") as fh:
        json.dump(record, fh, indent=2)
    print(json.dumps({c["scope"].split("::")[-2] + "::" + c["scope"].split("::")[-1]:
                      {"predicted": (None if c["value"] is None
                                     else round(c["value"], 6)),
                       "measured": (None if c["measured"] is None
                                    else round(c["measured"], 6)),
                       "verdict": c["verdict"]} for c in claims}, indent=2))
    print("record ->", out)
    print("sink drift ratio:", round(sink["horizon_error_over_delta"], 6),
          " lorenz drift ratio:", round(lor["horizon_error_over_delta"], 1))
    print("slopes:", sink["log_error_slope_per_s"], lor["log_error_slope_per_s"])
    print("refresh runs (sink):",
          [(r["tau"], r["refreshes"], round(r["max_deviation"], 4))
           for r in ad_sink["runs"]])
    print("refresh runs (lorenz):",
          [(r["tau"], r["refreshes"], round(r["max_deviation"], 4))
           for r in ad_lor["runs"]])
    print("random access speedup:", round(ra["speedup"], 2),
          "storage frac:", round(ra["storage_frac_of_full_traj"], 4))


if __name__ == "__main__":
    main()
