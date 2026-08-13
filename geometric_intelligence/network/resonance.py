"""
resonance.py -- multi-scale resonance and injection detection over phi bands.

Bins a spectrum into phi-ratio bands, fits a power law across bands, and
reports bands whose energy departs from the fit. `detect_injection` compares a
spectrum against a captured baseline.

=====================================================================
AUDIT
=====================================================================
Behaviour is UNCHANGED from the file as supplied, except one inline comment
that misstated its own threshold (GR-4). The rest is recorded because each fix
picks a number, and the numbers here are detection thresholds.

GR-1   The band edges are not monotonic, and the top band is dead.
       `_compute_edges` multiplies by phi `while edges[-1] < f_max`, so it
       exits only AFTER overshooting f_max, and then appends f_max. With the
       defaults the tail is [..., 9349.0, 15127.0, 10000.0]: the last
       interval is [15127, 10000), which `lo <= f < hi` can never satisfy.
       One band in 21 is empty by construction, the band below it runs to
       15127 Hz -- past the f_max the caller asked for -- and any component
       above 15127 Hz is dropped without a word. Same screen as GLY-1.

GR-2   `bands_per_octave` is stored and never read.
       `_compute_edges` uses PHI and nothing else, so
       `MultiScaleResonance(bands_per_octave=1)` and `(bands_per_octave=64)`
       produce byte-identical edge lists. An argument that looks like the
       resolution control does nothing. `band_resolution_is_honoured()`
       returns the proof.

GR-3   The power-law fit includes the peaks it is used to judge.
       The comment above the fit says "Fit power law to non-peak bands". The
       loop is guarded only by `band_count[i] > 0`, so every populated band
       goes in, peaks included. A peak therefore raises the baseline it is
       then compared against, which is P-SELF-SUPPLIED-FALSIFIER: the
       reference value is produced by the data under test. It biases toward
       missing anomalies, and the bias grows with how much of the spectrum is
       anomalous -- i.e. it is weakest exactly when there is most to find.

GR-5   `detect_injection` has no noise model and no null.
       The gate is a bare per-bin ratio against the baseline with no
       multiplicity correction and no minimum-sample rule. Measured on two
       independent draws of the SAME Rayleigh noise process -- no injection
       present -- it flags 15.7 % of bins, and `injection_score`, documented
       as `n_injections / len(freqs)`, reads 0.157. That is not a rate of
       anything; it is the constant this gate returns on noise. Calibrating
       it needs a null (shuffle the two series against each other, or
       bootstrap the ratio distribution) and a correction over the number of
       bins tested -- the same two things `field/field_claim_loop.py`'s
       FCL-5/6 needed.

GR-6   One method returns two different shapes.
       `detect_injection(f, a, baseline_amps=None)` falls back to
       `self.analyze(f, a)`, whose dict has no `injections`, `n_injections`,
       `injection_score` or `threshold_ratio` key. So
       `detect_injection(...)["injections"]` raises KeyError for exactly the
       callers who did not capture a baseline -- the cold-workshop case the
       field guide is written for. The fallback is intended; the silent shape
       change is not.

GR-4   FIXED (comment only, no behaviour change).
       The injection gate reads `ratio > 1.0 + PHI_INV_9 * 100`, which is
       2.3156. The inline comment said "> ~1.315x baseline", low by a factor
       of 1.76. The docstring's own wording -- "exceed baseline by
       > phi^-9 * 100 %" -- is self-consistent with 2.3156, so the comment
       was the wrong one and is corrected below.

Also worth naming, though it is a design question rather than a defect: both
thresholds are a phi constant times a round number (phi^-9 x 10 = 0.1316,
phi^-9 x 100 = 1.3156). The multiplier is what sets the scale in each case, so
phi^-9 is not doing the work its name implies. Open problem GR-7.

License: CC0. Stdlib only.
"""
from __future__ import annotations

import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from .core import PHI, PHI_INV, PHI_INV_9


@dataclass
class ResonancePeak:
    scale: float          # frequency or spatial scale
    amplitude: float      # energy at that scale
    expected_amp: float   # what self-similarity predicts
    deviation: float      # |actual - expected| / expected
    q_factor: float       # sharpness of peak


class MultiScaleResonance:
    """
    Analyze a spectrum for self-similar resonance patterns.

    Scales are arranged in φ-octave bands:
      band_n spans [f0 * φ^n, f0 * φ^(n+1))

    In a self-similar (fractal/geometric) system, energy should
    follow a power law across bands. Deviations flag anomalies.
    """

    def __init__(self, f_min: float = 1.0, f_max: float = 10000.0,
                 bands_per_octave: int = 5):
        self.f_min = f_min
        self.f_max = f_max
        self.bands_per_octave = bands_per_octave
        # φ-based band edges
        self.band_edges = self._compute_edges()

    def _compute_edges(self) -> List[float]:
        edges = [self.f_min]
        while edges[-1] < self.f_max:
            edges.append(edges[-1] * PHI)
        edges.append(self.f_max)
        return edges

    def analyze(self, freqs: List[float], amps: List[float],
                expected_slope: float = -1.0) -> Dict:
        """
        Analyze spectrum.

        expected_slope: power-law slope for self-similar systems.
                       -1.0 is 1/f noise; 0.0 is flat; -2.0 is steeper.

        Returns dict with peaks, anomalies, and anomaly_score.
        """
        if len(freqs) != len(amps):
            raise ValueError("freqs and amps must have same length")
        if not freqs:
            return {"peaks": [], "anomalies": [], "anomaly_score": 0.0}

        # Bin into φ-bands
        band_energy = [0.0] * (len(self.band_edges) - 1)
        band_count = [0] * len(band_energy)

        for f, a in zip(freqs, amps):
            for i in range(len(band_energy)):
                lo, hi = self.band_edges[i], self.band_edges[i+1]
                if lo <= f < hi:
                    band_energy[i] += a * a  # energy = amplitude squared
                    band_count[i] += 1
                    break

        # Average energy per band
        band_avg = [e / c if c > 0 else 0.0 
                    for e, c in zip(band_energy, band_count)]

        # Find peaks (local maxima in energy)
        peaks = []
        for i in range(1, len(band_avg) - 1):
            if band_avg[i] > band_avg[i-1] and band_avg[i] > band_avg[i+1]:
                # Q-factor approximation: f_center / bandwidth
                f_center = math.sqrt(self.band_edges[i] * self.band_edges[i+1])
                bw = self.band_edges[i+1] - self.band_edges[i]
                q = f_center / bw if bw > 0 else 0.0
                peaks.append(ResonancePeak(
                    scale=f_center,
                    amplitude=band_avg[i],
                    expected_amp=0.0,  # filled later
                    deviation=0.0,
                    q_factor=q
                ))

        # Fit power law to non-peak bands
        # Use median of log-log data for robustness
        log_centers = []
        log_energies = []
        for i in range(len(band_avg)):
            if band_count[i] > 0:
                f_c = math.sqrt(self.band_edges[i] * self.band_edges[i+1])
                log_centers.append(math.log(f_c))
                log_energies.append(math.log(band_avg[i] + 1e-12))

        if len(log_centers) >= 2:
            # Simple linear regression on log-log
            n = len(log_centers)
            mx = sum(log_centers) / n
            my = sum(log_energies) / n
            num = sum((x - mx) * (y - my) for x, y in zip(log_centers, log_energies))
            den = sum((x - mx) ** 2 for x in log_centers)
            slope = num / den if den != 0 else expected_slope
            intercept = my - slope * mx
        else:
            slope = expected_slope
            intercept = 0.0

        # Compute expected energy and deviations for each peak
        anomalies = []
        for p in peaks:
            log_f = math.log(p.scale)
            log_expected = slope * log_f + intercept
            p.expected_amp = math.exp(log_expected)
            if p.expected_amp > 0:
                p.deviation = abs(p.amplitude - p.expected_amp) / p.expected_amp
            else:
                p.deviation = float('inf')

            # Anomaly: deviation exceeds φ⁻⁹ threshold
            if p.deviation > PHI_INV_9 * 10:  # 10x φ⁻⁹ = ~0.13 (13%)
                anomalies.append({
                    "scale_hz": round(p.scale, 2),
                    "amplitude": round(p.amplitude, 6),
                    "expected": round(p.expected_amp, 6),
                    "deviation_pct": round(p.deviation * 100, 2),
                    "q_factor": round(p.q_factor, 2),
                    "severity": "high" if p.deviation > 1.0 else "medium"
                })

        # Overall anomaly score: fraction of total energy in anomalous peaks
        total_energy = sum(band_avg)
        anomalous_energy = sum(p.amplitude for p in peaks if p.deviation > PHI_INV_9 * 10)
        anomaly_score = anomalous_energy / total_energy if total_energy > 0 else 0.0

        return {
            "peaks": [
                {
                    "scale_hz": round(p.scale, 2),
                    "amplitude": round(p.amplitude, 6),
                    "q_factor": round(p.q_factor, 2)
                }
                for p in peaks
            ],
            "anomalies": anomalies,
            "anomaly_score": round(anomaly_score, 6),
            "fitted_slope": round(slope, 4),
            "n_bands": len(band_energy),
            "threshold": round(PHI_INV_9 * 10, 6)
        }

    def detect_injection(self, freqs: List[float], amps: List[float],
                         baseline_amps: Optional[List[float]] = None) -> Dict:
        """
        Detect energy injections — frequencies that appear in the
        current signal but not in the baseline (or that exceed
        baseline by > φ⁻⁹ * 100%).

        This is the operational equivalent of "trojan detection":
        finding unexpected structure in a signal.
        """
        if baseline_amps is None:
            # No baseline: use power-law expectation as baseline
            return self.analyze(freqs, amps)

        if len(freqs) != len(amps) or len(freqs) != len(baseline_amps):
            raise ValueError("freqs, amps, baseline_amps must match")

        injections = []
        for f, a, b in zip(freqs, amps, baseline_amps):
            if b <= 0:
                b = 1e-12
            ratio = a / b
            # GR-4: the gate is ratio > 2.3156, i.e. the current bin must
            # exceed the baseline by phi^-9 * 100 % = 131.6 %. An earlier
            # comment here read '> ~1.315x baseline', low by 1.76x.
            if ratio > (1.0 + PHI_INV_9 * 100):
                injections.append({
                    "freq_hz": round(f, 2),
                    "amplitude": round(a, 6),
                    "baseline": round(b, 6),
                    "ratio": round(ratio, 4),
                    "excess_db": round(20 * math.log10(ratio), 2)
                })

        return {
            "injections": injections,
            "n_injections": len(injections),
            "injection_score": len(injections) / len(freqs) if freqs else 0.0,
            "threshold_ratio": round(1.0 + PHI_INV_9 * 100, 4)
        }


# ---------------------------------------------------------------------
# MEASUREMENTS  --  the audit header's numbers, on demand
# ---------------------------------------------------------------------

def edges_are_monotonic(r: "MultiScaleResonance" = None):
    """GR-1. Return (ok, reversed_indices, dead_bands) for the band edges."""
    r = r or MultiScaleResonance()
    e = r.band_edges
    bad = [i for i in range(len(e) - 1) if e[i] >= e[i + 1]]
    return (not bad, bad, [(e[i], e[i + 1]) for i in bad])


def band_resolution_is_honoured():
    """GR-2. True if bands_per_octave changes anything. It does not."""
    a = MultiScaleResonance(bands_per_octave=1).band_edges
    b = MultiScaleResonance(bands_per_octave=64).band_edges
    return a != b


def fit_includes_peaks():
    """GR-3. True when the power-law fit is built from every populated band,
    peaks included, contradicting the comment above it."""
    import inspect
    body = inspect.getsource(MultiScaleResonance.analyze).split('"""')[2]
    return ("if band_count[i] > 0:" in body
            and "non-peak" in inspect.getsource(MultiScaleResonance.analyze))


def injection_false_alarm_rate(n_bins: int = 4096, trials: int = 40,
                               seed: int = 1) -> float:
    """GR-5. Fraction of bins flagged when both series are independent draws
    of the same noise process -- i.e. when there is nothing to find.

    Rayleigh amplitudes, which is what the magnitude of a complex Gaussian
    spectrum has. No injection is present in any trial.
    """
    import random
    rng = random.Random(seed)
    r = MultiScaleResonance()
    freqs = [float(i + 1) for i in range(n_bins)]

    def draw():
        return math.sqrt(-2.0 * math.log(rng.random()))

    total = 0.0
    for _ in range(trials):
        a = [draw() for _ in range(n_bins)]
        b = [draw() for _ in range(n_bins)]
        total += r.detect_injection(freqs, a, b)["injection_score"]
    return total / trials


def injection_return_shapes():
    """GR-6. The key sets returned with and without a baseline."""
    r = MultiScaleResonance()
    return (sorted(r.detect_injection([1.0], [1.0], [1.0])),
            sorted(r.detect_injection([1.0], [1.0], None)))
