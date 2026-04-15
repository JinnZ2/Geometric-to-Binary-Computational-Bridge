"""
Ohmic Damping and Stochastic Resonance Simulation
================================================

This file is the repository's **conceptual entry-point** for the recent LMR
thread. It explores a deliberately simplified lossy-resonance model in which
ohmic damping broadens an LMR-style transmission dip while also introducing
measurement noise. A weak signal shift is then assessed probabilistically
through repeated noisy sampling.

Model status
------------

This script is best read as a **toy mechanism sketch**. It is useful for
building intuition about how loss, noise, and probabilistic detection can be
coupled, but it is not a full optical model and should not be interpreted as a
calibrated prediction for a physical sensor.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm


def lmr_transmission(wavelength: np.ndarray, damping_factor: float) -> np.ndarray:
    """
    Model a simplified lossy LMR transmission dip.

    Higher damping broadens the resonance and increases the full width at half
    maximum of the dip.
    """
    resonance_wl = 1550.0  # nm
    width = 5.0 + 20.0 * damping_factor
    return 1.0 - (width**2 / ((wavelength - resonance_wl) ** 2 + width**2))


def detection_probability(
    signal_shift: float,
    damping_factor: float,
    samples: int = 1000,
    rng: np.random.Generator | None = None,
) -> float:
    """
    Estimate weak-signal detection probability under damping-induced noise.

    The measurement noise scales with the damping factor, loosely inspired by a
    Johnson-Nyquist-style intuition for noisy dissipative systems.
    """
    if rng is None:
        rng = np.random.default_rng()

    noise_std = 0.5 * damping_factor
    base_signal = 0.0
    shifted_signal = signal_shift

    if noise_std <= 0:
        return float(shifted_signal > base_signal)

    base_measurements = rng.normal(base_signal, noise_std, samples)
    shifted_measurements = rng.normal(shifted_signal, noise_std, samples)

    threshold = float(np.mean(base_measurements) + 1.0 * noise_std)
    prob_detection = np.sum(shifted_measurements > threshold) / samples
    return float(prob_detection)


def analytical_detection_probability(signal_shift: float, damping_factor: float) -> float:
    """
    Analytical Gaussian approximation for the same threshold detection rule.
    """
    noise_std = 0.5 * damping_factor
    base_signal = 0.0

    if noise_std <= 0:
        return float(signal_shift > base_signal)

    threshold = base_signal + 1.0 * noise_std
    z_score = (threshold - signal_shift) / noise_std
    return float(1.0 - norm.cdf(z_score))


def run_simulation(
    samples: int = 1000,
    signal_shift: float = 0.8,
    seed: int = 42,
    save_figure: bool = True,
) -> None:
    """
    Run the damping sweep and visualize both resonance broadening and
    probabilistic detection performance.
    """
    rng = np.random.default_rng(seed)

    damping_range = np.linspace(0.01, 1.0, 20)
    wavelengths = np.linspace(1500.0, 1600.0, 1000)

    simulated_probabilities = [
        detection_probability(signal_shift, damping, samples=samples, rng=rng)
        for damping in damping_range
    ]
    analytical_probabilities = [
        analytical_detection_probability(signal_shift, damping)
        for damping in damping_range
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for damping in (0.05, 0.25, 0.5, 1.0):
        axes[0].plot(
            wavelengths,
            lmr_transmission(wavelengths, damping),
            label=f"damping={damping:.2f}",
        )
    axes[0].set_xlabel("Wavelength (nm)")
    axes[0].set_ylabel("Transmission")
    axes[0].set_title("Ohmic Damping Broadens the LMR Dip")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(
        damping_range,
        simulated_probabilities,
        marker="o",
        label="Monte Carlo estimate",
    )
    axes[1].plot(
        damping_range,
        analytical_probabilities,
        linestyle="--",
        label="Analytical Gaussian estimate",
    )
    axes[1].set_xlabel("Ohmic Damping Factor (Loss)")
    axes[1].set_ylabel("Probability of Information Detection")
    axes[1].set_title("Stochastic Resonance: Loss and Weak-Signal Detection")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()

    if save_figure:
        output_path = Path(__file__).with_name("ohmic_stochastic_resonance_example.png")
        fig.savefig(output_path, dpi=160)
        print(f"Saved example figure to: {output_path}")

    plt.show()


if __name__ == "__main__":
    run_simulation()
