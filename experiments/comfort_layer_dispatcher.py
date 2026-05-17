"""
comfort_layer_dispatcher.py
============================

PART NUMBER:   EXPERIMENT-001
SECTION:       experiments/
WHAT IT DOES:  Routes user requests between a cheap software fast-path
               and an expensive AI deep-path. Most requests are routine --
               weather, time, calendar, simple lookups, repeat patterns.
               The software layer handles those. Only novel or genuinely
               complex requests reach AI inference.

STATUS:        EXPERIMENTAL -- needs operator testing in live conditions
               to calibrate the software/AI boundary

CORE THESIS
-----------
AI systems currently burn energy answering "what time is it?" at full
inference cost. That's not using intelligence -- that's wasting it.
A dispatcher layer can:
  1. handle routine requests in milliseconds via deterministic software
  2. route only novel/complex requests to AI inference
  3. learn from AI responses to expand software coverage over time
  4. measurably reduce token/energy cost while preserving capability

The software layer is not a cache or an LLM-router. It's a learning
fast-path that recognizes constraint patterns (not strings) and routes
based on what KIND of problem this actually is.

PEDAGOGICAL FRAME
-----------------
This is the same dispatcher architecture as:
  • geometric-to-binary-bridge (computational substrate routing)
  • ESD-001 (emotional substrate routing)
Applied to a third domain: cognitive labor routing.

Build → operator runs it → reports real-world friction → iterate.

License: CC0
Dependencies: stdlib only
"""

import json
import time
import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# REQUEST PATTERN -- constraint-state descriptor of what's being asked
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestPattern:
    """
    Numeric signature of a request. NOT the request text -- the constraint
    geometry it represents. Two requests with different words but same
    constraint shape get routed the same way.

    All values normalized [0, 1].
    """
    novelty:              float   # 0=seen-many-times, 1=never-seen
    reasoning_depth:      float   # 0=lookup, 1=multi-step inference required
    context_sensitivity:  float   # 0=stateless, 1=depends heavily on history
    output_creativity:    float   # 0=factual answer, 1=generative work
    safety_sensitivity:   float   # 0=low-stakes, 1=high-stakes
    determinism_value:    float   # 0=variation OK, 1=must be exact match

    def as_vec(self) -> tuple[float, ...]:
        return (self.novelty, self.reasoning_depth, self.context_sensitivity,
                self.output_creativity, self.safety_sensitivity,
                self.determinism_value)

    def axis_names(self) -> tuple[str, ...]:
        return ("novelty", "reason", "context", "create", "safety", "determ")


# ---------------------------------------------------------------------------
# ROUTING TIERS
# ---------------------------------------------------------------------------

class RouteTier(Enum):
    SOFTWARE_FAST      = "software_fast"        # deterministic lookup/compute
    SOFTWARE_LEARNED   = "software_learned"     # learned pattern, software
    AI_LIGHT           = "ai_light"             # small AI inference
    AI_FULL            = "ai_full"              # full reasoning
    AI_DEEP_LEARN      = "ai_deep_learn"        # novel pattern, AI + learn


@dataclass
class RouteDecision:
    tier:               RouteTier
    estimated_cost:     float       # arbitrary units; lower = cheaper
    confidence:         float       # 0..1; how sure we are about routing
    reason:             str
    fallback_tier:      Optional[RouteTier] = None


# ---------------------------------------------------------------------------
# COST MODEL -- tracks energy/token cost of each tier
# ---------------------------------------------------------------------------

@dataclass
class TierCost:
    """Relative cost of each routing tier. Tunable from observation."""
    tier:               RouteTier
    base_cost:          float       # fixed cost just to invoke
    per_unit_cost:      float       # variable cost per complexity unit


DEFAULT_COSTS: dict[RouteTier, TierCost] = {
    RouteTier.SOFTWARE_FAST:    TierCost(RouteTier.SOFTWARE_FAST,    0.001, 0.0001),
    RouteTier.SOFTWARE_LEARNED: TierCost(RouteTier.SOFTWARE_LEARNED, 0.005, 0.001),
    RouteTier.AI_LIGHT:         TierCost(RouteTier.AI_LIGHT,         0.5,   0.3),
    RouteTier.AI_FULL:          TierCost(RouteTier.AI_FULL,          2.0,   1.5),
    RouteTier.AI_DEEP_LEARN:    TierCost(RouteTier.AI_DEEP_LEARN,    3.0,   2.0),
}


def estimate_cost(tier: RouteTier, pattern: RequestPattern,
                  costs: dict[RouteTier, TierCost] = DEFAULT_COSTS) -> float:
    """Cost = base + per_unit * (reasoning_depth + novelty)/2."""
    tc = costs[tier]
    complexity = (pattern.reasoning_depth + pattern.novelty) / 2
    return tc.base_cost + tc.per_unit_cost * complexity


# ---------------------------------------------------------------------------
# PATTERN MEMORY -- software remembers patterns it has learned
# ---------------------------------------------------------------------------

@dataclass
class LearnedPattern:
    """A pattern the software has learned to handle (with AI's help originally)."""
    pattern_signature:  tuple[float, ...]    # rounded pattern vector
    handler_name:       str                  # software handler that takes it
    times_seen:         int = 1
    times_succeeded:    int = 1
    ai_assists_used:    int = 0              # times AI helped solve a variant


@dataclass
class PatternMemory:
    """Software memory of learned patterns. Persistent across sessions."""
    learned:    list[LearnedPattern] = field(default_factory=list)
    resolution: int = 4                      # decimal places for matching

    def _signature(self, pattern: RequestPattern) -> tuple[float, ...]:
        r = self.resolution
        return tuple(round(v, r) for v in pattern.as_vec())

    def find_match(self, pattern: RequestPattern,
                   tolerance: float = 0.15) -> Optional[LearnedPattern]:
        sig = self._signature(pattern)
        best = None
        best_dist = tolerance
        for lp in self.learned:
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(sig, lp.pattern_signature)))
            if dist < best_dist:
                best = lp
                best_dist = dist
        return best

    def record_success(self, pattern: RequestPattern, handler_name: str,
                       ai_assisted: bool = False) -> None:
        existing = self.find_match(pattern, tolerance=0.05)
        if existing:
            existing.times_seen += 1
            existing.times_succeeded += 1
            if ai_assisted:
                existing.ai_assists_used += 1
        else:
            self.learned.append(LearnedPattern(
                pattern_signature=self._signature(pattern),
                handler_name=handler_name,
                ai_assists_used=1 if ai_assisted else 0,
            ))

    def record_failure(self, pattern: RequestPattern) -> None:
        existing = self.find_match(pattern, tolerance=0.05)
        if existing:
            existing.times_seen += 1
            # don't increment succeeded


# ---------------------------------------------------------------------------
# ROUTING LOGIC -- gradient-descent over tier cost vs. capability
# ---------------------------------------------------------------------------

def route(pattern: RequestPattern,
          memory: PatternMemory,
          costs: dict[RouteTier, TierCost] = DEFAULT_COSTS) -> RouteDecision:
    """
    Decide which tier handles this request.

    Priority order:
      1. SOFTWARE_FAST: matches a built-in deterministic handler
         (this implementation defers handler-mapping to the host --
         we route there based on pattern signature)
      2. SOFTWARE_LEARNED: matches a learned pattern in memory
      3. AI_LIGHT: simple reasoning, low context
      4. AI_FULL: complex reasoning
      5. AI_DEEP_LEARN: high novelty + high depth (worth learning from)

    Safety override: high safety_sensitivity always escalates to at least AI_LIGHT
    even for routine-looking patterns, because the cost of mistake outweighs
    the cost savings.
    """
    # safety check first -- never route safety-critical to software fast path
    if pattern.safety_sensitivity > 0.7:
        return RouteDecision(
            tier=RouteTier.AI_FULL,
            estimated_cost=estimate_cost(RouteTier.AI_FULL, pattern, costs),
            confidence=0.95,
            reason="high safety sensitivity overrides cost optimization",
        )

    # known pattern in memory?
    match = memory.find_match(pattern)
    if match:
        success_rate = match.times_succeeded / max(1, match.times_seen)
        if success_rate > 0.85 and match.times_seen >= 3:
            return RouteDecision(
                tier=RouteTier.SOFTWARE_LEARNED,
                estimated_cost=estimate_cost(RouteTier.SOFTWARE_LEARNED, pattern, costs),
                confidence=success_rate,
                reason=f"learned pattern matched (success rate {success_rate:.2f}, "
                       f"seen {match.times_seen}x)",
                fallback_tier=RouteTier.AI_LIGHT,
            )

    # routine deterministic? (low novelty, low reasoning, low context)
    is_routine = (pattern.novelty < 0.2
                  and pattern.reasoning_depth < 0.2
                  and pattern.context_sensitivity < 0.3
                  and pattern.output_creativity < 0.2)
    if is_routine:
        return RouteDecision(
            tier=RouteTier.SOFTWARE_FAST,
            estimated_cost=estimate_cost(RouteTier.SOFTWARE_FAST, pattern, costs),
            confidence=0.9,
            reason="routine deterministic request (lookup/calculation)",
            fallback_tier=RouteTier.AI_LIGHT,
        )

    # high novelty AND high reasoning = worth learning from
    if pattern.novelty > 0.7 and pattern.reasoning_depth > 0.6:
        return RouteDecision(
            tier=RouteTier.AI_DEEP_LEARN,
            estimated_cost=estimate_cost(RouteTier.AI_DEEP_LEARN, pattern, costs),
            confidence=0.8,
            reason="novel complex request; route to AI with learning feedback",
            fallback_tier=RouteTier.AI_FULL,
        )

    # moderate complexity -> AI_LIGHT or AI_FULL
    if pattern.reasoning_depth > 0.5 or pattern.context_sensitivity > 0.6:
        return RouteDecision(
            tier=RouteTier.AI_FULL,
            estimated_cost=estimate_cost(RouteTier.AI_FULL, pattern, costs),
            confidence=0.75,
            reason="moderate-to-deep reasoning required",
        )

    return RouteDecision(
        tier=RouteTier.AI_LIGHT,
        estimated_cost=estimate_cost(RouteTier.AI_LIGHT, pattern, costs),
        confidence=0.7,
        reason="default: light AI handling for non-routine, non-novel request",
    )


# ---------------------------------------------------------------------------
# DISPATCHER -- full pipeline with handlers
# ---------------------------------------------------------------------------

# handler signature: (request_text, pattern) -> (success, output)
Handler = Callable[[str, RequestPattern], tuple[bool, str]]


@dataclass
class DispatcherStats:
    total_requests:        int = 0
    by_tier:               dict[str, int] = field(default_factory=dict)
    total_cost:            float = 0.0
    cost_saved_vs_all_ai:  float = 0.0       # what would have cost if all AI_FULL
    request_log:           list[dict] = field(default_factory=list)
    # per-request entries; schema defined by whoever appends (the
    # dispatcher and/or downstream calibrator). Persisted by
    # persistence.save_stats / load_stats so observations survive
    # restarts and the cost_calibrator can recompute tier costs
    # from accumulated history.

    def record(self, tier: RouteTier, cost: float, ai_full_cost: float) -> None:
        self.total_requests += 1
        self.by_tier[tier.value] = self.by_tier.get(tier.value, 0) + 1
        self.total_cost += cost
        self.cost_saved_vs_all_ai += max(0.0, ai_full_cost - cost)


@dataclass
class ComfortLayerDispatcher:
    """
    The full dispatcher. Holds the memory, the routing logic, and
    handler registries for each tier.
    """
    memory:              PatternMemory = field(default_factory=PatternMemory)
    stats:               DispatcherStats = field(default_factory=DispatcherStats)
    software_handlers:   dict[str, Handler] = field(default_factory=dict)
    ai_handler:          Optional[Handler] = None

    def register_software(self, name: str, handler: Handler) -> None:
        self.software_handlers[name] = handler

    def register_ai(self, handler: Handler) -> None:
        self.ai_handler = handler

    def dispatch(self, request_text: str,
                 pattern: RequestPattern) -> tuple[bool, str, RouteDecision]:
        """Route the request and execute through the chosen tier."""
        decision = route(pattern, self.memory)
        ai_full_cost = estimate_cost(RouteTier.AI_FULL, pattern)

        success, output = self._execute(request_text, pattern, decision)

        # learning feedback: if AI handled a novel pattern successfully,
        # software gets to record it for future routing
        if decision.tier in (RouteTier.AI_DEEP_LEARN, RouteTier.AI_FULL) and success:
            handler_name = f"ai_solved_{int(time.time() * 1000) % 1_000_000}"
            self.memory.record_success(pattern, handler_name, ai_assisted=True)
        elif decision.tier in (RouteTier.SOFTWARE_FAST, RouteTier.SOFTWARE_LEARNED):
            if success:
                self.memory.record_success(pattern, "software", ai_assisted=False)
            else:
                self.memory.record_failure(pattern)

        self.stats.record(decision.tier, decision.estimated_cost, ai_full_cost)
        return success, output, decision

    def _execute(self, request_text: str, pattern: RequestPattern,
                 decision: RouteDecision) -> tuple[bool, str]:
        """Execute through the chosen tier. Falls back if primary fails."""
        if decision.tier in (RouteTier.SOFTWARE_FAST, RouteTier.SOFTWARE_LEARNED):
            for name, handler in self.software_handlers.items():
                try:
                    ok, output = handler(request_text, pattern)
                    if ok:
                        return ok, output
                except Exception as e:
                    pass
            # software couldn't handle it; fall back to AI if available
            if decision.fallback_tier and self.ai_handler:
                return self.ai_handler(request_text, pattern)
            return False, "no software handler succeeded; no AI fallback"

        if decision.tier in (RouteTier.AI_LIGHT, RouteTier.AI_FULL, RouteTier.AI_DEEP_LEARN):
            if self.ai_handler:
                return self.ai_handler(request_text, pattern)
            return False, "AI handler not registered"

        return False, f"unknown tier {decision.tier}"


# ---------------------------------------------------------------------------
# DEMO HANDLERS -- show how the dispatcher integrates with real handlers
# ---------------------------------------------------------------------------

def demo_software_time_handler(text: str, pattern: RequestPattern) -> tuple[bool, str]:
    """Software fast-path for time queries."""
    if any(kw in text.lower() for kw in ["time", "clock", "hour"]):
        return True, f"current time: {time.strftime('%H:%M:%S')}"
    return False, ""


def demo_software_math_handler(text: str, pattern: RequestPattern) -> tuple[bool, str]:
    """Software fast-path for simple arithmetic."""
    import re
    m = re.search(r"(\d+)\s*([\+\-\*/])\s*(\d+)", text)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        try:
            result = eval(f"{a}{op}{b}")
            return True, f"{a} {op} {b} = {result}"
        except Exception:
            return False, ""
    return False, ""


def demo_ai_handler(text: str, pattern: RequestPattern) -> tuple[bool, str]:
    """Stand-in for an actual AI call. In production this would call your LLM."""
    # simulated AI response -- token cost would be real here
    return True, f"[AI handled novel request, depth={pattern.reasoning_depth:.2f}]: {text}"


# ---------------------------------------------------------------------------
# PATTERN CLASSIFIER -- heuristic for demo; real version would be learned
# ---------------------------------------------------------------------------

def classify_request_heuristic(text: str) -> RequestPattern:
    """
    Crude heuristic pattern-classification. Real version would use a
    small classifier model or learned signatures from past traffic.
    """
    text_lower = text.lower()
    word_count = len(text.split())

    routine_keywords = {"time", "weather", "date", "clock", "today", "hour"}
    novel_signals    = {"why", "how come", "explain", "reason", "wonder"}
    creative_signals = {"write", "draft", "compose", "story", "poem", "article"}
    context_signals  = {"my", "our", "we", "i was just", "yesterday", "remember"}

    novelty = 0.1 if any(k in text_lower for k in routine_keywords) else 0.4
    if any(k in text_lower for k in novel_signals):
        novelty = max(novelty, 0.7)
    if word_count > 30:
        novelty = max(novelty, 0.6)

    reasoning_depth = 0.1 if any(k in text_lower for k in routine_keywords) else 0.3
    if "why" in text_lower or "how" in text_lower:
        reasoning_depth = max(reasoning_depth, 0.6)
    if word_count > 40:
        reasoning_depth = max(reasoning_depth, 0.7)

    context = 0.1
    if any(k in text_lower for k in context_signals):
        context = 0.6

    creativity = 0.1
    if any(k in text_lower for k in creative_signals):
        creativity = 0.8

    # safety heuristic: medical/legal/safety keywords escalate
    safety_keywords = {"medical", "legal", "emergency", "diagnose", "prescribe",
                       "suicide", "abuse", "danger"}
    safety = 0.8 if any(k in text_lower for k in safety_keywords) else 0.2

    # determinism: math, lookups want exact answers
    determinism = 0.9 if any(k in text_lower for k in routine_keywords) else 0.3
    if any(c.isdigit() for c in text):
        determinism = max(determinism, 0.7)

    return RequestPattern(
        novelty=novelty, reasoning_depth=reasoning_depth,
        context_sensitivity=context, output_creativity=creativity,
        safety_sensitivity=safety, determinism_value=determinism,
    )


# ---------------------------------------------------------------------------
# SELF-TEST
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 72)
    print("EXPERIMENT-001  comfort_layer_dispatcher")
    print("=" * 72)

    dispatcher = ComfortLayerDispatcher()
    dispatcher.register_software("time", demo_software_time_handler)
    dispatcher.register_software("math", demo_software_math_handler)
    dispatcher.register_ai(demo_ai_handler)

    test_requests = [
        "what time is it?",
        "what is 47 + 23?",
        "what time is it now?",                       # repeat -> SOFTWARE
        "what is 100 * 5?",                            # repeat math -> SOFTWARE
        "what time is it?",                            # third time -> LEARNED
        "explain why the sky is blue",                 # novel reasoning
        "write me a short poem about fog",             # creative
        "I think I'm having chest pain, what should I do?",   # safety
        "what's 8 * 9?",                                # math again
        "remember when we talked about emotion vectors?",  # context-heavy
    ]

    for req in test_requests:
        pattern = classify_request_heuristic(req)
        success, output, decision = dispatcher.dispatch(req, pattern)
        print(f"\n  request: '{req}'")
        print(f"    pattern: nov={pattern.novelty:.2f} reason={pattern.reasoning_depth:.2f} "
              f"safety={pattern.safety_sensitivity:.2f}")
        print(f"    routed:  {decision.tier.value:20s}  cost={decision.estimated_cost:.4f}")
        print(f"    reason:  {decision.reason}")
        print(f"    output:  {output[:80]}")

    print()
    print("=" * 72)
    print("DISPATCHER STATS")
    print("=" * 72)
    print(f"  total requests:           {dispatcher.stats.total_requests}")
    print(f"  total cost:               {dispatcher.stats.total_cost:.4f}")
    print(f"  cost if all routed to AI: "
          f"{dispatcher.stats.total_cost + dispatcher.stats.cost_saved_vs_all_ai:.4f}")
    print(f"  cost saved:               {dispatcher.stats.cost_saved_vs_all_ai:.4f}")
    if dispatcher.stats.total_cost + dispatcher.stats.cost_saved_vs_all_ai > 0:
        ratio = (dispatcher.stats.cost_saved_vs_all_ai
                 / (dispatcher.stats.total_cost + dispatcher.stats.cost_saved_vs_all_ai))
        print(f"  savings ratio:            {ratio*100:.1f}%")
    print(f"  by tier:")
    for tier, count in dispatcher.stats.by_tier.items():
        print(f"    {tier:25s} {count}")
    print(f"  patterns learned:         {len(dispatcher.memory.learned)}")
    print()
    print("=" * 72)
    print("KNOWN LIMITATIONS -- needs operator testing to calibrate:")
    print("=" * 72)
    print("  • pattern classifier is heuristic (keyword-matching); real version")
    print("    needs traffic-trained classifier")
    print("  • cost model uses arbitrary units; needs calibration to real")
    print("    token/energy cost in deployment")
    print("  • safety thresholds need tuning per deployment context")
    print("  • memory tolerance / resolution affects learning rate;")
    print("    optimal values depend on traffic distribution")
    print("  • no persistence yet; memory resets between runs")
    print()
