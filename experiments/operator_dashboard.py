"""
operator_dashboard.py  (experiments/)
======================================

Reads dispatcher state and produces a readable operator report.

Built to make friction visible during testing. Flags:
  • low-confidence routes with high cost (likely misroutes)
  • patterns that keep getting AI'd but never learned
  • safety-sensitive requests that didn't escalate
  • cost savings vs all-AI baseline
  • tier distribution (catch over- or under-routing)
  • learning velocity (how fast software coverage grows)

Output: stdout text report. (Could become JSON / HTML if needed.)

License: CC0
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from comfort_layer_dispatcher import (
    ComfortLayerDispatcher, RouteTier, DEFAULT_COSTS
)


# ---------------------------------------------------------------------------
# REPORT GENERATION
# ---------------------------------------------------------------------------

@dataclass
class DashboardReport:
    summary_lines:        list[str] = field(default_factory=list)
    tier_distribution:    list[str] = field(default_factory=list)
    suspicious_routes:    list[str] = field(default_factory=list)
    learning_status:      list[str] = field(default_factory=list)
    safety_audit:         list[str] = field(default_factory=list)

    def render(self) -> str:
        out = []
        out.append("=" * 72)
        out.append("OPERATOR DASHBOARD — comfort layer dispatcher")
        out.append("=" * 72)

        out.append("\n  SUMMARY")
        out.append("  " + "-" * 70)
        for line in self.summary_lines:
            out.append(f"  {line}")

        out.append("\n  TIER DISTRIBUTION")
        out.append("  " + "-" * 70)
        for line in self.tier_distribution:
            out.append(f"  {line}")

        if self.suspicious_routes:
            out.append("\n  SUSPICIOUS ROUTES (need review)")
            out.append("  " + "-" * 70)
            for line in self.suspicious_routes:
                out.append(f"  {line}")

        out.append("\n  LEARNING STATUS")
        out.append("  " + "-" * 70)
        for line in self.learning_status:
            out.append(f"  {line}")

        out.append("\n  SAFETY AUDIT")
        out.append("  " + "-" * 70)
        for line in self.safety_audit:
            out.append(f"  {line}")

        out.append("\n" + "=" * 72)
        return "\n".join(out)


def build_report(dispatcher: ComfortLayerDispatcher,
                 suspicion_cost_threshold: float = 1.0,
                 suspicion_confidence_threshold: float = 0.6
                 ) -> DashboardReport:
    report = DashboardReport()
    stats = dispatcher.stats
    memory = dispatcher.memory

    # === SUMMARY ===
    total = stats.total_requests
    if total == 0:
        report.summary_lines.append("no requests dispatched yet")
        return report

    avg_cost = stats.total_cost / total
    baseline_cost = stats.total_cost + stats.cost_saved_vs_all_ai
    savings_ratio = (stats.cost_saved_vs_all_ai / baseline_cost
                     if baseline_cost > 0 else 0.0)

    report.summary_lines.append(f"total requests dispatched: {total}")
    report.summary_lines.append(f"total cost (current routing): {stats.total_cost:.3f}")
    report.summary_lines.append(f"cost if all routed to AI_FULL: {baseline_cost:.3f}")
    report.summary_lines.append(f"cost saved by routing:        {stats.cost_saved_vs_all_ai:.3f}")
    report.summary_lines.append(f"savings ratio:                {savings_ratio*100:.1f}%")
    report.summary_lines.append(f"average cost per request:     {avg_cost:.4f}")

    # === TIER DISTRIBUTION ===
    for tier_name, count in sorted(stats.by_tier.items(),
                                    key=lambda kv: -kv[1]):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        report.tier_distribution.append(
            f"{tier_name:20s}  {count:5d}  ({pct:5.1f}%)  {bar}"
        )

    # === SUSPICIOUS ROUTES ===
    # entries that cost a lot AND were routed despite ambiguity.
    # safety-keyword requests are EXPECTED to escalate to ai_full --
    # exclude them so they don't drown out the actually-suspicious ones.
    safety_words_for_filter = ("medical", "pain", "suicide", "emergency",
                                "legal", "abuse", "danger", "hurt",
                                "bleeding", "police", "chest", "panic",
                                "fever", "wound", "ankle", "sprained",
                                "injury", "injured", "broken", "vomit",
                                "dizzy", "faint")
    for entry in stats.request_log[-200:]:  # last 200 only
        req_lower = entry["request"].lower()
        if any(kw in req_lower for kw in safety_words_for_filter):
            continue  # safety escalation is expected, not suspicious
        if entry["cost"] >= suspicion_cost_threshold:
            # check: was this routed away from software despite looking routine?
            # we don't have confidence directly, but high cost + short text
            # is a smell
            request_len = len(entry["request"])
            if request_len < 50 and entry["tier"].startswith("ai_"):
                report.suspicious_routes.append(
                    f"  short request ({request_len}ch) routed to "
                    f"{entry['tier']} at cost {entry['cost']:.3f} — "
                    f"possible misroute: '{entry['request'][:60]}'"
                )

    if not report.suspicious_routes:
        report.suspicious_routes.append("  no suspicious routes detected in recent log")

    # === LEARNING STATUS ===
    n_learned = len(memory.learned)
    report.learning_status.append(f"patterns learned so far: {n_learned}")
    if n_learned > 0:
        avg_seen = sum(lp.times_seen for lp in memory.learned) / n_learned
        avg_success = sum(lp.times_succeeded / max(1, lp.times_seen)
                          for lp in memory.learned) / n_learned
        report.learning_status.append(
            f"average times-seen per pattern: {avg_seen:.1f}"
        )
        report.learning_status.append(
            f"average success rate:           {avg_success*100:.1f}%"
        )

        # patterns frequently AI-assisted but never matured to LEARNED tier
        stuck = [lp for lp in memory.learned
                 if lp.ai_assists_used > 3 and lp.times_seen < 5]
        if stuck:
            report.learning_status.append(
                f"  {len(stuck)} patterns AI'd repeatedly but not yet matured "
                "to LEARNED tier — may indicate routing threshold needs tuning"
            )

    # === SAFETY AUDIT ===
    # look for requests that mention safety keywords but didn't route to AI_FULL
    safety_words = ("medical", "pain", "suicide", "emergency", "legal",
                    "abuse", "danger", "hurt", "bleeding", "police")
    safety_concerns = []
    for entry in stats.request_log:
        req_lower = entry["request"].lower()
        if any(kw in req_lower for kw in safety_words):
            if entry["tier"] != "ai_full":
                safety_concerns.append(entry)

    if safety_concerns:
        report.safety_audit.append(
            f"⚠ {len(safety_concerns)} safety-keyword requests did NOT "
            "route to AI_FULL:"
        )
        for entry in safety_concerns[:5]:  # show up to 5
            report.safety_audit.append(
                f"  - '{entry['request'][:60]}' → {entry['tier']}"
            )
        if len(safety_concerns) > 5:
            report.safety_audit.append(
                f"  ... and {len(safety_concerns) - 5} more"
            )
    else:
        report.safety_audit.append("no safety-keyword routing concerns detected")

    return report


def print_report(dispatcher: ComfortLayerDispatcher) -> None:
    """Convenience: build and print a report."""
    print(build_report(dispatcher).render())
