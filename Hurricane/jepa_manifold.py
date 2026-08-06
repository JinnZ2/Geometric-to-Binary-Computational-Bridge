#!/usr/bin/env python3
"""
jepa_manifold.py — JEPA manifold for seismo-acoustic hurricane features.

Trains a predictive manifold on the time series of seismo-acoustic features
to forecast storm evolution (e.g., intensification).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import List, Tuple
from sklearn.preprocessing import StandardScaler

class SeismoJEPA(nn.Module):
    """
    JEPA model for seismo-acoustic features.
    """
    def __init__(self, input_dim: int = 5, latent_dim: int = 2, hidden_dim: int = 32):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim)
        )
        self.predictor = nn.Sequential(
            nn.Linear(latent_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim)
        )
        self.latent_dim = latent_dim
        self.scaler = StandardScaler()

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def predict(self, u_prev: torch.Tensor, u_curr: torch.Tensor) -> torch.Tensor:
        return self.predictor(torch.cat([u_prev, u_curr], dim=1))

    def fit(self, features: np.ndarray, epochs: int = 100, lr: float = 0.01):
        """
        features: (n_timesteps, input_dim) - each row is a time step.
        We train to predict the next state from previous two.
        """
        # Normalize features
        features_scaled = self.scaler.fit_transform(features)
        X = torch.tensor(features_scaled, dtype=torch.float32)
        N = X.shape[0]
        optimizer = torch.optim.Adam(self.parameters(), lr=lr)

        for epoch in range(epochs):
            total_loss = 0.0
            for t in range(2, N):
                u_prev = self.encode(X[t-2].unsqueeze(0))
                u_curr = self.encode(X[t-1].unsqueeze(0))
                u_pred = self.predict(u_prev, u_curr)
                u_target = self.encode(X[t].unsqueeze(0))
                loss = F.mse_loss(u_pred, u_target.detach())
                total_loss += loss
            total_loss /= (N-2)
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()
            if epoch % 20 == 0:
                print(f"Epoch {epoch}: loss = {total_loss.item():.4f}")

    def project_sequence(self, features: np.ndarray) -> np.ndarray:
        """
        Project a sequence of features into latent space.
        """
        features_scaled = self.scaler.transform(features)
        X = torch.tensor(features_scaled, dtype=torch.float32)
        with torch.no_grad():
            u = self.encode(X)
        return u.numpy()

    def forecast(self, past_two: np.ndarray, steps: int = 5) -> np.ndarray:
        """
        Given two consecutive time steps (features), forecast future latent states.
        """
        past_scaled = self.scaler.transform(past_two)
        u_prev = self.encode(torch.tensor(past_scaled[0], dtype=torch.float32).unsqueeze(0))
        u_curr = self.encode(torch.tensor(past_scaled[1], dtype=torch.float32).unsqueeze(0))
        forecasts = []
        for _ in range(steps):
            u_pred = self.predict(u_prev, u_curr)
            forecasts.append(u_pred.squeeze().numpy())
            u_prev, u_curr = u_curr, u_pred
        return np.array(forecasts)

# Example usage with synthetic data
if __name__ == "__main__":
    # Generate synthetic seismo features: [disp, press, diss, wind, sst]
    np.random.seed(42)
    t = np.linspace(0, 100, 50)
    # Simulate a storm intensifying
    disp = 5 + 2 * np.exp(t/20) + np.random.randn(50)*0.5
    press = 100 + 10 * np.exp(t/20) + np.random.randn(50)*2
    diss = 0.01 + 0.005 * np.exp(t/15) + np.random.randn(50)*0.002
    wind = 10 + 5 * np.exp(t/25) + np.random.randn(50)*0.5
    sst = 28 - 0.01 * t + np.random.randn(50)*0.2
    features = np.column_stack([disp, press, diss, wind, sst])

    model = SeismoJEPA()
    model.fit(features, epochs=50)
    latent = model.project_sequence(features)
    print("Latent trajectory:", latent.shape)

    # Forecast next 5 steps from last two
    last_two = features[-2:]
    forecast = model.forecast(last_two, steps=5)
    print("Forecasted latent states:\n", forecast)
