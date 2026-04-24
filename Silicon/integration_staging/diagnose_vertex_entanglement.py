"""
diagnose_vertex_entanglement.py
================================
Investigates whether the octahedral trajectory passes near the diagonal
vertices (110 diag-a, 111 diag-b) during the solitonic/entangled regime
peak (t ~ 1.5–2.5), and whether this correlates with the kernel
entanglement ratio.

Produces:
  diag_vertex_vs_entanglement.png  — 4-panel cross-correlation plot
  diag_diagonal_vertex_zoom.png    — zoomed view of diagonal vertex weights
  diag_correlation_matrix.png      — Pearson correlation heatmap

Also prints:
  - Peak times for diagonal vertex weights
  - Peak times for kernel entanglement ratio
  - Pearson r between each vertex weight and entanglement ratio
  - Pearson r between each vertex weight and regime weights
"""

import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
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
VERTEX_COLORS = [
    "#4C9BE8",  # 000 +x
    "#56C596",  # 001 -x
    "#E85C4C",  # 010 +y
    "#B07FE8",  # 011 -y
    "#F0A500",  # 100 +z
    "#E87C4C",  # 101 -z
    "#1AC9A0",  # 110 diag-a  ← diagonal
    "#888888",  # 111 diag-b  ← diagonal
]
DIAGONAL_IDX = [6, 7]   # indices of 110 diag-a and 111 diag-b

REGIME_COLORS = {
    "A_linear_quantum":       "#4C9BE8",
    "B_solitonic":            "#56C596",
    "C_chaotic_turbulent":    "#E85C4C",
    "D_topological":          "#B07FE8",
    "E_signature_transition": "#F0A500",
}
REGIME_SHORT = {
    "A_linear_quantum":       "A:Linear",
    "B_solitonic":            "B:Solitonic",
    "C_chaotic_turbulent":    "C:Chaotic",
    "D_topological":          "D:Topological",
    "E_signature_transition": "E:Transition",
}


def run_full_pipeline(steps=500, seed=42, noise=0.05, kernel_every=5):
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


def extract_series(result, bundle, weights_T8):
    """Extract all time series needed for cross-correlation."""
    times = np.array(result.times)

    # Vertex weights: (T, 8)
    vertex_w = weights_T8

    # Kernel entanglement ratio — sampled at kernel_trace_every steps
    kt = result.kernel_trace_array()
    kt_times = kt["time"]
    kt_ratio  = kt["entanglement_ratio"]
    kt_gap    = kt["spectral_gap"]
    kt_schanges = kt["sign_changes"]

    # Interpolate kernel ratio onto full time grid
    ratio_interp  = np.interp(times, kt_times, kt_ratio)
    gap_interp    = np.interp(times, kt_times, kt_gap)

    # Regime weights: (T, 5)
    regime_w = np.array([
        [atlas.weights.get(r, 0.0) for r in ALL_REGIMES]
        for atlas in result.regimes
    ])

    # Omega2 mean
    o2 = result.omega2_log_array()
    omega2_mean = o2["mean"]

    return {
        "times"        : times,
        "vertex_w"     : vertex_w,      # (T, 8)
        "ratio_interp" : ratio_interp,  # (T,)
        "gap_interp"   : gap_interp,    # (T,)
        "regime_w"     : regime_w,      # (T, 5)
        "omega2_mean"  : omega2_mean,   # (T,)
        "kt_times"     : kt_times,
        "kt_ratio"     : kt_ratio,
        "kt_gap"       : kt_gap,
        "kt_schanges"  : kt_schanges,
    }


def compute_correlations(series):
    """Pearson r between each vertex weight and key signals."""
    vertex_w   = series["vertex_w"]
    ratio      = series["ratio_interp"]
    solitonic  = series["regime_w"][:, 1]   # B_solitonic
    omega2     = series["omega2_mean"]

    results = []
    for i in range(8):
        w = vertex_w[:, i]
        r_ent,  p_ent  = stats.pearsonr(w, ratio)
        r_sol,  p_sol  = stats.pearsonr(w, solitonic)
        r_om2,  p_om2  = stats.pearsonr(w, omega2)
        results.append({
            "vertex"        : VERTEX_LABELS[i],
            "r_entanglement": r_ent,
            "p_entanglement": p_ent,
            "r_solitonic"   : r_sol,
            "p_solitonic"   : p_sol,
            "r_omega2"      : r_om2,
            "p_omega2"      : p_om2,
        })
    return results


def print_correlation_table(corr):
    print("\n── Pearson Correlations ──────────────────────────────────────────────")
    print(f"{'Vertex':<22}  {'r(entangle)':>12}  {'r(solitonic)':>13}  {'r(Ω²)':>8}")
    print("─" * 65)
    for c in corr:
        sig_e = "**" if c["p_entanglement"] < 0.01 else ("*" if c["p_entanglement"] < 0.05 else "  ")
        sig_s = "**" if c["p_solitonic"]   < 0.01 else ("*" if c["p_solitonic"]   < 0.05 else "  ")
        sig_o = "**" if c["p_omega2"]      < 0.01 else ("*" if c["p_omega2"]      < 0.05 else "  ")
        print(f"  {c['vertex']:<20}  {c['r_entanglement']:>+.4f}{sig_e}  "
              f"{c['r_solitonic']:>+.4f}{sig_s}  {c['r_omega2']:>+.4f}{sig_o}")
    print("  ** p<0.01  * p<0.05")


def plot_main_diagnostic(series, corr, save_path):
    """
    4-panel cross-correlation plot:
      1. Diagonal vertex weights (110, 111) over time
      2. Kernel entanglement ratio over time
      3. Solitonic regime weight over time
      4. All three overlaid (normalised) for direct peak alignment
    """
    times     = series["times"]
    vertex_w  = series["vertex_w"]
    ratio     = series["ratio_interp"]
    solitonic = series["regime_w"][:, 1]
    omega2    = series["omega2_mean"]
    kt_times  = series["kt_times"]
    kt_ratio  = series["kt_ratio"]

    diag_a = vertex_w[:, 6]   # 110
    diag_b = vertex_w[:, 7]   # 111
    diag_sum = diag_a + diag_b

    fig = plt.figure(figsize=(14, 12))
    gs  = gridspec.GridSpec(4, 1, hspace=0.38)
    fig.suptitle(
        "Diagonal Vertex Occupation vs. Kernel Entanglement & Solitonic Regime",
        fontsize=13, fontweight="bold"
    )

    # ── Panel 1: diagonal vertex weights ─────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(times, diag_a, color=VERTEX_COLORS[6], linewidth=1.5,
             label="110 diag-a weight")
    ax1.plot(times, diag_b, color=VERTEX_COLORS[7], linewidth=1.5,
             label="111 diag-b weight", linestyle="--")
    ax1.fill_between(times, diag_a + diag_b, alpha=0.12, color="#1AC9A0",
                     label="diag-a + diag-b (sum)")
    ax1.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500",
                label="Solitonic peak window (t=1.5–2.5)")
    ax1.set_ylabel("Vertex Weight", fontsize=9)
    ax1.legend(fontsize=7.5, loc="upper right", framealpha=0.85)
    ax1.grid(True, alpha=0.25)
    ax1.set_title("Diagonal Vertex Weights (110, 111)", fontsize=10)

    # ── Panel 2: kernel entanglement ratio ───────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(kt_times, kt_ratio, color="#2A6EBB", linewidth=1.5,
             label="Entanglement ratio (sampled)")
    ax2.fill_between(times, 0, ratio, alpha=0.12, color="#2A6EBB")
    ax2.axhspan(0.0, 0.1, alpha=0.07, color="#56C596", label="Separable (<0.1)")
    ax2.axhspan(0.1, 0.5, alpha=0.07, color="#F0A500", label="Weakly coupled (0.1–0.5)")
    ax2.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500")
    ax2.set_ylabel("Off-diag / Diag", fontsize=9)
    ax2.legend(fontsize=7.5, loc="upper right", framealpha=0.85)
    ax2.grid(True, alpha=0.25)
    ax2.set_title("Kernel Entanglement Ratio", fontsize=10)

    # ── Panel 3: solitonic regime weight ─────────────────────────────────────
    ax3 = fig.add_subplot(gs[2])
    ax3.fill_between(times, 0, solitonic, alpha=0.35,
                     color=REGIME_COLORS["B_solitonic"])
    ax3.plot(times, solitonic, color=REGIME_COLORS["B_solitonic"],
             linewidth=1.5, label="B: Solitonic weight")
    ax3.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500")
    ax3.set_ylabel("Regime Weight", fontsize=9)
    ax3.legend(fontsize=7.5, loc="upper right", framealpha=0.85)
    ax3.grid(True, alpha=0.25)
    ax3.set_title("Solitonic Regime Weight", fontsize=10)

    # ── Panel 4: normalised overlay ──────────────────────────────────────────
    ax4 = fig.add_subplot(gs[3])

    def _norm(x):
        r = x.max() - x.min()
        return (x - x.min()) / (r + 1e-12)

    ax4.plot(times, _norm(diag_sum),  color="#1AC9A0", linewidth=1.8,
             label="Diagonal vertex sum (norm)")
    ax4.plot(times, _norm(ratio),     color="#2A6EBB", linewidth=1.5,
             linestyle="--", label="Entanglement ratio (norm)")
    ax4.plot(times, _norm(solitonic), color=REGIME_COLORS["B_solitonic"],
             linewidth=1.5, linestyle=":", label="Solitonic weight (norm)")
    ax4.axvspan(1.5, 2.5, alpha=0.07, color="#F0A500",
                label="Solitonic peak window")

    # Annotate Pearson r for diagonal sum vs entanglement
    r_diag_ent, p_diag_ent = stats.pearsonr(diag_sum, ratio)
    r_diag_sol, p_diag_sol = stats.pearsonr(diag_sum, solitonic)
    ax4.text(0.02, 0.92,
             f"r(diag_sum, entanglement) = {r_diag_ent:+.4f}  "
             f"{'**' if p_diag_ent < 0.01 else '*' if p_diag_ent < 0.05 else 'ns'}\n"
             f"r(diag_sum, solitonic)    = {r_diag_sol:+.4f}  "
             f"{'**' if p_diag_sol < 0.01 else '*' if p_diag_sol < 0.05 else 'ns'}",
             transform=ax4.transAxes, fontsize=8.5,
             bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.85))

    ax4.set_ylabel("Normalised value", fontsize=9)
    ax4.set_xlabel("Time", fontsize=10)
    ax4.legend(fontsize=7.5, loc="lower right", framealpha=0.85)
    ax4.grid(True, alpha=0.25)
    ax4.set_title("Normalised Overlay — Peak Alignment Check", fontsize=10)

    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_diagonal_zoom(series, save_path):
    """
    Zoomed view of t=1.0–3.0 showing diagonal vertex weights against
    all other vertex weights and the entanglement ratio.
    """
    times    = series["times"]
    vertex_w = series["vertex_w"]
    ratio    = series["ratio_interp"]

    mask = (times >= 1.0) & (times <= 3.0)
    t_z  = times[mask]

    fig, axes = plt.subplots(2, 1, figsize=(13, 7), sharex=True)
    fig.suptitle(
        "Zoomed: t=1.0–3.0 — Vertex Weight Detail vs. Entanglement",
        fontsize=12, fontweight="bold"
    )

    ax = axes[0]
    for i in range(8):
        lw  = 2.2 if i in DIAGONAL_IDX else 0.9
        ls  = "-"  if i in DIAGONAL_IDX else "--"
        alp = 0.95 if i in DIAGONAL_IDX else 0.45
        ax.plot(t_z, vertex_w[mask, i],
                color=VERTEX_COLORS[i], linewidth=lw,
                linestyle=ls, alpha=alp, label=VERTEX_LABELS[i])
    ax.set_ylabel("Vertex Weight", fontsize=9)
    ax.legend(fontsize=7, loc="upper right", ncol=2, framealpha=0.85)
    ax.grid(True, alpha=0.25)
    ax.set_title("All 8 Vertex Weights (diagonal highlighted)", fontsize=10)

    ax2 = axes[1]
    ax2.plot(t_z, ratio[mask], color="#2A6EBB", linewidth=1.6,
             label="Entanglement ratio")
    ax2r = ax2.twinx()
    diag_sum = vertex_w[:, 6] + vertex_w[:, 7]
    ax2r.plot(t_z, diag_sum[mask], color="#1AC9A0", linewidth=1.4,
              linestyle="--", label="Diag vertex sum (right)")
    ax2r.set_ylabel("Diagonal vertex sum", fontsize=8, color="#1AC9A0")
    ax2r.tick_params(labelsize=7)
    ax2.set_ylabel("Entanglement ratio", fontsize=9)
    ax2.set_xlabel("Time", fontsize=10)
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2r.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    ax2.grid(True, alpha=0.25)
    ax2.set_title("Entanglement Ratio vs. Diagonal Vertex Sum", fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_correlation_matrix(series, save_path):
    """
    Pearson correlation heatmap: 8 vertex weights × {entanglement, solitonic,
    linear, Ω², spectral_gap}.
    """
    times     = series["times"]
    vertex_w  = series["vertex_w"]
    ratio     = series["ratio_interp"]
    gap       = series["gap_interp"]
    omega2    = series["omega2_mean"]
    regime_w  = series["regime_w"]

    signals = {
        "Entanglement\nratio"  : ratio,
        "Spectral\ngap"        : gap,
        "Ω² mean"              : omega2,
        "Solitonic\nweight"    : regime_w[:, 1],
        "Linear/QM\nweight"    : regime_w[:, 0],
        "Chaotic\nweight"      : regime_w[:, 2],
    }

    sig_names = list(signals.keys())
    sig_vals  = [signals[k] for k in sig_names]

    corr_mat = np.zeros((8, len(sig_names)))
    for i in range(8):
        for j, sv in enumerate(sig_vals):
            r, _ = stats.pearsonr(vertex_w[:, i], sv)
            corr_mat[i, j] = r

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle("Pearson Correlation: Vertex Weights × Key Signals",
                 fontsize=12, fontweight="bold")

    im = ax.imshow(corr_mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(im, ax=ax, label="Pearson r")

    ax.set_xticks(range(len(sig_names)))
    ax.set_xticklabels(sig_names, fontsize=8)
    ax.set_yticks(range(8))
    ax.set_yticklabels(VERTEX_LABELS, fontsize=8)

    # Annotate cells
    for i in range(8):
        for j in range(len(sig_names)):
            r = corr_mat[i, j]
            color = "white" if abs(r) > 0.5 else "black"
            ax.text(j, i, f"{r:+.3f}", ha="center", va="center",
                    fontsize=7.5, color=color,
                    fontweight="bold" if i in DIAGONAL_IDX else "normal")

    # Highlight diagonal vertex rows
    for di in DIAGONAL_IDX:
        ax.add_patch(plt.Rectangle((-0.5, di - 0.5),
                                   len(sig_names), 1,
                                   fill=False, edgecolor="#1AC9A0",
                                   linewidth=2.0))

    ax.set_xlabel("Signal", fontsize=9)
    ax.set_ylabel("Octahedral Vertex", fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def print_peak_alignment(series):
    """Report peak times for diagonal vertices and entanglement ratio."""
    times    = series["times"]
    vertex_w = series["vertex_w"]
    ratio    = series["ratio_interp"]

    print("\n── Peak Times ────────────────────────────────────────────────────────")
    for i in DIAGONAL_IDX:
        peak_t = times[np.argmax(vertex_w[:, i])]
        peak_w = vertex_w[:, i].max()
        print(f"  {VERTEX_LABELS[i]:<22} peak weight = {peak_w:.5f}  at t = {peak_t:.3f}")

    diag_sum = vertex_w[:, 6] + vertex_w[:, 7]
    peak_t_sum = times[np.argmax(diag_sum)]
    print(f"  {'Diagonal sum':<22} peak sum    = {diag_sum.max():.5f}  at t = {peak_t_sum:.3f}")

    peak_t_ent = times[np.argmax(ratio)]
    print(f"  {'Entanglement ratio':<22} peak ratio  = {ratio.max():.5f}  at t = {peak_t_ent:.3f}")

    dt = abs(peak_t_sum - peak_t_ent)
    print(f"\n  Peak lag |t_diag - t_entanglement| = {dt:.3f} time units")
    if dt < 0.1:
        print("  → Peaks are co-incident: strong mapping confirmed.")
    elif dt < 0.5:
        print("  → Peaks are close: partial mapping, possible lag.")
    else:
        print("  → Peaks are separated: mapping is weak or indirect.")


def main():
    print("=" * 60)
    print("  Diagonal Vertex × Entanglement Correlation Diagnostic")
    print("=" * 60)

    result = run_full_pipeline(steps=500, seed=42, noise=0.05, kernel_every=5)

    print("\nBuilding octahedral bundle...")
    bundle, weights_T8 = bundle_from_pipeline(result)
    print(f"  Bundle built. {len(bundle.history)} steps recorded.")

    series = extract_series(result, bundle, weights_T8)
    corr   = compute_correlations(series)

    print_correlation_table(corr)
    print_peak_alignment(series)

    print("\nGenerating plots...")
    plot_main_diagnostic(series, corr,
        os.path.join(_HERE, "diag_vertex_vs_entanglement.png"))
    plot_diagonal_zoom(series,
        os.path.join(_HERE, "diag_diagonal_vertex_zoom.png"))
    plot_correlation_matrix(series,
        os.path.join(_HERE, "diag_correlation_matrix.png"))

    print("\nDone.")
    return series, corr


if __name__ == "__main__":
    main()
