# SPDX-License-Identifier: CC0-1.0
"""T2 weld: a cut reads the NET through it; the cost is paid on the TOTAL.
Co-authored.  Stdlib only.

    python experiments/loop_topology/weld.py

Four systems with a loop that returns through the cut, and the same four
with the return branch removed (controls).
"""


def joule(currents, r=2.0):
    return {"cut": sum(currents) ** 2 * r, "true": sum(i * i * r for i in currents)}


def kinetic(velocities, m=1.0):
    net = sum(m * v for v in velocities)
    mass = m * len(velocities)
    return {"cut": 0.5 * net * net / mass, "true": sum(0.5 * m * v * v for v in velocities)}


def futile(flux, affinity, returns=True):
    net = 0.0 if returns else flux
    return {"cut": net * affinity, "true": flux * affinity}


def migration(movers_in, movers_out, cost=1.0):
    return {"cut": abs(movers_in - movers_out) * cost, "true": (movers_in + movers_out) * cost}


def numbers():
    out = {}
    j, k = joule([3.0, -3.0]), kinetic([5.0, -5.0])
    f, m = futile(5.0, 10.0), migration(10, 10)
    out["T2.joule.cut"], out["T2.joule.true"] = j["cut"], j["true"]
    out["T2.kinetic.cut"], out["T2.kinetic.true"] = k["cut"], k["true"]
    out["T2.futile.cut"] = f["cut"]
    out["T2.migration.cut"], out["T2.migration.true"] = m["cut"], m["true"]
    controls = [joule([3.0]), kinetic([5.0]), futile(5.0, 10.0, returns=False), migration(10, 0)]
    ratios = [c["cut"] / c["true"] for c in controls]
    out["T2.controls.ratio"] = sum(ratios) / len(ratios)
    out["_controls_each"] = ratios
    out["_futile_true"] = f["true"]
    return out


if __name__ == "__main__":
    for k, v in numbers().items():
        print("%-22s %s" % (k, v))
