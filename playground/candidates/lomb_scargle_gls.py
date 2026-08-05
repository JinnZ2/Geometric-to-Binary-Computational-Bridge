"""Generalised Lomb-Scargle, stdlib, as the period estimator FCL-12b wants.

The slotted autocorrelation in field/ answers "is this structured" with a
calibrated p-value and then refuses to name a period, because the argmax lag
is not one: a rider peaks at every multiple of T/2 and noise picks the winner.
Both textbook autocorrelation handles were measured and both were refused.

This fits sinusoids directly to the irregular timestamps instead. Floating
mean and uniform weights, Zechmeister & Kuerster 2009 eq 5-9, which is the
form to use here because the deviation series is not zero-mean. Power is
normalised to [0, 1].

Measured on Poisson-sampled riders, n=200, sigma 0.3:
    T =  6 s   median |error| 0.0092 s   (0.15% of the period)
    T = 12 s   median |error| 0.0346 s   (0.29%)
    T = 20 s   median |error| 0.1329 s   (0.66%)
against the slotted argmax, which came back at a median 8.8 s for a true
T/2 of 3.0 s.

Separation from noise on the same clocks: the max power a white series
reaches has a 95th percentile of 0.156, against a median peak power of 0.842
for the real riders. The gap is what the ceiling check tests.
"""
import math
import random

PROBLEM = "FCL-12b"
CLAIM = ("Generalised Lomb-Scargle recovers the period of an irregularly "
         "sampled rider to better than 1% of the period, where the slotted "
         "autocorrelation argmax cannot name a period at all.")
KIND = "CODE"
AUTHOR = "claude, session 2026-08-05"
NEEDS_NULL = True
MATERIAL = None

RIDERS = (6.0, 12.0, 20.0)
TOL_FRAC = 0.01          # 1% of the true period
NOISE_95 = 0.25          # max power a white series is allowed to reach


# --- the estimator -----------------------------------------------------
def gls_power(times, ys, freqs):
    """Generalised Lomb-Scargle periodogram. Power in [0, 1] per frequency."""
    n = len(ys)
    if n != len(times):
        raise ValueError("times and ys differ in length")
    if n < 4:
        raise ValueError("need at least 4 samples")
    w = 1.0 / n
    Y = sum(ys) * w
    YY = sum(y * y for y in ys) * w - Y * Y
    out = []
    for f in freqs:
        om = 2.0 * math.pi * f
        C = S = YC = YS = CC = SS = CS = 0.0
        for t, y in zip(times, ys):
            c, s = math.cos(om * t), math.sin(om * t)
            C += c
            S += s
            YC += y * c
            YS += y * s
            CC += c * c
            SS += s * s
            CS += c * s
        C *= w
        S *= w
        YC *= w
        YS *= w
        CC *= w
        SS *= w
        CS *= w
        YC -= Y * C
        YS -= Y * S
        CC -= C * C
        SS -= S * S
        CS -= C * S
        D = CC * SS - CS * CS
        if D <= 0.0 or YY <= 0.0:
            out.append(0.0)
            continue
        p = (SS * YC * YC + CC * YS * YS - 2.0 * CS * YC * YS) / (YY * D)
        out.append(max(0.0, min(1.0, p)))
    return out


def frequency_grid(times, oversample=5.0, fmax_factor=1.0):
    """From 1/span up to a pseudo-Nyquist set by the median sampling gap.

    There is no true Nyquist for irregular sampling; the median gap is the
    honest stand-in and the factor is exposed so it can be pushed.
    """
    st = sorted(times)
    span = st[-1] - st[0]
    gaps = sorted(b - a for a, b in zip(st, st[1:]) if b > a)
    if span <= 0 or not gaps:
        raise ValueError("degenerate clock")
    med = gaps[len(gaps) // 2]
    fmin, fmax = 1.0 / span, fmax_factor / (2.0 * med)
    df = 1.0 / (oversample * span)
    return [fmin + i * df for i in range(int((fmax - fmin) / df) + 1)]


def best_period(times, ys, **kw):
    """Period at peak power, and the power there."""
    fs = frequency_grid(times, **kw)
    ps = gls_power(times, ys, fs)
    i = max(range(len(ps)), key=lambda k: ps[k])
    return {"period_s": 1.0 / fs[i], "power": ps[i], "n_freqs": len(fs)}


# --- the artifact ------------------------------------------------------
def _poisson(n, seed, rate=1.0):
    r = random.Random(seed)
    t, out = 0.0, []
    for _ in range(n):
        t += r.expovariate(rate)
        out.append(t)
    return out


def _series(kind, T, seed, n=200, noise=0.3):
    ts = _poisson(n, seed)
    r = random.Random(9000 + seed)
    if kind == "rider":
        ys = [math.sin(2.0 * math.pi * t / T) + r.gauss(0, noise) for t in ts]
    elif kind == "noise":
        ys = [r.gauss(0, 1) for _ in ts]
    elif kind == "wrong":
        # a rider at a DIFFERENT period than the one claimed
        ys = [math.sin(2.0 * math.pi * t / (T * 2.7)) + r.gauss(0, noise)
              for t in ts]
    else:
        raise ValueError(kind)
    return ts, ys


def _artifact(kind):
    est = {}
    for T in RIDERS:
        errs, pw = [], []
        for s in range(12):
            ts, ys = _series(kind, T, s)
            b = best_period(ts, ys)
            errs.append(abs(b["period_s"] - T))
            pw.append(b["power"])
        errs.sort()
        est[T] = {"median_abs_error_s": errs[len(errs) // 2],
                  "worst_abs_error_s": errs[-1],
                  "median_power": sorted(pw)[len(pw) // 2]}
    noise_max = []
    for s in range(40):
        ts, ys = _series("noise", 1.0, 500 + s, n=100)
        noise_max.append(best_period(ts, ys)["power"])
    noise_max.sort()
    return {"kind": kind, "by_period": est,
            "noise_power_95": noise_max[int(0.95 * len(noise_max))]}


def solve():
    return _artifact("rider")


def broken():
    """The estimator handed a rider at 2.7x the period it claims to find.

    If the period checks still pass on this, they are not testing the period.
    """
    return _artifact("wrong")


def null():
    """White values on the same clocks. Structure gone, sampling identical."""
    return _artifact("noise")


def checks(a):
    out = []
    for T in RIDERS:
        d = a["by_period"][T]
        tol = TOL_FRAC * T
        out.append(("period T=%.0fs within %.0f%%" % (T, 100 * TOL_FRAC),
                    d["median_abs_error_s"] <= tol,
                    "median |error| %.4f s against tolerance %.3f s"
                    % (d["median_abs_error_s"], tol)))
    worst = max(a["by_period"][T]["worst_abs_error_s"] / T for T in RIDERS)
    out.append(("worst case stays under 5%", worst <= 0.05,
                "worst fractional error %.4f" % worst))
    weakest = min(a["by_period"][T]["median_power"] for T in RIDERS)
    out.append(("peak power clears the noise ceiling",
                weakest > NOISE_95,
                "weakest median peak power %.3f against ceiling %.2f"
                % (weakest, NOISE_95)))
    out.append(("white series stay under the ceiling",
                a["noise_power_95"] <= NOISE_95,
                "95th percentile of max power on noise = %.3f"
                % a["noise_power_95"]))
    return out
