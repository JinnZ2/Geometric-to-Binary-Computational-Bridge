# Geometric Intelligence — Field Operations Guide

For workshops, fabrication sites, and remote locations where temperatures drop
below −20 °C, internet is intermittent or absent, parts are scarce and must be
verified before use, and phone batteries die.

> **Corrections applied to the version this replaces.** Two numbers in it were
> wrong and one worked example does not do what it says. All three are marked
> **[corrected]** below with the arithmetic, because a field guide is used
> away from anything that could check it.

---

## Philosophy (30 seconds)

A geometric network is a set of measurements that should relate to each other
in predictable ways. If they don't, something is wrong — wrong part, wrong
assembly, wrong temperature, or wrong assumption.

You don't need to understand φ. You need: *"these three lengths should be in
ratio 1 : 1.618 : 2.618, and if they're not I need to know why before I weld
them."*

---

## Before you start

### 1. Record temperature

Every geometric prediction is temperature-sensitive. Write down ambient
temperature and part temperature, separately — a part carried in from outside
is not at ambient for a long time.

**[corrected]** For acoustic work, the speed of sound is

```
c(T) ≈ 331.3 + 0.606·T          T in °C, c in m/s
```

which is within 0.1 % of the exact √(1 + T/273.15) form down to −20 °C, 0.3 %
at −40 °C, and 0.5 % at −50 °C.

| T | c (m/s) |
|---|---|
| +20 °C | 343.4 |
| +15 °C | 340.4 (the 343 m/s in the code is this, near enough) |
| −20 °C | 319.2 |
| −40 °C | 307.1 |

A prediction made at +20 °C and measured at −40 °C reads **10.6 % low**, not
6 %. 307.1 / 343.4 = 0.894. Frequency scales directly with `c`, so a 10.6 %
error swamps every tolerance band in the ledger — the acoustic verdicts are
±8 %.

`fabrication/pipe_modes.py` already takes `c=` on `pipe_modes`, `box_modes`,
`cylinder_modes` and `ka_check`. What is missing is a caller that computes `c`
from a recorded temperature and a verifier that passes it through; today the
default 343.0 is used everywhere.

### 2. Choose your verification tool

| What you have | Method | Accuracy | Notes |
|---|---|---|---|
| Phone + mic | Sweep + baseline | ±2 % | Battery dies fast in cold; keep it warm |
| Multimeter | Resistance, LCR | ±1 % | Low battery reads high resistance → false "fail" |
| Caliper / tape | Direct dimension | ±0.5 % | See contraction table below |
| Ear + experience | Tap test, pitch comparison | ±10 % | Reliable for go/no-go |
| Frequency counter | Oscillator + probe | ±0.1 % | Best for resonance |

### 3. Check the ledger

```bash
python -m fabrication.ledger summary
```

Look for verdict `drift` (inspect before it becomes `fail`), domains with no
recent measurements, and baselines older than one season.

**The ledger path is relative.** All 23 sites write `Path("CLAIM_TABLE.fab.json")`,
resolved against the current working directory — so running from `fabrication/`
and from the repo root writes to two different ledgers, and neither knows about
the other. Always run from the repo root, or fix the path first.

---

## Building a geometric network

### Example: timber frame joint

**[corrected]** — the version this replaces built the network with forward
edges only, and that example reports `brace_short` **untrusted even when every
brace is cut perfectly**. Nothing can predict the first node of a one-way
chain, so it falls to the isolated-node branch, which marks it untrusted
unconditionally. Add the reverse edges:

```python
from geometric_intelligence.network import GeometricNetwork, PHI

net = GeometricNetwork()
net.add_node("brace_short", value=0.600)          # 600 mm
net.add_node("brace_mid",   value=0.600 * PHI)    # 970.8 mm
net.add_node("brace_long",  value=0.600 * PHI**2) # 1570.8 mm

net.add_edge("brace_short", "brace_mid",  "scale", factor=PHI)
net.add_edge("brace_mid",   "brace_long", "scale", factor=PHI)
net.add_edge("brace_mid",   "brace_short", "scale", factor=1/PHI)   # <- required
net.add_edge("brace_long",  "brace_mid",   "scale", factor=1/PHI)   # <- required
```

Do **not** also add a direct `brace_short → brace_long` edge at `PHI**2`
"for completeness". Two routes to the same node is exactly the case where
`check()` keeps whichever route agrees best with the measurement (GI-3), and
it will report a contradiction as `trusted`.

`net.audit()` raises `NotImplementedError` — it was named in the drop's README
and never supplied. Until it exists there is no integrity score for a design,
only for measurements against one.

### Example: verifying cut parts

```python
from geometric_intelligence.network import IntegrityMonitor

monitor = IntegrityMonitor(net)
monitor.add_measurement("brace_short", 0.598)
monitor.add_measurement("brace_mid",   0.965)
monitor.add_measurement("brace_long",  1.580)

report = monitor.full_report()
```

**Read `predictions_use_measurements` in the report before you read anything
else.** While it is `False` (which is today), a prediction for a node is the
*design* value propagated to it, not anything derived from what you measured
elsewhere. A brace cut 200 mm short still predicts its neighbour at 970.8 mm.
So this tells you "is this part where the drawing says", part by part — it does
**not** tell you "given that this brace came out short, is the next one still
compatible". That second question is the one the module reads as if it answers,
and GI-1 is why it doesn't.

If a measurement is flagged untrusted: re-measure with a different tool; check
temperature; check tool zero; and only then remake the part.

---

## Cold-weather specifics

### Material contraction

**[corrected]** — the version this replaces gave percentages with no reference
temperature, and back-solving them showed three different references (+15, +10
and 0 °C) across five rows. All rows below are **from +15 °C**, and the wood
rows carry the caveat that matters more than the numbers.

| Material | α (per °C) | Δ from +15 °C to −40 °C |
|---|---|---|
| Steel | 12 × 10⁻⁶ | −0.066 % |
| Aluminium | 23 × 10⁻⁶ | −0.127 % |
| Concrete | 10 × 10⁻⁶ | −0.055 % |
| Wood, parallel to grain | 3–5 × 10⁻⁶ | −0.017 % to −0.028 % |
| Wood, perpendicular | 25–60 × 10⁻⁶ | −0.14 % to −0.33 % |

**For timber, thermal contraction is the small term and quoting it alone is
misleading.** Wood moves 2–8 % across the grain with moisture content, one to
two orders more than the −0.3 % thermal figure, and a cold shop is a dry shop:
equilibrium moisture content falls as the air is heated, and the timber keeps
shrinking for weeks after it comes indoors. If a brace is out of tolerance
across the grain, moisture is the first thing to check, not temperature. The
φ-ratio check above is a *ratio* between three braces of the same stock, so a
uniform moisture change largely cancels — which is a real advantage of ratio
checks and worth knowing.

For precision fits tighter than 0.5 %, measure at operating temperature.

### Phone / mic limits at −40 °C

- Lithium battery: 30–50 % capacity loss. Inner pocket; warm external pack.
- Speaker cone stiffens, resonance shifts up ~5–10 %. Use a baseline captured
  at a similar temperature — this is why baselines carry a season.
- Touchscreen may not respond through gloves.
- Condensation on the way back indoors. Seal in a bag first.

### When the phone dies

```bash
python -m fabrication.mini      # → 4 (emit) → loom
```

The loom emitter produces an ASCII topology grid you can print or sketch and
build by hand, then verify with a multimeter and your ear. It is the only path
in the toolchain that needs no working electronics to execute.

---

## Anomaly detection without a spectrum analyser

1. **Tap test.** One clear pitch = one dominant mode. Multiple pitches or a
   rattle = loose joint, crack, or internal void.
2. **Thermal cycling.** Warm the part gently and listen; cracks open and close
   with temperature and change the signature.
3. **Load test.** Known load, measure deflection, compare to prediction. 2×
   predicted deflection means crack, delamination, or wrong material.

If you *do* have a spectrum, `MultiScaleResonance` will bin it — but read
GR-1 and GR-5 in `resonance.py` first. Its top band is dead, components above
15 127 Hz are dropped silently, and `detect_injection` flags **15.7 % of bins
on pure noise**, so `injection_score` cannot be read as a rate until it is
calibrated against a null.

---

## Emergency: reconstruction from surviving measurements

**[corrected]** — the version this replaces said "if you lose a measurement,
call `reconstruct()`". From **one** surviving measurement it returns `{}`: a
lone measured node has no other measured node to check it, so it is marked
untrusted, and reconstruction seeds only from trusted nodes.

You need **two** surviving measurements that agree with each other. Then:

```python
recon = monitor.reconstruct()
```

The result is an estimate, not a measurement. Where two routes reach the same
node, the value you get is decided by the order the edges were added, not by
any averaging (GI-4) — so if the network has redundant paths, do not treat a
reconstructed value as better than a single-path guess.

---

## Weekly maintenance

1. `python -m fabrication.smoke`
2. `python -m fabrication.ledger summary` — from the repo root
3. Recapture baselines if temperature moved more than 20 °C since the last one
4. Archive old measurement logs

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Everything "fail" | Temperature uncompensated | Record T, apply c(T); 10.6 % at −40 °C |
| Everything "drift" | Tool calibration | Check zero, battery, reference standard |
| One node always untrusted | No edge points at it | Add the reverse edge — see the timber example |
| `reconstruct()` returns `{}` | Only one measurement | Needs two that agree |
| Two ledgers with different contents | Relative `CLAIM_TABLE.fab.json` | Always run from the repo root |
| `audit()` raises NotImplementedError | It was never supplied | Open problem GI-8 |
| FFT takes minutes | Pure-Python radix-2 on a long file | Shorten the sample, or install numpy |

---

## One-pager

```
□ Record ambient temperature AND part temperature
□ Verify tool battery / calibration
□ Run from the repo root: python -m fabrication.ledger summary
□ Build the network with edges in BOTH directions
□ Measure → predict → compare → decide
□ Check predictions_use_measurements before reading a verdict
□ If drift: inspect, don't ignore
□ If fail: check temperature first, then tool, then the part
□ Log every measurement: timestamp, temp, tool, operator
□ When in doubt: rebuild from loom ASCII, verify by hand
```

## License

CC0 — use, modify, teach, sell, give away. No attribution required.
