"""Run the repository's LMR experiment suite with reproducible example settings.

This utility is intended as a lightweight benchmark and artifact generator for
repository readers. It executes the four LMR-related scripts with fixed seeds
and reduced settings for the heaviest model so that the progression can be
checked quickly in a non-interactive environment.
"""

from __future__ import annotations

import os

os.environ.setdefault("MPLBACKEND", "Agg")

import lmr_tmm_sensor as tmm
import multi_analyte_lmr_bayesian as multi
import ohmic_stochastic_resonance as ohmic
import quantum_fisher_ml_deconvolution as qfi


def main() -> None:
    """Execute the LMR experiment ladder and save example figures."""
    print("=" * 72)
    print("LMR SUITE BENCHMARK")
    print("=" * 72)
    print("This runner executes the repository's LMR examples with reproducible settings.")

    print("\n[1/4] Conceptual ohmic stochastic-resonance sketch")
    ohmic.run_simulation(samples=300, signal_shift=0.8, seed=42, save_figure=True)

    print("\n[2/4] Compact transfer-matrix baseline")
    tmm.run_simulation(save_figure=True)

    print("\n[3/4] Multi-analyte optics-plus-inference sandbox")
    multi.run_simulation(save_figure=True)

    print("\n[4/4] QFI and estimator comparison with reduced runtime settings")
    qfi.run_simulation(dataset_size=240, training_epochs=4, wavelength_points=120, seed=42, save_figure=True)

    print("\nBenchmark complete. Example figures were saved next to the scripts.")


if __name__ == "__main__":
    main()
