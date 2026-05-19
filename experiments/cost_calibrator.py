"""
cost_calibrator.py  (experiments/)
====================================

Reads the dispatcher's request_log and updates TierCost based on actual
observed wall-time and (optionally) token cost. Replaces the arbitrary
cost units in the prototype with empirically grounded values.

USAGE
-----
    from cost_calibrator import calibrate_from_log
    new_costs = calibrate_from_log(dispatcher.stats.request_log)
    # apply new_costs to dispatcher's routing

CALIBRATION MODEL
-----------------
For each tier with at least min_samples observations:
  base_cost      <- mean of (wall_time - per_unit * complexity)
  per_unit_cost  <- slope of wall_time vs complexity (least-squares)

If a tier has fewer than min_samples observations, keep its default.

STATUS: experimental. Real deployment would also incorporate token
cost (count input/output tokens) and energy cost (compute time *
hardware draw).

License: CC0
"""

from dataclasses import dataclass, field
from typing import Optional

from comfort_layer_dispatcher import (
    RouteTier, TierCost, DEFAULT_COSTS
)


# ---------------------------------------------------------------------------
# CALIBRATION
# ---------------------------------------------------------------------------

@dataclass
class CalibrationReport:
    updated_tiers: dict[str, TierCost] = field(default_factory=dict)
    samples_per_tier: dict[str, int]   = field(default_factory=dict)
    confidence_per_tier: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _least_squares(xs: list[float], ys: list[float]
                   ) -> tuple[float, float]:
    """Fit y = a + b*x. Returns (a, b)."""
    n = len(xs)
    if n < 2:
        return 0.0, 0.0
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    num = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    den = sum((x - x_mean) ** 2 for x in xs)
    if den == 0:
        return y_mean, 0.0
    b = num / den
    a = y_mean - b * x_mean
    return a, b


def calibrate_from_log(request_log: list[dict],
                       min_samples: int = 5
                       ) -> CalibrationReport:
    """
    Read the dispatcher's request_log and produce updated TierCost values
    for each tier with sufficient observations.

    The log entry shape (from comfort_layer_dispatcher):
        {timestamp, request, tier, cost, wall_time, success, output}
    """
    report = CalibrationReport()

    # group by tier
    by_tier: dict[str, list[dict]] = {}
    for entry in request_log:
        by_tier.setdefault(entry["tier"], []).append(entry)

    for tier_value, entries in by_tier.items():
        report.samples_per_tier[tier_value] = len(entries)
        if len(entries) < min_samples:
            report.notes.append(
                f"{tier_value}: only {len(entries)} samples, "
                f"keeping default cost (need >= {min_samples})"
            )
            continue

        # complexity proxy: cost stored at decision time reflects
        # estimate_cost(tier, pattern) = base + per_unit * complexity
        # so we reverse-engineer: complexity ~ (cost - base_default) / per_unit_default
        try:
            tier_enum = RouteTier(tier_value)
        except ValueError:
            continue
        default = DEFAULT_COSTS[tier_enum]

        complexities = []
        wall_times = []
        for e in entries:
            if not e.get("success"):
                continue
            wt = e.get("wall_time", 0.0)
            if wt <= 0:
                continue
            cost = e.get("cost", 0.0)
            if default.per_unit_cost == 0:
                complexity = 0.0
            else:
                complexity = (cost - default.base_cost) / default.per_unit_cost
            complexity = max(0.0, min(1.0, complexity))
            complexities.append(complexity)
            wall_times.append(wt)

        if len(complexities) < min_samples:
            report.notes.append(
                f"{tier_value}: only {len(complexities)} successful "
                f"samples after filtering, keeping default"
            )
            continue

        # least-squares fit: wall_time = a + b * complexity
        a, b = _least_squares(complexities, wall_times)
        a = max(0.0, a)       # base cost can't be negative
        b = max(0.0, b)       # per-unit cost can't be negative

        report.updated_tiers[tier_value] = TierCost(
            tier=tier_enum,
            base_cost=a,
            per_unit_cost=b,
        )

        # confidence: how well does the fit explain variance?
        if wall_times:
            mean_wt = sum(wall_times) / len(wall_times)
            ss_tot = sum((wt - mean_wt) ** 2 for wt in wall_times)
            ss_res = sum(
                (wall_times[i] - (a + b * complexities[i])) ** 2
                for i in range(len(wall_times))
            )
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
            report.confidence_per_tier[tier_value] = max(0.0, r_squared)

    return report


def apply_calibration(report: CalibrationReport,
                      current_costs: dict[RouteTier, TierCost],
                      blend_weight: float = 0.5
                      ) -> dict[RouteTier, TierCost]:
    """
    Blend calibrated costs with current costs. blend_weight=1.0 means
    fully adopt calibration; blend_weight=0.0 means keep current.
    Default 0.5 means halfway -- smooths against single-batch outliers.
    """
    out = dict(current_costs)
    for tier_value, new_tc in report.updated_tiers.items():
        tier = new_tc.tier
        if tier in current_costs:
            curr = current_costs[tier]
            out[tier] = TierCost(
                tier=tier,
                base_cost=curr.base_cost * (1 - blend_weight)
                          + new_tc.base_cost * blend_weight,
                per_unit_cost=curr.per_unit_cost * (1 - blend_weight)
                              + new_tc.per_unit_cost * blend_weight,
            )
        else:
            out[tier] = new_tc
    return out
