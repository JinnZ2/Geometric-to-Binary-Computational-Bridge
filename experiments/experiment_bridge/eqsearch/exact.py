"""Exact tier for equation_search: the step map in rationals. Co-authored. CC0.

An opt-in add-on beside the received equation_search.py, which is not
changed and whose float path is not touched. PROPOSED. Stdlib only
(fractions); Python 3.10.

  python -m experiments.experiment_bridge.eqsearch.exact --output NEW_FILE.json
  python -m experiments.experiment_bridge.eqsearch.exact --selftest

1 TRIGGER  engaged with --exact, or automatically when every coefficient,
    the step and the start parse as rationals from text or integers. A float
    anywhere -> NOT_ENGAGED, with the reason logged; a float is never turned
    into a rational on the caller's behalf.

2 DATA  the step map is generated in Fraction. Default system: Lorenz with
    sigma 10, rho 28, beta 8/3, explicit Euler, dt 1/200, start (1, 1, 1).
    No derivative is estimated: the target is the next state itself.

3 FIT  per component, next_c = sum of coef_j * term_j(state) over the
    specimen's ten library terms. The coefficients are the solution of a
    linear system over Fraction. UNIQUE means the system has full rank.
    VERIFY: every step is checked by exact equality (as F1 does for
    recurrences). The first mismatch is located by step and component and
    the verdict is FAIL. No BIC, no tolerance.

4 GROWTH  the bit length of the largest denominator is logged per step. It
    grows geometrically (measured here: about 1.6 times per step, not the
    doubling expected when the cap was declared). Past DENOM_CAP_BITS no
    further exact state is generated:
      enough exact steps for full rank      -> EXACT
      not enough, modular branch allowed    -> MODULAR: the trajectory and
          the solve are redone modulo several primes, the coefficients are
          put back together by CRT and rational reconstruction, then checked
          exactly on every step under the cap and modulo each prime on every
          step. A check modulo a prime is necessary, not sufficient; the
          record says which steps were checked which way.
      not enough, no modular branch         -> VOID. Never a float fallback.

5 CLAIMS  the planted step map comes back exactly, 3 of 3 components,
    unique; and the null: one coefficient changed by 1/1000 must make the
    exact check fail, located.

LIMITS  This recovers the STEP MAP of a known discretisation from exact,
    noise-free states. It says nothing about noisy or measured data, and
    reading ODE coefficients back from the map assumes the scheme is explicit
    Euler. Uniqueness is uniqueness within the ten-term library.
"""
import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

VERSION = "experiment-bridge/eqsearch-exact-1"
TERMS = ("1", "x", "y", "z", "xy", "xz", "yz", "x2", "y2", "z2")
DENOM_CAP_BITS = 65536
STEPS_EXACT_RUN, STEPS_LONG_RUN = 12, 40
N_PRIMES = 4
PERTURBATION = Fraction(1, 1000)
LORENZ = {"name": "lorenz", "scheme": "explicit Euler",
          "coefficients": {"sigma": "10", "rho": "28", "beta": "8/3"},
          "dt": "1/200", "start": ["1", "1", "1"]}
PLANTED_SETS = [{"x", "y"}, {"x", "y", "xz"}, {"xy", "z"}]


class NotRational(ValueError):
    pass


def rational(value, what):
    """Text or an integer -> Fraction. A float is refused, not converted."""
    if isinstance(value, bool) or isinstance(value, float):
        raise NotRational(f"{what} is a float ({value!r}): not a rational as given")
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    if isinstance(value, str):
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError):
            raise NotRational(f"{what}: cannot read {value!r} as a rational")
    raise NotRational(f"{what}: not text or an integer")


def engage(system, forced=False):
    """The trigger. Returns (engaged, log entry, parsed system or None)."""
    try:
        coeffs = {k: rational(v, f"coefficient {k}")
                  for k, v in system["coefficients"].items()}
        dt = rational(system["dt"], "the step")
        start = [rational(v, f"start[{i}]") for i, v in enumerate(system["start"])]
        if dt <= 0:
            raise NotRational("the step is not above 0")
    except NotRational as exc:
        return False, {"engaged": False, "forced": forced, "state": "NOT_ENGAGED",
                       "reason": str(exc),
                       "note": "a float is not converted; the float path is unchanged"}, None
    return True, {"engaged": True, "forced": forced, "state": "ENGAGED",
                  "reason": "--exact" if forced else
                  "auto: every coefficient, the step and the start are rational"}, \
        {"coefficients": coeffs, "dt": dt, "start": start}


def phi(s):
    x, y, z = s
    return [type(x)(1) if not isinstance(x, int) else 1, x, y, z,
            x * y, x * z, y * z, x * x, y * y, z * z]


def lorenz_step(s, c, dt):
    x, y, z = s
    return [x + dt * c["sigma"] * (y - x),
            y + dt * (x * (c["rho"] - z) - y),
            z + dt * (x * y - c["beta"] * z)]


def planted_map(c, dt):
    """The step map the generator applies, written over the library."""
    zero = Fraction(0)
    rows = [dict.fromkeys(TERMS, zero) for _ in range(3)]
    rows[0].update(x=1 - dt * c["sigma"], y=dt * c["sigma"])
    rows[1].update(x=dt * c["rho"], y=1 - dt, xz=-dt)
    rows[2].update(z=1 - dt * c["beta"], xy=dt)
    return [[r[t] for t in TERMS] for r in rows]


def bits(s):
    return max(v.denominator.bit_length() for v in s)


def exact_states(parsed, steps, cap=DENOM_CAP_BITS):
    """States in Fraction until `steps` or the cap. Returns (states, growth, cap step)."""
    states, growth = [list(parsed["start"])], [bits(parsed["start"])]
    for n in range(1, steps + 1):
        nxt = lorenz_step(states[-1], parsed["coefficients"], parsed["dt"])
        b = bits(nxt)
        if b > cap:
            return states, growth, n
        states.append(nxt)
        growth.append(b)
    return states, growth, None


# ---------------------------------------------------------------- exact solve

def solve_exact(rows, rhs):
    """Rows of ten Fractions, right-hand sides (one per component).
    Returns (rank, coefficient lists or None). Full column rank -> unique."""
    m, n, k = len(rows), len(TERMS), len(rhs)
    A = [list(rows[i]) + [rhs[c][i] for c in range(k)] for i in range(m)]
    rank, pivots = 0, []
    for col in range(n):
        piv = next((r for r in range(rank, m) if A[r][col] != 0), None)
        if piv is None:
            continue
        A[rank], A[piv] = A[piv], A[rank]
        inv = 1 / A[rank][col]
        A[rank] = [v * inv for v in A[rank]]
        for r in range(m):
            if r != rank and A[r][col] != 0:
                f = A[r][col]
                A[r] = [a - f * b for a, b in zip(A[r], A[rank])]
        pivots.append(col)
        rank += 1
        if rank == m:
            break
    if rank < n:
        return rank, None
    return rank, [[A[i][n + c] for i in range(n)] for c in range(k)]


def verify_exact(states, coeffs):
    """Every step by exact equality. Returns (steps checked, first mismatch or None)."""
    for n in range(len(states) - 1):
        terms = phi(states[n])
        for c in range(3):
            got = sum(a * t for a, t in zip(coeffs[c], terms))
            if got != states[n + 1][c]:
                return n, {"step": n, "component": "xyz"[c],
                           "predicted": str(got)[:80], "observed": str(states[n + 1][c])[:80],
                           "rule": "predicted next state is not equal to the generated one"}
    return len(states) - 1, None


# ---------------------------------------------------------------- modular

def is_prime(n):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d, r = d // 2, r + 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):   # exact below 3.3e24
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def primes_below(limit, count):
    out, n = [], limit - 1
    while len(out) < count:
        if is_prime(n):
            out.append(n)
        n -= 1
    return out


def mod_states(parsed, steps, p):
    f = lambda v: v.numerator % p * pow(v.denominator, -1, p) % p   # noqa: E731
    c = {k: f(v) for k, v in parsed["coefficients"].items()}
    dt = f(parsed["dt"])
    states = [[f(v) for v in parsed["start"]]]
    for _ in range(steps):
        x, y, z = states[-1]
        states.append([(x + dt * c["sigma"] * (y - x)) % p,
                       (y + dt * (x * (c["rho"] - z) - y)) % p,
                       (z + dt * (x * y - c["beta"] * z)) % p])
    return states


def solve_mod(states, p):
    """Rank and the coefficients modulo p, from every transition; also
    whether every transition is consistent with them."""
    n = len(TERMS)
    A = []
    for i in range(len(states) - 1):
        x, y, z = states[i]
        row = [1, x, y, z, x * y % p, x * z % p, y * z % p, x * x % p, y * y % p, z * z % p]
        A.append(row + list(states[i + 1]))
    rank = 0
    for col in range(n):
        piv = next((r for r in range(rank, len(A)) if A[r][col] % p), None)
        if piv is None:
            continue
        A[rank], A[piv] = A[piv], A[rank]
        inv = pow(A[rank][col], -1, p)
        A[rank] = [v * inv % p for v in A[rank]]
        for r in range(len(A)):
            if r != rank and A[r][col] % p:
                f = A[r][col]
                A[r] = [(a - f * b) % p for a, b in zip(A[r], A[rank])]
        rank += 1
    if rank < n:
        return rank, None, False
    consistent = all(all(v % p == 0 for v in row[n:]) for row in A[n:])
    return rank, [[A[i][n + c] for i in range(n)] for c in range(3)], consistent


def reconstruct(residue, modulus):
    """The rational n/d with |n|, d <= sqrt(modulus / 2) that is `residue`
    modulo `modulus`, or None when there is none."""
    bound = math.isqrt(modulus // 2)
    r0, r1, t0, t1 = modulus, residue % modulus, 0, 1
    while r1 > bound:
        q = r0 // r1
        r0, r1, t0, t1 = r1, r0 - q * r1, t1, t0 - q * t1
    if t1 == 0 or abs(t1) > bound:
        return None
    out = Fraction(r1, t1)
    return out if (out.numerator - residue * out.denominator) % modulus == 0 else None


def crt(residues, primes):
    x, m = 0, 1
    for r, p in zip(residues, primes):
        x += m * ((r - x) * pow(m, -1, p) % p)
        m *= p
    return x % m, m


def modular_fit(parsed, steps, exact):
    primes = primes_below(2 ** 61, N_PRIMES)
    per, sols = [], []
    for p in primes:
        states = mod_states(parsed, steps, p)
        rank, sol, consistent = solve_mod(states, p)
        per.append({"prime": p, "rank": rank, "transitions": steps,
                    "all_transitions_consistent": consistent})
        sols.append(sol)
    if any(s is None for s in sols):
        return {"primes": per, "coefficients": None,
                "reason": "the system is rank deficient modulo a prime"}, None
    coeffs = []
    for c in range(3):
        row = []
        for j in range(len(TERMS)):
            residue, modulus = crt([s[c][j] for s in sols], primes)
            row.append(reconstruct(residue, modulus))
        coeffs.append(row)
    if any(v is None for row in coeffs for v in row):
        return {"primes": per, "coefficients": None,
                "reason": "rational reconstruction failed for a coefficient"}, None
    checked, miss = verify_exact(exact, coeffs)
    mod_ok = []
    for p in primes:
        states = mod_states(parsed, steps, p)
        ok = True
        for n in range(steps):
            x, y, z = states[n]
            terms = [1, x, y, z, x * y, x * z, y * z, x * x, y * y, z * z]
            for c in range(3):
                got = sum(a.numerator * pow(a.denominator, -1, p) * t
                          for a, t in zip(coeffs[c], terms)) % p
                ok = ok and got == states[n + 1][c]
        mod_ok.append(ok)
    return {"primes": per,
            "checked_exactly": {"steps": checked, "mismatch": miss},
            "checked_modulo_each_prime": {"steps": steps, "all_hold": all(mod_ok),
                                          "note": "necessary, not sufficient"}}, \
        coeffs if miss is None and all(mod_ok) else None


# ---------------------------------------------------------------- one run

def show(coeffs):
    return [{t: str(v) for t, v in zip(TERMS, row) if v != 0} for row in coeffs]


def read_back(coeffs, dt):
    """ODE coefficients from an explicit Euler step map: (coef - identity) / dt."""
    own = ("x", "y", "z")
    out = []
    for c in range(3):
        out.append({t: str((v - (1 if t == own[c] else 0)) / dt)
                    for t, v in zip(TERMS, coeffs[c])
                    if (v - (1 if t == own[c] else 0)) != 0})
    return out


def run(system=None, steps=STEPS_EXACT_RUN, cap=DENOM_CAP_BITS, modular=True, forced=False):
    system = LORENZ if system is None else system
    engaged, log, parsed = engage(system, forced)
    rec = {"version": VERSION, "status": "PROPOSED", "system": system, "trigger": log,
           "steps_asked": steps, "denominator_cap_bits": cap, "modular_allowed": modular,
           "branch": None, "verdict": None, "void_reason": None,
           "human_interest": None, "ai_interest": None}
    if not engaged:
        rec.update(branch="NOT_ENGAGED", verdict=None)
        return rec
    states, growth, cap_step = exact_states(parsed, steps, cap)
    rec["growth"] = {"denominator_bits_per_step": growth, "cap_hit_at_step": cap_step,
                     "exact_states": len(states), "exact_transitions": len(states) - 1}
    rows = [phi(s) for s in states[:-1]]
    rhs = [[states[i + 1][c] for i in range(len(states) - 1)] for c in range(3)]
    rank, coeffs = solve_exact(rows, rhs) if rows else (0, None)
    rec["exact_solve"] = {"rank": rank, "unknowns_per_component": len(TERMS),
                          "unique": rank == len(TERMS)}
    planted = planted_map(parsed["coefficients"], parsed["dt"])
    if coeffs is not None and cap_step is None:
        rec["branch"] = "EXACT"
    elif coeffs is not None:
        rec["branch"] = "EXACT"
        rec["growth"]["note"] = (f"the cap stopped generation at step {cap_step}; the "
                                 f"{len(states) - 1} exact steps before it give full rank")
    elif not modular:
        rec.update(branch="VOID", verdict="VOID",
                   void_reason=f"denominator cap ({cap} bits) reached at step {cap_step} with "
                               f"rank {rank} of {len(TERMS)} and no modular branch; "
                               "no float fallback")
        return rec
    else:
        rec["branch"] = "MODULAR"
        rec["modular"], coeffs = modular_fit(parsed, steps, states)
        if coeffs is None:
            rec.update(verdict="VOID", void_reason="the modular branch did not return a map: "
                       + str(rec["modular"].get("reason", "a check failed")))
            return rec
    checked, miss = verify_exact(states, coeffs)
    sets = [{t for t, v in zip(TERMS, row) if v != 0} for row in coeffs]
    hits = sum(1 for c in range(3) if coeffs[c] == planted[c])
    rec.update(
        recovered_step_map=show(coeffs), planted_step_map=show(planted),
        recovered_term_sets=[sorted(s) for s in sets],
        planted_term_sets=[sorted(s) for s in PLANTED_SETS],
        components_equal_to_planted=hits, term_sets_equal=sets == PLANTED_SETS,
        unique=rec["exact_solve"]["unique"] if rec["branch"] == "EXACT"
        else all(p["rank"] == len(TERMS) for p in rec["modular"]["primes"]),
        ode_coefficients_read_back=read_back(coeffs, parsed["dt"]),
        verification={"steps_checked_exactly": checked, "mismatch": miss,
                      "rule": "exact equality at every step; no tolerance, no BIC"},
        verdict="PASS" if miss is None and hits == 3 else "FAIL",
        located_error=miss)
    # the null: one coefficient moved by 1/1000 must fail the exact check, located
    nulls = []
    for c in range(3):
        for j, t in enumerate(TERMS):
            bent = [list(r) for r in coeffs]
            bent[c][j] += PERTURBATION
            _, m = verify_exact(states, bent)
            nulls.append({"component": "xyz"[c], "term": t,
                          "was_zero": coeffs[c][j] == 0, "check_fails": m is not None,
                          "located_at": None if m is None else
                          {"step": m["step"], "component": m["component"]}})
    rec["null_perturbation"] = {
        "perturbation": str(PERTURBATION), "trials": len(nulls),
        "check_failed": sum(1 for n in nulls if n["check_fails"]),
        "not_caught": [n for n in nulls if not n["check_fails"]],
        "first": nulls[1], "all_caught": all(n["check_fails"] for n in nulls)}
    return rec


def build():
    exact = run(steps=STEPS_EXACT_RUN)
    long_run = run(steps=STEPS_LONG_RUN)
    capped = run(steps=STEPS_LONG_RUN, cap=256)
    capped_void = run(steps=STEPS_LONG_RUN, cap=256, modular=False)
    floats = run(system=dict(LORENZ, coefficients={"sigma": 10.0, "rho": 28.0,
                                                   "beta": 8.0 / 3.0}, dt=0.005))
    forced = run(system=dict(LORENZ, dt=0.005), forced=True)
    agree = capped.get("recovered_step_map") == exact.get("recovered_step_map")
    claims = [
        {"scope": "fab::eqsearch::exact::step_map_recovery",
         "measured": exact.get("components_equal_to_planted"), "value": 3,
         "unique": exact.get("unique"), "verdict": "pass"
         if exact["verdict"] == "PASS" and exact.get("unique") else "fail",
         "tol_source": "DEFINITION", "tol_note": "exact equality; there is no tolerance"},
        {"scope": "fab::eqsearch::exact::null_perturbed_coefficient",
         "measured": exact.get("null_perturbation", {}).get("check_failed"),
         "value": exact.get("null_perturbation", {}).get("trials"),
         "verdict": "pass" if exact.get("null_perturbation", {}).get("all_caught") else "fail",
         "tol_source": "DEFINITION", "tol_note": "every perturbed map must fail"},
        {"scope": "fab::eqsearch::exact::modular_branch_agrees",
         "measured": agree, "value": True,
         "verdict": "pass" if capped["branch"] == "MODULAR" and capped["verdict"] == "PASS"
         and agree else "fail", "tol_source": "DEFINITION",
         "tol_note": "the same map, coefficient for coefficient"},
        {"scope": "fab::eqsearch::exact::cap_without_branch_is_void",
         "measured": capped_void["verdict"], "value": "VOID",
         "verdict": "pass" if capped_void["verdict"] == "VOID" else "fail",
         "tol_source": "DEFINITION", "tol_note": "VOID, never a float fallback"},
        {"scope": "fab::eqsearch::exact::float_system_not_engaged",
         "measured": floats["branch"], "value": "NOT_ENGAGED",
         "verdict": "pass" if floats["branch"] == "NOT_ENGAGED"
         and forced["branch"] == "NOT_ENGAGED" else "fail",
         "tol_source": "DEFINITION", "tol_note": "a float is refused, also under --exact"}]
    return {"version": VERSION, "status": "PROPOSED",
            "scope": "the step map of a declared rational system from exact, noise-free "
                     "states; nothing about measured data",
            "declared_in": "eqsearch/DECLARED.json (committed before any run)",
            "runs": {"exact_12_steps": exact, "long_40_steps_cap_65536": long_run,
                     "long_40_steps_cap_256_modular": capped,
                     "long_40_steps_cap_256_no_modular": capped_void,
                     "float_system": floats, "float_step_forced": forced},
            "claims": claims, "human_interest": None, "ai_interest": None}


def selftest():
    rec = build()
    checks = [(c["scope"].split("::")[-1], c["verdict"] == "pass") for c in rec["claims"]]
    ex = rec["runs"]["exact_12_steps"]
    checks.append(("a wrong planted system is caught",
                   verify_exact(exact_states(engage(dict(LORENZ, coefficients=dict(
                       LORENZ["coefficients"], rho="28001/1000")))[2], 6)[0],
                       planted_map(engage(LORENZ)[2]["coefficients"],
                                   engage(LORENZ)[2]["dt"]))[1] is not None))
    checks.append(("read-back gives sigma 10, rho 28, beta 8/3",
                   ex["ode_coefficients_read_back"] == [
                       {"x": "-10", "y": "10"}, {"x": "28", "y": "-1", "xz": "-1"},
                       {"z": "-8/3", "xy": "1"}]))
    for name, ok in checks:
        print(("PASS  " if ok else "FAIL  ") + name)
    print(f"checks: {len(checks)}   failed: {sum(1 for _, ok in checks if not ok)}")
    return 0 if all(ok for _, ok in checks) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="equation_search exact tier")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exact", action="store_true", help="force the trigger")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.output is None:
        parser.error("--output is required (or --selftest)")
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    rec = build()
    args.output.write_text(json.dumps(rec, indent=1, ensure_ascii=True) + "\n", encoding="ascii")
    for name, r in rec["runs"].items():
        g = r.get("growth", {})
        print(f"{name:36s} {r['branch']:12s} verdict {r['verdict']}  "
              f"exact steps {g.get('exact_transitions')}  cap at {g.get('cap_hit_at_step')}")
    for c in rec["claims"]:
        print(f"   {c['verdict']:5s} {c['scope'].split('::')[-1]}: {c['measured']}")
    print("written ->", args.output)
    return 0 if all(c["verdict"] == "pass" for c in rec["claims"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
