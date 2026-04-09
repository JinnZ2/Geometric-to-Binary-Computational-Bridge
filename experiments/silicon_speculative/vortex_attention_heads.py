#!/usr/bin/env python3
# STATUS: speculative — vortex-based ML attention heads experiment
"""
vortex_attention_heads.py
=========================
Winding-number-centred attention: vortex cores as attention head anchors.

What this experiment establishes
----------------------------------
Topological CHARGE (winding number ±1) is invariant under smooth deformation
of phi -- standard KT / homotopy-group result.

Topological core POSITION is NOT invariant.  Vortices are free to drift
(they are zero modes of the action).  Re-detecting position from the winding
field each step does NOT give a locked head position.

The correct design -- as used by VortexMemory -- is a REGISTRY:
    1. Inject vortex at desired head location
    2. Scan winding field ONCE and record pixel coordinates in a registry
    3. All future attention computation uses registry coordinates, not re-detection
    4. Gradient updates phi smoothly -> winding charge is preserved at the
       registered address -> head influence is preserved
    5. W (strength) remains gradient-updatable

This file demonstrates both the naive (re-detect) approach and the physics
finding that motivated the registry design.

Experiment structure
--------------------
1. Build phi_v (vortex at source) and phi_s (smooth random)
2. Train: only W updated; position re-detected from phi each step
   - Model V: position = nearest winding core to hint
   - Model S: position = soft argmax of cos^2(phi)
3. Adversarial test: smooth perturbation of phi, positions re-detected
4. Finding: V position drifts MORE (core is a free collective coordinate)
            S position locked near zero (W→0 trivial solution)
5. Conclusion: registry-based locking needed for true positional invariance

The task
---------
Input: x-component of dipole field E_x(r) from source at (x_s, y_s).
Target: contrast c = s+ - s- where s+/-  = integral of E_x over right/left
        half-plane of the source (using a reference Gaussian at the source).

This target is non-trivial (large magnitude) and requires the attention
to be at the correct location.  It cannot be achieved by sigma collapse.

Run:
    python Silicon/vortex_attention_heads.py
"""

from __future__ import annotations
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from Silicon.topological_memory import (
    _make_grid, _add_vortex, _wrap, _winding_field
)

# ---------------------------------------------------------------------------
# Shared task
# ---------------------------------------------------------------------------

def dipole_Ex(X, Y, x0=0.0, y0=0.0, eps=0.08):
    dx = X - x0; dy = Y - y0
    return dx / (dx**2 + dy**2 + eps**2) ** 1.5


def reference_contrast(X, Y, inp, x_s, y_s, sigma=0.3):
    """
    Target: integral of E_x weighted by Gaussian at source.
    Positive because Gaussian at source captures +E_x on the right
    side of the source more than -E_x on the left (asymmetric kernel).
    """
    a = np.exp(-((X - x_s)**2 + (Y - y_s)**2) / (2 * sigma**2))
    a /= a.sum() + 1e-10
    return float((a * inp).sum())


# ---------------------------------------------------------------------------
# Gaussian attention (fixed sigma, only position and W vary)
# ---------------------------------------------------------------------------

SIGMA = 0.30   # fixed for all experiments -- prevents sigma collapse


def gaussian_map(xc, yc, X, Y, sigma=SIGMA):
    a = np.exp(-((X - xc)**2 + (Y - yc)**2) / (2.0 * sigma**2))
    return a / (a.sum() + 1e-10)


def attended_signal(xc, yc, inp, X, Y, sigma=SIGMA):
    return float((gaussian_map(xc, yc, X, Y, sigma) * inp).sum())


# ---------------------------------------------------------------------------
# Position detectors
# ---------------------------------------------------------------------------

def topological_position(phi, X, Y, x_hint, y_hint, threshold=0.35):
    """
    Find the winding-number core closest to the hint position.
    Topological invariant: unchanged under smooth phi perturbation.
    """
    w = _winding_field(phi)
    rows, cols = np.where(w > threshold)
    if len(rows) == 0:
        return x_hint, y_hint   # fallback

    dx = X[0, 1] - X[0, 0]
    best_dist, best_x, best_y = np.inf, x_hint, y_hint
    for r, c in zip(rows, cols):
        xp = float(-1.0 + c * dx)
        yp = float(-1.0 + r * dx)
        d = (xp - x_hint)**2 + (yp - y_hint)**2
        if d < best_dist:
            best_dist, best_x, best_y = d, xp, yp
    return best_x, best_y


def smooth_position(phi, X, Y, beta=6.0):
    """
    Soft argmax of cos^2(phi): attention-weighted centroid.
    Smooth function of phi -- changes under smooth perturbation.
    """
    c2  = np.cos(phi) ** 2
    w   = np.exp(beta * c2)
    Z   = w.sum() + 1e-10
    xc  = float((w * X).sum() / Z)
    yc  = float((w * Y).sum() / Z)
    return xc, yc


def smooth_position_gradient(phi, X, Y, inp, target, W, beta=6.0):
    """
    Gradient of loss w.r.t. phi through the soft-argmax position.

    Loss = 0.5*(W * s(xc,yc) - target)^2
    xc   = sum_r x_r * softmax(beta*cos^2(phi_r))
    s    = sum_r Gaussian(xc, yc) * inp_r

    We need:
        dL/dphi = dL/ds * ds/d(xc,yc) * d(xc,yc)/dphi
    """
    c2   = np.cos(phi) ** 2
    sm   = np.exp(beta * c2); sm /= sm.sum() + 1e-10   # softmax weights
    xc   = float((sm * X).sum())
    yc   = float((sm * Y).sum())

    a    = gaussian_map(xc, yc, X, Y)
    s    = float((a * inp).sum())
    out  = W * s
    e    = out - target

    # ds/dxc and ds/dyc (gradient of attention signal w.r.t. centre)
    ds_dxc = float((a * (xc - X) / SIGMA**2 * inp).sum())
    ds_dyc = float((a * (yc - Y) / SIGMA**2 * inp).sum())

    # d(xc)/dphi_r = x_r * dsm_r/dphi_r - xc * dsm_r/dphi_r
    #              = (x_r - xc) * sm_r * (-2*beta*cos*sin)
    sin2   = 2.0 * np.cos(phi) * np.sin(phi)   # d(cos^2)/dphi = -sin(2phi)
    d_xc   = (X - xc) * sm * (-beta * sin2)
    d_yc   = (Y - yc) * sm * (-beta * sin2)

    # Chain rule
    g = e * W * (ds_dxc * d_xc + ds_dyc * d_yc)
    return g


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run(N=40, n_steps=300, x_s=0.3, y_s=0.2, seed=42,
        perturb_amp=0.6, n_perturb_trials=6):

    rng  = np.random.default_rng(seed)
    X, Y, dx = _make_grid(N)
    inp    = dipole_Ex(X, Y, x0=x_s, y0=y_s)
    target = reference_contrast(X, Y, inp, x_s, y_s)

    print("=" * 68)
    print("WINDING-CORE ATTENTION  --  topologically locked heads")
    print("=" * 68)
    print()
    print(f"  Source=({x_s},{y_s})  target={target:.4f}  sigma={SIGMA}  N={N}x{N}")
    print()
    print("  Architecture:")
    print("    Model V -- position from winding core  (topological, fixed)")
    print("    Model S -- position from cos^2 argmax  (smooth, can drift)")
    print("    Both: Gaussian attention, fixed sigma, only W learned")
    print()

    # --- Build phi fields ---
    phi_v = _wrap(
        _add_vortex(np.zeros((N, N)), X, Y, x_s, y_s, k=1)
        + rng.uniform(-0.05, 0.05, (N, N))
    )
    phi_s = rng.uniform(-np.pi, np.pi, (N, N))

    # Initial positions
    xv0, yv0 = topological_position(phi_v, X, Y, x_s, y_s)
    xs0, ys0 = smooth_position(phi_s, X, Y)
    print(f"  Initial positions:  V=({xv0:.3f},{yv0:.3f})  "
          f"S=({xs0:.3f},{ys0:.3f})  source=({x_s},{y_s})")
    print()

    # Learnable W only
    W_v = rng.uniform(0.5, 1.5)
    W_s = rng.uniform(0.5, 1.5)

    eta_W   = 0.2    # W learning rate
    eta_phi = 0.03   # phi learning rate for smooth model (moves soft peak)
    alpha   = 0.2    # Laplacian smoothing on phi_s

    from Silicon.topological_memory import _laplacian

    print(f"  {'step':>5}  {'loss(V)':>9}  {'loss(S)':>9}  "
          f"  {'pos_V':>14}  {'pos_S':>14}")
    print("  " + "-" * 58)

    for step in range(n_steps + 1):
        # Recompute positions from current phi each step
        xv, yv = topological_position(phi_v, X, Y, x_s, y_s)
        xs, ys = smooth_position(phi_s, X, Y)

        sv  = attended_signal(xv, yv, inp, X, Y)
        ss  = attended_signal(xs, ys, inp, X, Y)
        lv  = 0.5 * (W_v * sv - target) ** 2
        ls  = 0.5 * (W_s * ss - target) ** 2

        if step % 30 == 0 or step == n_steps:
            print(f"  {step:>5}  {lv:9.5f}  {ls:9.5f}  "
                  f"  ({xv:.3f},{yv:.3f})  ({xs:.3f},{ys:.3f})")

        if step == n_steps:
            break

        # W gradients
        W_v -= eta_W * (W_v * sv - target) * sv
        W_s -= eta_W * (W_s * ss - target) * ss

        # phi_v: only Laplacian smoothing (maintains vortex, W does the work)
        phi_v = _wrap(phi_v - 0.005 * _laplacian(phi_v))

        # phi_s: gradient through soft-argmax position + smoothing
        g_phi_s = smooth_position_gradient(phi_s, X, Y, inp, target, W_s)
        phi_s = _wrap(phi_s - eta_phi * (g_phi_s + alpha * _laplacian(phi_s)))

    # Final positions and outputs
    xv_f, yv_f = topological_position(phi_v, X, Y, x_s, y_s)
    xs_f, ys_f = smooth_position(phi_s, X, Y)
    sv_f = attended_signal(xv_f, yv_f, inp, X, Y)
    ss_f = attended_signal(xs_f, ys_f, inp, X, Y)
    out_v = W_v * sv_f
    out_s = W_s * ss_f
    lv_f  = 0.5 * (out_v - target) ** 2
    ls_f  = 0.5 * (out_s - target) ** 2

    print()
    print("  Final state:")
    print(f"    V: pos=({xv_f:.3f},{yv_f:.3f})  W={W_v:.3f}  "
          f"out={out_v:.4f}  loss={lv_f:.6f}")
    print(f"    S: pos=({xs_f:.3f},{ys_f:.3f})  W={W_s:.3f}  "
          f"out={out_s:.4f}  loss={ls_f:.6f}")
    print(f"    source=({x_s},{y_s})  target={target:.4f}")
    print()

    # ----------------------------------------------------------------
    # Adversarial robustness: smooth perturbation of phi
    # ----------------------------------------------------------------
    print("─" * 68)
    print("ROBUSTNESS: smooth phi perturbation, position re-detected each time")
    print("─" * 68)
    print(f"  Amplitude: {perturb_amp} rad  Trials: {n_perturb_trials}")
    print()

    # Make a smooth low-frequency noise field (guaranteed no winding change)
    def make_smooth_noise(amplitude, trial):
        rng2 = np.random.default_rng(trial + 200)
        n = rng2.uniform(-amplitude, amplitude, (N, N))
        for _ in range(12):   # many smoothing passes -> only low-frequency
            n = 0.25 * (np.roll(n,1,0)+np.roll(n,-1,0)+
                        np.roll(n,1,1)+np.roll(n,-1,1))
        return n

    print(f"  {'trial':>5}  {'V pos shift':>12}  {'S pos shift':>12}  "
          f"{'|Δout| V':>10}  {'|Δout| S':>10}")
    print("  " + "-" * 56)

    pos_shifts_v, pos_shifts_s = [], []
    out_shifts_v, out_shifts_s = [], []

    for trial in range(1, n_perturb_trials + 1):
        delta = make_smooth_noise(perturb_amp, trial)

        phi_v_p = _wrap(phi_v + delta)
        phi_s_p = _wrap(phi_s + delta)

        # Re-detect positions from perturbed phi
        xvp, yvp = topological_position(phi_v_p, X, Y, x_s, y_s)
        xsp, ysp = smooth_position(phi_s_p, X, Y)

        # Outputs with perturbed positions
        svp = attended_signal(xvp, yvp, inp, X, Y)
        ssp = attended_signal(xsp, ysp, inp, X, Y)
        out_vp = W_v * svp
        out_sp = W_s * ssp

        ps_v = np.sqrt((xvp - xv_f)**2 + (yvp - yv_f)**2)
        ps_s = np.sqrt((xsp - xs_f)**2 + (ysp - ys_f)**2)
        do_v = abs(out_vp - out_v)
        do_s = abs(out_sp - out_s)

        pos_shifts_v.append(ps_v); pos_shifts_s.append(ps_s)
        out_shifts_v.append(do_v); out_shifts_s.append(do_s)

        print(f"  {trial:>5}  {ps_v:12.4f}  {ps_s:12.4f}  "
              f"{do_v:10.5f}  {do_s:10.5f}")

    mpv = float(np.mean(pos_shifts_v)); mps = float(np.mean(pos_shifts_s))
    mov = float(np.mean(out_shifts_v)); mos = float(np.mean(out_shifts_s))

    print()
    print(f"  Mean position shift:  V={mpv:.4f}   S={mps:.4f}  "
          f"  ratio S/V={mps/(mpv+1e-6):.1f}x")
    print(f"  Mean |Δout|:          V={mov:.5f}  S={mos:.5f}  "
          f"  ratio S/V={mos/(mov+1e-6):.1f}x")
    print()

    if mpv < mps * 0.3:
        pos_verdict = "TOPOLOGICAL POSITION STABLE: V position moves <<  S position"
    elif mpv < mps * 0.7:
        pos_verdict = "Vortex position more stable than smooth (clear)"
    else:
        pos_verdict = "Similar position stability"
    print(f"  Position verdict: {pos_verdict}")

    if mov < mos * 0.5:
        out_verdict = "TOPOLOGICAL OUTPUT STABLE: V output barely changes"
    elif mov < mos:
        out_verdict = "Vortex output more stable (marginal)"
    else:
        out_verdict = "Similar output stability"
    print(f"  Output verdict:   {out_verdict}")
    print()

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print("=" * 68)
    print("WHAT THIS SHOWS")
    print("=" * 68)
    print()
    print("  FINDING: Topological CHARGE is invariant. Core POSITION is NOT.")
    print()
    print("  The winding NUMBER (+1/-1) cannot be created or destroyed by")
    print("  smooth deformation of phi -- this is the topological invariant.")
    print()
    print("  The winding core POSITION is a collective coordinate that IS")
    print("  dynamical.  Vortices can drift, diffuse, and move.  The charge")
    print("  is conserved; the address is not -- this is standard KT physics.")
    print()
    print("  Result: re-detecting position from phi each step means the")
    print("  'topological' head is NOT position-locked.  It drifts as phi")
    print("  evolves under Laplacian smoothing.")
    print()
    print("  CORRECT DESIGN -- registry-based locking (as VortexMemory does):")
    print()
    print("    At write time: record core pixel in a registry (address book)")
    print("    At read time:  use the REGISTERED position, not re-detected")
    print("    Training:      updates phi smoothly -- charge preserved, and")
    print("                   the registry address is never re-computed from phi")
    print()
    print("  VortexMemory already does this correctly:")
    print("    self._registry[bit_index] = (row_pos, col_pos, row_neg, col_neg)")
    print("    read() uses col_pos/col_neg from registry, never from winding field")
    print()
    print("  Lesson for attention architecture:")
    print("    1. Inject vortex at desired head location")
    print("    2. Record position in registry (one-time winding field scan)")
    print("    3. Gaussian head permanently anchored to registry coordinates")
    print("    4. Gradient updates phi -> winding number preserved -> charge at")
    print("       the RIGHT address preserved -> head influence preserved")
    print("    5. W and sigma remain gradient-updatable (learnable strength)")
    print()
    print("  Connection to vacuum_field_theory.md Section VIII:")
    print("  Topological MODES have lambda=0 (Lyapunov stable) -- referring")
    print("  to the charge quantum, not the location.  The position of a vortex")
    print("  core is a zero mode of the action (free to move at no energy cost)")
    print("  unless a pinning potential is added.  The registry IS that pin.")
    print()
    print("Run complete.")

    return {
        "pos_shift_v": mpv, "pos_shift_s": mps,
        "out_shift_v": mov, "out_shift_s": mos,
        "loss_v": lv_f, "loss_s": ls_f,
    }


if __name__ == "__main__":
    run()
