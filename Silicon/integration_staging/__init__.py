"""
Silicon/integration_staging — Step 1 octahedral integration (staging)
======================================================================
STATUS: STAGING — not yet migrated to Silicon/modules/

Contents
--------
  octahedral_bundle.py  — OctahedralBundle: live fiber substitution (Step 1)
  demo_step1.py         — standalone demo + visualisation
  STAGING_NOTES.md      — migration checklist and status

See Silicon/modules/Octahedral_Integration.md for the full integration plan.
"""

from .octahedral_bundle import (
    OctahedralVertex,
    OctahedralBundle,
    BarycentricPosition,
    build_vertex_atlas,
    project_to_barycentric,
    bundle_from_pipeline,
)

__all__ = [
    "OctahedralVertex",
    "OctahedralBundle",
    "BarycentricPosition",
    "build_vertex_atlas",
    "project_to_barycentric",
    "bundle_from_pipeline",
]
