"""
acoustic_fret.py – Acoustic control of FRET via distance modulation.
- Time-dependent r(t) from surface acoustic waves (SAW) or bulk resonators.
- Parametric enhancement of average efficiency.
- Phononic bandgap engineering for selective mode damping.
"""

import numpy as np
from scipy.integrate import quad
from fret_core import E_FRET, k_FRET

class AcousticModulator:
    """
    Models FRET under periodic distance modulation.
    r(t) = r0 + A * sin(2π f t + φ)
    """
    def __init__(self, r0: float, amplitude: float, frequency: float, R0: float, tau_D: float = 2.5):
        """
        Parameters
        ----------
        r0 : float
            Mean donor-acceptor distance (nm).
        amplitude : float
            Oscillation amplitude (nm).
        frequency : float
            Acoustic frequency (MHz).
        R0 : float
            Förster radius (nm).
        tau_D : float
            Donor lifetime (ns).
        """
        self.r0 = r0
        self.A = amplitude
        self.f = frequency  # MHz
        self.R0 = R0
        self.tau_D = tau_D
        self.omega = 2 * np.pi * frequency  # rad/μs (if f in MHz)

    def r_t(self, t: float) -> float:
        """Instantaneous distance at time t (μs)."""
        return self.r0 + self.A * np.sin(self.omega * t)

    def k_inst(self, t: float) -> float:
        """Instantaneous FRET rate at time t."""
        r = self.r_t(t)
        return k_FRET(r, self.R0, self.tau_D)

    def E_inst(self, t: float) -> float:
        """Instantaneous FRET efficiency."""
        r = self.r_t(t)
        return E_FRET(r, self.R0)

    def average_efficiency(self, n_cycles: int = 10) -> float:
        """
        Time-averaged efficiency over multiple acoustic cycles.
        Uses numerical integration.
        """
        period = 1.0 / self.f  # μs
        T = n_cycles * period

        def integrand(t):
            return self.E_inst(t)

        avg_E, _ = quad(integrand, 0, T, limit=100)
        return avg_E / T

    def average_rate(self, n_cycles: int = 10) -> float:
        """Time-averaged FRET rate."""
        period = 1.0 / self.f
        T = n_cycles * period

        def integrand(t):
            return self.k_inst(t)

        avg_k, _ = quad(integrand, 0, T, limit=100)
        return avg_k / T

    def enhancement_factor(self, n_cycles: int = 10) -> float:
        """Ratio of average efficiency to static efficiency at r0."""
        E_static = E_FRET(self.r0, self.R0)
        E_avg = self.average_efficiency(n_cycles)
        return E_avg / E_static

    def parametric_gain_curve(self, A_range: tuple = (0, 1.0), num_points: int = 50):
        """
        Compute enhancement factor vs. amplitude.
        Returns amplitudes and enhancement factors.
        """
        A_vals = np.linspace(A_range[0], A_range[1], num_points)
        gains = []
        orig_A = self.A
        for A in A_vals:
            self.A = A
            gains.append(self.enhancement_factor())
        self.A = orig_A
        return A_vals, np.array(gains)


class PhononicBandgapCage:
    """
    Models suppression of specific acoustic modes via a phononic crystal.
    Allows selective damping of thermal vibrations while permitting coherent drive.
    """
    def __init__(self, center_freq: float, gap_width: float, suppression_db: float = 40.0):
        """
        Parameters
        ----------
        center_freq : float
            Center frequency of the phononic bandgap (MHz).
        gap_width : float
            Width of the bandgap (MHz).
        suppression_db : float
            Suppression of vibrational density of states inside gap (dB).
        """
        self.f0 = center_freq
        self.df = gap_width
        self.suppression = 10**(-suppression_db / 20)  # amplitude suppression factor

    def transmission(self, f: float) -> float:
        """
        Amplitude transmission factor at frequency f (MHz).
        Approximates bandstop filter.
        """
        if abs(f - self.f0) < self.df / 2:
            return self.suppression
        else:
            return 1.0

    def effective_amplitude(self, f_drive: float, A_nominal: float) -> float:
        """
        Reduced amplitude if drive frequency falls in bandgap.
        """
        return A_nominal * self.transmission(f_drive)

    def thermal_jitter_reduction(self, sigma_r_thermal: float) -> float:
        """
        Estimate reduction in thermal position jitter by integrating
        over suppressed phonon spectrum. Simplified: use bandgap suppression.
        """
        # Assume thermal motion is broadband; bandgap removes fraction of spectrum
        fraction_suppressed = self.df / (2 * self.f0)  # crude
        return sigma_r_thermal * (1 - fraction_suppressed * (1 - self.suppression))


def saw_fret_efficiency(r0, R0, A, f, tau_D=2.5, k_rad=0.1, k_nr=0.05):
    """
    Convenience function for quick SAW-FRET efficiency estimate.
    Returns time-averaged efficiency including radiative/non-radiative losses.
    """
    mod = AcousticModulator(r0, A, f, R0, tau_D)
    k_avg = mod.average_rate()
    return k_avg / (k_avg + k_rad + k_nr)
