# horizon_sweep.py — CC0
# Sweeps forecast horizon and emits divergence vs. horizon as plot data + CSV.
# Headline result: narrative false-confidence COMPOUNDS with prediction distance.
# That curve is why LLM-in-robot fails at 5s but looks fine at 0.5s.
# Depends only on stdlib + contrast_harness.py in the same dir.

from __future__ import annotations
import csv
from contrast_harness import Interval, Coupling, State, divergence

def sweep(seed_factory, world, track, max_h):
    """Run divergence at every horizon 1..max_h. Return (horizon, FCI, alarm_step)."""
    out = []
    for h in range(1, max_h+1):
        rows, total, plog = divergence(seed_factory(), world, h, track)
        first_alarm = plog[0][0] if plog else None
        out.append((h, total, first_alarm))
    return out

def ascii_plot(series, width=46, label="FCI"):
    """Terminal-readable curve — survives a phone screen, no libs."""
    ys = [y for _, y in series]
    hi = max(ys) or 1.0
    print(f"\n{label} vs horizon   (▇ scaled to max={hi:.2f})")
    for h, y in series:
        bar = "▇" * int(round(width * y / hi))
        print(f"  {h:2d}s |{bar} {y:.2f}")

if __name__ == "__main__":
    world = [
        Coupling("water_level","road_risk",   0.8, noise=0.4),
        Coupling("temp",       "beaver_repro", 1.5, valid_lo=-40, valid_hi=10, noise=0.3),
        Coupling("beaver_repro","water_level", 0.6, noise=0.5),
    ]
    def fresh_seed():
        return State({
            "temp":         Interval(15, 25),
            "water_level":  Interval(2, 4),
            "road_risk":    Interval(2, 3),
            "beaver_repro": Interval(1, 2),
        })

    MAX_H = 10
    data = sweep(fresh_seed, world, track="road_risk", max_h=MAX_H)

    # ── table ──
    print("  horizon   false-confidence-index   first regime alarm")
    for h, fci, alarm in data:
        a = "—" if alarm is None else f"{alarm}s"
        print(f"    {h:2d}s         {fci:8.2f}              {a}")

    # ── compounding check: is the curve super-linear? ──
    fcis = [f for _,f,_ in data]
    per_step = [fcis[i]-fcis[i-1] for i in range(1, len(fcis))]
    growing = all(per_step[i] >= per_step[i-1]-1e-9 for i in range(1, len(per_step)))
    print(f"\n  marginal drift per added second: "
          + " ".join(f"{d:.2f}" for d in per_step))
    print(f"  drift is {'COMPOUNDING (super-linear)' if growing else 'sub-linear / flattening'}")

    ascii_plot([(h,f) for h,f,_ in data], label="False-Confidence Index")

    # ── CSV for real plotting elsewhere ──
    with open("horizon_sweep.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["horizon_s","false_confidence_index","first_regime_alarm_s"])
        for h, fci, alarm in data:
            w.writerow([h, f"{fci:.4f}", alarm if alarm is not None else ""])
    print("\nwrote horizon_sweep.csv")
