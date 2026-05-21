"""
dispatcher.py  (fabrication/voice/)

Maps gated commands to fabrication.* public APIs only -- voice
can't bypass any verifier or claim writer.

For verbs that REQUIRE non-spoken inputs (file paths, physical
parameters), the dispatcher refuses and points the user at the
mini app's interactive menu. Verbs that work safely from voice
(ledger queries, sweep with defaults) execute live.

License: CC0. Stdlib only.
"""


def dispatch(gated):
    if not gated.get("accepted"):
        return {"ok": False, "error": "rejected by gate",
                "gate_result": gated}

    verb      = gated["verb"]
    substrate = gated.get("substrate")
    coupler   = gated.get("coupler")

    try:
        if verb in ("list", "show", "summary"):
            return _dispatch_ledger(verb, substrate, coupler)
        if verb == "predict":
            return _dispatch_predict(substrate, gated["tokens"])
        if verb == "emit":
            return _dispatch_emit(substrate, gated["tokens"])
        if verb in ("verify", "measure", "compare"):
            return _dispatch_verify(substrate, coupler,
                                    gated["tokens"])
        if verb == "sweep":
            return _dispatch_sweep(gated["tokens"])
        if verb == "baseline":
            return _dispatch_baseline(gated["tokens"])
        return {"ok": False,
                "error": f"verb '{verb}' not routed yet"}
    except Exception as e:
        return {"ok": False,
                "error": f"{type(e).__name__}: {e}",
                "command_used": f"{verb} {substrate or coupler}"}


def _dispatch_ledger(verb, substrate, coupler):
    from .. import ledger
    if verb == "summary":
        return {"ok": True, "result": ledger.summary(),
                "command_used": "ledger.summary"}
    if verb == "list":
        prefix = None
        if substrate:
            prefix = f"fab::{substrate}::"
        if coupler:
            prefix = f"fab::coupler::{coupler}::"
        return {"ok": True,
                "result": ledger.list_claims(prefix),
                "command_used": f"ledger.list_claims({prefix})"}
    if verb == "show":
        return {"ok": False,
                "error": "show requires explicit id; "
                         "use the mini app for this"}
    return {"ok": False, "error": f"ledger verb {verb} unrouted"}


def _dispatch_predict(substrate, tokens):
    return {"ok": False,
            "error": ("predict requires parameters; use "
                      "fabrication.mini PREDICT menu -- voice "
                      "can't safely set physical dimensions")}


def _dispatch_emit(substrate, tokens):
    return {"ok": False,
            "error": ("emit requires an existing IR + geometry "
                      "hash; voice route not yet wired "
                      "(planned: load-by-hash)")}


def _dispatch_verify(substrate, coupler, tokens):
    return {"ok": False,
            "error": ("verify requires file paths to CSV/WAV "
                      "inputs; use mini app VERIFY menu -- not "
                      "yet wired for voice")}


def _dispatch_sweep(tokens):
    from ..verify.sweep import make_sweep_file
    meta = make_sweep_file()
    return {"ok": True, "result": meta,
            "command_used": "verify.sweep.make_sweep_file()"}


def _dispatch_baseline(tokens):
    from ..verify.baseline import list_baselines
    return {"ok": True, "result": list_baselines(),
            "command_used": "verify.baseline.list_baselines"}
