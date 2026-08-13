"""
trend.py -- drift detection over a fabrication measurement log.

    python geometric_intelligence/network/trend.py

Reads `CLAIM_TABLE.fab.measurements.json`, groups by scope, fits a line
against time, and classifies each scope as failed / accelerating / drifting /
noisy / stable. The question it exists to answer is the one the ledger cannot:
"is this parameter walking toward its band edge", not "is it inside the band
today".

=====================================================================
AUDIT
=====================================================================
Behaviour is UNCHANGED from the file as supplied. Run on the shipped
20-point fixture it produces a report whose headline is wrong in a specific
way, and that is the fastest way to see what is broken:

    [FAIL ] fab::thermal::test::delta_T        failed   R2=1.000  fail_in=N/A
    [FAIL ] fab::mechanical::test::resonance   failed   R2=1.000  fail_in=N/A
    [OK   ] fab::electrical::test::R0          noisy    R2=0.294  fail_in=1950.8d

The two channels that are actually drifting report **no** time to failure,
and the only failure prediction in the report belongs to the **stable** one,
extrapolated 1950.8 days out of a fit explaining 29 % of its variance.

TRD-1  The fail band is one-sided.
       `fail_threshold = predicted * (1 + 2*tol_frac)` -- an upper edge only.
       A resistor drifting DOWN from 10.0 to 0.5 against a claim of
       10.0 +/- 5 % is 95 % below its band and is never classified `failed`;
       it is reported `drifting` with `days_to_fail = None`. Measured.

TRD-2  The negative-slope branch answers a different question.
       `elif slope < 0 and current > fail_threshold: days_to_fail =
       (current - fail_threshold) / abs(slope)`. If `current` is already above
       the threshold the claim has already failed, so this is days until it
       comes back INSIDE the band -- reported in the field named
       `predicted_fail_days`. Measured: a value falling from 30.0 against a
       claim of 10.0 reports "fails in 10.0 days" while failing throughout.

TRD-3  No minimum-sample gate, so two points always look like a trend.
       With n = 2 the residual sum of squares is exactly zero, so R^2 = 1.0
       for any pair of points, and the `r2 > 0.5` and `r2 > 0.7` branches
       fire. Two readings 0.0001 apart classify as `drifting`; two readings
       0.5 apart on a 200 Hz claim classify as `failed`. This is the FCL-3/4
       shape: a threshold with no sample-count guard, on a series whose
       normal length is short.

TRD-4  `abs(slope) < 1e-6` for "stable" compares quantities of different
       dimension against one constant. `slope` is measured-units per day, so
       the same 1e-5/day is 0.036 % of a 10 ohm claim per year, 0.0005 % of an
       800 Hz claim, and 365 % of a 0.001-unit claim. A relative slope --
       `slope / predicted` -- is dimensionless and would compare.

TRD-5  `cross_domain_correlation` has no null, and its gate is a statement
       about time rather than about physics.
       Any two monotone drifts correlate at |r| ~ 1 whatever their cause. On
       the fixture, thermal and mechanical -- two straight ramps -- give
       **r = 1.0000** exactly. The gate is `abs(corr) > 0.6` with no
       permutation null and no correction over the pairs tested. The same
       repair the field loop needed for FCL-5: detrend, or shuffle one series
       against the other and count.

TRD-6  It also cannot see the pair it would fire on.
       Overlap is computed as `set(ta.keys()) & set(tb.keys())` over raw
       float timestamps, so two channels sampled a millisecond apart share no
       points and the function returns nothing. And the defaults are
       `domain_a="electrical", domain_b="thermal"` -- on the shipped fixture
       the only correlated pair is thermal x mechanical, which the defaults
       never compare. Both measured.

TRD-7  `LEDGER` is a relative path, like the 24 sites in `bridge.py` and
       `fabrication/`. Same consequence: the log read depends on the working
       directory. GB-5, open problem GI-10.

Two smaller ones, recorded because they are one line each: the exported
`"generated"` field is the LEDGER's mtime rather than the report's time, and
`print_trend_report` renders a `predicted_fail_days` of 0.0 as "N/A" because
the test is truthiness -- so "fails today" and "no prediction" print the same.

What is right and is the point of the file: the regression itself, the
grouping by scope, and the severity ordering. Fitting a line against time and
asking where it crosses the band is the correct question, and nothing else in
this repository asks it.

License: CC0. Stdlib only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

LEDGER = Path("CLAIM_TABLE.fab.measurements.json")  # TRD-7: relative


@dataclass
class TrendResult:
    scope: str
    n_points: int
    slope_per_day: float      # change per day
    r_squared: float          # goodness of fit
    current_value: float
    predicted_fail_days: Optional[float]  # days until predicted fail
    verdict_trend: str        # "stable", "drifting", "accelerating", "failed"


def _linear_regression(x: List[float], y: List[float]) -> Tuple[float, float, float]:
    """
    Simple linear regression: y = slope * x + intercept.
    Returns (slope, intercept, r_squared).
    """
    n = len(x)
    if n < 2:
        return 0.0, 0.0, 0.0

    mx = sum(x) / n
    my = sum(y) / n

    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = sum((xi - mx) ** 2 for xi in x)

    if den == 0:
        return 0.0, my, 0.0

    slope = num / den
    intercept = my - slope * mx

    # R-squared
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    ss_tot = sum((yi - my) ** 2 for yi in y)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return slope, intercept, r2


def _seconds_to_days(ts: float) -> float:
    return ts / 86400.0


def load_measurements(path: Path = LEDGER) -> List[Dict]:
    """Load measurement log."""
    if not path.exists():
        return []
    return json.loads(path.read_text())


def group_by_scope(measurements: List[Dict]) -> Dict[str, List[Dict]]:
    """Group measurements by scope."""
    groups = {}
    for m in measurements:
        scope = m.get("scope", "unknown")
        groups.setdefault(scope, []).append(m)
    return groups


def analyze_scope_trend(scope: str, entries: List[Dict],
                         fail_threshold: Optional[float] = None) -> TrendResult:
    """
    Analyze trend for a single scope.

    entries: list of measurement dicts with 'ts', 'measured', 'predicted', 'verdict'
    fail_threshold: if None, derived from last entry's predicted + tol_frac
    """
    # Sort by timestamp
    entries = sorted(entries, key=lambda e: e.get("ts", 0))

    if len(entries) < 2:
        return TrendResult(
            scope=scope,
            n_points=len(entries),
            slope_per_day=0.0,
            r_squared=0.0,
            current_value=entries[-1].get("measured", 0.0) if entries else 0.0,
            predicted_fail_days=None,
            verdict_trend="insufficient_data"
        )

    # Extract time series
    times = [_seconds_to_days(e.get("ts", 0)) for e in entries]
    values = [e.get("measured", 0.0) for e in entries]

    # Normalize times to start at 0
    t0 = times[0]
    times = [t - t0 for t in times]

    slope, intercept, r2 = _linear_regression(times, values)

    # Determine fail threshold
    if fail_threshold is None:
        last = entries[-1]
        pred = last.get("predicted", 0.0)
        tol = last.get("tol_frac", 0.05)
        fail_threshold = pred * (1.0 + 2.0 * tol)  # fail band upper edge

    current = values[-1]

    # Predict failure
    if slope > 0 and current < fail_threshold:
        days_to_fail = (fail_threshold - current) / slope
    elif slope < 0 and current > fail_threshold:
        days_to_fail = (current - fail_threshold) / abs(slope)
    else:
        days_to_fail = None

    # Classify trend
    if current > fail_threshold:
        verdict = "failed"
    elif abs(slope) < 1e-6:
        verdict = "stable"
    elif r2 > 0.7 and days_to_fail is not None and days_to_fail < 30:
        verdict = "accelerating"
    elif r2 > 0.5:
        verdict = "drifting"
    else:
        verdict = "noisy"

    return TrendResult(
        scope=scope,
        n_points=len(entries),
        slope_per_day=slope,
        r_squared=r2,
        current_value=current,
        predicted_fail_days=days_to_fail,
        verdict_trend=verdict
    )


def detect_all_trends(path: Path = LEDGER) -> Dict[str, TrendResult]:
    """
    Analyze trends for all scopes in the measurement log.
    """
    measurements = load_measurements(path)
    groups = group_by_scope(measurements)

    results = {}
    for scope, entries in groups.items():
        results[scope] = analyze_scope_trend(scope, entries)

    return results


def cross_domain_correlation(path: Path = LEDGER,
                              domain_a: str = "electrical",
                              domain_b: str = "thermal") -> List[Dict]:
    """
    Find scopes in different domains that may be correlated.

    Returns list of potential correlations where trends move
    together (same direction, similar timing).
    """
    measurements = load_measurements(path)
    groups = group_by_scope(measurements)

    # Filter by domain prefix
    a_scopes = {s: e for s, e in groups.items() 
                if s.startswith(f"fab::{domain_a}::")}
    b_scopes = {s: e for s, e in groups.items() 
                if s.startswith(f"fab::{domain_b}::")}

    correlations = []

    for sa, ea in a_scopes.items():
        for sb, eb in b_scopes.items():
            # Find overlapping time windows
            ta = {e.get("ts", 0): e.get("measured", 0.0) for e in ea}
            tb = {e.get("ts", 0): e.get("measured", 0.0) for e in eb}

            common_ts = sorted(set(ta.keys()) & set(tb.keys()))
            if len(common_ts) < 3:
                continue

            va = [ta[t] for t in common_ts]
            vb = [tb[t] for t in common_ts]

            # Pearson correlation
            n = len(common_ts)
            ma = sum(va) / n
            mb = sum(vb) / n

            num = sum((a - ma) * (b - mb) for a, b in zip(va, vb))
            den_a = sum((a - ma) ** 2 for a in va)
            den_b = sum((b - mb) ** 2 for b in vb)

            if den_a > 0 and den_b > 0:
                corr = num / math.sqrt(den_a * den_b)
                if abs(corr) > 0.6:
                    correlations.append({
                        "scope_a": sa,
                        "scope_b": sb,
                        "correlation": round(corr, 4),
                        "n_common": n,
                        "interpretation": "same_direction" if corr > 0 else "opposite_direction"
                    })

    return correlations


def print_trend_report(path: Path = LEDGER):
    """Print a human-readable trend report."""
    trends = detect_all_trends(path)

    print("=" * 72)
    print("TREND DETECTION REPORT")
    print("=" * 72)

    # Sort by severity
    severity_order = {"failed": 0, "accelerating": 1, "drifting": 2, 
                      "noisy": 3, "stable": 4, "insufficient_data": 5}
    sorted_trends = sorted(trends.items(), 
                          key=lambda x: severity_order.get(x[1].verdict_trend, 99))

    for scope, tr in sorted_trends:
        flag = {
            "failed": "FAIL",
            "accelerating": "WARN",
            "drifting": "DRIFT",
            "noisy": "OK",
            "stable": "OK",
            "insufficient_data": "N/A"
        }.get(tr.verdict_trend, "?")

        days_str = f"{tr.predicted_fail_days:.1f}d" if tr.predicted_fail_days else "N/A"

        print(f"[{flag:5s}] {scope:50s} {tr.verdict_trend:12s} "
              f"slope={tr.slope_per_day:+.4f}/day  R²={tr.r_squared:.3f}  "
              f"fail_in={days_str}")

    print("-" * 72)

    # Cross-domain
    xdom = cross_domain_correlation(path)
    if xdom:
        print("\nCROSS-DOMAIN CORRELATIONS:")
        for c in xdom:
            print(f"  {c['scope_a'][:40]:40s} <-> {c['scope_b'][:40]:40s} "
                  f"r={c['correlation']:.3f} ({c['interpretation']})")
    else:
        print("\nNo significant cross-domain correlations found.")

    print("=" * 72)


def export_trend_json(path: Path = LEDGER, out_path: Path = Path("trend_report.json")):
    """Export trend report as JSON."""
    trends = detect_all_trends(path)
    xdom = cross_domain_correlation(path)

    report = {
        "generated": Path(path).stat().st_mtime if path.exists() else 0,
        "n_scopes": len(trends),
        "trends": [
            {
                "scope": tr.scope,
                "n_points": tr.n_points,
                "slope_per_day": tr.slope_per_day,
                "r_squared": tr.r_squared,
                "current_value": tr.current_value,
                "predicted_fail_days": tr.predicted_fail_days,
                "verdict": tr.verdict_trend
            }
            for tr in trends.values()
        ],
        "cross_domain": xdom
    }

    out_path.write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    print_trend_report()
