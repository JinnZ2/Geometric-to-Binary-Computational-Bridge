# forward_predict.py — CC0
# Companion to constraint_playground. Propagates a COUPLED system forward in time.
# Physics-first: unknowns widen honestly as they propagate (no false confidence).
# Couplings carry a VALIDITY SCOPE — the model flags when its own regime expired.
# This is the DNR agent made structural: authority frozen in a regime it left.

from __future__ import annotations
from dataclasses import dataclass, field
from math import inf

@dataclass
class Interval:
    lo: float = -inf
    hi: float = inf
    def known(self): return self.lo > -inf and self.hi < inf
    def width(self): return self.hi - self.lo
    def mid(self):   return (self.lo + self.hi)/2 if self.known() else None
    def widen(self, e): return Interval(self.lo - e, self.hi + e)   # honest uncertainty growth
    def __repr__(self):
        a = "∅" if self.lo==-inf else f"{self.lo:g}"
        b = "∅" if self.hi== inf else f"{self.hi:g}"
        return f"[{a},{b}]"

@dataclass
class Coupling:
    src: str; dst: str; k: float
    valid_lo: float = -inf       # regime scope: this k only holds while src ∈ [valid_lo, valid_hi]
    valid_hi: float =  inf
    noise: float = 0.0           # per-step uncertainty this coupling injects downstream
    def in_regime(self, iv):     # is the source still inside the regime this k was fit for?
        if not iv.known(): return True
        return iv.lo >= self.valid_lo and iv.hi <= self.valid_hi
    def push(self, iv):
        v = [self.k*iv.lo, self.k*iv.hi]
        return Interval(min(v), max(v)).widen(self.noise)

@dataclass
class State:
    vars: dict = field(default_factory=dict)
    def get(self, v): return self.vars.get(v, Interval())
    def copy(self):   return State({k: Interval(i.lo, i.hi) for k,i in self.vars.items()})

class Predictor:
    def __init__(self, couplings):
        self.cpl = couplings
        self.history, self.alarms = [], []

    def step(self, s, t):
        nxt = s.copy()
        for c in self.cpl:
            src = s.get(c.src)
            # ── LOAD-BEARING 1: regime check. Model flags when its own k expired. ──
            if not c.in_regime(src):
                self.alarms.append((t, f"⚠ {c.src}→{c.dst}: src={src} left scope "
                                       f"[{c.valid_lo:g},{c.valid_hi:g}] — coupling unreliable"))
            # ── LOAD-BEARING 2: physics-first propagation, unknowns widen forward ──
            contrib = c.push(src)
            cur = nxt.get(c.dst)
            nxt.vars[c.dst] = (cur.meet_or(contrib) if hasattr(cur,'meet_or')
                               else Interval(min(cur.lo, contrib.lo), max(cur.hi, contrib.hi)))
        return nxt

    def run(self, seed, steps):
        s = seed
        self.history = [(0, s)]
        for t in range(1, steps+1):
            s = self.step(s, t)
            self.history.append((t, s))
        return self.history


# ── demo: cascade run 5 steps forward. beaver coupling fit for COLD regime only. ──
if __name__ == "__main__":
    world = [
        Coupling("water_level", "road_risk",   0.8, noise=0.3),
        Coupling("temp",        "beaver_repro", 1.5, valid_lo=-40, valid_hi=10, noise=0.2),
        Coupling("beaver_repro","water_level",  0.6, noise=0.4),   # the feedback loop
    ]
    p = Predictor(world)
    seed = State({
        "temp":         Interval(15, 25),    # WARM — already past the regime the k was fit for
        "water_level":  Interval(2, 4),
        "road_risk":    Interval(),          # ∅ unknown — let it emerge
        "beaver_repro": Interval(),
    })
    for t, s in p.run(seed, 5):
        print(f"t={t}  " + "  ".join(f"{k}={s.get(k)}" for k in
              ["temp","beaver_repro","water_level","road_risk"]))
    print("\nregime alarms:")
    print("\n".join(f"  {t}s: {m}" for t,m in p.alarms) or "  none")
