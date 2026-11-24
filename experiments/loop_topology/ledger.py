# SPDX-License-Identifier: CC0-1.0
"""T6 ledger: the heat the bath receives, and the heat a Markov reading of
the merged chain can account for.  Co-authored.  Stdlib only.

    python experiments/loop_topology/ledger.py

Unit temperature, so heat rate = entropy production rate.
"""
import ctmc
import nested


def markov_heat(W, merges):
    return ctmc.sigma(ctmc.merged_markov(W, ctmc.groups_for(len(W), merges)))


def numbers():
    W = nested.graph()
    out = {"T6.heat.bath": ctmc.sigma(W),
           "T6.heat.markov.across": markov_heat(W, nested.CUTS["across"]),
           "T6.heat.markov.hub": markov_heat(W, nested.CUTS["hub"])}
    out["_markov_heat_all_cuts"] = {k: markov_heat(W, m) for k, m in nested.CUTS.items()}
    return out


if __name__ == "__main__":
    for k, v in numbers().items():
        print("%-26s %s" % (k, v))
