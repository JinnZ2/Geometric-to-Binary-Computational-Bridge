# contrast_harness.py — CC0
# Same seed → two forecasters. Narrative NARROWS forward (false confidence,
# ignores regime scope). Physics WIDENS forward (honest, flags expired regime).
# Output: a single divergence number = how far narrative drifts from honesty.
# Pairs with forward_predict.py / constraint_playground.py.

from __future__ import annotations
from dataclasses import dataclass, field
from math import inf

@dataclass
class Interval:
    lo: float = -inf
    hi: float = inf
    def known(self): return self.lo > -inf and self.hi < inf
    def width(self): return self.hi - self.lo if self.known() else inf
    def widen(self, e):  return Interval(self.lo - e, self.hi + e)
    def shrink(self, f):                      # narrative move: pull toward the midpoint
        if not self.known(): return self
        m = (self.lo + self.hi)/2
        return Interval(m - (m-self.lo)*f, m + (self.hi-m)*f)
    def __repr__(self):
        a = "∅" if self.lo==-inf else f"{self.lo:g}"
        b = "∅" if self.hi== inf else f"{self.hi:g}"
        return f"[{a},{b}]"

@dataclass
class Coupling:
    src: str; dst: str; k: float
    valid_lo: float = -inf; valid_hi: float = inf; noise: float = 0.0
    def in_regime(self, iv):
        if not iv.known(): return True
        return iv.lo >= self.valid_lo and iv.hi <= self.valid_hi
    def push(self, iv):
        v = [self.k*iv.lo, self.k*iv.hi]
        return Interval(min(v), max(v))

def _merge(a, b):
    if not a.known(): return b
    if not b.known(): return a
    return Interval(min(a.lo, b.lo), max(a.hi, b.hi))

class State(dict):
    def get_iv(self, v): return self.get(v, Interval())
    def clone(self):     return State({k: Interval(i.lo, i.hi) for k,i in self.items()})


def physics_step(s, cpl, t, log):
    nxt = s.clone()
    for c in cpl:
        src = s.get_iv(c.src)
        if not c.in_regime(src):
            log.append((t, f"⚠ {c.src}→{c.dst}: {src} outside fit-scope "
                           f"[{c.valid_lo:g},{c.valid_hi:g}]"))
        contrib = c.push(src).widen(c.noise)       # honest: uncertainty GROWS
        nxt[c.dst] = _merge(nxt.get_iv(c.dst), contrib)
    return nxt

def narrative_step(s, cpl, t, log):
    nxt = s.clone()
    for c in cpl:
        src = s.get_iv(c.src)
        # narrative ignores regime scope entirely — authority assumed valid forever
        contrib = c.push(src).shrink(0.85)         # false: tightens toward a clean story
        nxt[c.dst] = _merge(nxt.get_iv(c.dst), contrib)
    return nxt

def run(stepper, seed, cpl, steps):
    s, hist, log = seed.clone(), [], []
    for t in range(1, steps+1):
        s = stepper(s, cpl, t, log); hist.append((t, s))
    return hist, log

def divergence(seed, cpl, steps, track):
    ph,_ = run(physics_step,   seed, cpl, steps)
    nh,plog = run(narrative_step, seed, cpl, steps)
    # divergence = how much narrower narrative claims to be than physics, per step
    rows, total = [], 0.0
    for (t, ps), (_, ns) in zip(ph, nh):
        pw, nw = ps.get_iv(track).width(), ns.get_iv(track).width()
        if pw == inf or nw == inf:
            rows.append((t, ps.get_iv(track), ns.get_iv(track), None)); continue
        gap = pw - nw                              # >0 = narrative overclaims confidence
        total += max(gap, 0); rows.append((t, ps.get_iv(track), ns.get_iv(track), gap))
    return rows, total, plog


if __name__ == "__main__":
    world = [
        Coupling("water_level","road_risk",   0.8, noise=0.4),
        Coupling("temp",       "beaver_repro", 1.5, valid_lo=-40, valid_hi=10, noise=0.3),
        Coupling("beaver_repro","water_level", 0.6, noise=0.5),
    ]
    seed = State({
        "temp":         Interval(15, 25),   # warm — past the beaver coupling's fit-scope
        "water_level":  Interval(2, 4),
        "road_risk":    Interval(2, 3),
        "beaver_repro": Interval(1, 2),
    })
    rows, total, plog = divergence(seed, world, 5, track="road_risk")
    print("  t   physics road_risk     narrative road_risk    overclaim")
    for t, p, n, g in rows:
        g = "—" if g is None else f"{g:+.2f}"
        print(f"  {t}   {str(p):<20} {str(n):<20} {g}")
    print(f"\nFALSE-CONFIDENCE INDEX (Σ overclaim) = {total:.2f}")
    print("higher = narrative model claims more certainty than the physics supports\n")
    print("regime alarms physics raised that narrative ignored:")
    print("\n".join(f"  {t}s: {m}" for t,m in plog) or "  none")
