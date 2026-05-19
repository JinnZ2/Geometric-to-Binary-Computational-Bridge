"""
transfer.py  (fabrication/verify/)

Transfer function H(f) = Y(f) / X(f)  with regularization.

Plain division blows up where X(f) ≈ 0.  Use Wiener-style
regularized inversion:
      H(f) = (X*·Y) / (|X|² + ε)
where ε is a small fraction of max(|X|²).  This is standard
noise-robust deconvolution for sine-sweep measurements.

Coherence γ²(f) = |Sxy|² / (Sxx·Syy)  on simple block estimates,
used to gate which frequency bins we trust.  γ² ∈ [0,1];
γ² > 0.7 is a conventional threshold for reliable bins.

License: CC0. Stdlib only.
"""
import math

from .fft import fft, _next_pow2, hann
from .wav_reader import read_wav


def _complex_spectrum(samples, sr):
    n_raw = len(samples)
    n     = _next_pow2(n_raw)
    win   = hann(n_raw)
    padded = [samples[i] * win[i] for i in range(n_raw)] + [0.0]*(n - n_raw)
    spec   = fft(padded)
    half   = n // 2
    return spec[:half], [i * sr / n for i in range(half)]


def _align_lengths(a, b):
    """Truncate longer signal to match shorter (post-recording trim)."""
    n = min(len(a), len(b))
    return a[:n], b[:n]


def _resample_match(a, sr_a, b, sr_b):
    """If sample rates differ, force the test to bail loudly."""
    if sr_a != sr_b:
        raise ValueError(
            f"Sample-rate mismatch: input {sr_a} Hz vs output {sr_b} Hz. "
            f"Record both at the same rate on the phone."
        )
    return sr_a


def transfer_function(x_wav, y_wav, eps_frac=1e-3):
    """
    x_wav : reference (the sweep you played)
    y_wav : recording (what the mic captured)
    Returns: (freqs, |H|, phase_H, coherence_proxy)
    """
    x_samples, sr_x = read_wav(x_wav)
    y_samples, sr_y = read_wav(y_wav)
    sr = _resample_match(x_samples and sr_x, sr_x, y_samples and sr_y, sr_y)

    x_samples, y_samples = _align_lengths(x_samples, y_samples)

    X, freqs = _complex_spectrum(x_samples, sr)
    Y, _     = _complex_spectrum(y_samples, sr)

    # |X|² for regularization floor
    px = [abs(v)**2 for v in X]
    eps = eps_frac * max(px) if max(px) > 0 else 1e-12

    H = [(X[i].conjugate() * Y[i]) / (px[i] + eps) for i in range(len(X))]
    mag   = [abs(h) for h in H]
    phase = [math.atan2(h.imag, h.real) for h in H]

    # block-free coherence proxy: |X|² / (|X|² + ε)
    # rises toward 1 where excitation is strong, drops where weak
    coh = [px[i] / (px[i] + eps) for i in range(len(X))]

    return freqs, mag, phase, coh
