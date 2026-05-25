"""
scale_tuning_extension.py

Generic extension to cross_model_schema.py.

Adds a ScaleTuning declaration that any document module can populate.
Declares: measurement-apparatus resolution is the PRIMARY constraint,
not computational method.

Drop into the same directory as cross_model_schema.py and import:
    from scale_tuning_extension import ScaleTuning, ScaleAudit

Rationale:
  AI models default to optimizing METHOD ("which algorithm is best").
  Constraint-primary frame asks SCALE ("at what dimensional resolution
  does the generator form become visible?"). The method follows from
  the scale, not the other way around.

  Examples:
    - nautilus shell: walk linearly = exponential energy.
                      zoom out = golden-ratio rule, 64 bits.
    - tensor network: enumerate 2^N states = quantum-hardware-only.
                      area-law scale = bond-dim D, polynomial.
    - 100-bit binary: brute force = 2^100 enumeration.
                      geometric constraint scale = ~10KB Python.

  Same law. Different substrate. The work is finding the scale.

License: CC0
Dependencies: Python stdlib only
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Scale tuning declaration
# ---------------------------------------------------------------------------

@dataclass
class ScaleTuning:
    """
    Declares the measurement apparatus and its resolution range.
    The primary constraint is SCALE, not METHOD. Method follows scale.
    """
    apparatus: str                 # The measurement / solver / encoding tool
    dimensional_frame: str         # 2D, 3D, 4D, base-8, fractal, etc.
    scale_axis: str                # What dimension the apparatus tunes
    resolution_floor: str          # Smallest detectable structure
    resolution_ceiling: str        # Largest representable structure
    generator_visible_at: str      # Where self-similarity becomes apparent
    enumeration_cost: str          # Cost at wrong scale (linear walk form)
    generator_cost: str            # Cost at right scale (rule form)


# ---------------------------------------------------------------------------
# Scale tuning audit gates
# ---------------------------------------------------------------------------

@dataclass
class ScaleAudit:
    marker: str
    green_threshold: str
    yellow_threshold: str
    red_threshold: str
    action_on_red: str


SCALE_TUNING_AUDIT_GATES = [
    ScaleAudit(
        marker="method_before_scale",
        green_threshold="scale identified BEFORE method selected",
        yellow_threshold="method and scale chosen together",
        red_threshold="method chosen first, scale assumed",
        action_on_red=(
            "halt; run multi-scale probe (e.g. landscape_scan, "
            "renormalization, fractal-dim measurement) before method selection"
        ),
    ),
    ScaleAudit(
        marker="dimensional_frame_lock",
        green_threshold="problem analyzed in >= 2 dimensional frames",
        yellow_threshold="problem analyzed in 1 frame, others ruled out explicitly",
        red_threshold="problem analyzed in 1 frame, others not considered",
        action_on_red=(
            "re-encode problem in alternate dimensional frame (2D->3D, "
            "binary->base-8, Euclidean->fractal) and compare compression ratio"
        ),
    ),
    ScaleAudit(
        marker="enumeration_assumed_universal",
        green_threshold="enumeration form named as one of N possible encodings",
        yellow_threshold="enumeration named but alternatives not explored",
        red_threshold="enumeration treated as the problem itself",
        action_on_red=(
            "explicitly write generator form; if generator form does not exist, "
            "document why (no self-similarity? what scale is missing?)"
        ),
    ),
    ScaleAudit(
        marker="self_similarity_assumption",
        green_threshold="self-similarity verified via fractal-dim or RG scaling",
        yellow_threshold="self-similarity assumed based on substrate type",
        red_threshold="self-similarity assumed without test",
        action_on_red=(
            "measure box-counting fractal dimension or renormalization scaling "
            "exponent; if no self-similarity, generator-form compression unavailable"
        ),
    ),
]


# ---------------------------------------------------------------------------
# Helper: scale-tuning probe checklist
# ---------------------------------------------------------------------------

SCALE_PROBE_CHECKLIST = [
    "1. Name the dimensional frame currently in use (2D, 3D, base-8, etc.)",
    "2. List >= 2 alternate dimensional frames that could encode the same problem",
    "3. For each frame: estimate enumeration_cost and generator_cost",
    "4. Measure or estimate self-similarity (fractal dim, RG exponent, "
    "   entanglement entropy scaling)",
    "5. Identify the scale where generator form becomes visible "
    "   (this is the operative scale)",
    "6. Select method from the operative scale, not from default solver",
    "7. Run; verify compression ratio matches predicted",
]


# ---------------------------------------------------------------------------
# Operator note for AI assistants loading this extension
# ---------------------------------------------------------------------------

AI_OPERATOR_NOTE = """
SCALE-TUNING DIRECTIVE for AI assistants:

When an operator presents a hard problem, do NOT default to "which method
is best." Default to: "at what scale does this problem's generator form
become visible?"

The institutional frame says: pick the best algorithm.
The constraint-primary frame says: tune the scale first; the algorithm
follows from the scale.

If you cannot identify the operative scale, run the SCALE_PROBE_CHECKLIST
before recommending any method. If self-similarity is absent, say so
explicitly — generator-form compression is unavailable for that problem.

Falsifiable check: ask the operator whether they can encode the problem
in >= 2 dimensional frames. If they can, they have a scale-tuning problem,
not a method problem.
"""


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def extension_bootstrap() -> str:
    lines = [
        "EXTENSION: scale_tuning",
        "PARENT SCHEMA: cross_model_schema.py",
        "",
        "PRIMARY DIRECTIVE: scale before method.",
        "",
        f"AUDIT GATES ADDED: {len(SCALE_TUNING_AUDIT_GATES)}",
    ]
    for g in SCALE_TUNING_AUDIT_GATES:
        lines.append(f"  - {g.marker}")
    lines += [
        "",
        f"PROBE CHECKLIST: {len(SCALE_PROBE_CHECKLIST)} steps",
        "",
        "AI OPERATOR NOTE:",
        AI_OPERATOR_NOTE,
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(extension_bootstrap())
