"""
substrate_waste_audit.py

Captures the OVERHEAD signatures of each dispatch cycle and turns waste
into learning signal.

Default optimization thinking:
    measure solver speed -> pick fastest

What this adds:
    also measure parse_time, subprocess_overhead, memory_peak,
    transcription_confidence, api_jitter. fold those into landscape updates.

The dispatcher learns not just "which solver is fastest" but
"which solver is most efficient given the COST OF GETTING TO IT
for this problem class."

License: CC0
"""

from __future__ import annotations

import json
import os
import resource
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable


# ===================================================================
# WASTE SIGNATURE -- what we extract from each cycle
# ===================================================================

@dataclass
class WasteSignature:
    """Overhead profile of a single dispatch cycle.

    All fields default-zero so partial captures still work (e.g. no
    voice input means transcription_confidence stays None).
    """
    problem_name:           str
    problem_shape:          tuple[str, ...]        # sorted shape tags
    solver_lang:            str

    # timing breakdown (seconds)
    parse_time:             float = 0.0    # dispatcher classify + rank
    subprocess_overhead:    float = 0.0    # fork+exec if applicable
    compute_time:           float = 0.0    # actual solver work
    api_jitter:             float = 0.0    # network/queue lag (env signal)

    # memory
    memory_peak_kb:         int = 0        # rss peak from getrusage

    # input quality (voice path)
    transcription_confidence: float | None = None   # 0.0-1.0, None if text input

    # success
    succeeded:              bool = True
    error_class:            str = ""       # e.g. "compile_fail", "timeout"

    @property
    def total_time(self) -> float:
        return (self.parse_time + self.subprocess_overhead
                + self.compute_time + self.api_jitter)

    @property
    def overhead_fraction(self) -> float:
        """What share of total time was NON-compute (i.e. waste)?"""
        t = self.total_time
        if t <= 0:
            return 0.0
        return (self.parse_time + self.subprocess_overhead
                + self.api_jitter) / t

    def to_dict(self) -> dict:
        return asdict(self)


# ===================================================================
# CAPTURE -- wrap a dispatch cycle, measure overhead
# ===================================================================

@dataclass
class CycleTimers:
    """Manual timers populated by the dispatcher integration layer.
    Each phase is bracketed by t = time.perf_counter() probes."""
    t_dispatch_start:   float = 0.0
    t_dispatch_done:    float = 0.0    # parse + rank complete
    t_solver_start:     float = 0.0    # solver invoked
    t_solver_done:      float = 0.0    # solver returned
    t_cycle_done:       float = 0.0    # post-processing complete


def capture_waste(problem_name: str,
                  problem_shape: tuple[str, ...],
                  solver_lang: str,
                  timers: CycleTimers,
                  succeeded: bool = True,
                  error_class: str = "",
                  is_subprocess_solver: bool = False,
                  transcription_confidence: float | None = None,
                  api_jitter: float = 0.0,
                  ) -> WasteSignature:
    """Compute WasteSignature from raw timers."""
    parse_time = max(0.0, timers.t_dispatch_done - timers.t_dispatch_start)
    full_solver = max(0.0, timers.t_solver_done - timers.t_solver_start)

    # split solver time into subprocess overhead vs actual compute.
    # for subprocess-based langs (c, rust, cobol, fortran, go, bash, julia, node, perl, awk)
    # the FIRST ~5-15ms is fork+exec startup. heuristic: if total_solver is short,
    # most of it IS overhead. If it's long, overhead amortized.
    if is_subprocess_solver:
        # rough estimate: 8ms typical subprocess startup on linux
        subprocess_overhead = min(0.008, full_solver * 0.5)
        compute_time = max(0.0, full_solver - subprocess_overhead)
    else:
        subprocess_overhead = 0.0
        compute_time = full_solver

    # memory peak in KB (linux: kilobytes; macos: bytes -- we report linux units)
    try:
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        memory_peak_kb = int(rusage.ru_maxrss)
    except Exception:
        memory_peak_kb = 0

    return WasteSignature(
        problem_name=problem_name,
        problem_shape=tuple(sorted(problem_shape)),
        solver_lang=solver_lang,
        parse_time=parse_time,
        subprocess_overhead=subprocess_overhead,
        compute_time=compute_time,
        api_jitter=api_jitter,
        memory_peak_kb=memory_peak_kb,
        transcription_confidence=transcription_confidence,
        succeeded=succeeded,
        error_class=error_class,
    )


# ===================================================================
# ANALYZER -- detect patterns across many cycles
# ===================================================================

@dataclass
class OverheadProfile:
    """Aggregated waste profile for a (problem_shape, solver) pair."""
    problem_shape:          tuple[str, ...]
    solver_lang:            str
    n_samples:              int = 0

    # medians (robust to outliers)
    median_parse:           float = 0.0
    median_subprocess:      float = 0.0
    median_compute:         float = 0.0
    median_total:           float = 0.0
    median_overhead_frac:   float = 0.0

    # variance signal
    compute_jitter:         float = 0.0    # stdev of compute_time
    success_rate:           float = 1.0

    def dominant_cost(self) -> str:
        """Which cost component is largest? Tells you what's worth optimizing."""
        costs = {
            "parse":      self.median_parse,
            "subprocess": self.median_subprocess,
            "compute":    self.median_compute,
        }
        return max(costs.items(), key=lambda kv: kv[1])[0]

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_waste(signatures: list[WasteSignature]
                  ) -> dict[tuple[tuple[str, ...], str], OverheadProfile]:
    """Group signatures by (shape, solver), compute profile per group."""
    groups: dict[tuple[tuple[str, ...], str], list[WasteSignature]] = defaultdict(list)
    for s in signatures:
        groups[(s.problem_shape, s.solver_lang)].append(s)

    profiles: dict[tuple[tuple[str, ...], str], OverheadProfile] = {}
    for (shape, lang), sigs in groups.items():
        succ = [s for s in sigs if s.succeeded]
        n = len(succ)
        if n == 0:
            profiles[(shape, lang)] = OverheadProfile(
                problem_shape=shape, solver_lang=lang,
                n_samples=len(sigs), success_rate=0.0)
            continue

        parses     = [s.parse_time for s in succ]
        subprocs   = [s.subprocess_overhead for s in succ]
        computes   = [s.compute_time for s in succ]
        totals     = [s.total_time for s in succ]
        overheads  = [s.overhead_fraction for s in succ]

        profiles[(shape, lang)] = OverheadProfile(
            problem_shape=shape,
            solver_lang=lang,
            n_samples=n,
            median_parse=statistics.median(parses),
            median_subprocess=statistics.median(subprocs),
            median_compute=statistics.median(computes),
            median_total=statistics.median(totals),
            median_overhead_frac=statistics.median(overheads),
            compute_jitter=(statistics.stdev(computes) if n > 1 else 0.0),
            success_rate=n / len(sigs),
        )
    return profiles


# ===================================================================
# DERIVED SIGNALS -- turn profiles into landscape-update vectors
# ===================================================================

@dataclass
class OverheadAxes:
    """Per-solver penalties along NEW landscape axes.

    These get added to v2 LANDSCAPE weights to penalize solvers
    whose overhead dominates for a given problem class.
    """
    solver_lang:             str
    memory_locality_penalty: float = 0.0   # high if memory_peak large for shape
    parse_tax:               float = 0.0    # high if parse_time large fraction
    subprocess_tax:          float = 0.0    # high if fork dominates compute
    transcribe_robustness:   float = 0.0    # high if low confidence still solved


def derive_overhead_axes(profile: OverheadProfile,
                         signatures: list[WasteSignature],
                         ) -> OverheadAxes:
    """From profile + raw signatures, compute penalty axes for the landscape."""
    axes = OverheadAxes(solver_lang=profile.solver_lang)

    # subprocess_tax: if subprocess_overhead >= compute_time, the solver
    # spends as much time forking as solving. heavy penalty.
    if profile.median_compute > 0:
        ratio = profile.median_subprocess / profile.median_compute
        axes.subprocess_tax = min(1.0, ratio)
    elif profile.median_subprocess > 0:
        axes.subprocess_tax = 1.0   # all overhead, no compute

    # parse_tax: if parse_time > 10% of total, dispatcher is doing too much
    if profile.median_total > 0:
        parse_frac = profile.median_parse / profile.median_total
        axes.parse_tax = max(0.0, parse_frac - 0.10)

    # transcribe_robustness: among signatures with low transcription
    # confidence (<0.7), what fraction still succeeded? high = robust solver.
    # NOTE: if no voice-confidence data exists at all, return None to signal
    # "no observation" rather than 0.0 (which would falsely look like total failure).
    low_conf = [s for s in signatures
                if s.transcription_confidence is not None
                and s.transcription_confidence < 0.7]
    if low_conf:
        succ_rate = sum(1 for s in low_conf if s.succeeded) / len(low_conf)
        axes.transcribe_robustness = succ_rate
    else:
        # sentinel: -1.0 means "no voice data, do not update transcribe axis"
        axes.transcribe_robustness = -1.0

    return axes


# ===================================================================
# PERSISTENCE
# ===================================================================

def save_signatures(signatures: list[WasteSignature], path: Path) -> None:
    path.write_text(json.dumps([s.to_dict() for s in signatures], indent=2))


def load_signatures(path: Path) -> list[WasteSignature]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    out = []
    for d in data:
        d["problem_shape"] = tuple(d["problem_shape"])
        out.append(WasteSignature(**d))
    return out


# ===================================================================
# SELF-TEST
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("substrate_waste_audit -- synthetic test")
    print("=" * 60)

    # synthesize signatures: c solver has subprocess tax, python doesn't
    sigs = []
    for _ in range(10):
        # python on small problem: no subprocess, tiny compute
        sigs.append(WasteSignature(
            problem_name="factor_small", problem_shape=("bignum",),
            solver_lang="python",
            parse_time=0.0001, subprocess_overhead=0.0,
            compute_time=0.003, memory_peak_kb=12000,
        ))
        # c on same problem: subprocess fork dominates
        sigs.append(WasteSignature(
            problem_name="factor_small", problem_shape=("bignum",),
            solver_lang="c",
            parse_time=0.0001, subprocess_overhead=0.008,
            compute_time=0.001, memory_peak_kb=15000,
        ))

    profiles = analyze_waste(sigs)
    for key, prof in profiles.items():
        print(f"\n{key[1]} on shape {key[0]}:")
        print(f"  n_samples         = {prof.n_samples}")
        print(f"  median_compute    = {prof.median_compute*1000:.3f} ms")
        print(f"  median_subprocess = {prof.median_subprocess*1000:.3f} ms")
        print(f"  median_total      = {prof.median_total*1000:.3f} ms")
        print(f"  overhead_fraction = {prof.median_overhead_frac:.2%}")
        print(f"  dominant_cost     = {prof.dominant_cost()}")

        axes = derive_overhead_axes(prof, sigs)
        print(f"  subprocess_tax    = {axes.subprocess_tax:.2f}")
        print(f"  parse_tax         = {axes.parse_tax:.2f}")

    print("\n-> c has subprocess_tax >> python because fork cost dominates compute.")
    print("-> landscape should penalize c for problems with this overhead signature.")
