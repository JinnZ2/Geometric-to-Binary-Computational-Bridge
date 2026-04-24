"""
Silicon Computational Bridge — Modular Package
===============================================
Implements the dynamical silicon manifold system described in To-Do-alternate.md.

Modules
-------
state       : SiliconState dataclass and fabrication-grounded state vector
metric      : Riemannian metric, inverse, and Christoffel symbols
potential   : Effective potential and gradient on the state manifold
dynamics    : Deterministic geodesic and stochastic geodesic integrators
coupling    : Geometry field → silicon force injection and bidirectional coupling
operators   : Continuous operator algebra (silicon-state-derived weight kernels)
regime      : Regime atlas classifier over (Λ, d, σ, χ) with Ω² boundary
pipeline    : Unified closed-loop system runner and trajectory recorder
"""

from .state import SiliconState, make_state
from .metric import metric_tensor, metric_inverse, christoffel_symbols
from .potential import potential, grad_potential
from .dynamics import evolve_deterministic, evolve_stochastic
from .coupling import geometry_force, update_with_geometry
from .operators import build_kernel, evaluate_field, feedback_update
from .regime import RegimeAtlas, classify_regime
from .pipeline import run_pipeline, PipelineConfig

__all__ = [
    "SiliconState", "make_state",
    "metric_tensor", "metric_inverse", "christoffel_symbols",
    "potential", "grad_potential",
    "evolve_deterministic", "evolve_stochastic",
    "geometry_force", "update_with_geometry",
    "build_kernel", "evaluate_field", "feedback_update",
    "RegimeAtlas", "classify_regime",
    "run_pipeline", "PipelineConfig",
]
