#!/usr/bin/env python3
"""
Co-Cradle Phase 1: Silent Multi-Modal Prediction
Minimal prototype of the Symbiotic Cognition Framework (SCF).

An AI agent observes a simulated human's sensory stream (vision, audio,
haptic, proprioception) and learns to predict the next sensory frame.
Surprise is detected in real time.

CC0 - No rights reserved.

STATUS: COMMITTED UNVERIFIED
----------------------------
This file requires torch, which was not available in the environment where
it was committed. Nobody has run it. Do not cite its output.

Two things to check on the first real run, both of which the audit in
`audit.md` predicts will be problems:

1. THE THRESHOLD SETS THE FLAG RATE, NOT THE DATA.
   `tau = mean + 2*std` over the surprise history flags roughly 2-5% of
   steps for any roughly-normal loss distribution, whatever the stream
   contains. A detector that fires at a fixed rate is measuring its own
   rule. Before reporting any surprise count as meaningful, run the null
   test at the bottom of this file: feed the same detector a structureless
   stream and confirm the flag rate collapses. If it does not, replace the
   rule with the EVT/GPD tail fit used in `asc_core.AnomalyDetector` and
   state the return period.

   This is the same defect class as NEG-7 in `Negentropic/` -- a number that
   comes out the same regardless of what it is pointed at.

2. THE MODEL TRAINS ON THE STEP IT IS SCORED ON.
   Loss is computed and then backpropagated on the same frame, so surprise
   falls simply because the model is fitting. That confounds learning with
   novelty. Hold the evaluation frame out of the update if the surprise
   trace is meant to mean anything.

What is sound here and worth keeping: the SimulatedHuman world. A hand whose
velocity sets an audio frequency and whose position determines contact
pressure is a genuinely multi-modal stream with real cross-modal structure
to discover, which is the hard part of building this kind of testbed.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque


# -------------------------------
# 1. Simulated World (the "human's" body and environment)
# -------------------------------
class SimulatedHuman:
    """
    Produces a synthetic multi-modal sensory stream.
    - Vision: a 2D binary image with a moving "hand" (a small square).
    - Audio: a tone whose frequency changes based on the hand's velocity.
    - Haptic: pressure when the hand touches a fixed object in the centre.
    - Proprioception: 2D position of the hand (normalised).
    """

    def __init__(self, img_size=16, seed=None):
        self.img_size = img_size
        self.rng = np.random.default_rng(seed)
        self.hand_pos = np.array([0.5, 0.5])
        self.velocity = np.array([0.0, 0.0])
        self.object_center = np.array([0.6, 0.6])
        self.object_radius = 0.15
        self.time_step = 0

    def step_world(self):
        self.velocity += self.rng.normal(0, 0.04, 2)
        self.velocity = np.clip(self.velocity, -0.15, 0.15)
        self.hand_pos = np.clip(self.hand_pos + self.velocity, 0.0, 1.0)
        self.time_step += 1

    def get_vision(self):
        img = np.zeros((self.img_size, self.img_size))
        x = int(self.hand_pos[0] * (self.img_size - 1))
        y = int(self.hand_pos[1] * (self.img_size - 1))
        img[x, y] = 1.0
        return img.flatten()

    def get_audio(self):
        speed = np.linalg.norm(self.velocity)
        freq = 200 + 400 * speed
        t = self.time_step * 0.1
        return np.array([np.sin(2 * np.pi * freq * t) * 0.5], dtype=np.float32)

    def get_haptic(self):
        dist = np.linalg.norm(self.hand_pos - self.object_center)
        if dist < self.object_radius:
            return np.array([1.0 - dist / self.object_radius], dtype=np.float32)
        return np.array([0.0], dtype=np.float32)

    def get_proprioception(self):
        return self.hand_pos.astype(np.float32)

    def sense(self):
        self.step_world()
        return {
            "vision": torch.tensor(self.get_vision(), dtype=torch.float32),
            "audio": torch.tensor(self.get_audio(), dtype=torch.float32),
            "haptic": torch.tensor(self.get_haptic(), dtype=torch.float32),
            "proprio": torch.tensor(self.get_proprioception(), dtype=torch.float32),
        }


# -------------------------------
# 2. AI Multi-Modal World Model Predictor
# -------------------------------
class MultiModalPredictor(nn.Module):
    """Ingests concatenated sensory streams at t and predicts t+1."""

    def __init__(self, vis_dim=256, aud_dim=1, hap_dim=1, prop_dim=2,
                 hidden_dim=64):
        super().__init__()
        self.total_input_dim = vis_dim + aud_dim + hap_dim + prop_dim
        self.encoder = nn.Sequential(
            nn.Linear(self.total_input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.head_vision = nn.Linear(hidden_dim, vis_dim)
        self.head_audio = nn.Linear(hidden_dim, aud_dim)
        self.head_haptic = nn.Linear(hidden_dim, hap_dim)
        self.head_proprio = nn.Linear(hidden_dim, prop_dim)

    def forward(self, x):
        h = self.encoder(x)
        return {
            "vision": self.head_vision(h),
            "audio": self.head_audio(h),
            "haptic": self.head_haptic(h),
            "proprio": self.head_proprio(h),
        }


# -------------------------------
# 3. Surprise threshold
# -------------------------------
def rolling_threshold(history, k=2.0, warmup=10, default=1.0):
    """tau = mean + k*std over the recent window.

    Kept as originally written so the null test below measures the rule that
    was actually proposed. For any roughly-normal loss this flags a fixed
    small fraction of steps regardless of the input -- see `null_test`.
    """
    if len(history) <= warmup:
        return default
    return float(np.mean(history) + k * np.std(history))


def null_test(trials=2000, k=2.0, window=50, seed=0):
    """Flag rate of the threshold rule on a structureless stream.

    If the rate here is close to the rate on real data, the detector is
    reporting its own threshold rather than anything about the world.
    Prints the fraction flagged for pure noise and for a drifting signal.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for label, stream in (
        ("white noise", rng.normal(1.0, 0.2, trials)),
        ("decaying loss", np.exp(-np.linspace(0, 3, trials))
         + rng.normal(0, 0.05, trials)),
    ):
        hist = deque(maxlen=window)
        flags = 0
        for value in stream:
            hist.append(float(value))
            if float(value) > rolling_threshold(list(hist), k=k):
                flags += 1
        out[label] = flags / trials
    return out


# -------------------------------
# 4. Execution & Surprise Loop
# -------------------------------
def run_co_cradle_simulation(steps=200, seed=0, verbose=True):
    human = SimulatedHuman(img_size=16, seed=seed)
    torch.manual_seed(seed)
    model = MultiModalPredictor()
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    mse = nn.MSELoss()

    history = deque(maxlen=50)
    prev_obs = human.sense()
    flagged = 0

    for t in range(steps):
        curr_obs = human.sense()
        x = torch.cat([prev_obs["vision"], prev_obs["audio"],
                       prev_obs["haptic"], prev_obs["proprio"]]).unsqueeze(0)

        preds = model(x)
        loss = sum(mse(preds[k], curr_obs[k].unsqueeze(0))
                   for k in ("vision", "audio", "haptic", "proprio"))
        surprise = loss.item()
        history.append(surprise)

        tau = rolling_threshold(list(history))
        is_anomaly = surprise > tau
        flagged += int(is_anomaly)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if verbose and (t % 20 == 0 or is_anomaly):
            mark = "  <- flagged" if is_anomaly else ""
            print(f"Step {t:3d} | surprise {surprise:.4f} | tau {tau:.4f}{mark}")

        prev_obs = curr_obs

    rate = flagged / steps
    if verbose:
        print(f"\nFlagged {flagged}/{steps} steps ({rate:.1%}).")
        print("Compare against the null test before calling any of these"
              " genuine surprises:")
        for label, null_rate in null_test().items():
            print(f"  {label:14s} flag rate {null_rate:.1%}")
        print("If the rates are comparable, the detector is measuring its"
              " own threshold rule.")
    return {"flag_rate": rate, "steps": steps}


if __name__ == "__main__":
    run_co_cradle_simulation()
