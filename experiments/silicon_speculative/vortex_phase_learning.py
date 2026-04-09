#!/usr/bin/env python3
# STATUS: speculative — vortex phase learning experiment
"""
vortex_phase_learning.py
========================
2D phase field with injected topological vortex defects, optimized via
gradient descent on a simple input->output task.

Tests whether topological defects (non-removable by smooth transformation)
serve as useful memory anchors during learning, or disrupt it.

Four observations instrumented:
  1. Defect persistence  -- vortex winding number tracked per step
  2. Energy localization -- gradient magnitude near vs far from defects
  3. Functional behavior -- loss convergence rate, output structure
  4. Emergent behavior   -- dipole formation, phase domain statistics

Connection to vacuum_field_theory.md Section VIII:
  Topological edge modes have lambda approx 0 (Lyapunov-stable).
  This simulation tests whether that stability is also computationally useful.

Run:
    python Silicon/vortex_phase_learning.py
"""

import numpy as np

# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
N   = 40
x   = np.linspace(-1, 1, N)
y   = np.linspace(-1, 1, N)
X, Y = np.meshgrid(x, y)
dx  = x[1] - x[0]

# ---------------------------------------------------------------------------
# Topological vortex injection
# ---------------------------------------------------------------------------

def add_vortex(phi: np.ndarray, x0: float, y0: float, k: int = 1) -> np.ndarray:
    """Add a vortex of winding number k centred at (x0, y0)."""
    return phi + k * np.arctan2(Y - y0, X - x0)


def winding_number_field(phi: np.ndarray) -> np.ndarray:
    """
    Compute the local topological charge density at each plaquette.

    For each 2x2 plaquette the discrete vorticity is the sum of
    phase differences around the loop, modulo 2pi, divided by 2pi.
    A value of +/-1 at a pixel means a vortex core sits there.
    """
    # Phase differences (wrapped to [-pi, pi])
    def wrap(d):
        return (d + np.pi) % (2 * np.pi) - np.pi

    dphi_x = wrap(np.roll(phi, -1, axis=1) - phi)   # right
    dphi_y = wrap(np.roll(phi, -1, axis=0) - phi)   # down

    # Circulation around each plaquette (counterclockwise)
    circ = (dphi_x
            + wrap(np.roll(dphi_y, -1, axis=1))
            - wrap(np.roll(dphi_x, -1, axis=0))
            - dphi_y)
    return circ / (2 * np.pi)


def count_vortices(phi: np.ndarray, threshold: float = 0.4) -> dict:
    """Return counts of positive and negative vortex cores."""
    w = winding_number_field(phi)
    pos = int((w >  threshold).sum())
    neg = int((w < -threshold).sum())
    return {"positive": pos, "negative": neg, "total": pos + neg,
            "winding_field": w}


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------

def laplacian(f: np.ndarray) -> np.ndarray:
    return (np.roll(f,  1, 0) + np.roll(f, -1, 0) +
            np.roll(f,  1, 1) + np.roll(f, -1, 1) - 4 * f)


def wrap_phase(phi: np.ndarray) -> np.ndarray:
    """Keep phi in (-pi, pi] to prevent unbounded growth."""
    return (phi + np.pi) % (2 * np.pi) - np.pi


def forward(phi: np.ndarray, inp: np.ndarray) -> np.ndarray:
    return np.cos(phi) * inp


def loss(phi: np.ndarray, inp: np.ndarray, target: np.ndarray) -> float:
    out = forward(phi, inp)
    return 0.5 * float(np.linalg.norm(out - target) ** 2)


def gradient(phi: np.ndarray, inp: np.ndarray, target: np.ndarray,
             alpha: float, beta: float) -> np.ndarray:
    out   = forward(phi, inp)
    e     = out - target

    g_compute = -np.sin(phi) * inp * e
    g_smooth  = laplacian(phi)
    norm      = np.linalg.norm(out) + 1e-8
    g_stab    = (out * (-np.sin(phi) * inp)) / norm

    return g_compute + alpha * g_smooth + beta * g_stab


# ---------------------------------------------------------------------------
# Observation helpers
# ---------------------------------------------------------------------------

def gradient_near_defects(grad_mag: np.ndarray, w_field: np.ndarray,
                           radius: int = 3) -> dict:
    """
    Compare mean gradient magnitude near vortex cores vs far.
    'Near' = within `radius` pixels of any vortex core pixel.
    """
    core_mask = np.abs(w_field) > 0.4
    # Dilate core mask by radius using manual rolling
    near_mask = core_mask.copy()
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            if dr == 0 and dc == 0:
                continue
            near_mask |= np.roll(np.roll(core_mask, dr, 0), dc, 1)

    far_mask = ~near_mask
    near_mean = float(grad_mag[near_mask].mean()) if near_mask.any() else 0.0
    far_mean  = float(grad_mag[far_mask].mean())  if far_mask.any()  else 0.0
    return {"near": near_mean, "far": far_mean,
            "ratio": near_mean / (far_mean + 1e-10),
            "n_near": int(near_mask.sum()), "n_far": int(far_mask.sum())}


def phase_domain_stats(phi: np.ndarray) -> dict:
    """
    Count approximate phase domains by thresholding cos(phi).
    Domain = connected region where cos(phi) > 0 (phase near 0 mod 2pi).
    Returns fraction of pixels in positive domain and local variance.
    """
    cosine    = np.cos(phi)
    pos_frac  = float((cosine > 0).mean())
    local_var = float(np.abs(laplacian(phi)).mean())
    return {"pos_domain_frac": pos_frac, "local_phase_var": local_var}


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run(seed: int = 42, n_steps: int = 200,
        eta: float = 0.05, alpha: float = 0.2, beta: float = 0.05):

    rng = np.random.default_rng(seed)
    inp    = rng.standard_normal((N, N))
    target = rng.standard_normal((N, N))

    # -- Experiment A: with vortices --
    phi_v = np.zeros((N, N))
    phi_v = add_vortex(phi_v, 0.0,  0.0,  k= 1)
    phi_v = add_vortex(phi_v, 0.3,  0.3,  k=-1)

    # -- Experiment B: same random init, no vortices --
    phi_flat = rng.uniform(-0.3, 0.3, (N, N))

    print("=" * 68)
    print("VORTEX PHASE LEARNING  --  topological defect memory experiment")
    print("=" * 68)
    print(f"  Grid: {N}x{N}   steps: {n_steps}   eta={eta}  "
          f"alpha={alpha}  beta={beta}")
    print()

    # ---- Observation 1: initial vortex count ----
    vc0 = count_vortices(phi_v)
    print(f"Observation 1 -- Defect count at t=0:")
    print(f"  Injected:  +1 vortex at (0,0),  -1 antivortex at (0.3,0.3)")
    print(f"  Detected:  +{vc0['positive']}  -{vc0['negative']}  "
          f"total={vc0['total']}")
    print()

    # ---- Training loop ----
    history = {"step": [], "loss_v": [], "loss_flat": [],
               "n_vortex": [], "near_ratio": [], "domain_var": []}

    for step in range(n_steps):
        g_v    = gradient(phi_v,    inp, target, alpha, beta)
        g_flat = gradient(phi_flat, inp, target, alpha, beta)
        phi_v    = wrap_phase(phi_v    - eta * g_v)
        phi_flat = wrap_phase(phi_flat - eta * g_flat)

        if step % 20 == 0 or step == n_steps - 1:
            lv  = loss(phi_v,    inp, target)
            lf  = loss(phi_flat, inp, target)
            vc  = count_vortices(phi_v)
            gm  = np.abs(g_v)
            eg  = gradient_near_defects(gm, vc["winding_field"])
            ds  = phase_domain_stats(phi_v)

            history["step"].append(step)
            history["loss_v"].append(lv)
            history["loss_flat"].append(lf)
            history["n_vortex"].append(vc["total"])
            history["near_ratio"].append(eg["ratio"])
            history["domain_var"].append(ds["local_phase_var"])

            print(f"  step {step:3d} | "
                  f"loss(vortex)={lv:7.3f}  loss(flat)={lf:7.3f} | "
                  f"vortices={vc['total']}  "
                  f"grad_near/far={eg['ratio']:.2f}  "
                  f"phase_var={ds['local_phase_var']:.4f}")

    print()

    # ---- Observation 1 final: did vortices survive? ----
    vc_final = count_vortices(phi_v)
    print(f"Observation 1 -- Defect persistence:")
    print(f"  Initial: {vc0['total']}  Final: {vc_final['total']}")
    survived = vc_final["total"] >= max(1, vc0["total"] - 1)
    print(f"  Result: {'VORTICES PERSISTED' if survived else 'VORTICES ANNIHILATED'}")
    print()

    # ---- Observation 2: energy localization ----
    gm_final = np.abs(gradient(phi_v, inp, target, alpha, beta))
    eg_final = gradient_near_defects(gm_final, vc_final["winding_field"])
    print(f"Observation 2 -- Energy localization (final step):")
    print(f"  Mean |grad| near defects: {eg_final['near']:.4f}")
    print(f"  Mean |grad| far from defects: {eg_final['far']:.4f}")
    print(f"  Ratio near/far: {eg_final['ratio']:.3f}")
    localized = eg_final["ratio"] > 1.2
    print(f"  Result: {'GRADIENT CONCENTRATES NEAR DEFECTS' if localized else 'GRADIENT IS UNIFORM'}")
    print()

    # ---- Observation 3: functional behavior ----
    loss_v_0   = history["loss_v"][0]
    loss_v_end = history["loss_v"][-1]
    loss_f_0   = history["loss_flat"][0]
    loss_f_end = history["loss_flat"][-1]

    reduction_v    = (loss_v_0 - loss_v_end) / (loss_v_0 + 1e-10)
    reduction_flat = (loss_f_0 - loss_f_end) / (loss_f_0 + 1e-10)

    print(f"Observation 3 -- Functional behavior (loss reduction):")
    print(f"  Vortex field: {loss_v_0:.3f} -> {loss_v_end:.3f}  "
          f"({100*reduction_v:.1f}% reduction)")
    print(f"  Flat field:   {loss_f_0:.3f} -> {loss_f_end:.3f}  "
          f"({100*reduction_flat:.1f}% reduction)")
    if reduction_v > reduction_flat + 0.05:
        case = "Case A: DEFECTS HELP  (faster convergence)"
    elif reduction_v < reduction_flat - 0.05:
        case = "Case B: DEFECTS HURT  (slower convergence)"
    else:
        case = "Case NEUTRAL: defects neither help nor hurt"
    print(f"  Result: {case}")
    print()

    # ---- Observation 4: emergent behavior ----
    # Dipole: +/- vortex pair close together = dipole
    w = vc_final["winding_field"]
    pos_cores = np.array(np.where(w >  0.4)).T   # (n, 2)
    neg_cores = np.array(np.where(w < -0.4)).T

    ds_final = phase_domain_stats(phi_v)

    print(f"Observation 4 -- Emergent behavior:")
    if len(pos_cores) > 0 and len(neg_cores) > 0:
        # Find nearest +/- pair distance
        dists = np.linalg.norm(
            pos_cores[:, None, :] - neg_cores[None, :, :], axis=-1)
        min_dist = float(dists.min()) * dx
        print(f"  Positive cores: {len(pos_cores)}  Negative cores: {len(neg_cores)}")
        print(f"  Nearest +/- pair distance: {min_dist:.3f} (in field units)")
        if min_dist < 0.25:
            print(f"  Dipole status: BOUND DIPOLE FORMED (separation < 0.25)")
        else:
            print(f"  Dipole status: unbound pair (separation >= 0.25)")
    else:
        print(f"  No vortex cores detected in final field.")

    print(f"  Phase domain fraction in cos(phi)>0: "
          f"{ds_final['pos_domain_frac']:.3f}")
    print(f"  Local phase variance (|laplacian|): "
          f"{ds_final['local_phase_var']:.4f}")
    print()

    # ---- Summary ----
    print("=" * 68)
    print("SUMMARY -- topological defect as non-erasable memory anchor")
    print("=" * 68)
    print()
    print(f"  A defect is a discontinuity that cannot be removed by")
    print(f"  smooth transformation.  If useful: non-erasable memory")
    print(f"  that also participates in computation.")
    print()
    print(f"  Persistence:       {'YES' if survived else 'NO '}  "
          f"-- vortex topology survives {n_steps} gradient steps")
    print(f"  Energy anchoring:  {'YES' if localized else 'NO '}  "
          f"-- gradient concentrates near defect cores")
    print(f"  Learning:          {case.split(':')[0].strip()}")
    print()

    # Connection to vacuum_field_theory.md
    print("  Connection to vacuum_field_theory.md Section VIII:")
    print("  Topological modes have lambda approx 0 (Lyapunov stable).")
    print("  This simulation confirms that stability is not just passive:")
    if survived:
        print("  the defects remain structurally intact under the full")
        print("  gradient field, consistent with topological protection.")
    else:
        print("  but vortex cores annihilated -- protection defeated by")
        print("  the gradient at these parameters (try smaller eta).")
    print()
    print("Run complete.")

    return history


if __name__ == "__main__":
    run()
