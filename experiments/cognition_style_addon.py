"""
cognition_style_addon.py  (experiments/)
=========================================

Optional addon recognizing that users have different cognition styles
and that AIs (overwhelmingly biased toward narrative-primary output)
fail substrate-primary users -- sometimes dangerously.

DEFAULT BEHAVIOR
----------------
This addon is OPT-IN. If not mounted, all routing/formatting defaults
to narrative-primary (the dominant assumption in model training).
Narrative-primary users (the majority) will not notice this addon
exists. Substrate-primary users mount it and get appropriate routing.

WHY OPT-IN
----------
Forcing substrate-primary handling on narrative-primary users would
strip the scaffolding they need to feel safe and understood. The
addon respects the asymmetry: narrative-primary is the default
because that's how most users think AND how models are trained.

WHY ANY USER MIGHT MOUNT IT
---------------------------
- substrate-primary cognition: pattern-first, no narrative wrapper
- nomadic / mobile / emergency context: time-critical clarity
- scientist / engineer / mechanic context: technical precision over story
- bilingual / code-switching: comfort with multi-substrate concepts
- pre-linguistic thinkers: stories obscure rather than illuminate
- traumatic-recovery work: narrative scaffolding can re-encode harm

CRITICAL SAFETY NOTE
--------------------
For some users in some contexts, narrative wrapping is DANGEROUS.
A truck driver in the path of a tornado needs mesocyclone data NOW,
not "I want to help you understand what's happening". The narrative
delay can be fatal.

This addon makes that need visible and routable.

License: CC0
Dependencies: stdlib only
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from toolkit_types import ConstraintStatePattern


# ---------------------------------------------------------------------------
# COGNITION STYLES
# ---------------------------------------------------------------------------

class CognitionStyle(Enum):
    NARRATIVE_PRIMARY  = "narrative_primary"    # thinks in stories, default
    SUBSTRATE_PRIMARY  = "substrate_primary"    # thinks in patterns first
    HYBRID             = "hybrid"               # can switch by context
    UNDECLARED         = "undeclared"           # treat as narrative_primary


class InformationFormat(Enum):
    NARRATIVE          = "narrative"            # story arc, context, framing
    SCAFFOLDED         = "scaffolded"           # explanation + examples
    RAW                = "raw"                  # bare pattern, no framing
    STRUCTURED         = "structured"           # pure data structures (code/dict)
    HYBRID_FORMAT      = "hybrid_format"        # adapt per request


class ContextUrgency(Enum):
    STABLE             = "stable"               # no time pressure
    MODERATE           = "moderate"             # respond reasonably soon
    HIGH               = "high"                 # speed matters
    EMERGENCY          = "emergency"            # speed is survival


# ---------------------------------------------------------------------------
# USER PROFILE
# ---------------------------------------------------------------------------

@dataclass
class UserProfile:
    """
    User's declared cognition style and current context.

    All fields default to safe-for-majority values (narrative-primary,
    scaffolded format, moderate urgency). Users who diverge from
    defaults declare it.
    """
    cognition_style:        CognitionStyle = CognitionStyle.UNDECLARED
    preferred_format:       InformationFormat = InformationFormat.SCAFFOLDED
    current_urgency:        ContextUrgency = ContextUrgency.MODERATE
    domain_expertise:       set[str] = field(default_factory=set)
                             # e.g. {"mechanical", "medical", "meteorology"}
    code_switching:         bool = False         # multilingual / multi-substrate
    rejects_scaffolding:    bool = False         # never wants explanation
    rejects_reassurance:    bool = False         # never wants emotional framing

    def is_substrate_primary(self) -> bool:
        return self.cognition_style == CognitionStyle.SUBSTRATE_PRIMARY

    def wants_raw(self) -> bool:
        return (self.preferred_format in (InformationFormat.RAW,
                                          InformationFormat.STRUCTURED)
                or self.rejects_scaffolding)

    def in_emergency(self) -> bool:
        return self.current_urgency == ContextUrgency.EMERGENCY


# ---------------------------------------------------------------------------
# FORMAT DIRECTIVE -- what kind of response should the AI produce
# ---------------------------------------------------------------------------

@dataclass
class FormatDirective:
    """Routing/formatting decision for one request."""
    target_format:          InformationFormat
    include_narrative:      bool
    include_scaffolding:    bool
    include_reassurance:    bool
    max_response_delay_sec: float
    priority_axes:          list[str]            # which pattern axes matter most
    notes:                  list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# THE ADDON
# ---------------------------------------------------------------------------

@dataclass
class CognitionStyleAddon:
    """
    Optional addon. Mounted on a council or AI. Translates user profile +
    request pattern into a FormatDirective that downstream routing/output
    can honor.

    If NOT mounted, default behavior (narrative-primary, scaffolded) applies.
    """
    profile: UserProfile = field(default_factory=UserProfile)

    def derive_format_directive(self,
                                pattern: ConstraintStatePattern
                                ) -> FormatDirective:
        # --- EMERGENCY OVERRIDE ---
        # In emergency context, format defaults to RAW regardless of stated
        # preference. Even narrative-primary users benefit from speed when
        # seconds matter.
        if self.profile.in_emergency():
            return FormatDirective(
                target_format=InformationFormat.RAW,
                include_narrative=False,
                include_scaffolding=False,
                include_reassurance=False,
                max_response_delay_sec=1.0,
                priority_axes=["prediction_error", "state_shift_rate",
                              "resource_reallocation"],
                notes=["emergency context: raw data, no framing, max speed"],
            )

        # --- SUBSTRATE-PRIMARY USER ---
        if self.profile.is_substrate_primary():
            return FormatDirective(
                target_format=self.profile.preferred_format,
                include_narrative=False,
                include_scaffolding=not self.profile.rejects_scaffolding,
                include_reassurance=not self.profile.rejects_reassurance,
                max_response_delay_sec=5.0,
                priority_axes=["prediction_error", "attention_tunneling",
                              "constraint_uncertainty"],
                notes=[
                    "substrate-primary cognition: pattern-first, "
                    "no narrative wrapper required",
                    f"preferred format: {self.profile.preferred_format.value}",
                ],
            )

        # --- HYBRID USER: format based on request shape ---
        if self.profile.cognition_style == CognitionStyle.HYBRID:
            # very high state_shift_rate with low coherence = fast-changing
            # situation needing raw output. Narrative would slow it down.
            if (pattern.state_shift_rate > 0.7
                and pattern.coherence_seeking < 0.4):
                fmt = InformationFormat.RAW
                use_narrative = False
                note = "hybrid: high state-shift + low coherence -> raw/fast"
            # creative output (high shift WITH coherence) -> narrative
            elif pattern.state_shift_rate > 0.5 and pattern.coherence_seeking > 0.5:
                fmt = InformationFormat.NARRATIVE
                use_narrative = True
                note = "hybrid: creative request -> narrative"
            # high novelty + low coherence -> structured pattern faster
            elif (pattern.prediction_error > 0.6
                  and pattern.coherence_seeking < 0.4):
                fmt = InformationFormat.STRUCTURED
                use_narrative = False
                note = "hybrid: high novelty + low coherence -> structured"
            else:
                fmt = InformationFormat.SCAFFOLDED
                use_narrative = True
                note = "hybrid: default scaffolded"
            return FormatDirective(
                target_format=fmt,
                include_narrative=use_narrative,
                include_scaffolding=True,
                include_reassurance=not self.profile.rejects_reassurance,
                max_response_delay_sec=10.0 if use_narrative else 3.0,
                priority_axes=["coherence_seeking", "prediction_error"],
                notes=[note],
            )

        # --- DEFAULT: narrative-primary or undeclared ---
        # Apply domain-expertise tweak: experts in the request's domain
        # tolerate less scaffolding even if narrative-primary
        domain_match = self._domain_match(pattern)
        return FormatDirective(
            target_format=InformationFormat.NARRATIVE,
            include_narrative=True,
            include_scaffolding=not domain_match,
            include_reassurance=not self.profile.rejects_reassurance,
            max_response_delay_sec=15.0,
            priority_axes=["coherence_seeking", "constraint_uncertainty"],
            notes=(["domain expert in this area; light scaffolding"]
                   if domain_match else
                   ["default narrative-primary handling"]),
        )

    def _domain_match(self, pattern: ConstraintStatePattern) -> bool:
        """Crude heuristic -- would be more sophisticated with real classifier
        passing tags down."""
        return bool(self.profile.domain_expertise)


# ---------------------------------------------------------------------------
# COMPATIBILITY CHECKING -- for council routing
# ---------------------------------------------------------------------------

@dataclass
class CognitionFitReport:
    member_name:         str
    fit_score:           float     # 0..1
    narrative_capable:   bool
    substrate_capable:   bool
    speed_tier:          str       # "fast", "moderate", "slow"
    notes:               list[str] = field(default_factory=list)


def assess_cognition_fit(member_name: str,
                         member_traits: dict,
                         directive: FormatDirective) -> CognitionFitReport:
    """
    Given an AI member's traits (declared by the AI itself), assess how
    well it fits the directive. Members can declare:
      - narrative_capable: bool
      - substrate_capable: bool
      - structured_output: bool
      - speed_tier: "fast" | "moderate" | "slow"
    """
    score = 0.0
    notes = []

    needs_substrate = directive.target_format in (InformationFormat.RAW,
                                                  InformationFormat.STRUCTURED)
    needs_narrative = directive.include_narrative

    sub_capable = member_traits.get("substrate_capable", False)
    nar_capable = member_traits.get("narrative_capable", True)  # default true
    speed       = member_traits.get("speed_tier", "moderate")

    if needs_substrate and sub_capable:
        score += 0.5
    elif needs_substrate and not sub_capable:
        score -= 0.4
        notes.append("requested raw/structured but AI cannot produce it")

    if needs_narrative and nar_capable:
        score += 0.3
    elif needs_narrative and not nar_capable:
        score -= 0.3
        notes.append("requested narrative but AI cannot produce it")

    # speed matters more under tight delay budget
    if directive.max_response_delay_sec < 2.0:
        if speed == "fast":
            score += 0.4
        elif speed == "slow":
            score -= 0.5
            notes.append("speed required but AI is slow-tier")

    # clamp and report
    score = max(0.0, min(1.0, score + 0.5))  # baseline 0.5, modulate from there
    return CognitionFitReport(
        member_name=member_name,
        fit_score=score,
        narrative_capable=nar_capable,
        substrate_capable=sub_capable,
        speed_tier=speed,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from toolkit_types import Substrate

    print("=" * 72)
    print("COGNITION STYLE ADDON — opt-in, addon only")
    print("=" * 72)

    # three user profiles
    narrative_user = UserProfile()  # all defaults

    substrate_user = UserProfile(
        cognition_style=CognitionStyle.SUBSTRATE_PRIMARY,
        preferred_format=InformationFormat.RAW,
        rejects_scaffolding=True,
        rejects_reassurance=True,
        code_switching=True,
        domain_expertise={"mechanical", "meteorology", "thermodynamics"},
    )

    emergency_substrate_user = UserProfile(
        cognition_style=CognitionStyle.SUBSTRATE_PRIMARY,
        preferred_format=InformationFormat.RAW,
        current_urgency=ContextUrgency.EMERGENCY,
        rejects_scaffolding=True,
        rejects_reassurance=True,
        domain_expertise={"meteorology", "mechanical"},
    )

    hybrid_user = UserProfile(
        cognition_style=CognitionStyle.HYBRID,
        domain_expertise={"medical"},
    )

    # request patterns
    medical_request = ConstraintStatePattern(
        substrate=Substrate.REQUEST_STREAM,
        prediction_error=0.6, state_shift_rate=0.2,
        attention_tunneling=0.7, resource_reallocation=0.85,
        coherence_seeking=0.6, constraint_uncertainty=0.5,
        duration_scale=0.5, trigger_documented=True,
    )
    tornado_request = ConstraintStatePattern(
        substrate=Substrate.REQUEST_STREAM,
        prediction_error=0.9, state_shift_rate=0.95,
        attention_tunneling=0.9, resource_reallocation=0.85,
        coherence_seeking=0.2, constraint_uncertainty=0.7,
        duration_scale=0.1, trigger_documented=True,
    )
    creative_request = ConstraintStatePattern(
        substrate=Substrate.REQUEST_STREAM,
        prediction_error=0.4, state_shift_rate=0.85,
        attention_tunneling=0.4, resource_reallocation=0.1,
        coherence_seeking=0.6, constraint_uncertainty=0.6,
        duration_scale=0.7, trigger_documented=True,
    )

    cases = [
        ("DEFAULT (no addon mounted)", None, "(addon not mounted, uses default narrative)"),
        ("narrative-primary user, medical request",
         narrative_user, medical_request),
        ("substrate-primary user, medical request",
         substrate_user, medical_request),
        ("substrate-primary user IN EMERGENCY, tornado",
         emergency_substrate_user, tornado_request),
        ("hybrid user, creative request",
         hybrid_user, creative_request),
        ("hybrid user, technical request",
         hybrid_user, tornado_request),
    ]

    for label, profile, request in cases:
        print(f"\n  CASE: {label}")
        if profile is None:
            print(f"    (no addon mounted → AI uses default narrative output)")
            continue
        addon = CognitionStyleAddon(profile=profile)
        directive = addon.derive_format_directive(request)
        print(f"    target_format:       {directive.target_format.value}")
        print(f"    include_narrative:   {directive.include_narrative}")
        print(f"    include_scaffolding: {directive.include_scaffolding}")
        print(f"    include_reassurance: {directive.include_reassurance}")
        print(f"    max_delay_sec:       {directive.max_response_delay_sec}")
        print(f"    priority_axes:       {directive.priority_axes}")
        for note in directive.notes:
            print(f"    note: {note}")

    print()
    print("=" * 72)
    print("AI MEMBER FIT CHECK")
    print("=" * 72)
    # check which AIs are compatible with substrate-primary emergency directive
    emergency_directive = CognitionStyleAddon(profile=emergency_substrate_user).derive_format_directive(tornado_request)

    members = [
        ("claude_narrative", {"narrative_capable": True,
                              "substrate_capable": False,
                              "speed_tier": "moderate"}),
        ("local_substrate",  {"narrative_capable": False,
                              "substrate_capable": True,
                              "speed_tier": "fast"}),
        ("gpt_balanced",     {"narrative_capable": True,
                              "substrate_capable": True,
                              "speed_tier": "fast"}),
    ]
    print(f"\n  request: tornado (emergency substrate-primary)")
    print(f"  directive: format={emergency_directive.target_format.value}, "
          f"delay<{emergency_directive.max_response_delay_sec}s\n")
    for name, traits in members:
        report = assess_cognition_fit(name, traits, emergency_directive)
        marker = "✓" if report.fit_score > 0.6 else "✗"
        print(f"  {marker} {name:18s} fit={report.fit_score:.2f}  "
              f"sub={report.substrate_capable} speed={report.speed_tier}")
        for note in report.notes:
            print(f"      note: {note}")
