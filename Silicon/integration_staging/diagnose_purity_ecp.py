"""
diagnose_purity_ecp.py — Operator Purity and Entanglement-Computation Product
==============================================================================
Implements and plots two diagnostics derived from the computational phase
diagram interpretation:

  A. Operator Purity
     purity(t) = max(vertex_weights(t))
     When purity → 1.0: single pure computational mode (classical/solitonic).
     When purity → 1/8 ≈ 0.125: maximally mixed, all modes contribute equally.

  B. Entanglement-Computation Product (ECP)
     ECP(t) = entanglement_ratio(t) × (1 - purity(t))
     Peaks when the system is simultaneously entangled AND mixed.
     This is the regime of maximally non-classical computation.

Produces:
  purity_ecp.png           — 4-panel: purity, ECP, regime overlay, phase portrait
  purity_phase_portrait.png — purity vs. entanglement ratio scatter, coloured by time
"""

import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.cm as cm
from scipy import stats

_HERE    = os.path.dirname(os.path.abspath(__file__))
_SILICON = os.path.dirname(_HERE)
_MODULES = os.path.join(_SILICON, "modules")
sys.path.insert(0, _MODULES)
sys.path.insert(0, _SILICON)

from modules.state import make_state
from modules.pipeline import PipelineConfig, run_pipeline
from modules.regime import ALL_REGIMES
from integration_staging.octahedral_bundle import (
    build_vertex_atlas, bundle_from_pipeline, _VERTEX_SPECS,
)

VERTEX_LABELS = [f"{bits} {label}" for bits, label, *_ in _VERTEX_SPECS]
DIAGONAL_IDX  = [6, 7]

REGIME_COLORS = {
    "A_linear_quantum":       "#4C9BE8",
    "B_solitonic":            "#56C596",
    "C_chaotic_turbulent":    "#E85C4C",
    "D_topological":          "#B07FE8",
    "E_signature_transition": "#F0A500",
}
REGIME_SHORT = {
    "A_linear_quantum":       "A: Linear/QM",
    "B_solitonic":            "B: Solitonic",
    "C_chaotic_turbulent":    "C: Chaotic",
    "D_topological":          "D: Topological",
    "E_signature_transition": "E: Transition",
}


def run_pipeline_with_tracing(steps=500, seed=42, noise=0.05, kernel_every=5):
    cfg = PipelineConfig(
        steps              = steps,
        dt                 = 0.01,
        integrator         = "stochastic",
        noise_scale        = noise,
        N_spatial          = 64,
        pde_coupling       = True,
        record_every       = 1,
        kernel_trace_every = kernel_every,
        omega2_alpha       = 1.0,
        seed               = seed,
    )
    S0 = make_state(n=1e17, mu=1400.0, T=300.0,
                    d_bulk=0.05, d_iface=0.05,
                    l=3.0, k1=1.0, k2=0.5, k3=0.3)
    print(f"Running pipeline: {steps} steps, noise={noise}, seed={seed} ...")
    result = run_pipeline(S0=S0, config=cfg)
    print(f"  Done. Final regime: {result.regimes[-1].label}")
    return result


def compute_purity_ecp(result, weights_T8):
    """Compute purity and ECP from vertex weights and entanglement ratio."""
    times = np.array(result.times)

    # Operator purity: max vertex weight at each step
    purity = np.max(weights_T8, axis=1)

    # Dominant vertex index over time
    dom_idx = np.argmax(weights_T8, axis=1)

    # Entanglement ratio interpolated onto full time grid
    kt = result.kernel_trace_array()
    ratio_interp = np.interp(times, kt["time"], kt["entanglement_ratio"])
    gap_interp   = np.interp(times, kt["time"], kt["spectral_gap"])

    # ECP: entanglement × (1 - purity)
    ecp = ratio_interp * (1.0 - purity)

    # Regime weights (T, 5)
    regime_w = np.array([
        [atlas.weights.get(r, 0.0) for r in ALL_REGIMES]
        for atlas in result.regimes
    ])

    # Diagonal vertex sum
    diag_sum = weights_T8[:, 6] + weights_T8[:, 7]

    return {
        "times"        : times,
        "purity"       : purity,
        "dom_idx"      : dom_idx,
        "ratio_interp" : ratio_interp,
        "gap_interp"   : gap_interp,
        "ecp"          : ecp,
        "regime_w"     : regime_w,
        "diag_sum"     : diag_sum,
        "weights_T8"   : weights_T8,
    }


def print_summary(d):
    times  = d["times"]
    purity = d["purity"]
    ecp    = d["ecp"]
    ratio  = d["ratio_interp"]

    print("\n── Operator Purity ───────────────────────────────────────────────────")
    print(f"  Mean purity       : {purity.mean():.4f}")
    print(f"  Min  purity       : {purity.min():.4f}  at t = {times[np.argmin(purity)]:.3f}")
    print(f"  Max  purity       : {purity.max():.4f}  at t = {times[np.argmax(purity)]:.3f}")
    print(f"  Pure-mode frac    : {(purity > 0.35).mean()*100:.1f}%  (purity > 0.35)")
    print(f"  Mixed-mode frac   : {(purity < 0.20).mean()*100:.1f}%  (purity < 0.20)")

    print("\n── Entanglement-Computation Product (ECP) ────────────────────────────")
    print(f"  Mean ECP          : {ecp.mean():.5f}")
    print(f"  Max  ECP          : {ecp.max():.5f}  at t = {times[np.argmax(ecp)]:.3f}")
    print(f"  Peak entanglement : {ratio.max():.5f}  at t = {times[np.argmax(ratio)]:.3f}")
    print(f"  ECP > 0.02 frac   : {(ecp > 0.02).mean()*100:.1f}%  of trajectory")

    # Correlation between purity and ECP
    r_pe, p_pe = stats.pearsonr(purity, ecp)
    r_pr, p_pr = stats.pearsonr(purity, ratio)
    print(f"\n  r(purity, ECP)    : {r_pe:+.4f}  {'**' if p_pe < 0.01 else ''}")
    print(f"  r(purity, ratio)  : {r_pr:+.4f}  {'**' if p_pr < 0.01 else ''}")

    # Solitonic window check
    mask_sol = (times >= 1.5) & (times <= 2.5)
    print(f"\n── Solitonic Window (t=1.5–2.5) ─────────────────────────────────────")
    print(f"  Mean purity in window : {purity[mask_sol].mean():.4f}")
    print(f"  Mean ECP    in window : {ecp[mask_sol].mean():.5f}")
    print(f"  Mean ratio  in window : {ratio[mask_sol].mean():.5f}")
    if purity[mask_sol].mean() > purity.mean():
        print("  → Purity is ABOVE average in solitonic window (pure-mode computation)")
    else:
        print("  → Purity is BELOW average in solitonic window (mixed-mode computation)")
    if ecp[mask_sol].mean() < ecp.mean():
        print("  → ECP is BELOW average in solitonic window (low non-classical content)")
    else:
        print("  → ECP is ABOVE average in solitonic window (high non-classical content)")


def plot_purity_ecp(d, save_path):
    """4-panel: purity, ECP, regime overlay, purity vs. entanglement."""
    times   = d["times"]
    purity  = d["purity"]
    ecp     = d["ecp"]
    ratio   = d["ratio_interp"]
    gap     = d["gap_interp"]
    regime_w = d["regime_w"]

    fig = plt.figure(figsize=(14, 13))
    gs  = gridspec.GridSpec(4, 1, hspace=0.40)
    fig.suptitle(
        "Operator Purity and Entanglement-Computation Product (ECP)",
        fontsize=13, fontweight="bold"
    )

    # ── Panel 1: Operator Purity ──────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    ax1.fill_between(times, 1/8, purity, where=(purity >= 1/8),
                     alpha=0.22, color="#56C596", label="Above uniform (1/8)")
    ax1.plot(times, purity, color="#2A6EBB", linewidth=1.8, label="Purity = max(vertex weights)")
    ax1.axhline(1/8, color="#888888", linewidth=0.9, linestyle=":",
                label="Uniform (1/8 = fully mixed)")
    ax1.axhline(0.35, color="#E85C4C", linewidth=0.8, linestyle="--",
                label="Pure-mode threshold (0.35)")
    ax1.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500", label="Solitonic window")
    ax1.set_ylabel("Purity", fontsize=9)
    ax1.set_ylim(0, 0.55)
    ax1.legend(fontsize=7.5, loc="upper right", framealpha=0.85, ncol=2)
    ax1.grid(True, alpha=0.25)
    ax1.set_title("Operator Purity  [purity(t) = max(vertex_weights(t))]", fontsize=10)

    # ── Panel 2: ECP ─────────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.fill_between(times, 0, ecp, alpha=0.30, color="#B07FE8")
    ax2.plot(times, ecp, color="#7B3FBE", linewidth=1.8,
             label="ECP = entanglement_ratio × (1 − purity)")
    ax2r = ax2.twinx()
    ax2r.plot(times, ratio, color="#4C9BE8", linewidth=1.0, linestyle="--",
              alpha=0.7, label="Entanglement ratio (right)")
    ax2r.set_ylabel("Entanglement ratio", fontsize=8, color="#4C9BE8")
    ax2r.tick_params(labelsize=7)
    ax2.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500")
    ax2.set_ylabel("ECP", fontsize=9)
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2r.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=7.5,
               loc="upper left", framealpha=0.85)
    ax2.grid(True, alpha=0.25)
    ax2.set_title(
        "Entanglement-Computation Product  [ECP(t) = ratio(t) × (1 − purity(t))]",
        fontsize=10
    )

    # ── Panel 3: Regime weights stacked ──────────────────────────────────────
    ax3 = fig.add_subplot(gs[2])
    bottom = np.zeros(len(times))
    for i, (rname, rcolor) in enumerate(REGIME_COLORS.items()):
        w = regime_w[:, i]
        ax3.fill_between(times, bottom, bottom + w,
                         color=rcolor, alpha=0.75,
                         label=REGIME_SHORT[rname])
        bottom += w
    ax3.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500")
    ax3.set_ylim(0, 1)
    ax3.set_ylabel("Regime Weight", fontsize=9)
    ax3.legend(fontsize=7.5, loc="upper right", framealpha=0.85, ncol=2)
    ax3.grid(True, alpha=0.25)
    ax3.set_title("Regime Weights (stacked)", fontsize=10)

    # ── Panel 4: Purity vs. ECP normalised overlay ───────────────────────────
    ax4 = fig.add_subplot(gs[3])

    def _norm(x):
        r = x.max() - x.min()
        return (x - x.min()) / (r + 1e-12)

    ax4.plot(times, _norm(purity),  color="#2A6EBB", linewidth=1.8,
             label="Purity (norm)")
    ax4.plot(times, _norm(ecp),     color="#7B3FBE", linewidth=1.5,
             linestyle="--", label="ECP (norm)")
    ax4.plot(times, _norm(gap),     color="#E85C4C", linewidth=1.2,
             linestyle=":", label="Spectral gap (norm)")
    ax4.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500", label="Solitonic window")

    # Annotate correlations
    r_pe, _ = stats.pearsonr(purity, ecp)
    r_pg, _ = stats.pearsonr(purity, gap)
    ax4.text(0.02, 0.90,
             f"r(purity, ECP)          = {r_pe:+.4f}\n"
             f"r(purity, spectral_gap) = {r_pg:+.4f}",
             transform=ax4.transAxes, fontsize=8.5,
             bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85))

    ax4.set_ylabel("Normalised value", fontsize=9)
    ax4.set_xlabel("Time", fontsize=10)
    ax4.legend(fontsize=7.5, loc="lower right", framealpha=0.85)
    ax4.grid(True, alpha=0.25)
    ax4.set_title("Normalised Overlay: Purity, ECP, Spectral Gap", fontsize=10)

    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_phase_portrait(d, save_path):
    """
    Purity vs. entanglement ratio scatter plot, coloured by time.
    Reveals the trajectory through computational phase space.
    Annotates the diagonal vertex and axis vertex regions.
    """
    times   = d["times"]
    purity  = d["purity"]
    ratio   = d["ratio_interp"]
    ecp     = d["ecp"]
    dom_idx = d["dom_idx"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.subplots_adjust(left=0.07, right=0.96, top=0.88, bottom=0.12, wspace=0.38)
    fig.suptitle(
        "Computational Phase Space: Purity × Entanglement Ratio",
        fontsize=13, fontweight="bold"
    )

    # ── Left: trajectory coloured by time ────────────────────────────────────
    ax = axes[0]
    sc = ax.scatter(ratio, purity, c=times, cmap="plasma",
                    s=6, alpha=0.7, linewidths=0)
    plt.colorbar(sc, ax=ax, label="Time")

    # Annotate quadrants
    ax.axhline(0.25, color="#888888", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.axvline(0.15, color="#888888", linewidth=0.8, linestyle="--", alpha=0.6)

    ax.text(0.02, 0.38, "PURE + LOW ENTANGLE\n(Solitonic / Classical)",
            fontsize=8, color="#2A6EBB", alpha=0.85)
    ax.text(0.16, 0.38, "PURE + HIGH ENTANGLE\n(Entangled pure mode)",
            fontsize=8, color="#7B3FBE", alpha=0.85)
    ax.text(0.02, 0.10, "MIXED + LOW ENTANGLE\n(Transition / Chaotic)",
            fontsize=8, color="#E85C4C", alpha=0.85)
    ax.text(0.16, 0.10, "MIXED + HIGH ENTANGLE\n(Maximal ECP — non-classical)",
            fontsize=8, color="#56C596", alpha=0.85)

    # Mark start and end
    ax.scatter([ratio[0]], [purity[0]], s=80, color="white",
               edgecolors="#333333", linewidths=1.5, zorder=5, label="Start")
    ax.scatter([ratio[-1]], [purity[-1]], s=80, marker="*", color="yellow",
               edgecolors="#333333", linewidths=1.0, zorder=5, label="End")

    ax.set_xlabel("Entanglement Ratio (off-diag / diag)", fontsize=9)
    ax.set_ylabel("Operator Purity (max vertex weight)", fontsize=9)
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(True, alpha=0.2)
    ax.set_title("Trajectory in Computational Phase Space", fontsize=10)

    # ── Right: ECP landscape (purity vs ratio, coloured by ECP) ─────────────
    ax2 = axes[1]
    sc2 = ax2.scatter(ratio, purity, c=ecp, cmap="hot_r",
                      s=6, alpha=0.7, linewidths=0, vmin=0)
    plt.colorbar(sc2, ax=ax2, label="ECP = ratio × (1 − purity)")

    ax2.axhline(0.25, color="#888888", linewidth=0.8, linestyle="--", alpha=0.6)
    ax2.axvline(0.15, color="#888888", linewidth=0.8, linestyle="--", alpha=0.6)

    # Annotate ECP peak
    peak_idx = np.argmax(ecp)
    ax2.scatter([ratio[peak_idx]], [purity[peak_idx]], s=100,
                marker="D", color="cyan", edgecolors="#333333",
                linewidths=1.2, zorder=5, label=f"ECP peak (t={times[peak_idx]:.2f})")

    ax2.set_xlabel("Entanglement Ratio", fontsize=9)
    ax2.set_ylabel("Operator Purity", fontsize=9)
    ax2.legend(fontsize=8, loc="upper left")
    ax2.grid(True, alpha=0.2)
    ax2.set_title("ECP Landscape in Phase Space", fontsize=10)

    plt.savefig(save_path, dpi=100)
    plt.close()
    print(f"  Saved: {save_path}")


def main():
    print("=" * 60)
    print("  Operator Purity & ECP Diagnostic")
    print("=" * 60)

    result = run_pipeline_with_tracing(steps=500, seed=42, noise=0.05, kernel_every=5)

    print("\nBuilding octahedral bundle...")
    bundle, weights_T8 = bundle_from_pipeline(result)
    print(f"  Bundle built. {len(bundle.history)} steps recorded.")

    d = compute_purity_ecp(result, weights_T8)
    print_summary(d)

    print("\nGenerating plots...")
    plot_purity_ecp(d,       os.path.join(_HERE, "purity_ecp.png"))
    plot_phase_portrait(d,   os.path.join(_HERE, "purity_phase_portrait.png"))

    print("\nDone.")
    return d


if __name__ == "__main__":
    main()
