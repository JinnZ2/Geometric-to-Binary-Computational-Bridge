"""
fft.py  (fabrication/verify/)

Iterative radix-2 Cooley-Tukey FFT. No external deps.
For phone-mic clips (1-10 s @ 44.1 kHz) this runs in seconds.
If perf matters later, swap in numpy; interface is identical.

License: CC0. Stdlib only.
"""
import math
from cmath import exp, pi as PI


def _next_pow2(n):
    p = 1
    while p < n:
        p <<= 1
    return p


def _bit_reverse(x):
    n = len(x)
    j = 0
    out = list(x)
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    return out


def fft(x):
    """In-place radix-2 FFT. len(x) must be power of 2."""
    n = len(x)
    if n & (n - 1):
        raise ValueError("FFT length must be power of 2")
    a = _bit_reverse([complex(v) for v in x])
    size = 2
    while size <= n:
        half = size // 2
        w_step = exp(-2j * PI / size)
        for start in range(0, n, size):
            w = 1 + 0j
            for k in range(half):
                t = w * a[start + k + half]
                u = a[start + k]
                a[start + k]        = u + t
                a[start + k + half] = u - t
                w *= w_step
        size <<= 1
    return a


def hann(n):
    """Window -- reduces spectral leakage on tap-style transients."""
    return [0.5 * (1 - math.cos(2 * PI * i / (n - 1)))
            for i in range(n)]


def magnitude_spectrum(samples, sample_rate):
    """Returns (freqs_Hz, magnitudes). Zero-padded to next pow2."""
    n_raw = len(samples)
    n     = _next_pow2(n_raw)
    win   = hann(n_raw)
    padded = [samples[i] * win[i] for i in range(n_raw)] + [0.0]*(n - n_raw)
    spec   = fft(padded)
    half   = n // 2
    mags   = [abs(spec[i]) / n_raw for i in range(half)]
    freqs  = [i * sample_rate / n for i in range(half)]
    return freqs, mags
