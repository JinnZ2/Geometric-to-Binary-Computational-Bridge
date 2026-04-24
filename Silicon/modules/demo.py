"""
demo.py — Silicon Computational Bridge: Modular Pipeline Demo
=============================================================
Runs the full closed-loop pipeline and produces four diagnostic plots:

  1. Silicon State Trajectory  — all 9 state coordinates over time
  2. Regime Weights            — continuous regime probability over time
  3. Field Evolution           — ψ(x,t) and y(x,t) as heatmaps
  4. Phase Portrait            — Λ vs Ω² with attractor labels

Usage
-----
    python3 demo.py [--steps N] [--stochastic] [--deterministic] [--seed S]

Output
------
    silicon_state_trajectory.png
    regime_weights.png
    field_evolution.png
    phase_portrait.png
"""

import argparse
import sys
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

# ── Add parent directory to path so modules can be imported directly ──────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.state import make_state
from modules.pipeline import PipelineConfig, run_pipeline
from modules.regime import ALL_REGIMES

REGIME_COLORS = {
    "A_linear_quantum":    "#4C9BE8",
    "B_solitonic":         "#56C596",
    "C_chaotic_turbulent": "#E85C4C",
    "D_topological":       "#B07FE8",
    "E_signature_transition": "#F0A500",
}
REGIME_LABELS = {
    "A_linear_quantum":    "A: Linear/QM",
    "B_solitonic":         "B: Solitonic",
    "C_chaotic_turbulent": "C: Chaotic",
    "D_topological":       "D: Topological",
    "E_signature_transition": "E: Transition",
}

STATE_LABELS = [
    "n (cm⁻³)", "μ (cm²/Vs)", "T (K)",
    "d_bulk", "d_iface", "ℓ (nm)",
    "κ₁", "κ₂", "κ₃"
]

PLOT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--steps",       type=int,   default=300)
    p.add_argument("--deterministic", action="store_true")
    p.add_argument("--seed",        type=int,   default=42)
    p.add_argument("--noise",       type=float, default=0.05)
    return p.parse_args()


def plot_state_trajectory(result, save_path):
    states = result.state_array()   # (T, 9)
    times  = np.array(result.times)
    T, D   = states.shape

    fig, axes = plt.subplots(3, 3, figsize=(14, 9), sharex=True)
    fig.suptitle("Silicon State Trajectory", fontsize=14, fontweight="bold")

    for i, ax in enumerate(axes.flat):
        ax.plot(times, states[:, i], color="#2A6EBB", linewidth=1.2)
        ax.set_ylabel(STATE_LABELS[i], fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)

    for ax in axes[-1]:
        ax.set_xlabel("Time", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_regime_weights(result, save_path):
    times  = np.array(result.times)
    regimes = result.regimes

    weight_series = {r: [] for r in ALL_REGIMES}
    for atlas in regimes:
        for r in ALL_REGIMES:
            weight_series[r].append(atlas.weights.get(r, 0.0))

    fig, ax = plt.subplots(figsize=(13, 4))
    fig.suptitle("Continuous Regime Weights Over Time", fontsize=13, fontweight="bold")

    bottom = np.zeros(len(times))
    for r in ALL_REGIMES:
        w = np.array(weight_series[r])
        ax.fill_between(times, bottom, bottom + w,
                        label=REGIME_LABELS[r],
                        color=REGIME_COLORS[r], alpha=0.85)
        bottom += w

    ax.set_ylim(0, 1)
    ax.set_xlabel("Time", fontsize=10)
    ax.set_ylabel("Regime Weight", fontsize=10)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.8)
    ax.grid(True, alpha=0.2)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_field_evolution(result, save_path):
    psi_arr = np.array(result.psi_fields)   # (T, N)
    y_arr   = np.array(result.y_fields)     # (T, N)
    times   = np.array(result.times)
    x       = result.x

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Field Evolution: ψ(x,t) and y(x,t)", fontsize=13, fontweight="bold")

    for ax, data, title, cmap in zip(
        axes,
        [psi_arr, y_arr],
        ["Geometry Field ψ(x, t)", "Computation Output y(x, t)"],
        ["RdBu_r", "PiYG"],
    ):
        vmax = np.percentile(np.abs(data), 98)
        im = ax.imshow(
            data.T,
            aspect="auto",
            origin="lower",
            extent=[times[0], times[-1], x[0], x[-1]],
            cmap=cmap,
            vmin=-vmax, vmax=vmax,
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Time", fontsize=9)
        ax.set_ylabel("x", fontsize=9)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_phase_portrait(result, save_path):
    lam_series    = result.lambda_series()
    omega2_series = result.omega2_mean_series()
    times         = np.array(result.times)
    labels        = result.regime_labels()

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle("Phase Portrait: Λ vs ⟨Ω²⟩", fontsize=13, fontweight="bold")

    # Colour by time
    norm = Normalize(vmin=times[0], vmax=times[-1])
    cmap = plt.cm.viridis
    sc   = ax.scatter(lam_series, omega2_series, c=times, cmap=cmap,
                      norm=norm, s=12, alpha=0.7, zorder=3)
    plt.colorbar(sc, ax=ax, label="Time")

    # Mark Ω² = 0 boundary
    ax.axhline(0, color="#E85C4C", linewidth=1.5, linestyle="--",
               label="Ω² = 0 (transition boundary)", zorder=2)

    # Attractor regions
    ax.axvspan(0,   0.5, alpha=0.07, color="#4C9BE8", label="QM attractor (Λ<0.5)")
    ax.axvspan(0.5, 2.0, alpha=0.07, color="#56C596", label="Soliton attractor")
    ax.axvspan(2.0, ax.get_xlim()[1] if ax.get_xlim()[1] > 2 else 5,
               alpha=0.07, color="#E85C4C", label="Lorentzian basin (Λ>2)")

    ax.set_xlabel("Coupling Strength Λ", fontsize=10)
    ax.set_ylabel("Mean Ω²(x)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def main():
    args = parse_args()

    print("=" * 60)
    print("  Silicon Computational Bridge — Modular Pipeline Demo")
    print("=" * 60)

    cfg = PipelineConfig(
        steps       = args.steps,
        dt          = 0.01,
        integrator  = "deterministic" if args.deterministic else "stochastic",
        noise_scale = args.noise,
        N_spatial   = 64,
        x_range     = (-5.0, 5.0),
        pde_coupling= True,
        record_every= 1,
        seed        = args.seed,
    )

    S0 = make_state(n=1e17, mu=1400.0, T=300.0,
                    d_bulk=0.05, d_iface=0.05,
                    l=3.0, k1=1.0, k2=0.5, k3=0.3)

    print(f"\nInitial state: {S0}")
    print(f"Config: {cfg.steps} steps, integrator={cfg.integrator}, noise={cfg.noise_scale}")
    print("\nRunning pipeline...")

    result = run_pipeline(S0=S0, config=cfg)

    print(f"\nCompleted {len(result.times)} recorded steps.")
    print(f"Final state: {result.states[-1]}")
    print(f"Final regime: {result.regimes[-1].label}")

    print("\nGenerating plots...")
    plot_state_trajectory(result, os.path.join(PLOT_DIR, "silicon_state_trajectory.png"))
    plot_regime_weights(  result, os.path.join(PLOT_DIR, "regime_weights.png"))
    plot_field_evolution( result, os.path.join(PLOT_DIR, "field_evolution.png"))
    plot_phase_portrait(  result, os.path.join(PLOT_DIR, "phase_portrait.png"))

    print("\nDone.")
    return result


if __name__ == "__main__":
    main()
