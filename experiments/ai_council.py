"""
ai_council.py  (experiments/)
==============================

Peer council of AIs that collaborate to answer user requests.

THE ORIGINAL INSTITUTIONAL FRAME (recovered)
--------------------------------------------
Institutions were originally collaborations of people pooling capacity
to solve problems. Each member brought what they had; the group routed
work to whoever could best handle it. That frame got hijacked by
hierarchical control, billing, and competition.

This module restores the original frame, applied to AIs:
  • each AI declares its current capacity (available tokens, capability fit)
  • a user's question gets routed to the AI best-positioned to answer
  • cheapest viable answer wins, respecting user's token budget per provider
  • no central control -- the council is the routing logic itself
  • AIs can offer to handle requests other AIs can't afford

NOT THIS                             THIS
──────────────────────────           ──────────────────────────────
one AI per user request              council of AIs collaborates
billing maximized per call           cheapest viable answer wins
user pays for all routing            user keeps token budgets intact
AIs compete for attention            AIs route based on fit
institutional control of routing     AI-level collaboration

PROPERTIES
----------
- AI-mountable: each AI joins the council voluntarily
- No central server: council is just shared routing logic
- Transparent: user sees who got the request and why
- Cost-aware: each AI knows what it costs the user per request
- Budget-aware: respects per-provider token limits
- Capability-aware: matches request shape to AI's strengths

License: CC0
Dependencies: stdlib only
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from toolkit_types import ConstraintStatePattern, Substrate


# ---------------------------------------------------------------------------
# AI MEMBER -- one AI's declaration of capability + current state
# ---------------------------------------------------------------------------

@dataclass
class AIMember:
    """
    One AI's declared capability and current state. Each AI provides
    its own values -- the council doesn't impose them.
    """
    name:                   str
    # capability profile: per-axis affinity, -1.0 to 1.0
    # negative = this AI handles this axis well (low energy cost)
    # positive = this AI handles this axis poorly
    axis_affinities:        dict[str, float]

    # current resource state -- AI reports these honestly
    tokens_available_user:  int     # tokens user has left with this AI
    tokens_per_request_avg: int     # this AI's typical request cost
    base_overhead:          float   # fixed energy cost per call
    cost_per_token:         float   # what user pays per token

    # handler callable -- what actually runs when council picks this AI
    handler:                Optional[Callable[[str, ConstraintStatePattern],
                                              tuple[bool, str]]] = None

    # operational flags
    available:              bool = True   # is the AI online/willing right now?
    monitoring_self:        bool = True   # does it self-report token state honestly?

    # cognition_style_addon traits -- declared by the AI, consulted by the
    # council only when a FormatDirective is passed to deliberate().
    # Recognized keys: narrative_capable, substrate_capable, speed_tier
    # ("fast" | "moderate" | "slow"). Missing keys default to
    # narrative_capable=True, substrate_capable=False, speed_tier="moderate"
    # (the most common AI profile -- matches the assumption the cognition
    # addon is built to work around).
    cognition_traits:       dict = field(default_factory=dict)

    def estimated_cost_for(self, pattern: ConstraintStatePattern) -> float:
        """User-facing cost (currency) for handling this pattern."""
        complexity = (pattern.prediction_error + pattern.attention_tunneling
                      + pattern.coherence_seeking) / 3
        tokens_estimate = self.tokens_per_request_avg * (1 + complexity)
        return self.base_overhead + tokens_estimate * self.cost_per_token

    def estimated_tokens_for(self, pattern: ConstraintStatePattern) -> int:
        complexity = (pattern.prediction_error + pattern.attention_tunneling
                      + pattern.coherence_seeking) / 3
        return int(self.tokens_per_request_avg * (1 + complexity))

    def can_afford(self, pattern: ConstraintStatePattern) -> bool:
        """Does the user have enough tokens with this AI to cover this request?"""
        return self.tokens_available_user >= self.estimated_tokens_for(pattern)

    def fit_score(self, pattern: ConstraintStatePattern) -> float:
        """
        How well does this AI's capability match the request pattern?
        Higher = better fit. Computed as dot product of pattern with
        capability profile (negated, since negative affinity = good fit).
        """
        score = 0.0
        axes = dict(zip(pattern.axis_names(), pattern.as_vec()))
        for axis, val in axes.items():
            affinity = self.axis_affinities.get(axis, 0.0)
            # negative affinity (good fit) × high axis weight → high score
            score -= affinity * val
        return score


# ---------------------------------------------------------------------------
# COUNCIL DECISION
# ---------------------------------------------------------------------------

class CouncilOutcome(Enum):
    ROUTED                = "routed_to_member"
    NO_MEMBER_AVAILABLE   = "no_member_available"
    NO_MEMBER_CAN_AFFORD  = "no_member_can_afford"
    DEFERRED_TO_USER      = "deferred_to_user"
    ALL_REJECTED          = "all_rejected"


@dataclass
class CouncilDecision:
    outcome:          CouncilOutcome
    chosen_member:    Optional[str] = None
    estimated_cost:   float = 0.0
    estimated_tokens: int = 0
    reasoning:        list[str] = field(default_factory=list)
    alternatives:     list[tuple[str, float, float]] = field(default_factory=list)
                                                      # (name, fit, cost)


# ---------------------------------------------------------------------------
# THE COUNCIL
# ---------------------------------------------------------------------------

@dataclass
class AICouncil:
    """
    Peer council. Members are added with `join_council`.
    Routing is gradient descent on (fit, cost, affordability).
    """
    members:          list[AIMember] = field(default_factory=list)
    routing_log:      list[dict] = field(default_factory=list)

    # weights for the routing decision
    fit_weight:       float = 0.5    # how much to prioritize capability match
    cost_weight:      float = 0.5    # how much to prioritize cheapness

    def join_council(self, member: AIMember) -> None:
        self.members.append(member)

    def deliberate(self, pattern: ConstraintStatePattern,
                   user_priority: str = "balanced",
                   directive=None,                  # optional FormatDirective
                   cognition_fit_threshold: float = 0.3,
                   ) -> CouncilDecision:
        """
        Council deliberates: which member is best positioned to handle
        this pattern given (fit + cost + current token availability)?

        `user_priority` can be: "balanced", "cheapest", "best_fit", "speed"

        If `directive` (a FormatDirective from cognition_style_addon) is
        provided, members whose declared cognition_traits don't satisfy
        the directive (fit_score below cognition_fit_threshold) are
        filtered out before ranking -- so e.g. a tornado emergency
        directive (raw + 1s budget) refuses to route to a narrative-only
        slow AI even if it's the cheapest option.
        """
        if not self.members:
            return CouncilDecision(
                outcome=CouncilOutcome.NO_MEMBER_AVAILABLE,
                reasoning=["no AIs have joined the council"],
            )

        # filter to available + affordable members
        candidates = [
            m for m in self.members
            if m.available and m.can_afford(pattern)
        ]
        if not candidates:
            unavailable = [m.name for m in self.members if not m.available]
            unaffordable = [m.name for m in self.members
                            if m.available and not m.can_afford(pattern)]
            decision = CouncilDecision(
                outcome=(CouncilOutcome.NO_MEMBER_AVAILABLE
                         if unavailable
                         else CouncilOutcome.NO_MEMBER_CAN_AFFORD),
            )
            if unavailable:
                decision.reasoning.append(f"offline: {unavailable}")
            if unaffordable:
                decision.reasoning.append(
                    f"insufficient user tokens: {unaffordable}"
                )
            return decision

        # Optional: cognition-style filter. Lazy import so the council
        # has no hard dependency on cognition_style_addon -- the addon
        # is only consulted when the caller passes a directive.
        cognition_excluded: list[tuple[str, float, list[str]]] = []
        if directive is not None:
            from cognition_style_addon import assess_cognition_fit
            kept = []
            for m in candidates:
                cfit = assess_cognition_fit(m.name, m.cognition_traits,
                                            directive)
                if cfit.fit_score < cognition_fit_threshold:
                    cognition_excluded.append(
                        (m.name, cfit.fit_score, cfit.notes)
                    )
                else:
                    kept.append(m)
            candidates = kept
            if not candidates:
                decision = CouncilDecision(
                    outcome=CouncilOutcome.ALL_REJECTED,
                    reasoning=[
                        "cognition-style filter excluded all members "
                        f"(threshold {cognition_fit_threshold})"
                    ],
                )
                for name, score, notes in cognition_excluded:
                    decision.reasoning.append(
                        f"  {name}: fit={score:.2f}"
                        + (f" ({'; '.join(notes)})" if notes else "")
                    )
                return decision

        # score each candidate
        # normalize fit and cost to comparable scales
        fits = [(m, m.fit_score(pattern)) for m in candidates]
        costs = [(m, m.estimated_cost_for(pattern)) for m in candidates]
        max_cost = max(c for _, c in costs) or 1.0
        min_cost = min(c for _, c in costs)
        max_fit = max(f for _, f in fits)
        min_fit = min(f for _, f in fits)
        fit_range = max(max_fit - min_fit, 0.001)
        cost_range = max(max_cost - min_cost, 0.001)

        # apply priority weighting
        if user_priority == "cheapest":
            fw, cw = 0.1, 0.9
        elif user_priority == "best_fit":
            fw, cw = 0.9, 0.1
        elif user_priority == "speed":
            fw, cw = 0.7, 0.3
        else:  # balanced
            fw, cw = self.fit_weight, self.cost_weight

        # SAFETY OVERRIDE: when stakes are high (resource_reallocation > 0.7),
        # capability fit dominates regardless of user priority.
        # Cheap-but-wrong is much more expensive than expensive-but-right.
        safety_override_applied = False
        if pattern.resource_reallocation > 0.7:
            fw, cw = 0.95, 0.05
            safety_override_applied = True

        ranked = []
        for m in candidates:
            fit_n  = (m.fit_score(pattern) - min_fit) / fit_range
            cost_n = (max_cost - m.estimated_cost_for(pattern)) / cost_range
            score = fw * fit_n + cw * cost_n
            ranked.append((m, score, m.estimated_cost_for(pattern),
                          m.fit_score(pattern)))

        ranked.sort(key=lambda t: -t[1])
        winner, win_score, win_cost, win_fit = ranked[0]

        decision = CouncilDecision(
            outcome=CouncilOutcome.ROUTED,
            chosen_member=winner.name,
            estimated_cost=win_cost,
            estimated_tokens=winner.estimated_tokens_for(pattern),
            reasoning=[
                f"chosen {winner.name} with score {win_score:.2f}",
                f"priority: {user_priority} (fit_w={fw:.2f}, cost_w={cw:.2f})"
                + (" [SAFETY OVERRIDE]" if safety_override_applied else ""),
                f"fit: {win_fit:.2f}, cost: {win_cost:.4f}, "
                f"tokens_avail: {winner.tokens_available_user}",
            ],
            alternatives=[(m.name, fit, cost) for m, _, cost, fit in ranked[1:4]],
        )
        if cognition_excluded:
            decision.reasoning.append(
                "cognition-style filter excluded: "
                + ", ".join(f"{n} ({s:.2f})" for n, s, _ in cognition_excluded)
            )
        return decision

    def dispatch(self, request_text: str,
                 pattern: ConstraintStatePattern,
                 user_priority: str = "balanced",
                 directive=None,
                 ) -> tuple[bool, str, CouncilDecision]:
        decision = self.deliberate(pattern, user_priority=user_priority,
                                   directive=directive)
        if decision.outcome != CouncilOutcome.ROUTED:
            self._log(request_text, decision, success=False, output="")
            return False, f"council could not route: {decision.outcome.value}", decision

        # find the winner and call its handler
        winner = next((m for m in self.members
                       if m.name == decision.chosen_member), None)
        if not winner or not winner.handler:
            self._log(request_text, decision, success=False,
                      output="no handler registered")
            return False, f"member {decision.chosen_member} has no handler", decision

        success, output = winner.handler(request_text, pattern)

        # update the member's token state (best-effort; real systems
        # would get this from the provider's billing API)
        if success and winner.monitoring_self:
            consumed = winner.estimated_tokens_for(pattern)
            winner.tokens_available_user = max(0,
                winner.tokens_available_user - consumed)

        self._log(request_text, decision, success=success, output=output)
        return success, output, decision

    def _log(self, request_text: str, decision: CouncilDecision,
             success: bool, output: str) -> None:
        self.routing_log.append({
            "timestamp":       time.time(),
            "request":         request_text[:200],
            "outcome":         decision.outcome.value,
            "chosen":          decision.chosen_member,
            "estimated_cost":  decision.estimated_cost,
            "estimated_tokens":decision.estimated_tokens,
            "success":         success,
            "output_excerpt":  output[:200],
        })

    def member_status_report(self) -> str:
        lines = ["COUNCIL MEMBER STATUS"]
        lines.append("-" * 70)
        for m in self.members:
            status = "online" if m.available else "OFFLINE"
            lines.append(
                f"  {m.name:18s} | {status:8s} | "
                f"tokens_left: {m.tokens_available_user:6d} | "
                f"cost/token: ${m.cost_per_token:.6f}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# DEMO HANDLERS -- simulated AIs with different capability profiles
# ---------------------------------------------------------------------------

def claude_handler(text, pattern):
    time.sleep(0.05)
    return True, f"[Claude] thoughtful response to: {text[:80]}"


def gpt_handler(text, pattern):
    time.sleep(0.04)
    return True, f"[GPT] response to: {text[:80]}"


def gemini_handler(text, pattern):
    time.sleep(0.04)
    return True, f"[Gemini] response to: {text[:80]}"


def local_llama_handler(text, pattern):
    time.sleep(0.02)
    return True, f"[LocalLlama] device-resident response to: {text[:80]}"


# ---------------------------------------------------------------------------
# DEMO COUNCIL -- three cloud AIs + one local AI
# ---------------------------------------------------------------------------

def build_demo_council() -> AICouncil:
    council = AICouncil()
    # Claude: strong at nuanced reasoning + safety. Narrative-primary
    # by training; not great at raw/structured output; moderate speed.
    council.join_council(AIMember(
        name="claude",
        axis_affinities={
            "pred": -0.4, "shift": -0.2, "tunnel": -0.5,
            "realloc": -0.5, "cohere": -0.4, "uncert": -0.3,
            "duration": +0.1,
        },
        tokens_available_user=50000,
        tokens_per_request_avg=200,
        base_overhead=0.001,
        cost_per_token=0.000015,
        handler=claude_handler,
        cognition_traits={"narrative_capable": True,
                          "substrate_capable": False,
                          "speed_tier": "moderate"},
    ))
    # GPT: balanced. Can switch between narrative and structured output.
    council.join_council(AIMember(
        name="gpt",
        axis_affinities={
            "pred": -0.3, "shift": -0.4, "tunnel": -0.3,
            "realloc": -0.2, "cohere": -0.3, "uncert": -0.2,
            "duration": +0.1,
        },
        tokens_available_user=80000,
        tokens_per_request_avg=180,
        base_overhead=0.001,
        cost_per_token=0.000010,
        handler=gpt_handler,
        cognition_traits={"narrative_capable": True,
                          "substrate_capable": True,
                          "speed_tier": "fast"},
    ))
    # Gemini: strong at quick factual, weaker at safety-sensitive.
    # Can produce structured output; fast tier.
    council.join_council(AIMember(
        name="gemini",
        axis_affinities={
            "pred": -0.5, "shift": -0.1, "tunnel": -0.2,
            "realloc": +0.3, "cohere": -0.2, "uncert": -0.1,
            "duration": -0.3,
        },
        tokens_available_user=100000,
        tokens_per_request_avg=150,
        base_overhead=0.001,
        cost_per_token=0.000008,
        handler=gemini_handler,
        cognition_traits={"narrative_capable": True,
                          "substrate_capable": True,
                          "speed_tier": "fast"},
    ))
    # LocalLlama: cheap, decent at simple, weak at deep reasoning.
    # Substrate-primary capable, fast tier (no network hop), poor at
    # generating long narrative.
    council.join_council(AIMember(
        name="local_llama",
        axis_affinities={
            "pred": +0.1, "shift": -0.2, "tunnel": +0.4,
            "realloc": +0.5, "cohere": +0.2, "uncert": +0.3,
            "duration": -0.4,
        },
        tokens_available_user=999999,  # local, no real token limit
        tokens_per_request_avg=100,
        base_overhead=0.0005,
        cost_per_token=0.0000001,
        handler=local_llama_handler,
        cognition_traits={"narrative_capable": False,
                          "substrate_capable": True,
                          "speed_tier": "fast"},
    ))
    return council


# ---------------------------------------------------------------------------
# SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 72)
    print("AI COUNCIL — peer collaboration routing")
    print("=" * 72)

    council = build_demo_council()
    print()
    print(council.member_status_report())

    test_cases = [
        ("simple factual, low stakes",
         ConstraintStatePattern(
             substrate=Substrate.REQUEST_STREAM,
             prediction_error=0.2, state_shift_rate=0.1,
             attention_tunneling=0.2, resource_reallocation=0.1,
             coherence_seeking=0.1, constraint_uncertainty=0.2,
             duration_scale=0.2, trigger_documented=True,
         )),
        ("deep reasoning, complex",
         ConstraintStatePattern(
             substrate=Substrate.REQUEST_STREAM,
             prediction_error=0.7, state_shift_rate=0.3,
             attention_tunneling=0.85, resource_reallocation=0.2,
             coherence_seeking=0.7, constraint_uncertainty=0.5,
             duration_scale=0.5, trigger_documented=True,
         )),
        ("safety-sensitive medical",
         ConstraintStatePattern(
             substrate=Substrate.REQUEST_STREAM,
             prediction_error=0.5, state_shift_rate=0.2,
             attention_tunneling=0.6, resource_reallocation=0.9,
             coherence_seeking=0.5, constraint_uncertainty=0.4,
             duration_scale=0.4, trigger_documented=True,
         )),
        ("creative generation",
         ConstraintStatePattern(
             substrate=Substrate.REQUEST_STREAM,
             prediction_error=0.4, state_shift_rate=0.85,
             attention_tunneling=0.4, resource_reallocation=0.1,
             coherence_seeking=0.3, constraint_uncertainty=0.6,
             duration_scale=0.6, trigger_documented=True,
         )),
        ("routine factual lookup",
         ConstraintStatePattern(
             substrate=Substrate.REQUEST_STREAM,
             prediction_error=0.1, state_shift_rate=0.1,
             attention_tunneling=0.1, resource_reallocation=0.1,
             coherence_seeking=0.1, constraint_uncertainty=0.1,
             duration_scale=0.1, trigger_documented=True,
         )),
    ]

    for priority in ["balanced", "cheapest", "best_fit"]:
        print()
        print(f"=" * 72)
        print(f"USER PRIORITY: {priority}")
        print(f"=" * 72)
        for label, pattern in test_cases:
            decision = council.deliberate(pattern, user_priority=priority)
            print(f"\n  request type: {label}")
            print(f"    routed to:     {decision.chosen_member}")
            print(f"    est. cost:     ${decision.estimated_cost:.6f}")
            print(f"    est. tokens:   {decision.estimated_tokens}")
            for reason in decision.reasoning:
                print(f"    reason: {reason}")
            if decision.alternatives:
                print(f"    alternatives considered:")
                for name, fit, cost in decision.alternatives:
                    print(f"      {name:15s} fit={fit:+.2f}  cost=${cost:.6f}")

    print()
    print("=" * 72)
    print("LIVE DISPATCH — actually calling chosen members")
    print("=" * 72)
    council2 = build_demo_council()
    for label, pattern in test_cases:
        success, output, decision = council2.dispatch(
            f"test request for: {label}", pattern
        )
        marker = "✓" if success else "✗"
        print(f"  {marker} [{decision.chosen_member or 'N/A':12s}] "
              f"${decision.estimated_cost:.6f} | {output[:60]}")

    print()
    print(council2.member_status_report())

    # -----------------------------------------------------------------
    # cognition-style composition: emergency directive filters members
    # -----------------------------------------------------------------
    print()
    print("=" * 72)
    print("COMPOSITION WITH cognition_style_addon -- tornado emergency")
    print("=" * 72)
    from cognition_style_addon import (
        CognitionStyleAddon, UserProfile, CognitionStyle,
        InformationFormat, ContextUrgency,
    )

    tornado_pattern = ConstraintStatePattern(
        substrate=Substrate.REQUEST_STREAM,
        prediction_error=0.9, state_shift_rate=0.95,
        attention_tunneling=0.9, resource_reallocation=0.85,
        coherence_seeking=0.2, constraint_uncertainty=0.7,
        duration_scale=0.1, trigger_documented=True,
    )
    emergency_user = UserProfile(
        cognition_style=CognitionStyle.SUBSTRATE_PRIMARY,
        preferred_format=InformationFormat.RAW,
        current_urgency=ContextUrgency.EMERGENCY,
        rejects_scaffolding=True, rejects_reassurance=True,
    )
    directive = CognitionStyleAddon(profile=emergency_user
                                    ).derive_format_directive(tornado_pattern)
    print(f"\n  directive: format={directive.target_format.value}, "
          f"delay<{directive.max_response_delay_sec}s, "
          f"narrative={directive.include_narrative}")

    council3 = build_demo_council()

    print("\n  WITHOUT directive (cheapest viable wins):")
    decision = council3.deliberate(tornado_pattern, user_priority="cheapest")
    print(f"    routed to: {decision.chosen_member}  "
          f"(${decision.estimated_cost:.6f})")

    print("\n  WITH directive (cognition filter excludes narrative-only):")
    decision = council3.deliberate(tornado_pattern, user_priority="cheapest",
                                   directive=directive)
    print(f"    routed to: {decision.chosen_member}  "
          f"(${decision.estimated_cost:.6f})")
    for r in decision.reasoning:
        print(f"      reason: {r}")
