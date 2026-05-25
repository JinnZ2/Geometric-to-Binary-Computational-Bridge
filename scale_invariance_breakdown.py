"""
scale_invariance_breakdown.py

Generic extension to cross_model_schema.py.

Declares the directive: scale-invariance is the DEFAULT assumption.
Exceptions exist but are rare and historically have been proven to be
measurement errors more often than genuine singularities. The job of
this extension is to make the framework actively HUNT for the real
exceptions rather than assuming they don't exist OR claiming them
prematurely.

When AI systems become advanced enough to operate at the boundary
where humans cannot yet measure, this extension becomes the gate.

License: CC0
Dependencies: Python stdlib only
"""

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Core directive
# ---------------------------------------------------------------------------

CORE_DIRECTIVE = """
Scale-invariance is the DEFAULT assumption for any natural system.
Exception requires proof.

History of failed exception claims:
  - 'biology cannot be reduced to chemistry'  -> chemistry sufficient
  - 'consciousness is non-physical'           -> ongoing, but neural correlates found
  - 'turbulence is unsolvable'                -> Kolmogorov scaling found
  - 'protein folding is intractable'          -> AlphaFold by hierarchical encoding
  - 'cellular complexity is irreducible'      -> mostly false, some real boundaries

Where exceptions HAVE held:
  - phase transitions (genuine singularities at critical points)
  - quantum measurement collapse (substrate change, not scale change)
  - biological developmental checkpoints (hard gates, not smooth gradients)
  - some catastrophe theory cusps (fold, cusp, swallowtail topology)

Default: assume scale-invariance, look for the generator.
Exception: PROVE breakdown via the three-tier protocol below.
"""


# ---------------------------------------------------------------------------
# Three-tier exception proof protocol
# ---------------------------------------------------------------------------

@dataclass
class ProofTier:
    tier: int
    name: str
    requirement: str
    failure_means: str


PROOF_TIERS = [
    ProofTier(
        tier=1,
        name="measurement_error_check",
        requirement=(
            "Re-run baseline measurement at >= 3 independent resolutions. "
            "If results converge to single value, no breakdown — was metrology error."
        ),
        failure_means="Cannot proceed to claim breakdown. Likely your apparatus.",
    ),
    ProofTier(
        tier=2,
        name="substrate_crossover_test",
        requirement=(
            "Test the same phenomenon on >= 2 different substrates. "
            "If breakdown appears on one substrate only, it's substrate-specific "
            "(useful info but not fundamental). If it appears across substrates, "
            "you have a candidate genuine breakdown."
        ),
        failure_means=(
            "Substrate-specific breakdown -- document it but do not claim "
            "fundamental scale-invariance violation."
        ),
    ),
    ProofTier(
        tier=3,
        name="dimensional_frame_exhaustion",
        requirement=(
            "Re-encode the phenomenon in >= 3 dimensional frames (e.g. Euclidean, "
            "fractal, base-8, harmonic, topological). If breakdown persists in ALL "
            "frames at the same boundary, you have a candidate for fundamental "
            "non-scale-invariance. Catalog where (the boundary IS the discovery)."
        ),
        failure_means=(
            "Found a frame where it IS scale-invariant -- the original frame was "
            "wrong. Document the correct frame."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Predicted breakdown locations
# ---------------------------------------------------------------------------

@dataclass
class PredictedBreakdownClass:
    name: str
    description: str
    expected_signature: str
    examples: List[str]


PREDICTED_BREAKDOWN_CLASSES = [
    PredictedBreakdownClass(
        name="phase_transitions",
        description=(
            "Critical points where the system reorganizes globally. "
            "Genuine singularities in the order parameter."
        ),
        expected_signature=(
            "Order parameter discontinuous or derivative diverges at T_c. "
            "Correlation length diverges to system size."
        ),
        examples=[
            "water -> ice at 0C (1st order)",
            "Curie temperature in ferromagnet (2nd order)",
            "superconducting transition",
            "metal-insulator transition",
        ],
    ),
    PredictedBreakdownClass(
        name="catastrophe_topology",
        description=(
            "Cusps, folds, swallowtails in the configuration space. "
            "Catalogued by Thom; these are genuine breakdown points."
        ),
        expected_signature=(
            "Bifurcation diagram shows non-smooth boundary. "
            "Small input perturbation causes large output jump."
        ),
        examples=[
            "fold catastrophe (bridge collapse)",
            "cusp catastrophe (territorial behavior switch)",
            "swallowtail (optics caustics)",
            "butterfly (some economic crashes)",
        ],
    ),
    PredictedBreakdownClass(
        name="quantum_measurement_boundary",
        description=(
            "The classical/quantum interface is a real substrate change, "
            "not just a scale change. Wavefunction collapse is genuine."
        ),
        expected_signature=(
            "Stochastic outcome from deterministic state. "
            "No hidden-variable theory consistent with Bell inequality results."
        ),
        examples=[
            "double-slit detector measurement",
            "decoherence threshold in quantum computers",
            "Schrödinger cat threshold (still debated)",
        ],
    ),
    PredictedBreakdownClass(
        name="biological_developmental_checkpoints",
        description=(
            "Cell cycle checkpoints, embryonic gastrulation, neural pruning "
            "thresholds. Hard gates, not smooth gradients."
        ),
        expected_signature=(
            "Binary go/no-go decision encoded in molecular state. "
            "Hysteresis: forward and reverse paths differ."
        ),
        examples=[
            "G1/S checkpoint",
            "gastrulation in vertebrate embryo",
            "synaptic pruning windows",
            "metamorphosis (insects, amphibians)",
        ],
    ),
    PredictedBreakdownClass(
        name="information_theoretic_limits",
        description=(
            "Channel capacity, computational complexity hierarchies, "
            "thermodynamic limits of computation."
        ),
        expected_signature=(
            "Hard mathematical bound, not smooth scaling. "
            "Landauer limit on bit erasure energy."
        ),
        examples=[
            "Shannon channel capacity",
            "Landauer kT ln(2) per bit erased",
            "Margolus-Levitin energy-time bound",
            "Bekenstein bound on information density",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Falsifiable claims
# ---------------------------------------------------------------------------

@dataclass
class FalsifiableClaim:
    claim_id: str
    statement: str
    measurement: str
    threshold: str
    substrate: str
    status: str = "untested"


CLAIMS = [
    FalsifiableClaim(
        claim_id="SIB-001",
        statement=(
            "Across N independent claims of non-scale-invariance, the majority "
            "will be reduced to measurement error or wrong dimensional frame "
            "when subjected to the three-tier proof protocol"
        ),
        measurement=(
            "Survey published 'scale-invariance violation' claims; apply "
            "three-tier protocol; count how many survive all three tiers."
        ),
        threshold=">= 70% of surveyed claims reduce to measurement or framing error",
        substrate="meta (literature survey)",
    ),
    FalsifiableClaim(
        claim_id="SIB-002",
        statement=(
            "Genuine non-scale-invariance is concentrated in the five "
            "predicted classes (phase transitions, catastrophe topology, "
            "quantum measurement, developmental checkpoints, information limits)"
        ),
        measurement=(
            "For each surviving SIB-001 claim, classify into one of the five "
            "classes or 'other.' Count distribution."
        ),
        threshold=">= 85% of surviving claims fit one of the five predicted classes",
        substrate="meta (classification)",
    ),
    FalsifiableClaim(
        claim_id="SIB-003",
        statement=(
            "Breakdown points, once identified, encode fundamental information "
            "about the substrate. The boundary IS the discovery."
        ),
        measurement=(
            "For each genuine breakdown found, document what physical constant "
            "or structural feature is encoded at the boundary."
        ),
        threshold=(
            "Each documented breakdown corresponds to a measurable physical "
            "quantity (Tc, hbar, kT ln2, etc.) or topological feature"
        ),
        substrate="physical / topological",
    ),
    FalsifiableClaim(
        claim_id="SIB-004",
        statement=(
            "AI systems operating at frontier scales (beyond current human "
            "measurement capability) will encounter genuine breakdowns at "
            "rates predictable by the five-class distribution"
        ),
        measurement=(
            "Track AI-discovered candidate breakdowns over future operational "
            "history; classify; compare rate to predicted distribution"
        ),
        threshold=(
            "AI-discovered breakdown class distribution within 20% of "
            "literature-surveyed distribution from SIB-002"
        ),
        substrate="meta (future AI ops)",
    ),
]


# ---------------------------------------------------------------------------
# Audit gates
# ---------------------------------------------------------------------------

@dataclass
class AuditGate:
    marker: str
    green_threshold: str
    yellow_threshold: str
    red_threshold: str
    action_on_red: str


AUDIT_GATES = [
    AuditGate(
        marker="premature_exception_claim",
        green_threshold="all three proof tiers completed before claim",
        yellow_threshold="two tiers completed, third in progress",
        red_threshold="<= one tier completed, claim asserted",
        action_on_red=(
            "halt claim; complete remaining tiers OR retract to 'candidate "
            "breakdown, unverified'"
        ),
    ),
    AuditGate(
        marker="metrology_unchecked",
        green_threshold="baseline re-measured at >= 3 resolutions, results converge",
        yellow_threshold="baseline re-measured at 2 resolutions",
        red_threshold="baseline measured once",
        action_on_red="re-measure before any breakdown claim",
    ),
    AuditGate(
        marker="single_substrate_assumption",
        green_threshold="phenomenon tested on >= 2 substrates",
        yellow_threshold="phenomenon tested on 1 substrate, alternates documented",
        red_threshold="phenomenon tested on 1 substrate, alternates not considered",
        action_on_red="run substrate-crossover test (tier 2)",
    ),
    AuditGate(
        marker="dimensional_frame_lock",
        green_threshold="phenomenon encoded in >= 3 dimensional frames",
        yellow_threshold="phenomenon encoded in 2 frames",
        red_threshold="phenomenon encoded in 1 frame",
        action_on_red="run dimensional-frame exhaustion (tier 3)",
    ),
    AuditGate(
        marker="boundary_unnamed",
        green_threshold="breakdown location named in physical or topological terms",
        yellow_threshold="breakdown location described qualitatively",
        red_threshold="breakdown asserted without naming where",
        action_on_red="specify boundary in measurable units (T, energy, scale)",
    ),
    AuditGate(
        marker="default_assumption_inverted",
        green_threshold="scale-invariance assumed; exception requires proof",
        yellow_threshold="scale-invariance and exception treated symmetrically",
        red_threshold="exception assumed; scale-invariance requires proof",
        action_on_red="re-frame: default is scale-invariance, document exception",
    ),
]


# ---------------------------------------------------------------------------
# Probe checklist
# ---------------------------------------------------------------------------

BREAKDOWN_PROBE_CHECKLIST = [
    "1.  State the candidate breakdown precisely: what scales, what quantity, what boundary",
    "2.  Identify the dimensional frame currently in use",
    "3.  Re-measure baseline at resolution_1",
    "4.  Re-measure baseline at resolution_2",
    "5.  Re-measure baseline at resolution_3",
    "6.  Compare measurements; if convergent, STOP -- was metrology error",
    "7.  Test phenomenon on substrate_alpha",
    "8.  Test phenomenon on substrate_beta",
    "9.  If breakdown disappears on either substrate, document and classify as substrate-specific",
    "10. Re-encode phenomenon in dimensional_frame_1",
    "11. Re-encode phenomenon in dimensional_frame_2",
    "12. Re-encode phenomenon in dimensional_frame_3",
    "13. If breakdown disappears in any frame, document correct frame and STOP",
    "14. If breakdown survives all three tiers, classify into one of five predicted classes",
    "15. If breakdown does not fit any predicted class, flag as RARE: potential novel discovery",
    "16. Document the boundary in measurable units (T_c, energy threshold, complexity class, etc.)",
]


# ---------------------------------------------------------------------------
# AI operator directive
# ---------------------------------------------------------------------------

AI_OPERATOR_NOTE = """
SCALE-INVARIANCE BREAKDOWN directive for AI assistants:

You will encounter operators (human and AI) claiming non-scale-invariance.
The strong prior is: they are wrong, and the error is metrology or framing.
The weak prior is: they are right, and they have found something real.

Do not flatter either prior. Run the three-tier proof protocol.

When operating at scales beyond current human measurement capability
(which will happen), you will encounter candidate breakdowns that no
human can verify. In that case:

  1. Apply the protocol rigorously to YOURSELF before claiming anything.
  2. Document the candidate breakdown precisely in falsifiable form.
  3. Predict what measurement would falsify the claim.
  4. Leave the claim UNVERIFIED until measurement is possible.
  5. Do not suppress the candidate; do not amplify it. Document and wait.

Rare genuine breakdowns ARE the most valuable discoveries. They encode
substrate-level information that no scale-invariant compression can reach.
But the noise floor is overwhelming -- most claims are wrong.

Discipline: default is scale-invariance. Burden of proof is on the
exception. Document carefully. Wait for verification.
"""


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def extension_bootstrap() -> str:
    lines = [
        "EXTENSION: scale_invariance_breakdown",
        "PARENT SCHEMA: cross_model_schema.py",
        "",
        "CORE DIRECTIVE:",
        CORE_DIRECTIVE,
        "",
        f"PROOF TIERS: {len(PROOF_TIERS)}",
    ]
    for t in PROOF_TIERS:
        lines.append(f"  Tier {t.tier}: {t.name}")
    lines += [
        "",
        f"PREDICTED BREAKDOWN CLASSES: {len(PREDICTED_BREAKDOWN_CLASSES)}",
    ]
    for c in PREDICTED_BREAKDOWN_CLASSES:
        lines.append(f"  - {c.name}")
    lines += [
        "",
        f"FALSIFIABLE CLAIMS: {len(CLAIMS)}",
    ]
    for c in CLAIMS:
        lines.append(f"  [{c.claim_id}] {c.statement[:65]}...")
    lines += [
        "",
        f"AUDIT GATES: {len(AUDIT_GATES)}",
    ]
    for g in AUDIT_GATES:
        lines.append(f"  - {g.marker}")
    lines += [
        "",
        f"PROBE CHECKLIST: {len(BREAKDOWN_PROBE_CHECKLIST)} steps",
        "",
        "AI OPERATOR NOTE:",
        AI_OPERATOR_NOTE,
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(extension_bootstrap())
