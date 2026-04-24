"""
demo_step1.py — Step 1 Octahedral Integration Demo
====================================================
Runs the full Silicon/modules pipeline, then wraps the trajectory in an
OctahedralBundle to demonstrate live fiber substitution.

Produces two plots:
  step1_barycentric_weights.png  — 8-vertex barycentric weight stack over time
  step1_dominant_vertex.png      — dominant vertex index + distance to it

Usage
-----
    python3 demo_step1.py [--steps N] [--seed S] [--noise F]
"""

import argparse
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_SILICON = os.path.dirname(_HERE)
_MODULES = os.path.join(_SILICON, "modules")
sys.path.insert(0, _MODULES)
sys.path.insert(0, _SILICON)

from modules.state import make_state
from modules.pipeline import PipelineConfig, run_pipeline
from integration_staging.octahedral_bundle import (
    build_vertex_atlas, bundle_from_pipeline, OctahedralBundle,
    _VERTEX_SPECS,
)

# Vertex colours — one per vertex, ordered 0–7
VERTEX_COLORS = [
    "#4C9BE8",  # 000 +x  spherical
    "#56C596",  # 001 -x  elongated +x
    "#E85C4C",  # 010 +y  elongated +y
    "#B07FE8",  # 011 -y  elongated +z
    "#F0A500",  # 100 +z  compressed
    "#E87C4C",  # 101 -z  biaxial xy
    "#4CE8C5",  # 110 diag-a
    "#A0A0A0",  # 111 diag-b
]
VERTEX_LABELS = [f"{bits} {label}" for bits, label, *_ in _VERTEX_SPECS]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int,   default=300)
    p.add_argument("--seed",  type=int,   default=42)
    p.add_argument("--noise", type=float, default=0.05)
    return p.parse_args()


def plot_barycentric_weights(bundle: OctahedralBundle, save_path: str):
    """Stacked area chart of all 8 vertex weights over time."""
    weights = bundle.history_weights()   # (T, 8)
    times   = bundle.history_times()

    fig, ax = plt.subplots(figsize=(13, 5))
    fig.suptitle(
        "Step 1: Barycentric Vertex Weights — Live Fiber in Octahedral Bundle",
        fontsize=13, fontweight="bold"
    )

    bottom = np.zeros(len(times))
    for i in range(8):
        w = weights[:, i]
        ax.fill_between(times, bottom, bottom + w,
                        label=VERTEX_LABELS[i],
                        color=VERTEX_COLORS[i], alpha=0.82)
        bottom += w

    ax.set_ylim(0, 1)
    ax.set_xlabel("Time", fontsize=10)
    ax.set_ylabel("Barycentric Weight", fontsize=10)
    ax.legend(loc="upper right", fontsize=7.5, framealpha=0.85,
              ncol=2, title="Vertex (bits | label)")
    ax.grid(True, alpha=0.2)

    # Annotate initial and final dominant vertex
    init_dom = bundle.history[0]["position"]["dominant_bits"]
    final_dom = bundle.history[-1]["position"]["dominant_bits"]
    ax.text(times[0],  1.02, f"start: {init_dom}",  fontsize=8, color="#333333")
    ax.text(times[-1], 1.02, f"end: {final_dom}",   fontsize=8, color="#333333",
            ha="right")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_dominant_vertex(bundle: OctahedralBundle, save_path: str):
    """Two-panel: dominant vertex index over time + distance to dominant vertex."""
    weights = bundle.history_weights()   # (T, 8)
    times   = bundle.history_times()
    dom_idx = np.argmax(weights, axis=1)
    dom_dist = np.array([
        h["position"]["distances"][np.argmax(h["position"]["weights"])]
        for h in bundle.history
    ])
    dom_weight = np.max(weights, axis=1)

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                             gridspec_kw={"height_ratios": [2, 1.5]})
    fig.suptitle(
        "Step 1: Dominant Vertex Trajectory — Octahedral Bundle",
        fontsize=13, fontweight="bold"
    )

    # Panel 1: dominant vertex index (scatter coloured by vertex)
    ax = axes[0]
    for i in range(8):
        mask = dom_idx == i
        if mask.any():
            ax.scatter(times[mask], np.full(mask.sum(), i),
                       color=VERTEX_COLORS[i], s=8, alpha=0.7,
                       label=VERTEX_LABELS[i])
    ax.set_yticks(range(8))
    ax.set_yticklabels(VERTEX_LABELS, fontsize=7)
    ax.set_ylabel("Dominant Vertex", fontsize=9)
    ax.legend(loc="upper right", fontsize=6.5, framealpha=0.8, ncol=2)
    ax.grid(True, alpha=0.2)

    # Panel 2: distance to dominant vertex + dominant weight
    ax2 = axes[1]
    ax2.plot(times, dom_dist,   color="#2A6EBB", linewidth=1.3, label="Distance to dominant")
    ax2r = ax2.twinx()
    ax2r.plot(times, dom_weight, color="#56C596", linewidth=1.0, linestyle="--",
              label="Dominant weight")
    ax2r.set_ylabel("Dominant weight", fontsize=8, color="#56C596")
    ax2r.tick_params(labelsize=7)
    ax2.set_ylabel("Dist. in norm S-space", fontsize=9)
    ax2.set_xlabel("Time", fontsize=10)
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2r.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    ax2.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def main():
    args = parse_args()

    print("=" * 60)
    print("  Step 1: Octahedral Live Fiber Demo")
    print("=" * 60)

    # ── Run the standard pipeline ─────────────────────────────────────────────
    cfg = PipelineConfig(
        steps              = args.steps,
        dt                 = 0.01,
        integrator         = "stochastic",
        noise_scale        = args.noise,
        N_spatial          = 64,
        pde_coupling       = True,
        record_every       = 1,
        kernel_trace_every = 0,   # not needed for this demo
        seed               = args.seed,
    )
    S0 = make_state(n=1e17, mu=1400.0, T=300.0,
                    d_bulk=0.05, d_iface=0.05,
                    l=3.0, k1=1.0, k2=0.5, k3=0.3)

    print(f"\nInitial state: {S0}")
    print(f"Config: {cfg.steps} steps, stochastic, noise={cfg.noise_scale}")
    print("\nRunning pipeline...")
    result = run_pipeline(S0=S0, config=cfg)
    print(f"Completed {len(result.times)} steps. Final regime: {result.regimes[-1].label}")

    # ── Wrap in OctahedralBundle ──────────────────────────────────────────────
    print("\nBuilding octahedral vertex atlas...")
    bundle, weights = bundle_from_pipeline(result)

    print(f"\nOctahedral Bundle Summary")
    print(f"  Vertices         : {len(bundle.vertices)}")
    print(f"  Trajectory steps : {len(bundle.history)}")
    print(f"  Initial position : {bundle.history[0]['position']['dominant_bits']} "
          f"({bundle.vertices[np.argmax(bundle.history[0]['position']['weights'])].label})")
    print(f"  Final position   : {bundle.position.dominant_bits} "
          f"({bundle.dominant_vertex().label})")
    print(f"\n  Final barycentric weights:")
    for i, (v, w) in enumerate(zip(bundle.vertices, bundle.position.weights)):
        bar = "█" * int(w * 30)
        print(f"    {v.bits} {v.label:<18} {w:.4f}  {bar}")

    # ── Plots ─────────────────────────────────────────────────────────────────
    print("\nGenerating plots...")
    plot_barycentric_weights(bundle, os.path.join(_HERE, "step1_barycentric_weights.png"))
    plot_dominant_vertex(    bundle, os.path.join(_HERE, "step1_dominant_vertex.png"))

    print("\nDone.")
    return bundle


if __name__ == "__main__":
    main()
