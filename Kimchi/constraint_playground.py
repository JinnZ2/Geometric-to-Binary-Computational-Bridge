# constraint_playground.py — CC0
# Two parallel sensor streams. One observation SPLITS into both branches.
# Knowledge is created at the INTERSECTION — not by next-token prediction.
# Unknowns are first-class information, never failure.
# A metacognition layer narrates its own reasoning geometry before each act.

from __future__ import annotations
from dataclasses import dataclass, field
from math import inf

# ── symbol layer (compression over the mechanism) ───────────────
# ⟦v⟧ variable   ⟂ split   ⊂ tighten   ∩ reconverge   ✦ novel pin   ∅ unknown

@dataclass
class Interval:                       # a partial constraint: half-open = still unknown
    lo: float = -inf
    hi: float = inf
    def known(self):  return self.lo > -inf and self.hi < inf
    def width(self):  return self.hi - self.lo
    def meet(self, o):                # intersection of two partial constraints
        return Interval(max(self.lo, o.lo), min(self.hi, o.hi))
    def __repr__(self):
        a = "∅" if self.lo == -inf else f"{self.lo:g}"
        b = "∅" if self.hi ==  inf else f"{self.hi:g}"
        return f"[{a},{b}]"

@dataclass
class Coupling:                       # how one variable constrains another = the world model
    src: str; dst: str; k: float
    def push(self, iv):
        v = [self.k*iv.lo, self.k*iv.hi]
        return Interval(min(v), max(v))

@dataclass
class Branch:                         # a parallel path; holds its own partial world, no collapse
    name: str; frame: str
    vars: dict = field(default_factory=dict)
    def see(self, v, iv): self.vars[v] = self.get(v).meet(iv)
    def get(self, v):     return self.vars.get(v, Interval())

class Field:
    def __init__(self, couplings):
        self.cpl = couplings
        self.L = Branch("L", "ground/water")
        self.R = Branch("R", "road/thermal")
        self.shared = Branch("∩", "reconverged")
        self.trace, self.found = [], []

    def meta(self, m): self.trace.append(m)          # narrate BEFORE acting

    # ── MECHANISM 1: split — one observation informs BOTH branches at once ──
    def split(self, var, iv, to):
        self.meta(f"⟂ ⟦{var}⟧={iv}  →  " + " | ".join(f"{b}·{getattr(self,b).frame}" for b in to))
        for b in to: getattr(self, b).see(var, iv)

    def propagate(self, br):          # run the world model forward inside one frame
        moved = True
        while moved:
            moved = False
            for c in self.cpl:
                s = br.get(c.src)
                if s.known():
                    new = br.get(c.dst).meet(c.push(s))
                    if new.width() < br.get(c.dst).width():
                        br.vars[c.dst] = new; moved = True

    # ── MECHANISM 2: intersect — knowledge NEITHER branch held alone ──
    def intersect(self):
        self.meta("∩ reconverge L ∩ R  →  seek ✦")
        self.propagate(self.L); self.propagate(self.R)
        lk = {v: self.L.get(v).known() for v in self.L.vars}
        rk = {v: self.R.get(v).known() for v in self.R.vars}
        for v in sorted(set(self.L.vars) | set(self.R.vars)):
            self.shared.vars[v] = self.L.get(v).meet(self.R.get(v))
        self.propagate(self.shared)                  # downstream pins emerge here
        for v in sorted(self.shared.vars):
            iv = self.shared.get(v)
            if iv.known() and not lk.get(v) and not rk.get(v):
                self.found.append((v, iv))
                self.meta(f"  ✦ ⟦{v}⟧={iv}  (neither branch held this)")

    def unknowns(self):  return [v for v in self.shared.vars if not self.shared.get(v).known()]
    def score(self):     return len(self.found)      # reward = constraint DISCOVERED, not matched


# ── demo: your cascade. Each sensor reads only ONE SIDE of water_level. ──
if __name__ == "__main__":
    world = [
        Coupling("water_level", "road_risk",   0.8),
        Coupling("willow",      "beaver_food",  0.5),
        Coupling("beaver_food", "beaver_pop",   2.0),
        Coupling("temp_cold",   "feed_need",    0.1),
    ]
    f = Field(world)
    # ground sensor: "water no higher than 5" + sees willow      (one-sided on water)
    f.split("water_level", Interval(-inf, 5), ["L"])
    f.split("willow",      Interval(3, 5),    ["L"])
    # road sensor: "water at least 4" (washout onset) + temp      (other side on water)
    f.split("water_level", Interval(4, inf),  ["R"])
    f.split("temp_cold",   Interval(20, 30),  ["R"])

    f.intersect()

    print("\n".join(f.trace))
    print("\nshared:", {v: str(iv) for v, iv in f.shared.vars.items()})
    print("unknowns:", f.unknowns())
    print("discoveries:", [(v, str(iv)) for v, iv in f.found], "| score =", f.score())
