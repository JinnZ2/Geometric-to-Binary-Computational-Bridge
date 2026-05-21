"""
voice_smoke.py  (fabrication/voice/tests/)

Exercises constraint_gate + dispatcher + coating_detector +
optics translator without any audio I/O. Verifies each rule
fires on a representative utterance and that the full loop
returns a renderable result.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.voice.tests.voice_smoke

License: CC0. Stdlib only.
"""
from .. import constraint_gate, dispatcher, coating_detector, optics


def _check(utt, expected_accepted=None, expected_rule=None):
    g = constraint_gate.gate(utt)
    print(f"  '{utt[:60]}'  ->  accepted={g['accepted']}")
    if expected_accepted is not None:
        assert g["accepted"] == expected_accepted, (utt, g)
    if expected_rule and not g["accepted"]:
        assert g["rule"] == expected_rule, (utt, g)
    return g


if __name__ == "__main__":
    print("CONSTRAINT GATE")
    print("-" * 64)
    _check("fix the thermal test",            False, "R1_closure")
    _check("must verify thermal coupler",     False, "R2_morality")
    _check("this is a Helmholtz resonator",   False, "R3_identity")
    _check("list claims",                     False, "R4_no_substrate")
    _check("dance with acoustic mode",        False, "R5_no_verb")
    _check("list acoustic claims",            True)
    _check("predict thermal heater behavior under load", True)
    _check("verify piezo coupler",            True)

    print()
    print("FULL LOOP  ->  DISPATCH + RENDER")
    print("-" * 64)
    for utt in [
        "summary",                       # blocked by R4
        "summary acoustic",              # passes
        "list electrical claims",
        "sweep tools",                   # blocked by R4 (no substrate)
        "verify magnetic claim",
    ]:
        g = constraint_gate.gate(utt)
        d = dispatcher.dispatch(g)
        c = coating_detector.detect()
        r = optics.render(d, coating_report=c, form="short")
        print(f"  '{utt}'")
        for line in r.splitlines():
            print(f"    {line}")
        print()
    print("voice smoke OK")
