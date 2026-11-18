"""equation_search round 3: a second guard, a rename, a threshold sweep, a noisy run. Co-authored. CC0.

PROPOSED. Stdlib only; Python 3.10. Generated data only. The received
equation_search.py is imported, never edited. Every number below was declared
in DECLARED.json ("round3") and committed before this file was run.

  python -m experiments.experiment_bridge.eqsearch.round3 --output NEW_FILE.json

a TIME-SHUFFLE GUARD  a second guard that does not use R^2. The time order of
    the states is shuffled, the derivatives (or the map target) are recomputed
    from the shuffled order, and the SAME selected structure is refitted. The
    guard passes only if the residual in the true order is below that of all
    19 shuffles. On data with no time structure the true order is one
    arrangement among twenty, so the guard passes about 1 time in 20 by
    chance: it is expected to let about 2 of 40 noise datasets through. False
    discoveries are reported with the R^2 gate alone, the shuffle guard alone,
    and both.

b LINEAR COMPARISON  the specimen fits a linear map beside the logistic one
    and calls it a guard. Round 2 measured the quadratic beating it on 398 of
    400 pure-noise series: it compares two fits and guards nothing. It is
    named linear_comparison here; the specimen keeps its own names.

c STLSQ THRESHOLD SWEEP  thresholds 0.01 to 1.0 on Lorenz, and on Lorenz with
    a planted term of true coefficient 0.05 (+ 0.05 x in dz/dt). Logged per
    threshold: components recovered, the cause of each miss, and the range of
    thresholds that recovers 3 of 3.

d NOISY LORENZ  noise 1e-3 on the round-2 trajectory through STLSQ, and
    through the exact tier: float states must read NOT_ENGAGED; an exact
    trajectory with rational noise added must read FAIL, located; the same
    trajectory with no noise must read PASS. A pass on noisy data would be a
    defect of the tier.
"""
import argparse
import json
import random
import sys
from fractions import Fraction
from pathlib import Path

from . import exact as X
from . import round2 as R

EQ = R.EQ
VERSION = "experiment-bridge/eqsearch-round3-1"
D3 = R.DECLARED["round3"]
SHUFFLES = D3["time_shuffle_guard"]["shuffles"]
SEEDS = D3["time_shuffle_guard"]["seeds"]
TRIALS = D3["time_shuffle_guard"]["null_trials_per_family"]
THRESHOLDS = [float(t) for t in D3["stlsq_sweep"]["thresholds"]]
SMALL = 0.05
TRUTH_SMALL = [{"x", "y"}, {"x", "y", "xz"}, {"xy", "z", "x"}]
NOISE = 0.001


def rng(seed, purpose):
    return random.Random(f"{seed}|r3|{purpose}")


# ---------------------------------------------------------------- fits

def stlsq(traj, dt, threshold):
    """Thresholded least squares at a given threshold (round 2's branch, parametrised)."""
    states, ders, _ = R.derivatives(traj, dt, 3)
    phis = [EQ.f3_phi(s) for s in states]
    chosen_all, beta_all = [], []
    for c in range(3):
        keep, beta = list(range(len(EQ.F3_TERMS))), []
        for _ in range(R.STLSQ_ROUNDS):
            if not keep:
                beta = []
                break
            try:
                beta, _ = EQ.lstsq([[row[j] for j in keep] for row in phis], ders[c])
            except ArithmeticError:
                keep, beta = [], []
                break
            small = [j for j, b in zip(keep, beta) if abs(b) < threshold]
            if not small:
                break
            keep = [j for j in keep if j not in small]
        else:
            if keep:
                beta, _ = EQ.lstsq([[row[j] for j in keep] for row in phis], ders[c])
        chosen_all.append([EQ.F3_TERMS[j] for j in keep])
        beta_all.append(beta)
    return chosen_all, beta_all


def rss_fixed(traj, dt, chosen):
    """Residual of a FIXED structure on a trajectory, summed over its components."""
    states, ders, _ = R.derivatives(traj, dt, 3)
    phis = [EQ.f3_phi(s) for s in states]
    total = 0.0
    for c in range(3):
        idx = [EQ.F3_TERMS.index(t) for t in chosen[c]]
        if not idx:
            continue
        try:
            _, rss = EQ.lstsq([[row[j] for j in idx] for row in phis], ders[c])
        except ArithmeticError:
            return None
        total += rss
    return total


def cause(chosen, truth):
    got = set(chosen)
    if got == truth:
        return None
    if got > truth:
        return "OVER_SELECTION"
    if got < truth:
        return "UNDER_SELECTION"
    if len(got) == len(truth):
        return "SWAP"
    return "OTHER"


# ---------------------------------------------------------------- the shuffle guard

def shuffle_guard(real, refit, items, g):
    """True only if `real` is below the refit residual of every shuffled order."""
    if real is None:
        return {"passes": False, "real": None, "shuffled_min": None, "rank": None,
                "reason": "no residual in the true order"}
    values = []
    for _ in range(SHUFFLES):
        order = list(items)
        g.shuffle(order)
        v = refit(order)
        if v is not None:
            values.append(v)
    below = sum(1 for v in values if v <= real)
    return {"passes": bool(values) and below == 0, "real": real,
            "shuffled_min": min(values) if values else None, "rank": below + 1,
            "of": len(values) + 1}


def f2_case(traj, dt, g):
    lam, ome, rss = EQ.f2_fit(traj, dt)
    tss = sum(((traj[i + 1][c] - traj[i - 1][c]) / (2 * dt)) ** 2
              for i in range(1, len(traj) - 1) for c in range(2))
    guard = shuffle_guard(rss, lambda o: EQ.f2_fit(o, dt)[2], traj, g)
    return {"selected": True, "r2": R.r_squared(rss, tss), "shuffle": guard}


def f3_case(traj, dt, chosen, g):
    r2s = [r for r, ch in zip(R.fit_quality(traj, dt, chosen), chosen) if ch]
    selected = any(chosen)
    guard = shuffle_guard(rss_fixed(traj, dt, chosen) if selected else None,
                          lambda o: rss_fixed(o, dt, chosen), traj, g)
    return {"selected": selected, "r2": max(r2s) if r2s else None, "shuffle": guard}


def linear_comparison(seq):
    """The specimen's f4_null_guard under the name it has earned: it compares
    the quadratic map with a linear one by BIC. Returns (r_hat, quadratic wins)."""
    r_hat, bic_q, bic_l, _ = EQ.f4_null_guard(seq)
    return r_hat, bic_q < bic_l


def f4_case(seq, g):
    r_hat, gate = R.f4_fit_gated(seq)
    rss = lambda s: EQ.f4_fit(s)[1]                                     # noqa: E731
    guard = shuffle_guard(rss(seq), rss, seq, g)
    return {"selected": linear_comparison(seq)[1], "r2": gate["r2"], "shuffle": guard,
            "r_hat": r_hat}


def tally(rows):
    ok_r2 = lambda r: r["selected"] and r["r2"] is not None and r["r2"] >= R.R2_MIN   # noqa: E731
    ok_sh = lambda r: r["selected"] and r["shuffle"]["passes"]                         # noqa: E731
    return {"trials": len(rows), "selected_any_term": sum(1 for r in rows if r["selected"]),
            "false_discoveries": {"r2_only": sum(1 for r in rows if ok_r2(r)),
                                  "shuffle_only": sum(1 for r in rows if ok_sh(r)),
                                  "both": sum(1 for r in rows if ok_r2(r) and ok_sh(r))}}


def nulls(seed):
    out = {}
    f2 = [f2_case([[g.gauss(0, 1), g.gauss(0, 1)] for _ in range(501)], 0.01, g)
          for g in (rng(seed, f"null-f2-{i}") for i in range(TRIALS))]
    out["f2"] = tally(f2)
    per = {"greedy_bic": [], "noise_floor": [], "stlsq": []}
    for i in range(TRIALS):
        g = rng(seed, f"null-f3-{i}")
        traj = [[g.gauss(0, 1) for _ in range(3)] for _ in range(501)]
        for name, fn in (("greedy_bic", R.branch_greedy_bic), ("noise_floor", R.branch_noise_floor),
                         ("stlsq", R.branch_stlsq)):
            per[name].append(f3_case(traj, 0.005, fn(traj, 0.005)[0], g))
    for name, rows in per.items():
        out[f"f3::{name}"] = tally(rows)
    f4 = [f4_case([g.random() for _ in range(401)], g)
          for g in (rng(seed, f"null-f4-{i}") for i in range(TRIALS))]
    out["f4"] = tally(f4)
    return out


def power(seed, lorenz):
    """The planted data must pass the shuffle guard."""
    g = rng(seed, "power")
    sink = EQ.integrate(EQ.sink_rhs_gen(-0.1, 6.283185307179586), [1.0, 0.0], 0.01, 5000)
    noisy = [[x + 0.01 * g.gauss(0, 1) for x in s] for s in sink]
    seq = [EQ.LOGISTIC_X0]
    for _ in range(EQ.LOGISTIC_N):
        seq.append(EQ.LOGISTIC_R * seq[-1] * (1.0 - seq[-1]))
    chosen = stlsq(lorenz, 0.005, R.STLSQ_THRESHOLD)[0]
    cases = {"f2_planted_noise_0.01": f2_case(noisy, 0.01, g),
             "f3_planted_stlsq": f3_case(lorenz, 0.005, chosen, g),
             "f4_planted": f4_case(seq, g)}
    return {k: {"passes_shuffle_guard": v["shuffle"]["passes"], "r2": v["r2"],
                "rank": v["shuffle"]["rank"], "of": v["shuffle"]["of"]} for k, v in cases.items()}


# ---------------------------------------------------------------- b, c, d

def linear_comparison_count():
    """Round 2's 400 pure-noise series, read with the renamed comparison."""
    wins = 0
    for seed in R.SEEDS:
        for i in range(R.NULL_TRIALS):
            g = R.rng(seed, f"null-f4-{i}")              # round 2's own stream, one per series
            wins += linear_comparison([g.random() for _ in range(401)])[1]
    return {"series": len(R.SEEDS) * R.NULL_TRIALS, "quadratic_beats_linear": wins,
            "name": "linear_comparison", "was": "linear_guard",
            "reading": "on pure noise the quadratic wins almost always, so winning it is "
                       "not evidence of structure"}


def small_term_rhs(s):
    return [10.0 * (s[1] - s[0]), s[0] * (28.0 - s[2]) - s[1],
            s[0] * s[1] - (8.0 / 3.0) * s[2] + SMALL * s[0]]


def sweep(traj, truth):
    rows = []
    for t in THRESHOLDS:
        chosen, betas = stlsq(traj, 0.005, t)
        causes = [cause(chosen[c], truth[c]) for c in range(3)]
        rows.append({"threshold": t, "chosen": chosen,
                     "components_recovered": sum(1 for x in causes if x is None),
                     "failure_causes": {"xyz"[c]: causes[c] for c in range(3) if causes[c]},
                     "smallest_kept_coefficient": min((abs(b) for bb in betas for b in bb),
                                                      default=None)})
    good = [r["threshold"] for r in rows if r["components_recovered"] == 3]
    return {"rows": rows, "recovers_3_of_3_at": good,
            "lowest": min(good) if good else None, "highest": max(good) if good else None,
            "breaks_at": [{"threshold": r["threshold"], "causes": r["failure_causes"]}
                          for r in rows if r["components_recovered"] < 3]}


def exact_fit_states(states):
    """The exact tier on GIVEN states: solve the step map on the first ten
    transitions, verify every transition by exact equality."""
    if any(isinstance(v, float) for s in states for v in s):
        return {"branch": "NOT_ENGAGED", "verdict": None,
                "reason": "the states are floats: not rationals as given; not converted"}
    states = [[Fraction(v) for v in s] for s in states]
    rows = [X.phi(s) for s in states[:10]]
    rhs = [[states[i + 1][c] for i in range(10)] for c in range(3)]
    rank, coeffs = X.solve_exact(rows, rhs)
    if coeffs is None:
        return {"branch": "EXACT", "verdict": "VOID", "reason": f"rank {rank} of 10"}
    checked, miss = X.verify_exact(states, coeffs)
    parsed = X.engage(X.LORENZ)[2]
    planted = X.planted_map(parsed["coefficients"], parsed["dt"])
    return {"branch": "EXACT", "verdict": "PASS" if miss is None else "FAIL",
            "transitions": len(states) - 1, "steps_checked_before_mismatch": checked,
            "located_error": None if miss is None else
            {"step": miss["step"], "component": miss["component"], "rule": miss["rule"]},
            "equals_planted_map": coeffs == planted,
            "note": "the first ten transitions are fitted exactly by construction; the "
                    "verdict comes from the ones after them"}


def noisy_lorenz(lorenz):
    g = rng(0, "noisy-lorenz")
    noisy = [[x + NOISE * g.gauss(0, 1) for x in s] for s in lorenz]
    chosen, betas = stlsq(noisy, 0.005, R.STLSQ_THRESHOLD)
    causes = [cause(chosen[c], R.TRUTH[c]) for c in range(3)]
    clean = X.exact_states(X.engage(X.LORENZ)[2], 13)[0]
    ge = rng(0, "noisy-exact")
    bent = [[v + Fraction(round(NOISE * ge.gauss(0, 1), 9)).limit_denominator(10 ** 9)
             for v in s] for s in clean]
    return {"noise": NOISE,
            "stlsq": {"threshold": R.STLSQ_THRESHOLD, "chosen": chosen, "betas": betas,
                      "components_recovered": sum(1 for x in causes if x is None),
                      "failure_causes": {"xyz"[c]: causes[c] for c in range(3) if causes[c]},
                      "r2_per_component": R.fit_quality(noisy, 0.005, chosen)},
            "exact_tier": {"float_states": exact_fit_states(noisy[:14]),
                           "rationalised_noisy_states": exact_fit_states(bent),
                           "control_no_noise": exact_fit_states(clean)}}


def build():
    lorenz = R.lorenz_traj()
    small = EQ.integrate(small_term_rhs, [1.0, 1.0, 1.0], 0.005, 11000)[1000:]
    by_seed = {}
    for seed in SEEDS:
        print(f"nulls, seed {seed} ...", flush=True)
        by_seed[str(seed)] = nulls(seed)
    families = list(by_seed[str(SEEDS[0])])
    total = {f: {k: sum(by_seed[str(s)][f]["false_discoveries"][k] for s in SEEDS)
                 for k in ("r2_only", "shuffle_only", "both")} for f in families}
    for f in families:
        total[f]["datasets"] = TRIALS * len(SEEDS)
        total[f]["selected_any_term"] = sum(by_seed[str(s)][f]["selected_any_term"]
                                            for s in SEEDS)
    noisy = noisy_lorenz(lorenz)
    ex = noisy["exact_tier"]
    rec = {"version": VERSION, "status": "PROPOSED",
           "scope": "generated data only; the received specimen is imported, not edited",
           "declared_in": "eqsearch/DECLARED.json round3, committed before any run",
           "a_time_shuffle_guard": {"shuffles": SHUFFLES, "seeds": SEEDS,
                                    "nulls_by_seed": by_seed, "false_discoveries_total": total,
                                    "power": power(0, lorenz)},
           "b_linear_comparison": linear_comparison_count(),
           "c_stlsq_sweep": {"lorenz": sweep(lorenz, R.TRUTH),
                             "lorenz_small_term": dict(sweep(small, TRUTH_SMALL),
                                                       planted_small_coefficient=SMALL)},
           "d_noisy_lorenz": noisy,
           "human_interest": None, "ai_interest": None}
    rec["checks"] = {
        "planted_data_passes_the_shuffle_guard": all(
            v["passes_shuffle_guard"] for v in rec["a_time_shuffle_guard"]["power"].values()),
        "no_false_discovery_with_both_guards": all(t["both"] == 0 for t in total.values()),
        "exact_tier_never_passes_noisy_data":
            ex["float_states"]["branch"] == "NOT_ENGAGED"
            and ex["rationalised_noisy_states"]["verdict"] == "FAIL",
        "exact_tier_control_passes": ex["control_no_noise"]["verdict"] == "PASS"}
    return rec


def main(argv=None):
    parser = argparse.ArgumentParser(description="equation_search round 3")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    rec = build()
    args.output.write_text(json.dumps(rec, indent=1, ensure_ascii=True) + "\n", encoding="ascii")
    for f, t in rec["a_time_shuffle_guard"]["false_discoveries_total"].items():
        print(f"null {f:16s} of {t['datasets']}: selected {t['selected_any_term']:>3}  "
              f"r2 only {t['r2_only']}  shuffle only {t['shuffle_only']}  both {t['both']}")
    print("power:", {k: v["passes_shuffle_guard"]
                     for k, v in rec["a_time_shuffle_guard"]["power"].items()})
    b = rec["b_linear_comparison"]
    print(f"linear_comparison: quadratic wins {b['quadratic_beats_linear']} of {b['series']}")
    for name, s in rec["c_stlsq_sweep"].items():
        print(f"sweep {name}: 3/3 at {s['recovers_3_of_3_at']}; breaks {s['breaks_at']}")
    d = rec["d_noisy_lorenz"]
    print("noisy stlsq:", d["stlsq"]["components_recovered"], d["stlsq"]["failure_causes"])
    print("noisy exact:", {k: (v["branch"], v["verdict"]) for k, v in d["exact_tier"].items()})
    print("checks:", rec["checks"])
    print("written ->", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
