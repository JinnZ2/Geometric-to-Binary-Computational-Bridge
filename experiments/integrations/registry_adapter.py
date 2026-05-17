"""
experiments/integrations/registry_adapter.py

OPT-IN: wires the repo-root solver_registry.Registry into the
polyglot_playground.solver_adapter slot, so any Playground pipeline
step can invoke any registered solver in the project (GEIS,
bridges/*, Silicon core/FRET/lattice, NFS) by its registry name --
no new runner files needed.

Usage:

    from polyglot_playground import Playground
    from integrations.registry_adapter import make_registry_adapter

    pg = Playground(solver_adapter=make_registry_adapter())
    # then a Step with operation="encode_magnetic" routes via the
    # adapter to Registry.solve("encode_magnetic", **payload)

The adapter constructs Registry() lazily on first call. If any of
its subsystems fail to import (e.g. missing optional dep), the call
returns (False, "<diagnostic>") instead of crashing the whole
pipeline.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable


def make_registry_adapter() -> Callable[[str, str, dict], tuple[bool, Any]]:
    """Return a solver_adapter callable compatible with Playground.

    Adapter signature: (lang, op_name, payload) -> (ok, output)

    The `lang` argument is accepted but ignored -- the root Registry
    routes by op_name, not by language. Use this adapter when you want
    a Playground step to call a project-wide solver by name.
    """
    _reg = [None]   # boxed so the closure can mutate it
    _err = [None]

    def adapter(lang: str, op_name: str, payload: dict) -> tuple[bool, Any]:
        # Lazy construction: defer Registry init until first use so the
        # cost of importing every project module is paid only if the
        # user actually exercises this adapter.
        if _reg[0] is None and _err[0] is None:
            try:
                repo_root = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..")
                )
                if repo_root not in sys.path:
                    sys.path.insert(0, repo_root)
                from solver_registry import Registry
                _reg[0] = Registry()
            except Exception as e:
                _err[0] = (
                    f"registry_adapter: failed to construct root Registry "
                    f"({type(e).__name__}: {e})"
                )
        if _err[0] is not None:
            return False, _err[0]

        reg = _reg[0]
        if op_name not in reg._solvers:
            return False, (
                f"registry_adapter: '{op_name}' not in root registry "
                f"(have {len(reg._solvers)} solvers)"
            )
        try:
            result = reg.solve(op_name, **payload)
            return True, result
        except TypeError as e:
            return False, (
                f"registry_adapter: payload mismatch for '{op_name}': {e}. "
                f"Required inputs: "
                f"{list(reg._solvers[op_name].inputs.keys())}"
            )
        except Exception as e:
            return False, (
                f"registry_adapter: '{op_name}' raised {type(e).__name__}: {e}"
            )

    return adapter


def list_registered_solvers() -> list[str]:
    """Return the names of all solvers in the root Registry, or [] on failure.
    Useful for discovering what op_names a Playground step can target."""
    try:
        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        if repo_root not in sys.path:
            sys.path.insert(0, repo_root)
        from solver_registry import Registry
        return sorted(Registry()._solvers.keys())
    except Exception:
        return []


# ===================================================================
# SELF-TEST -- pipeline that uses the adapter for a real step
# ===================================================================

def _self_test() -> None:
    print("=" * 64)
    print("registry_adapter self-test")
    print("=" * 64)

    # discover what's available
    names = list_registered_solvers()
    print(f"\nroot Registry exposes {len(names)} solvers")
    if names:
        print(f"sample: {names[:6]} ...")

    # build a playground that uses the adapter for one step
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from polyglot_playground import Playground, Pipeline, Step

    adapter = make_registry_adapter()
    pg = Playground(solver_adapter=adapter)
    pg.register_language("python")

    # Step 1: in-process Python builds a token
    # Step 2: routes through the registry adapter to GEIS encode_token
    def make_token(inputs, state):
        return "001|O"

    pipe = Pipeline(
        name="adapter_demo",
        description="in-process -> registry adapter",
        steps=[
            Step("build_token", {"symbolic"},
                 make_token, [], "token"),
            Step("encode",      {"bitwise"},
                 "encode_token", ["token"], "encoded", lang="python"),
        ],
    )
    run = pg.run(pipe)

    print(f"\npipeline success: {run.success}")
    for sr in run.step_results:
        print(f"  [{sr.lang_used:8s}] {sr.label:14s}  "
              f"{sr.duration_ms:6.2f}ms  ok={sr.success}")
        if sr.error:
            print(f"      error: {sr.error}")
        elif sr.output is not None:
            print(f"      output: {str(sr.output)[:80]}")


if __name__ == "__main__":
    _self_test()
