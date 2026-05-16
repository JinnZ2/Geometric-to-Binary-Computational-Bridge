"""
landscape_overhead_axes.py

Extends dispatcher_v2_energetic with overhead-cost axes learned from
substrate_waste_audit. The v2 landscape originally tracked problem shape
(bit, num, mem, par, rel, stt, big, io). This adds:

    parse_tax        -- dispatcher parse cost dominates total time
    subprocess_tax   -- fork+exec dominates compute
    memory_tax       -- memory footprint penalty
    transcribe_risk  -- failure rate under low-confidence input

Solvers accumulate empirical penalties on these axes. Future dispatch
chooses solver by minimizing TOTAL energy, including overhead costs.

This is the recursive learning loop:
    solve  ->  capture waste  ->  derive axes  ->  reshape landscape
                                                          |
                                                  next solve uses
                                                  learned overhead profile

License: CC0
"""

from __future__ import annotations

import json
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dataclasses import dataclass, field, asdict
from pathlib import Path
from dispatcher_v2_energetic import (
    ProblemState, PotentialWell, LANDSCAPE, dispatch as base_dispatch,
)
from substrate_waste_audit import (
    WasteSignature, OverheadProfile, OverheadAxes,
    analyze_waste, derive_overhead_axes,
)


# ===================================================================
# EXTENDED PROBLEM STATE -- adds context axes the original v2 lacked
# ===================================================================

@dataclass(frozen=True)
class ExtendedProblemState:
    """ProblemState plus the OPERATIONAL context.
    The original v2 axes describe the problem's mathematical shape.
    These new axes describe its OPERATIONAL conditions:
      - how small is the work? (subprocess overhead amortizes only at scale)
      - how confident was the input? (transcription quality)
      - how stable is the environment? (api_jitter recent history)
    """
    base:                   ProblemState
    expected_work_scale:    float = 0.5    # 0=trivial, 1=massive (subprocess amort.)
    input_confidence:       float = 1.0    # 1=text/clear, 0=garbled voice
    env_jitter_recent:      float = 0.0    # recent api lag normalized

    def overhead_penalties(self) -> dict[str, float]:
        """Compute how strongly each overhead axis should affect dispatch.
        Returns multipliers in [0, 1]: 0 = ignore, 1 = full penalty."""
        return {
            # subprocess_tax matters MORE when work is small
            "subprocess_tax":     1.0 - self.expected_work_scale,
            # parse_tax always relevant but more so on simple problems
            "parse_tax":          0.5 + 0.5 * (1.0 - self.expected_work_scale),
            # memory_tax matters more on large problems
            "memory_tax":         self.expected_work_scale,
            # transcribe_risk matters when input quality is low
            "transcribe_risk":    1.0 - self.input_confidence,
        }


# ===================================================================
# OVERHEAD-EXTENDED WELL -- per-solver learned overhead penalties
# ===================================================================

@dataclass
class OverheadPenalties:
    """Accumulated overhead penalties for one solver. Updated from waste."""
    subprocess_tax:    float = 0.0
    parse_tax:         float = 0.0
    memory_tax:        float = 0.0
    transcribe_risk:   float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class OverheadAwareLandscape:
    """Wraps the base v2 LANDSCAPE and adds learned overhead penalties.

    energy(state, lang) = base_well.energy(state.base)              [shape cost]
                        + sum(penalty_axis * penalty_value          [overhead cost,
                              * state.overhead_penalties()[axis])    weighted by context]
    """

    def __init__(self, base_landscape: dict[str, PotentialWell] = None):
        self.base = base_landscape if base_landscape is not None else LANDSCAPE
        self.overhead: dict[str, OverheadPenalties] = {
            name: OverheadPenalties() for name in self.base
        }

    # --- energy computation -----------------------------------
    def energy(self, state: ExtendedProblemState, lang: str) -> float:
        if lang not in self.base:
            return float("inf")
        shape_e = self.base[lang].energy(state.base)
        pen = self.overhead[lang]
        wts = state.overhead_penalties()
        overhead_e = (
            pen.subprocess_tax  * wts["subprocess_tax"]
            + pen.parse_tax       * wts["parse_tax"]
            + pen.memory_tax      * wts["memory_tax"]
            + pen.transcribe_risk * wts["transcribe_risk"]
        )
        return shape_e + overhead_e

    def dispatch(self, state: ExtendedProblemState) -> tuple[str, list[tuple[str, float]]]:
        energies = [(lang, self.energy(state, lang)) for lang in self.base]
        energies.sort(key=lambda kv: kv[1])
        return energies[0][0], energies

    # --- learning from waste ----------------------------------
    def update_from_waste(self, signatures: list[WasteSignature],
                          learning_rate: float = 0.1) -> dict:
        """Aggregate signatures, derive overhead axes, update penalties.
        Returns a summary dict of changes for inspection."""
        profiles = analyze_waste(signatures)
        changes: dict[str, dict] = {}

        for (shape, lang), profile in profiles.items():
            if lang not in self.overhead:
                continue
            axes_per_lang = derive_overhead_axes(profile, signatures)
            pen = self.overhead[lang]

            # exponential moving average toward observed penalty
            before = OverheadPenalties(**asdict(pen))
            pen.subprocess_tax  = (1-learning_rate)*pen.subprocess_tax  + learning_rate*axes_per_lang.subprocess_tax
            pen.parse_tax       = (1-learning_rate)*pen.parse_tax       + learning_rate*axes_per_lang.parse_tax
            # transcribe: only update if we actually observed voice data
            if axes_per_lang.transcribe_robustness >= 0.0:
                pen.transcribe_risk = (1-learning_rate)*pen.transcribe_risk + learning_rate*(1.0 - axes_per_lang.transcribe_robustness)

            # memory_tax: relative to others on this shape
            # (set later in second pass once we have all profiles)

            changes[lang] = {
                "subprocess_tax":  (before.subprocess_tax,  pen.subprocess_tax),
                "parse_tax":       (before.parse_tax,       pen.parse_tax),
                "transcribe_risk": (before.transcribe_risk, pen.transcribe_risk),
            }

        # second pass: normalize memory_tax across solvers within same shape
        for shape in set(s for s, _ in profiles):
            shape_profiles = {lang: p for (sh, lang), p in profiles.items() if sh == shape}
            if len(shape_profiles) < 2:
                continue
            # this would use raw memory_peak_kb if we tracked it; for now skip
            # leave hook in place for when memory measurement is reliable

        return changes

    # --- persistence ------------------------------------------
    def save(self, path: Path) -> None:
        data = {name: pen.to_dict() for name, pen in self.overhead.items()}
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text())
        for name, d in data.items():
            if name in self.overhead:
                self.overhead[name] = OverheadPenalties(**d)


# ===================================================================
# SELF-TEST
# ===================================================================

if __name__ == "__main__":
    from dispatcher_v2_energetic import ProblemState, shape_tags_to_state

    print("=" * 64)
    print("OverheadAwareLandscape -- full recursive loop test")
    print("=" * 64)

    ls = OverheadAwareLandscape()

    # --- PROBLEM: small bignum/numeric (factoring a small composite) ---
    base = shape_tags_to_state(["bignum", "bitwise", "numeric_tight"])
    state_small = ExtendedProblemState(base=base,
                                       expected_work_scale=0.1,    # SMALL
                                       input_confidence=1.0)
    state_large = ExtendedProblemState(base=base,
                                       expected_work_scale=0.95,   # LARGE
                                       input_confidence=1.0)

    print("\n[BEFORE waste observation]")
    for label, st in [("small work scale", state_small),
                      ("large work scale", state_large)]:
        chosen, energies = ls.dispatch(st)
        print(f"\n  {label}: chosen = {chosen}")
        for lang, e in energies[:5]:
            print(f"    {lang:8s}  E = {e:+.3f}")

    # --- simulate waste: c spends 8ms on fork, only 1ms on compute ---
    print("\n--- feeding waste: 10 cycles of c subprocess tax ---")
    fake_sigs = []
    for _ in range(10):
        fake_sigs.append(WasteSignature(
            problem_name="factor_small",
            problem_shape=("bignum", "bitwise", "numeric_tight"),
            solver_lang="c",
            parse_time=0.0001,
            subprocess_overhead=0.008,
            compute_time=0.001,
        ))
        fake_sigs.append(WasteSignature(
            problem_name="factor_small",
            problem_shape=("bignum", "bitwise", "numeric_tight"),
            solver_lang="python",
            parse_time=0.0001,
            subprocess_overhead=0.0,
            compute_time=0.003,
        ))

    changes = ls.update_from_waste(fake_sigs, learning_rate=0.3)
    print("\noverhead penalty changes:")
    for lang, deltas in changes.items():
        for axis, (before, after) in deltas.items():
            if abs(after - before) > 0.001:
                print(f"  {lang:8s}.{axis:18s}  {before:+.3f}  ->  {after:+.3f}")

    print("\n[AFTER waste observation]")
    for label, st in [("small work scale", state_small),
                      ("large work scale", state_large)]:
        chosen, energies = ls.dispatch(st)
        print(f"\n  {label}: chosen = {chosen}")
        for lang, e in energies[:5]:
            print(f"    {lang:8s}  E = {e:+.3f}")

    print("\n-> on SMALL work scale, c's subprocess_tax now penalizes it.")
    print("-> on LARGE work scale, the same tax is muted (amortized).")
    print("-> landscape learned WORK-SCALE-DEPENDENT routing from waste alone.")
