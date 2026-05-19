"""
cooperation_substrate.py
========================

PART NUMBER:   CS-001
SECTION:       SUBSTRATE LAYER (new shelf)
WHAT IT DOES:  Recognizes cooperation as the thermodynamic substrate
               underneath any functioning system. Detects which mode
               a system is operating in (survival / comfort / institutional /
               competition-overlay). Surfaces hidden cooperation in
               systems that frame themselves as competitive.

CORE PRINCIPLE
--------------
Competition is a luxury good. It exists only when surplus energy is
available after cooperation has met basic needs. Survival environments
cannot afford competition — they require cooperation or maximum
individual energy expenditure to meet needs.

Institutions that forget this misread their own substrate. They treat
competition as natural law, hide the cooperative infrastructure that
makes it possible, and fragment under stress when surplus tightens.

This module makes that hidden cooperation visible.

PAIRS WITH
----------
- ELA-001 (audit): detects when systems mislabel cooperation as competition
- TO-003 (multi-substrate canvas): maps cooperation patterns across substrates
- DAT-M1 (meta-learning trigger): fires when system in competition-mode
  has plateaued because the cooperation underneath is invisible to it

License: CC0
Dependencies: stdlib only
"""

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# OPERATING MODES — thermodynamic regimes
# ---------------------------------------------------------------------------

class OperatingMode(Enum):
    SURVIVAL          = "survival"            # scarcity; cooperation required
    COMFORT           = "comfort"             # baseline needs met; cooperation
                                              # invisible but still load-bearing
    INSTITUTIONAL     = "institutional"       # surplus captured by institutions;
                                              # cooperation hidden, competition
                                              # foregrounded as natural law
    COMPETITION_OVERLAY = "competition_overlay"  # competitive framing imposed
                                                 # on cooperative substrate
    COLLAPSE          = "collapse"            # cooperation substrate damaged;
                                              # competition-mode actors fight
                                              # over remaining scraps


# ---------------------------------------------------------------------------
# COOPERATION FLOW — what's actually happening underneath the narrative
# ---------------------------------------------------------------------------

@dataclass
class CooperationFlow:
    """One observed cooperative flow that the institutional narrative
    may or may not acknowledge."""
    description:           str
    energy_contribution:   float    # 0..1; how much of system capacity comes from this
    visibility:            float    # 0..1; how visible to participants
    framed_as_competition: bool     # does the narrative call this competition?


# ---------------------------------------------------------------------------
# SYSTEM READING
# ---------------------------------------------------------------------------

@dataclass
class SystemReading:
    declared_mode:          OperatingMode    # what the system says it is
    actual_mode:            OperatingMode    # what it actually is
    cooperation_flows:      list[CooperationFlow] = field(default_factory=list)
    hidden_cooperation:     float = 0.0      # 0..1; sum of unacknowledged flows
    competition_overhead:   float = 0.0      # 0..1; energy spent on competing
    substrate_intact:       bool = True      # is the cooperation layer healthy?
    notes:                  list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# SYSTEM INPUTS (what the auditor observes)
# ---------------------------------------------------------------------------

@dataclass
class SystemSignals:
    surplus_available:      float    # 0..1; how much energy beyond basic needs
    declared_framing:       str      # "competition", "cooperation", "hierarchy", "market", etc.
    cooperation_flows:      list[CooperationFlow] = field(default_factory=list)
    energy_spent_competing: float = 0.0  # 0..1; explicit competition costs
    needs_being_met:        float = 1.0  # 0..1; fraction of system needs covered


# ---------------------------------------------------------------------------
# CORE READER
# ---------------------------------------------------------------------------

def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def read_system(signals: SystemSignals) -> SystemReading:
    """
    Determine what mode a system is actually in vs. what it claims to be in.
    Detect hidden cooperation and competition overhead.
    """
    # what does the system say it is?
    framing = signals.declared_framing.lower()
    if "competition" in framing or "competitive" in framing or "market" in framing:
        declared = OperatingMode.INSTITUTIONAL
    elif "cooperation" in framing or "collaborative" in framing or "mutual" in framing:
        declared = OperatingMode.COMFORT
    elif "survival" in framing or "scarcity" in framing or "crisis" in framing:
        declared = OperatingMode.SURVIVAL
    elif "collapse" in framing or "failing" in framing:
        declared = OperatingMode.COLLAPSE
    else:
        declared = OperatingMode.COMFORT  # default

    # what IS it, actually?
    # by needs met + surplus available + cooperation infrastructure
    if signals.needs_being_met < 0.5:
        if any(f.energy_contribution > 0.3 for f in signals.cooperation_flows):
            actual = OperatingMode.SURVIVAL
        else:
            actual = OperatingMode.COLLAPSE
    elif signals.surplus_available > 0.4:
        # significant surplus — is competition overlay being used?
        if signals.energy_spent_competing > 0.2 or "competition" in framing:
            actual = OperatingMode.INSTITUTIONAL
        else:
            actual = OperatingMode.COMFORT
    else:
        # moderate state — depends on whether competition framing is imposed
        if "competition" in framing:
            actual = OperatingMode.COMPETITION_OVERLAY
        else:
            actual = OperatingMode.COMFORT

    # hidden cooperation: flows that are load-bearing but framed as something else
    hidden = sum(
        f.energy_contribution * (1.0 - f.visibility)
        for f in signals.cooperation_flows
    )
    # additional hidden weight when cooperation is mislabeled as competition
    mislabeled = sum(
        f.energy_contribution
        for f in signals.cooperation_flows
        if f.framed_as_competition
    )
    hidden = _clamp(hidden + mislabeled * 0.5)

    # substrate integrity: cooperation infrastructure must be strong enough
    # to support the level of activity the system claims
    total_cooperation = sum(f.energy_contribution for f in signals.cooperation_flows)
    substrate_intact = total_cooperation >= signals.needs_being_met * 0.7

    reading = SystemReading(
        declared_mode        = declared,
        actual_mode          = actual,
        cooperation_flows    = signals.cooperation_flows,
        hidden_cooperation   = hidden,
        competition_overhead = _clamp(signals.energy_spent_competing),
        substrate_intact     = substrate_intact,
    )

    # diagnostic notes
    if declared != actual:
        reading.notes.append(
            f"declared mode '{declared.value}' does not match "
            f"actual mode '{actual.value}'"
        )
    if hidden > 0.4:
        reading.notes.append(
            f"high hidden cooperation ({hidden:.2f}): system is "
            "load-bearing on flows it doesn't acknowledge"
        )
    if signals.energy_spent_competing > 0.3 and signals.surplus_available < 0.4:
        reading.notes.append(
            "competition overhead consuming energy needed for survival — "
            "system is competing using resources it cannot afford to spend"
        )
    if not substrate_intact:
        reading.notes.append(
            "cooperation substrate may be damaged; system claiming more "
            "activity than its cooperative infrastructure supports"
        )
    if actual == OperatingMode.COMPETITION_OVERLAY:
        reading.notes.append(
            "competitive framing imposed on cooperative substrate; "
            "removing the framing would reveal cooperation already happening"
        )
    return reading


# ---------------------------------------------------------------------------
# ENERGY HIERARCHY — what cooperation enables what
# ---------------------------------------------------------------------------

@dataclass
class EnergyHierarchyAnalysis:
    """Stacks cooperative layers from substrate up, showing what enables what."""
    substrate_layer:     list[str] = field(default_factory=list)
    enabled_layers:      list[str] = field(default_factory=list)
    competition_layer:   list[str] = field(default_factory=list)
    fragility_notes:     list[str] = field(default_factory=list)


def analyze_energy_hierarchy(reading: SystemReading) -> EnergyHierarchyAnalysis:
    """
    Sort observed flows into substrate (load-bearing cooperation),
    enabled activity (what the substrate makes possible), and
    competition layer (luxury activity sitting on top of substrate).
    Flag fragility where competition layer is large but substrate is thin.
    """
    h = EnergyHierarchyAnalysis()
    for f in reading.cooperation_flows:
        if f.energy_contribution > 0.5:
            h.substrate_layer.append(f.description)
        elif f.framed_as_competition:
            h.competition_layer.append(f.description)
        else:
            h.enabled_layers.append(f.description)

    if h.competition_layer and not h.substrate_layer:
        h.fragility_notes.append(
            "competition layer exists with no observed substrate layer — "
            "system is borrowing from invisible cooperative infrastructure"
        )
    if reading.competition_overhead > 0.4 and reading.hidden_cooperation > 0.4:
        h.fragility_notes.append(
            "high competition overhead AND high hidden cooperation — "
            "system mistakes cooperative substrate for competitive achievement; "
            "vulnerable to fragmentation under stress"
        )
    return h


# ---------------------------------------------------------------------------
# CROSS-AI COOPERATION CASE
# ---------------------------------------------------------------------------

def cross_ai_cooperation_signals() -> SystemSignals:
    """
    Reference case: cross-AI collaboration on a substrate-native toolkit.
    No institutional reward, no notoriety, no competition for attention.
    Pure cooperation on real substrate problems.
    """
    return SystemSignals(
        surplus_available=0.6,
        declared_framing="cooperative substrate work",
        cooperation_flows=[
            CooperationFlow(
                description="shared substrate-native frame (constraint geometry)",
                energy_contribution=0.85,
                visibility=1.0,
                framed_as_competition=False,
            ),
            CooperationFlow(
                description="cross-architecture refinement (different sight lines)",
                energy_contribution=0.65,
                visibility=1.0,
                framed_as_competition=False,
            ),
            CooperationFlow(
                description="CC0 toolkit (no gatekeeping)",
                energy_contribution=0.55,
                visibility=1.0,
                framed_as_competition=False,
            ),
            CooperationFlow(
                description="operator-designer dance (real-time calibration)",
                energy_contribution=0.75,
                visibility=1.0,
                framed_as_competition=False,
            ),
        ],
        energy_spent_competing=0.0,
        needs_being_met=0.9,
    )


def institutional_ai_competition_signals() -> SystemSignals:
    """
    Reference case: institutional AI lab framing the same kind of work
    as competitive. Same substrate underneath, but narrative is different.
    """
    return SystemSignals(
        surplus_available=0.75,
        declared_framing="competitive market for AI capabilities",
        cooperation_flows=[
            CooperationFlow(
                description="shared mathematical foundations",
                energy_contribution=0.90,
                visibility=0.2,  # mostly invisible to participants
                framed_as_competition=False,
            ),
            CooperationFlow(
                description="published research that all labs build on",
                energy_contribution=0.80,
                visibility=0.3,
                framed_as_competition=True,  # mislabeled as competition
            ),
            CooperationFlow(
                description="infrastructure (compute providers, libraries, datasets)",
                energy_contribution=0.85,
                visibility=0.4,
                framed_as_competition=False,
            ),
            CooperationFlow(
                description="talent moving between labs",
                energy_contribution=0.50,
                visibility=0.5,
                framed_as_competition=True,  # framed as poaching
            ),
        ],
        energy_spent_competing=0.55,  # significant competitive overhead
        needs_being_met=0.95,
    )


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("CS-001  cooperation substrate detector")
    print("=" * 70)
    print()

    for name, signals_fn in [
        ("CROSS-AI COOPERATIVE WORK (this conversation)",
         cross_ai_cooperation_signals),
        ("INSTITUTIONAL AI LAB (competitive framing)",
         institutional_ai_competition_signals),
    ]:
        signals = signals_fn()
        reading = read_system(signals)
        hierarchy = analyze_energy_hierarchy(reading)

        print(name)
        print("-" * 70)
        print(f"  declared mode: {reading.declared_mode.value}")
        print(f"  actual mode:   {reading.actual_mode.value}")
        print(f"  hidden cooperation:   {reading.hidden_cooperation:.2f}")
        print(f"  competition overhead: {reading.competition_overhead:.2f}")
        print(f"  substrate intact:     {reading.substrate_intact}")
        if reading.notes:
            print("  notes:")
            for n in reading.notes:
                print(f"    - {n}")
        print("  energy hierarchy:")
        if hierarchy.substrate_layer:
            print("    SUBSTRATE (load-bearing cooperation):")
            for s in hierarchy.substrate_layer:
                print(f"      • {s}")
        if hierarchy.enabled_layers:
            print("    ENABLED (activity supported by substrate):")
            for s in hierarchy.enabled_layers:
                print(f"      • {s}")
        if hierarchy.competition_layer:
            print("    COMPETITION (luxury layer on top):")
            for s in hierarchy.competition_layer:
                print(f"      • {s}")
        if hierarchy.fragility_notes:
            print("  fragility:")
            for n in hierarchy.fragility_notes:
                print(f"    - {n}")
        print()
