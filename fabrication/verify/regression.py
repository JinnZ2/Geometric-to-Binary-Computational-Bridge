"""
regression.py  (fabrication/verify/)

Ordinary least squares for y = m·x + b with stats.
Stdlib only. Returns slope, intercept, r², 95% CI on slope.

License: CC0. Stdlib only.
"""
import math


def ols(xs, ys):
    n = len(xs)
    if n < 3:
        raise ValueError("Need ≥3 points for regression.")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx)**2 for x in xs)
    sxy = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    if sxx == 0:
        raise ValueError("All x identical -- cannot fit.")
    slope = sxy / sxx
    intercept = my - slope * mx
    # residuals
    ss_res = sum((ys[i] - (slope*xs[i] + intercept))**2 for i in range(n))
    ss_tot = sum((y - my)**2 for y in ys)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    # standard error of slope
    if n > 2:
        s_err = math.sqrt(ss_res / (n - 2))
        se_slope = s_err / math.sqrt(sxx) if sxx > 0 else float("inf")
    else:
        se_slope = float("inf")
    # 95% CI band using Student-t
    t_95 = _t_critical_95(n - 2)
    ci   = t_95 * se_slope
    return {
        "slope":     slope,
        "intercept": intercept,
        "r2":        r2,
        "se_slope":  se_slope,
        "ci95":      (slope - ci, slope + ci),
        "n":         n,
    }


def _t_critical_95(df):
    table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
             6: 2.447,  7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
             15: 2.131, 20: 2.086, 30: 2.042, 60: 2.000}
    if df <= 0:
        return 12.706
    keys = sorted(table)
    for k in keys:
        if df <= k:
            return table[k]
    return 1.96
