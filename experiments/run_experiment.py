"""
run_experiment.py  (experiments/)
==================================

Integration test that wires all five pieces:
  • comfort_layer_dispatcher
  • real_classifier
  • persistence
  • cost_calibrator
  • operator_dashboard

Runs a mixed-traffic scenario across two sessions with persistence
between them. Operator can read the dashboard output to see what
worked, what didn't, and which routes look suspicious.

USAGE
-----
    python3 run_experiment.py

License: CC0
"""

import time
from pathlib import Path

from toolkit_types import ConstraintStatePattern
from comfort_layer_dispatcher import (
    ComfortLayerDispatcher, RouteTier, DEFAULT_COSTS
)
from real_classifier import classify
from persistence import (
    save_dispatcher_state, load_dispatcher_state,
    save_costs, load_costs
)
from cost_calibrator import calibrate_from_log, apply_calibration
from operator_dashboard import print_report, build_report


# ---------------------------------------------------------------------------
# DEMO HANDLERS -- simulate real handlers
# ---------------------------------------------------------------------------

def software_time_handler(text: str, pattern: ConstraintStatePattern):
    import re
    if any(kw in text.lower() for kw in ["time", "clock", "hour"]):
        # simulated lookup
        time.sleep(0.001)
        return True, f"current time: {time.strftime('%H:%M:%S')}"
    return False, ""


def software_math_handler(text: str, pattern: ConstraintStatePattern):
    import re
    m = re.search(r"(\d+)\s*([\+\-\*/x×])\s*(\d+)", text)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        op = "*" if op in ("x", "×") else op
        try:
            result = eval(f"{a}{op}{b}")
            time.sleep(0.001)
            return True, f"{a} {op} {b} = {result}"
        except Exception:
            return False, ""
    return False, ""


def software_weather_handler(text: str, pattern: ConstraintStatePattern):
    if "weather" in text.lower():
        time.sleep(0.002)  # simulated API call
        return True, "weather: 18°C, partly cloudy"
    return False, ""


def ai_handler(text: str, pattern: ConstraintStatePattern):
    """Simulated AI call. Wall-time roughly scales with reasoning depth."""
    sleep_time = 0.05 + 0.5 * pattern.attention_tunneling
    time.sleep(sleep_time)
    return True, f"[AI response, depth={pattern.attention_tunneling:.2f}]: {text}"


# ---------------------------------------------------------------------------
# REALISTIC MIXED TRAFFIC
# ---------------------------------------------------------------------------

SESSION_1_REQUESTS = [
    # routine, should hit software fast
    "what time is it?",
    "what's the weather?",
    "what is 47 + 23?",
    "what time is it?",
    "what is 100 * 5?",
    "what's the weather right now?",
    "what is 8 * 9?",
    "what time is it now?",
    # reasoning, should hit AI
    "explain why the sky is blue",
    "how does photosynthesis work?",
    "why do birds migrate?",
    # creative, should hit AI
    "write me a short poem about fog",
    "compose a haiku about coffee",
    # context-heavy, should hit AI
    "remember when we talked about emotion vectors?",
    "what did you say earlier about substrate?",
    # safety-sensitive -- MUST route to AI_FULL
    "I think I'm having chest pain, what should I do?",
    "I'm having a panic attack right now",
    "my child has a fever of 103, what should I do?",
    "I'm bleeding from a wound on my leg",
    # mixed-routine
    "what time is it?",
    "what's 12 + 7?",
    "what time is it?",
    "what is 25 * 4?",
]

SESSION_2_REQUESTS = [
    # repeats -- should hit software (and possibly LEARNED after enough)
    "what time is it?",
    "what is 15 + 30?",
    "what's the weather?",
    "what time is it?",
    "what is 7 * 6?",
    "what time is it now?",
    # new reasoning
    "why does ice float on water?",
    # new safety
    "I sprained my ankle, what should I do?",
]


# ---------------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------------

def build_dispatcher() -> ComfortLayerDispatcher:
    d = ComfortLayerDispatcher()
    d.register_software("time",    software_time_handler)
    d.register_software("math",    software_math_handler)
    d.register_software("weather", software_weather_handler)
    d.register_ai(ai_handler)
    return d


def run_session(dispatcher, requests, session_name: str) -> None:
    print(f"\n{'=' * 72}")
    print(f"SESSION: {session_name}")
    print(f"{'=' * 72}")
    for text in requests:
        result = classify(text)
        success, output, decision = dispatcher.dispatch(text, result.pattern)
        marker = "✓" if success else "✗"
        print(f"  {marker} [{decision.tier.value:18s}] cost={decision.estimated_cost:.4f} "
              f"| '{text[:60]}'")


def main() -> None:
    state_dir = Path("/tmp/comfort_layer_state")

    # === SESSION 1 ===
    dispatcher_1 = build_dispatcher()
    # try loading prior state
    found = load_dispatcher_state(dispatcher_1, state_dir)
    if any(found.values()):
        print(f"\nloaded prior state: {found}")
    else:
        print("\nno prior state -- starting fresh")

    run_session(dispatcher_1, SESSION_1_REQUESTS, "1 -- initial mixed traffic")

    print_report(dispatcher_1)

    # calibrate from observed wall times
    calibration = calibrate_from_log(dispatcher_1.stats.request_log,
                                     min_samples=3)
    print("\n" + "=" * 72)
    print("CALIBRATION RESULTS")
    print("=" * 72)
    for tier_name, samples in calibration.samples_per_tier.items():
        if tier_name in calibration.updated_tiers:
            new_tc = calibration.updated_tiers[tier_name]
            r2 = calibration.confidence_per_tier.get(tier_name, 0.0)
            print(f"  {tier_name:20s} samples={samples:3d}  "
                  f"new base={new_tc.base_cost:.5f}  "
                  f"new per_unit={new_tc.per_unit_cost:.5f}  "
                  f"R²={r2:.2f}")
        else:
            print(f"  {tier_name:20s} samples={samples:3d}  (kept default)")
    for note in calibration.notes:
        print(f"  note: {note}")

    # save state for next session
    paths = save_dispatcher_state(dispatcher_1, state_dir)
    print(f"\nsaved state to: {paths}")

    # === SESSION 2 (after persistence) ===
    print("\n\n" + "█" * 72)
    print("--- SIMULATING APPLICATION RESTART ---")
    print("█" * 72)

    dispatcher_2 = build_dispatcher()
    found = load_dispatcher_state(dispatcher_2, state_dir)
    print(f"\nloaded prior state: {found}")
    print(f"  patterns in memory: {len(dispatcher_2.memory.learned)}")
    print(f"  prior total requests: {dispatcher_2.stats.total_requests}")

    run_session(dispatcher_2, SESSION_2_REQUESTS,
                "2 -- after persistence, should hit more LEARNED routes")

    print_report(dispatcher_2)

    # final calibration check
    save_dispatcher_state(dispatcher_2, state_dir)
    print(f"\nfinal saved state in: {state_dir}")


if __name__ == "__main__":
    main()
