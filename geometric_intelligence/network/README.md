# geometric_intelligence.network

Geometric network analysis with φ scaling. Stdlib only, CC0.

Directed graphs whose edges carry a numeric relation between node values;
measurement checking against those relations; φ-band spectrum analysis. The
generated claim table for this folder is `../CLAIMS.md`.

## Status

This arrived as a partial drop and is **not** a finished package. What runs and
what does not:

| | |
|---|---|
| `core.py` | runs. **Reconstructed** from what the other modules call — it was not in the drop. `audit()` and `correct()` raise `NotImplementedError` rather than guess. |
| `integrity.py` | runs, as supplied. Six recorded findings, GI-1..6. |
| `resonance.py` | runs, as supplied except one corrected comment. Six recorded findings, GR-1..6. |
| `bridge.py` | **absent.** `network_to_claims` / `append_geo_claims`. Open problem GI-10. |
| `tests/test_geometric_intelligence.py` | **absent.** The README cited 20 tests. `tests/test_gi_network.py` here tests the findings, not those behaviours. |
| `examples/demo.py` | **absent.** |

Read the audit header of each module before using its output. The short
version, in the order that matters:

- **`IntegrityMonitor` predictions do not use your measurements** (GI-1). A
  prediction is the design value propagated along a path. So it answers "is
  this part where the drawing says", not "given this part came out wrong, is
  the next one still compatible". `full_report()` reports
  `predictions_use_measurements: False` so this cannot be read the wrong way
  by accident.
- **`INTEGRITY_THRESHOLD` does nothing** (GI-2). `integrity` is a product of
  two fractions, so ≤ 1; the clause that tests it against 1.809 can never
  fire. `passes` is decided entirely by its first clause.
- **`detect_injection` flags 15.7 % of bins on pure noise** (GR-5). No noise
  model, no multiplicity correction. `injection_score` is not a rate.
- **`MultiScaleResonance` drops everything above 15 127 Hz** with the default
  `f_max=10000`, and its top band is empty by construction (GR-1).

`python geometric_intelligence/falsifiers_gi_network.py` runs all twelve and
exits nonzero if any stops holding.

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

monitor = IntegrityMonitor(net)
monitor.add_measurement("chamber_0", 1.01)
monitor.add_measurement("chamber_1", 1.62)
report = monitor.full_report()
```

Edges in both directions is not decoration: a node nothing points at cannot be
predicted, falls to the isolated-node branch, and is reported untrusted
whatever its measurement. The drop's own timber-frame example had forward
edges only and flagged `brace_short` untrusted on perfect measurements.

## Files

| File | Purpose |
|---|---|
| `core.py` | `GeometricNetwork`, `GeoNode`, `GeoEdge`, the four constants |
| `integrity.py` | `IntegrityMonitor` — measurement checking, reconstruction |
| `resonance.py` | `MultiScaleResonance` — φ-band analysis, injection detection |
| `FIELD_GUIDE.md` | Cold-workshop operating procedures |
| `../falsifiers_gi_network.py` | Runnable GI/GR report |

## Constants

| Constant | Value | Where it is actually used |
|---|---|---|
| `PHI` | 1.6180339887 | Edge factors, band ratios |
| `PHI_INV` | 0.6180339887 | Reverse edges |
| `PHI_INV_9` | 0.0131556 | Default residual tolerance, 1.3 % |
| `INTEGRITY_THRESHOLD` | 3.6180340 | Nowhere reachable — see GI-2 |

`PHI_INV_9` also appears in `resonance.py` as `×10` (0.1316) and `×100`
(1.3156). The multiplier sets the scale in both cases, so the φ constant is
not doing the work its name implies. Open problem GR-7.

## Running

```bash
python geometric_intelligence/falsifiers_gi_network.py   # GI-1..6, GR-1..6
python tests/test_gi_network.py                          # unit tests
python claims_index.py show GI-1                         # one claim, every site
```

## License

CC0 — public domain.
