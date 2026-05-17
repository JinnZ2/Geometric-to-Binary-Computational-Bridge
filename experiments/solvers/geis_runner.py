"""solvers/geis_runner.py -- GEIS encode/decode CELL.

╔════════════════════════════════════════════════════════════════╗
║ ECOLOGICAL INTELLIGENCE ARCHITECTURE                           ║
║                                                                ║
║ This file is a specialized CELL in a distributed ecology.      ║
║ It does ONE thing: lossless geometric-token <-> binary via the ║
║ GEIS encoder. In-process (no subprocess overhead).             ║
║                                                                ║
║ Registers under lang='geis' to NOT collide with python_runner. ║
║ Invoke via Problem(..., hint_lang='geis'). Not in the          ║
║ canonical 13-language roster -- opt-in problem family.         ║
║                                                                ║
║ Problem families served:                                       ║
║   geis_encode  payload={"token": str}    -> binary string      ║
║   geis_decode  payload={"binary": str}   -> token string       ║
╚════════════════════════════════════════════════════════════════╝

OPT-IN: import this module explicitly to register the runner.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner_api import Problem, register_runner


def _name_matches(problem_name: str, family: str) -> bool:
    return problem_name == family or problem_name.startswith(family + "_")


# Repo root for GEIS import (one level above experiments/).
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_ENCODER = None   # lazy singleton


def _get_encoder():
    global _ENCODER
    if _ENCODER is None:
        from GEIS.geometric_encoder import GeometricEncoder
        _ENCODER = GeometricEncoder()
    return _ENCODER


@register_runner("geis")
def run_geis(problem: Problem) -> tuple[bool, str, float]:
    name = problem.name

    if _name_matches(name, "geis_encode"):
        if "token" not in problem.payload:
            return False, "geis_encode: missing required payload key 'token'", 0.0
        token = problem.payload["token"]
        if not isinstance(token, str):
            return False, f"geis_encode: payload['token'] must be str, got {type(token).__name__}", 0.0
        try:
            enc = _get_encoder()
            binary = enc.encode_to_binary(token)
        except Exception as e:
            return False, f"geis_encode: {type(e).__name__}: {e}", 0.0
        return True, f"token '{token}' -> binary '{binary}'", 0.0

    if _name_matches(name, "geis_decode"):
        if "binary" not in problem.payload:
            return False, "geis_decode: missing required payload key 'binary'", 0.0
        binary = problem.payload["binary"]
        if not isinstance(binary, str):
            return False, f"geis_decode: payload['binary'] must be str, got {type(binary).__name__}", 0.0
        try:
            enc = _get_encoder()
            token = enc.decode_from_binary(binary)
        except Exception as e:
            return False, f"geis_decode: {type(e).__name__}: {e}", 0.0
        return True, f"binary '{binary}' -> token '{token}'", 0.0

    return False, f"no geis solver for '{name}'", 0.0
