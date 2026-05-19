"""
peak_multi.py  (fabrication/verify/)

Multi-peak detection in a magnitude spectrum. No scipy.

Approach:
  1. Smooth |H| with a 3-bin moving median (kills bin spikes)
  2. Find local maxima above a prominence threshold
  3. Coherence-gate each candidate
  4. Sort by magnitude, keep top N
  5. Compute per-peak Q from local -3 dB bandwidth

"Prominence" = peak height above the higher of its two adjacent
local minima within a search window. Standard SciPy semantics,
implemented from scratch here.

License: CC0. Stdlib only.
"""
import math


def _moving_median(x, k=3):
    """Tiny 3-bin median to suppress single-bin FFT spikes."""
    if k < 2:
        return list(x)
    half = k // 2
    out = []
    for i in range(len(x)):
        lo = max(0, i - half)
        hi = min(len(x), i + half + 1)
        window = sorted(x[lo:hi])
        out.append(window[len(window)//2])
    return out


def _local_maxima(y):
    """Indices i where y[i] > y[i-1] and y[i] >= y[i+1].
    The `>=` on the right side lets plateau left-edges qualify --
    the 3-bin median smoother can flatten the top of a sharp peak
    into 2-3 equal bins, and a strict `>` on both sides would miss it.
    A pure constant region (..., a, a, a, ...) is still rejected
    because the left-edge check fails for every index but the first
    of the run, which itself fails the strict-greater left check."""
    return [i for i in range(1, len(y)-1)
            if y[i] > y[i-1] and y[i] >= y[i+1]]


def _prominence(y, i, max_lookback=200):
    """
    Drop on each side until y STRICTLY exceeds y[i] OR window exhausted;
    prominence = y[i] - max(min_left, min_right).

    Note `<=` (not `<`) in the loop guard: plateau peaks (where the
    3-bin median smoother flattens 2-3 adjacent bins to equal values)
    must walk ACROSS the plateau before they can find a minimum.
    Strict `<` would exit on the first equal neighbor and return
    prominence=0 for every peak that has a tied bin -- which is most
    real peaks after windowing + smoothing.
    """
    # left side
    min_left = y[i]
    j = i - 1
    steps = 0
    while j >= 0 and y[j] <= y[i] and steps < max_lookback:
        if y[j] < min_left:
            min_left = y[j]
        j -= 1
        steps += 1
    # right side
    min_right = y[i]
    j = i + 1
    steps = 0
    while j < len(y) and y[j] <= y[i] and steps < max_lookback:
        if y[j] < min_right:
            min_right = y[j]
        j += 1
        steps += 1
    return y[i] - max(min_left, min_right)


def _local_q(freqs, mags, i):
    """Half-power Q around local max at index i."""
    peak = mags[i]
    half = peak / math.sqrt(2)
    iL = i
    while iL > 0 and mags[iL] > half:
        iL -= 1
    iR = i
    while iR < len(mags)-1 and mags[iR] > half:
        iR += 1
    bw = freqs[iR] - freqs[iL]
    return (freqs[i] / bw) if bw > 0 else float("inf")


def detect_peaks(freqs, mags, coh,
                 search_band=(50, 2000),
                 coh_min=0.7,
                 prominence_frac=0.05,
                 max_peaks=8):
    """
    Returns list of dicts sorted by frequency:
        [{"f": Hz, "mag": ..., "q": ..., "coh": ...}, ...]

    prominence_frac : minimum prominence as fraction of max(|H|)
                      in the search band. 0.05 = 5% -- strict enough
                      to ignore numerical ripple, loose enough to
                      keep secondary modes.
    """
    fL, fH = search_band
    smooth = _moving_median(mags, k=3)
    mx = max((smooth[i] for i in range(len(smooth))
              if fL <= freqs[i] <= fH), default=0.0)
    if mx <= 0:
        return []
    prom_floor = prominence_frac * mx

    candidates = []
    for i in _local_maxima(smooth):
        if not (fL <= freqs[i] <= fH):
            continue
        if coh[i] < coh_min:
            continue
        prom = _prominence(smooth, i)
        if prom < prom_floor:
            continue
        candidates.append({
            "idx":        i,
            "f":          freqs[i],
            "mag":        smooth[i],
            "q":          _local_q(freqs, smooth, i),
            "coh":        coh[i],
            "prominence": prom,
        })
    # keep top N by magnitude, then sort by frequency for return
    candidates.sort(key=lambda c: c["mag"], reverse=True)
    candidates = candidates[:max_peaks]
    candidates.sort(key=lambda c: c["f"])
    return candidates
