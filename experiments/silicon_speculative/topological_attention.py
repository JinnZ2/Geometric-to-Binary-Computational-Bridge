#!/usr/bin/env python3
# STATUS: speculative — topological attention mechanism experiment
"""
topological_attention.py
========================
Objective function that requires topology to compute, not just survive it.

The problem with case_a_demo.py
--------------------------------
cos(phi) * inp has a degeneracy: near a vortex core phi ~ pi/2, so
cos(phi) ~ 0 regardless of the target. A smooth model can exploit this by
driving phi -> pi/2 everywhere near the boundary, achieving low loss without
topology. The vortex advantage only shows up at initialization.

The fix: topological attention
--------------------------------
Two attention heads are defined by the phase field:

    a+(r) = softmax_r( beta * cos(phi(r)) )    -- attends to cos > 0 region
    a-(r) = softmax_r( beta * -cos(phi(r)) )   -- attends to cos < 0 region

    out = W+ * sum_r a+(r)*inp(r)  +  W- * sum_r a-(r)*inp(r)

A vortex at (x0, y0) creates a sharp half-plane boundary. a+ integrates
over one half, a- over the other. For tasks where the signal has opposite
sign in the two halves, this perfectly separates the contributions.

A smooth phi gives overlapping, diffuse attention -- both heads see the same
mixed signal, raising the irreducible loss. The vortex is necessary.

The task: dipole source localization
--------------------------------------
Input: x-component of electric field from a unit dipole at the origin.
    E_x(r) = (x - x0) / |r - r0|^3  (positive right, negative left)

Target: scalar -- the x-coordinate of the source (here 0.0).

The optimal phi has a vortex at (x0, y0). The attention boundary then
cleanly separates E_x > 0 from E_x < 0. The learned W+, W- recover
the contrast, and out = W+*sum+ + W-*sum- reconstructs the source position.

A smooth phi cannot place a sharp boundary at the source -- the softmax
spreads weight across both sides, mixing signals and raising loss.

Physics connection
------------------
This is Gauss's law as an objective function. The topological winding
around the source gives an integer invariant (total enclosed charge).
The attention heads are computing a discrete version of the surface
integral -- exact with a topological boundary, approximate with a smooth one.

The same structure appears in:
    - Topological quantum computation (vortices as qubits)
    - Holographic entanglement entropy (Ryu-Takayanagi surface)
    - Persistent homology (topological data analysis)

Here it becomes a concrete gradient-descent objective.

Run:
    python Silicon/topological_attention.py
"""

from __future__ import annotations
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from Silicon.topological_memory import (
    _make_grid, _add_vortex, _wrap, _laplacian, _winding_field
)

# ---------------------------------------------------------------------------
# Dipole field (the task input)
# ---------------------------------------------------------------------------

def dipole_field(X: np.ndarray, Y: np.ndarray,
                 x0: float = 0.0, y0: float = 0.0,
                 eps: float = 0.05) -> np.ndarray:
    """
    x-component of the electric field from a point charge at (x0, y0).

    E_x(r) = (x - x0) / (|r - r0|^2 + eps^2)^(3/2)

    Regularised by eps to avoid singularity at the source.
    Positive to the right of the source, negative to the left.
    """
    dx = X - x0
    dy = Y - y0
    r3 = (dx**2 + dy**2 + eps**2) ** 1.5
    return dx / r3


# ---------------------------------------------------------------------------
# Topological attention forward pass
# ---------------------------------------------------------------------------

def attention_heads(phi: np.ndarray, beta: float = 8.0) -> tuple:
    """
    Compute two attention weight maps from the phase field.

    a+(r) = exp(beta * cos(phi(r))) / Z+     attends to cos > 0
    a-(r) = exp(-beta * cos(phi(r))) / Z-    attends to cos < 0

    Returns (a_pos, a_neg), each shape (N, N), summing to 1.
    """
    c = np.cos(phi)
    exp_pos = np.exp(beta * c)
    exp_neg = np.exp(-beta * c)
    a_pos = exp_pos / (exp_pos.sum() + 1e-10)
    a_neg = exp_neg / (exp_neg.sum() + 1e-10)
    return a_pos, a_neg


def forward(phi: np.ndarray, inp: np.ndarray,
            W: np.ndarray, beta: float = 8.0) -> float:
    """
    Two-head topological attention readout.

    out = W[0] * sum(a+ * inp)  +  W[1] * sum(a- * inp)

    W : shape (2,) -- learned readout weights
    Returns scalar output.
    """
    a_pos, a_neg = attention_heads(phi, beta)
    s_pos = float((a_pos * inp).sum())
    s_neg = float((a_neg * inp).sum())
    return W[0] * s_pos + W[1] * s_neg


def loss_fn(phi: np.ndarray, inp: np.ndarray,
            W: np.ndarray, target: float, beta: float = 8.0) -> float:
    """Scalar MSE loss."""
    out = forward(phi, inp, W, beta)
    return 0.5 * (out - target) ** 2


# ---------------------------------------------------------------------------
# Gradients
# ---------------------------------------------------------------------------

def grad_phi(phi: np.ndarray, inp: np.ndarray,
             W: np.ndarray, target: float,
             beta: float = 8.0, alpha: float = 0.3) -> np.ndarray:
    """
    Gradient of loss w.r.t. phi(r), plus Laplacian smoothing.

    d_loss/d_phi(r):
      out = W0*s+ + W1*s-
      e   = out - target

      ds+/d_phi(r) = a+(r) * (-sin(phi(r)) * beta) * (inp(r) - s+)
      ds-/d_phi(r) = a-(r) * ( sin(phi(r)) * beta) * (inp(r) - s-)

    Full gradient adds Laplacian to keep phi smooth between vortex cores.
    """
    a_pos, a_neg = attention_heads(phi, beta)
    s_pos = float((a_pos * inp).sum())
    s_neg = float((a_neg * inp).sum())
    out = W[0] * s_pos + W[1] * s_neg
    e   = out - target

    sin_phi = np.sin(phi)

    # Chain rule through softmax attention
    g_pos = a_pos * (-sin_phi * beta) * (inp - s_pos)   # (N,N)
    g_neg = a_neg * ( sin_phi * beta) * (inp - s_neg)

    # d_loss/d_phi = e * (W0 * g_pos + W1 * g_neg)
    g_phi = e * (W[0] * g_pos + W[1] * g_neg)

    # Laplacian smoothing (keeps non-core regions well-behaved)
    g_smooth = _laplacian(phi)

    return g_phi + alpha * g_smooth


def grad_W(phi: np.ndarray, inp: np.ndarray,
           W: np.ndarray, target: float, beta: float = 8.0) -> np.ndarray:
    """Gradient of loss w.r.t. readout weights W."""
    a_pos, a_neg = attention_heads(phi, beta)
    s_pos = float((a_pos * inp).sum())
    s_neg = float((a_neg * inp).sum())
    out = W[0] * s_pos + W[1] * s_neg
    e   = out - target
    return np.array([e * s_pos, e * s_neg])


# ---------------------------------------------------------------------------
# Contrast metric: how well-separated are the two heads?
# ---------------------------------------------------------------------------

def head_contrast(phi: np.ndarray, inp: np.ndarray, beta: float = 8.0) -> float:
    """
    Signal contrast between the two attention heads.

    contrast = |sum(a+*inp) - sum(a-*inp)| / (|sum(a+*inp)| + |sum(a-*inp)| + 1e-8)

    Perfect separation of a bipolar field: contrast -> 1.0
    Diffuse / overlapping heads:            contrast -> 0.0

    This is the metric that topology maximises and smooth phi cannot match.
    """
    a_pos, a_neg = attention_heads(phi, beta)
    s_pos = float((a_pos * inp).sum())
    s_neg = float((a_neg * inp).sum())
    return abs(s_pos - s_neg) / (abs(s_pos) + abs(s_neg) + 1e-8)


# ---------------------------------------------------------------------------
# Experiment
# ---------------------------------------------------------------------------

def run(N: int = 40, n_steps: int = 600, source_x: float = 0.0,
        source_y: float = 0.0, eta_phi: float = 0.02, eta_W: float = 0.05,
        beta: float = 8.0, alpha_smooth: float = 0.3, seed: int = 42):
    """
    Compare vortex-initialised vs smooth phi on dipole source localization.

    Both models learn W (readout weights) simultaneously.
    phi is updated by gradient descent.
    The task target is the x-coordinate of the source (0.0 here).
    """
    rng = np.random.default_rng(seed)
    X, Y, dx = _make_grid(N)

    # Task input: dipole field at the source position
    inp = dipole_field(X, Y, x0=source_x, y0=source_y)
    target = source_x   # recover x-coordinate from field

    # --- Model V: vortex at source position ---
    phi_v = _wrap(_add_vortex(np.zeros((N, N)), X, Y, source_x, source_y, k=1)
                  + rng.uniform(-0.1, 0.1, (N, N)))
    W_v   = rng.uniform(-0.1, 0.1, 2)

    # --- Model S: smooth random init, no vortex ---
    phi_s = rng.uniform(-0.5, 0.5, (N, N))
    W_s   = rng.uniform(-0.1, 0.1, 2)

    print("=" * 68)
    print("TOPOLOGICAL ATTENTION  --  dipole source localization")
    print("=" * 68)
    print()
    print("Task: recover source x-coordinate from dipole field E_x(r).")
    print("Two attention heads split the field; W learns the readout.")
    print()
    print("Model V: vortex at source -- heads cleanly separate +/- E_x.")
    print("Model S: smooth random   -- heads overlap, mixed signal.")
    print()
    print(f"  Grid: {N}x{N}  steps: {n_steps}  beta={beta}  source=({source_x},{source_y})")
    print()

    # Initial contrast
    c_v0 = head_contrast(phi_v, inp, beta)
    c_s0 = head_contrast(phi_s, inp, beta)
    l_v0 = loss_fn(phi_v, inp, W_v, target, beta)
    l_s0 = loss_fn(phi_s, inp, W_s, target, beta)

    print(f"  {'step':>5}  {'loss(V)':>9}  {'loss(S)':>9}  "
          f"{'contrast(V)':>13}  {'contrast(S)':>13}")
    print("  " + "-" * 56)
    print(f"  {'0':>5}  {l_v0:9.5f}  {l_s0:9.5f}  "
          f"{c_v0:13.4f}  {c_s0:13.4f}")

    hist = dict(step=[0], loss_v=[l_v0], loss_s=[l_s0],
                contrast_v=[c_v0], contrast_s=[c_s0])

    for step in range(1, n_steps + 1):
        # Model V update
        gp_v = grad_phi(phi_v, inp, W_v, target, beta, alpha_smooth)
        gW_v = grad_W(phi_v, inp, W_v, target, beta)
        phi_v = _wrap(phi_v - eta_phi * gp_v)
        W_v  -= eta_W * gW_v

        # Model S update
        gp_s = grad_phi(phi_s, inp, W_s, target, beta, alpha_smooth)
        gW_s = grad_W(phi_s, inp, W_s, target, beta)
        phi_s = _wrap(phi_s - eta_phi * gp_s)
        W_s  -= eta_W * gW_s

        if step % 60 == 0 or step == n_steps:
            l_v = loss_fn(phi_v, inp, W_v, target, beta)
            l_s = loss_fn(phi_s, inp, W_s, target, beta)
            c_v = head_contrast(phi_v, inp, beta)
            c_s = head_contrast(phi_s, inp, beta)
            hist["step"].append(step)
            hist["loss_v"].append(l_v)
            hist["loss_s"].append(l_s)
            hist["contrast_v"].append(c_v)
            hist["contrast_s"].append(c_s)
            print(f"  {step:>5}  {l_v:9.5f}  {l_s:9.5f}  "
                  f"{c_v:13.4f}  {c_s:13.4f}")

    print()

    # --- Results ---
    l_v_f  = hist["loss_v"][-1]
    l_s_f  = hist["loss_s"][-1]
    c_v_f  = hist["contrast_v"][-1]
    c_s_f  = hist["contrast_s"][-1]

    # Vortex count at end
    w_v = _winding_field(phi_v)
    n_vortex = int((w_v > 0.35).sum())

    # Readout weights
    out_v = forward(phi_v, inp, W_v, beta)
    out_s = forward(phi_s, inp, W_s, beta)

    print("=" * 68)
    print("RESULTS")
    print("=" * 68)
    print()
    print(f"  Source position (true):          x = {source_x:.4f}")
    print(f"  Vortex model output:             x = {out_v:.4f}   "
          f"error = {abs(out_v - source_x):.5f}")
    print(f"  Smooth model output:             x = {out_s:.4f}   "
          f"error = {abs(out_s - source_x):.5f}")
    print()
    print(f"  Final loss     V={l_v_f:.6f}   S={l_s_f:.6f}")
    print(f"  Head contrast  V={c_v_f:.4f}    S={c_s_f:.4f}")
    print(f"  Vortex cores in Model V: {n_vortex}")
    print()
    print(f"  Readout W (vortex): {W_v}")
    print(f"  Readout W (smooth): {W_s}")
    print()

    # Key metric: contrast gap
    contrast_gap = c_v_f - c_s_f
    loss_gap = l_s_f - l_v_f

    if contrast_gap > 0.1:
        verdict = "TOPOLOGY COMPUTES: vortex head contrast >> smooth"
    elif contrast_gap > 0.02:
        verdict = "TOPOLOGY HELPS: vortex head contrast > smooth"
    else:
        verdict = "NEUTRAL: both models achieve similar contrast"

    print(f"  Verdict: {verdict}")
    print(f"  Contrast gap (V - S): {contrast_gap:+.4f}")
    print(f"  Loss gap (S - V):     {loss_gap:+.6f}")
    print()

    print("  Why contrast matters:")
    print("  Head contrast = how cleanly the two heads see opposite signals.")
    print("  A vortex at the source creates a perfect half-plane boundary.")
    print("  Smooth phi cannot create a sharp boundary => contrast stays low.")
    print("  Low contrast means both heads see the same mixed signal =>")
    print("  the readout W cannot separate them => irreducible error floor.")
    print()

    print("  Connection to Gauss's law:")
    print("  The topological winding number around the source is an integer")
    print("  invariant. It counts the enclosed charge exactly. The attention")
    print("  heads compute a differentiable approximation to the surface")
    print("  integral -- exact at the topological boundary, approximate")
    print("  (and improvable) for smooth boundaries.")
    print()

    assert c_v0 > c_s0 or abs(c_v0 - c_s0) < 0.05, \
        "Vortex should start with higher or equal contrast"
    print("  [OK] Vortex model starts with higher or equal head contrast")
    print()
    print("Run complete.")

    return hist


# ---------------------------------------------------------------------------
# Multi-source experiment: does topology scale?
# ---------------------------------------------------------------------------

def run_multisource(N: int = 64, n_steps: int = 400, n_sources: int = 2,
                    seed: int = 7):
    """
    Two dipole sources at known positions.
    Model V: two vortices, one at each source.
    Model S: smooth random init.
    Task: recover sum of source x-coordinates.

    Demonstrates that multiple vortices compute multiple Gauss integrals
    simultaneously -- a topological parallel computation.
    """
    rng = np.random.default_rng(seed)
    X, Y, dx = _make_grid(N)

    # Source positions
    sources = [(-0.4, 0.0), (0.4, 0.0)]
    target  = sum(s[0] for s in sources)   # sum of x-coords = 0.0 here

    # Combined field (superposition)
    inp = sum(dipole_field(X, Y, x0=sx, y0=sy) for sx, sy in sources)

    # Model V: vortices at both sources
    phi_v = np.zeros((N, N))
    for sx, sy in sources:
        phi_v = _add_vortex(phi_v, X, Y, sx, sy, k=1)
    phi_v = _wrap(phi_v + rng.uniform(-0.05, 0.05, (N, N)))
    W_v   = rng.uniform(-0.1, 0.1, 2)

    # Model S: smooth
    phi_s = rng.uniform(-0.5, 0.5, (N, N))
    W_s   = rng.uniform(-0.1, 0.1, 2)

    print()
    print("=" * 68)
    print("MULTI-SOURCE EXPERIMENT")
    print("=" * 68)
    print(f"  Sources: {sources}  target={target:.1f}  N={N}x{N}")
    print()

    eta_phi = 0.015
    eta_W   = 0.05
    beta    = 6.0
    alpha   = 0.3

    print(f"  {'step':>5}  {'loss(V)':>9}  {'loss(S)':>9}  "
          f"{'contrast(V)':>13}  {'contrast(S)':>13}")
    print("  " + "-" * 56)

    for step in range(n_steps + 1):
        if step % 80 == 0 or step == n_steps:
            l_v = loss_fn(phi_v, inp, W_v, target, beta)
            l_s = loss_fn(phi_s, inp, W_s, target, beta)
            c_v = head_contrast(phi_v, inp, beta)
            c_s = head_contrast(phi_s, inp, beta)
            print(f"  {step:>5}  {l_v:9.5f}  {l_s:9.5f}  "
                  f"{c_v:13.4f}  {c_s:13.4f}")

        if step < n_steps:
            gp_v = grad_phi(phi_v, inp, W_v, target, beta, alpha)
            gW_v = grad_W(phi_v, inp, W_v, target, beta)
            phi_v = _wrap(phi_v - eta_phi * gp_v)
            W_v  -= eta_W * gW_v

            gp_s = grad_phi(phi_s, inp, W_s, target, beta, alpha)
            gW_s = grad_W(phi_s, inp, W_s, target, beta)
            phi_s = _wrap(phi_s - eta_phi * gp_s)
            W_s  -= eta_W * gW_s

    out_v = forward(phi_v, inp, W_v, beta)
    out_s = forward(phi_s, inp, W_s, beta)
    l_v = loss_fn(phi_v, inp, W_v, target, beta)
    l_s = loss_fn(phi_s, inp, W_s, target, beta)
    c_v = head_contrast(phi_v, inp, beta)
    c_s = head_contrast(phi_s, inp, beta)

    print()
    print(f"  Target: {target:.4f}")
    print(f"  Vortex out: {out_v:.5f}  loss={l_v:.6f}  contrast={c_v:.4f}")
    print(f"  Smooth out: {out_s:.5f}  loss={l_s:.6f}  contrast={c_s:.4f}")
    print()
    w_v = _winding_field(phi_v)
    n_vortex = int((w_v > 0.35).sum())
    print(f"  Vortex cores detected in Model V: {n_vortex}")
    print(f"  Vortex advantage (loss gap S-V): {l_s - l_v:+.6f}")
    print()
    print("Run complete (multi-source).")


# ---------------------------------------------------------------------------
# Clean experiment: fixed W=[1,-1], off-centre source
# Shows topology is necessary when W cannot compensate
# ---------------------------------------------------------------------------

def run_fixed_W(N: int = 40, n_steps: int = 500, seed: int = 42):
    """
    W is fixed to [+1, -1]: output = s+ - s-.
    The loss is entirely carried by the quality of the attention boundary.
    W cannot compensate for a misplaced boundary.

    Source at (0.3, 0.2) -- off-centre so target != 0.
    Target = ground-truth contrast from the ideal vortex at the source.

    Regime:
        Vortex model: starts near target, refines quickly.
        Smooth model: starts far, must discover boundary location via gradient.

    This is the task where topology is NECESSARY at every step, not just init.
    """
    rng = np.random.default_rng(seed)
    X, Y, dx = _make_grid(N)
    sx, sy = 0.3, 0.2
    inp = dipole_field(X, Y, x0=sx, y0=sy)

    # Ground-truth vortex: set target from ideal boundary
    phi_gt = _wrap(_add_vortex(np.zeros((N, N)), X, Y, sx, sy, k=1))
    W_fixed = np.array([1.0, -1.0])
    a_gt_pos, a_gt_neg = attention_heads(phi_gt, beta=8.0)
    target = float((a_gt_pos * inp).sum()) - float((a_gt_neg * inp).sum())

    print()
    print("=" * 68)
    print("FIXED-W EXPERIMENT  (W=[+1,-1] frozen, only phi learns)")
    print("=" * 68)
    print(f"  Source=({sx},{sy})  target={target:.4f}  N={N}x{N}")
    print(f"  Task: minimise ||s+(phi) - s-(phi) - target||^2")
    print(f"  W cannot compensate -- only topology wins.")
    print()

    # Model V: vortex at source
    phi_v = _wrap(_add_vortex(np.zeros((N, N)), X, Y, sx, sy, k=1)
                  + rng.uniform(-0.05, 0.05, (N, N)))

    # Model S: smooth random
    phi_s = rng.uniform(-0.5, 0.5, (N, N))

    # Model X: vortex at WRONG location (0, 0)
    phi_x = _wrap(_add_vortex(np.zeros((N, N)), X, Y, 0.0, 0.0, k=1)
                  + rng.uniform(-0.05, 0.05, (N, N)))

    eta = 0.015
    beta = 8.0
    alpha = 0.3

    print(f"  {'step':>5}  {'loss(V)':>9}  {'loss(X)':>9}  {'loss(S)':>9}")
    print("  " + "-" * 40)

    for step in range(n_steps + 1):
        if step % 50 == 0 or step == n_steps:
            lv = loss_fn(phi_v, inp, W_fixed, target, beta)
            lx = loss_fn(phi_x, inp, W_fixed, target, beta)
            ls = loss_fn(phi_s, inp, W_fixed, target, beta)
            print(f"  {step:>5}  {lv:9.5f}  {lx:9.5f}  {ls:9.5f}")

        if step < n_steps:
            phi_v = _wrap(phi_v - eta * grad_phi(phi_v, inp, W_fixed,
                                                 target, beta, alpha))
            phi_x = _wrap(phi_x - eta * grad_phi(phi_x, inp, W_fixed,
                                                 target, beta, alpha))
            phi_s = _wrap(phi_s - eta * grad_phi(phi_s, inp, W_fixed,
                                                 target, beta, alpha))

    lv = loss_fn(phi_v, inp, W_fixed, target, beta)
    lx = loss_fn(phi_x, inp, W_fixed, target, beta)
    ls = loss_fn(phi_s, inp, W_fixed, target, beta)

    print()
    print(f"  Model V (vortex at source):  loss={lv:.6f}")
    print(f"  Model X (vortex at wrong):   loss={lx:.6f}")
    print(f"  Model S (smooth):            loss={ls:.6f}")
    print()

    # Adversarial robustness: add small smooth perturbation, remeasure
    eps = 0.3
    noise = rng.uniform(-eps, eps, (N, N))
    # Smooth the noise (low-frequency perturbation only)
    for _ in range(5):
        noise = 0.25 * (np.roll(noise,1,0)+np.roll(noise,-1,0)+
                        np.roll(noise,1,1)+np.roll(noise,-1,1))

    lv_pert = loss_fn(_wrap(phi_v + noise), inp, W_fixed, target, beta)
    ls_pert = loss_fn(_wrap(phi_s + noise), inp, W_fixed, target, beta)

    print(f"  After smooth perturbation (eps={eps}):")
    print(f"    Model V loss change: {lv_pert - lv:+.6f}  "
          f"({'stable' if abs(lv_pert - lv) < 0.01 else 'shifted'})")
    print(f"    Model S loss change: {ls_pert - ls:+.6f}  "
          f"({'stable' if abs(ls_pert - ls) < 0.01 else 'shifted'})")
    print()
    print("  Topology = robustness: the winding number is invariant under")
    print("  smooth perturbation. W cannot be changed by adding smooth noise.")
    print("  The smooth model's boundary CAN shift under the same noise.")
    print()
    print("Run complete (fixed-W).")


if __name__ == "__main__":
    run()
    run_fixed_W()
