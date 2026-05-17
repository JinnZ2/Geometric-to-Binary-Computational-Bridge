"""
╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ Shared surface between CELLS and the routers that consume them.║
║ Every runner imports Problem + register_runner from here.      ║
║ Every router consumes RUNNERS from here. Neither router sees   ║
║ the other -- they share only this protocol.                    ║
╚════════════════════════════════════════════════════════════════╝

ROLE: PROTOCOL -- the runner-API surface (Problem dataclass, register_runner
decorator, RUNNERS registry, and the canonical LANGUAGES roster).

runner_api.py -- single source of truth for the cell-to-router contract.

Holds the data both dispatchers must agree on (LANGUAGES) and the API
runner cells implement against (Problem + register_runner). Importing
this module does NOT pull in dispatcher logic, so cells stay independent
of routing choices.

Note: a separate `solver_registry.py` lives at the repo root -- that one
is a higher-level project facade (Registry class wrapping all solvers).
This file is unrelated and lives one level deeper.

License: CC0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


# ===================================================================
# CANONICAL LANGUAGE ROSTER -- single source of truth
# ===================================================================
# Both LANG_PROFILE (dispatcher v1) and LANDSCAPE (dispatcher v2) must
# cover exactly this set. assert_complete() at module-load time in each
# dispatcher catches drift before runtime.

LANGUAGES: tuple[str, ...] = (
    "python", "c", "rust", "sql", "bash",
    "cobol", "lisp", "julia", "fortran", "go",
    "perl", "node", "awk",
)


def assert_complete(registry: dict, label: str = "registry") -> None:
    """Verify `registry` has exactly the canonical LANGUAGES as keys.
    Called by each dispatcher right after defining its per-language
    parameter dict, so any drift surfaces at import time."""
    actual = set(registry.keys())
    expected = set(LANGUAGES)
    missing = expected - actual
    extra   = actual - expected
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing {sorted(missing)}")
        if extra:
            parts.append(f"unexpected {sorted(extra)}")
        raise AssertionError(
            f"{label} drift vs canonical LANGUAGES: " + "; ".join(parts)
        )


# ===================================================================
# PROBLEM CONTRACT -- what a CELL receives
# ===================================================================

@dataclass
class Problem:
    """A unit of work handed from router to cell.

    `tags` are Shape enum members (defined in dispatcher.py); kept loose
    here as `list` so runner_api stays free of dispatcher imports.
    """
    name:        str
    description: str
    tags:        list             # list[Shape] -- kept untyped here to avoid coupling
    payload:     dict             # actual data for the solver
    hint_lang:   str | None = None    # user override


# ===================================================================
# RUNNER REGISTRATION -- how a CELL plugs in
# ===================================================================

RunnerFn = Callable[[Problem], tuple[bool, str, float]]
RUNNERS: dict[str, RunnerFn] = {}


def register_runner(lang: str):
    """Decorator: @register_runner("c") wires a runner fn into RUNNERS."""
    def deco(fn: RunnerFn) -> RunnerFn:
        RUNNERS[lang] = fn
        return fn
    return deco


def registered_languages() -> Iterable[str]:
    """Languages that have actually registered (i.e. their runner module
    was imported and the decorator fired). Distinct from LANGUAGES, which
    is the design-time roster -- a lang can be in LANGUAGES without an
    available runner yet (e.g. rust, cobol)."""
    return RUNNERS.keys()
