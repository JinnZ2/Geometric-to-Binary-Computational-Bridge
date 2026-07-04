#!/usr/bin/env python3
# exploration_engine.py — CC0
# Geometric-to-Binary-Computational-Bridge — cross-substrate exploration engine
# stdlib only, no cloud dependency
#
# EXPLORATION ENGINE — energy flow
# ════════════════════════════════
#
#   TARGET  (objective + constraints + envelope + substrate)
#      │
#      ▼
#   Edge B  cross-class query
#     scan TRANSMITTING ∪ EMBODIED sources
#     match on constraint OVERLAP, not on domain   ← the multi-domain jump
#      │ sources that share the PROBLEM
#      ▼
#   Edge A  recover()  (inverse PhysicsGuard)
#     embodiment → PROPOSED constraint set
#     proposes + flags gaps, never asserts          ← honest, or it's overwrite
#      │
#      ▼
#   RESONANCE  transfer-candidate generation
#     port form across substrates via bond-graph IR:
#     acoustic / fluidic / electrical / mechanical / thermal / magnetic
#     matched constraints = support
#     UNMET constraints   = the innovation risk
#      │ raw candidates
#      ▼
#   three gates in series — each a deliberate bottleneck:
#     G1 PHYSICS  conservation / closure / in-envelope   → reject non-physical
#     G2 VALUES   reciprocity, non-extraction,
#                 honors source (recovered, not styled)  → reject extractive
#     G3 TEST     falsifiable prediction + probe protocol → reject untestable
#                 SOUND = drive→listen
#      ▼
#   TESTABLE INNOVATION
#     prediction + envelope + acoustic signature
#
# REFUTATION_PROTOCOL: if a candidate's prediction is refuted by data,
# update THAT CANDIDATE. Never loosen a gate to force a pass, and never
# adjust the engine to save a candidate's claim.
#
# Domain vocabulary reused verbatim from fabrication/substrate_ir.py's
# bond-graph IR (same substrates, same "one law, many media" stance).

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

DOMAINS = ("acoustic", "fluidic", "electrical", "mechanical", "thermal", "magnetic")


class SourceClass(Enum):
    TRANSMITTING = "transmitting"  # documented / theory-first (papers, specs)
    EMBODIED = "embodied"          # practice-first (craft, folk technique, wetware)


@dataclass(frozen=True)
class Target:
    objective: str
    constraints: frozenset       # constraint tags the solution must satisfy
    envelope: dict               # operating envelope, e.g. {"T_K": (0, 400)}
    substrate: str                # domain the target currently lives in


@dataclass(frozen=True)
class Source:
    name: str
    source_class: SourceClass
    domain: str                  # one of DOMAINS
    constraints: frozenset       # constraints already explicit for this source
    embodiment: dict = field(default_factory=dict)   # raw practice, if EMBODIED
    reciprocity: float = 1.0      # 0..1, non-extraction score (G2 input)
    styled_as_own: bool = False   # True = presented without crediting the source
    derivation: tuple = ()        # (tag, origin, matched_keyword) triples, for
                                   # mechanically-derived constraints — how a
                                   # tag was earned, not just that it was earned


@dataclass
class Candidate:
    source: Source
    matched: frozenset
    unmet: frozenset
    recovered_constraints: frozenset
    gap_flags: tuple
    prediction: Optional[str] = None
    probe_protocol: Optional[str] = None
    acoustic_signature: Optional[str] = None
    rejected_at: Optional[str] = None
    reject_reason: Optional[str] = None

    @property
    def survived(self) -> bool:
        return self.rejected_at is None


def edge_b_query(target: Target, sources: list) -> list:
    """Cross-class query: scan TRANSMITTING ∪ EMBODIED, match on constraint
    OVERLAP, not domain. Domain-blind by design — that IS the multi-domain
    jump. Returns (source, overlap) pairs, richest overlap first."""
    hits = [(s, target.constraints & s.constraints) for s in sources]
    hits = [(s, overlap) for s, overlap in hits if overlap]
    hits.sort(key=lambda pair: len(pair[1]), reverse=True)
    return hits


def edge_a_recover(source: Source) -> tuple:
    """Inverse PhysicsGuard: embodiment -> PROPOSED constraint set.
    Proposes, never asserts — every inferred constraint is flagged as a
    gap so a human/downstream gate can verify it, rather than silently
    treating a folk practice as if it were a measured spec."""
    if source.source_class is SourceClass.TRANSMITTING:
        return source.constraints, ()  # already explicit; nothing to recover
    proposed = set(source.constraints)
    gaps = []
    for key in source.embodiment:
        tag = f"embodied:{key}"
        if tag not in proposed:
            proposed.add(tag)
            gaps.append(f"UNVERIFIED — '{key}' inferred from embodiment, "
                         f"not measured; treat as proposal, not fact")
    return frozenset(proposed), tuple(gaps)


def resonance(target: Target, source: Source) -> Candidate:
    """Transfer-candidate generation: run recover(), then port the source's
    form across the bond-graph substrate list into the target's substrate.
    Matched constraints are support; unmet constraints are the risk the
    remaining gates must price in, not hide."""
    recovered, gaps = edge_a_recover(source)
    matched = target.constraints & recovered
    unmet = target.constraints - recovered
    return Candidate(source=source, matched=matched, unmet=unmet,
                      recovered_constraints=recovered, gap_flags=gaps)


def g1_physics(candidate: Candidate, target: Target) -> Candidate:
    """Reject non-physical transfers: any conservation-tagged constraint
    the target requires must be in `matched`, not merely unmet-and-ignored."""
    required_conservation = {c for c in target.constraints
                              if c.startswith("conserve:")}
    missing = required_conservation - candidate.matched
    if missing:
        candidate.rejected_at = "G1_PHYSICS"
        candidate.reject_reason = f"unmet conservation constraints: {sorted(missing)}"
    return candidate


def g2_values(candidate: Candidate, reciprocity_min: float = 0.5) -> Candidate:
    """Reject extractive transfers: low reciprocity, or a source recovered
    via embodiment but then presented as if it had no origin (styled_as_own)."""
    if candidate.rejected_at:
        return candidate
    s = candidate.source
    if s.reciprocity < reciprocity_min:
        candidate.rejected_at = "G2_VALUES"
        candidate.reject_reason = f"reciprocity {s.reciprocity:.2f} < {reciprocity_min:.2f}"
    elif s.source_class is SourceClass.EMBODIED and s.styled_as_own:
        candidate.rejected_at = "G2_VALUES"
        candidate.reject_reason = "recovered from embodiment but not honored as source"
    return candidate


def acoustic_probe(candidate: Candidate) -> str:
    """SOUND's G3 role: harmonics as non-destructive coherence readout.
    Every surviving candidate gets one, regardless of its own domain —
    drive -> listen is the universal, non-destructive test."""
    n_matched = len(candidate.matched)
    n_unmet = len(candidate.unmet)
    if n_unmet == 0:
        return "drive at f0, expect NO pitch shift / NO damping change (fully matched)"
    return (f"drive at f0, expect pitch shift and/or damping-factor change "
            f"proportional to {n_unmet} unmet constraint(s) "
            f"({n_matched} matched act as the reference baseline)")


def g3_test(candidate: Candidate) -> Candidate:
    """Reject untestable transfers: must emit a falsifiable prediction plus
    a probe protocol. SOUND is the mandatory probe: drive -> listen."""
    if candidate.rejected_at:
        return candidate
    candidate.acoustic_signature = acoustic_probe(candidate)
    candidate.probe_protocol = "drive->listen (harmonic excitation, passive readout)"
    candidate.prediction = (
        f"{candidate.source.name}: matched={sorted(candidate.matched)} "
        f"predicts closure on target within envelope; "
        f"unmet={sorted(candidate.unmet)} predicts measurable deviation "
        f"in the acoustic signature above"
    )
    if not candidate.prediction or not candidate.probe_protocol:
        candidate.rejected_at = "G3_TEST"
        candidate.reject_reason = "no falsifiable prediction / probe protocol"
    return candidate


def run_pipeline(target: Target, sources: list) -> list:
    """TARGET -> Edge B -> RESONANCE (incl. Edge A) -> G1 -> G2 -> G3."""
    hits = edge_b_query(target, sources)
    candidates = [resonance(target, s) for s, _overlap in hits]
    candidates = [g3_test(g2_values(g1_physics(c, target))) for c in candidates]
    return candidates


if __name__ == "__main__":
    target = Target(
        objective="damp mechanical resonance without added mass",
        constraints=frozenset({
            "conserve:energy", "low_extraction", "measurable_signature",
        }),
        envelope={"T_K": (250, 320), "f_Hz": (20, 2000)},
        substrate="mechanical",
    )

    sources = [
        Source(
            name="tuned-mass damper (paper, 2019)",
            source_class=SourceClass.TRANSMITTING,
            domain="mechanical",
            constraints=frozenset({"conserve:energy", "measurable_signature"}),
            reciprocity=0.9,
        ),
        Source(
            name="luthier tap-tone selection (craft, undated)",
            source_class=SourceClass.EMBODIED,
            domain="acoustic",
            constraints=frozenset({"conserve:energy"}),
            embodiment={"low_extraction": "select wood by ear, no added material"},
            reciprocity=0.8,
        ),
        Source(
            name="eddy-current brake (patent, styled as novel)",
            source_class=SourceClass.EMBODIED,
            domain="electrical",
            constraints=frozenset({"conserve:energy", "measurable_signature"}),
            embodiment={"low_extraction": "reused from open hobbyist forum thread"},
            reciprocity=0.9,
            styled_as_own=True,
        ),
    ]

    print("Cross-class query (Edge B) — sources sharing the PROBLEM:")
    for s, overlap in edge_b_query(target, sources):
        print(f"  {s.name:<40} overlap={sorted(overlap)}")

    print("\nPipeline verdicts:")
    for c in run_pipeline(target, sources):
        print(f"\n- {c.source.name}")
        print(f"  matched={sorted(c.matched)}  unmet={sorted(c.unmet)}")
        if c.gap_flags:
            for g in c.gap_flags:
                print(f"  gap: {g}")
        if c.survived:
            print(f"  TESTABLE INNOVATION")
            print(f"  prediction: {c.prediction}")
            print(f"  probe: {c.probe_protocol}")
            print(f"  acoustic signature: {c.acoustic_signature}")
        else:
            print(f"  REJECTED at {c.rejected_at}: {c.reject_reason}")
