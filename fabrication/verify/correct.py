"""
correct.py  (fabrication/verify/)

Divide H_total by H_baseline to isolate the cavity.

Regularized to prevent division-by-near-zero at frequencies where
the speaker was inaudible. Bands where the baseline itself was
untrustworthy (low coherence) are BLANKED rather than amplified
-- this is the difference between "isolating the cavity" and
"manufacturing spurious peaks".

License: CC0. Stdlib only.
"""


def correct_with_baseline(freqs, mag_total, coh_total,
                          baseline, eps_frac=1e-3, coh_min=0.3):
    """
    Returns corrected (freqs, mag, coh) where:
      mag_c  ≈ H_total / H_baseline  (regularized)
      coh_c  = min(coh_total, coh_baseline) per bin (weakest link)
      blanked to 0 in bands where coh_baseline < coh_min
    """
    f_b   = baseline["freqs"]
    mag_b = baseline["mag"]
    coh_b = baseline["coh"]

    if len(f_b) != len(freqs):
        raise ValueError(
            "Baseline length differs from current measurement. "
            "Re-record at the same sample rate and sweep duration."
        )
    # frequency-axis check (sample rates match -> same bin layout)
    if abs(f_b[1] - freqs[1]) > 1e-6:
        raise ValueError("Baseline bin spacing mismatch.")

    eps = eps_frac * max(mag_b)
    mag_c = []
    coh_c = []
    for i in range(len(freqs)):
        if coh_b[i] < coh_min:
            # baseline didn't sample this band -> can't correct
            mag_c.append(0.0)
            coh_c.append(0.0)
            continue
        mag_c.append(mag_total[i] / (mag_b[i] + eps))
        coh_c.append(min(coh_total[i], coh_b[i]))
    return freqs, mag_c, coh_c
