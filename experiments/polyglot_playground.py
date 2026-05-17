"""
polyglot_playground.py

A learning playground for mid-stream language mixing.

╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ The polyglot stack treats each language as a specialized cell. ║
║ The playground lets you COMPOSE those cells in real time --    ║
║ break a problem into steps, route each step to the cell with   ║
║ the deepest energy well for that step, pass state between      ║
║ them, and learn from waste signals which compositions work.    ║
║                                                                ║
║ This is not a single-language solver. It's a pipeline where    ║
║ each stage can be a different language, chosen by problem      ║
║ shape rather than convention.                                  ║
╚════════════════════════════════════════════════════════════════╝

Core concepts:

- Step:     one stage of a pipeline, has its own shape + payload
- Pipeline: ordered list of Steps, with shared state flowing through
- State:    a dict that each step can read from and write to
- Recipe:   a saved pipeline pattern, reusable across problems

Mid-stream mixing example:
    Step 1: Python -- parse input, build search space
    Step 2: C      -- tight bitwise inner loop on the candidates
    Step 3: SQL    -- relational join of results against a constraint set
    Step 4: Python -- format output

Each step picks its own language by shape, not by convention.
State flows through. Waste is captured. Landscape learns.

License: CC0
"""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


# ===================================================================
# STEP -- one stage of a pipeline
# ===================================================================

@dataclass
class Step:
    """One stage in a polyglot pipeline.

    shape:       what kind of computation this step does (e.g. {"bignum"})
                 used by the router to pick a language if lang is None
    lang:        explicit language pick, None = let the router choose
    operation:   a callable, takes (state) returns (new_state, output)
                 OR a string naming a registered solver to invoke
    input_keys:  which keys from shared state this step reads
    output_key:  where in shared state to store this step's result
    label:       human-readable name for the step
    """
    label:        str
    shape:        set[str]
    operation:    Any                        # Callable or string solver name
    input_keys:   list[str] = field(default_factory=list)
    output_key:   str = ""
    lang:         str | None = None          # explicit override


@dataclass
class StepResult:
    label:        str
    lang_used:    str
    success:      bool
    output:       Any
    error:        str = ""
    duration_ms:  float = 0.0
    state_before: dict = field(default_factory=dict)
    state_after:  dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        # state may contain non-JSON-serializable values; coerce
        return {
            "label":        self.label,
            "lang_used":    self.lang_used,
            "success":      self.success,
            "output":       str(self.output)[:500] if self.output else "",
            "error":        self.error,
            "duration_ms":  self.duration_ms,
        }


# ===================================================================
# PIPELINE -- composes steps, threads state through
# ===================================================================

@dataclass
class Pipeline:
    name:         str
    steps:        list[Step]
    description:  str = ""

    def add(self, step: Step) -> "Pipeline":
        """Fluent: pipe.add(Step(...)).add(Step(...))"""
        self.steps.append(step)
        return self


@dataclass
class PipelineRun:
    pipeline_name:    str
    started_at:       str
    finished_at:      str = ""
    success:          bool = False
    total_duration_ms: float = 0.0
    final_state:      dict = field(default_factory=dict)
    step_results:     list[StepResult] = field(default_factory=list)
    error:            str = ""

    def to_dict(self) -> dict:
        return {
            "pipeline_name":     self.pipeline_name,
            "started_at":        self.started_at,
            "finished_at":       self.finished_at,
            "success":           self.success,
            "total_duration_ms": self.total_duration_ms,
            "error":             self.error,
            "step_results":      [s.to_dict() for s in self.step_results],
        }


# ===================================================================
# ROUTER -- pick a language for a step based on shape + landscape
# ===================================================================
# Minimal embedded router so the playground works standalone.
# In the full stack, this delegates to dispatcher_v2_energetic or v1.
# Shape -> preferred languages, roughly ordered by typical fit.

DEFAULT_AFFINITY: dict[str, list[str]] = {
    "bignum":        ["python", "lisp", "julia"],
    "bitwise":       ["c", "rust", "go"],
    "numeric_tight": ["c", "rust", "fortran", "julia"],
    "relational":    ["sql", "lisp", "python"],
    "search":        ["python", "lisp", "rust"],
    "parallel":      ["go", "rust", "bash", "julia"],
    "io_bound":      ["node", "python", "bash", "awk"],
    "symbolic":      ["lisp", "python"],
    "metaprog":      ["lisp", "python"],
}


def route(shape: set[str], available: set[str],
          override: str | None = None) -> str:
    """Pick a language for the given shape from available solvers.

    Strategy: for each shape tag, get the affinity ranking; pick the
    first language that appears as a top choice across the most tags
    AND is available. Falls back to python if everything else fails."""
    if override and override in available:
        return override

    scores: dict[str, float] = {}
    for tag in shape:
        ranking = DEFAULT_AFFINITY.get(tag, [])
        for i, lang in enumerate(ranking):
            if lang in available:
                # higher score = better fit; rank 0 -> 1.0, rank 1 -> 0.5, etc.
                scores[lang] = scores.get(lang, 0) + 1.0 / (i + 1)

    if scores:
        return max(scores.items(), key=lambda kv: kv[1])[0]
    return "python" if "python" in available else next(iter(available))


# ===================================================================
# EXECUTOR -- runs a pipeline, threads state, captures waste
# ===================================================================

class Playground:
    """Compose, execute, and learn from polyglot pipelines.

    Solvers can be registered as Python callables (in-process) OR as
    string-named external solvers handled by an adapter. For the
    playground itself we use in-process callables; the adapter slot
    lets you plug in the real dispatcher/runners from the parent
    polyglot stack."""

    def __init__(self,
                 solver_adapter: Callable[[str, str, dict], tuple[bool, Any]] | None = None):
        """
        solver_adapter: optional callable (lang, op_name, payload) -> (ok, output)
                        used when a Step's operation is a string solver name.
                        If None, only in-process callable operations work.
        """
        self.recipes: dict[str, Pipeline] = {}
        self.runs:    list[PipelineRun]   = []
        self.solver_adapter = solver_adapter
        self.available_langs: set[str] = {"python"}   # python is always in-process

    # --- registration -------------------------------------------

    def register_language(self, lang: str) -> None:
        """Mark a language as available. The adapter must know how to handle it."""
        self.available_langs.add(lang)

    def save_recipe(self, pipeline: Pipeline) -> None:
        self.recipes[pipeline.name] = pipeline

    def load_recipe(self, name: str) -> Pipeline | None:
        return self.recipes.get(name)

    # --- execution ----------------------------------------------

    def run(self, pipeline: Pipeline,
            initial_state: dict | None = None) -> PipelineRun:
        """Execute a pipeline, threading state through each step.
        Captures per-step timing, lang chosen, success/failure."""
        state = dict(initial_state or {})
        run = PipelineRun(
            pipeline_name=pipeline.name,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        t_pipe_start = time.perf_counter()

        for step in pipeline.steps:
            lang = route(step.shape, self.available_langs, override=step.lang)
            state_snapshot = dict(state)
            t_step_start = time.perf_counter()
            success, output, error = False, None, ""

            try:
                # gather inputs the step asked for
                inputs = {k: state.get(k) for k in step.input_keys}

                if callable(step.operation):
                    # in-process operation: pass inputs, get output
                    output = step.operation(inputs, state)
                    success = True
                elif isinstance(step.operation, str):
                    # external solver: route through adapter
                    if self.solver_adapter is None:
                        raise RuntimeError(
                            f"step '{step.label}' uses solver '{step.operation}' "
                            f"but no solver_adapter was registered")
                    payload = {**inputs, **state}
                    success, output = self.solver_adapter(lang, step.operation, payload)
                else:
                    raise TypeError(
                        f"step '{step.label}' operation is "
                        f"{type(step.operation).__name__}, expected callable or str")

                if step.output_key and success:
                    state[step.output_key] = output

            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                success = False

            elapsed_ms = (time.perf_counter() - t_step_start) * 1000
            run.step_results.append(StepResult(
                label=step.label,
                lang_used=lang,
                success=success,
                output=output,
                error=error,
                duration_ms=elapsed_ms,
                state_before=state_snapshot,
                state_after=dict(state),
            ))

            if not success:
                run.error = f"step '{step.label}' failed: {error}"
                break

        run.total_duration_ms = (time.perf_counter() - t_pipe_start) * 1000
        run.finished_at = datetime.now(timezone.utc).isoformat()
        run.success = all(r.success for r in run.step_results)
        run.final_state = state
        self.runs.append(run)
        return run

    # --- learning -----------------------------------------------

    def waste_summary(self) -> dict:
        """Aggregate per-language timing across all runs.
        This is the playground's local waste signal -- feed back into
        landscape_overhead_axes.py for full learning loop integration."""
        by_lang: dict[str, list[float]] = {}
        for run in self.runs:
            for sr in run.step_results:
                by_lang.setdefault(sr.lang_used, []).append(sr.duration_ms)

        summary = {}
        for lang, times in by_lang.items():
            summary[lang] = {
                "n":         len(times),
                "median_ms": sorted(times)[len(times)//2],
                "total_ms":  sum(times),
            }
        return summary

    # --- persistence --------------------------------------------

    def save_runs(self, path: Path) -> None:
        Path(path).write_text(
            json.dumps([r.to_dict() for r in self.runs], indent=2)
        )


# ===================================================================
# SELF-TEST -- mid-stream language mixing in action
# ===================================================================

def _self_test() -> None:
    print("=" * 64)
    print("polyglot_playground self-test")
    print("=" * 64)

    pg = Playground()
    pg.register_language("c")
    pg.register_language("sql")
    pg.register_language("python")

    # Build a 4-step pipeline that mixes languages mid-stream:
    #
    #   Step 1 (python): generate a list of candidate ints
    #   Step 2 (c):      filter to primes (bitwise + numeric_tight)
    #   Step 3 (sql):    group/count by property (relational)
    #   Step 4 (python): format the report

    def step1_generate(inputs, state):
        n = inputs.get("upper_bound", 30)
        return list(range(2, n + 1))

    def step2_filter_primes(inputs, state):
        # in real use, this routes to C runner via adapter.
        # for self-test we do it in python so we can verify the flow.
        candidates = inputs.get("candidates", [])
        primes = []
        for n in candidates:
            is_p = n > 1
            for p in range(2, int(n**0.5) + 1):
                if n % p == 0:
                    is_p = False
                    break
            if is_p:
                primes.append(n)
        return primes

    def step3_group(inputs, state):
        primes = inputs.get("primes", [])
        return {
            "even":   [p for p in primes if p % 2 == 0],
            "odd":    [p for p in primes if p % 2 == 1],
            "twin":   [p for p in primes if (p+2) in primes or (p-2) in primes],
        }

    def step4_report(inputs, state):
        groups = inputs.get("groups", {})
        return (f"found {sum(len(v) for v in groups.values())} primes; "
                f"twins={len(groups.get('twin', []))}, "
                f"odd={len(groups.get('odd', []))}, "
                f"even={len(groups.get('even', []))}")

    pipe = Pipeline(
        name="prime_classification",
        description="generate -> filter -> group -> report, mixing langs by shape",
        steps=[
            Step("generate",     {"search"},
                 step1_generate, ["upper_bound"], "candidates"),
            Step("filter_primes", {"bitwise", "numeric_tight"},
                 step2_filter_primes, ["candidates"], "primes"),
            Step("group",        {"relational"},
                 step3_group, ["primes"], "groups"),
            Step("report",       {"symbolic"},
                 step4_report, ["groups"], "report"),
        ],
    )

    pg.save_recipe(pipe)

    run = pg.run(pipe, initial_state={"upper_bound": 30})

    print(f"\npipeline: {pipe.name}")
    print(f"success:  {run.success}")
    print(f"total:    {run.total_duration_ms:.2f}ms")
    print(f"\nstep-by-step:")
    for sr in run.step_results:
        print(f"  [{sr.lang_used:8s}] {sr.label:18s}  "
              f"{sr.duration_ms:7.3f}ms  "
              f"{'OK' if sr.success else 'FAIL'}")
    print(f"\nfinal report: {run.final_state.get('report')}")

    print(f"\nwaste summary (per-language timing):")
    for lang, stats in pg.waste_summary().items():
        print(f"  {lang:8s}  n={stats['n']}  "
              f"median={stats['median_ms']:.3f}ms  "
              f"total={stats['total_ms']:.3f}ms")

    print(f"\nrouting decisions (mid-stream mixing):")
    print(f"  generate shape={{'search'}}              -> "
          f"{run.step_results[0].lang_used}")
    print(f"  filter   shape={{'bitwise','numeric'}}   -> "
          f"{run.step_results[1].lang_used}")
    print(f"  group    shape={{'relational'}}          -> "
          f"{run.step_results[2].lang_used}")
    print(f"  report   shape={{'symbolic'}}            -> "
          f"{run.step_results[3].lang_used}")

    print("\nKey property: each step picked its own language based on")
    print("shape, state flowed through cleanly, waste was captured per step.")


if __name__ == "__main__":
    _self_test()
