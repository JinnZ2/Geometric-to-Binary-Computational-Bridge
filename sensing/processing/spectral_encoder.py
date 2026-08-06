#!/usr/bin/env python3
"""
spectral_encoder.py — 1D CNN encoder for Raman spectra.

Takes a Raman intensity vector (e.g., 1024 wavenumbers) and maps it to a
2D latent representation, preserving local spectral features.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional

class SpectralEncoder(nn.Module):
    """
    1D CNN + Transformer encoder for Raman spectra.
    Designed to handle variable-length spectra (with padding).
    """
    
    def __init__(
        self,
        input_dim: int = 1024,
        latent_dim: int = 2,
        hidden_dim: int = 64,
        n_conv_layers: int = 3,
        kernel_size: int = 7,
        use_transformer: bool = True,
        n_transformer_heads: int = 4,
        n_transformer_layers: int = 2
    ):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.use_transformer = use_transformer
        
        # ---- 1D Convolutional feature extractor ----
        conv_layers = []
        in_channels = 1
        for i in range(n_conv_layers):
            out_channels = hidden_dim * (2 ** i)
            conv_layers.extend([
                nn.Conv1d(in_channels, out_channels, kernel_size, padding=kernel_size//2),
                nn.BatchNorm1d(out_channels),
                nn.ReLU(),
                nn.MaxPool1d(2)
            ])
            in_channels = out_channels
        self.conv_net = nn.Sequential(*conv_layers)
        
        # ---- Transformer (optional) ----
        if use_transformer:
            self.transformer = nn.TransformerEncoder(
                nn.TransformerEncoderLayer(
                    d_model=hidden_dim * (2 ** (n_conv_layers - 1)),
                    nhead=n_transformer_heads,
                    dim_feedforward=hidden_dim * 2,
                    activation='gelu',
                    dropout=0.1,
                    batch_first=True
                ),
                num_layers=n_transformer_layers
            )
        else:
            self.transformer = None
        
        # ---- Projection to latent ----
        # Determine the feature dimension after conv + pooling
        with torch.no_grad():
            dummy = torch.zeros(1, 1, input_dim)
            conv_out = self.conv_net(dummy)
            conv_dim = conv_out.shape[1] * conv_out.shape[2]  # flattened
        
        self.projection = nn.Sequential(
            nn.Linear(conv_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim * 2, latent_dim)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, input_dim) — Raman intensity vector.
        Returns:
            u: (batch, latent_dim) — Latent embedding.
        """
        # Add channel dimension: (batch, 1, input_dim)
        x = x.unsqueeze(1)
        
        # Conv features
        features = self.conv_net(x)  # (batch, channels, reduced_length)
        
        if self.use_transformer and self.transformer is not None:
            # Transpose to (batch, length, channels) for transformer
            features = features.permute(0, 2, 1)
            features = self.transformer(features)
            # Flatten
            features = features.reshape(features.shape[0], -1)
        else:
            # Flatten
            features = features.reshape(features.shape[0], -1)
        
        # Project to latent
        u = self.projection(features)
        return u
    
    def encode_batch(self, spectra: np.ndarray) -> np.ndarray:
        """Convenience method for numpy arrays."""
        with torch.no_grad():
            x = torch.tensor(spectra, dtype=torch.float32)
            return self.forward(x).numpy()


class SpectralPredictor(nn.Module):
    """
    JEPA-style predictor for Raman spectra.
    Predicts next latent state from previous two.
    """
    def __init__(self, latent_dim: int = 2, hidden_dim: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2 * latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim)
        )
    
    def forward(self, u_prev: torch.Tensor, u_curr: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([u_prev, u_curr], dim=1))


class SpectralUncertainty(nn.Module):
    """
    Quantifies epistemic uncertainty from a Raman spectrum.
    """
    def __init__(self, latent_dim: int = 2, hidden_dim: int = 16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, u: torch.Tensor) -> torch.Tensor:
        return F.softplus(self.net(u)).squeeze(-1)
