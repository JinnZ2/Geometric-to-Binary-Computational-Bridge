# SPDX-License-Identifier: CC0-1.0
"""T5 dwell: dwell-time plus entry/exit estimator on merged rings.
Co-authored.  Stdlib only.

    python experiments/loop_topology/dwell.py
    python experiments/loop_topology/dwell.py --selftest

The estimator reads a merged process as second-order semi-Markov: which
state it entered from, how long it stayed, where it left to.  The
affinity term uses CONDITIONAL exit probabilities.  The known error is to
use joint triple probabilities there, which counts each jump twice; the
selftest requires the two forms to differ on a case where the correct one
is known.

The ring rates are not in the work order.  DECLARED.json fixes them before
the run: uniform rings at 3.0 forward, 0.5 backward; the 'uneven' ring is
a labelled guess.
"""
import sys

import ctmc

FWD, BACK = 3.0, 0.5
UNEVEN_FWD, UNEVEN_BACK = [8.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0]


def fraction(W, merges, conditional=True):
    est = ctmc.semi_markov(W, ctmc.groups_for(len(W), merges), conditional=conditional)
    return est["total"] / ctmc.sigma(W), est


def numbers():
    r4, r3 = ctmc.ring(4, FWD, BACK), ctmc.ring(3, FWD, BACK)
    out = {}
    good, _ = fraction(r4, [{0, 1}])
    bad, _ = fraction(r4, [{0, 1}], conditional=False)
    out["T5.unconditional_ratio"] = bad / good
    out["T5.ring4.adjacent"] = good
    out["T5.ring3.merge"] = fraction(r3, [{1, 2}])[0]
    out["T5.ring4.nonadjacent"] = fraction(r4, [{0, 2}])[0]
    f, est = fraction(ctmc.ring(4, UNEVEN_FWD, UNEVEN_BACK), [{0, 2}])
    out["T5.ring4.nonadjacent.uneven"] = f
    out["_uneven_parts"] = est
    out["T5.two_pairs"] = fraction(r4, [{0, 1}, {2, 3}])[0]
    return out


def selftest():
    """The unconditional form must be caught: on the unmerged 4-ring the
    correct estimator returns sigma exactly, and the wrong one must not."""
    checks = []
    r4 = ctmc.ring(4, FWD, BACK)
    good, _ = fraction(r4, [])
    bad, _ = fraction(r4, [], conditional=False)
    checks.append(("conditional form returns sigma on the unmerged ring", abs(good - 1.0) < 1e-9))
    checks.append(("unconditional form does not", abs(bad - 1.0) > 1e-3))
    good, _ = fraction(r4, [{0, 1}])
    bad, _ = fraction(r4, [{0, 1}], conditional=False)
    checks.append(("unconditional form over-counts on the adjacent merge", bad > good * 1.01))
    balanced = ctmc.ring(4, 2.0, 2.0)
    checks.append(("detailed balance reads zero", abs(ctmc.semi_markov(
        balanced, ctmc.groups_for(4, [{0, 1}]))["total"]) < 1e-9))
    failed = 0
    for name, ok in checks:
        failed += not ok
        print("%s  %s" % ("PASS" if ok else "FAIL", name))
    print("checks: %d   failed: %d" % (len(checks), failed))
    return failed


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        raise SystemExit(1 if selftest() else 0)
    for k, v in numbers().items():
        print("%-30s %s" % (k, v))
