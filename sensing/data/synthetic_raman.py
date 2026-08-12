#!/usr/bin/env python3
"""
synthetic_raman.py — Generates realistic synthetic Raman spectra for testing.

Simulates common biomolecular peaks:
- Lipids: 1060, 1300, 1440, 1740 cm⁻¹
- Proteins: 1000, 1250, 1450, 1650 cm⁻¹
- DNA/RNA: 785, 1090, 1580 cm⁻¹
- Glucose: 850, 1125, 1360 cm⁻¹
- Water: 1640 cm⁻¹ (broad)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import matplotlib.pyplot as plt

@dataclass
class RamanState:
    """Ground truth cellular state with corresponding spectral peaks."""
    label: str
    peaks: Dict[float, float]  # wavenumber (cm⁻¹) -> intensity (a.u.)
    background_slope: float
    noise_scale: float
    cell_cycle_phase: str  # G1, S, G2, M

class SyntheticRamanGenerator:
    """
    Generates realistic Raman spectra for various cellular states.
    """
    
    # Standard peak libraries (wavenumber -> intensity for pure components)
    PEAK_LIBRARY = {
        # Lipids
        "lipids": {
            1060: 0.8, 1080: 0.6, 1125: 0.5, 1300: 0.9, 
            1440: 1.0, 1740: 0.7, 2850: 0.8, 2880: 0.6
        },
        # Proteins (amide)
        "proteins": {
            1000: 0.7, 1250: 0.9, 1450: 0.8, 1650: 1.0,
            1550: 0.6, 1600: 0.7, 2930: 0.5
        },
        # DNA/RNA
        "nucleic_acids": {
            785: 0.9, 1090: 0.8, 1340: 0.6, 1480: 0.7,
            1580: 0.8, 1660: 0.6
        },
        # Glucose
        "glucose": {
            850: 0.6, 1125: 0.9, 1360: 0.7, 1460: 0.5,
            2900: 0.4, 3400: 0.3  # OH broad
        },
        # Cytochromes (heme)
        "cytochrome": {
            750: 0.6, 1120: 0.5, 1360: 0.8, 1580: 0.9,
            1620: 0.7
        },
        # Water (broad background)
        "water": {
            1640: 0.3, 3200: 0.4  # broad OH stretch
        }
    }
    
    # Cell state templates: which peaks are active and with what weights
    STATE_TEMPLATES = {
        "healthy_fibroblast": {
            "lipids": 0.3,
            "proteins": 0.8,
            "nucleic_acids": 0.4,
            "glucose": 0.2,
            "cytochrome": 0.3,
            "water": 0.5
        },
        "adipocyte": {
            "lipids": 1.0,
            "proteins": 0.3,
            "nucleic_acids": 0.1,
            "glucose": 0.2,
            "cytochrome": 0.1,
            "water": 0.4
        },
        "neuronal": {
            "lipids": 0.6,
            "proteins": 0.9,
            "nucleic_acids": 0.3,
            "glucose": 0.4,
            "cytochrome": 0.5,
            "water": 0.5
        },
        "apoptotic": {
            "lipids": 0.4,
            "proteins": 0.5,
            "nucleic_acids": 0.2,
            "glucose": 0.1,
            "cytochrome": 0.9,  # released
            "water": 0.6
        },
        "mitotic": {
            "lipids": 0.4,
            "proteins": 0.9,
            "nucleic_acids": 0.9,  # DNA duplication
            "glucose": 0.5,
            "cytochrome": 0.6,
            "water": 0.5
        },
        "stressed": {
            "lipids": 0.3,
            "proteins": 0.6,
            "nucleic_acids": 0.3,
            "glucose": 0.1,
            "cytochrome": 0.7,
            "water": 0.5
        }
    }
    
    # Cell cycle labels for each state
    CYCLE_PHASES = {
        "healthy_fibroblast": "G1",
        "adipocyte": "G0",
        "neuronal": "G0",
        "apoptotic": "M",  # undergoing apoptosis
        "mitotic": "M",
        "stressed": "G1"
    }
    
    def __init__(
        self,
        wavenumber_min: int = 500,
        wavenumber_max: int = 3500,
        num_points: int = 1024,
        seed: int = 42
    ):
        self.wavenumbers = np.linspace(wavenumber_min, wavenumber_max, num_points)
        self.num_points = num_points
        np.random.seed(seed)
    
    def gaussian_peak(self, wavenumbers: np.ndarray, center: float, height: float, sigma: float = 15.0) -> np.ndarray:
        """Generate a single Gaussian peak."""
        return height * np.exp(-((wavenumbers - center) ** 2) / (2 * sigma ** 2))
    
    def generate_spectrum(
        self,
        state_label: str,
        add_noise: bool = True,
        snr: float = 30.0,
        baseline_poly: int = 2
    ) -> Tuple[np.ndarray, Dict]:
        """
        Generate a single Raman spectrum for a given cell state.
        
        Args:
            state_label: One of the keys in STATE_TEMPLATES.
            add_noise: If True, add Poisson + Gaussian noise.
            snr: Signal-to-noise ratio.
            baseline_poly: Polynomial order for baseline.
        
        Returns:
            (spectrum, metadata) where metadata contains the active peaks and state info.
        """
        if state_label not in self.STATE_TEMPLATES:
            raise ValueError(f"Unknown state: {state_label}. Available: {list(self.STATE_TEMPLATES.keys())}")
        
        weights = self.STATE_TEMPLATES[state_label]
        spectrum = np.zeros(self.num_points)
        active_peaks = {}
        
        # Add peaks from each component
        for component, weight in weights.items():
            if weight == 0:
                continue
            component_peaks = self.PEAK_LIBRARY.get(component, {})
            for center, height in component_peaks.items():
                scaled_height = height * weight * 0.5  # scale to realistic intensity
                spectrum += self.gaussian_peak(self.wavenumbers, center, scaled_height)
                active_peaks[center] = active_peaks.get(center, 0) + scaled_height
        
        # Add baseline (polynomial + fluorescence-like)
        x_norm = np.linspace(0, 1, self.num_points)
        baseline = 0.1 + 0.3 * x_norm**2 + 0.1 * np.sin(2 * np.pi * x_norm * 0.3)
        spectrum += baseline * 0.2
        
        # Add noise
        if add_noise:
            # Poisson noise (photon shot)
            poisson = np.random.poisson(spectrum * snr) / snr
            # Gaussian read noise
            gaussian = np.random.normal(0, 0.05, self.num_points)
            spectrum = poisson + gaussian
        
        # Ensure non-negative
        spectrum = np.maximum(spectrum, 0.0)
        
        metadata = {
            "state": state_label,
            "cell_cycle": self.CYCLE_PHASES.get(state_label, "G1"),
            "active_component_weights": weights,
            "active_peaks": active_peaks,
            "snr": snr
        }
        
        return spectrum, metadata
    
    def generate_timeseries(
        self,
        states: List[str],
        transition_points: Optional[List[int]] = None,
        add_noise: bool = True,
        snr: float = 30.0,
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Generate a time-series of spectra, optionally with state transitions.
        
        Args:
            states: List of state labels for each time point.
            transition_points: Optional list of indices where the cell state changes.
                               If None, the cell stays in the first state.
        
        Returns:
            (spectra_matrix, metadata_list)
        """
        if transition_points is None:
            # All the same state
            spectra = []
            metas = []
            for state in states:
                spec, meta = self.generate_spectrum(state, add_noise, snr)
                spectra.append(spec)
                metas.append(meta)
            return np.array(spectra), metas
        
        # Interpolate between states at transition points
        # (simplified: just switch abruptly at the transition points)
        spectra = []
        metas = []
        current_state = states[0]
        for i, state in enumerate(states):
            if i in transition_points:
                current_state = state
            spec, meta = self.generate_spectrum(current_state, add_noise, snr)
            # Add slight temporal drift (e.g., photobleaching)
            if i > 0:
                spec = spec * (1.0 - 0.001 * i)  # gradual intensity decay
            spectra.append(spec)
            metas.append(meta)
        
        return np.array(spectra), metas
    
    def plot_spectrum(self, spectrum: np.ndarray, metadata: Dict, title: str = ""):
        """Plot a single spectrum with annotations."""
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(self.wavenumbers, spectrum, 'b-', linewidth=0.8)
        ax.set_xlabel("Wavenumber (cm⁻¹)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title(f"{title} - {metadata['state']} (Phase: {metadata['cell_cycle']})")
        ax.grid(alpha=0.3)
        # Mark active peaks
        for center in metadata.get("active_peaks", {}).keys():
            ax.axvline(center, color='red', alpha=0.3, linestyle='--')
        plt.tight_layout()
        plt.show()
        return fig, ax


# ============================================================
# Quick test
# ============================================================
if __name__ == "__main__":
    generator = SyntheticRamanGenerator()
    
    # Generate a single healthy fibroblast spectrum
    spec, meta = generator.generate_spectrum("healthy_fibroblast")
    generator.plot_spectrum(spec, meta, "Healthy Fibroblast")
    
    # Generate a time-series: healthy → stressed → apoptotic
    states = ["healthy_fibroblast"] * 5 + ["stressed"] * 5 + ["apoptotic"] * 5
    transitions = [5, 10]
    spectra, metas = generator.generate_timeseries(states, transitions)
    
    print(f"Generated {len(spectra)} spectra with shape {spectra.shape[1]} points.")
    print(f"State transitions at indices: {transitions}")
    print(f"Final state: {metas[-1]['state']}")
    
    # Visualise 3 spectra (beginning, middle, end)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for i, idx in enumerate([0, 5, 14]):
        axes[i].plot(generator.wavenumbers, spectra[idx])
        axes[i].set_title(f"t={idx}: {metas[idx]['state']}")
        axes[i].set_xlabel("Wavenumber (cm⁻¹)")
        axes[i].grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("raman_timeseries_example.png", dpi=150)
    plt.show()
