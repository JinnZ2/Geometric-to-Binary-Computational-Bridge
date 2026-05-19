"""
assign.py  (fabrication/verify/)

Predicted ↔ measured mode assignment.

Greedy nearest-frequency matching with a relative-distance gate.
For small N (≤ 8) this is optimal in practice and avoids the full
Hungarian algorithm. If we ever go to >10 modes, swap in
Hungarian -- interface stays the same.

Distance metric:  d_ij = |log(f_meas_i) - log(f_pred_j)|
(log-domain is correct for spectra -- equal weight per octave)

License: CC0. Stdlib only.
"""
import math


def assign(predicted, measured, max_log_dist=math.log(1.30)):
    """
    predicted    : list of dicts with key "f"
    measured     : list of dicts with key "f"
    max_log_dist : reject matches farther than this (≈30% by default)

    Returns:
      matches    : [(pred_idx, meas_idx, log_dist), ...]
      unmatched_predicted : list of pred indices
      unmatched_measured  : list of meas indices
    """
    pairs = []
    for pi, p in enumerate(predicted):
        for mi, m in enumerate(measured):
            d = abs(math.log(m["f"]) - math.log(p["f"]))
            if d <= max_log_dist:
                pairs.append((d, pi, mi))
    pairs.sort()
    used_p, used_m = set(), set()
    matches = []
    for d, pi, mi in pairs:
        if pi in used_p or mi in used_m:
            continue
        used_p.add(pi)
        used_m.add(mi)
        matches.append((pi, mi, d))
    unmatched_p = [i for i in range(len(predicted)) if i not in used_p]
    unmatched_m = [i for i in range(len(measured))  if i not in used_m]
    return matches, unmatched_p, unmatched_m
