# SPDX-License-Identifier: CC0-1.0
"""Run the six toys and compare every number with DECLARED.json.
Co-authored.  Stdlib only.

    python experiments/loop_topology/run_all.py

MATCH needs |rebuilt - recorded| <= the declared tolerance.  A MISMATCH
inside half a unit of the recorded number's last digit is marked
ROUNDING_ONLY beside it; that is information, not a pass.  Nothing here
adjusts a toy to a recorded number.
"""
import json
import os

import collision
import cuts
import dwell
import ledger
import nested
import te
import weld

HERE = os.path.dirname(os.path.abspath(__file__))
NOT_RECORDED = {"T5.ring4.nonadjacent.uneven": "PARAMS_NOT_RECORDED"}
DIGITS = {"T3.obs_both_over_sigma": 1}


def last_digit_half(recorded_text):
    if "." not in recorded_text:
        return 0.5
    return 0.5 * 10 ** (-len(recorded_text.split(".")[1]))


def main():
    raw = open(os.path.join(HERE, "DECLARED.json")).read()
    declared = json.loads(raw)
    tol = float(declared["tolerance"]["abs"])
    got = {}
    for mod in (cuts, weld, collision, te, dwell, nested, ledger):
        got.update(mod.numbers())
    counts = {}
    print("%-30s %12s %12s %10s  %s" % ("id", "recorded", "rebuilt", "abs diff", "verdict"))
    for row in declared["numbers"]:
        rid, rec = row["id"], float(row["recorded"])
        text = raw.split('"id": "%s"' % rid)[1].split('"recorded": ')[1].split(",")[0].strip()
        val = got[rid]
        diff = abs(val - rec)
        verdict = "MATCH" if diff <= tol else "MISMATCH"
        if verdict == "MISMATCH" and diff <= last_digit_half(text) + 1e-12:
            verdict += " (ROUNDING_ONLY)"
        if rid in NOT_RECORDED:
            verdict = NOT_RECORDED[rid] + " (" + verdict + ")"
        counts[verdict] = counts.get(verdict, 0) + 1
        print("%-30s %12s %12.6f %10.2e  %s" % (rid, text, val, diff, verdict))
    print()
    print("tolerance %g abs; %d numbers" % (tol, len(declared["numbers"])))
    for k in sorted(counts):
        print("  %-40s %d" % (k, counts[k]))


if __name__ == "__main__":
    main()
