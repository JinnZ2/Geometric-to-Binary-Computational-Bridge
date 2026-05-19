"""
peak.py  (fabrication/verify/)

Peak-pick + Q-factor extraction.

  f₀ = arg-max magnitude inside [f_lo, f_hi] search band
  Q  = f₀ / Δf_-3dB    (half-power bandwidth)

Q is the second falsification axis:
  low Q  -> wall losses / leak / wrong damping model
  high Q -> fab better than predicted (good news -- but flag it)

License: CC0. Stdlib only.
"""
import math


def peak_pick(freqs, mags, f_lo, f_hi):
    in_band = [(f, m) for f, m in zip(freqs, mags) if f_lo <= f <= f_hi]
    if not in_band:
        return None
    return max(in_band, key=lambda fm: fm[1])


def q_factor(freqs, mags, f0):
    """Half-power (-3 dB => peak/√2) bandwidth."""
    # find peak index
    i0 = min(range(len(freqs)), key=lambda i: abs(freqs[i] - f0))
    peak = mags[i0]
    half = peak / math.sqrt(2)

    # walk left
    iL = i0
    while iL > 0 and mags[iL] > half:
        iL -= 1
    # walk right
    iR = i0
    while iR < len(mags) - 1 and mags[iR] > half:
        iR += 1

    bw = freqs[iR] - freqs[iL]
    return (f0 / bw) if bw > 0 else float("inf")


def peak_pick_gated(freqs, mags, coh, f_lo, f_hi, coh_min=0.7):
    """Coherence-gated peak pick. Refuses to return a peak in a
    frequency bin where the excitation was too weak to trust."""
    in_band = [
        (f, m, c)
        for f, m, c in zip(freqs, mags, coh)
        if f_lo <= f <= f_hi and c >= coh_min
    ]
    if not in_band:
        return None
    f0, m0, _ = max(in_band, key=lambda t: t[1])
    return f0, m0
