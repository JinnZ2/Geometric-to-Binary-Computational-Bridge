"""
Multi-Analyte LMR Sensor with Temperature-Dependent Damping
===========================================================

This experiment extends the repository's lossy-mode-resonance simulations into
an integrated workflow that combines three elements:

1. a multi-analyte LMR spectrum model,
2. temperature-dependent ohmic damping in the lossy TiO2 layer, and
3. a Bayesian diagnostic stage that maps biomarker-like measurements to simple
   disease hypotheses.

The model is intentionally exploratory rather than clinically validated. Its
purpose is to provide a self-contained computational experiment inside the
repository's `experiments` collection.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks, peak_widths
from scipy.stats import multivariate_normal

warnings.filterwarnings("ignore")


@dataclass
class Analyte:
    """Biomarker-like analyte with simple optical and thermal properties."""

    name: str
    refractive_index: float
    molecular_weight: float  # kDa
    binding_affinity: float  # K_d in nM
    thermal_expansion_coeff: float  # dn/dT
    concentration_range: Tuple[float, float] = (0.0, 100.0)


class MultiAnalyteLMRSensor:
    """
    Multi-analyte LMR sensor with temperature-dependent ohmic damping.

    The optical model is a compact transfer-matrix approximation intended for
    qualitative experimentation and visualization.
    """

    def __init__(self, wavelength_range: Tuple[float, float] = (400, 2000), points: int = 2000):
        self.wavelengths = np.linspace(wavelength_range[0], wavelength_range[1], points)
        self.theta = np.radians(75.0)
        self.temperature = 298.15
        self.analytes = {
            "CRP": Analyte("C-Reactive Protein", 1.42, 115.0, 5.0, 1.8e-4),
            "IL6": Analyte("Interleukin-6", 1.38, 21.0, 2.0, 1.5e-4),
            "PSA": Analyte("Prostate Specific Antigen", 1.45, 28.0, 3.0, 1.9e-4),
            "TNFa": Analyte("Tumor Necrosis Factor Alpha", 1.40, 17.0, 1.5, 1.6e-4),
            "BNP": Analyte("Brain Natriuretic Peptide", 1.43, 3.5, 4.0, 1.7e-4),
        }
        self._calibration_cache: Dict[str, Dict[str, np.ndarray]] = {}

    def effective_refractive_index(self, base_ri: float, bound_analytes: Dict[str, float]) -> float:
        """Lorentz-Lorenz effective-medium approximation for mixed analytes."""
        if not bound_analytes:
            return base_ri

        def ll_term(n_value: float) -> float:
            return (n_value**2 - 1.0) / (n_value**2 + 2.0)

        ll_base = ll_term(base_ri)
        ll_mixture = ll_base

        for name, fraction in bound_analytes.items():
            if name in self.analytes:
                n_analyte = self.analytes[name].refractive_index
                ll_mixture += fraction * (ll_term(n_analyte) - ll_base)

        if np.isclose(1.0 - ll_mixture, 0.0):
            return base_ri

        n_eff = np.sqrt((1.0 + 2.0 * ll_mixture) / (1.0 - ll_mixture))
        return float(np.real(n_eff))

    def temperature_dependent_ohmic_damping(self, wavelength_nm: float, temperature: float) -> float:
        """
        Model temperature-dependent ohmic damping in the lossy layer.

        The expression combines a baseline loss term with phonon, Urbach-tail,
        and carrier-absorption style corrections.
        """
        t_ref = 298.15
        wl_um = wavelength_nm / 1000.0

        k0 = 0.005 + 0.003 * np.exp(-((wl_um - 0.8) ** 2) / 0.15)
        phonon_factor = 1.0 + 0.002 * (temperature - t_ref)

        e_g = 3.2
        e_photon = 1.24 / wl_um
        urbach_energy = 0.05 * (temperature / t_ref)
        if e_photon < e_g:
            urbach_factor = 1.0 + 0.1 * np.exp((e_photon - e_g) / urbach_energy)
        else:
            urbach_factor = 1.1

        carrier_factor = 1.0 + 0.001 * (temperature / t_ref) ** 1.5
        return float(k0 * phonon_factor * urbach_factor * carrier_factor)

    def refractive_index_tio2_temperature(self, wavelength_nm: float, temperature: float = 298.15) -> complex:
        """Approximate TiO2 index with thermo-optic and loss effects."""
        wl_um = wavelength_nm / 1000.0
        a1, a2, a3 = 4.896, 0.244, 0.197
        b1, b2, b3 = 0.048, 0.076, 13.0
        n_real = np.sqrt(
            1.0
            + a1 * wl_um**2 / (wl_um**2 - b1)
            + a2 * wl_um**2 / (wl_um**2 - b2)
            + a3 * wl_um**2 / (wl_um**2 - b3)
        )
        n_real *= 1.0 + 1e-4 * (temperature - 298.15)
        k_ext = self.temperature_dependent_ohmic_damping(wavelength_nm, temperature)
        return n_real + 1j * k_ext

    def refractive_index_pss(self, wavelength_nm: float, bound_analytes: Dict[str, float] | None = None) -> complex:
        """Approximate PSS biolayer with analyte-dependent effective index."""
        wl_um = wavelength_nm / 1000.0
        base_n = 1.48 + 0.01 / (wl_um + 0.1)
        n_eff = self.effective_refractive_index(base_n, bound_analytes or {})
        return n_eff + 1j * 1e-4

    def refractive_index_fiber_core(self, wavelength_nm: float) -> complex:
        """Fused-silica fiber-core approximation."""
        wl_um = wavelength_nm / 1000.0
        n_real = np.sqrt(
            1.0
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
        """Calculate the 2x2 transfer matrix for a single layer."""
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

    def calculate_multi_analyte_spectrum(
        self,
        bound_analytes: Dict[str, float],
        temperature: float = 298.15,
        polarization: str = "TM",
    ) -> np.ndarray:
        """Calculate the reflectance spectrum for a multi-analyte sample."""
        reflectance = np.zeros(len(self.wavelengths), dtype=float)
        d_tio2 = 120.0
        d_pss = 15.0

        for i, wavelength_nm in enumerate(self.wavelengths):
            n_core = self.refractive_index_fiber_core(wavelength_nm)
            n_surr = 1.33 + 0j
            n_tio2 = self.refractive_index_tio2_temperature(wavelength_nm, temperature)
            n_pss = self.refractive_index_pss(wavelength_nm, bound_analytes)
            q_0 = (2.0 * np.pi / wavelength_nm) * n_core * np.cos(self.theta)

            matrix_tio2, _ = self.transfer_matrix_layer(n_tio2, n_core, d_tio2, wavelength_nm, polarization)
            matrix_pss, _ = self.transfer_matrix_layer(n_pss, n_tio2, d_pss, wavelength_nm, polarization)
            matrix_total = matrix_pss @ matrix_tio2
            _, q_n = self.transfer_matrix_layer(n_surr, n_pss, 0.0, wavelength_nm, polarization)

            numerator = (matrix_total[0, 0] + matrix_total[0, 1] * q_n) * q_0 - (
                matrix_total[1, 0] + matrix_total[1, 1] * q_n
            )
            denominator = (matrix_total[0, 0] + matrix_total[0, 1] * q_n) * q_0 + (
                matrix_total[1, 0] + matrix_total[1, 1] * q_n
            )
            reflectance[i] = np.abs(numerator / denominator) ** 2

        return reflectance

    def extract_multi_analyte_features(self, spectrum: np.ndarray) -> Dict[str, List[float] | int]:
        """Extract dip count, locations, depths, widths, and areas."""
        inverted = 1.0 - spectrum
        peaks, _ = find_peaks(inverted, height=0.05, distance=50)
        features: Dict[str, List[float] | int] = {
            "n_dips": int(len(peaks)),
            "dip_wavelengths": [],
            "dip_depths": [],
            "dip_fwhm": [],
            "dip_areas": [],
        }

        if len(peaks) == 0:
            return features

        widths = peak_widths(inverted, peaks, rel_height=0.5)
        wavelength_step = self.wavelengths[1] - self.wavelengths[0]

        for i, peak_idx in enumerate(peaks):
            features["dip_wavelengths"].append(float(self.wavelengths[peak_idx]))
            features["dip_depths"].append(float(inverted[peak_idx]))
            features["dip_fwhm"].append(float(widths[0][i] * wavelength_step))
            left = max(0, int(peak_idx - widths[2][i]))
            right = min(len(self.wavelengths), int(peak_idx + widths[3][i]))
            area = np.trapz(inverted[left:right], self.wavelengths[left:right]) if right > left else 0.0
            features["dip_areas"].append(float(area))

        return features

    def generate_calibration_curves(
        self,
        analyte_names: List[str],
        concentrations: np.ndarray,
        temperature: float = 298.15,
    ) -> Dict[str, Dict[str, List[float] | np.ndarray]]:
        """Generate simple concentration-response calibration curves."""
        cache_key = f"{','.join(analyte_names)}|{temperature:.2f}|{','.join(map(str, concentrations.tolist()))}"
        if cache_key in self._calibration_cache:
            return self._calibration_cache[cache_key]

        calibration: Dict[str, Dict[str, List[float] | np.ndarray]] = {
            name: {"conc": concentrations, "shift": [], "area": []} for name in analyte_names
        }

        for concentration in concentrations:
            for name in analyte_names:
                kd = self.analytes[name].binding_affinity
                fraction = concentration / (kd + concentration) * 0.1 if concentration > 0 else 0.0
                bound = {name: fraction}
                spectrum = self.calculate_multi_analyte_spectrum(bound, temperature)
                features = self.extract_multi_analyte_features(spectrum)

                if features["dip_wavelengths"]:
                    calibration[name]["shift"].append(float(features["dip_wavelengths"][0]))
                    calibration[name]["area"].append(float(features["dip_areas"][0]))
                else:
                    calibration[name]["shift"].append(np.nan)
                    calibration[name]["area"].append(np.nan)

        self._calibration_cache[cache_key] = calibration
        return calibration


class MultiAnalyteBayesianDiagnostic:
    """Simple Bayesian diagnostic model for simultaneous biomarker readings."""

    def __init__(self, analytes: List[str], disease_prevalences: Dict[str, float]):
        self.analytes = analytes
        self.diseases = list(disease_prevalences.keys())
        self.prior = disease_prevalences
        self.healthy_means = {analyte: 0.0 for analyte in analytes}
        self.healthy_cov = np.eye(len(analytes)) * 0.5
        self.disease_means: Dict[str, np.ndarray] = {}
        self.disease_covs: Dict[str, np.ndarray] = {}
        self._initialize_disease_profiles()

    def _initialize_disease_profiles(self) -> None:
        idx_map = {analyte: i for i, analyte in enumerate(self.analytes)}

        if "Inflammation" in self.diseases:
            means = np.zeros(len(self.analytes))
            if "CRP" in idx_map:
                means[idx_map["CRP"]] = 3.5
            if "IL6" in idx_map:
                means[idx_map["IL6"]] = 2.8
            if "TNFa" in idx_map:
                means[idx_map["TNFa"]] = 2.2
            self.disease_means["Inflammation"] = means
            cov = np.eye(len(self.analytes)) * 0.5
            for analyte, variance in {"CRP": 0.8, "IL6": 0.6, "TNFa": 0.5}.items():
                if analyte in idx_map:
                    cov[idx_map[analyte], idx_map[analyte]] = variance
            self.disease_covs["Inflammation"] = cov

        if "Prostate Cancer" in self.diseases:
            means = np.zeros(len(self.analytes))
            if "PSA" in idx_map:
                means[idx_map["PSA"]] = 4.2
            if "CRP" in idx_map:
                means[idx_map["CRP"]] = 1.5
            self.disease_means["Prostate Cancer"] = means
            self.disease_covs["Prostate Cancer"] = np.eye(len(self.analytes)) * 0.7

        if "Heart Failure" in self.diseases:
            means = np.zeros(len(self.analytes))
            if "BNP" in idx_map:
                means[idx_map["BNP"]] = 5.0
            self.disease_means["Heart Failure"] = means
            self.disease_covs["Heart Failure"] = np.eye(len(self.analytes)) * 0.9

    def temperature_dependent_covariance(self, base_cov: np.ndarray, temperature: float) -> np.ndarray:
        """Scale covariance with a simple temperature-dependent noise model."""
        t_ref = 298.15
        adjusted = base_cov.copy().astype(float)
        diagonal_scale = 1.0 + 0.1 * (temperature - t_ref) / t_ref
        for i in range(len(adjusted)):
            adjusted[i, i] *= diagonal_scale
        return adjusted

    def likelihood_healthy(self, measurements: np.ndarray, temperature: float) -> float:
        cov = self.temperature_dependent_covariance(self.healthy_cov, temperature)
        means = np.array([self.healthy_means[analyte] for analyte in self.analytes])
        return float(multivariate_normal.pdf(measurements, mean=means, cov=cov, allow_singular=True))

    def likelihood_disease(self, measurements: np.ndarray, disease: str, temperature: float) -> float:
        if disease not in self.disease_means:
            return 0.0
        cov = self.temperature_dependent_covariance(self.disease_covs[disease], temperature)
        means = self.disease_means[disease]
        if len(measurements) != len(means):
            return 0.0
        return float(multivariate_normal.pdf(measurements, mean=means, cov=cov, allow_singular=True))

    def posterior_diseases(self, measurements: Dict[str, float], temperature: float) -> Dict[str, float]:
        """Compute posterior probabilities over diseases and the healthy state."""
        measurement_array = np.array([measurements.get(analyte, 0.0) for analyte in self.analytes])
        healthy_prior = max(0.0, 1.0 - sum(self.prior.values()))

        evidence = 0.0
        likelihoods: Dict[str, float] = {}
        healthy_likelihood = self.likelihood_healthy(measurement_array, temperature)
        evidence += healthy_likelihood * healthy_prior

        for disease in self.diseases:
            likelihood = self.likelihood_disease(measurement_array, disease, temperature)
            likelihoods[disease] = likelihood
            evidence += likelihood * self.prior[disease]

        if evidence <= 0:
            fallback = dict(self.prior)
            fallback["Healthy"] = healthy_prior
            return fallback

        posteriors = {
            disease: (likelihoods[disease] * self.prior[disease]) / evidence for disease in self.diseases
        }
        posteriors["Healthy"] = (healthy_likelihood * healthy_prior) / evidence
        return posteriors

    def differential_diagnosis(
        self,
        measurements: Dict[str, float],
        temperature: float,
        threshold: float = 0.1,
    ) -> List[Tuple[str, float]]:
        """Rank states by posterior probability and keep those above threshold."""
        posteriors = self.posterior_diseases(measurements, temperature)
        ranked = sorted(posteriors.items(), key=lambda item: item[1], reverse=True)
        return [(name, probability) for name, probability in ranked if probability > threshold]

    def information_gain(self, measurements: Dict[str, float], temperature: float) -> float:
        """KL-like information gain from prior to posterior."""
        posteriors = self.posterior_diseases(measurements, temperature)
        prior_distribution = dict(self.prior)
        prior_distribution["Healthy"] = max(0.0, 1.0 - sum(self.prior.values()))

        kl_value = 0.0
        for state, prior_probability in prior_distribution.items():
            posterior_probability = posteriors.get(state, 0.0)
            if prior_probability > 0 and posterior_probability > 0:
                kl_value += posterior_probability * np.log2(posterior_probability / prior_probability)
        return float(kl_value)


def run_simulation() -> None:
    """Run the full multi-analyte optical and Bayesian demonstration."""
    print("=" * 70)
    print("MULTI-ANALYTE LMR SENSOR WITH TEMPERATURE-DEPENDENT DAMPING")
    print("=" * 70)

    sensor = MultiAnalyteLMRSensor(wavelength_range=(600, 1800))

    print("\n" + "-" * 50)
    print("TEMPERATURE-DEPENDENT OHMIC DAMPING")
    print("-" * 50)

    temperatures = [280, 298, 310, 330, 350]
    test_wavelengths = [800, 1200, 1600]
    print("\nOhmic Damping k_ext at different temperatures:")
    print(f"{'T (K)':<8} {'800 nm':<12} {'1200 nm':<12} {'1600 nm':<12}")
    print("-" * 44)
    for temperature in temperatures:
        k_values = [sensor.temperature_dependent_ohmic_damping(wl, temperature) for wl in test_wavelengths]
        print(f"{temperature:<8} {k_values[0]:<12.6f} {k_values[1]:<12.6f} {k_values[2]:<12.6f}")

    print("\n" + "-" * 50)
    print("MULTI-ANALYTE CALIBRATION CURVES")
    print("-" * 50)

    analytes_to_calibrate = ["CRP", "IL6", "PSA"]
    concentrations = np.array([0, 1, 2, 5, 10, 20, 50, 100], dtype=float)
    calibration = sensor.generate_calibration_curves(analytes_to_calibrate, concentrations)

    print("\nCalibration Summary (Shift from baseline at 100 nM):")
    for name in analytes_to_calibrate:
        shifts = np.array(calibration[name]["shift"], dtype=float)
        baseline = shifts[0]
        shift_100nm = shifts[-1] - baseline if not np.isnan(shifts[-1]) else np.nan
        print(f"  {name}: {shift_100nm:.2f} nm shift at 100 nM")

    print("\n" + "-" * 50)
    print("SIMULTANEOUS MULTI-ANALYTE DETECTION")
    print("-" * 50)

    patient_analytes = {"CRP": 0.08, "IL6": 0.05, "PSA": 0.02}
    spectrum_baseline = sensor.calculate_multi_analyte_spectrum({}, temperature=298)
    spectrum_298k = sensor.calculate_multi_analyte_spectrum(patient_analytes, temperature=298)
    spectrum_310k = sensor.calculate_multi_analyte_spectrum(patient_analytes, temperature=310)
    spectrum_330k = sensor.calculate_multi_analyte_spectrum({}, temperature=330)

    features_298k = sensor.extract_multi_analyte_features(spectrum_298k)
    features_310k = sensor.extract_multi_analyte_features(spectrum_310k)

    print("\nDetected features at 298K:")
    print(f"  Number of LMR dips: {features_298k['n_dips']}")
    if features_298k["dip_wavelengths"]:
        print(f"  Primary dip: {features_298k['dip_wavelengths'][0]:.1f} nm")
        print(f"  Dip area: {features_298k['dip_areas'][0]:.3f}")

    print("\nDetected features at 310K (fever temperature):")
    print(f"  Number of LMR dips: {features_310k['n_dips']}")
    if features_310k["dip_wavelengths"]:
        print(f"  Primary dip: {features_310k['dip_wavelengths'][0]:.1f} nm")
        print(f"  Dip area: {features_310k['dip_areas'][0]:.3f}")

    print("\n" + "-" * 50)
    print("BAYESIAN MULTI-ANALYTE DIAGNOSIS")
    print("-" * 50)

    disease_prevalences = {"Inflammation": 0.08, "Prostate Cancer": 0.02, "Heart Failure": 0.03}
    diagnostic = MultiAnalyteBayesianDiagnostic(
        analytes=["CRP", "IL6", "PSA", "TNFa", "BNP"],
        disease_prevalences=disease_prevalences,
    )

    patient_measurements = {"CRP": 3.2, "IL6": 2.5, "PSA": 0.8, "TNFa": 1.9, "BNP": 0.3}

    for temperature in [298, 310, 315]:
        print(f"\nAt {temperature}K ({temperature - 273.15:.1f}°C):")
        posteriors = diagnostic.posterior_diseases(patient_measurements, temperature)
        for disease, probability in sorted(posteriors.items(), key=lambda item: item[1], reverse=True):
            if probability > 0.01:
                print(f"  {disease}: {probability:.3f}")

    print("\nDifferential Diagnosis (threshold > 0.05):")
    diff_diag = diagnostic.differential_diagnosis(patient_measurements, 298, threshold=0.05)
    for disease, probability in diff_diag:
        print(f"  {disease}: {probability:.3f}")

    information_gain = diagnostic.information_gain(patient_measurements, 298)
    print(f"\nInformation Gain from measurements: {information_gain:.3f} bits")

    print("\n" + "-" * 50)
    print("TEMPERATURE EFFECT ON DIAGNOSTIC CONFIDENCE")
    print("-" * 50)

    temp_range = np.linspace(280, 320, 20)
    confidence_trend = []
    for temperature in temp_range:
        posteriors = diagnostic.posterior_diseases(patient_measurements, float(temperature))
        confidence_trend.append(max(posteriors.values()))

    print(f"Max confidence at 280K: {confidence_trend[0]:.3f}")
    print(f"Max confidence near 298K: {confidence_trend[len(temp_range) // 2]:.3f}")
    print(f"Max confidence at 320K: {confidence_trend[-1]:.3f}")
    print(f"Confidence drop at elevated temperature: {(confidence_trend[0] - confidence_trend[-1]):.3f}")

    fig = plt.figure(figsize=(18, 12))

    ax1 = fig.add_subplot(3, 4, 1)
    wl_range = np.linspace(400, 2000, 200)
    for temperature in [280, 298, 320, 350]:
        k_values = [sensor.temperature_dependent_ohmic_damping(wavelength, temperature) for wavelength in wl_range]
        ax1.plot(wl_range, k_values, label=f"{temperature}K ({temperature - 273.15:.0f}°C)", linewidth=1.5)
    ax1.set_xlabel("Wavelength (nm)")
    ax1.set_ylabel("k_ext (Ohmic Damping)")
    ax1.set_title("Temperature-Dependent Ohmic Damping")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(3, 4, 2)
    for name in analytes_to_calibrate:
        shifts = np.array(calibration[name]["shift"], dtype=float)
        shifts = shifts - shifts[0]
        ax2.semilogx(concentrations[1:], shifts[1:], "o-", label=name, linewidth=1.5)
    ax2.set_xlabel("Concentration (nM)")
    ax2.set_ylabel("Wavelength Shift (nm)")
    ax2.set_title("Multi-Analyte Calibration")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(3, 4, 3)
    ax3.plot(sensor.wavelengths, spectrum_baseline, color="gray", alpha=0.7, label="298K baseline")
    ax3.plot(sensor.wavelengths, spectrum_298k, "b-", label="298K with analytes", linewidth=1.5)
    ax3.plot(sensor.wavelengths, spectrum_310k, "r--", label="310K with analytes", linewidth=1.5)
    ax3.plot(sensor.wavelengths, spectrum_330k, color="orange", linestyle=":", label="330K baseline", alpha=0.8)
    ax3.set_xlabel("Wavelength (nm)")
    ax3.set_ylabel("Reflectance")
    ax3.set_title("Multi-Analyte LMR Spectra")
    ax3.legend(fontsize=7)
    ax3.grid(True, alpha=0.3)

    ax4 = fig.add_subplot(3, 4, 4)
    mask = (sensor.wavelengths > 1000) & (sensor.wavelengths < 1400)
    ax4.plot(sensor.wavelengths[mask], spectrum_298k[mask], "b-", label="298K", linewidth=1.5)
    ax4.plot(sensor.wavelengths[mask], spectrum_310k[mask], "r--", label="310K", linewidth=1.5)
    if features_298k["dip_wavelengths"]:
        ax4.axvline(features_298k["dip_wavelengths"][0], color="b", linestyle=":", alpha=0.5)
    if features_310k["dip_wavelengths"]:
        ax4.axvline(features_310k["dip_wavelengths"][0], color="r", linestyle=":", alpha=0.5)
    ax4.set_xlabel("Wavelength (nm)")
    ax4.set_ylabel("Reflectance")
    ax4.set_title("Primary LMR Dip (Zoom)")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    ax5 = fig.add_subplot(3, 4, 5)
    post_298 = diagnostic.posterior_diseases(patient_measurements, 298)
    disease_labels = list(post_298.keys())
    probabilities = [post_298[disease] for disease in disease_labels]
    colors = [
        "green" if disease == "Healthy" else "red" if "Cancer" in disease else "orange"
        for disease in disease_labels
    ]
    ax5.bar(range(len(disease_labels)), probabilities, color=colors, alpha=0.7)
    ax5.set_xticks(range(len(disease_labels)))
    ax5.set_xticklabels(disease_labels, rotation=45, ha="right", fontsize=8)
    ax5.set_ylabel("Posterior Probability")
    ax5.set_title("Disease Probabilities at 298K")
    ax5.set_ylim(0, 1)
    ax5.axhline(0.05, color="gray", linestyle="--", alpha=0.5)

    ax6 = fig.add_subplot(3, 4, 6)
    ax6.plot(temp_range - 273.15, confidence_trend, "o-", color="purple", linewidth=2)
    ax6.axhline(0.9, color="green", linestyle="--", alpha=0.5, label="High confidence")
    ax6.axhline(0.5, color="orange", linestyle="--", alpha=0.5, label="Decision boundary")
    ax6.set_xlabel("Temperature (°C)")
    ax6.set_ylabel("Max Posterior Probability")
    ax6.set_title("Temperature Effect on Confidence")
    ax6.legend(fontsize=8)
    ax6.grid(True, alpha=0.3)

    ax7 = fig.add_subplot(3, 4, 7)
    analytes_list = ["CRP", "IL6", "PSA", "TNFa", "BNP"]
    measured_array = np.array([patient_measurements.get(analyte, 0.0) for analyte in analytes_list])
    expected_inflammation = np.array([3.5, 2.8, 0.5, 2.2, 0.2])
    expected_cancer = np.array([1.5, 0.5, 4.2, 0.5, 0.1])
    data_matrix = np.vstack([measured_array, expected_inflammation, expected_cancer])
    image = ax7.imshow(data_matrix.T, aspect="auto", cmap="RdBu_r", vmin=0, vmax=5)
    ax7.set_xticks([0, 1, 2])
    ax7.set_xticklabels(["Measured", "Inflammation\nExpected", "Cancer\nExpected"], fontsize=8)
    ax7.set_yticks(range(len(analytes_list)))
    ax7.set_yticklabels(analytes_list, fontsize=8)
    ax7.set_title("Biomarker Profile Comparison")
    plt.colorbar(image, ax=ax7, label="Concentration (normalized)")

    ax8 = fig.add_subplot(3, 4, 8)
    information_gain_trend = [diagnostic.information_gain(patient_measurements, float(temperature)) for temperature in temp_range]
    ax8.plot(temp_range - 273.15, information_gain_trend, "s-", color="teal", linewidth=2)
    ax8.set_xlabel("Temperature (°C)")
    ax8.set_ylabel("Information Gain (bits)")
    ax8.set_title("Information Gain vs Temperature")
    ax8.grid(True, alpha=0.3)

    ax9 = fig.add_subplot(3, 4, 9)
    thresholds = np.linspace(0, 1, 50)
    sensitivity = []
    specificity = []
    rng = np.random.default_rng(42)
    healthy_measurements = {analyte: float(rng.normal(0.3, 0.3)) for analyte in analytes_list}
    healthy_post = diagnostic.posterior_diseases(healthy_measurements, 298)
    disease_post = diagnostic.posterior_diseases(patient_measurements, 298)
    for threshold in thresholds:
        sensitivity.append(1 if disease_post.get("Inflammation", 0.0) > threshold else 0)
        specificity.append(1 if healthy_post.get("Healthy", 0.0) > threshold else 0)
    ax9.plot(1 - np.array(specificity), sensitivity, "b-", linewidth=2)
    ax9.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax9.set_xlabel("1 - Specificity")
    ax9.set_ylabel("Sensitivity")
    ax9.set_title("Multi-Analyte Detection Performance")
    ax9.grid(True, alpha=0.3)

    ax10 = fig.add_subplot(3, 4, 10)
    temperature_analysis = np.linspace(280, 350, 30)
    wl_fixed = 1200.0
    t_ref = 298.15
    k0 = sensor.temperature_dependent_ohmic_damping(wl_fixed, t_ref)
    phonon = []
    urbach = []
    carrier = []
    total = []
    for temperature in temperature_analysis:
        phonon_factor = 1.0 + 0.002 * (temperature - t_ref)
        e_g = 3.2
        e_photon = 1.24 / (wl_fixed / 1000.0)
        urbach_energy = 0.05 * (temperature / t_ref)
        urbach_factor = 1.0 + 0.1 * np.exp((e_photon - e_g) / urbach_energy) if e_photon < e_g else 1.1
        carrier_factor = 1.0 + 0.001 * (temperature / t_ref) ** 1.5
        phonon.append(k0 * phonon_factor)
        urbach.append(k0 * phonon_factor * urbach_factor)
        carrier.append(k0 * phonon_factor * urbach_factor * carrier_factor)
        total.append(sensor.temperature_dependent_ohmic_damping(wl_fixed, float(temperature)))
    ax10.stackplot(
        temperature_analysis - 273.15,
        [np.array(phonon) - k0, np.array(urbach) - np.array(phonon), np.array(carrier) - np.array(urbach)],
        labels=["Phonon", "Urbach", "Carrier"],
        alpha=0.7,
    )
    ax10.plot(temperature_analysis - 273.15, total, "k-", linewidth=2, label="Total")
    ax10.set_xlabel("Temperature (°C)")
    ax10.set_ylabel("Ohmic Damping k_ext")
    ax10.set_title("Damping Component Breakdown")
    ax10.legend(fontsize=8)
    ax10.grid(True, alpha=0.3)

    ax11 = fig.add_subplot(3, 4, 11)
    interference = np.zeros((len(analytes_to_calibrate), len(analytes_to_calibrate)))
    for i, analyte_i in enumerate(analytes_to_calibrate):
        for j, analyte_j in enumerate(analytes_to_calibrate):
            if i == j:
                interference[i, j] = 1.0
            else:
                shift_i = np.array(calibration[analyte_i]["shift"], dtype=float)
                shift_j = np.array(calibration[analyte_j]["shift"], dtype=float)
                if len(shift_i) > 1 and len(shift_j) > 1:
                    corr = np.corrcoef(shift_i[1:], shift_j[1:])[0, 1]
                    interference[i, j] = abs(corr) if not np.isnan(corr) else 0.1
    image11 = ax11.imshow(interference, cmap="Blues", vmin=0, vmax=1)
    ax11.set_xticks(range(len(analytes_to_calibrate)))
    ax11.set_yticks(range(len(analytes_to_calibrate)))
    ax11.set_xticklabels(analytes_to_calibrate, fontsize=8)
    ax11.set_yticklabels(analytes_to_calibrate, fontsize=8)
    ax11.set_title("Cross-Sensitivity Matrix")
    plt.colorbar(image11, ax=ax11, label="Correlation")

    ax12 = fig.add_subplot(3, 4, 12)
    n_measurements = 8
    measurement_sequence = []
    for _ in range(n_measurements):
        noise = rng.normal(0, 0.2, len(analytes_list))
        measurement = {analyte: patient_measurements[analyte] + noise[idx] for idx, analyte in enumerate(analytes_list)}
        measurement_sequence.append(measurement)

    seq_posteriors = {"Inflammation": [], "Healthy": []}
    current_prior = dict(disease_prevalences)
    for measurement in measurement_sequence:
        temp_diag = MultiAnalyteBayesianDiagnostic(analytes=analytes_list, disease_prevalences=current_prior)
        post = temp_diag.posterior_diseases(measurement, 298)
        seq_posteriors["Inflammation"].append(post.get("Inflammation", 0.0))
        seq_posteriors["Healthy"].append(post.get("Healthy", 0.0))
        current_prior["Inflammation"] = post.get("Inflammation", current_prior["Inflammation"])

    ax12.plot(range(1, n_measurements + 1), seq_posteriors["Inflammation"], "ro-", label="Inflammation", linewidth=1.5)
    ax12.plot(range(1, n_measurements + 1), seq_posteriors["Healthy"], "go-", label="Healthy", linewidth=1.5)
    ax12.axhline(0.5, color="gray", linestyle="--", alpha=0.5)
    ax12.set_xlabel("Measurement Number")
    ax12.set_ylabel("Posterior Probability")
    ax12.set_title("Sequential Diagnostic Update")
    ax12.legend(fontsize=8)
    ax12.set_ylim(0, 1)
    ax12.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 70)
    print("SIMULATION SUMMARY")
    print("=" * 70)
    print("\nKey Findings:")
    increase_pct = (
        sensor.temperature_dependent_ohmic_damping(1200, 320)
        / sensor.temperature_dependent_ohmic_damping(1200, 298)
        - 1.0
    ) * 100.0
    confidence_drop_pct_points = (confidence_trend[0] - confidence_trend[-1]) * 100.0
    primary_condition = diff_diag[0][0] if diff_diag else "Undetermined"
    primary_probability = diff_diag[0][1] if diff_diag else 0.0
    print(f"1. Ohmic damping increases by {increase_pct:.1f}% from 25°C to 47°C")
    print(f"2. Multi-analyte detection achieved {features_298k['n_dips']} distinct LMR dips")
    print(f"3. Diagnostic confidence drops by {confidence_drop_pct_points:.1f} percentage points at elevated temperature")
    print(f"4. Information gain from 5-analyte panel: {information_gain:.3f} bits")
    print(f"5. Primary suspected condition: {primary_condition} (probability: {primary_probability:.3f})")


if __name__ == "__main__":
    run_simulation()
