#!/usr/bin/env python3
"""
raman_jepa_pipeline.py — End-to-end JEPA pipeline for Ramanomics.

Wraps the spectral encoder, predictor, uncertainty, and claim table
into a single pipeline that integrates with the exploration engine.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import json
from datetime import datetime

# Import your existing components
from .spectral_encoder import SpectralEncoder, SpectralPredictor, SpectralUncertainty
from ..claims.scientific_claim import ScientificClaimTable, TrialResult
from ..exploration.exploration_engine_complete import (
    FrameContext, ManifoldState, ExplorationFrame, FrameID,
    safe_evaluate, TrialResult
)

class RamanJEPA(nn.Module):
    """
    Full JEPA model for Raman spectra.
    Encoder + Predictor + Uncertainty + Attunement (learned from data).
    """
    
    def __init__(
        self,
        input_dim: int = 1024,
        latent_dim: int = 2,
        encoder_hidden: int = 64,
        predictor_hidden: int = 32,
        use_transformer: bool = True
    ):
        super().__init__()
        self.encoder = SpectralEncoder(
            input_dim=input_dim,
            latent_dim=latent_dim,
            hidden_dim=encoder_hidden,
            use_transformer=use_transformer
        )
        self.predictor = SpectralPredictor(latent_dim, predictor_hidden)
        self.uncertainty = SpectralUncertainty(latent_dim, predictor_hidden)
        
        # Attunement field: learns which spectral regions are most informative
        self.attunement = nn.Sequential(
            nn.Linear(latent_dim, predictor_hidden),
            nn.Tanh(),
            nn.Linear(predictor_hidden, 1)
        )
        
        # Instrument field: Riemannian metric for the latent space
        self.instrument = nn.Sequential(
            nn.Linear(latent_dim, predictor_hidden),
            nn.Tanh(),
            nn.Linear(predictor_hidden, 3)
        )
        
        self.latent_dim = latent_dim
        self.binary_window = []  # store latent states for training
        self.spectral_window = []  # store raw spectra
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)
    
    def step_from_spectrum(self, spectrum: np.ndarray) -> ManifoldState:
        """
        Process a single Raman spectrum and return the manifold state.
        """
        x = torch.tensor(spectrum, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            u = self.encoder(x).squeeze(0).numpy()
            u_t = torch.tensor(u, dtype=torch.float32).unsqueeze(0)
            omega = torch.sigmoid(self.attunement(u_t)).item()
            uncertainty = self.uncertainty(u_t).item()
        
        # Store in window for training
        self.binary_window.append(u)  # we use 'binary_window' as latent history
        self.spectral_window.append(spectrum)
        if len(self.binary_window) > 32:
            self.binary_window.pop(0)
            self.spectral_window.pop(0)
        
        # Compute metric
        with torch.no_grad():
            raw = self.instrument(u_t)
            L = torch.zeros(1, 2, 2)
            L[0, 0, 0] = raw[0, 0]
            L[0, 1, 0] = raw[0, 1]
            L[0, 1, 1] = raw[0, 2]
            metric = (L @ L.transpose(1, 2) + 0.1 * torch.eye(2)).numpy()[0]
        
        return ManifoldState(
            u=u,
            omega=omega,
            uncertainty=uncertainty,
            extra={"metric": metric}
        )
    
    def get_latent_window(self) -> torch.Tensor:
        """Return the recent latent states as a tensor."""
        if len(self.binary_window) < 2:
            return torch.zeros(1, self.latent_dim)
        return torch.tensor(np.stack(self.binary_window), dtype=torch.float32)
    
    def train_on_window(self, stp_weight: float = 0.0):
        """
        Train the JEPA on the accumulated spectral window.
        Uses stress loss + prediction loss + curvature loss.
        """
        if len(self.spectral_window) < 5:
            return
        
        # Convert spectral window to tensor
        X = torch.tensor(np.stack(self.spectral_window), dtype=torch.float32)
        u = self.encoder(X)
        
        # ----- Stress loss (preserve spectral similarity) -----
        sim = self._compute_similarity(X)
        loss = self._stress_loss(u, sim)
        
        # ----- Prediction loss -----
        if u.shape[0] >= 3:
            u_hat = self.predictor(u[:-2], u[1:-1])
            loss += 0.5 * F.mse_loss(u_hat, u[2:].detach())
        
        # ----- Curvature loss (encourage smooth manifold) -----
        loss += 0.02 * self._curvature_loss(u)
        
        # ----- STP loss (optional) -----
        if stp_weight > 0 and u.shape[0] >= 3:
            vel = u[1:] - u[:-1]
            acc = vel[1:] - vel[:-1]
            stp = F.relu(torch.norm(acc, dim=1) - 0.2).mean()
            loss += stp_weight * stp
        
        # ----- Uncertainty regularization -----
        loss += 0.2 * self.uncertainty(u).mean()
        
        # Backprop
        optimizer = torch.optim.Adam(self.parameters(), lr=0.01)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    
    def _compute_similarity(self, X: torch.Tensor) -> torch.Tensor:
        """Cosine similarity between spectra."""
        n = X.shape[0]
        X_norm = F.normalize(X, dim=1)
        sim = X_norm @ X_norm.T
        return sim.clamp(0, 1)
    
    def _stress_loss(self, u: torch.Tensor, sim: torch.Tensor) -> torch.Tensor:
        """Preserve similarity in latent space with learned metric."""
        diff = u.unsqueeze(1) - u.unsqueeze(0)
        # Compute metric from instrument field
        raw = self.instrument(u)
        L = torch.zeros(u.shape[0], 2, 2, device=u.device)
        L[:, 0, 0] = raw[:, 0]
        L[:, 1, 0] = raw[:, 1]
        L[:, 1, 1] = raw[:, 2]
        I = L @ L.transpose(1, 2) + 0.1 * torch.eye(2, device=u.device).unsqueeze(0)
        
        I_avg = 0.5 * (I.unsqueeze(1) + I.unsqueeze(0))
        d = torch.sqrt(torch.einsum('...i,...ij,...j->...', diff, I_avg, diff) + 1e-8)
        return ((d - (1.0 - sim))**2).mean()
    
    def _curvature_loss(self, u: torch.Tensor) -> torch.Tensor:
        """Penalise acceleration in latent space."""
        if u.shape[0] < 3:
            return torch.tensor(0.0, device=u.device)
        vel = u[1:] - u[:-1]
        acc = vel[1:] - vel[:-1]
        return torch.norm(acc, dim=1).mean()


# ============================================================
# Raman‑specific Claim predicates
# ============================================================
def raman_peak_predicate(peak_center: float, threshold: float, direction: str = ">"):
    """
    Generate a predicate string for a Raman peak intensity.
    Example: "peak_gt(1600, 0.5)" means peak at 1600 cm⁻¹ > 0.5.
    """
    # This is designed to work with the safe parser; we inject 'peak_intensity' into context.
    # Usage in claim: {"type": "raman_peak", "center": 1600, "threshold": 0.5, "direction": "gt"}
    return lambda context: context['peak_intensity'][peak_center] > threshold if direction == "gt" else context['peak_intensity'][peak_center] < threshold

# ============================================================
# Raman Claim Table extension
# ============================================================
class RamanClaimTable(ScientificClaimTable):
    """
    Extends claim table with Raman‑specific hypothesis helpers.
    """
    
    def add_raman_claim(
        self,
        claim_id: str,
        description: str,
        peak_center: float,
        threshold: float,
        direction: str = "gt",
        scope: Optional[Dict] = None,
        bias: Optional[Dict] = None
    ):
        """
        Add a claim that a specific Raman peak intensity exceeds a threshold.
        """
        if scope is None:
            scope = {
                "sensor_types": ["raman"],
                "max_uncertainty_threshold": 0.3,
                "min_attunement_threshold": 0.5
            }
        if bias is None:
            bias = {"additive": 0.0, "multiplicative": 1.0, "estimated_systematic_error": 0.02}
        
        claim_data = {
            "id": claim_id,
            "version": 1,
            "author": "ramanomics",
            "date_created": datetime.utcnow().isoformat(),
            "status": "active",
            "description": description,
            "scope": scope,
            "predicate": {
                "type": "raman_peak",
                "condition": f"peak_{direction}({peak_center}, {threshold})",
                "peak_center": peak_center,
                "threshold": threshold,
                "direction": direction
            },
            "measurement_bias": bias,
            "evidence": {
                "supporting_count": 0,
                "falsifying_count": 0,
                "total_trials": 0,
                "last_trial_timestamp": None,
                "confidence_interval": None
            },
            "falsification_criteria": {
                "consecutive_failures_to_falsify": 3,
                "failure_threshold_p_value": 0.05
            }
        }
        self.add_claim(claim_data)


# ============================================================
# Integration with Exploration Engine
# ============================================================
class RamanFrame(ExplorationFrame):
    """
    A frame that uses the Raman JEPA pipeline.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.RAMAN  # Add this to your FrameID enum if desired
    
    def __init__(self):
        self.jepa = RamanJEPA()
        self.optimizer = torch.optim.Adam(self.jepa.parameters(), lr=0.01)
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        """
        In this context, 'binary_vec' is actually a Raman spectrum.
        We override the name for clarity.
        """
        spectrum = binary_vec  # aliasing
        state = self.jepa.step_from_spectrum(spectrum)
        context.current_state = state
        
        # Extract peak intensities for claim evaluation
        # (We compute a simple peak detection from the spectrum)
        peaks = self._extract_peaks(spectrum)
        context.extra["peak_intensity"] = peaks
        
        return {"latent_u": state.u.tolist(), "peaks_detected": list(peaks.keys())}
    
    def _extract_peaks(self, spectrum: np.ndarray) -> Dict[float, float]:
        """
        Simple peak extraction for claim evaluation.
        In production, use a proper peak picking algorithm.
        """
        # Simulate: just return known peak positions with intensities
        # For demo, we assume the spectrum contains known peak centers
        known_centers = [785, 1000, 1060, 1090, 1250, 1300, 1440, 1580, 1650, 1740]
        peaks = {}
        # Find the closest point in the spectrum for each known center
        # (assuming wavenumber array is uniformly spaced)
        wavenumbers = np.linspace(500, 3500, len(spectrum))
        for center in known_centers:
            idx = np.argmin(np.abs(wavenumbers - center))
            if idx < len(spectrum):
                peaks[center] = float(spectrum[idx])
        return peaks
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        # The claim table is already equipped to handle Raman peak predicates
        # We just need to pass the peak intensities in the context
        return context.claim_table.test_all(context.current_state, context.extra)
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Use the LLM bridge with Raman-specific context
        state = context.current_state
        if state:
            peaks = context.extra.get("peak_intensity", {})
            peak_str = ", ".join([f"{k}cm⁻¹:{v:.2f}" for k, v in list(peaks.items())[:5]])
            prompt = f"{prompt} Active Raman peaks: {peak_str}. Attunement: {state.omega:.2f}."
        return context.llm_bridge.generate(state, prompt)
    
    def update(self, context: FrameContext):
        self.jepa.train_on_window(stp_weight=0.1)
        context.claim_table.save()


# ============================================================
# Quick Test
# ============================================================
if __name__ == "__main__":
    from ..data.synthetic_raman import SyntheticRamanGenerator
    
    # Generate synthetic data
    gen = SyntheticRamanGenerator()
    states = ["healthy_fibroblast"] * 5 + ["stressed"] * 5 + ["apoptotic"] * 5
    spectra, metas = gen.generate_timeseries(states, transitions=[5, 10])
    
    # Initialize pipeline
    pipeline = RamanJEPA()
    
    # Process each spectrum
    for i, (spec, meta) in enumerate(zip(spectra, metas)):
        state = pipeline.step_from_spectrum(spec)
        print(f"t={i}: {meta['state']} -> u={state.u}, ω={state.omega:.3f}, κ={state.uncertainty:.3f}")
        
        # Train incrementally
        pipeline.train_on_window()
    
    # Visualize latent trajectory
    u_traj = np.stack([pipeline.step_from_spectrum(spec).u for spec in spectra])
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 6))
    plt.scatter(u_traj[:, 0], u_traj[:, 1], c=range(len(u_traj)), cmap='viridis')
    plt.colorbar(label='Time step')
    plt.title("Raman JEPA Manifold Trajectory")
    plt.xlabel("u0"); plt.ylabel("u1")
    plt.grid(alpha=0.3)
    plt.savefig("raman_jepa_trajectory.png", dpi=150)
    plt.show()
