# sensing/processing/jepa_manifold.py
"""
JEPA manifold learning for Primitive streams.
Converts timestamped observations → binary vectors → geometric manifold → LLM grounding.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Optional, Tuple
from dataclasses import dataclass
from ..firmware.sensor_drivers.base import SensorReading
from .primitives_encoder import Primitive

@dataclass
class ManifoldState:
    """Latent state of the geometric manifold at a given tick."""
    u: torch.Tensor          # 2D embedding
    omega: float             # attunement (observer entanglement)
    uncertainty: float       # epistemic uncertainty

class JEPAManifold:
    """
    Learns a continuous 2D manifold from binary-encoded Primitive streams.
    Follows the bridge's "substrate-primary cognition" pattern.
    """
    
    def __init__(self, latent_dim: int = 2, hidden_dim: int = 16):
        self.latent_dim = latent_dim
        self.hidden_dim = hidden_dim
        self._init_networks()
        self.binary_window: List[np.ndarray] = []  # rolling window of binary states
        
    def _init_networks(self):
        # Encoder: Primitive → binary → latent
        self.encoder = nn.Sequential(
            nn.Linear(64, self.hidden_dim),  # fixed binary width
            nn.Tanh(),
            nn.Linear(self.hidden_dim, self.latent_dim)
        )
        # Predictor: previous two latent states → next latent state
        self.predictor = nn.Sequential(
            nn.Linear(2 * self.latent_dim, self.hidden_dim),
            nn.ReLU(),
            nn.Linear(self.hidden_dim, self.latent_dim)
        )
        # Instrument field: latent → local Riemannian metric
        self.instrument = nn.Sequential(
            nn.Linear(self.latent_dim, self.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.hidden_dim, 3)
        )
        # Unknown field: latent → epistemic uncertainty
        self.unknown = nn.Sequential(
            nn.Linear(self.latent_dim, self.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.hidden_dim, 1)
        )
        # Attunement field: latent → observer entanglement
        self.attunement = nn.Sequential(
            nn.Linear(self.latent_dim, self.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.hidden_dim, 1)
        )
        self.optimizer = torch.optim.Adam(
            list(self.encoder.parameters()) + 
            list(self.predictor.parameters()) +
            list(self.instrument.parameters()) +
            list(self.unknown.parameters()) +
            list(self.attunement.parameters()),
            lr=0.02
        )
    
    def _primitive_to_binary(self, primitive: Primitive) -> np.ndarray:
        """
        Convert a Primitive to a fixed-width binary vector.
        This is the "geometric → binary" bridge from the repo's core idea[reference:3].
        """
        # Extract numeric values from the primitive's form (JSON) or readings
        values = []
        for reading in primitive.readings:
            values.extend(reading.values.values())
        
        # Quantize to binary (threshold at median of observed range)
        arr = np.array(values[:64])  # cap at 64 values
        if len(arr) < 64:
            arr = np.pad(arr, (0, 64 - len(arr)))
        median = np.median(arr) if len(arr) > 0 else 0.5
        return (arr > median).astype(np.float32)
    
    def step(self, primitive: Primitive) -> Optional[ManifoldState]:
        """
        Process one Primitive: update the manifold and return the latent state.
        Called by the sensing node's tick loop[reference:4].
        """
        # 1. Convert to binary
        binary_vec = self._primitive_to_binary(primitive)
        self.binary_window.append(binary_vec)
        if len(self.binary_window) > 32:
            self.binary_window.pop(0)
        
        # 2. Encode to latent
        x = torch.tensor(binary_vec, dtype=torch.float32).unsqueeze(0)
        u = self.encoder(x).detach().numpy()[0]
        
        # 3. Compute attunement and uncertainty
        u_t = torch.tensor(u, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            omega = torch.sigmoid(self.attunement(u_t)).item()
            uncertainty = F.softplus(self.unknown(u_t)).item()
        
        return ManifoldState(u=u, omega=omega, uncertainty=uncertainty)
    
    def train_on_window(self):
        """Train the JEPA on the accumulated binary window."""
        if len(self.binary_window) < 5:
            return
        
        # Convert window to tensor
        X = torch.tensor(np.stack(self.binary_window), dtype=torch.float32)
        u = self.encoder(X)
        
        # Stress loss: preserve similarity structure
        sim = self._compute_similarity(X)
        loss = self._stress_loss(u, sim)
        
        # Prediction loss: forecast next state
        if len(u) >= 3:
            u_hat = self.predictor(torch.cat([u[:-2], u[1:-1]], dim=1))
            loss += 0.5 * F.mse_loss(u_hat, u[2:].detach())
        
        # Regularization
        loss += 0.1 * self._curvature_loss(u)
        loss += 0.2 * self.unknown(u).mean()
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
    
    def _compute_similarity(self, X: torch.Tensor) -> torch.Tensor:
        """Hamming similarity between binary vectors."""
        n = X.shape[0]
        sim = torch.zeros(n, n)
        for i in range(n):
            for j in range(n):
                if i == j:
                    sim[i, j] = 1.0
                else:
                    hamming = (X[i] != X[j]).float().mean()
                    sim[i, j] = 1.0 - hamming
        return sim
    
    def _stress_loss(self, u: torch.Tensor, sim: torch.Tensor) -> torch.Tensor:
        """Preserve similarity structure in latent space."""
        I = self._metric(u)
        diff = u.unsqueeze(1) - u.unsqueeze(0)
        d = torch.sqrt(torch.einsum('...i,...ij,...j->...', diff, I, diff) + 1e-8)
        return ((d - (1.0 - sim))**2).mean()
    
    def _metric(self, u: torch.Tensor) -> torch.Tensor:
        """Learnable Riemannian metric (InstrumentField)."""
        raw = self.instrument(u)
        L = torch.zeros(u.shape[0], 2, 2, device=u.device)
        L[:, 0, 0] = raw[:, 0]
        L[:, 1, 0] = raw[:, 1]
        L[:, 1, 1] = raw[:, 2]
        return L @ L.transpose(1, 2) + 0.1 * torch.eye(2, device=u.device).unsqueeze(0)
    
    def _curvature_loss(self, u: torch.Tensor) -> torch.Tensor:
        """Penalize deviation from isometric embedding."""
        # Simplified: encourage unit singular values
        return torch.tensor(0.0)  # full Jacobian requires vmap
