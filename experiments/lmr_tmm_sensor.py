"""
Lossy Mode Resonance Sensor via Transfer Matrix Method
======================================================

This experiment models a simple TiO2/PSS LMR sensor using a transfer-matrix
approach. The imaginary part of the refractive index represents ohmic damping,
which broadens the resonance and influences the detectable spectral shift when
an analyte perturbs the surrounding refractive index.
"""

import numpy as np
import matplotlib.pyplot as plt


class LMRSensor:
    """
    Lossy Mode Resonance sensor simulator using a transfer-matrix method.

    The loss channel is encoded in the imaginary part of the refractive index.
    """

    def __init__(self, wavelength_range: tuple[float, float] = (400, 2000), points: int = 2000):
        self.wavelengths = np.linspace(wavelength_range[0], wavelength_range[1], points)
        self.theta = np.radians(75.0)

    def refractive_index_tio2(self, wavelength_nm: float) -> complex:
        """
        Approximate TiO2 dispersion with an adjustable imaginary part.
        """
        wl_um = wavelength_nm / 1000.0

        a1, a2, a3 = 4.896, 0.244, 0.197
        b1, b2, b3 = 0.048, 0.076, 13.0
        n_real = np.sqrt(
            1
            + a1 * wl_um**2 / (wl_um**2 - b1)
            + a2 * wl_um**2 / (wl_um**2 - b2)
            + a3 * wl_um**2 / (wl_um**2 - b3)
        )

        k_ext = 0.008 + 0.002 * np.exp(-((wl_um - 0.8) ** 2) / 0.1)
        return n_real + 1j * k_ext

    def refractive_index_pss(self, wavelength_nm: float) -> complex:
        """Approximate dispersion for a PSS biolayer."""
        wl_um = wavelength_nm / 1000.0
        n_real = 1.48 + 0.01 / (wl_um + 0.1)
        k_ext = 0.0001
        return n_real + 1j * k_ext

    def refractive_index_surrounding(self, wavelength_nm: float, analyte_ri: float = 1.33) -> complex:
        """Surrounding medium such as water with an analyte perturbation."""
        _ = wavelength_nm
        return analyte_ri + 0j

    def refractive_index_fiber_core(self, wavelength_nm: float) -> complex:
        """Approximate fused-silica fiber-core refractive index."""
        wl_um = wavelength_nm / 1000.0
        n_real = np.sqrt(
            1
            + 0.6961663 * wl_um**2 / (wl_um**2 - 0.0684043**2)
            + 0.4079426 * wl_um**2 / (wl_um**2 - 0.1162414**2)
            + 0.8974794 * wl_um**2 / (wl_um**2 - 9.896161**2)
        )
        return n_real + 0j

    def transfer_matrix_layer(
        self,
        n_layer: complex,
        n_substrate: complex,
        thickness_nm: float,
        wavelength_nm: float,
        polarization: str = "TM",
    ) -> tuple[np.ndarray, complex]:
        """Calculate the transfer matrix for a single layer."""
        theta_t = np.arcsin(n_substrate * np.sin(self.theta) / n_layer)
        kz = (2.0 * np.pi / wavelength_nm) * n_layer * np.cos(theta_t)

        if polarization == "TM":
            q = (n_layer**2) / kz
            q_sub = (n_substrate**2) / ((2.0 * np.pi / wavelength_nm) * n_substrate * np.cos(self.theta))
        else:
            q = kz
            q_sub = (2.0 * np.pi / wavelength_nm) * n_substrate * np.cos(self.theta)

        delta = kz * thickness_nm
        matrix = np.array(
            [
                [np.cos(delta), -1j / q * np.sin(delta)],
                [-1j * q * np.sin(delta), np.cos(delta)],
            ],
            dtype=complex,
        )
        return matrix, q_sub

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
            q_0 = (2.0 * np.pi / wavelength_nm) * n_core * np.cos(self.theta)

            total_matrix = np.eye(2, dtype=complex)
            n_current = n_core

            for layer in layer_stack:
                material = layer["material"]
                if material == "TiO2":
                    n_layer = self.refractive_index_tio2(wavelength_nm)
                elif material == "PSS":
                    n_layer = self.refractive_index_pss(wavelength_nm)
                else:
                    raise ValueError(f"Unknown material: {material}")

                thickness_nm = float(layer["thickness_nm"])
                layer_matrix, _ = self.transfer_matrix_layer(
                    n_layer,
                    n_current,
                    thickness_nm,
                    wavelength_nm,
                    polarization,
                )
                total_matrix = total_matrix @ layer_matrix
                n_current = n_layer

            _, q_n = self.transfer_matrix_layer(n_surr, n_current, 0.0, wavelength_nm, polarization)
            numerator = (total_matrix[0, 0] + total_matrix[0, 1] * q_n) * q_0 - (
                total_matrix[1, 0] + total_matrix[1, 1] * q_n
            )
            denominator = (total_matrix[0, 0] + total_matrix[0, 1] * q_n) * q_0 + (
                total_matrix[1, 0] + total_matrix[1, 1] * q_n
            )
            reflectance[i] = np.abs(numerator / denominator) ** 2

        return reflectance

    def find_resonance_dip(self, reflectance: np.ndarray) -> dict[str, float]:
        """Locate the dominant resonance dip and estimate simple metrics."""
        min_idx = int(np.argmin(reflectance))
        dip_wavelength = float(self.wavelengths[min_idx])
        dip_depth = float(1.0 - reflectance[min_idx])

        half_max = (1.0 + reflectance[min_idx]) / 2.0
        above = np.where(reflectance > half_max)[0]

        if len(above) >= 2:
            left_candidates = above[above < min_idx]
            right_candidates = above[above > min_idx]
            left_idx = int(left_candidates[-1]) if len(left_candidates) else 0
            right_idx = int(right_candidates[0]) if len(right_candidates) else len(self.wavelengths) - 1
            fwhm = float(self.wavelengths[right_idx] - self.wavelengths[left_idx])
        else:
            fwhm = 50.0

        return {
            "wavelength": dip_wavelength,
            "depth": dip_depth,
            "fwhm": fwhm,
            "q_factor": float(dip_wavelength / fwhm) if fwhm > 0 else 0.0,
        }


def run_simulation() -> None:
    """Run a baseline/analyte comparison and visualize the spectrum."""
    sensor = LMRSensor(wavelength_range=(600, 1800))
    layer_stack = [
        {"material": "TiO2", "thickness_nm": 120.0},
        {"material": "PSS", "thickness_nm": 15.0},
    ]

    reflectance_baseline = sensor.calculate_reflectance(layer_stack, analyte_ri=1.330)
    reflectance_analyte = sensor.calculate_reflectance(layer_stack, analyte_ri=1.335)

    dip_baseline = sensor.find_resonance_dip(reflectance_baseline)
    dip_analyte = sensor.find_resonance_dip(reflectance_analyte)

    print("=" * 50)
    print("LMR SENSOR SIMULATION RESULTS")
    print("=" * 50)
    print(
        f"Baseline Dip: {dip_baseline['wavelength']:.1f} nm, "
        f"FWHM: {dip_baseline['fwhm']:.1f} nm"
    )
    print(
        f"Analyte Dip:  {dip_analyte['wavelength']:.1f} nm, "
        f"FWHM: {dip_analyte['fwhm']:.1f} nm"
    )
    print(f"Spectral Shift: {dip_analyte['wavelength'] - dip_baseline['wavelength']:.2f} nm")
    print(f"Q-Factor (Loss Metric): {dip_baseline['q_factor']:.1f}")

    plt.figure(figsize=(10, 5))
    plt.plot(sensor.wavelengths, reflectance_baseline, label="Baseline (n = 1.330)")
    plt.plot(sensor.wavelengths, reflectance_analyte, label="Analyte (n = 1.335)", linestyle="--")
    plt.axvline(dip_baseline["wavelength"], color="tab:blue", alpha=0.3)
    plt.axvline(dip_analyte["wavelength"], color="tab:orange", alpha=0.3)
    plt.xlabel("Wavelength (nm)")
    plt.ylabel("Reflectance")
    plt.title("LMR Sensor Response from Transfer Matrix Simulation")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    run_simulation()
