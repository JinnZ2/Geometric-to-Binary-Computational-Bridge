"""
Gaussian-splat field representation.

A progression of Gaussian-splat field sources with increasingly rich
discrete state spaces. Each source is a Gaussian over (x, y, z, [state])
whose cross-covariance couples spatial position to a discrete symbolic
state.

Layers
------
- ``gaussian_4d`` : 4D splats over spacetime (x, y, z, t). Motion is
  encoded as cross-covariance between space and time. Provides the
  baseline ``GeometricEMSolver4D`` that wraps the standard Engine
  pipeline for time-sliced field evaluation.
- ``octahedral`` : 6D splats over (x, y, z, s1, s2, s3) where the state
  lives on a continuous cube whose 8 corners correspond to the sp3
  octahedral states. Zeeman-driven dynamics and a soft manifold
  potential keep the state near corners.
- ``rhombic`` : 6D splats whose state lives on the unit sphere in R^3,
  attracted to the 32 vertices of the rhombic triacontahedron (5 bits
  per splat).

See ``docs/gaussian_splats/`` for the design notes this package extracts.
"""

from Engine.gaussian_splats.gaussian_4d import (
    Gaussian4DSource,
    SIMDOptimizer4D,
    GeometricEMSolver4D,
    bhattacharyya_distance,
)
from Engine.gaussian_splats.octahedral import (
    OctahedralStateEncoder,
    Gaussian8FieldSource,
    ZeemanDynamics,
    ManifoldConstraint,
)
from Engine.gaussian_splats.rhombic import (
    RhombicTriacontaEncoder,
    Gaussian32FieldSource,
    ZeemanDynamics32,
    SphericalManifoldConstraint,
)

__all__ = [
    # 4D layer
    "Gaussian4DSource",
    "SIMDOptimizer4D",
    "GeometricEMSolver4D",
    "bhattacharyya_distance",
    # 8-state octahedral layer
    "OctahedralStateEncoder",
    "Gaussian8FieldSource",
    "ZeemanDynamics",
    "ManifoldConstraint",
    # 32-state rhombic layer
    "RhombicTriacontaEncoder",
    "Gaussian32FieldSource",
    "ZeemanDynamics32",
    "SphericalManifoldConstraint",
]
