#!/usr/bin/env python3
"""
exploration_engine_complete.py — The Full Monolithic Meta‑Scientific Engine

A single‑file, drop‑in replacement for your exploration engine.
Includes:
  - All frames (Falsificationist, Bayesian, SemanticTube, Diffusion, LLMGated,
    Epistemic, Neurosymbolic, GeoAlgebraic, PyGeom, Routed, Resonance, Ensemble)
  - Safe AST parser (replaces eval)
  - Learned Router (contextual bandit with RL)
  - Stroboscopic Scheduler (for heavy frames)
  - Full FrameRouter with configurable switching
"""

import ast
import operator
import math
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional, List, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import deque
from datetime import datetime

# ============================================================
# SECTION 1: FRAME ID ENUM
# ============================================================
class FrameID(Enum):
    FALSIFICATIONIST = "falsificationist"
    BAYESIAN = "bayesian"
    SEMANTIC_TUBE = "semantic_tube"
    DIFFUSION = "diffusion"
    LLM_GATED = "llm_gated"
    EPISTEMIC = "epistemic"
    NEUROSYMBOLIC = "neurosymbolic"
    GEO_ALGEBRAIC = "geo_algebraic"
    PYGEOM = "pygeom"
    ROUTED = "routed"
    RESONANCE = "resonance"
    ENSEMBLE = "ensemble"

# ============================================================
# SECTION 2: SAFE AST PARSER (Replaces eval)
# ============================================================
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.IfExp: lambda cond, t, f: t if cond else f,
}

ALLOWED_NODE_TYPES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare,
    ast.BoolOp, ast.IfExp, ast.Name, ast.Constant,
    ast.Load, ast.List, ast.Tuple, ast.Dict, ast.Subscript,
    ast.Attribute, ast.Index, ast.Slice, ast.Call, ast.keyword,
)

class SafeEvaluator(ast.NodeVisitor):
    def __init__(self, locals_dict: Dict[str, Any]):
        self.locals = locals_dict
        self._allowed_names = set(locals_dict.keys()) | {"True", "False", "None", "abs", "len", "min", "max", "sum", "math"}
        self._math = math

    def visit(self, node):
        if not isinstance(node, ALLOWED_NODE_TYPES):
            raise ValueError(f"Disallowed node type: {type(node).__name__}")
        return super().visit(node)

    def visit_Constant(self, node: ast.Constant):
        return node.value

    def visit_Name(self, node: ast.Name):
        if node.id not in self._allowed_names:
            if node.id in self.locals:
                return self.locals[node.id]
            if node.id in dir(math):
                return getattr(math, node.id)
            raise ValueError(f"Variable '{node.id}' not allowed.")
        if node.id == "True": return True
        if node.id == "False": return False
        if node.id == "None": return None
        if node.id == "math": return math
        return self.locals.get(node.id, None)

    def visit_Attribute(self, node: ast.Attribute):
        obj = self.visit(node.value)
        if hasattr(obj, node.attr):
            return getattr(obj, node.attr)
        raise ValueError(f"Attribute '{node.attr}' not found.")

    def visit_Subscript(self, node: ast.Subscript):
        obj = self.visit(node.value)
        if isinstance(node.slice, ast.Index):
            idx = self.visit(node.slice.value)
        elif isinstance(node.slice, ast.Slice):
            lower = self.visit(node.slice.lower) if node.slice.lower else None
            upper = self.visit(node.slice.upper) if node.slice.upper else None
            step = self.visit(node.slice.step) if node.slice.step else None
            return obj[lower:upper:step]
        else:
            idx = self.visit(node.slice)
        return obj[idx]

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Binary operator {op_type.__name__} not allowed.")
        return ALLOWED_OPERATORS[op_type](left, right)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Unary operator {op_type.__name__} not allowed.")
        return ALLOWED_OPERATORS[op_type](operand)

    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        results = []
        for op, comp in zip(node.ops, node.comparators):
            right = self.visit(comp)
            op_type = type(op)
            if op_type not in ALLOWED_OPERATORS:
                raise ValueError(f"Comparison {op_type.__name__} not allowed.")
            results.append(ALLOWED_OPERATORS[op_type](left, right))
            left = right
        return all(results)

    def visit_BoolOp(self, node: ast.BoolOp):
        values = [self.visit(v) for v in node.values]
        op_type = type(node.op)
        if op_type not in ALLOWED_OPERATORS:
            raise ValueError(f"Boolean operator {op_type.__name__} not allowed.")
        result = values[0]
        for v in values[1:]:
            result = ALLOWED_OPERATORS[op_type](result, v)
        return result

    def visit_IfExp(self, node: ast.IfExp):
        cond = self.visit(node.test)
        return self.visit(node.body) if cond else self.visit(node.orelse)

    def visit_Call(self, node: ast.Call):
        func = self.visit(node.func)
        if func not in (abs, len, min, max, sum) and not hasattr(math, func.__name__):
            raise ValueError(f"Function call to '{func}' not allowed.")
        args = [self.visit(a) for a in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
        return func(*args, **kwargs)

    def visit_List(self, node: ast.List):
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple):
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_Dict(self, node: ast.Dict):
        return {self.visit(k): self.visit(v) for k, v in zip(node.keys, node.values)}

    def generic_visit(self, node):
        raise ValueError(f"Unsupported node type: {type(node).__name__}")

def safe_evaluate(condition_str: str, context: Dict[str, Any]) -> bool:
    try:
        tree = ast.parse(condition_str, mode="eval")
        evaluator = SafeEvaluator(context)
        result = evaluator.visit(tree.body)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Failed to evaluate condition '{condition_str}': {e}")

# ============================================================
# SECTION 3: CORE DATA CLASSES (ManifoldState, TrialResult)
# ============================================================
@dataclass
class ManifoldState:
    u: np.ndarray
    omega: float
    uncertainty: float
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrialResult:
    claim_id: str
    timestamp: str
    passed: bool
    scope_verified: bool
    bias_corrected_input: float
    raw_input: float
    confidence: float
    is_falsification: bool

@dataclass
class FrameContext:
    manifold: Any
    claim_table: Any
    llm_bridge: Any
    current_state: Optional[ManifoldState] = None
    sensor_type: str = "unknown"
    elapsed_ticks: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

# ============================================================
# SECTION 4: ABSTRACT BASE CLASS
# ============================================================
class ExplorationFrame(ABC):
    @property
    @abstractmethod
    def id(self) -> FrameID:
        pass

    @abstractmethod
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        pass

    @abstractmethod
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        pass

    @abstractmethod
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        pass

    @abstractmethod
    def update(self, context: FrameContext):
        pass

# ============================================================
# SECTION 5: ALL CONCRETE FRAMES
# ============================================================

# 5.1 Falsificationist (Popperian)
class FalsificationistFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.FALSIFICATIONIST

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        # Simplified: assume manifold has step_from_binary
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"loss_added": 0.0}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        return context.llm_bridge.generate(context.current_state, prompt)

    def update(self, context: FrameContext):
        context.manifold.train_on_window()
        context.claim_table.save()

# 5.2 Bayesian (continuous belief)
class BayesianFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.BAYESIAN

    def __init__(self):
        self.beliefs = {}

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"loss_added": 0.0}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            result = claim.evaluate(context.current_state, context.extra)
            if result.scope_verified:
                a, b = self.beliefs.get(claim.id, (1.0, 1.0))
                if result.passed:
                    a += 1.0
                else:
                    b += 1.0
                self.beliefs[claim.id] = (a, b)
                posterior_mean = a / (a + b)
                if posterior_mean < 0.1 and a + b > 5:
                    claim.status = "falsified"
            results.append(result)
        return results

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        belief_str = "; ".join([f"{cid}: p={a/(a+b):.2f}" for cid, (a,b) in self.beliefs.items()])
        full_prompt = f"{prompt} Current Bayesian beliefs: {belief_str}."
        return context.llm_bridge.generate(context.current_state, full_prompt)

    def update(self, context: FrameContext):
        context.manifold.train_on_window()
        context.claim_table.save()

# 5.3 Semantic Tube (STP regularizer)
class SemanticTubeFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.SEMANTIC_TUBE

    def __init__(self, tube_radius: float = 0.2):
        self.tube_radius = tube_radius

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        if len(context.manifold.binary_window) >= 5:
            u_tensor = context.manifold.get_latent_window()
            if u_tensor.shape[0] > 2:
                velocity = u_tensor[1:] - u_tensor[:-1]
                acceleration = velocity[1:] - velocity[:-1]
                tube_loss = torch.mean(torch.norm(acceleration, dim=1)) - self.tube_radius
                tube_loss = torch.relu(tube_loss) ** 2
                if hasattr(context.manifold, '_stp_loss'):
                    context.manifold._stp_loss = tube_loss
        return {"tube_loss_applied": True}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        return context.llm_bridge.generate(context.current_state, prompt)

    def update(self, context: FrameContext):
        context.manifold.train_on_window(stp_weight=0.3)
        context.claim_table.save()

# 5.4 Diffusion (Geometric Diffusion Bridge)
class DiffusionBridge(nn.Module):
    def __init__(self, d=2, hidden=16, n_steps=10):
        super().__init__()
        self.n_steps = n_steps
        self.denoiser = nn.Sequential(
            nn.Linear(d + 1, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, d)
        )
        self.noise_scale = nn.Parameter(torch.ones(1) * 0.1)

    def forward(self, u0: torch.Tensor, t: int) -> torch.Tensor:
        noise = torch.randn_like(u0) * self.noise_scale.abs() * (t / self.n_steps)
        return u0 + noise

    def reverse(self, ut: torch.Tensor, t: int) -> torch.Tensor:
        t_norm = torch.tensor([t / self.n_steps], device=ut.device).expand(ut.shape[0], 1)
        inp = torch.cat([ut, t_norm], dim=1)
        return self.denoiser(inp)

    def sample_trajectory(self, u0: torch.Tensor, steps: int) -> List[torch.Tensor]:
        trajectory = [u0]
        u = u0
        for t in range(1, steps+1):
            u = self.forward(u, t)
            trajectory.append(u)
        return trajectory

class DiffusionFrame(ExplorationFrame):
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
        if len(context.manifold.binary_window) >= 3:
            latents = context.manifold.get_latent_window()
            if latents.shape[0] > 2:
                for t in range(1, min(5, latents.shape[0])):
                    u0 = latents[-t-1].unsqueeze(0)
                    u1 = latents[-t].unsqueeze(0).detach()
                    ut = self.bridge.forward(u0, t)
                    u_hat = self.bridge.reverse(ut, t)
                    loss = F.mse_loss(u_hat, u1)
                    self.bridge_optimizer.zero_grad()
                    loss.backward()
                    self.bridge_optimizer.step()
        with torch.no_grad():
            traj = self.bridge.sample_trajectory(u_t, steps=5)
            self.trajectory_buffer.append([s.numpy() for s in traj])
            if len(self.trajectory_buffer) > 10:
                self.trajectory_buffer.pop(0)
        return {"diffusion_steps": 5}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        if not self.trajectory_buffer:
            return results
        latest_traj = self.trajectory_buffer[-1]
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            passed_count = 0
            for u_arr in latest_traj:
                traj_state = ManifoldState(u=u_arr, omega=0.5, uncertainty=0.2)
                result = claim.evaluate(traj_state, context.extra)
                if result.passed:
                    passed_count += 1
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
        if self.trajectory_buffer:
            latest = self.trajectory_buffer[-1]
            disp = f"Diffusion trajectory: from {latest[0]} to {latest[-1]}"
        else:
            disp = "No trajectory yet."
        return context.llm_bridge.generate(context.current_state, f"{prompt} {disp}")

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.5 LLM Gated (proposes claims)
class LLMGatedFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.LLM_GATED

    def __init__(self):
        self.proposed_claims = []

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        if context.elapsed_ticks % 10 == 0 and context.elapsed_ticks > 0:
            prompt = "Propose a new falsifiable claim about the current geometric state."
            hypothesis = context.llm_bridge.generate(state, prompt, max_new_tokens=30)
            self.proposed_claims.append(hypothesis)
        return {"hypotheses_generated": len(self.proposed_claims)}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        proposals = "; ".join(self.proposed_claims[-3:])
        return context.llm_bridge.generate(context.current_state, f"{prompt} Recently proposed: {proposals}.")

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.6 Epistemic (truth maintenance)
class EpistemicFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.EPISTEMIC

    def __init__(self):
        self.dependency_graph = {}

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"loss_added": 0.0}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = context.claim_table.test_all(context.current_state, context.extra)
        for i, r1 in enumerate(results):
            for r2 in results[i+1:]:
                if r1.claim_id != r2.claim_id and r1.passed != r2.passed:
                    if abs(r1.confidence - r2.confidence) < 0.1:
                        print(f"⚠️ Epistemic tension: {r1.claim_id} vs {r2.claim_id}")
        return results

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        return context.llm_bridge.generate(context.current_state, f"{prompt} Epistemic status: consistency enforced.")

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.7 Neurosymbolic (symbolic reduction)
class SymbolicReducer(nn.Module):
    def __init__(self, input_dim=64, codebook_size=8, code_dim=4):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, code_dim))
        self.decoder = nn.Sequential(nn.Linear(code_dim, 32), nn.ReLU(), nn.Linear(32, input_dim))
        self.codebook = nn.Parameter(torch.randn(codebook_size, code_dim))
        self.codebook_size = codebook_size

    def quantize(self, z: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
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
    @property
    def id(self) -> FrameID:
        return FrameID.NEUROSYMBOLIC

    def __init__(self):
        self.reducer = SymbolicReducer()
        self.reducer_optimizer = torch.optim.Adam(self.reducer.parameters(), lr=0.01)
        self.symbol_history = []

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        x = torch.tensor(binary_vec, dtype=torch.float32).unsqueeze(0)
        x_hat, indices = self.reducer(x)
        recon_loss = F.mse_loss(x_hat, x)
        z = self.reducer.encoder(x)
        z_q = self.reducer.codebook[indices]
        commit_loss = F.mse_loss(z.detach(), z_q) * 0.25
        total_loss = recon_loss + commit_loss
        self.reducer_optimizer.zero_grad()
        total_loss.backward()
        self.reducer_optimizer.step()
        self.symbol_history.append(indices.detach().numpy())
        if len(self.symbol_history) > 20:
            self.symbol_history.pop(0)
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"symbols": indices.detach().numpy().tolist()}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        if self.symbol_history:
            context.extra["symbols"] = self.symbol_history[-1]
            for claim in context.claim_table.claims:
                if claim.status in ["active", "deprecated"]:
                    result = claim.evaluate(context.current_state, context.extra)
                    claim.record_trial(result)
                    results.append(result)
        return results

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        sym_str = f"Recent symbols: {self.symbol_history[-1]}" if self.symbol_history else "No symbols yet."
        return context.llm_bridge.generate(context.current_state, f"{prompt} {sym_str}")

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.8 GeoAlgebraic (bijective mapping)
class GeoAlgebraicBridge(nn.Module):
    def __init__(self, input_dim=64, latent_dim=2):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, latent_dim))
        self.decoder = nn.Sequential(nn.Linear(latent_dim, 32), nn.ReLU(), nn.Linear(32, input_dim))

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        u = self.encoder(x)
        x_hat = self.decoder(u)
        return u, x_hat

class GeoAlgebraicFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.GEO_ALGEBRAIC

    def __init__(self):
        self.bridge = GeoAlgebraicBridge()
        self.bridge_optimizer = torch.optim.Adam(self.bridge.parameters(), lr=0.01)

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        x = torch.tensor(binary_vec, dtype=torch.float32).unsqueeze(0)
        u, x_hat = self.bridge(x)
        recon_loss = F.mse_loss(x_hat, x)
        unit_loss = F.relu(torch.norm(u, dim=1) - 1.0).mean()
        loss = recon_loss + 0.1 * unit_loss
        self.bridge_optimizer.zero_grad()
        loss.backward()
        self.bridge_optimizer.step()
        state = ManifoldState(u=u.detach().numpy()[0], omega=0.5, uncertainty=recon_loss.item())
        context.current_state = state
        return {"recon_loss": recon_loss.item()}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        for claim in context.claim_table.claims:
            if claim.status in ["active", "deprecated"]:
                result = claim.evaluate(context.current_state, context.extra)
                claim.record_trial(result)
                results.append(result)
        return results

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        u_str = f"Algebraic form: {context.current_state.u}" if context.current_state else "No algebraic form."
        return context.llm_bridge.generate(context.current_state, f"{prompt} {u_str}")

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.9 PyGeom (declarative geometric constraints)
class GeometryConstraint:
    @staticmethod
    def is_parallel(u1: np.ndarray, u2: np.ndarray, tol: float = 0.1) -> bool:
        v1 = u1[1] - u1[0]
        v2 = u2[1] - u2[0]
        return abs(np.cross(v1, v2)) < tol

    @staticmethod
    def is_perpendicular(u1: np.ndarray, u2: np.ndarray, tol: float = 0.1) -> bool:
        v1 = u1[1] - u1[0]
        v2 = u2[1] - u2[0]
        return abs(np.dot(v1, v2)) < tol

    @staticmethod
    def distance_between(u1: np.ndarray, u2: np.ndarray) -> float:
        return np.linalg.norm(u1 - u2)

class PyGeomFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.PYGEOM

    def __init__(self):
        self.constraints = {
            "parallel": GeometryConstraint.is_parallel,
            "perpendicular": GeometryConstraint.is_perpendicular,
            "distance_less_than": lambda u1, u2, thresh: GeometryConstraint.distance_between(u1, u2) < thresh,
        }

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"constraints_checked": 0}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        if not context.current_state:
            return results
        u = context.current_state.u
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            pred = claim.predicate
            if pred.get("type") in self.constraints:
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
        active_rels = [c.predicate.get("type", "unknown") for c in context.claim_table.claims if c.status == "active"]
        return context.llm_bridge.generate(context.current_state, f"{prompt} Active relations: {active_rels}")

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.10 Routed (multi-manifold fleet)
class RoutedFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.ROUTED

    def __init__(self):
        self.manifolds = {}
        self.current_manifold = None

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        sensor_type = context.sensor_type
        if sensor_type not in self.manifolds:
            self.manifolds[sensor_type] = context.manifold.__class__()  # clone architecture
        manifold = self.manifolds[sensor_type]
        self.current_manifold = sensor_type
        state = manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"routed_to": sensor_type}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        if not self.current_manifold:
            return []
        return context.claim_table.test_all(context.current_state, context.extra)

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        info = f"Active sensor: {self.current_manifold}; {len(self.manifolds)} manifolds."
        return context.llm_bridge.generate(context.current_state, f"{prompt} {info}")

    def update(self, context: FrameContext):
        for m in self.manifolds.values():
            m.train_on_window()
        context.claim_table.save()

# 5.11 Resonance (binary toggles generate geometry)
class ResonanceFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.RESONANCE

    def __init__(self, rule: int = 90):
        self.rule = rule

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        window = np.stack(context.manifold.binary_window[-5:]) if len(context.manifold.binary_window) >= 5 else None
        if window is not None:
            new_row = np.zeros_like(window[-1])
            for i in range(1, len(window[-1])-1):
                left = window[-1][i-1]
                center = window[-1][i]
                right = window[-1][i+1]
                idx = 4*left + 2*center + right
                new_row[i] = (self.rule >> idx) & 1
            context.manifold.binary_window.append(new_row)
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"rule_applied": self.rule}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        return context.llm_bridge.generate(context.current_state, prompt)

    def update(self, context: FrameContext):
        context.manifold.train_on_window()

# 5.12 Ensemble (runs all frames in parallel)
class EnsembleFrame(ExplorationFrame):
    @property
    def id(self) -> FrameID:
        return FrameID.ENSEMBLE

    def __init__(self):
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
            ResonanceFrame(),
        ]
        self.weights = {f.id: 1.0 for f in self.frames}

    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        results = {}
        for frame in self.frames:
            try:
                res = frame.process_primitive(context, binary_vec)
                results[frame.id.value] = res
            except Exception as e:
                results[frame.id.value] = {"error": str(e)}
        return {"ensemble_results": results}

    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        all_results = []
        for frame in self.frames:
            all_results.extend(frame.evaluate_claims(context))
        claim_support = {}
        for res in all_results:
            cid = res.claim_id
            if cid not in claim_support:
                claim_support[cid] = {"pass": 0.0, "total": 0.0}
            weight = self.weights.get(frame.id, 1.0)
            claim_support[cid]["total"] += weight
            if res.passed:
                claim_support[cid]["pass"] += weight
        final_results = []
        for cid, stats in claim_support.items():
            passed = (stats["pass"] / stats["total"]) > 0.5
            confidence = stats["pass"] / stats["total"]
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
            claim = context.claim_table.get_claim(cid)
            if claim:
                claim.record_trial(result)
            final_results.append(result)
        return final_results

    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        narratives = []
        for frame in self.frames:
            try:
                narratives.append(f"[{frame.id.value}] {frame.generate_narrative(context, prompt)}")
            except:
                narratives.append(f"[{frame.id.value}] (error)")
        return "Ensemble synthesis:\n" + "\n".join(narratives)

    def update(self, context: FrameContext):
        for frame in self.frames:
            try:
                if hasattr(context, 'manifold') and hasattr(context.manifold, 'get_latent_window'):
                    latents = context.manifold.get_latent_window()
                    if len(latents) > 1:
                        perf = 1.0 - F.mse_loss(latents[-2], latents[-1]).item()
                        self.weights[frame.id] = max(0.1, self.weights[frame.id] * 0.9 + 0.1 * perf)
            except:
                pass
            frame.update(context)
        total = sum(self.weights.values())
        self.weights = {k: v/total for k, v in self.weights.items()}
        context.claim_table.save()

# ============================================================
# SECTION 6: LEARNED ROUTER (Contextual Bandit)
# ============================================================
class LinearBandit(nn.Module):
    def __init__(self, n_features: int = 6, n_actions: int = 12, epsilon: float = 0.1, lr: float = 0.01):
        super().__init__()
        self.n_features = n_features
        self.n_actions = n_actions
        self.epsilon = epsilon
        self.W = nn.Parameter(torch.randn(n_features, n_actions) * 0.01)
        self.optimizer = torch.optim.Adam([self.W], lr=lr)
        self.replay_buffer = deque(maxlen=2000)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return features @ self.W

    def select_action(self, features: torch.Tensor) -> int:
        if np.random.rand() < self.epsilon:
            return np.random.randint(self.n_actions)
        with torch.no_grad():
            scores = self.forward(features)
            return torch.argmax(scores, dim=0).item()

    def update(self, features: torch.Tensor, action: int, reward: float):
        self.replay_buffer.append((features.clone(), action, reward))
        if len(self.replay_buffer) >= 32:
            self._train_batch()

    def _train_batch(self, batch_size: int = 32):
        indices = np.random.choice(len(self.replay_buffer), min(batch_size, len(self.replay_buffer)), replace=False)
        batch = [self.replay_buffer[i] for i in indices]
        features = torch.stack([b[0] for b in batch])
        actions = torch.tensor([b[1] for b in batch], dtype=torch.long)
        rewards = torch.tensor([b[2] for b in batch], dtype=torch.float32)
        scores = self.forward(features)
        log_probs = F.log_softmax(scores, dim=1)
        selected_log_probs = log_probs.gather(1, actions.unsqueeze(1)).squeeze()
        loss = -(selected_log_probs * rewards).mean()
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

class LearnedRouter:
    def __init__(self):
        self.bandit = LinearBandit(
            n_features=6,
            n_actions=len(FrameID),
            epsilon=0.15,
            lr=0.01
        )
        self.frame_id_to_idx = {fid: i for i, fid in enumerate(FrameID)}
        self.idx_to_frame_id = {i: fid for fid, i in self.frame_id_to_idx.items()}
        self.last_features = None
        self.last_action = None

    def extract_features(self, context: FrameContext) -> torch.Tensor:
        state = context.current_state
        uncertainty = state.uncertainty if state else 0.5
        omega = state.omega if state else 0.5
        elapsed = context.elapsed_ticks / 100.0
        claim_density = len(context.claim_table.claims) / 10.0
        if hasattr(context.manifold, 'binary_window') and context.manifold.binary_window:
            recent = np.stack(context.manifold.binary_window[-5:])
            p = recent.mean() if recent.size > 0 else 0.5
            entropy = -(p * np.log(p+1e-6) + (1-p)*np.log(1-p+1e-6))
        else:
            entropy = 1.0
        sensor_embed = hash(context.sensor_type) % 10 / 10.0 if context.sensor_type else 0.0
        return torch.tensor([uncertainty, omega, elapsed, claim_density, entropy, sensor_embed], dtype=torch.float32)

    def choose_frame(self, context: FrameContext) -> FrameID:
        features = self.extract_features(context)
        action_idx = self.bandit.select_action(features)
        self.last_features = features
        self.last_action = action_idx
        return self.idx_to_frame_id[action_idx]

    def assign_reward(self, reward: float):
        if self.last_features is not None and self.last_action is not None:
            self.bandit.update(self.last_features, self.last_action, reward)
            self.last_features = None
            self.last_action = None

    def compute_online_reward(self, context: FrameContext) -> float:
        state = context.current_state
        if not state:
            return 0.0
        uncertainty_bonus = 1.0 - state.uncertainty
        omega_bonus = state.omega
        falsification_rate = sum(1 for c in context.claim_table.claims if c.status == "falsified") / max(1, len(context.claim_table.claims))
        return 0.3 * uncertainty_bonus + 0.3 * omega_bonus + 0.4 * (1.0 - falsification_rate)

# ============================================================
# SECTION 7: STROBOSCOPIC SCHEDULER
# ============================================================
class StroboscopicScheduler:
    def __init__(self, heavy_frames: Set[FrameID], interval: int = 10):
        self.heavy_frames = heavy_frames
        self.interval = interval
        self.current_tick = 0
        self.last_heavy_results = {}

    def should_run(self, frame_id: FrameID) -> bool:
        if frame_id in self.heavy_frames:
            return (self.current_tick % self.interval) == 0
        return True

    def run_frame(self, frame: ExplorationFrame, context: FrameContext, binary_vec: np.ndarray) -> Dict:
        if frame.id in self.heavy_frames:
            if self.should_run(frame.id):
                result = {
                    "metrics": frame.process_primitive(context, binary_vec),
                    "trial_results": frame.evaluate_claims(context),
                    "narrative": frame.generate_narrative(context, "Frame state")
                }
                self.last_heavy_results[frame.id] = result
                frame.update(context)
                return result
            else:
                return self.last_heavy_results.get(frame.id, {
                    "metrics": {"cached": True},
                    "trial_results": [],
                    "narrative": "[Cached]"
                })
        else:
            result = {
                "metrics": frame.process_primitive(context, binary_vec),
                "trial_results": frame.evaluate_claims(context),
                "narrative": frame.generate_narrative(context, "Frame state")
            }
            frame.update(context)
            return result

    def tick(self):
        self.current_tick += 1

# ============================================================
# SECTION 8: FRAME ROUTER (Master Controller)
# ============================================================
class FrameRouter:
    def __init__(self, config_path: Optional[Path] = None, use_learned_router: bool = False):
        self.frames: Dict[FrameID, ExplorationFrame] = {}
        self.active_frame_id: Optional[FrameID] = None
        self.default_frame = FrameID.FALSIFICATIONIST
        self.use_learned_router = use_learned_router
        self.learned_router = LearnedRouter() if use_learned_router else None
        self.scheduler = StroboscopicScheduler(
            heavy_frames={FrameID.DIFFUSION, FrameID.ENSEMBLE, FrameID.SEMANTIC_TUBE},
            interval=10
        )
        self.history = []

        # Register all frames
        self.register(FalsificationistFrame())
        self.register(BayesianFrame())
        self.register(SemanticTubeFrame())
        self.register(DiffusionFrame())
        self.register(LLMGatedFrame())
        self.register(EpistemicFrame())
        self.register(NeurosymbolicFrame())
        self.register(GeoAlgebraicFrame())
        self.register(PyGeomFrame())
        self.register(RoutedFrame())
        self.register(ResonanceFrame())
        self.register(EnsembleFrame())

        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.active_frame_id = FrameID(config.get("active_frame", "falsificationist"))
        else:
            self.active_frame_id = self.default_frame

    def register(self, frame: ExplorationFrame):
        self.frames[frame.id] = frame

    def switch_to(self, frame_id: FrameID, reason: str = "manual"):
        if frame_id in self.frames:
            self.active_frame_id = frame_id
            self.history.append({"timestamp": datetime.utcnow().isoformat(), "frame": frame_id.value, "reason": reason})
            print(f"🔄 Switched to frame: {frame_id.value} ({reason})")
        else:
            raise ValueError(f"Frame {frame_id} not registered.")

    def get_active_frame(self) -> ExplorationFrame:
        return self.frames.get(self.active_frame_id, self.frames[self.default_frame])

    def choose_frame(self, context: FrameContext) -> FrameID:
        if self.use_learned_router and self.learned_router:
            return self.learned_router.choose_frame(context)
        else:
            return self._heuristic_choose(context)

    def _heuristic_choose(self, context: FrameContext) -> FrameID:
        state = context.current_state
        scores = {}
        if state:
            scores[FrameID.BAYESIAN] = state.uncertainty
            scores[FrameID.FALSIFICATIONIST] = 0.5 + 0.5 * (context.claim_table.meta.get("binary_clarity", 0.5))
            scores[FrameID.SEMANTIC_TUBE] = 0.7 if context.elapsed_ticks > 10 else 0.2
            scores[FrameID.EPISTEMIC] = 0.8 if len(context.claim_table.claims) > 3 else 0.2
            scores[FrameID.LLM_GATED] = 0.9 if context.elapsed_ticks < 20 else 0.1
            if context.manifold.binary_window:
                recent = np.stack(context.manifold.binary_window[-5:])
                entropy = -(recent.mean() * np.log(recent.mean()+1e-6) + (1-recent.mean())*np.log(1-recent.mean()+1e-6))
                scores[FrameID.RESONANCE] = 1.0 - entropy
            else:
                scores[FrameID.RESONANCE] = 0.1
        else:
            scores = {fid: 0.3 for fid in FrameID}
        return max(scores, key=scores.get)

    def assign_router_reward(self, context: FrameContext):
        if self.use_learned_router and self.learned_router:
            reward = self.learned_router.compute_online_reward(context)
            self.learned_router.assign_reward(reward)

    def step(self, context: FrameContext, binary_vec: Optional[np.ndarray] = None,
             force_frame: Optional[FrameID] = None) -> Dict:
        self.scheduler.tick()
        context.elapsed_ticks += 1

        if force_frame:
            chosen_id = force_frame
        else:
            chosen_id = self.choose_frame(context)

        if chosen_id != self.active_frame_id:
            self.switch_to(chosen_id, reason="automatic" if not force_frame else "forced")

        frame = self.get_active_frame()
        if binary_vec is None:
            binary_vec = np.random.binomial(1, 0.5, size=(64,)).astype(np.float32)

        # Run through scheduler
        frame_result = self.scheduler.run_frame(frame, context, binary_vec)
        result = {
            "active_frame": self.active_frame_id.value,
            "metrics": frame_result["metrics"],
            "trial_results": frame_result["trial_results"],
            "narrative": frame_result["narrative"],
            "scores": {}  # for debugging
        }

        # Assign reward if using learned router
        if self.use_learned_router:
            self.assign_router_reward(context)

        return result

# ============================================================
# SECTION 9: SELF-TEST
# ============================================================
if __name__ == "__main__":
    # Mock objects for testing
    class MockManifold:
        def step_from_binary(self, binary_vec):
            return ManifoldState(u=np.random.randn(2), omega=0.5, uncertainty=0.2)
        def train_on_window(self, stp_weight=0.0):
            pass
        def get_latent_window(self):
            return torch.randn(5, 2)
        binary_window = [np.random.binomial(1, 0.5, size=(64,)) for _ in range(5)]

    class MockClaimTable:
        claims = []
        meta = {"binary_clarity": 0.7}
        def test_all(self, state, extra): return []
        def save(self): pass
        def get_claim(self, cid): return None

    class MockLLMBridge:
        def generate(self, state, prompt, max_new_tokens=30):
            return f"Mock narrative for: {prompt[:20]}..."

    context = FrameContext(
        manifold=MockManifold(),
        claim_table=MockClaimTable(),
        llm_bridge=MockLLMBridge(),
        elapsed_ticks=0
    )

    router = FrameRouter(use_learned_router=True)
    for i in range(15):
        result = router.step(context)
        print(f"Tick {i}: {result['active_frame']} -> {result['narrative'][:40]}...")
