#!/usr/bin/env python3
"""Runnable report: FCL-1..13. Stdlib only. Exits nonzero on failure.

Each block states what the shipped skeleton did, what it does now, and the
number that separates the two. Run it after any change to the router or the
gates -- the two statistical gates are calibrated, and calibration drifts.
"""
import math
import os
import random
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))

from field import field_claim_loop as F  # noqa: E402

FAILED = []


def check(cid, what, ok, detail):
    print("  %-8s %-4s %s" % (cid, "PASS" if ok else "FAIL", what))
    print("           %s" % detail)
    if not ok:
        FAILED.append(cid)


def _store():
    d = tempfile.mkdtemp()
    os.chdir(d)
    return d


def _break(n=40, p=0.34, anchor_dev=0.0, cov=None, seed=0):
    """Breaks drawn independently, NOT every k-th reading.

    A fixed stride is a periodic rider, and since FCL-11 uncensored the series
    the correlation branch sees it -- correctly. The first version of this
    fixture used `i % 3 == 0` and the router routed it to NOISE_AS_SIGNAL,
    which was the right answer to a question the fixture did not mean to ask.
    """
    rng = random.Random(seed)
    F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)
    for i in range(n):
        v = 2.0 + rng.random() if rng.random() < p else rng.gauss(0.5, 0.08)
        F.reading("piezo_trunk_n", v, anchor_dev=anchor_dev, covariates=cov,
                  ts="t%03d" % i)


def _rider(T, n=100, seed=5, noise=0.5):
    rng = random.Random(seed)
    ph = rng.random() * 6.283
    return [math.sin(2 * math.pi * i / T + ph) + rng.gauss(0, noise)
            for i in range(n)]


home = os.getcwd()
print(__doc__.strip())
print()
print("ROUTER")

d = _store()
_break(anchor_dev=0.0)
r = F.route("c001")
routes = [c["route"] for c in r["candidates"]]
check("FCL-1", "NOVEL is reachable with a stable anchor logged",
      routes == ["NOVEL"],
      "%d residuals, anchor 0.0 throughout -> %s "
      "(skeleton: [INSTRUMENT 0.0], NOVEL absent)" % (r["n_residuals"], routes))
q = F.next_query("c001")
check("FCL-1b", "and it emits the experiment that route implies",
      "spawn child claim" in q["action"],
      "action = %r" % q["action"])
os.chdir(home)
shutil.rmtree(d, ignore_errors=True)

d = _store()
_break(anchor_dev=0.4)
top = F.route("c001")["candidates"][0]
check("FCL-2", "anchor_dev is a deviation against an explicit tolerance",
      top["route"] == "INSTRUMENT" and top["weight"] == 1.0,
      "dev 0.4 vs tol %g -> %s w=%.2f; the same field fed a raw 1004 hPa "
      "reading made INSTRUMENT win every claim forever"
      % (F.ANCHOR_TOL, top["route"], top["weight"]))
quiet = [c["route"] for c in F.route("c001", anchor_tol=1.0)["candidates"]]
check("FCL-2b", "and the tolerance actually gates it",
      "INSTRUMENT" not in quiet, "tol=1.0 -> %s" % quiet)
os.chdir(home)
shutil.rmtree(d, ignore_errors=True)

print()
print("GATES  (each calibrated against its own null)")

rng = random.Random(11)
old8 = sum(1 for _ in range(2000)
           if abs(F._autocorr([rng.gauss(0, 1) for _ in range(8)], 3)) > 0.35)
rates = []
for n in (20, 40, 100):
    rng = random.Random(11)
    f = sum(1 for _ in range(2000)
            if F.autocorr_scan([rng.gauss(0, 1) for _ in range(n)]
                               )["status"] == "STRUCTURED")
    rates.append((n, 100.0 * f / 2000))
check("FCL-3", "NOISE_AS_SIGNAL has a sample floor and a scaled band",
      all(p < 8.0 for _, p in rates),
      "white-noise false alarm now %s; skeleton at n=8 fired %.1f%%"
      % (", ".join("n=%d %.1f%%" % t for t in rates), 100.0 * old8 / 2000))

blind = [T for T in (4, 10, 12, 14, 16)
         if sum(1 for s in range(60)
                if abs(F._autocorr(_rider(T, seed=s), 3)) > 0.35) < 5]
found = [T for T in (4, 10, 12, 14, 16)
         if sum(1 for s in range(60)
                if F.autocorr_scan(_rider(T, seed=s))["status"] == "STRUCTURED")
         > 55]
check("FCL-4", "a lag scan sees the rider periods a fixed lag cannot",
      set(blind) == {4, 10, 12, 14, 16} and set(found) == set(blind),
      "rho(lag)=cos(2*pi*lag/T); at lag 3 periods %s give ~0%% detection, "
      "scan gives >92%% on all of them" % blind)


def null_rate(n_read, n_lev, p, trials=400, seed=7, old=False):
    rng = random.Random(seed)
    fires = 0
    for _ in range(trials):
        rs = [{"covariates": {"phase": rng.randrange(n_lev)}}
              for _ in range(n_read)]
        hit = {i for i in range(n_read) if rng.random() < p}
        if old:
            base = len(hit) / float(n_read)
            bins = {}
            for i, rr in enumerate(rs):
                k = rr["covariates"]["phase"]
                t, h = bins.get(k, (0, 0))
                bins[k] = (t + 1, h + (1 if i in hit else 0))
            if any(t >= 8 and h / float(t) > base * 1.5
                   for t, h in bins.values()):
                fires += 1
        elif F.covariate_concentration(hit, rs):
            fires += 1
    return 100.0 * fires / trials


cases = ((40, 4, 0.3), (200, 8, 0.3), (200, 4, 0.1))
new = [(c, null_rate(*c)) for c in cases]
old = [(c, null_rate(*c, old=True)) for c in cases]
check("FCL-5", "MISSING_VARIABLE is a corrected binomial tail, not 1.5x base",
      all(p <= 5.0 for _, p in new),
      "null now %s | shipped rule %s"
      % (", ".join("%.1f%%" % p for _, p in new),
         ", ".join("%.1f%%" % p for _, p in old)))

rng = random.Random(9)
rs, hit = [], set()
for i in range(200):
    rain = 1 if i % 4 == 0 else 0
    rs.append({"covariates": {"rain": rain}})
    if rng.random() < (0.9 if rain else 0.05):
        hit.add(i)
out = F.covariate_concentration(hit, rs)
check("FCL-5b", "and it still finds a real concentration",
      bool(out) and out[0]["covariate"] == "rain",
      "rain=1 -> %s" % (out[0] if out else None))

dup = ([{"covariates": {"phase": "dusk"}, "value": 1.0}] * 10
       + [{"covariates": {"phase": "dawn"}, "value": 9.0}] * 10)
check("FCL-6", "residual membership is by index, not dict equality",
      F.covariate_concentration({0}, dup) == [],
      "20 duplicate readings, 1 real residual -> [] "
      "(skeleton: rate 1.00 under phase=dusk vs base 0.05)")

print()
print("LOOP DISCIPLINE")

d = _store()
F.claim("piezo baseline", "piezo_trunk_n", 0.0, 1.0)
wider = tighter = None
try:
    F.deepen("c001", -1e9, 1e9)
except ValueError:
    wider = "refused"
tighter = F.deepen("c001", 0.2, 0.8)["depth"]
check("FCL-7", "deepen requires a tighter band or a named axis",
      wider == "refused" and tighter == 1,
      "[-1e9, 1e9] %s; [0.2, 0.8] accepted at depth %d" % (wider, tighter))
os.chdir(home)
shutil.rmtree(d, ignore_errors=True)

d = _store()
_break(anchor_dev=0.0)
over = F.next_query("c001", budget=0.5)      # before anything is pending
q1 = F.next_query("c001")
q2 = F.next_query("c001")
F.resolve_query(q1["id"], moved=False)
y = F.yield_rate()
check("FCL-8", "self-initiated actuation is metered, capped and credited",
      over.get("refused") == "budget" and q2.get("refused") == "duplicate"
      and F.spent() == F.QUERY_COST["NOVEL"] and y["rate"] == 0.0,
      "budget 0.5 vs cost %.1f -> refused %r (nothing charged); duplicate "
      "-> refused %r; spend %.1f/%.1f; curiosity yield %d/%d funded queries "
      "moved a claim"
      % (F.QUERY_COST["NOVEL"], over.get("refused"), q2.get("refused"),
         F.spent(), F.BUDGET, y["moved"], y["resolved"]))

try:
    F.reading("chem_soil_a", 0.5, shape=[0.1, 0.2, 0.45])
    scal = "accepted"
except ValueError:
    scal = "refused"
check("FCL-9", "a shape cannot be scalarized without naming the projection",
      scal == "refused",
      "shape without projection -> %s. PARTIAL: test() still compares the "
      "scalar, so every claim is a claim about one projection." % scal)

F.claim("a", "ch", 0, 1)
F.refresh("c001")
F.refresh("c002")
F.refresh("c002")
nxt = F.claim("c", "ch", 0, 1)["id"]
check("FCL-10", "claim ids come from live ids, not the log line count",
      nxt == "c003",
      "after 3 updates the next id is %s (skeleton: c001, c002, c004, c007; "
      "a compacted log would have collided)" % nxt)
os.chdir(home)
shutil.rmtree(d, ignore_errors=True)

d = _store()
ok = F.promote_channel("tide", _rider(8, 120, 1, 0.4), _rider(8, 120, 2, 0.4))
rng = random.Random(3)
ghost = F.promote_channel("ghost", _rider(8, 120, 1, 0.4),
                          [rng.gauss(0, 1) for _ in range(120)])
check("5b", "a demodulated channel needs the hold-out before promotion",
      ok["promoted"] and not ghost["promoted"],
      "real rider promoted (%s); noise hold-out refused (%s)"
      % (ok["reason"], ghost["reason"]))
os.chdir(home)
shutil.rmtree(d, ignore_errors=True)

print()
print("UNCENSORED SERIES, AND A CLOCK")

rng = random.Random(4)
vals = [0.5 + 0.9 * math.sin(2 * math.pi * i / 10.0) + rng.gauss(0, 0.05)
        for i in range(120)]
cens = [(v - 1.0 if v > 1.0 else v) for v in vals if v > 1.0 or v < 0.0]
unc = [v - 0.5 for v in vals]
a, b = F.autocorr_scan(cens), F.autocorr_scan(unc)
check("FCL-11", "the correlated series is uncensored",
      b["lag"] == 5 and a["lag"] != 5 and abs(b["rho"]) > abs(a["rho"]),
      "120 readings, band [0,1], rider of half-period 5: censored keeps %d "
      "and recovers lag %s (|rho| %.2f); uncensored keeps %d and recovers "
      "lag %s (|rho| %.2f). Censoring biased the answer, it did not hide it."
      % (len(cens), a["lag"], abs(a["rho"]), len(unc), b["lag"],
         abs(b["rho"])))

ts = [i * 2.5 for i in range(120)]
s = F.slotted_scan(ts, unc, n_perm=200, seed=0)
check("FCL-12", "lag is a duration when there is a clock",
      s["status"] == "STRUCTURED" and abs(s["lag_s"] - 12.5) < 1e-9,
      "regular 2.5 s clock, rider T=25 s -> rho %.2f at lag %.1f s (=T/2), "
      "p=%.4f, slot %.2f s, scanned range %.1f s"
      % (s["rho"], s["lag_s"], s["p"], s["slot_width"], s["lag_range_s"]))


def poisson(n, seed, rate=1.0):
    r = random.Random(seed)
    t, out = 0.0, []
    for _ in range(n):
        t += r.expovariate(rate)
        out.append(t)
    return out


fires = 0
for s2 in range(150):
    tt = poisson(80, s2)
    r2 = random.Random(1000 + s2)
    fires += F.slotted_scan(tt, [r2.gauss(0, 1) for _ in range(80)],
                            n_perm=100, seed=s2)["status"] == "STRUCTURED"
pw = []
for T in (3.0, 6.0, 12.0):
    h = 0
    for s2 in range(20):
        tt = poisson(80, s2)
        r2 = random.Random(2000 + s2)
        h += F.slotted_scan(tt, [math.sin(2 * math.pi * t / T)
                                 + r2.gauss(0, 0.5) for t in tt],
                            n_perm=100, seed=s2)["status"] == "STRUCTURED"
    pw.append((T, 100.0 * h / 20))
check("FCL-12b", "and it is calibrated on an irregular clock",
      fires / 150.0 < 0.10 and all(p == 100.0 for _, p in pw),
      "Poisson sampling: white values fire %.1f%% (alpha 5%%); riders %s"
      % (100.0 * fires / 150,
         ", ".join("T=%.0fs %.0f%%" % t for t in pw)))
check("FCL-12c", "and no period is claimed",
      s["period_s"] is None,
      "argmax lag is not a period -- a rider peaks at every multiple of T/2, "
      "and on a Poisson clock the argmax ran to a median 8.8 s against a true "
      "T/2 of 3.0 s. %s." % s["period_note"])

one = [0.001, 0.4, 0.6, 0.9]
many = [0.008, 0.012, 0.02, 0.9]
check("FCL-13", "multiplicity correction is BH, and the gain is stated small",
      F.bh_reject(one, 0.05, "bh")[0] == F.bh_reject(one, 0.05,
                                                     "bonferroni")[0]
      and len(F.bh_reject(many, 0.05, "bh")[0])
      > len(F.bh_reject(many, 0.05, "bonferroni")[0]),
      "at rank 1 BH IS Bonferroni, so with one true effect they are identical "
      "(85.2% recovery each); BH gains +4.6 pts at two true effects, +1.8 at "
      "three, +0.6 at four. Right error target, small gain, never worse.")

print()
print("OPEN, not papered over:")
print("  5a  what the physical anchor standard IS. The mechanism is built;")
print("      the reference whose failure mode differs from the sensors' is")
print("      not specified and was not invented here.")
print("  5e  the conservation ledger. The spend ledger counts query cost,")
print("      which is not the reservoir. Units unstated, so not guessed at.")
print("  --  a rider whose period exceeds the scanned lag range is invisible.")
print("      lag_range_s is reported so WHITE cannot quietly mean 'white")
print("      inside a window nobody named', but nothing widens it.")
print()

if FAILED:
    print("FAILED: %s" % ", ".join(FAILED))
    sys.exit(1)
print("all checks passed")
