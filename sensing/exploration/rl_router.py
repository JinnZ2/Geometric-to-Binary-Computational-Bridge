#!/usr/bin/env python3
"""
rl_router.py — Contextual Bandit for dynamic frame selection.

Replaces the hard-coded heuristics in `choose_frame()` with a lightweight
linear model that learns which frame performs best based on current context.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from collections import deque
from .exploration_engine import FrameID, FrameContext

class LinearBandit(nn.Module):
    """
    A simple contextual bandit with epsilon-greedy exploration.
    Features: [uncertainty, omega, elapsed_ticks, claim_density, entropy, ...]
    Actions: frame indices.
    """
    def __init__(self, n_features: int = 6, n_actions: int = 11, epsilon: float = 0.1, lr: float = 0.01):
        super().__init__()
        self.n_features = n_features
        self.n_actions = n_actions
        self.epsilon = epsilon
        self.W = nn.Parameter(torch.randn(n_features, n_actions) * 0.01)
        self.optimizer = torch.optim.Adam([self.W], lr=lr)
        self.replay_buffer = deque(maxlen=2000)
    
    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return features @ self.W  # (batch, n_actions)
    
    def select_action(self, features: torch.Tensor) -> int:
        """Epsilon-greedy selection."""
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.n_actions)
        with torch.no_grad():
            scores = self.forward(features)
            return torch.argmax(scores, dim=0).item()
    
    def update(self, features: torch.Tensor, action: int, reward: float):
        """Store experience and perform a mini-batch update."""
        self.replay_buffer.append((features.clone(), action, reward))
        if len(self.replay_buffer) >= 32:
            self._train_batch()
    
    def _train_batch(self, batch_size: int = 32):
        """Batch update using stored experiences."""
        indices = np.random.choice(len(self.replay_buffer), min(batch_size, len(self.replay_buffer)), replace=False)
        batch = [self.replay_buffer[i] for i in indices]
        
        features = torch.stack([b[0] for b in batch])
        actions = torch.tensor([b[1] for b in batch], dtype=torch.long)
        rewards = torch.tensor([b[2] for b in batch], dtype=torch.float32)
        
        # Compute loss: negative log probability weighted by reward (REINFORCE-style)
        scores = self.forward(features)
        log_probs = F.log_softmax(scores, dim=1)
        selected_log_probs = log_probs.gather(1, actions.unsqueeze(1)).squeeze()
        loss = -(selected_log_probs * rewards).mean()
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()


class LearnedRouter:
    """
    Wraps the bandit and provides the `choose_frame()` interface.
    Extracts features from the FrameContext.
    """
    
    def __init__(self):
        self.bandit = LinearBandit(
            n_features=6,  # we'll use: uncertainty, omega, elapsed_ticks, claim_density, entropy, sensor_type_embedding
            n_actions=len(FrameID),
            epsilon=0.15,
            lr=0.01
        )
        self.frame_id_to_idx = {fid: i for i, fid in enumerate(FrameID)}
        self.idx_to_frame_id = {i: fid for fid, i in self.frame_id_to_idx.items()}
        self.last_features = None
        self.last_action = None
        self.action_history = []
    
    def extract_features(self, context: FrameContext) -> torch.Tensor:
        """Convert context into a feature vector for the bandit."""
        state = context.current_state
        if state is None:
            uncertainty = 0.5
            omega = 0.5
        else:
            uncertainty = state.uncertainty
            omega = state.omega
        
        elapsed = context.elapsed_ticks / 100.0  # normalize
        claim_density = len(context.claim_table.claims) / 10.0
        
        # Entropy of recent binary window (if available)
        if hasattr(context.manifold, 'binary_window') and context.manifold.binary_window:
            recent = np.stack(context.manifold.binary_window[-5:])
            if recent.size > 0:
                p = recent.mean()
                entropy = - (p * np.log(p+1e-6) + (1-p)*np.log(1-p+1e-6))
            else:
                entropy = 1.0
        else:
            entropy = 1.0
        
        # Sensor type as a simple category (convert to one-hot? we'll just use a float)
        sensor_type_embed = hash(context.sensor_type) % 10 / 10.0 if context.sensor_type else 0.0
        
        features = torch.tensor([
            uncertainty,
            omega,
            elapsed,
            claim_density,
            entropy,
            sensor_type_embed
        ], dtype=torch.float32)
        return features
    
    def choose_frame(self, context: FrameContext) -> FrameID:
        """
        Returns the chosen frame ID using the learned bandit.
        Also stores the chosen action for later reward assignment.
        """
        features = self.extract_features(context)
        action_idx = self.bandit.select_action(features)
        frame_id = self.idx_to_frame_id[action_idx]
        
        # Store for reward assignment later
        self.last_features = features
        self.last_action = action_idx
        self.action_history.append((frame_id, context.elapsed_ticks))
        return frame_id
    
    def assign_reward(self, reward: float):
        """
        Call this after the frame's performance is known (e.g., after 5 ticks).
        Updates the bandit with the reward.
        """
        if self.last_features is not None and self.last_action is not None:
            self.bandit.update(self.last_features, self.last_action, reward)
            self.last_features = None
            self.last_action = None
    
    def compute_online_reward(self, context: FrameContext) -> float:
        """
        Compute a reward signal from the current context.
        This is called after each tick to update the bandit online.
        Reward = negative of (uncertainty + (1 - omega) + claim_falsification_rate)
        """
        state = context.current_state
        if state is None:
            return 0.0
        
        # Lower uncertainty is better
        uncertainty_bonus = 1.0 - state.uncertainty
        # Higher attunement is better
        omega_bonus = state.omega
        # Fewer falsifications is better (tracked in claim table)
        falsification_rate = 0.0
        total = 0
        for claim in context.claim_table.claims:
            total += 1
            if claim.status == "falsified":
                falsification_rate += 1
        if total > 0:
            falsification_rate /= total
        reward = 0.3 * uncertainty_bonus + 0.3 * omega_bonus + 0.4 * (1.0 - falsification_rate)
        # Reward is bounded [0, 1]
        return reward
