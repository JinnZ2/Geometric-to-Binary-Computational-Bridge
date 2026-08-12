#!/usr/bin/env python3
"""
exploration_engine.py — Multiple‑Choice Frame Switch Engine

Allows the Geometric Bridge to dynamically switch between scientific paradigms:
- Falsificationist (Popper)
- Bayesian (continuous belief)
- Geometric (STP, GDB, Resonance)
- Epistemic (truth maintenance)
- Neurosymbolic (reduction)
- ... and more.

Each frame implements the same interface but changes HOW the system interprets
data, evaluates claims, and interacts with the LLM.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import numpy as np
from pathlib import Path

# Import your existing components
from ..processing.jepa_manifold import JEPAManifold, ManifoldState
from ..claims.scientific_claim import ScientificClaimTable, TrialResult

# ============================================================
# Frame Definition & Registry
# ============================================================
class FrameID(Enum):
    FALSIFICATIONIST = "falsificationist"          # Binary pass/fail, Popper
    BAYESIAN = "bayesian"                          # Beta distributions, continuous
    SEMANTIC_TUBE = "semantic_tube"                # STP regularizer
    DIFFUSION = "diffusion"                        # GDB probabilistic bridge
    LLM_GATED = "llm_gated"                        # LLM as falsifiable prior
    EPISTEMIC = "epistemic"                        # Truth maintenance
    NEUROSYMBOLIC = "neurosymbolic"                # ML-driven reduction
    GEO_ALGEBRAIC = "geo_algebraic"                # Explicit GAB mapping
    PYGEOM = "pygeom"                              # Declarative DSL constraints
    RESONANCE = "resonance"                        # Emergent toggles
    ROUTED = "routed"                              # Multi-manifold fleet


@dataclass
class FrameContext:
    """All shared state passed to every frame."""
    manifold: JEPAManifold
    claim_table: ScientificClaimTable
    llm_bridge: Any  # your LLMBridge class
    current_state: Optional[ManifoldState] = None
    sensor_type: str = "unknown"
    elapsed_ticks: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


class ExplorationFrame(ABC):
    """Base class for all exploration frames."""
    
    @property
    @abstractmethod
    def id(self) -> FrameID:
        pass
    
    @abstractmethod
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        """
        How to ingest the binary primitive.
        Returns metrics (e.g., losses, reduced features).
        """
        pass
    
    @abstractmethod
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        """
        How to test claims against the current manifold state.
        Returns trial results.
        """
        pass
    
    @abstractmethod
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        """How to generate text from the manifold + claim state."""
        pass
    
    @abstractmethod
    def update(self, context: FrameContext):
        """Called at the end of each tick to update frame-specific state."""
        pass


# ============================================================
# Concrete Frames (abbreviated implementations)
# ============================================================

class FalsificationistFrame(ExplorationFrame):
    """Popperian: binary support/falsify. (Your current default.)"""
    
    @property
    def id(self) -> FrameID:
        return FrameID.FALSIFICATIONIST
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        # Standard encoder step
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"loss_added": 0.0}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        return context.llm_bridge.generate(context.current_state, prompt)
    
    def update(self, context: FrameContext):
        # Train manifold on window
        context.manifold.train_on_window()
        # Save claim table
        context.claim_table.save()


class BayesianFrame(ExplorationFrame):
    """
    Continuous belief updating.
    Each claim maintains a Beta(α, β) posterior instead of counters.
    """
    
    @property
    def id(self) -> FrameID:
        return FrameID.BAYESIAN
    
    def __init__(self):
        self.beliefs = {}  # claim_id -> (alpha, beta)
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"loss_added": 0.0}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = []
        for claim in context.claim_table.claims:
            if claim.status not in ["active", "deprecated"]:
                continue
            # Use standard evaluation but update beliefs differently
            result = claim.evaluate(context.current_state, context.extra)
            # Update Beta distribution
            if result.scope_verified:
                a, b = self.beliefs.get(claim.id, (1.0, 1.0))
                if result.passed:
                    a += 1.0  # support
                else:
                    b += 1.0  # falsification (weighted by confidence)
                self.beliefs[claim.id] = (a, b)
                # Compute posterior mean and credibility
                posterior_mean = a / (a + b)
                # If posterior mean drops below 0.1, mark falsified
                if posterior_mean < 0.1 and a + b > 5:
                    claim.status = "falsified"
            results.append(result)
        return results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Inject belief summary into prompt
        belief_str = "; ".join([f"{cid}: p={a/(a+b):.2f}" for cid, (a,b) in self.beliefs.items()])
        full_prompt = f"{prompt} Current Bayesian beliefs: {belief_str}."
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()
        context.claim_table.save()


class SemanticTubeFrame(ExplorationFrame):
    """Adds Semantic Tube Prediction (STP) regularizer to the JEPA loss."""
    
    @property
    def id(self) -> FrameID:
        return FrameID.SEMANTIC_TUBE
    
    def __init__(self, tube_radius: float = 0.2):
        self.tube_radius = tube_radius
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        # Add STP loss to the manifold's optimizer
        if len(context.manifold.binary_window) >= 5:
            u_tensor = context.manifold.get_latent_window()  # assume this returns tensor
            # Compute geodesic tube loss
            if u_tensor.shape[0] > 2:
                velocity = u_tensor[1:] - u_tensor[:-1]
                acceleration = velocity[1:] - velocity[:-1]
                tube_loss = torch.mean(torch.norm(acceleration, dim=1)) - self.tube_radius
                tube_loss = torch.relu(tube_loss) ** 2
                # Manually add to optimizer (simplified)
                if hasattr(context.manifold, '_stp_loss'):
                    context.manifold._stp_loss = tube_loss
        return {"tube_loss_applied": True}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        return context.llm_bridge.generate(context.current_state, prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window(stp_weight=0.3)  # modify training to include tube loss
        context.claim_table.save()


class EpistemicFrame(ExplorationFrame):
    """Truth maintenance: enforces consistency across claims."""
    
    @property
    def id(self) -> FrameID:
        return FrameID.EPISTEMIC
    
    def __init__(self):
        self.dependency_graph = {}  # claim_id -> [dependent_claim_ids]
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        return {"loss_added": 0.0}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        results = context.claim_table.test_all(context.current_state, context.extra)
        # Check for contradictions: if a claim supports X and another supports not-X
        # Mark both as "tension" and flag them in the claim table meta
        for i, r1 in enumerate(results):
            for r2 in results[i+1:]:
                if r1.claim_id != r2.claim_id and r1.passed != r2.passed:
                    if abs(r1.confidence - r2.confidence) < 0.1:
                        print(f"⚠️ Epistemic tension: {r1.claim_id} vs {r2.claim_id}")
        return results
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Add epistemic status (consistency score) to prompt
        tensions = "No contradictions" # simplified
        full_prompt = f"{prompt} Epistemic status: {tensions}."
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()
        context.claim_table.save()


class LLMGatedFrame(ExplorationFrame):
    """LLM proposes new claims; they are gated by evidence."""
    
    @property
    def id(self) -> FrameID:
        return FrameID.LLM_GATED
    
    def __init__(self):
        self.proposed_claims = []
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        state = context.manifold.step_from_binary(binary_vec)
        context.current_state = state
        # Every 10 ticks, ask LLM for a hypothesis
        if context.elapsed_ticks % 10 == 0 and context.elapsed_ticks > 0:
            prompt = "Propose a new falsifiable claim about the current geometric state."
            hypothesis = context.llm_bridge.generate(state, prompt, max_new_tokens=30)
            # Parse into a claim and add to table if it meets basic criteria
            # (simplified: just log it)
            self.proposed_claims.append(hypothesis)
        return {"hypotheses_generated": len(self.proposed_claims)}
    
    def evaluate_claims(self, context: FrameContext) -> List[TrialResult]:
        return context.claim_table.test_all(context.current_state, context.extra)
    
    def generate_narrative(self, context: FrameContext, prompt: str) -> str:
        # Include proposed claims in the narrative prompt
        proposals = "; ".join(self.proposed_claims[-3:])
        full_prompt = f"{prompt} Recently proposed claims: {proposals}."
        return context.llm_bridge.generate(context.current_state, full_prompt)
    
    def update(self, context: FrameContext):
        context.manifold.train_on_window()
        context.claim_table.save()


class ResonanceFrame(ExplorationFrame):
    """Binary toggles generate geometry via local interaction rules."""
    
    @property
    def id(self) -> FrameID:
        return FrameID.RESONANCE
    
    def __init__(self, rule: int = 90):  # Elementary cellular automaton
        self.rule = rule
    
    def process_primitive(self, context: FrameContext, binary_vec: np.ndarray) -> Dict[str, Any]:
        # Instead of just encoding, evolve the binary window with the rule
        window = np.stack(context.manifold.binary_window[-5:]) if len(context.manifold.binary_window) >= 5 else None
        if window is not None:
            # Simple ECA rule (simplified 1D)
            new_row = np.zeros_like(window[-1])
            for i in range(1, len(window[-1])-1):
                left = window[-1][i-1]
                center = window[-1][i]
                right = window[-1][i+1]
                idx = 4*left + 2*center + right
                new_row[i] = (self.rule >> idx) & 1
            # Append new binary to manifold
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
        context.claim_table.save()


# ============================================================
# Multi‑Choice Engine: The Frame Router
# ============================================================

class FrameRouter:
    """
    Routes between frames based on context (multiple‑choice).
    Acts as a Mixture of Experts at the epistemic level.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.frames: Dict[FrameID, ExplorationFrame] = {}
        self.active_frame_id: Optional[FrameID] = None
        self.default_frame = FrameID.FALSIFICATIONIST
        
        # Register all frames
        self.register(FalsificationistFrame())
        self.register(BayesianFrame())
        self.register(SemanticTubeFrame())
        self.register(EpistemicFrame())
        self.register(LLMGatedFrame())
        self.register(ResonanceFrame())
        # Add others (Diffusion, Neurosymbolic, GeoAlgebraic, PyGeom, Routed) as needed
        
        # Load configuration if exists
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.active_frame_id = FrameID(config.get("active_frame", "falsificationist"))
        else:
            self.active_frame_id = self.default_frame
        
        self.history = []  # track frame switches
    
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
        """
        The core multiple‑choice decision.
        Scores each frame based on the current context and picks the best.
        """
        scores = {}
        state = context.current_state
        claim_table = context.claim_table
        
        # 1. Falsificationist: high if claims are mostly binary and clear
        falsification_score = 0.5 + 0.5 * (claim_table.meta.get("binary_clarity", 0.5))
        scores[FrameID.FALSIFICATIONIST] = falsification_score
        
        # 2. Bayesian: high if uncertainty is high (needs continuous beliefs)
        if state:
            bayesian_score = state.uncertainty  # high uncertainty -> Bayesian
            scores[FrameID.BAYESIAN] = bayesian_score
        else:
            scores[FrameID.BAYESIAN] = 0.3
        
        # 3. Semantic Tube: high if trajectory is smooth and we have enough history
        if context.elapsed_ticks > 10 and state:
            scores[FrameID.SEMANTIC_TUBE] = 0.7
        else:
            scores[FrameID.SEMANTIC_TUBE] = 0.2
        
        # 4. Epistemic: high if we detect contradictions or have many claims
        if len(claim_table.claims) > 3:
            scores[FrameID.EPISTEMIC] = 0.8
        else:
            scores[FrameID.EPISTEMIC] = 0.2
        
        # 5. LLM Gated: high if we're in an exploratory phase (early ticks)
        if context.elapsed_ticks < 20:
            scores[FrameID.LLM_GATED] = 0.9
        else:
            scores[FrameID.LLM_GATED] = 0.1
        
        # 6. Resonance: high if binary patterns show repetitive structure
        # (simplified: use entropy of recent binary window)
        if context.manifold.binary_window:
            recent = np.stack(context.manifold.binary_window[-5:])
            entropy = - (recent.mean() * np.log(recent.mean()+1e-6) + (1-recent.mean())*np.log(1-recent.mean()+1e-6))
            resonance_score = 1.0 - entropy  # low entropy -> high resonance
            scores[FrameID.RESONANCE] = resonance_score
        else:
            scores[FrameID.RESONANCE] = 0.1
        
        # Pick the highest scoring frame
        best = max(scores, key=scores.get)
        return best
    
    def step(self, context: FrameContext):
        """Execute one tick with the chosen frame."""
        # 1. Decide which frame to use (multiple‑choice)
        chosen_id = self.choose_frame(context)
        if chosen_id != self.active_frame_id:
            self.switch_to(chosen_id, reason="automatic_score")
        
        # 2. Get the active frame and run its pipeline
        frame = self.get_active_frame()
        context.elapsed_ticks += 1
        
        # Process primitive (needs binary_vec passed somehow)
        # In real integration, binary_vec would come from the sensor.
        # Here we simulate:
        if context.current_state is None:
            dummy_binary = np.random.binomial(1, 0.5, size=(64,)).astype(np.float32)
        else:
            dummy_binary = np.random.binomial(1, 0.5, size=(64,)).astype(np.float32)  # placeholder
        
        metrics = frame.process_primitive(context, dummy_binary)
        trial_results = frame.evaluate_claims(context)
        narrative = frame.generate_narrative(context, "Describe the current state.")
        frame.update(context)
        
        return {
            "active_frame": self.active_frame_id.value,
            "metrics": metrics,
            "trial_results": trial_results,
            "narrative": narrative,
            "scores": scores  # for debugging
        }


# ============================================================
#  Integration into sensing_node.py
# ============================================================
if __name__ == "__main__":
    # Quick self‑test
    from pathlib import Path
    import torch
    from ..processing.jepa_manifold import JEPAManifold
    from ..claims.scientific_claim import ScientificClaimTable
    
    # Mock components
    manifold = JEPAManifold()
    claim_table = ScientificClaimTable(Path("sensing/claims/CLAIM_TABLE.json"))
    llm_bridge = None  # mock
    
    context = FrameContext(
        manifold=manifold,
        claim_table=claim_table,
        llm_bridge=llm_bridge,
        elapsed_ticks=0
    )
    
    router = FrameRouter()
    for i in range(30):
        context.elapsed_ticks = i
        result = router.step(context)
        print(f"Tick {i}: Frame = {result['active_frame']}, Scores = {result['scores']}")
