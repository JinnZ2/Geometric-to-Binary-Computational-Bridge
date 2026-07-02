#!/usr/bin/env python3
# bridge_catalog.py — CC0
# Geometric-to-Binary-Computational-Bridge — real Source objects for
# exploration_engine.py, derived from the actual bridges/ code.
# stdlib only, no cloud dependency.
#
# "Honest, even if it's more work": rather than hand-authoring constraint
# tags for each bridge (arbitrary, unverifiable), this module introspects
# the real BinaryBridgeEncoder subclasses in bridges/ — their physics-helper
# functions, docstrings, and constructor thresholds — and derives constraint
# tags mechanically from literal text matches. Every tag on a Source carries
# a `derivation` triple (tag, origin, matched_keyword) so the claim can be
# checked against the actual source line, the same way Edge A's recover()
# is required to flag rather than assert.
#
# Two derivations are structural rather than per-function:
#   gray_code_stability   — every bridge module's source text contains
#                            "gray" (confirmed by grep across all 11 files;
#                            this is the repo-wide Gray-code convention
#                            documented in CLAUDE.md, not an inference).
#   threshold_bistability — the encoder's __init__ exposes a constructor
#                            parameter literally named *_threshold.
#
# REFUTATION_PROTOCOL: if a keyword match turns out to be a false positive
# (matches text that isn't actually the claimed physics), fix the keyword
# list or the derivation logic here. Never hand-add a tag "because it's
# obviously true" — if it's not in the source text, it doesn't belong.

import importlib
import inspect
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from exploration_engine import Source, SourceClass          # noqa: E402
from bridges.abstract_encoder import BinaryBridgeEncoder    # noqa: E402

BRIDGE_MODULES = [
    "bridges.thermal_encoder",
    "bridges.pressure_encoder",
    "bridges.chemical_encoder",
    "bridges.wave_encoder",
    "bridges.gravity_encoder",
    "bridges.electric_encoder",
    "bridges.sound_encoder",
    "bridges.light_encoder",
    "bridges.magnetic_encoder",
    "bridges.cognitive.consciousness_encoder",
    "bridges.cognitive.emotion_encoder",
]

# concept tag -> literal substrings (lowercased) that earn it, searched
# across "<function name> <docstring>" for every top-level physics helper.
CONCEPT_KEYWORDS = {
    "conserve:energy":       ("energy",),
    "inverse_square":        ("r²", "r^2", "/r²", "/r^2"),
    "exponential_decay":     ("exp(-", "exp(−"),   # − = unicode minus
    "information_theoretic": ("information", "entropy", "divergence"),
    "wave_phase":            ("wave", "wavelength", "interference"),
}


def _bridge_encoder_class(module):
    """The one BinaryBridgeEncoder subclass actually defined in this module
    (as opposed to imported into it)."""
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if (issubclass(obj, BinaryBridgeEncoder) and obj is not BinaryBridgeEncoder
                and obj.__module__ == module.__name__):
            return obj
    return None


def _own_functions(module):
    """Top-level functions defined in this module, excluding names imported
    from elsewhere (e.g. `_gray_bits` imported from bridges.common) and
    private helpers (leading underscore)."""
    return [(name, obj) for name, obj in inspect.getmembers(module, inspect.isfunction)
            if obj.__module__ == module.__name__ and not name.startswith("_")]


def derive_source(module_path: str) -> Source:
    """Introspect one bridge module and return a Source with mechanically
    derived constraints + provenance. Never asserts a tag without a literal
    keyword hit somewhere in the module's own source text."""
    module = importlib.import_module(module_path)
    encoder_cls = _bridge_encoder_class(module)
    encoder = encoder_cls()   # every one of the 11 encoders has all-default args

    constraints = set()
    derivation = []

    for fn_name, fn in _own_functions(module):
        haystack = f"{fn_name} {(fn.__doc__ or '').lower()}"
        for tag, keywords in CONCEPT_KEYWORDS.items():
            hit = next((kw for kw in keywords if kw in haystack), None)
            if hit:
                constraints.add(tag)
                derivation.append((tag, f"{module_path}.{fn_name}()", hit))

    for pname in inspect.signature(encoder_cls.__init__).parameters:
        if pname != "self" and "threshold" in pname:
            constraints.add("threshold_bistability")
            derivation.append(("threshold_bistability",
                                f"{module_path}.__init__(...,{pname}=...)",
                                "threshold"))

    if "gray" in inspect.getsource(module).lower():
        constraints.add("gray_code_stability")
        derivation.append(("gray_code_stability", module_path, "gray"))

    return Source(
        name=f"{encoder.modality} bridge ({module_path.rsplit('.', 1)[-1]})",
        source_class=SourceClass.TRANSMITTING,   # documented code, not craft
        domain=encoder.modality,
        constraints=frozenset(constraints),
        derivation=tuple(derivation),
    )


def derive_all_sources() -> list:
    return [derive_source(m) for m in BRIDGE_MODULES]


if __name__ == "__main__":
    from exploration_engine import Target, edge_b_query, run_pipeline

    sources = derive_all_sources()

    print("Derived sources (constraint tags are mechanical, not hand-authored):")
    for s in sources:
        print(f"\n- {s.name}  [{sorted(s.constraints)}]")
        for tag, origin, kw in s.derivation:
            print(f"    {tag:<22} <- {origin}  (matched {kw!r})")

    target = Target(
        objective="find a gray-code-stable inverse-square sensing law "
                  "shared across bridge domains",
        constraints=frozenset({"inverse_square", "gray_code_stability"}),
        envelope={},
        substrate="cross-domain",
    )

    print(f"\n\nTarget: {target.objective}")
    print(f"constraints: {sorted(target.constraints)}")

    print("\nEdge B cross-class query (constraint overlap, not domain):")
    for s, overlap in edge_b_query(target, sources):
        print(f"  {s.name:<38} overlap={sorted(overlap)}")

    print("\nFull pipeline verdicts:")
    for c in run_pipeline(target, sources):
        status = "TESTABLE" if c.survived else f"REJECTED at {c.rejected_at}"
        print(f"\n- {c.source.name}: {status}")
        print(f"  matched={sorted(c.matched)}  unmet={sorted(c.unmet)}")
        if c.survived:
            print(f"  acoustic signature: {c.acoustic_signature}")
        else:
            print(f"  reason: {c.reject_reason}")
