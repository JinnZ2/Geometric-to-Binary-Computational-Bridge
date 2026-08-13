# geometric_intelligence.network

Geometric network analysis with φ scaling. Stdlib only, CC0.

Directed graphs whose edges carry a numeric relation between node values;
measurement checking against those relations; φ-band spectrum analysis; a
bridge into the fabrication claim ledger. The generated claim table for this
folder is `../CLAIMS.md`.

## Status

Complete. It arrived in two drops — `integrity.py`, `resonance.py`,
`__init__.py` and the two documents first; `core.py`, `bridge.py`,
`examples/demo.py` and `tests/` second. Every file runs, every file is as
supplied except where noted.

| File | State |
|---|---|
| `core.py` | as supplied. GI-8 (positive), GI-11..16 |
| `integrity.py` | as supplied. GI-1..6 |
| `resonance.py` | as supplied except one corrected comment. GR-1..6 |
| `bridge.py` | as supplied. GB-1..5 |
| `examples/demo.py` | as supplied, imports repointed at the subpackage |
| `tests/test_geometric_intelligence.py` | the drop's 20 tests, all passing |

**The interim `core.py` is gone.** While the real one was missing, this
directory carried a reconstruction built from what `integrity.py` and
`resonance.py` actually call. Scoring that reconstruction against the real
file is worth recording, because guessing a contract is a method:

- **Right:** every attribute and method the callers touch, and `scale` /
  `offset` semantics — the timber-frame numbers reproduced exactly.
- **Wrong in a way that mattered:** it *raised* `ZeroDivisionError` on a
  zero-factor inverse. The real one returns `float('inf')`, and
  `integrity.reconstruct()` guards on the exception — so the reconstruction
  was safer than the original and hid GI-14. Guessing the sensible behaviour
  is exactly how you miss a bug.
- **Wrong harmlessly:** the edge field is `rel_type`, not `kind`; `rotate` is
  a real relation, not one to reject; `add_edge` auto-creates missing nodes
  rather than raising.
- **Correctly refused:** `audit()` and `correct()` raised `NotImplementedError`
  rather than acquire a plausible body. Both turned out to have defects a
  guess would not have reproduced — GI-11 and GI-13.

## Read this before trusting an output

One positive result first, because the rest are not: **`audit()` survives the
null harness.** Randomising every edge factor — destroying the geometry while
leaving the graph and the weights intact — drops `integrity_score` from 2.000
to a mean of **0.014** over 200 draws. The score is responding to the geometry.

Then, in the order that matters:

- **`audit()` probes each cycle at exactly one point** (GI-11). Closure error
  is `|a·1 + b − 1|` for the cycle's affine map `x → ax + b`, so any map with
  `a + b = 1` passes without being the identity. A cycle of
  `compose(2, −1)` reports closure error **0.000000** and counts CONSISTENT
  while returning 19 for an input of 10. Pure-`scale` cycles have `b = 0` and
  are safe, which is why nothing in the drop's own demos or tests sees it.
- **`IntegrityMonitor` predictions do not use your measurements** (GI-1). A
  prediction is the design value propagated along a path. `full_report()`
  reports `predictions_use_measurements: False`.
- **`correct()` reaches consistency without restoring the right value**
  (GI-13). The demo's injected +23.6 % defect ends as +11.9 % on one edge and
  −9.5 % on its inverse partner, and `audit()` then reports 5/5 consistent.
  The error is split until the product closes, not removed.
- **`integrity_score` is part geometry and part declaration** (GI-12). It is
  `base_score × (1 + mean_edge_weight)`, and `weight` is author-set
  confidence that only ever *adds*: declaring every edge weight 0.0 still
  scores 1.0000. Randomising weights alone spans 1.23–1.72 with the geometry
  untouched.
- **Two modules emit `integrity_score` with different ranges** and compare
  both to `INTEGRITY_THRESHOLD` (GI-2, GI-12). `core.audit()` reaches 2.0;
  `integrity.full_report()` is bounded by 1.0; the constant is 3.618 and
  neither reaches it.
- **`detect_injection` flags 15.7 % of bins on pure noise** (GR-5).
  `injection_score` is not a rate until it has a null and a multiplicity
  correction.
- **`MultiScaleResonance` drops everything above 15 127 Hz** with the default
  `f_max=10000`, and its top band is empty by construction (GR-1).
- **An acyclic design writes an integrity claim of zero** (GB-2), and
  `verify_edge_measurement` divides by the predicted value (GB-1), so that
  claim is the one it crashes on.

```bash
python geometric_intelligence/falsifiers_gi_network.py   # 25 checks, exits nonzero
```

## Import path

```python
from geometric_intelligence.network import GeometricNetwork, IntegrityMonitor, PHI
```

Not `from geometric_intelligence import ...`. The parent directory already
holds twelve modules with 127 tests behind them and an empty `__init__.py` on
purpose; giving it a body that imports `.core` would make all of those depend
on this package loading. See the subpackage docstring.

## Quick start

```python
from geometric_intelligence.network import GeometricNetwork, IntegrityMonitor, PHI

net = GeometricNetwork()
for i in range(6):
    net.add_node(f"chamber_{i}", value=PHI ** i)
for i in range(5):
    net.add_edge(f"chamber_{i}", f"chamber_{i+1}", "scale", factor=PHI)
    net.add_edge(f"chamber_{i+1}", f"chamber_{i}", "scale", factor=1 / PHI)

print(net.audit()["integrity_score"])          # 1.9636 on this network

monitor = IntegrityMonitor(net)
monitor.add_measurement("chamber_0", 1.01)
monitor.add_measurement("chamber_1", 1.62)
report = monitor.full_report()
```

Edges in both directions is not decoration. A node nothing points at cannot be
predicted and is reported untrusted whatever its measurement (GI-6), and a
network with no cycles has nothing to be consistent about, so it audits at
0.0 and writes a zero-valued ledger claim (GB-2).

## Files

| File | Purpose |
|---|---|
| `core.py` | `GeometricNetwork`, `GeoNode`, `GeoEdge`, cycle finding, `audit`, `correct` |
| `integrity.py` | `IntegrityMonitor` — measurement checking, reconstruction |
| `resonance.py` | `MultiScaleResonance` — φ-band analysis, injection detection |
| `bridge.py` | `network_to_claims`, `append_geo_claims`, `verify_edge_measurement` |
| `examples/demo.py` | the drop's five demos; three of its printouts are findings |
| `tests/test_geometric_intelligence.py` | the drop's 20 tests |
| `FIELD_GUIDE.md` | Cold-workshop operating procedures |
| `../falsifiers_gi_network.py` | Runnable GI / GR / GB report |

## Constants

| Constant | Value | Where it is actually used |
|---|---|---|
| `PHI` | 1.6180339887 | Edge factors, band ratios |
| `PHI_INV` | 0.6180339887 | Reverse edges |
| `PHI_INV_9` | 0.0131556 | Cycle-closure tolerance and residual tolerance, 1.3 % |
| `INTEGRITY_THRESHOLD` | 3.6180340 | Compared against two different quantities, reached by neither |

`PHI_INV_9` also appears in `resonance.py` as `×10` (0.1316) and `×100`
(1.3156), and in `correct()` as the step size. Where it is multiplied, the
multiplier sets the scale and the φ constant contributes a factor between 1
and 2. Open problem GR-7.

## Running

```bash
python geometric_intelligence/falsifiers_gi_network.py            # GI / GR / GB
python tests/test_gi_network.py                                   # 102 cases
python -m unittest geometric_intelligence.network.tests.test_geometric_intelligence
python geometric_intelligence/network/examples/demo.py
python claims_index.py show GI-11                                 # one claim, every site
```

## License

CC0 — public domain.
