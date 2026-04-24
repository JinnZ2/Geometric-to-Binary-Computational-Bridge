"""
demo.py — Silicon Computational Bridge: Modular Pipeline Demo
=============================================================
Runs the full closed-loop pipeline and produces six diagnostic plots:

  1. Silicon State Trajectory       — all 9 state coordinates over time
  2. Regime Weights                 — continuous regime probability over time
  3. Field Evolution                — ψ(x,t) and y(x,t) as heatmaps
  4. Phase Portrait                 — Λ vs Ω² with attractor labels
  5. Ω² Sign Log                    — mean Ω²(t), min/max envelope, sign
                                      transitions flagged, near-boundary band
  6. Kernel Entanglement Curvature  — off-diagonal/diagonal ratio over time,
                                      spectral gap, eigenvalue sign-change count

Usage
-----
    python3 demo.py [--steps N] [--stochastic] [--deterministic] [--seed S]

Output
------
    silicon_state_trajectory.png
    regime_weights.png
    field_evolution.png
    phase_portrait.png
    omega2_sign_log.png
    kernel_curvature.png
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

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.state import make_state
from modules.pipeline import PipelineConfig, run_pipeline
from modules.regime import ALL_REGIMES, OMEGA2_TRANSITION_TOL

REGIME_COLORS = {
    "A_linear_quantum":        "#4C9BE8",
    "B_solitonic":             "#56C596",
    "C_chaotic_turbulent":     "#E85C4C",
    "D_topological":           "#B07FE8",
    "E_signature_transition":  "#F0A500",
}
REGIME_LABELS = {
    "A_linear_quantum":        "A: Linear/QM",
    "B_solitonic":             "B: Solitonic",
    "C_chaotic_turbulent":     "C: Chaotic",
    "D_topological":           "D: Topological",
    "E_signature_transition":  "E: Transition",
}
STATE_LABELS = [
    "n (cm⁻³)", "μ (cm²/Vs)", "T (K)",
    "d_bulk", "d_iface", "ℓ (nm)",
    "κ₁", "κ₂", "κ₃"
]
PLOT_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--steps",         type=int,   default=300)
    p.add_argument("--deterministic",  action="store_true")
    p.add_argument("--seed",          type=int,   default=42)
    p.add_argument("--noise",         type=float, default=0.05)
    p.add_argument("--kernel-every",  type=int,   default=10,
                   dest="kernel_every",
                   help="Trace kernel curvature every N recorded steps (0=off)")
    return p.parse_args()


# ── Plot 1: State trajectory ──────────────────────────────────────────────────

def plot_state_trajectory(result, save_path):
    states = result.state_array()
    times  = np.array(result.times)
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


# ── Plot 2: Regime weights ────────────────────────────────────────────────────

def plot_regime_weights(result, save_path):
    times  = np.array(result.times)
    weight_series = {r: [] for r in ALL_REGIMES}
    for atlas in result.regimes:
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


# ── Plot 3: Field evolution ───────────────────────────────────────────────────

def plot_field_evolution(result, save_path):
    psi_arr = np.array(result.psi_fields)
    y_arr   = np.array(result.y_fields)
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
            data.T, aspect="auto", origin="lower",
            extent=[times[0], times[-1], x[0], x[-1]],
            cmap=cmap, vmin=-vmax, vmax=vmax,
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Time", fontsize=9)
        ax.set_ylabel("x", fontsize=9)
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


# ── Plot 4: Phase portrait ────────────────────────────────────────────────────

def plot_phase_portrait(result, save_path):
    lam_series    = result.lambda_series()
    omega2_series = result.omega2_mean_series()
    times         = np.array(result.times)
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.suptitle("Phase Portrait: Λ vs ⟨Ω²⟩", fontsize=13, fontweight="bold")
    norm = Normalize(vmin=times[0], vmax=times[-1])
    sc   = ax.scatter(lam_series, omega2_series, c=times, cmap="viridis",
                      norm=norm, s=12, alpha=0.7, zorder=3)
    plt.colorbar(sc, ax=ax, label="Time")
    ax.axhline(0, color="#E85C4C", linewidth=1.5, linestyle="--",
               label="Ω² = 0 (transition boundary)", zorder=2)
    ax.axvspan(0,   0.5, alpha=0.07, color="#4C9BE8", label="QM attractor (Λ<0.5)")
    ax.axvspan(0.5, 2.0, alpha=0.07, color="#56C596", label="Soliton attractor")
    xlim = ax.get_xlim()
    if xlim[1] > 2.0:
        ax.axvspan(2.0, xlim[1], alpha=0.07, color="#E85C4C", label="Lorentzian basin (Λ>2)")
    ax.set_xlabel("Coupling Strength Λ", fontsize=10)
    ax.set_ylabel("Mean Ω²(x)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


# ── Plot 5: Ω² sign log ───────────────────────────────────────────────────────

def plot_omega2_sign_log(result, save_path):
    """
    Three-panel Ω² diagnostic:
      Top    : mean Ω²(t) with min/max shaded envelope and near-boundary band
      Middle : fraction of spatial points with Ω² < 0
      Bottom : boolean transition flag (vertical red lines at sign-change events)
    """
    o2 = result.omega2_log_array()
    times      = o2["time"]
    mean_o2    = o2["mean"]
    min_o2     = o2["min"]
    max_o2     = o2["max"]
    frac_neg   = o2["fraction_negative"]
    transitions= o2["transition"]
    near_bnd   = o2["near_boundary"]

    transition_times = times[transitions]

    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.5, 1]})
    fig.suptitle("Ω² Sign Log — Signature Transition Diagnostics",
                 fontsize=13, fontweight="bold")

    # ── Panel 1: mean Ω² with envelope ───────────────────────────────────────
    ax = axes[0]
    ax.fill_between(times, min_o2, max_o2, alpha=0.15, color="#4C9BE8",
                    label="Ω²(x) spatial range")
    ax.plot(times, mean_o2, color="#2A6EBB", linewidth=1.5, label="Mean Ω²(x)")
    ax.axhline(0, color="#E85C4C", linewidth=1.2, linestyle="--",
               label="Ω² = 0 boundary")
    # Near-boundary band
    ax.axhspan(-OMEGA2_TRANSITION_TOL, OMEGA2_TRANSITION_TOL,
               alpha=0.12, color="#F0A500", label=f"|Ω²| < {OMEGA2_TRANSITION_TOL} (near-boundary)")
    # Mark transitions
    for tt in transition_times:
        ax.axvline(tt, color="#E85C4C", linewidth=1.5, alpha=0.8, linestyle=":")
    if len(transition_times):
        ax.axvline(transition_times[0], color="#E85C4C", linewidth=1.5,
                   linestyle=":", label="Sign transition")
    ax.set_ylabel("Ω²(x)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(True, alpha=0.25)

    # ── Panel 2: fraction negative ────────────────────────────────────────────
    ax2 = axes[1]
    ax2.fill_between(times, 0, frac_neg, alpha=0.6, color="#B07FE8")
    ax2.plot(times, frac_neg, color="#7A4FBB", linewidth=1.2)
    ax2.set_ylim(-0.02, 1.02)
    ax2.set_ylabel("Frac. Ω²(x) < 0", fontsize=9)
    ax2.axhline(0.5, color="#E85C4C", linewidth=0.8, linestyle="--", alpha=0.5)
    for tt in transition_times:
        ax2.axvline(tt, color="#E85C4C", linewidth=1.2, alpha=0.6, linestyle=":")
    ax2.grid(True, alpha=0.25)

    # ── Panel 3: boolean transition flag ─────────────────────────────────────
    ax3 = axes[2]
    ax3.fill_between(times, 0, transitions.astype(float),
                     step="mid", alpha=0.8, color="#E85C4C")
    ax3.set_ylim(-0.1, 1.5)
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(["no", "yes"], fontsize=8)
    ax3.set_ylabel("Transition", fontsize=9)
    ax3.set_xlabel("Time", fontsize=10)
    ax3.grid(True, alpha=0.25)

    n_trans = int(transitions.sum())
    n_near  = int(near_bnd.sum())
    fig.text(0.01, 0.01,
             f"Sign transitions: {n_trans}   Near-boundary steps: {n_near}   "
             f"Final sign: {'Riemannian (+)' if result.omega2_logs[-1].sign_positive else 'Lorentzian (-)'}",
             fontsize=8, color="#444444")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


# ── Plot 6: Kernel entanglement curvature ─────────────────────────────────────

def plot_kernel_curvature(result, save_path):
    """
    Three-panel kernel curvature diagnostic:
      Top    : entanglement ratio (off-diagonal / diagonal) over time
               with regime thresholds annotated
      Middle : spectral gap λ₁ − λ₂ over time
      Bottom : eigenvalue sign-change count over time
    """
    if not result.kernel_traces:
        print("  No kernel traces recorded — skipping kernel curvature plot.")
        return

    kt = result.kernel_trace_array()
    times  = kt["time"]
    ratio  = kt["entanglement_ratio"]
    gap    = kt["spectral_gap"]
    schanges = kt["sign_changes"]
    diag   = kt["diag_mean"]
    offdiag= kt["offdiag_mean"]

    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True,
                             gridspec_kw={"height_ratios": [3, 2, 1.5]})
    fig.suptitle("Kernel Entanglement Curvature — W(x,x') Diagnostics",
                 fontsize=13, fontweight="bold")

    # ── Panel 1: entanglement ratio ───────────────────────────────────────────
    ax = axes[0]
    ax.plot(times, ratio, color="#2A6EBB", linewidth=1.8, label="Entanglement ratio")
    ax.fill_between(times, 0, ratio, alpha=0.15, color="#2A6EBB")

    # Regime threshold bands
    ax.axhspan(0,    0.1,  alpha=0.08, color="#56C596", label="Separable (ratio < 0.1)")
    ax.axhspan(0.1,  0.5,  alpha=0.08, color="#F0A500", label="Weakly coupled (0.1–0.5)")
    ax.axhspan(0.5,  max(ratio.max() * 1.1, 0.6),
               alpha=0.08, color="#E85C4C", label="Entangled (ratio > 0.5)")

    # Annotate diag vs off-diag
    ax2r = ax.twinx()
    ax2r.plot(times, diag,    color="#888888", linewidth=0.9, linestyle="--",
              label="|W_ii| mean")
    ax2r.plot(times, offdiag, color="#B07FE8", linewidth=0.9, linestyle="--",
              label="|W_ij| mean")
    ax2r.set_ylabel("Kernel magnitude", fontsize=8, color="#888888")
    ax2r.tick_params(labelsize=7)

    ax.set_ylabel("Off-diag / Diag ratio", fontsize=10)
    # Combine legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2r.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper right",
              framealpha=0.85)
    ax.grid(True, alpha=0.25)

    # ── Panel 2: spectral gap ─────────────────────────────────────────────────
    ax3 = axes[1]
    ax3.plot(times, gap, color="#56C596", linewidth=1.5)
    ax3.fill_between(times, 0, gap, alpha=0.2, color="#56C596")
    ax3.axhline(0, color="#E85C4C", linewidth=0.8, linestyle="--", alpha=0.6)
    ax3.set_ylabel("Spectral gap λ₁ − λ₂", fontsize=9)
    ax3.grid(True, alpha=0.25)

    # ── Panel 3: eigenvalue sign changes ─────────────────────────────────────
    ax4 = axes[2]
    ax4.step(times, schanges, color="#E85C4C", linewidth=1.3, where="mid")
    ax4.fill_between(times, 0, schanges, step="mid", alpha=0.4, color="#E85C4C")
    ax4.set_ylabel("Eigenvalue\nsign changes", fontsize=9)
    ax4.set_xlabel("Time", fontsize=10)
    ax4.grid(True, alpha=0.25)

    fig.text(0.01, 0.01,
             f"Kernel snapshots: {len(times)}   "
             f"Mean ratio: {ratio.mean():.4f}   "
             f"Final: {'entangled' if ratio[-1] > 0.5 else 'weakly-coupled' if ratio[-1] > 0.1 else 'separable'} "
             f"(ratio={ratio[-1]:.4f})",
             fontsize=8, color="#444444")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    print("=" * 60)
    print("  Silicon Computational Bridge — Modular Pipeline Demo")
    print("=" * 60)

    cfg = PipelineConfig(
        steps              = args.steps,
        dt                 = 0.01,
        integrator         = "deterministic" if args.deterministic else "stochastic",
        noise_scale        = args.noise,
        N_spatial          = 64,
        x_range            = (-5.0, 5.0),
        pde_coupling       = True,
        record_every       = 1,
        kernel_trace_every = args.kernel_every,
        seed               = args.seed,
    )

    S0 = make_state(n=1e17, mu=1400.0, T=300.0,
                    d_bulk=0.05, d_iface=0.05,
                    l=3.0, k1=1.0, k2=0.5, k3=0.3)

    print(f"\nInitial state: {S0}")
    print(f"Config: {cfg.steps} steps, integrator={cfg.integrator}, "
          f"noise={cfg.noise_scale}, kernel_trace_every={cfg.kernel_trace_every}")
    print("\nRunning pipeline...")

    result = run_pipeline(S0=S0, config=cfg)

    print(f"\nCompleted {len(result.times)} recorded steps.")
    print(f"Final state: {result.states[-1]}")
    print(f"Final regime: {result.regimes[-1].label}")
    print()
    result.print_transition_summary()

    print("\nGenerating plots...")
    plot_state_trajectory(result, os.path.join(PLOT_DIR, "silicon_state_trajectory.png"))
    plot_regime_weights(  result, os.path.join(PLOT_DIR, "regime_weights.png"))
    plot_field_evolution( result, os.path.join(PLOT_DIR, "field_evolution.png"))
    plot_phase_portrait(  result, os.path.join(PLOT_DIR, "phase_portrait.png"))
    plot_omega2_sign_log( result, os.path.join(PLOT_DIR, "omega2_sign_log.png"))
    plot_kernel_curvature(result, os.path.join(PLOT_DIR, "kernel_curvature.png"))

    print("\nDone.")
    return result


if __name__ == "__main__":
    main()
