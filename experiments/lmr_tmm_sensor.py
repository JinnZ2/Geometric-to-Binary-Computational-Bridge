"""
Compact Baseline LMR Sensor via Fresnel / Transfer-Matrix Recursion
==================================================================

This file is the repository's **baseline physical optics experiment** for the
LMR thread. It is intentionally compact and is meant for qualitative
exploration, not for device calibration or performance claims.

Model status
------------

This script should be interpreted as a **small, semi-physical baseline**. It
captures p-polarized multilayer interference with a lossy TiO2 film and a PSS
biolayer, but it still uses simplified dispersion, fixed geometry, and a small
set of layers. The printed sensitivity numbers are therefore best treated as a
visual demonstration that surrounding-index perturbations can shift a modeled
resonance, not as validated sensor specifications.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


class LMRSensor:
    """
    Compact LMR sensor simulator using TM Fresnel recursion.

    The lossy channel is encoded in the imaginary part of the TiO2 refractive
    index. The surrounding refractive index enters explicitly through the final
    boundary condition, which makes the example suitable for qualitative
    refractive-index sensitivity demonstrations.
    """

    def __init__(self, wavelength_range: tuple[float, float] = (400, 2000), points: int = 2000):
        self.wavelengths = np.linspace(wavelength_range[0], wavelength_range[1], points)
        self.theta = np.radians(75.0)

    def refractive_index_tio2(self, wavelength_nm: float) -> complex:
        """Approximate TiO2 dispersion with a lossy extinction term."""
        wl_um = wavelength_nm / 1000.0
        a1, a2, a3 = 4.896, 0.244, 0.197
        b1, b2, b3 = 0.048, 0.076, 13.0
        n_real = np.sqrt(
            1.0
            + a1 * wl_um**2 / (wl_um**2 - b1)
            + a2 * wl_um**2 / (wl_um**2 - b2)
            + a3 * wl_um**2 / (wl_um**2 - b3)
        )
        k_ext = 0.008 + 0.002 * np.exp(-((wl_um - 0.8) ** 2) / 0.1)
        return n_real + 1j * k_ext

    def refractive_index_pss(self, wavelength_nm: float) -> complex:
        """Approximate dispersion for a thin PSS biolayer."""
        wl_um = wavelength_nm / 1000.0
        n_real = 1.48 + 0.01 / (wl_um + 0.1)
        k_ext = 1e-4
        return n_real + 1j * k_ext

    def refractive_index_surrounding(self, wavelength_nm: float, analyte_ri: float = 1.33) -> complex:
        """Surrounding medium such as water with a refractive-index perturbation."""
        _ = wavelength_nm
        return analyte_ri + 0j

    def refractive_index_fiber_core(self, wavelength_nm: float) -> complex:
        """Approximate fused-silica fiber-core refractive index."""
        wl_um = wavelength_nm / 1000.0
        n_real = np.sqrt(
            1.0
            + 0.6961663 * wl_um**2 / (wl_um**2 - 0.0684043**2)
            + 0.4079426 * wl_um**2 / (wl_um**2 - 0.1162414**2)
            + 0.8974794 * wl_um**2 / (wl_um**2 - 9.896161**2)
        )
        return n_real + 0j

    def layer_admittance(self, n_medium: complex, beta_parallel: complex, wavelength_nm: float, polarization: str = "TM") -> complex:
        """Return the optical admittance-like term for the chosen polarization."""
        k0 = 2.0 * np.pi / wavelength_nm
        kz = k0 * np.sqrt(n_medium**2 - beta_parallel**2)
        if np.imag(kz) < 0:
            kz = -kz

        if polarization == "TM":
            return kz / (n_medium**2)
        if polarization == "TE":
            return kz
        raise ValueError(f"Unsupported polarization: {polarization}")

    def layer_phase(self, n_medium: complex, thickness_nm: float, beta_parallel: complex, wavelength_nm: float) -> complex:
        """Phase accumulation through a layer."""
        k0 = 2.0 * np.pi / wavelength_nm
        kz = k0 * np.sqrt(n_medium**2 - beta_parallel**2)
        if np.imag(kz) < 0:
            kz = -kz
        return kz * thickness_nm

    @staticmethod
    def fresnel_reflection(q_left: complex, q_right: complex) -> complex:
        """Interface reflection coefficient expressed through optical admittances."""
        return (q_left - q_right) / (q_left + q_right)

    def calculate_reflectance(
        self,
        layer_stack: list[dict[str, float | str]],
        polarization: str = "TM",
        analyte_ri: float = 1.33,
    ) -> np.ndarray:
        """Evaluate reflectance across the wavelength sweep."""
        reflectance = np.zeros(len(self.wavelengths), dtype=float)

        for i, wavelength_nm in enumerate(self.wavelengths):
            n_core = self.refractive_index_fiber_core(wavelength_nm)
            n_surr = self.refractive_index_surrounding(wavelength_nm, analyte_ri)
            beta_parallel = n_core * np.sin(self.theta)

            media = [n_core]
            phases = []
            for layer in layer_stack:
                material = layer["material"]
                if material == "TiO2":
                    n_layer = self.refractive_index_tio2(wavelength_nm)
                elif material == "PSS":
                    n_layer = self.refractive_index_pss(wavelength_nm)
                else:
                    raise ValueError(f"Unknown material: {material}")
                media.append(n_layer)
                phases.append(self.layer_phase(n_layer, float(layer["thickness_nm"]), beta_parallel, wavelength_nm))
            media.append(n_surr)

            q_values = [self.layer_admittance(n_medium, beta_parallel, wavelength_nm, polarization) for n_medium in media]
            r_interfaces = [self.fresnel_reflection(q_values[j], q_values[j + 1]) for j in range(len(media) - 1)]

            n_layers = len(layer_stack)
            r_eff = r_interfaces[n_layers]
            for j in range(n_layers - 1, -1, -1):
                phase_factor = np.exp(2j * phases[j])
                r_eff = (r_interfaces[j] + r_eff * phase_factor) / (1.0 + r_interfaces[j] * r_eff * phase_factor)

            reflectance[i] = np.abs(r_eff) ** 2

        return reflectance

    def find_resonance_dip(self, reflectance: np.ndarray) -> dict[str, float]:
        """Locate the dominant resonance dip and estimate simple metrics."""
        min_idx = int(np.argmin(reflectance))
        dip_wavelength = float(self.wavelengths[min_idx])
        dip_depth = float(1.0 - reflectance[min_idx])

        half_level = reflectance[min_idx] + 0.5 * (np.max(reflectance) - reflectance[min_idx])
        left_idx = min_idx
        while left_idx > 0 and reflectance[left_idx] < half_level:
            left_idx -= 1
        right_idx = min_idx
        while right_idx < len(self.wavelengths) - 1 and reflectance[right_idx] < half_level:
            right_idx += 1
        fwhm = float(self.wavelengths[right_idx] - self.wavelengths[left_idx]) if right_idx > left_idx else 0.0

        return {
            "wavelength": dip_wavelength,
            "depth": dip_depth,
            "fwhm": fwhm,
            "q_factor": float(dip_wavelength / fwhm) if fwhm > 0 else float("inf"),
        }


def run_simulation(save_figure: bool = True) -> None:
    """
    Run a baseline/analyte comparison and visualize the spectrum.

    The demonstration uses a slightly thicker TiO2 layer and a modest surrounding
    refractive-index perturbation so that the modeled resonance shift is visible
    without claiming that the chosen geometry is optimized.
    """
    sensor = LMRSensor(wavelength_range=(800, 1800), points=2400)
    layer_stack = [
        {"material": "TiO2", "thickness_nm": 220.0},
        {"material": "PSS", "thickness_nm": 30.0},
    ]
    baseline_ri = 1.330
    analyte_ri = 1.340

    reflectance_baseline = sensor.calculate_reflectance(layer_stack, analyte_ri=baseline_ri)
    reflectance_analyte = sensor.calculate_reflectance(layer_stack, analyte_ri=analyte_ri)

    dip_baseline = sensor.find_resonance_dip(reflectance_baseline)
    dip_analyte = sensor.find_resonance_dip(reflectance_analyte)
    spectral_shift = dip_analyte["wavelength"] - dip_baseline["wavelength"]
    depth_change = dip_analyte["depth"] - dip_baseline["depth"]
    sensitivity = spectral_shift / (analyte_ri - baseline_ri)

    print("=" * 60)
    print("COMPACT LMR BASELINE SIMULATION")
    print("=" * 60)
    print("Interpretation: qualitative baseline only, not a calibrated sensor claim.")
    print(f"Layer stack: TiO2 {layer_stack[0]['thickness_nm']:.0f} nm / PSS {layer_stack[1]['thickness_nm']:.0f} nm")
    print(f"Baseline Dip: {dip_baseline['wavelength']:.2f} nm, depth {dip_baseline['depth']:.4f}, FWHM {dip_baseline['fwhm']:.2f} nm")
    print(f"Analyte Dip:  {dip_analyte['wavelength']:.2f} nm, depth {dip_analyte['depth']:.4f}, FWHM {dip_analyte['fwhm']:.2f} nm")
    print(f"Spectral Shift: {spectral_shift:.3f} nm for Δn = {analyte_ri - baseline_ri:.3f}")
    print(f"Approximate modeled sensitivity: {sensitivity:.1f} nm / RIU")
    print(f"Depth change: {depth_change:.4f}")
    print(f"Baseline Q-Factor: {dip_baseline['q_factor']:.1f}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(sensor.wavelengths, reflectance_baseline, label=f"Baseline (n = {baseline_ri:.3f})")
    ax.plot(sensor.wavelengths, reflectance_analyte, linestyle="--", label=f"Perturbed surrounding (n = {analyte_ri:.3f})")
    ax.axvline(dip_baseline["wavelength"], color="tab:blue", alpha=0.3)
    ax.axvline(dip_analyte["wavelength"], color="tab:orange", alpha=0.3)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Reflectance")
    ax.set_title("Compact LMR Baseline: Surrounding-Index-Induced Shift")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_figure:
        output_path = Path(__file__).with_name("lmr_tmm_sensor_example.png")
        fig.savefig(output_path, dpi=160)
        print(f"Saved example figure to: {output_path}")

    plt.show()


if __name__ == "__main__":
    run_simulation()
