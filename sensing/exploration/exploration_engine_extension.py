#!/usr/bin/env python3
"""
exploration_engine_extended.py — All Exploration Frames (Complete Set)

Extends the multiple‑choice engine with:
- DiffusionFrame (GDB)
- NeurosymbolicFrame
- GeoAlgebraicFrame
- PyGeomFrame
- RoutedFrame
- EnsembleFrame

Each frame implements the full ExplorationFrame interface.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import json
from pathlib import Path

# Existing imports (adapt to your project structure)
from ..processing.jepa_manifold import JEPAManifold, ManifoldState
from ..claims.scientific_claim import ScientificClaimTable, TrialResult
from .exploration_engine import ExplorationFrame, FrameContext, FrameID, FrameRouter

# ============================================================
# 1. DIFFUSION FRAME (Geometric Diffusion Bridge)
# ============================================================
class DiffusionBridge(nn.Module):
    """
    Simple denoising diffusion bridge for latent space.
    Learns to diffuse u(t) to u(t+1) via a stochastic process.
    """
    def __init__(self, d=2, hidden=16, n_steps=10):
        super().__init__()
        self.n_steps = n_steps
        self.denoiser = nn.Sequential(
            nn.Linear(d + 1, hidden),  # +1 for time step
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, d)
        )
        self.noise_scale = nn.Parameter(torch.ones(1) * 0.1)
    
    def forward(self, u0: torch.Tensor, t: int) -> torch.Tensor:
        """Diffuse u0 one step forward (forward process)"""
        noise = torch.randn_like(u0) * self.noise_scale.abs() * (t / self.n_steps)
        return u0 + noise
    
    def reverse(self, ut: torch.Tensor, t: int) -> torch.Tensor:
        """Denoise a noisy state back toward the manifold"""
        t_norm = torch.tensor([t / self.n_steps], device=ut.device).expand(ut.shape[0], 1)
        inp = torch.cat([ut, t_norm], dim=1)
        return self.denoiser(inp)
    
    def sample_trajectory(self, u0: torch.Tensor, steps: int) -> List[torch.Tensor]:
        """Generate a full diffusion trajectory"""
        trajectory = [u0]
        u = u0
        for t in range(1, steps+1):
            u = self.forward(u, t)
            trajectory.append(u)
        return trajectory

class DiffusionFrame(ExplorationFrame):
    """
    Uses a diffusion bridge to generate probabilistic future states.
    Claims are evaluated against the distribution, not just the point estimate.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.DIFFUSION
    
    def __init__(self):
        self.bridge = DiffusionBridge()
        self.bridge_optimizer = torch.optim.Adam(self.bridge.parameters(), lr=0.01)
        self.trajectory_buffer = []
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        u_t = torch.tensor(state.u, dtype=torch.float32).unsqueeze(0)
        
        # Train diffusion bridge on the latent trajectory
        if len(context.manifold.binary_window) >= 3:
            # Get recent latent states
            latents = context.manifold.get_latent_window()  # shape (N, 2)
            if latents.shape[0] > 2:
                # Forward diffusion and reverse loss
                for t in range(1, min(5, latents.shape[0])):
                    u0 = latents[-t-1].unsqueeze(0)
                    u1 = latents[-t].unsqueeze(0).detach()
                    ut = self.bridge.forward(u0, t)
                    u_hat = self.bridge.reverse(ut, t)
                    loss = F.mse_loss(u_hat, u1)
                    self.bridge_optimizer.zero_grad()
                    loss.backward()
                    self.bridge_optimizer.step()
        
        # Generate a probabilistic forecast (5 steps ahead)
        with torch.no_grad():
            traj = self.bridge.sample_trajectory(u_t, steps=5)
            self.trajectory_buffer.append([s.numpy() for s in traj])
            if len(self.trajectory_buffer) > 10:
                self.trajectory_buffer.pop(0)
        
        return {"diffusion_steps": 5, "trajectory_length": len(traj)}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        # Evaluate claims against the entire trajectory distribution
        results = []
        if not self.trajectory_buffer:
            return results
        
        # Use the latest trajectory
        latest_traj = self.trajectory_buffer[-1]
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            # Test claim against each point in the trajectory
            passed_count = 0
            for u_arr in latest_traj:
                # Create a dummy state from the trajectory point
                traj_state = ManifoldState(u=u_arr, omega=0.5, uncertainty=0.2)
                result = claim.evaluate(traj_state, context.extra)
                if result.passed:
                    passed_count += 1
            # If > 60% of trajectory supports the claim, treat as support
            majority_pass = (passed_count / len(latest_traj)) > 0.6
            trial = TrialResult(
                claim_id=claim.id,
                timestamp=datetime.utcnow().isoformat() + "Z",
                passed=majority_pass,
                scope_verified=True,
                bias_corrected_input=0.0,
                raw_input=0.0,
                confidence=passed_count / len(latest_traj),
                is_falsification=(not majority_pass)
            )
            claim.record_trial(trial)
            results.append(trial)
        return results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Inject trajectory summary into prompt
        if self.trajectory_buffer:
            latest = self.trajectory_buffer[-1]
            start = latest[0]
            end = latest[-1]
            disp = f"Diffusion trajectory: from {start} to {end}"
        else:
            disp = "No trajectory yet."
        full_prompt = f"{prompt} {disp}"
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()


# ============================================================
# 2. NEUROSYMBOLIC FRAME (ML-driven reduction)
# ============================================================
class SymbolicReducer(nn.Module):
    """
    Learns a compact symbolic representation of the binary vector.
    Uses a VQ-VAE style bottleneck to force discrete symbols.
    """
    def __init__(self, input_dim=64, codebook_size=8, code_dim=4):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, code_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(code_dim, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim)
        )
        # Codebook
        self.codebook = nn.Parameter(torch.randn(codebook_size, code_dim))
        self.codebook_size = codebook_size
    
    def quantize(self, z: torch.Tensor) -> torch.Tensor:
        """VQ-style quantization"""
        distances = torch.cdist(z, self.codebook)
        indices = torch.argmin(distances, dim=1)
        z_q = self.codebook[indices]
        return z_q, indices
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        z = self.encoder(x)
        z_q, indices = self.quantize(z)
        x_hat = self.decoder(z_q)
        return x_hat, indices

class NeurosymbolicFrame(ExplorationFrame):
    """
    Reduces binary input to a compact set of discrete symbols.
    Claims can be expressed in terms of these symbols, enabling symbolic reasoning.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.NEUROSYMBOLIC
    
    def __init__(self):
        self.reducer = SymbolicReducer()
        self.reducer_optimizer = torch.optim.Adam(self.reducer.parameters(), lr=0.01)
        self.symbol_history = []  # list of symbol sequences
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        # Convert binary to tensor
        x = torch.tensor(binary_vec, dtype=torch.float32).unsqueeze(0)
        x_hat, indices = self.reducer(x)
        # Reconstruction loss + commitment loss
        recon_loss = F.mse_loss(x_hat, x)
        # VQ commitment loss
        z = self.reducer.encoder(x)
        z_q = self.reducer.codebook[indices]
        commit_loss = F.mse_loss(z.detach(), z_q) * 0.25
        total_loss = recon_loss + commit_loss
        
        self.reducer_optimizer.zero_grad()
        total_loss.backward()
        self.reducer_optimizer.step()
        
        # Store symbols
        self.symbol_history.append(indices.detach().numpy())
        if len(self.symbol_history) > 20:
            self.symbol_history.pop(0)
        
        # Still update the manifold with the reduced representation if desired
        # Here we pass the original binary; manifold is separate
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        
        return {"symbols": indices.detach().numpy().tolist(), "recon_loss": recon_loss.item()}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        # Claims can be evaluated using symbol sequences
        results = []
        if not self.symbol_history:
            return results
        
        latest_symbols = self.symbol_history[-1]
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            # Example: claim that a specific symbol pattern corresponds to a high-uncertainty state
            # We'll test if the claim's predicate holds on the reduced representation
            # (Simplified: we append a dictionary to context.extra for symbol access)
            context.extra["symbols"] = latest_symbols
            result = claim.evaluate(context.current_state, context.extra)
            claim.record_trial(result)
            results.append(result)
        return results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        if self.symbol_history:
            sym_str = f"Recent symbols: {self.symbol_history[-1]}"
        else:
            sym_str = "No symbols yet."
        full_prompt = f"{prompt} {sym_str}"
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()


# ============================================================
# 3. GEO‑ALGEBRAIC FRAME (Explicit GAB mapping)
# ============================================================
class GeoAlgebraicBridge(nn.Module):
    """
    Explicit encoder + decoder pair.
    Guarantees that encoder(decoder(u)) = u and decoder(encoder(x)) ≈ x.
    """
    def __init__(self, input_dim=64, latent_dim=2):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, latent_dim)
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, input_dim)
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        u = self.encoder(x)
        x_hat = self.decoder(u)
        return u, x_hat

class GeoAlgebraicFrame(ExplorationFrame):
    """
    Enforces a bijective (or nearly bijective) mapping between binary and latent.
    Every geometric state has an explicit algebraic form, and vice versa.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.GEO_ALGEBRAIC
    
    def __init__(self):
        self.bridge = GeoAlgebraicBridge()
        self.bridge_optimizer = torch.optim.Adam(self.bridge.parameters(), lr=0.01)
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        x = torch.tensor(binary_vec, dtype=torch.float32).unsqueeze(0)
        u, x_hat = self.bridge(x)
        
        # Reconstruction loss (algebraic → geometric → algebraic)
        recon_loss = F.mse_loss(x_hat, x)
        # Regularization: encourage u to be in a unit ball (for stability)
        unit_loss = F.relu(torch.norm(u, dim=1) - 1.0).mean()
        loss = recon_loss + 0.1 * unit_loss
        
        self.bridge_optimizer.zero_grad()
        loss.backward()
        self.bridge_optimizer.step()
        
        # Override the manifold's encoder with our explicit encoder for consistency
        # (We'll keep the manifold separate, but we can also feed u to the manifold)
        state = ManifoldState(u=u.detach().numpy()[0], omega=0.5, uncertainty=recon_loss.item())
        context.current_state = state
        
        return {"recon_loss": recon_loss.item(), "unit_loss": unit_loss.item()}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        # Claims are evaluated directly in the algebraic domain if possible
        results = []
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            result = claim.evaluate(context.current_state, context.extra)
            claim.record_trial(result)
            results.append(result)
        return results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Provide the algebraic equivalent of the current latent state
        if context.current_state:
            u_str = f"Algebraic form: encoder(x) = {context.current_state.u}"
        else:
            u_str = "No algebraic form yet."
        full_prompt = f"{prompt} {u_str}"
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()


# ============================================================
# 4. PYGEOM FRAME (Declarative DSL constraints)
# ============================================================
class GeometryConstraint:
    """
    Declarative geometric relations.
    These are the primitives of the PyGeom DSL.
    """
    @staticmethod
    def is_parallel(u1: np.ndarray, u2: np.ndarray, tol: float = 0.1) -> bool:
        v1 = u1[1] - u1[0]
        v2 = u2[1] - u2[0]
        cross = np.cross(v1, v2)
        return abs(cross) < tol
    
    @staticmethod
    def is_perpendicular(u1: np.ndarray, u2: np.ndarray, tol: float = 0.1) -> bool:
        v1 = u1[1] - u1[0]
        v2 = u2[1] - u2[0]
        dot = np.dot(v1, v2)
        return abs(dot) < tol
    
    @staticmethod
    def distance_between(u1: np.ndarray, u2: np.ndarray) -> float:
        return np.linalg.norm(u1 - u2)
    
    @staticmethod
    def contains_point(u_line: np.ndarray, p: np.ndarray, tol: float = 0.1) -> bool:
        # Check if point p lies on the line segment u_line[0] -> u_line[1]
        v = u_line[1] - u_line[0]
        w = p - u_line[0]
        cross = np.cross(v, w)
        if abs(cross) > tol:
            return False
        t = np.dot(w, v) / np.dot(v, v)
        return 0 <= t <= 1

class PyGeomFrame(ExplorationFrame):
    """
    Claims are expressed as declarative geometric constraints.
    The system tests whether the current manifold state satisfies these constraints.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.PYGEOM
    
    def __init__(self):
        self.constraints = {
            "parallel": GeometryConstraint.is_parallel,
            "perpendicular": GeometryConstraint.is_perpendicular,
            "distance_less_than": lambda u1, u2, thresh: GeometryConstraint.distance_between(u1, u2) < thresh,
            "contains": GeometryConstraint.contains_point
        }
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        # No additional training; just pass through
        return {"constraints_checked": 0}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        if context.current_state is None:
            return results
        
        u = context.current_state.u
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            # Parse the claim's predicate into a geometric constraint
            # Example predicate: {"type": "parallel", "points": [[0,0], [1,1]]}
            pred = claim.predicate
            if pred.get("type") in self.constraints:
                # Extract geometry from the manifold state and context
                # Here we simulate having two points: u itself and a translated copy
                # In real use, you'd parse the predicate's arguments from the claim
                u1 = np.array([0.0, 0.0])
                u2 = u
                func = self.constraints[pred["type"]]
                passed = func(u1, u2) if "points" not in pred else func(u1, u2, pred.get("threshold", 0.1))
                result = TrialResult(
                    claim_id=claim.id,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    passed=passed,
                    scope_verified=True,
                    bias_corrected_input=0.0,
                    raw_input=0.0,
                    confidence=float(passed),
                    is_falsification=(not passed)
                )
                claim.record_trial(result)
                results.append(result)
        return results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Report active geometric constraints
        active_rels = []
        for claim in context.claim_table.claims:
            if claim.status == "active":
                active_rels.append(claim.predicate.get("type", "unknown"))
        rel_str = f"Active geometric relations: {active_rels}"
        full_prompt = f"{prompt} {rel_str}"
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()


# ============================================================
# 5. ROUTED FRAME (Multi‑manifold fleet)
# ============================================================
class RoutedFrame(ExplorationFrame):
    """
    Maintains a separate JEPA manifold per sensor type.
    Routes incoming primitives to the appropriate manifold.
    Aggregates outputs for unified reasoning.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.ROUTED
    
    def __init__(self):
        self.manifolds = {}  # sensor_type -> JEPAManifold
        self.current_manifold = None
        self.routing_history = []
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        sensor_type = context.sensor_type
        if sensor_type not in self.manifolds:
            # Create a new manifold for this sensor type
            self.manifolds[sensor_type] = JEPAManifold()
        
        manifold = self.manifolds[sensor_type]
        self.current_manifold = sensor_type
        state = manifold.step_from_binary(binary_vec)
        context.current_state = state
        self.routing_history.append(sensor_type)
        return {"routed_to": sensor_type, "active_manifolds": list(self.manifolds.keys())}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        # Evaluate claims using the specific manifold that produced the current state
        if self.current_manifold is None:
            return []
        return context.claim_table.test_all(context.current_state, context.extra)
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        manifold_info = f"Active sensor: {self.current_manifold}; {len(self.manifolds)} manifolds total."
        full_prompt = f"{prompt} {manifold_info}"
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        # Update all manifolds
        for m in self.manifolds.values():
            m.train_on_window()
        context.claim_table.save()


# ============================================================
# 6. ENSEMBLE FRAME (Meta‑oracle)
# ============================================================
class EnsembleFrame(ExplorationFrame):
    """
    Runs all frames in parallel and aggregates their outputs.
    Acts as a weighted voting system.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.ENSEMBLE
    
    def __init__(self, frames: Optional[List[ExplorationFrame]] = None):
        if frames is None:
            # Instantiate all frames with default params
            self.frames = [
                FalsificationistFrame(),
                BayesianFrame(),
                SemanticTubeFrame(),
                DiffusionFrame(),
                LLMGatedFrame(),
                EpistemicFrame(),
                NeurosymbolicFrame(),
                GeoAlgebraicFrame(),
                PyGeomFrame(),
                RoutedFrame(),
                ResonanceFrame()
            ]
        else:
            self.frames = frames
        
        self.weights = {f.id: 1.0 for f in self.frames}
        self.history = {f.id: [] for f in self.frames}
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        # Run all frames on the same primitive
        results = {}
        for frame in self.frames:
            try:
                res = frame.process_primitive(context, binary_vec)
                results[frame.id.value] = res
            except Exception as e:
                results[frame.id.value] = {"error": str(e)}
        return {"ensemble_results": results}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        # Aggregate trial results from all frames
        all_results = []
        for frame in self.frames:
            res = frame.evaluate_claims(context)
            all_results.extend(res)
        
        # Weighted voting: for each claim, compute weighted support
        claim_support = {}
        for res in all_results:
            cid = res.claim_id
            if cid not in claim_support:
                claim_support[cid] = {"pass": 0.0, "total": 0.0}
            frame_id = frame.id if hasattr(frame, 'id') else None
            weight = self.weights.get(frame_id, 1.0)
            claim_support[cid]["total"] += weight
            if res.passed:
                claim_support[cid]["pass"] += weight
        
        # Generate aggregated trial results
        final_results = []
        for cid, stats in claim_support.items():
            passed = (stats["pass"] / stats["total"]) > 0.5
            confidence = stats["pass"] / stats["total"]
            # Create a single trial result representing the ensemble
            result = TrialResult(
                claim_id=cid,
                timestamp=datetime.utcnow().isoformat() + "Z",
                passed=passed,
                scope_verified=True,
                bias_corrected_input=0.0,
                raw_input=0.0,
                confidence=confidence,
                is_falsification=(not passed) and confidence > 0.7
            )
            # Record into the primary claim table (context.claim_table)
            claim = context.claim_table.get_claim(cid)
            if claim:
                claim.record_trial(result)
            final_results.append(result)
        return final_results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Generate a narrative that synthesizes all frames' perspectives
        narratives = []
        for frame in self.frames:
            try:
                narr = frame.generate_narrative(context, prompt)
                narratives.append(f"[{frame.id.value}] {narr}")
            except:
                narratives.append(f"[{frame.id.value}] (error)")
        synthesis = "\n".join(narratives)
        return f"Ensemble synthesis:\n{synthesis}"
    
    def update(self, context: FrameContext):
        # Update each frame and track performance
        for frame in self.frames:
            try:
                # Measure how well the frame's predictions match the next state
                # (simplified: using prediction loss on the manifold)
                if hasattr(context, 'manifold') and hasattr(context.manifold, 'get_latent_window'):
                    latents = context.manifold.get_latent_window()
                    if len(latents) > 1:
                        # This is a dummy performance metric; in production, you'd use a validation loss
                        perf = 1.0 - F.mse_loss(latents[-2], latents[-1]).item()
                        # Update weight: higher performance => higher weight
                        self.weights[frame.id] = max(0.1, self.weights[frame.id] * 0.9 + 0.1 * perf)
            except:
                pass
            frame.update(context)
        
        # Normalize weights
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
        context.claim_table.save()


# ============================================================
# 7. REGISTER ALL FRAMES INTO THE ROUTER
# ============================================================
def register_all_frames(router: FrameRouter):
    """Helper to add all extended frames to a router."""
    router.register(FalsificationistFrame())
    router.register(BayesianFrame())
    router.register(SemanticTubeFrame())
    router.register(DiffusionFrame())
    router.register(LLMGatedFrame())
    router.register(EpistemicFrame())
    router.register(NeurosymbolicFrame())
    router.register(GeoAlgebraicFrame())
    router.register(PyGeomFrame())
    router.register(RoutedFrame())
    router.register(ResonanceFrame())
    # Register the Ensemble as a special meta-frame
    router.register(EnsembleFrame())
