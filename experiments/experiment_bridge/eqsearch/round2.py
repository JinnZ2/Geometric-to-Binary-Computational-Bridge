"""equation_search round 2: more branches, nulls, tolerance sources, seeds. Co-authored. CC0.

The received equation_search.py (evidence/equation_search_as_received/) is
imported and never edited; its greedy-BIC F3 search stays as it is and is run
here as one branch among three. Every threshold and band below was written
into DECLARED.json and committed before the specimen or this file was run.
PROPOSED. Stdlib only; Python 3.10. All data are generated; nothing here is a
measurement of a physical system.

  python -m experiments.experiment_bridge.eqsearch.round2 --output NEW_FILE.json

1 F3 BRANCHES on the specimen's Lorenz trajectory
    greedy_bic       the specimen's f3_search, called unchanged
    noise_floor      a: derivative error by Richardson (central differences at
                     dt and 2 dt; error of the dt estimate = (d_2dt - d_dt)/3);
                     its mean square per component is sigma^2; greedy forward
                     selection by rss / sigma^2 + k ln n instead of raw BIC
    stlsq            b: thresholded least squares, threshold 0.1 on the
                     coefficient, at most 10 rounds
    c: planted Lorenz must come back 3 of 3 on at least one branch; a branch
    that misses is logged per component with cause OVER_SELECTION (the
    planted set plus extras), SWAP (same size, other terms) or OTHER.

2 NULLS  40 pure-noise datasets per family (F2, F3 per branch, F4), per seed.
    A branch DISCOVERS only if it selects something AND one-step R^2 >= 0.5.
    Both counts are kept: selected_any_term (no gate) and false discoveries
    (with the gate). measured = false discoveries; the bar is 0.

3 F4 NOISE SWEEP  observation noise 0, 1e-3, 1e-2 on the logistic series. The
    2% band applies to the noisy rows only. The noiseless row is a
    SOLVER_CHECK (band 1e-6): it checks the arithmetic, not recovery.

4 F1 IDENTIFIABILITY  the constant sequence has more than one exact
    recurrence: NON_UNIQUE, verdict void with the hit list. Never pass.

5 TOL_SOURCE per claim: DEFINITION | PHYSICS_BOUND | DECLARED_PRE_RUN |
    UNSOURCED. A pass on an UNSOURCED tolerance is written
    "pass (tol unsourced)", never a plain pass.

6 SEEDS 0-9 for everything stochastic; per claim the verdicts over the ten
    seeds and whether they are all the same.
"""
import argparse
import importlib.util
import json
import math
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECIMEN = HERE.parent / "evidence" / "equation_search_as_received" / "equation_search.py"
DECLARED = json.loads((HERE / "DECLARED.json").read_text(encoding="utf-8"))
VERSION = "experiment-bridge/eqsearch-round2-1"

_spec = importlib.util.spec_from_file_location("equation_search_as_received", SPECIMEN)
EQ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EQ)                      # defines functions; main() is not run

R2 = DECLARED["round2"]
STLSQ_THRESHOLD = float(R2["f3_stlsq"]["threshold"])
STLSQ_ROUNDS = R2["f3_stlsq"]["max_iterations"]
R2_MIN = float(R2["adequacy_gate"]["r2_min"])
NULL_TRIALS = R2["nulls"]["trials_per_family"]
SEEDS = R2["seeds"]
F4_NOISE = [float(x) for x in R2["f4_noise_sweep"]["noise_levels"]]
F4_BAND, SOLVER_BAND = 0.02, 1e-6
F2_BAND = 0.05
TRUTH = [{"x", "y"}, {"x", "y", "xz"}, {"xy", "z"}]
TOL_SOURCES = tuple(R2["tol_source_values"])


def rng(seed, purpose):
    return random.Random(f"{seed}|{purpose}")


# ---------------------------------------------------------------- F3 data

def lorenz_rhs(s):                                 # as in the specimen's main()
    return [10.0 * (s[1] - s[0]), s[0] * (28.0 - s[2]) - s[1],
            s[0] * s[1] - (8.0 / 3.0) * s[2]]


def lorenz_traj():
    return EQ.integrate(lorenz_rhs, [1.0, 1.0, 1.0], 0.005, 11000)[1000:]


def derivatives(traj, dt, dim):
    """Rows i = 2 .. n-3: library row, central derivative, Richardson error."""
    phis, ders, errs = [], [[] for _ in range(dim)], [[] for _ in range(dim)]
    for i in range(2, len(traj) - 2):
        phis.append(traj[i])
        for c in range(dim):
            d1 = (traj[i + 1][c] - traj[i - 1][c]) / (2 * dt)
            d2 = (traj[i + 2][c] - traj[i - 2][c]) / (4 * dt)
            ders[c].append(d1)
            errs[c].append((d2 - d1) / 3.0)
    return phis, ders, errs


def r_squared(rss, tss):
    return None if tss <= 0 else 1.0 - rss / tss


# ---------------------------------------------------------------- F3 branches

def branch_greedy_bic(traj, dt):
    chosen, betas, _ = EQ.f3_search(traj, dt)
    return chosen, betas


def branch_noise_floor(traj, dt):
    states, ders, errs = derivatives(traj, dt, 3)
    phis = [EQ.f3_phi(s) for s in states]
    n = len(phis)
    chosen_all, beta_all, sigma2 = [], [], []
    for c in range(3):
        s2 = sum(e * e for e in errs[c]) / n
        sigma2.append(s2)
        if s2 <= 0:                               # no error estimate: nothing to score with
            chosen_all.append([])
            beta_all.append([])
            continue
        chosen, betas = [], []
        best = sum(v * v for v in ders[c]) / s2
        for _ in range(EQ.MAX_TERMS_F3):
            trial_best = None
            for t in range(len(EQ.F3_TERMS)):
                if t in chosen:
                    continue
                trial = chosen + [t]
                try:
                    beta, rss = EQ.lstsq([[row[j] for j in trial] for row in phis], ders[c])
                except ArithmeticError:
                    continue
                score = rss / s2 + len(trial) * math.log(n)
                if trial_best is None or score < trial_best[0]:
                    trial_best = (score, trial, beta)
            if trial_best is None or trial_best[0] >= best:
                break
            best, chosen, betas = trial_best
        chosen_all.append([EQ.F3_TERMS[j] for j in chosen])
        beta_all.append(betas)
    return chosen_all, beta_all, sigma2


def branch_stlsq(traj, dt):
    states, ders, _ = derivatives(traj, dt, 3)
    phis = [EQ.f3_phi(s) for s in states]
    chosen_all, beta_all = [], []
    for c in range(3):
        keep, beta = list(range(len(EQ.F3_TERMS))), []
        for _ in range(STLSQ_ROUNDS):
            if not keep:
                beta = []
                break
            try:
                beta, _ = EQ.lstsq([[row[j] for j in keep] for row in phis], ders[c])
            except ArithmeticError:
                keep, beta = [], []
                break
            small = [j for j, b in zip(keep, beta) if abs(b) < STLSQ_THRESHOLD]
            if not small:
                break
            keep = [j for j in keep if j not in small]
        else:                                     # rounds used up: refit what is left
            if keep:
                beta, _ = EQ.lstsq([[row[j] for j in keep] for row in phis], ders[c])
        chosen_all.append([EQ.F3_TERMS[j] for j in keep])
        beta_all.append(beta)
    return chosen_all, beta_all


def fit_quality(traj, dt, chosen):
    """One-step R^2 per component for a chosen structure (tss about zero)."""
    states, ders, _ = derivatives(traj, dt, 3)
    phis = [EQ.f3_phi(s) for s in states]
    out = []
    for c in range(3):
        tss = sum(v * v for v in ders[c])
        idx = [EQ.F3_TERMS.index(t) for t in chosen[c]]
        if not idx:
            out.append(r_squared(tss, tss))
            continue
        _, rss = EQ.lstsq([[row[j] for j in idx] for row in phis], ders[c])
        out.append(r_squared(rss, tss))
    return out


def cause(chosen, truth):
    got = set(chosen)
    if got == truth:
        return None
    if got > truth:
        return "OVER_SELECTION"
    if len(got) == len(truth):
        return "SWAP"
    return "OTHER"


def f3_branches(traj, dt):
    out = {}
    g_chosen, g_beta = branch_greedy_bic(traj, dt)
    n_chosen, n_beta, sigma2 = branch_noise_floor(traj, dt)
    s_chosen, s_beta = branch_stlsq(traj, dt)
    for name, chosen, beta in (("greedy_bic", g_chosen, g_beta),
                               ("noise_floor", n_chosen, n_beta),
                               ("stlsq", s_chosen, s_beta)):
        causes = [cause(chosen[c], TRUTH[c]) for c in range(3)]
        out[name] = {"chosen": chosen, "betas": beta,
                     "components_recovered": sum(1 for x in causes if x is None),
                     "failure_causes": {"xyz"[c]: causes[c] for c in range(3) if causes[c]},
                     "r2_per_component": fit_quality(traj, dt, chosen)}
    out["noise_floor"]["sigma2_per_component"] = sigma2
    return out


# ---------------------------------------------------------------- nulls

def discovered(selected, r2s):
    """The adequacy gate: something selected AND R^2 >= R2_MIN somewhere."""
    return bool(selected) and any(r is not None and r >= R2_MIN for r in r2s)


def null_f2(g):
    dt = 0.01
    traj = [[g.gauss(0, 1), g.gauss(0, 1)] for _ in range(501)]
    lam, ome, rss = EQ.f2_fit(traj, dt)
    tss = sum(((traj[i + 1][c] - traj[i - 1][c]) / (2 * dt)) ** 2
              for i in range(1, len(traj) - 1) for c in range(2))
    r2 = r_squared(rss, tss)
    return {"selected": True, "r2": r2, "discovered": discovered(True, [r2])}


def null_f3(g):
    dt = 0.005
    traj = [[g.gauss(0, 1) for _ in range(3)] for _ in range(501)]
    out = {}
    for name, fn in (("greedy_bic", branch_greedy_bic), ("noise_floor", branch_noise_floor),
                     ("stlsq", branch_stlsq)):
        chosen = fn(traj, dt)[0]
        r2s = fit_quality(traj, dt, chosen)
        selected = any(chosen)
        out[name] = {"selected": selected, "r2_max": max(r for r in r2s if r is not None),
                     "discovered": discovered(selected,
                                              [r for r, ch in zip(r2s, chosen) if ch])}
    return out


def f4_fit_gated(seq):
    r_hat, bic_q, bic_l, _ = EQ.f4_null_guard(seq)
    y = seq[1:]
    mean = sum(y) / len(y)
    tss = sum((v - mean) ** 2 for v in y)
    rss = sum((r_hat * x * (1.0 - x) - v) ** 2 for x, v in zip(seq[:-1], y))
    r2 = r_squared(rss, tss)
    beats = bic_q < bic_l
    return r_hat, {"selected": beats, "r2": r2, "discovered": discovered(beats, [r2])}


def null_f4(g):
    return f4_fit_gated([g.random() for _ in range(401)])[1]


def run_nulls(seed):
    f2 = [null_f2(rng(seed, f"null-f2-{i}")) for i in range(NULL_TRIALS)]
    f3 = [null_f3(rng(seed, f"null-f3-{i}")) for i in range(NULL_TRIALS)]
    f4 = [null_f4(rng(seed, f"null-f4-{i}")) for i in range(NULL_TRIALS)]
    count = lambda rows, key: sum(1 for r in rows if r[key])        # noqa: E731
    out = {"f2": {"trials": NULL_TRIALS, "selected_any_term": count(f2, "selected"),
                  "false_discoveries": count(f2, "discovered"),
                  "r2_max": max(r["r2"] for r in f2),
                  "note": "f2_fit always returns parameters; it has no abstention of its own"},
           "f4": {"trials": NULL_TRIALS, "selected_any_term": count(f4, "selected"),
                  "false_discoveries": count(f4, "discovered"),
                  "r2_max": max(r["r2"] for r in f4)}}
    for b in ("greedy_bic", "noise_floor", "stlsq"):
        rows = [r[b] for r in f3]
        out[f"f3::{b}"] = {"trials": NULL_TRIALS, "selected_any_term": count(rows, "selected"),
                           "false_discoveries": count(rows, "discovered"),
                           "r2_max": max(r["r2_max"] for r in rows)}
    return out


# ---------------------------------------------------------------- F2, F4 recovery

def f2_rows(seed):
    lam_true, ome_true, dt = -0.1, 2.0 * math.pi, 0.01
    traj = EQ.integrate(EQ.sink_rhs_gen(lam_true, ome_true), [1.0, 0.0], dt, 5000)
    g, rows = rng(seed, "f2-noise"), []
    for nl in EQ.NOISE_LEVELS:
        noisy = [[x + nl * g.gauss(0, 1) for x in s] for s in traj] if nl else traj
        lam, ome, rss = EQ.f2_fit(noisy, dt)
        tss = sum(((noisy[i + 1][c] - noisy[i - 1][c]) / (2 * dt)) ** 2
                  for i in range(1, len(noisy) - 1) for c in range(2))
        rows.append({"noise": nl, "lam": lam, "ome": ome, "lam_err": abs(lam - lam_true),
                     "ome_rel_err": abs(ome - ome_true) / ome_true,
                     "r2": r_squared(rss, tss)})
    return rows


def f4_rows(seed):
    seq = [EQ.LOGISTIC_X0]
    for _ in range(EQ.LOGISTIC_N):
        seq.append(EQ.LOGISTIC_R * seq[-1] * (1.0 - seq[-1]))
    g, rows = rng(seed, "f4-noise"), []
    for nl in F4_NOISE:
        noisy = [x + nl * g.gauss(0, 1) for x in seq] if nl else seq
        r_hat, gate = f4_fit_gated(noisy)
        rel = abs(r_hat - EQ.LOGISTIC_R) / EQ.LOGISTIC_R
        band = F4_BAND if nl else SOLVER_BAND
        rows.append({"noise": nl, "label": "RECOVERY" if nl else "SOLVER_CHECK",
                     "r_hat": r_hat, "rel_err": rel, "band": band,
                     "within_band": rel <= band, "quadratic_beats_linear": gate["selected"],
                     "r2": gate["r2"]})
    return rows


# ---------------------------------------------------------------- claims

def claim(scope, measured, value, verdict, tol_source, tol_note, **extra):
    if tol_source not in TOL_SOURCES:
        raise ValueError(f"tol_source {tol_source!r} is not declared")
    shown = verdict
    if verdict == "pass" and tol_source == "UNSOURCED":
        shown = R2["unsourced_pass_wording"]
    return dict({"scope": scope, "measured": measured, "value": value, "verdict": verdict,
                 "verdict_with_source": shown, "tol_source": tol_source,
                 "tol_note": tol_note}, **extra)


def deterministic_claims(f3):
    best = max(v["components_recovered"] for v in f3.values())
    winners = [k for k, v in f3.items() if v["components_recovered"] == 3]
    hits = EQ.f1_search(EQ.f1_family()["constant"]["seq"])
    out = [claim("fab::eqsearch::r2::f3::structure_recovery_any_branch", best, 3,
                 "pass" if winners else "fail", "DEFINITION",
                 "recovery means all three planted term sets",
                 branches_at_3_of_3=winners,
                 per_branch={k: {"components_recovered": v["components_recovered"],
                                 "failure_causes": v["failure_causes"]} for k, v in f3.items()})]
    for name, v in f3.items():
        out.append(claim(f"fab::eqsearch::r2::f3::{name}::structure_recovery",
                         v["components_recovered"], 3,
                         "pass" if v["components_recovered"] == 3 else "fail", "DEFINITION",
                         "recovery means all three planted term sets",
                         chosen=v["chosen"], failure_causes=v["failure_causes"]))
    out.append(claim("fab::eqsearch::r2::f1::identifiability_constant", None, None, "void",
                     "DEFINITION", "more than one exact hit is NON_UNIQUE by definition",
                     state="NON_UNIQUE" if len(hits) > 1 else "UNIQUE",
                     hit_count=len(hits), hits=[list(h) for h in hits]) if len(hits) > 1 else
               claim("fab::eqsearch::r2::f1::identifiability_constant", len(hits), 1,
                     "fail", "DEFINITION", "expected NON_UNIQUE", state="UNIQUE",
                     hit_count=len(hits), hits=[list(h) for h in hits]))
    return out


def seed_claims(seed):
    declared = "DECLARED_PRE_RUN"
    nulls = run_nulls(seed)
    out = []
    for name, n in nulls.items():
        out.append(claim(f"fab::eqsearch::r2::{name}::null_abstention",
                         n["false_discoveries"], 0,
                         "pass" if n["false_discoveries"] == 0 else "fail", declared,
                         "bar 0 of 40 and the R^2 >= 0.5 gate, in DECLARED.json",
                         selected_any_term=n["selected_any_term"], trials=n["trials"],
                         r2_max=n["r2_max"]))
    f2 = f2_rows(seed)
    worst = max(max(r["lam_err"], r["ome_rel_err"]) for r in f2)
    out.append(claim("fab::eqsearch::r2::f2::parameter_recovery", worst, 0.0,
                     "pass" if worst <= F2_BAND else "fail", "UNSOURCED",
                     "the specimen's 0.05; no reason is given for it", rows=f2))
    f4 = f4_rows(seed)
    for r in f4:
        if r["label"] == "SOLVER_CHECK":
            out.append(claim("fab::eqsearch::r2::f4::solver_check_noiseless", r["rel_err"], 0.0,
                             "pass" if r["within_band"] else "fail", declared,
                             "1e-6 relative, in DECLARED.json; checks the arithmetic, "
                             "not recovery", row=r))
        else:
            out.append(claim(f"fab::eqsearch::r2::f4::map_recovery_noise_{r['noise']}",
                             r["r_hat"], EQ.LOGISTIC_R,
                             "pass" if r["within_band"] and r["quadratic_beats_linear"]
                             else "fail", "UNSOURCED",
                             "the specimen's 2% band; no reason is given for it", row=r))
    return out, nulls


def replay_specimen():
    """Two runs of the unchanged specimen on a copy; its own claims, compared."""
    records = []
    with tempfile.TemporaryDirectory(prefix="experiment-bridge-eqsearch-") as td:
        shutil.copy2(SPECIMEN, Path(td) / SPECIMEN.name)
        for _ in range(2):
            proc = subprocess.run([sys.executable, SPECIMEN.name, "0"], cwd=td, text=True,
                                  capture_output=True, timeout=300)
            if proc.returncode:
                raise RuntimeError(f"the specimen exited {proc.returncode}")
            records.append(json.loads((Path(td) / "equation_search_seed0.json").read_text()))
    strip = lambda rec: [{k: v for k, v in c.items() if k != "ts"}      # noqa: E731
                         for c in rec["claims"]]
    source = {"f1::exact_recovery": ("DEFINITION", "exact equality is the family's rule"),
              "f1::null_abstention": ("UNSOURCED", "the bar 0 of 40 is stated, not argued"),
              "f2::parameter_recovery": ("UNSOURCED", "0.05; no reason is given"),
              "f3::structure_recovery": ("DEFINITION", "all three planted term sets"),
              "f4::map_recovery": ("UNSOURCED", "2%; no reason is given"),
              "cross::outside_grammar_abstention":
                  ("DEFINITION", "any hit is an invented structure")}
    claims = []
    for c in records[0]["claims"]:
        key = "::".join(c["scope"].split("::")[-2:])
        src, note = source[key]
        shown = R2["unsourced_pass_wording"] if c["verdict"] == "pass" \
            and src == "UNSOURCED" else c["verdict"]
        claims.append({"scope": c["scope"], "measured": c["measured"], "value": c["value"],
                       "tol_frac": c["tol_frac"], "verdict": c["verdict"],
                       "verdict_with_source": shown, "tol_source": src, "tol_note": note})
    return {"runs": 2, "claims_equal_between_runs": strip(records[0]) == strip(records[1]),
            "claims": claims, "f3_chosen": records[0]["f3"]["chosen"],
            "f1_constant_hits": records[0]["f1"]["constant"]["hits"]}


def build():
    traj = lorenz_traj()
    f3 = f3_branches(traj, 0.005)
    fixed = deterministic_claims(f3)
    per_seed, nulls_by_seed = {}, {}
    for seed in SEEDS:
        print(f"seed {seed} ...", flush=True)
        claims, nulls = seed_claims(seed)
        per_seed[str(seed)] = claims
        nulls_by_seed[str(seed)] = nulls
    scopes = [c["scope"] for c in per_seed[str(SEEDS[0])]]
    stability = []
    for scope in scopes:
        verdicts = [next(c for c in per_seed[str(s)] if c["scope"] == scope)["verdict"]
                    for s in SEEDS]
        measured = [next(c for c in per_seed[str(s)] if c["scope"] == scope)["measured"]
                    for s in SEEDS]
        stability.append({"scope": scope, "verdicts": verdicts,
                          "stable": len(set(verdicts)) == 1,
                          "pass_count": verdicts.count("pass"),
                          "measured_min": min(measured), "measured_max": max(measured)})
    return {"version": VERSION, "status": "PROPOSED",
            "scope": "generated data only; the received specimen is imported, not edited",
            "declared_in": "eqsearch/DECLARED.json, committed before any run",
            "specimen_replay": replay_specimen(),
            "f3_branches": f3, "deterministic_claims": fixed,
            "seeds": SEEDS, "claims_by_seed": per_seed, "nulls_by_seed": nulls_by_seed,
            "verdict_stability": stability,
            "tol_source_counts": {
                s: sum(1 for c in fixed + per_seed[str(SEEDS[0])] if c["tol_source"] == s)
                for s in TOL_SOURCES},
            "human_interest": None, "ai_interest": None}


def main(argv=None):
    parser = argparse.ArgumentParser(description="equation_search round 2")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    rec = build()
    args.output.write_text(json.dumps(rec, indent=1, ensure_ascii=True) + "\n", encoding="ascii")
    for name, v in rec["f3_branches"].items():
        print(f"f3 {name:12s} {v['components_recovered']}/3  {v['chosen']}  {v['failure_causes']}")
    for c in rec["deterministic_claims"]:
        print(f"   {c['verdict_with_source']:20s} {c['scope'].split('r2::')[-1]}")
    for s in rec["verdict_stability"]:
        print(f"   {'stable  ' if s['stable'] else 'UNSTABLE'} {s['pass_count']:>2}/10 pass  "
              f"{s['scope'].split('r2::')[-1]}  [{s['measured_min']:.4g}, {s['measured_max']:.4g}]")
    print("written ->", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
