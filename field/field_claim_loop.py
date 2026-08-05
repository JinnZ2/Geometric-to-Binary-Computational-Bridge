#!/usr/bin/env python3
"""
field_claim_loop.py  --  CC0, stdlib only, phone-buildable, no deps.

A curiosity engine that learns a physical environment from direct
transducers. Author's handoff spec is section 1-5 below, unedited.
Section 0 is what the router measured when it was put under test, and
what changed as a result.

=====================================================================
0. AUDIT  --  FCL-1..10, measured 2026-08-05
=====================================================================
The skeleton's router did not fork four ways. Under any logged anchor
it forked one way, and the branch that spawns new claims could not
fire at all. Numbers below are from tests/test_field_claim_loop.py;
`python field/falsifiers_field_loop.py` reruns them and exits nonzero
on failure.

FCL-1  NOVEL was unreachable whenever an anchor channel was logged.
       INSTRUMENT appended a candidate whenever `moved` was non-empty,
       including at weight 0.0 for a perfectly stable rig. NOVEL was
       guarded by `if hits and not cands`, so a non-empty cands list
       disabled it. Measured: 14 residuals, anchor 0.0 throughout,
       candidates = [INSTRUMENT 0.0], NOVEL absent, and the emitted
       query was "cross-check against a second transducer" when the
       correct action was "spawn a claim". The branch that detects new
       territory switched off exactly when instrumentation was good.
       FIX: a route contributes a candidate only with positive
       evidence. NOVEL is now computed from the other three coming
       back negative, and records that negative evidence.

FCL-2  `anchor` is specified in section 6 as "reading from the
       stability-reference channel at same ts" and used as
       `abs(r["anchor"]) > 0`, which is a test on a DEVIATION. Fed a
       reading (1004 hPa), INSTRUMENT wins at weight 1.0 on every
       claim forever and the router has one branch. Fed a deviation,
       float noise makes `> 0` true almost always anyway.
       FIX: field renamed `anchor_dev`, defined as reference minus its
       own expected value in reference units, with an explicit
       ANCHOR_TOL. `anchor_raw` carries the reading. OPEN QUESTION for
       the author is in section 5a -- what the physical standard is.

FCL-3  NOISE_AS_SIGNAL had no minimum-sample gate. MIN_SAMPLES gated
       the covariate branch only. Measured false-positive rate on
       white residuals at the shipped |r|>0.35: n=5 23.5%, n=8 21.9%,
       n=20 8.3%, n=40 1.6%. The residual series is short BY
       CONSTRUCTION -- it holds only band-breaking readings -- so the
       small-n regime is the normal one, not the edge case.
       FIX: AUTOCORR_MIN_N, and a band that scales as z/sqrt(n)
       instead of a fixed 0.35.

FCL-4  Worse, and the reason a fixed lag cannot work: for a periodic
       rider of period T, rho(lag) = cos(2*pi*lag/T). At the shipped
       lag=3 that is zero at T=12 and small for T in {4,10,14,16}.
       Measured power at n=100 against sin(2*pi*i/T)+N(0,0.5):
         T= 4   0.0%     T=12   0.0%     T=24  98.6%
         T= 6 100.0%     T=14   0.0%     T=48 100.0%
         T= 8  98.5%     T=16   0.1%
       A branch built to catch a second variable riding the residual
       is blind to whole bands of them. 22% false alarm and 0% power
       on the same statistic, in the same configuration.
       FIX: scan lags 1..AUTOCORR_MAX_LAG, take the max |rho|, widen
       the band for multiplicity. Measured after: 2.6% on white noise,
       100% power at T=6, 12 and 24.

FCL-5  MISSING_VARIABLE compared a bin rate to 1.5x the base rate with
       no significance test. Section 5c calls this "too permissive";
       the size of it was unmeasured. Null covariates, independent of
       residuals: 40 readings / 4 levels 34.7%, 200 / 8 levels 34.0%,
       200 / 4 levels at base rate 0.10 41.0%. It gets WORSE with more
       data at a low base rate, because more bins clear MIN_SAMPLES
       and each is another chance to fire.
       FIX: exact one-sided binomial tail against the base rate,
       Bonferroni-corrected over the bins actually tested.

FCL-6  `hit + (r in hits)` is dict equality, not identity. Two
       readings with the same channel, value, covariates and ts
       compare equal, and duplicate readings are the normal case for a
       transducer at rest. Measured: 20 readings, ONE of them an
       actual residual, reported "rate 1.00 under phase=dusk vs base
       0.05" -- a fabricated MISSING_VARIABLE finding from a single
       break. FIX: membership by index.

FCL-7  `deepen()` accepted any band, including a wider one.
       `deepen(cid, -1e9, 1e9)` produced a claim labelled "[refined]"
       that is strictly weaker than its parent. Section 4 requires "a
       tighter band or an added axis" and nothing checked it.
       FIX: the child band must be strictly inside the parent, or
       `added_axis` must name the new axis. Otherwise ValueError.

FCL-8  No spend ledger (section 5d, "NOT IMPLEMENTED"). next_query
       appended an unbounded stream of pending queries and would
       re-append an identical one on every call.
       FIX: LEDGER.jsonl, per-route costs, a hard cap, dedup of an
       identical pending (claim, route). resolve_query() credits the
       ledger with whether the funded query actually moved the claim,
       so `yield_rate()` states what fraction of spend bought a
       change. Costs are PLACEHOLDERS pending bench measurement.

FCL-9  `shape` is documented canonical -- "Do NOT scalarize on ingest"
       -- and no code path reads it. test() compares `value` only, so
       every claim in the system is tested on the scalar projection.
       Storing the shape without testing against it is scalarizing
       with a receipt. Not fixed here, because what the shape-level
       band should be is a physics question, not a coding one.
       PARTIAL FIX: a reading that carries a shape must name the
       `projection` that produced `value` from it. The scalarization
       becomes explicit and auditable instead of silent. Claims record
       which projection they test.

FCL-10 `cid = "c%03d" % (len(_load(CLAIMS)) + 1)` counts log LINES,
       but _claims() takes the latest record per id, so the log is
       meant to hold updates. Measured: ids ran c001, c002, c004, c007
       after two updates. Gaps only, until the log is ever compacted
       on a device that is short of space -- then len() shrinks and
       the next id collides with a live claim. FIX: max over existing
       ids.

Not fixed, and stated rather than papered over:
  - The residual series is indexed by POSITION, not time. Readings
    inside the band are dropped before the autocorrelation runs, so
    lag k is "k residuals ago", not a duration. Against an irregular
    sampling schedule the lag scan is measuring something without
    units. It needs resampling onto a time grid, which needs a
    sampling policy that does not exist yet.
  - Section 5e, the conservation ledger, is not implemented. See the
    OPEN QUESTION in section 5e.

=====================================================================
1. WHAT THIS IS                          (author's spec, from here on)
=====================================================================
A curiosity engine that learns a physical environment (forest, soil,
mycorrhizal network, insect and amphibian activity) from DIRECT
TRANSDUCERS rather than from textbooks, from prose descriptions, or
from a human translating readings into English first.

Rationale, in the author's frame:
  Curiosity is not a metabolic luxury funded by surplus. It is
  amortized self-preservation. A fixed-boundary organism -- a rote
  metabolism, a calculator -- is perfectly tuned to yesterday and dies
  the day conditions move, which they always do. Infants, worms placed
  on a plate, frogs placed in a pan explore FIRST, before securing
  the known exit. Not knowing the space is the lethal risk.
  Therefore: a system optimized to stay in-distribution is not safe.
  It is carrying an unbooked debt that comes due all at once.

Design consequence: novelty must be coupled to a validity check, or
it is dissipation. The claim table IS that coupling. Exploration that
does not reduce future surprise is heat.

=====================================================================
2. ARCHITECTURE  (five stages)
=====================================================================

  [TRANSDUCER] -> [BRIDGE] -> [CLAIM TABLE] -> [ROUTER] -> [QUERY]
       ^                                                      |
       |______________________ actuate ______________________|

  TRANSDUCER   direct physical sensing only. No human in the signal
               path. No textbook priors seeded.
  BRIDGE       geometric-to-binary. A reading enters as a SHAPE and
               must stay a shape. Do NOT scalarize on ingest.
  CLAIM TABLE  claims, not values. Readings test claims. The
               difference is the RESIDUAL, and the residual is the
               product.
  ROUTER       a residual forks FOUR ways before anything updates.
  QUERY        self-initiating. The engine commands its own next
               sample. A recorder waits; a curious system goes and
               gets the reading.

=====================================================================
3. THE RESIDUAL ROUTER  (the discriminator -- author-specified)
=====================================================================
  INSTRUMENT       sensor drift, loose connection, thermal offset.
                   Test: did the ANCHOR channel move at the same ts?
  NOISE_AS_SIGNAL  the residual may carry a SECOND variable. Test:
                   autocorrelation of the residual sequence.
  NOVEL            no existing claim covers this region.
  MISSING_VARIABLE the residual concentrates under some covariate or
                   cycle phase.

The router PROPOSES ranked candidates with evidence. It does not
conclude.

=====================================================================
4. RE-ENCOUNTER DEEPENS, IT DOES NOT CLOSE
=====================================================================
A supported claim is NOT closed. Each re-support increments depth and
spawns a child claim with a tighter band or an added axis. Terrain is
the checksum.

=====================================================================
5. OPEN PROBLEMS  (do not paper over these)
=====================================================================
  a. INSTRUMENT vs REAL CHANGE is not cleanly separable without a
     stable reference. The anchor channel is weak: an anchor can drift
     too. Needs a physical standard whose failure mode differs from
     the working sensors'.
     OPEN QUESTION: what is the anchor, physically? The mechanism is
     implemented against a declared deviation and tolerance, but the
     standard itself is not specified and was not invented here.
  b. NOISE_AS_SIGNAL can manufacture variables that are not there.
     Autocorrelation catches structure, not meaning. Requires a
     hold-out window before any demodulated channel is promoted.
     STATUS: hold-out is enforced by promote_channel().
  c. MISSING_VARIABLE routing is correlational. Needs a minimum-sample
     gate and a base-rate comparison.  STATUS: see FCL-5.
  d. SELF-INITIATED ACTUATION burns a real energy budget.
     STATUS: implemented, see FCL-8. Costs are placeholders.
  e. No conservation ledger yet.
     OPEN QUESTION: what is the reservoir, in what units? The spend
     ledger counts query cost, which is not the same quantity. Not
     guessed at.
"""
import datetime
import json
import math
import os
import sys

READINGS = "READINGS.jsonl"
CLAIMS = "CLAIMS.jsonl"
QUERIES = "QUERIES.jsonl"
LEDGER = "LEDGER.jsonl"

ROUTES = ("INSTRUMENT", "NOISE_AS_SIGNAL", "NOVEL", "MISSING_VARIABLE")

# --- gates. every one of these was calibrated against a null. see FCL-3..5.
MIN_SAMPLES = 8         # per-covariate-bin floor
COVAR_ALPHA = 0.05      # family-wise, Bonferroni over bins tested
AUTOCORR_MIN_N = 20     # below this the branch reports INSUFFICIENT, not white
AUTOCORR_MAX_LAG = 12   # scan 1..this. a single fixed lag is blind. FCL-4.
AUTOCORR_Z = 2.9        # ~alpha 0.05 after multiplicity over 12 lags
ANCHOR_TOL = 0.0        # deviation magnitude that counts as anchor motion.
#                         0.0 means "any nonzero", which for a float sensor is
#                         always true. SET THIS from the anchor's own noise
#                         floor before trusting INSTRUMENT. FCL-2.

# --- spend ledger. PLACEHOLDER COSTS, replace with bench measurement. FCL-8.
QUERY_COST = {
    "INSTRUMENT": 1.0,        # inspect mount, cross-check second transducer
    "NOISE_AS_SIGNAL": 4.0,   # raise sample rate, hold out a window
    "NOVEL": 2.0,             # resample across range
    "MISSING_VARIABLE": 2.0,  # log a covariate at higher resolution
}
BUDGET = 100.0
HOLDOUT_MIN = 20          # samples reserved before a demodulated channel
#                           may be promoted. section 5b.


# ---------------------------------------------------------------------
def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _append(path, rec):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


# ---------------------------------------------------------------------
# READINGS -- direct transducer only
# ---------------------------------------------------------------------
def reading(channel, value, shape=None, covariates=None, anchor_dev=None,
            anchor_raw=None, projection=None, ts=None):
    """
    channel    : transducer id ('piezo_trunk_n', 'chem_soil_a', 'lux_canopy')
    value      : scalar summary. kept for math ONLY.
    shape      : the reading as it actually arrived -- vector, multi-axis,
                 spectrum. THIS is canonical. value is a projection of it.
    projection : REQUIRED when shape is given. Names the function that
                 produced value from shape ('l2', 'axis_z', 'peak_nm', ...).
                 Not a formality: test() compares value and nothing else, so
                 this is the only record of what got thrown away. FCL-9.
    covariates : {'rain': 1, 'baro_hpa': 1004, 'temp_c': 18, 'phase': 'dusk'}
    anchor_dev : stability reference MINUS its own expected value, in
                 reference units. A deviation, not a reading. FCL-2.
    anchor_raw : the reference reading itself, for provenance. Never routed on.
    """
    if shape is not None and not projection:
        raise ValueError(
            "shape given without projection: name what produced `value` from "
            "it. Silent scalarization is the failure this loop is against.")
    return _append(READINGS, {
        "ts": ts or _now(), "channel": channel, "value": value,
        "shape": shape, "projection": projection,
        "covariates": covariates or {},
        "anchor_dev": anchor_dev, "anchor_raw": anchor_raw})


# ---------------------------------------------------------------------
# CLAIMS -- falsifiable relations with an expected band
# ---------------------------------------------------------------------
def _next_cid(existing):
    """Max over live ids, not a line count. FCL-10."""
    n = 0
    for cid in existing:
        try:
            n = max(n, int(cid.lstrip("c")))
        except ValueError:
            continue
    return "c%03d" % (n + 1)


def claim(statement, channel, lo, hi, parent=None, depth=0, projection=None,
          added_axis=None):
    if lo > hi:
        raise ValueError("claim band is inverted: lo=%r > hi=%r" % (lo, hi))
    cid = _next_cid(_claims())
    return _append(CLAIMS, {
        "id": cid, "ts": _now(), "statement": statement, "channel": channel,
        "lo": lo, "hi": hi, "parent": parent, "depth": depth,
        "projection": projection, "added_axis": added_axis,
        "support": 0, "n_residuals": 0, "status": "open"})


def _claims():
    """Latest state per claim id. The log is append-only; updates re-append."""
    out = {}
    for c in _load(CLAIMS):
        out[c["id"]] = c
    return out


def test(cid, r, claims=None):
    """Signed residual of reading r against claim cid. 0.0 = inside band.

    Compares `value` only. A claim has no shape-level band yet -- FCL-9.
    """
    c = (claims or _claims())[cid]
    v = r["value"]
    if v < c["lo"]:
        return v - c["lo"]
    if v > c["hi"]:
        return v - c["hi"]
    return 0.0


def refresh(cid):
    """Recount support and residuals from the log and append the update.

    `support` and `status` were carried on every claim record and never
    written by anything.
    """
    cs = _claims()
    c = dict(cs[cid])
    rs = [r for r in _load(READINGS) if r["channel"] == c["channel"]]
    resid = sum(1 for r in rs if test(cid, r, cs) != 0.0)
    c.update(ts=_now(), support=len(rs) - resid, n_residuals=resid,
             status="open")
    return _append(CLAIMS, c)


def deepen(cid, new_lo, new_hi, statement=None, added_axis=None,
           projection=None):
    """Re-support spawns a child at higher resolution. It does not close.

    The child must be strictly tighter than the parent, or must name an
    added axis. "[refined]" was previously accepted on a wider band. FCL-7.
    """
    c = _claims()[cid]
    if new_lo > new_hi:
        raise ValueError("child band is inverted: lo=%r > hi=%r"
                         % (new_lo, new_hi))
    tighter = (new_lo >= c["lo"] and new_hi <= c["hi"]
               and (new_hi - new_lo) < (c["hi"] - c["lo"]))
    if not tighter and not added_axis:
        raise ValueError(
            "deepen requires a strictly tighter band or an added axis. "
            "parent [%r, %r], child [%r, %r]. A wider child labelled "
            "'refined' is a weaker claim wearing the word."
            % (c["lo"], c["hi"], new_lo, new_hi))
    return claim(statement or (c["statement"] + " [refined]"), c["channel"],
                 new_lo, new_hi, parent=cid, depth=c["depth"] + 1,
                 projection=projection or c.get("projection"),
                 added_axis=added_axis)


# ---------------------------------------------------------------------
# statistics -- each calibrated against its own null
# ---------------------------------------------------------------------
def _autocorr(xs, lag):
    """Biased sample autocorrelation at one lag. Bounded in [-1, 1]."""
    n = len(xs)
    if n <= lag + 1:
        return 0.0
    m = sum(xs) / n
    den = sum((x - m) ** 2 for x in xs)
    if den == 0:
        return 0.0
    num = sum((xs[i] - m) * (xs[i + lag] - m) for i in range(n - lag))
    return num / den


def autocorr_scan(xs, max_lag=AUTOCORR_MAX_LAG, z=AUTOCORR_Z,
                  min_n=AUTOCORR_MIN_N):
    """Max |rho| over lags 1..max_lag, against a multiplicity-widened band.

    A single fixed lag has rho = cos(2*pi*lag/T) against a rider of period T,
    so it is blind wherever that cosine is small. FCL-4.
    """
    n = len(xs)
    if n < min_n:
        return {"status": "INSUFFICIENT", "n": n, "min_n": min_n,
                "rho": 0.0, "lag": None, "threshold": None}
    lags = [L for L in range(1, max_lag + 1) if n > L + 1]
    if not lags:
        return {"status": "INSUFFICIENT", "n": n, "min_n": min_n,
                "rho": 0.0, "lag": None, "threshold": None}
    rho, lag = max(((_autocorr(xs, L), L) for L in lags),
                   key=lambda t: abs(t[0]))
    thr = z / math.sqrt(n)
    return {"status": "STRUCTURED" if abs(rho) > thr else "WHITE",
            "n": n, "min_n": min_n, "rho": rho, "lag": lag, "threshold": thr,
            "lags_scanned": len(lags)}


def _binom_tail(k, n, p):
    """P(X >= k) for X ~ Binomial(n, p), exact, in log space.

    math.comb(n, i) is an exact int and overflows float conversion above
    n ~ 1000, so the terms are summed via lgamma rather than multiplied out.
    """
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    lp, lq = math.log(p), math.log1p(-p)
    lgn = math.lgamma(n + 1)
    total = 0.0
    for i in range(k, n + 1):
        lt = (lgn - math.lgamma(i + 1) - math.lgamma(n - i + 1)
              + i * lp + (n - i) * lq)
        if lt < -745.0:                 # exp underflows; the tail is done
            if i > n * p:
                break
            continue
        total += math.exp(lt)
    return min(1.0, total)


def covariate_concentration(hit_idx, all_rs, alpha=COVAR_ALPHA,
                            min_samples=MIN_SAMPLES):
    """Bins where residuals concentrate beyond chance.

    Exact one-sided binomial tail against the base rate, Bonferroni over the
    bins actually tested. The shipped `rate > 1.5 * base` fired on 35-41% of
    null covariate sets. FCL-5.

    hit_idx is a set of INDICES into all_rs. Membership was `r in hits`, dict
    equality, which counts duplicate readings as residuals. FCL-6.
    """
    n = len(all_rs)
    if n < min_samples:
        return []
    base = len(hit_idx) / float(n)
    if base <= 0.0 or base >= 1.0:
        return []
    bins = {}
    for i, r in enumerate(all_rs):
        for k, v in (r.get("covariates") or {}).items():
            key = (k, str(v))
            tot, hit = bins.get(key, (0, 0))
            bins[key] = (tot + 1, hit + (1 if i in hit_idx else 0))
    tested = [(key, tv) for key, tv in bins.items() if tv[0] >= min_samples]
    if not tested:
        return []
    adj = alpha / len(tested)
    out = []
    for (k, v), (tot, hit) in tested:
        p = _binom_tail(hit, tot, base)
        if p <= adj:
            out.append({"covariate": k, "value": v, "n": tot, "hits": hit,
                        "rate": round(hit / float(tot), 3),
                        "base": round(base, 3), "p": p,
                        "alpha_adj": adj, "bins_tested": len(tested)})
    return sorted(out, key=lambda d: d["p"])


# ---------------------------------------------------------------------
# ROUTER -- proposes, never concludes
# ---------------------------------------------------------------------
def route(cid, anchor_tol=ANCHOR_TOL):
    """Fork the residuals of one claim four ways.

    Every route is evaluated. A route contributes a candidate only when its
    own evidence is positive; a zero-weight candidate used to be appended for
    INSTRUMENT and that alone disabled NOVEL. FCL-1.
    """
    cs = _claims()
    c = cs[cid]
    rs = [r for r in _load(READINGS) if r["channel"] == c["channel"]]
    hit_idx, series = set(), []
    for i, r in enumerate(rs):
        d = test(cid, r, cs)
        if d != 0.0:
            hit_idx.add(i)
            series.append(d)
    cands, negative = [], []

    # INSTRUMENT: did the stability anchor move at the same timestamps?
    withdev = [rs[i] for i in sorted(hit_idx)
               if rs[i].get("anchor_dev") is not None]
    if withdev:
        drift = sum(1 for r in withdev if abs(r["anchor_dev"]) > anchor_tol)
        if drift:
            cands.append({
                "route": "INSTRUMENT",
                "evidence": "anchor deviation exceeds tol=%g on %d/%d residual "
                            "samples" % (anchor_tol, drift, len(withdev)),
                "weight": drift / float(len(withdev))})
        else:
            negative.append("anchor within tol=%g on all %d residual samples"
                            % (anchor_tol, len(withdev)))
    else:
        negative.append("no anchor logged on any residual sample -- "
                        "INSTRUMENT could not be ruled out, only unmeasured")

    # NOISE_AS_SIGNAL: structured or white, scanned over lags.
    ac = autocorr_scan(series)
    if ac["status"] == "STRUCTURED":
        cands.append({
            "route": "NOISE_AS_SIGNAL",
            "evidence": "residual autocorr = %.2f at lag %d (band %.2f, "
                        "n=%d, %d lags scanned) -- candidate second channel"
                        % (ac["rho"], ac["lag"], ac["threshold"], ac["n"],
                           ac["lags_scanned"]),
            "weight": min(1.0, abs(ac["rho"]))})
    elif ac["status"] == "INSUFFICIENT":
        negative.append("residual series n=%d below AUTOCORR_MIN_N=%d -- "
                        "not white, unjudged" % (ac["n"], ac["min_n"]))
    else:
        negative.append("residual white: max|rho|=%.2f at lag %d under band "
                        "%.2f" % (ac["rho"], ac["lag"], ac["threshold"]))

    # MISSING_VARIABLE: does the break concentrate under a covariate?
    conc = covariate_concentration(hit_idx, rs)
    for d in conc[:3]:
        cands.append({
            "route": "MISSING_VARIABLE",
            "evidence": "%d/%d residual under %s=%s (rate %.2f vs base %.2f), "
                        "p=%.2g against Bonferroni alpha=%.2g over %d bins"
                        % (d["hits"], d["n"], d["covariate"], d["value"],
                           d["rate"], d["base"], d["p"], d["alpha_adj"],
                           d["bins_tested"]),
            "weight": max(0.0, d["rate"] - d["base"])})
    if not conc:
        negative.append("no covariate bin concentrates beyond a "
                        "Bonferroni-corrected binomial tail")

    # NOVEL: residuals exist and the other three came back negative.
    if hit_idx and not cands:
        cands.append({"route": "NOVEL",
                      "evidence": "%d residuals; " % len(hit_idx)
                                  + "; ".join(negative),
                      "weight": 1.0})

    cands.sort(key=lambda d: -d["weight"])
    return {"claim": cid, "n_readings": len(rs), "n_residuals": len(hit_idx),
            "candidates": cands, "negative_evidence": negative,
            "note": "PROPOSAL ONLY. correlation is not the variable."}


# ---------------------------------------------------------------------
# QUERY -- the engine commands its own next sample, on a budget
# ---------------------------------------------------------------------
def _queries():
    """Latest state per query id. Same append-and-supersede rule as _claims().

    Written after the first draft of this file scanned _load(QUERIES) raw and
    saw a resolved query's superseded 'pending' record forever -- FCL-10 in a
    second place, one function over.
    """
    out = {}
    for q in _load(QUERIES):
        out[q["id"]] = q
    return out


def _next_qid(existing):
    n = 0
    for qid in existing:
        try:
            n = max(n, int(qid.lstrip("q")))
        except ValueError:
            continue
    return "q%03d" % (n + 1)


def _ledger():
    return _load(LEDGER)


def spent():
    return sum(e["cost"] for e in _ledger() if e["kind"] == "spend")


def remaining(budget=BUDGET):
    return budget - spent()


def yield_rate():
    """Fraction of funded queries that actually moved a claim.

    Section 1: exploration that does not reduce future surprise is heat. This
    is the number that says how much of the spend was heat.
    """
    qs = list(_queries().values())
    pending = sum(1 for q in qs if q.get("status") == "pending")
    resolved = [q for q in qs if q.get("status") in ("moved", "no_change")]
    if not resolved:
        return {"resolved": 0, "moved": 0, "rate": None,
                "spent": spent(), "pending": pending}
    moved = sum(1 for q in resolved if q["status"] == "moved")
    return {"resolved": len(resolved), "moved": moved,
            "rate": moved / float(len(resolved)), "spent": spent(),
            "pending": pending}


ASK = {
    "INSTRUMENT": "cross-check %s against a second transducer of different "
                  "failure mode; inspect mount and lead",
    "NOISE_AS_SIGNAL": "raise sample rate on %s and hold out >=%d samples "
                       "before promoting any demodulated channel",
    "NOVEL": "resample %s across its full range; spawn child claim",
    "MISSING_VARIABLE": "log the suspected covariate at higher resolution "
                        "alongside %s and re-test",
}


def next_query(cid, budget=BUDGET):
    """Emit the follow-up experiment the top route implies, if affordable.

    Refuses a duplicate of an already-pending (claim, route) and refuses to
    exceed the budget. Unbounded curiosity is the dissipation the design
    condemns. FCL-8.
    """
    rt = route(cid)
    if not rt["candidates"]:
        return None
    top = rt["candidates"][0]
    qs = _queries()
    for q in qs.values():
        if (q["claim"] == cid and q["route"] == top["route"]
                and q.get("status") == "pending"):
            return {"refused": "duplicate", "pending": q["id"],
                    "claim": cid, "route": top["route"]}
    cost = QUERY_COST[top["route"]]
    left = remaining(budget)
    if cost > left:
        return {"refused": "budget", "cost": cost, "remaining": left,
                "claim": cid, "route": top["route"],
                "note": "curiosity is amortized self-preservation, not free. "
                        "raise BUDGET deliberately or resolve open queries."}
    action = ASK[top["route"]]
    action = (action % (_claims()[cid]["channel"], HOLDOUT_MIN)
              if top["route"] == "NOISE_AS_SIGNAL"
              else action % _claims()[cid]["channel"])
    qid = _next_qid(qs)
    q = _append(QUERIES, {
        "id": qid, "ts": _now(), "claim": cid, "route": top["route"],
        "action": action, "evidence": top["evidence"], "cost": cost,
        "status": "pending"})
    _append(LEDGER, {"ts": _now(), "kind": "spend", "query": qid,
                     "route": top["route"], "cost": cost})
    return q


def resolve_query(qid, moved):
    """Close a funded query. moved=True if the claim actually changed.

    Without this the ledger counts spend and never return, which is a budget,
    not an accounting.
    """
    qs = _queries()
    if qid not in qs:
        raise KeyError("no such query: %r" % qid)
    q = dict(qs[qid])
    if q.get("status") != "pending":
        raise ValueError("query %s already resolved as %r"
                         % (qid, q.get("status")))
    q.update(ts=_now(), status="moved" if moved else "no_change")
    _append(QUERIES, q)
    _append(LEDGER, {"ts": _now(), "kind": "return", "query": qid,
                     "route": q["route"], "cost": 0.0, "moved": bool(moved)})
    return q


def promote_channel(name, fit_residuals, holdout_residuals,
                    min_n=HOLDOUT_MIN, z=1.96):
    """Section 5b: a demodulated channel needs a hold-out before promotion.

    The fit window SELECTS a lag; the hold-out TESTS that one lag. Asking the
    hold-out to rediscover the lag on its own is the wrong test twice over --
    it re-pays the multiple-comparison cost, and for a periodic rider the
    autocorrelation peaks at several lags of near-equal size (period 8 peaks
    at lag 4 and lag 8 alike), so noise decides which one each window names.
    Fixing the lag first means the hold-out faces a single hypothesis and the
    band is the uncorrected z, not the scan-corrected one.
    """
    if len(holdout_residuals) < min_n:
        return {"channel": name, "promoted": False, "fit": None,
                "holdout": None,
                "reason": "hold-out n=%d below %d"
                          % (len(holdout_residuals), min_n)}
    a = autocorr_scan(fit_residuals)
    if a["status"] != "STRUCTURED":
        return {"channel": name, "promoted": False, "fit": a, "holdout": None,
                "reason": "fit window is %s -- nothing to promote" % a["status"]}
    n = len(holdout_residuals)
    rho = _autocorr(holdout_residuals, a["lag"])
    thr = z / math.sqrt(n)
    ok = abs(rho) > thr and (rho > 0) == (a["rho"] > 0)
    return {"channel": name, "promoted": ok, "fit": a,
            "holdout": {"lag": a["lag"], "rho": rho, "threshold": thr, "n": n},
            "reason": ("lag %d survives out of sample: rho %.2f vs band %.2f"
                       % (a["lag"], rho, thr)) if ok else
                      ("lag %d selected on fit (rho %.2f) does not survive: "
                       "hold-out rho %.2f vs band %.2f"
                       % (a["lag"], a["rho"], rho, thr))}


# ---------------------------------------------------------------------
def status():
    cs, rs, qs = _claims(), _load(READINGS), _load(QUERIES)
    y = yield_rate()
    print("readings %d | claims %d | queries %d | spent %.1f/%.1f"
          % (len(rs), len(cs), len(qs), spent(), BUDGET))
    if y["rate"] is not None:
        print("curiosity yield: %d/%d funded queries moved a claim (%.0f%%)"
              % (y["moved"], y["resolved"], 100.0 * y["rate"]))
    for cid, c in sorted(cs.items()):
        rt = route(cid)
        top = rt["candidates"][0]["route"] if rt["candidates"] else "-"
        print("  %s d%-2d %-28s n=%-4d resid=%-4d %s"
              % (cid, c["depth"], c["statement"][:28], rt["n_readings"],
                 rt["n_residuals"], top))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "spec":
        print(__doc__)
    elif cmd == "route" and len(sys.argv) > 2:
        print(json.dumps(route(sys.argv[2]), indent=2))
    elif cmd == "query" and len(sys.argv) > 2:
        print(json.dumps(next_query(sys.argv[2]), indent=2))
    elif cmd == "ledger":
        print(json.dumps(yield_rate(), indent=2))
    else:
        print("usage: field_claim_loop.py "
              "[status | spec | route CID | query CID | ledger]")
