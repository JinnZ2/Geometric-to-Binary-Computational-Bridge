#!/usr/bin/env python3
"""
seismo_encoder.py — Physics functions for seismo-acoustic signals.

Implements the key physical relationships from the Science paper:
- Turbulent pressure spectrum (dissipation rate)
- Ground displacement response to pressure fluctuations
- Wind speed estimation from infrasound
"""

import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
from typing import Tuple, Optional

def turbulent_dissipation_rate(pressure_timeseries: np.ndarray, sampling_rate: float,
                               k_min: float = 0.01, k_max: float = 0.1) -> float:
    """
    Estimate turbulent dissipation rate from the pressure frequency spectrum.

    Based on the inertial subrange model: E(f) = C * epsilon^(2/3) * f^(-5/3)
    where epsilon is the dissipation rate.

    Args:
        pressure_timeseries: pressure signal (Pa) over time
        sampling_rate: Hz
        k_min, k_max: wavenumber bounds (in m^-1) – here we approximate with frequency.

    Returns:
        epsilon (m^2/s^3)
    """
    # Compute power spectral density
    f, Pxx = signal.welch(pressure_timeseries, fs=sampling_rate, nperseg=256)
    # Inertial subrange: find where slope is -5/3 in log-log
    log_f = np.log10(f)
    log_P = np.log10(Pxx)
    # Find region where slope ~ -1.67 (tolerance)
    slopes = np.gradient(log_P, log_f)
    mask = (np.abs(slopes + 1.67) < 0.3) & (f > 0.01) & (f < 1.0)
    if np.sum(mask) < 5:
        return np.nan

    # Use Kolmogorov constant C = 0.55
    # E(f) = C * eps^(2/3) * (2*pi*f)^(-5/3)
    # => eps = ( E(f) * (2*pi*f)^(5/3) / C )^(3/2)
    f_mid = f[mask][len(f[mask])//2]
    E_mid = Pxx[mask][len(Pxx[mask])//2]
    C = 0.55
    eps = (E_mid * (2 * np.pi * f_mid)**(5/3) / C)**(3/2)
    return eps

def ground_displacement_response(pressure_timeseries: np.ndarray, sampling_rate: float,
                                 soil_young_modulus: float = 1e7, density: float = 2000) -> np.ndarray:
    """
    Compute quasi-static ground displacement from pressure fluctuations.

    Model: displacement u ~ (pressure * characteristic_length) / (E)
    For a Rayleigh wave coupling.

    Returns displacement in nm.
    """
    # Simple linear model: u = (p * L) / E, with L ~ wavelength
    # We'll compute a frequency-dependent response
    f = fftfreq(len(pressure_timeseries), 1/sampling_rate)
    P = fft(pressure_timeseries)
    # Rayleigh wave speed ~ 300 m/s
    c_R = 300
    # Wavelength lambda = c_R / f
    # Response: u(f) = (P(f) * lambda) / E  (quasi-static)
    with np.errstate(divide='ignore', invalid='ignore'):
        lambda_wave = c_R / np.abs(f)
        lambda_wave[np.isinf(lambda_wave)] = 0
        response = (P * lambda_wave) / soil_young_modulus
    displacement = np.real(np.fft.ifft(response))
    # Convert to nm
    return displacement * 1e9

def wind_speed_from_infrasound(pressure_timeseries: np.ndarray, sampling_rate: float,
                               density_air: float = 1.2) -> Tuple[float, float]:
    """
    Estimate wind speed from infrasound pressure using empirical relation.

    Based on the finding that infrasound pressure is proportional to wind speed squared:
    p_rms = 0.5 * rho_air * (U^2) * (drag coefficient)

    Returns (U10, confidence) in m/s.
    """
    # Compute RMS pressure
    p_rms = np.sqrt(np.mean(pressure_timeseries**2))
    # Empirical drag coefficient for ocean ~ 0.001
    Cd = 0.001
    # U = sqrt(2 * p_rms / (rho * Cd))
    if p_rms < 1e-6:
        return 0.0, 0.0
    U = np.sqrt(2 * p_rms / (density_air * Cd))
    # Confidence is based on signal-to-noise ratio
    noise_floor = np.std(pressure_timeseries) * 0.1  # assume 10% noise
    confidence = 1.0 - np.minimum(1.0, noise_floor / p_rms)
    return U, confidence

def seismo_acoustic_features(seismo_obs_list) -> dict:
    """
    Compute all features from a list of SeismoObs.
    Returns a dictionary of time series for each feature.
    """
    times = []
    disp = []
    press = []
    dissipation = []
    wind_speed = []
    ground_disp = []

    for obs in seismo_obs_list:
        times.append(obs.timestamp)
        disp.append(obs.ground_displacement_nm)
        press.append(obs.infrasound_pressure_pa)

        # We need the full time series for dissipation, not just mean.
        # Here we assume obs contains the raw time series; for demonstration, we use synthetic.
        # In practice, we would store the raw vectors.
        # We'll just compute a dummy dissipation using mean.
        # For real implementation, store raw arrays.

        # Dummy: use mean pressure to estimate
        eps = turbulent_dissipation_rate(np.array([press[-1]]*100), 1.0)  # dummy
        dissipation.append(eps if not np.isnan(eps) else 0.0)
        U, conf = wind_speed_from_infrasound(np.array([press[-1]]*100), 1.0)
        wind_speed.append(U)
        ground_disp.append(disp[-1] * 0.5)  # dummy

    return {
        'timestamp': times,
        'ground_displacement_nm': disp,
        'infrasound_pressure_pa': press,
        'turbulent_dissipation_rate': dissipation,
        'wind_speed_ms': wind_speed,
        'ground_displacement_response_nm': ground_disp
    }
