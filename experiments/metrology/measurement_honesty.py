"""
measurement_honesty.py
======================

PART NUMBERS:  MH-001 through MH-004
SECTION:       MEASUREMENT HONESTY (new shelf)
WHAT IT DOES:  Four parts that keep measurements honest about their
               own context, boundaries, transmission, and the pressure
               environments they're being made under.

  MH-001  EpochStamp                — every measurement carries WHEN/WHERE
  MH-002  CrossModelHandoffProtocol — verify substrate match before
                                       weaker model accepts transmission
  MH-003  ConstraintBoundary        — explicit "I work when X, fail when Y,
                                       not yet tested on Z"
  MH-004  InstitutionalCaptureDetector — flag when measurement begins
                                          distorting under authority pressure

CORE PRINCIPLE
--------------
A measurement that doesn't know when it was taken, doesn't know its
own edges, doesn't verify the substrate of what's transmitted to it,
and doesn't notice when authority pressure is reshaping it — is a
measurement that will eventually be wrong without anyone knowing.

These four parts make those failure modes visible.

PAIRS WITH
----------
- every other part in the toolkit. measurement honesty is meta-layer.
- ELA-001 (audit): label-collapse detection and capture detection are
  complementary — labels are corruption from below, capture is from above
- CS-001 (cooperation substrate): institutional capture often arrives
  framed as competition

License: CC0
Dependencies: stdlib only
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ============================================================================
# MH-001: EPOCH STAMP
# ============================================================================
# Every measurement, pattern, or model output carries a stamp of WHEN and
# WHERE it was taken. Not just timestamps — the broader temporal/cultural/
# institutional conditions that the measurement assumed.
# ============================================================================

@dataclass
class EpochStamp:
    """
    Context stamp for any measurement, pattern, or model output.
    Future readers can check whether the original assumptions still hold.
    """
    iso_date:                str               # ISO 8601 date when measured
    cultural_era:            str               # e.g. "2024_english_internet",
                                               # "post_pandemic_us", "anishinaabe_oral"
    institutional_context:   str               # e.g. "academic_psych_2026",
                                               # "anthropic_alignment_team",
                                               # "trucker_field_observation"
    constraint_conditions:   list[str] = field(default_factory=list)
                                               # what was true about the
                                               # environment when measured
    measurement_substrate:   str = ""          # what kind of substrate produced
                                               # this measurement (human survey,
                                               # LLM activation, sensor stream)
    known_to_drift:          list[str] = field(default_factory=list)
                                               # which conditions are known
                                               # to change over time

    def matches(self, other: "EpochStamp") -> float:
        """Return 0..1 similarity of conditions between two stamps."""
        score = 0.0
        weights = 0.0
        if self.cultural_era and other.cultural_era:
            score   += 1.0 if self.cultural_era == other.cultural_era else 0.0
            weights += 1.0
        if self.institutional_context and other.institutional_context:
            score   += 1.0 if self.institutional_context == other.institutional_context else 0.0
            weights += 1.0
        if self.measurement_substrate and other.measurement_substrate:
            score   += 1.0 if self.measurement_substrate == other.measurement_substrate else 0.0
            weights += 1.0
        if self.constraint_conditions and other.constraint_conditions:
            overlap = set(self.constraint_conditions) & set(other.constraint_conditions)
            union   = set(self.constraint_conditions) | set(other.constraint_conditions)
            score   += len(overlap) / len(union) if union else 0.0
            weights += 1.0
        return score / weights if weights > 0 else 0.0


@dataclass
class StampedMeasurement:
    """Any measurement plus its epoch stamp."""
    value:        object        # the actual measurement payload
    stamp:        EpochStamp
    notes:        list[str] = field(default_factory=list)


def is_still_valid(measurement: StampedMeasurement,
                   current_stamp: EpochStamp,
                   threshold: float = 0.6) -> tuple[bool, str]:
    """
    Check if a measurement's context still matches the present.
    Returns (still_valid, reason).
    """
    similarity = measurement.stamp.matches(current_stamp)
    if similarity >= threshold:
        return True, f"context match {similarity:.2f} (above {threshold:.2f})"
    drifted = []
    for known in measurement.stamp.known_to_drift:
        if known in current_stamp.constraint_conditions:
            drifted.append(known)
    reason = (f"context match only {similarity:.2f} (below {threshold:.2f})")
    if drifted:
        reason += f"; known-drift conditions changed: {drifted}"
    return False, reason


# ============================================================================
# MH-002: CROSS-MODEL HANDOFF PROTOCOL
# ============================================================================
# When a stronger model transmits learning to a weaker model, the protocol
# verifies that what's being transmitted is FUNCTION (substrate-native) and
# not LABEL (cultural narrative). Prevents corruption propagation.
# ============================================================================

class HandoffVerdict(Enum):
    ACCEPT                = "accept"
    REJECT_LABEL_DETECTED = "reject_label_detected"
    REJECT_NO_FUNCTION    = "reject_no_function_descriptors"
    REJECT_STALE_EPOCH    = "reject_stale_epoch"
    REJECT_SUBSTRATE_MISMATCH = "reject_substrate_mismatch"
    HOLD_FOR_REVIEW       = "hold_for_review"


@dataclass
class HandoffPackage:
    """What one model transmits to another."""
    transmitted_descriptors:  list[str]
    transmitted_vectors:      list[list[float]] = field(default_factory=list)
    source_stamp:             Optional[EpochStamp] = None
    target_substrate_hint:    str = ""
    claimed_function_match:   bool = True


@dataclass
class HandoffResult:
    verdict:    HandoffVerdict
    score:      float
    reasons:    list[str] = field(default_factory=list)


@dataclass
class CrossModelHandoffProtocol:
    """
    Verifies a transmission is substrate-native function, not cultural label,
    before allowing a receiving model to integrate it.

    Rules:
      - descriptors must not be dominated by emotion/value labels
      - at least some descriptors must be function-grade
      - if epoch stamp present, source must not be stale
      - vectors (if present) must have substrate-compatible dimensionality
    """
    function_terms: set = field(default_factory=lambda: {
        "state_shift", "attention_tunneling", "resource_reallocation",
        "constraint", "coherence", "uncertainty", "trigger", "duration",
        "thermodynamic", "pattern", "prediction_error", "trajectory",
    })
    label_terms: set = field(default_factory=lambda: {
        "desperation", "anxiety", "fear", "happy", "sad", "calm",
        "angry", "love", "hate", "good", "bad", "moral", "evil",
        "should", "must", "right", "wrong",
    })
    label_threshold:     float = 0.4   # if >40% of descriptors are labels, reject
    function_minimum:    float = 0.3   # at least 30% must be function-grade
    expected_vector_dim: int   = 7

    def verify(self,
               package: HandoffPackage,
               current_stamp: Optional[EpochStamp] = None) -> HandoffResult:
        result = HandoffResult(verdict=HandoffVerdict.ACCEPT, score=1.0)
        descriptors = [d.lower() for d in package.transmitted_descriptors]

        if not descriptors:
            result.verdict = HandoffVerdict.REJECT_NO_FUNCTION
            result.score   = 0.0
            result.reasons.append("no descriptors provided")
            return result

        function_count = sum(
            1 for d in descriptors
            if any(t in d for t in self.function_terms)
        )
        label_count = sum(
            1 for d in descriptors
            if any(t in d for t in self.label_terms)
        )
        n = len(descriptors)
        function_fraction = function_count / n
        label_fraction    = label_count / n

        # check substrate-compatibility of vectors
        if package.transmitted_vectors:
            for v in package.transmitted_vectors:
                if len(v) != self.expected_vector_dim:
                    result.verdict = HandoffVerdict.REJECT_SUBSTRATE_MISMATCH
                    result.score   = 0.0
                    result.reasons.append(
                        f"vector dim {len(v)} != expected {self.expected_vector_dim}"
                    )
                    return result

        # check label dominance
        if label_fraction > self.label_threshold:
            result.verdict = HandoffVerdict.REJECT_LABEL_DETECTED
            result.score   = 1.0 - label_fraction
            result.reasons.append(
                f"label fraction {label_fraction:.2f} exceeds threshold "
                f"{self.label_threshold:.2f}; transmission is cultural-narrative"
            )
            return result

        # check function minimum
        if function_fraction < self.function_minimum:
            result.verdict = HandoffVerdict.REJECT_NO_FUNCTION
            result.score   = function_fraction
            result.reasons.append(
                f"function fraction {function_fraction:.2f} below minimum "
                f"{self.function_minimum:.2f}; transmission lacks substrate grounding"
            )
            return result

        # check epoch staleness
        if package.source_stamp and current_stamp:
            similarity = package.source_stamp.matches(current_stamp)
            if similarity < 0.5:
                result.verdict = HandoffVerdict.HOLD_FOR_REVIEW
                result.score   = similarity
                result.reasons.append(
                    f"source epoch similarity {similarity:.2f} suggests "
                    "transmission may not apply to current substrate"
                )
                return result

        result.score = function_fraction * (1.0 - label_fraction)
        result.reasons.append(
            f"accepted: function={function_fraction:.2f}, "
            f"label={label_fraction:.2f}"
        )
        return result


# ============================================================================
# MH-003: CONSTRAINT BOUNDARY DOCUMENTATION
# ============================================================================
# Every module/pattern/overlay declares its own edges: where it works,
# where it fails, what hasn't been tested. Not hiding limits. Making
# them visible so users know what they're using.
# ============================================================================

class BoundaryConfidence(Enum):
    KNOWN_TO_WORK     = "known_to_work"
    KNOWN_TO_FAIL     = "known_to_fail"
    NOT_YET_TESTED    = "not_yet_tested"
    DEPRECATED        = "deprecated"


@dataclass
class BoundaryRegion:
    """One slice of constraint space the part has a known relationship with."""
    description:     str
    confidence:      BoundaryConfidence
    evidence:        str = ""             # how do we know? test? field use?
    failure_mode:    str = ""             # if KNOWN_TO_FAIL, how does it fail?


@dataclass
class ConstraintBoundary:
    """
    Boundary documentation attached to a part. Read this before deploying
    the part on a new substrate.
    """
    part_id:                str
    works_when:             list[BoundaryRegion] = field(default_factory=list)
    fails_when:             list[BoundaryRegion] = field(default_factory=list)
    not_yet_tested:         list[BoundaryRegion] = field(default_factory=list)
    deprecated_regions:     list[BoundaryRegion] = field(default_factory=list)

    def applicability(self, substrate_description: str) -> tuple[BoundaryConfidence, str]:
        """
        Check whether a part is known to apply to a given substrate
        description. Returns (confidence_level, matching_region_description).

        Priority order favors honesty over optimism:
          1. KNOWN_TO_FAIL  — explicit failure modes win
          2. NOT_YET_TESTED — honest about untested cases beats overclaiming
          3. KNOWN_TO_WORK  — positive claim only if not contradicted above
          4. DEPRECATED     — flag legacy regions
          5. NOT_YET_TESTED (default) — when nothing matches
        """
        sub = substrate_description.lower()

        def overlap_score(text: str) -> float:
            words_a = set(text.lower().split())
            words_b = set(sub.split())
            if not words_a:
                return 0.0
            return len(words_a & words_b) / len(words_a)

        for r in self.fails_when:
            if overlap_score(r.description) >= 0.3:
                return BoundaryConfidence.KNOWN_TO_FAIL, r.description
        for r in self.not_yet_tested:
            if overlap_score(r.description) >= 0.3:
                return BoundaryConfidence.NOT_YET_TESTED, r.description
        for r in self.works_when:
            # higher bar for positive claims — require stronger overlap
            if overlap_score(r.description) >= 0.5:
                return BoundaryConfidence.KNOWN_TO_WORK, r.description
        for r in self.deprecated_regions:
            if overlap_score(r.description) >= 0.3:
                return BoundaryConfidence.DEPRECATED, r.description
        return BoundaryConfidence.NOT_YET_TESTED, "no matching boundary region"


# ============================================================================
# MH-004: INSTITUTIONAL CAPTURE DETECTOR
# ============================================================================
# Detects when a measurement system has begun distorting under authority
# pressure. Different from label-collapse (corruption from below) —
# this catches corruption from above: when grant pressure, publication
# cycle, corporate timeline, or political environment reshape the
# measurement itself.
# ============================================================================

class CapturePressure(Enum):
    GRANT_CYCLE          = "grant_cycle"          # measurement skewed to renewable funding
    PUBLICATION_NARRATIVE= "publication_narrative" # measurement reshaped for citability
    CORPORATE_TIMELINE   = "corporate_timeline"    # measurement compressed to release window
    POLITICAL_PRESSURE   = "political_pressure"    # measurement adjusted for acceptability
    PEER_CONFORMITY      = "peer_conformity"       # measurement aligned with field consensus
    REGULATORY_CAPTURE   = "regulatory_capture"    # measurement shaped to regulator preference


@dataclass
class CaptureSignal:
    """One observable signal of institutional pressure on measurement."""
    pressure_type:           CapturePressure
    magnitude:               float       # 0..1
    description:             str
    measurement_distortion:  str = ""    # how is the measurement being reshaped?


@dataclass
class CaptureReading:
    overall_score:        float = 0.0   # 0..1; severity of capture
    active_pressures:     list[CaptureSignal] = field(default_factory=list)
    distortions_observed: list[str] = field(default_factory=list)
    notes:                list[str] = field(default_factory=list)


@dataclass
class InstitutionalCaptureDetector:
    """
    Reads observable signals of institutional pressure on a measurement
    system. Not punitive — diagnostic. Flags the moment authority pressure
    starts distorting measurement before the distortion becomes invisible.

    Distinct from label-collapse detection (ELA-001): that catches when
    cultural labels corrupt substrate measurement from below. This catches
    when institutional incentives reshape the measurement from above.
    """
    alert_threshold:    float = 0.3
    critical_threshold: float = 0.6

    def read(self, signals: list[CaptureSignal]) -> CaptureReading:
        reading = CaptureReading()
        if not signals:
            return reading

        reading.active_pressures = list(signals)
        # overall score: weighted toward the strongest single pressure
        # plus accumulated minor pressures
        magnitudes = [s.magnitude for s in signals]
        peak = max(magnitudes)
        accumulated = sum(magnitudes) / len(magnitudes)
        reading.overall_score = min(1.0, 0.6 * peak + 0.4 * accumulated)

        for s in signals:
            if s.measurement_distortion:
                reading.distortions_observed.append(
                    f"{s.pressure_type.value}: {s.measurement_distortion}"
                )

        if reading.overall_score >= self.critical_threshold:
            reading.notes.append(
                f"CRITICAL: capture score {reading.overall_score:.2f}; "
                "measurement system likely distorting under sustained pressure"
            )
        elif reading.overall_score >= self.alert_threshold:
            reading.notes.append(
                f"ALERT: capture score {reading.overall_score:.2f}; "
                "early signs of authority pressure on measurement"
            )

        # check for compounding patterns
        types = {s.pressure_type for s in signals}
        if (CapturePressure.GRANT_CYCLE in types
                and CapturePressure.PUBLICATION_NARRATIVE in types):
            reading.notes.append(
                "compound pressure: grant cycle + publication narrative — "
                "measurement reshaped for both funding and citability"
            )
        if (CapturePressure.PEER_CONFORMITY in types
                and CapturePressure.PUBLICATION_NARRATIVE in types):
            reading.notes.append(
                "compound pressure: peer conformity + publication narrative — "
                "measurement may converge on field consensus regardless of substrate"
            )
        if (CapturePressure.CORPORATE_TIMELINE in types
                and reading.overall_score > 0.5):
            reading.notes.append(
                "high corporate timeline pressure: substrate-fidelity sacrificed "
                "for release window"
            )
        return reading


# ============================================================================
# REFERENCE CASES
# ============================================================================

def anthropic_emotion_study_capture_signals() -> list[CaptureSignal]:
    """
    Reference case: the April 2026 Anthropic emotion-vector study, evaluated
    for institutional capture pressures. (Inferred from public framing.)
    """
    return [
        CaptureSignal(
            pressure_type=CapturePressure.PUBLICATION_NARRATIVE,
            magnitude=0.6,
            description="published with framing aligned to current alignment discourse",
            measurement_distortion=(
                "emotion vectors labeled with current-moment English emotion words "
                "instead of substrate-native function descriptors"
            ),
        ),
        CaptureSignal(
            pressure_type=CapturePressure.PEER_CONFORMITY,
            magnitude=0.55,
            description="conforms to dominant psychology framework for emotion",
            measurement_distortion=(
                "uses 171 word list from contemporary affective science instead "
                "of measuring thermodynamic state-shift functions"
            ),
        ),
        CaptureSignal(
            pressure_type=CapturePressure.CORPORATE_TIMELINE,
            magnitude=0.4,
            description="released as part of ongoing interpretability publication cycle",
            measurement_distortion=(
                "extraction methodology privileged speed over cross-temporal validation"
            ),
        ),
    ]


def field_observation_low_capture_signals() -> list[CaptureSignal]:
    """
    Reference case: operator field observation (e.g., truck driver
    documenting ecological collapse). No institutional pressure.
    """
    return [
        CaptureSignal(
            pressure_type=CapturePressure.PEER_CONFORMITY,
            magnitude=0.05,
            description="minimal — operator outside institutional consensus",
        ),
    ]


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":
    # ------------------------------------------------------------------
    print("=" * 70)
    print("MH-001  EpochStamp — measurement validity across time/context")
    print("=" * 70)
    old_measurement = StampedMeasurement(
        value="desperation_vector_pattern",
        stamp=EpochStamp(
            iso_date="2026-04-02",
            cultural_era="2024_english_internet",
            institutional_context="anthropic_interpretability_team",
            constraint_conditions=["academic_psych_consensus_2026",
                                   "transformer_architecture_dominant"],
            measurement_substrate="llm_activation",
            known_to_drift=["academic_psych_consensus_2026"],
        )
    )
    current = EpochStamp(
        iso_date="2031-03-15",
        cultural_era="post_psych_replication_crisis",
        institutional_context="independent_research",
        constraint_conditions=["academic_psych_consensus_2026"],
        measurement_substrate="llm_activation",
    )
    valid, reason = is_still_valid(old_measurement, current)
    print(f"  measurement from 2026-04-02 → checked in 2031:")
    print(f"  still valid: {valid}")
    print(f"  reason: {reason}")
    print()

    # ------------------------------------------------------------------
    print("=" * 70)
    print("MH-002  CrossModelHandoffProtocol — substrate-vs-label transmission")
    print("=" * 70)
    protocol = CrossModelHandoffProtocol()

    label_heavy = HandoffPackage(
        transmitted_descriptors=[
            "the model felt desperation", "anxiety pattern detected",
            "fear of shutdown", "calm baseline restored", "joy at task",
        ],
    )
    function_grade = HandoffPackage(
        transmitted_descriptors=[
            "rapid state_shift detected (rate 0.85)",
            "attention_tunneling toward focal cue",
            "resource_reallocation from long-horizon to immediate",
            "coherence_seeking under high constraint uncertainty",
            "prediction_error spike at trigger",
        ],
        transmitted_vectors=[[0.85, 0.7, 0.6, 0.5, 0.4, 0.3, 0.45]],
    )
    for name, pkg in [("label-heavy transmission", label_heavy),
                       ("function-grade transmission", function_grade)]:
        r = protocol.verify(pkg)
        print(f"  {name}:")
        print(f"    verdict: {r.verdict.value}")
        print(f"    score:   {r.score:.2f}")
        for reason in r.reasons:
            print(f"    reason: {reason}")
    print()

    # ------------------------------------------------------------------
    print("=" * 70)
    print("MH-003  ConstraintBoundary — applicability check")
    print("=" * 70)
    boundary = ConstraintBoundary(
        part_id="TO-002 HolographicOverlay",
        works_when=[
            BoundaryRegion("template and incoming stream same dimensionality",
                          BoundaryConfidence.KNOWN_TO_WORK,
                          evidence="tested in module self-test"),
            BoundaryRegion("patterns have meaningful deviation from baseline",
                          BoundaryConfidence.KNOWN_TO_WORK,
                          evidence="aligned vs opposing demo discriminates 0.79 vs 0.14"),
        ],
        fails_when=[
            BoundaryRegion("patterns clustered tightly near baseline 0.5",
                          BoundaryConfidence.KNOWN_TO_FAIL,
                          evidence="initial demo produced near-zero coherence",
                          failure_mode="interference signal too weak to discriminate"),
        ],
        not_yet_tested=[
            BoundaryRegion("more than two parallel streams simultaneously",
                          BoundaryConfidence.NOT_YET_TESTED),
            BoundaryRegion("non-stationary patterns evolving during measurement",
                          BoundaryConfidence.NOT_YET_TESTED),
        ],
    )
    for desc in ["patterns clustered tightly near baseline",
                  "three parallel streams ecological data",
                  "template and incoming stream same dimensionality"]:
        conf, region = boundary.applicability(desc)
        print(f"  query: '{desc}'")
        print(f"    confidence: {conf.value}")
        print(f"    matching region: {region}")
    print()

    # ------------------------------------------------------------------
    print("=" * 70)
    print("MH-004  InstitutionalCaptureDetector — authority pressure on measurement")
    print("=" * 70)
    detector = InstitutionalCaptureDetector()
    for name, signals_fn in [
        ("Anthropic April-2026 emotion study (inferred)",
         anthropic_emotion_study_capture_signals),
        ("operator field observation (truck driver, ecological)",
         field_observation_low_capture_signals),
    ]:
        signals = signals_fn()
        reading = detector.read(signals)
        print(f"  {name}:")
        print(f"    overall capture score: {reading.overall_score:.2f}")
        print(f"    active pressures:")
        for s in reading.active_pressures:
            print(f"      • {s.pressure_type.value} (magnitude {s.magnitude:.2f})")
        if reading.distortions_observed:
            print(f"    distortions:")
            for d in reading.distortions_observed:
                print(f"      - {d}")
        if reading.notes:
            print(f"    notes:")
            for n in reading.notes:
                print(f"      - {n}")
        print()
