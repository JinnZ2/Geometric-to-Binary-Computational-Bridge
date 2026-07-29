"""
Reference implementation for Silicon_Error_Correction v2.0.

Strain-tensor fault detection in diamond-cubic Si. Scope is deliberately
narrow: athermal close-pair recovery only. See
``silicon_error_correction.json`` for the spec and the v1 audit.

WHAT CHANGED FROM v1 AND WHY IT MATTERS HERE
--------------------------------------------
v1 tripped on ``bond angle > 2 deg``. Two degrees IS the thermal noise floor
at 300 K -- Debye-Waller <u^2> ~ 0.006 A^2 gives u_rms 0.0775 A over a
2.352 A bond, so sigma_theta ~ 1.9 deg. A threshold at ~1 sigma false-positives
about a third of the time. Thresholds here are stated in multiples of that
sigma and scale as sqrt(T), so they stay meaningful off room temperature.

v1 also tripped on ``trace deviation > 0.02``. For a strain tensor the trace
is the dilatation dV/V, so that is a 2% volume change and bulk Si fractures
near 1%. The flag raised after the crystal had already failed.

THE BLINDNESS THIS MODULE EXISTS TO DEMONSTRATE
-----------------------------------------------
I1, J2 and J3 are rotation invariants. A pure reorientation of the strain
field leaves all three *exactly* unchanged, so no invariant-based detector
can see it -- and reorientation was the first item in v1's self-healing
list. :func:`frame_misalign_deg` compares principal axes instead, and
``python silicon_check.py`` prints the demonstration: a rotated tensor with
identical invariants to machine precision and a large frame misalignment.

That is falsifier SIL-1 made runnable rather than asserted. It is also the
same lesson as ``Negentropic/triangnet.py``: a spectrum is a scalarisation,
and the orientation is the part it throws away.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Tuple

__all__ = [
    "KB_EV", "IDEAL_BOND_ANGLE_DEG", "CAPTURE_RADIUS_NM",
    "sigma_theta_deg", "invariants", "tau_thermal", "recovery_channel",
    "eigen_symmetric_3x3", "frame_misalign_deg", "check",
]

KB_EV = 8.617333e-5                            # eV/K
IDEAL_BOND_ANGLE_DEG = math.degrees(math.acos(-1.0 / 3.0))   # 109.4712
CAPTURE_RADIUS_NM = 1.5

Matrix = Sequence[Sequence[float]]


def sigma_theta_deg(T: float = 300.0) -> float:
    """Thermal 1-sigma bond-angle spread, degrees.

    ``1.9 * sqrt(T/300)``, from the Debye-Waller displacement over the bond
    length. Any angular threshold must be quoted in multiples of this or it
    is measuring temperature rather than damage.
    """
    if T <= 0.0:
        raise ValueError("temperature must be positive")
    return 1.9 * math.sqrt(T / 300.0)


def invariants(e: Matrix) -> Tuple[float, float, float]:
    """Return ``(I1, J2, J3)`` of a symmetric 3x3 strain tensor.

    * ``I1 = Tr(e)`` -- volumetric (dilatation, dV/V).
    * ``J2 = 1/2 s:s`` -- deviatoric magnitude, where ``s`` is the traceless
      part. Carries strain^2; take the square root before comparing against
      a strain threshold.
    * ``J3 = det(s)`` -- the mode (which kind of shear).

    All three are rotation invariant, which is exactly the limitation
    documented at the top of this module.
    """
    _validate(e)
    I1 = e[0][0] + e[1][1] + e[2][2]
    m = I1 / 3.0
    s = [[e[i][j] - (m if i == j else 0.0) for j in range(3)] for i in range(3)]
    J2 = 0.5 * sum(s[i][j] * s[i][j] for i in range(3) for j in range(3))
    J3 = (s[0][0] * (s[1][1] * s[2][2] - s[1][2] * s[2][1])
          - s[0][1] * (s[1][0] * s[2][2] - s[1][2] * s[2][0])
          + s[0][2] * (s[1][0] * s[2][1] - s[1][1] * s[2][0]))
    return I1, J2, J3


def tau_thermal(T: float = 300.0, Ea: float = 0.45, tau0: float = 1e-13) -> float:
    """Arrhenius vacancy-migration time, seconds. ~3.6 us at 300 K.

    This is the OUT OF SCOPE channel, six orders slower than the ps budget.
    It is here so that anything quoting a picosecond cycle time has to say
    which mechanism it means -- conflating the two was v1's fourth FATAL.
    """
    if T <= 0.0:
        raise ValueError("temperature must be positive")
    return tau0 * math.exp(Ea / (KB_EV * T))


def recovery_channel(separation_nm: float, T: float = 300.0) -> Dict[str, object]:
    """Which recovery mechanism applies to a Frenkel pair at this separation.

    Inside the capture radius, recombination is athermal and effectively
    barrierless -- picoseconds, no activation. Outside it, recovery is
    Arrhenius vacancy migration and is microseconds at best. There is no
    interpolation between them; they are different physics, and the whole
    point of the v2 scope limit is that only the first fits a ps budget.
    """
    if separation_nm < 0.0:
        raise ValueError("separation must be non-negative")
    if separation_nm <= CAPTURE_RADIUS_NM:
        return {"channel": "athermal_close_pair", "barrier_eV": 0.0,
                "timescale_s": 1.5e-12, "in_scope": True}
    return {"channel": "thermal_vacancy_migration", "barrier_eV": 0.45,
            "timescale_s": tau_thermal(T), "in_scope": False}


# ---------------------------------------------------------------------------
# Eigen-decomposition -- what the invariants cannot give you
# ---------------------------------------------------------------------------

def eigen_symmetric_3x3(e: Matrix, iterations: int = 100,
                        tol: float = 1e-16) -> Tuple[List[float], List[List[float]]]:
    """Cyclic Jacobi eigen-decomposition of a symmetric 3x3 matrix.

    Returns ``(eigenvalues, eigenvectors)`` sorted by descending eigenvalue,
    with ``eigenvectors[k]`` the unit axis for ``eigenvalues[k]``.

    Written out rather than imported because this module is stdlib-only and
    the orientation comparison is the one thing here that numpy would
    otherwise be needed for.
    """
    _validate(e)
    a = [[float(e[i][j]) for j in range(3)] for i in range(3)]
    v = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]

    # Convergence is measured RELATIVE to the matrix norm. An absolute
    # tolerance is scale-dependent, and this module is applied to strains of
    # order 1e-4 and to O(1) test matrices in the same run -- an absolute
    # 1e-14 on the off-diagonal sum of squares leaves residuals near 1e-7 for
    # the latter.
    scale = math.sqrt(sum(a[i][j] ** 2 for i in range(3) for j in range(3)))
    if scale == 0.0:
        return [0.0, 0.0, 0.0], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    cutoff = tol * scale

    for _ in range(iterations):
        off = math.sqrt(sum(a[i][j] ** 2
                            for i in range(3) for j in range(3) if i != j))
        if off <= cutoff:
            break
        for p in range(2):
            for q in range(p + 1, 3):
                if abs(a[p][q]) <= cutoff:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(3):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(3):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(3):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - s * vkq
                    v[k][q] = s * vkp + c * vkq

    vals = [a[i][i] for i in range(3)]
    vecs = [[v[r][c] for r in range(3)] for c in range(3)]
    order = sorted(range(3), key=lambda k: vals[k], reverse=True)
    return [vals[k] for k in order], [vecs[k] for k in order]


def frame_misalign_deg(reference: Matrix, measured: Matrix) -> float:
    """Largest angle between corresponding principal axes, degrees.

    THIS is the orientation channel. Invariants cannot supply it: rotate a
    strain field and I1, J2, J3 are unchanged to machine precision while
    this returns the rotation angle.

    Axes are compared up to sign, because an eigenvector and its negation
    describe the same principal direction. Returns a value in [0, 90].
    """
    _, ref_axes = eigen_symmetric_3x3(reference)
    _, meas_axes = eigen_symmetric_3x3(measured)
    worst = 0.0
    for u, w in zip(ref_axes, meas_axes):
        dot = abs(sum(ui * wi for ui, wi in zip(u, w)))
        worst = max(worst, math.degrees(math.acos(max(-1.0, min(1.0, dot)))))
    return worst


# ---------------------------------------------------------------------------
# The check itself
# ---------------------------------------------------------------------------

def check(e: Matrix, theta_deg: float, T: float = 300.0, k: float = 4.0,
          reference: Matrix = None) -> Dict[str, object]:
    """Fault check on a strain tensor and a measured bond angle.

    Parameters
    ----------
    e : 3x3 symmetric strain tensor.
    theta_deg : measured bond angle, degrees.
    T : operating temperature, K. Sets the angular noise floor.
    k : threshold in multiples of thermal sigma. Default 4.0 gives a
        two-sided false-positive rate around 6e-5 per sample, against v1's
        ~32% at its 1-sigma threshold.
    reference : optional reference tensor. Supply it to enable the
        ORIENTATION check; without it that fault class is undetectable and
        the result says so rather than reporting a clean bill.
    """
    I1, J2, J3 = invariants(e)
    sqrtJ2 = math.sqrt(max(J2, 0.0))
    sigma = sigma_theta_deg(T)

    flags: List[str] = []
    if abs(I1) > 2.0e-4:
        flags.append("VOLUMETRIC")
    if sqrtJ2 > 1.0e-4:
        flags.append("DEVIATORIC")
    if abs(theta_deg - IDEAL_BOND_ANGLE_DEG) > k * sigma:
        flags.append("BOND_ANGLE")

    misalign = None
    if reference is not None:
        misalign = frame_misalign_deg(reference, e)
        if misalign > k * sigma:
            flags.append("ORIENTATION")

    return {
        "flags": flags,
        "I1": I1,
        "sqrtJ2": sqrtJ2,
        "J3": J3,
        "sigma_deg": round(sigma, 3),
        "angle_threshold_deg": round(k * sigma, 3),
        "frame_misalign_deg": misalign,
        "tau_thermal_s": tau_thermal(T),
        "orientation_checked": reference is not None,
        "BLIND_TO": (None if reference is not None else
                     "pure reorientation — invariants cannot see it; "
                     "pass reference= to enable the check"),
    }


def _validate(e: Matrix) -> None:
    if len(e) != 3 or any(len(row) != 3 for row in e):
        raise ValueError("strain tensor must be 3x3")
    for i in range(3):
        for j in range(i + 1, 3):
            if abs(e[i][j] - e[j][i]) > 1e-12:
                raise ValueError("strain tensor must be symmetric")


def _rotate_z(e: Matrix, angle_deg: float) -> List[List[float]]:
    """R e R^T about z. Used by the demo to make a pure-orientation fault."""
    c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    R = [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]
    Rt = [[R[j][i] for j in range(3)] for i in range(3)]
    tmp = [[sum(R[i][k] * e[k][j] for k in range(3)) for j in range(3)]
           for i in range(3)]
    return [[sum(tmp[i][k] * Rt[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


if __name__ == "__main__":
    print("Silicon_Error_Correction v2.0 -- reference checks\n")

    print(f"ideal bond angle          {IDEAL_BOND_ANGLE_DEG:.4f} deg")
    for T in (77.0, 300.0, 400.0):
        s = sigma_theta_deg(T)
        print(f"  T={T:5.0f}K   sigma={s:.3f} deg   4-sigma trip={4 * s:.3f} deg"
              f"   tau_thermal={tau_thermal(T):.2e} s")
    print("  v1 tripped at 2.0 deg, which at 300K is ~1 sigma: a false")
    print("  positive on roughly a third of clean samples.\n")

    print("SIL-1: invariants are blind to orientation")
    strain = [[3.0e-4, 0.0, 0.0], [0.0, -1.0e-4, 0.0], [0.0, 0.0, -2.0e-4]]
    rotated = _rotate_z(strain, 30.0)
    i_ref, i_rot = invariants(strain), invariants(rotated)
    print(f"  original   I1={i_ref[0]:+.6e}  J2={i_ref[1]:.6e}  J3={i_ref[2]:+.6e}")
    print(f"  rotated 30 I1={i_rot[0]:+.6e}  J2={i_rot[1]:.6e}  J3={i_rot[2]:+.6e}")
    print(f"  max invariant difference : "
          f"{max(abs(a - b) for a, b in zip(i_ref, i_rot)):.2e}")
    print(f"  frame misalignment       : {frame_misalign_deg(strain, rotated):.2f} deg")
    print("  Identical spectrum, 30 degrees of rotation. Any detector built")
    print("  on invariants alone cannot see this fault at all.\n")

    print("Detection with and without a reference frame")
    blind = check(rotated, IDEAL_BOND_ANGLE_DEG)
    seeing = check(rotated, IDEAL_BOND_ANGLE_DEG, reference=strain)
    print(f"  no reference : flags={blind['flags']}  ({blind['BLIND_TO']})")
    print(f"  reference    : flags={seeing['flags']}  "
          f"misalign={seeing['frame_misalign_deg']:.2f} deg\n")

    print("SIL-2 / SIL-3: recovery channel is set by separation, not by wishing")
    for sep in (0.5, 1.5, 2.0):
        r = recovery_channel(sep)
        print(f"  separation {sep:4.1f} nm -> {r['channel']:26s} "
              f"{r['timescale_s']:.2e} s   in_scope={r['in_scope']}")
    print("  Six orders between the two channels. A single cycle_time_ps")
    print("  cannot describe both, which was v1's fourth FATAL.")
