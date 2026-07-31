"""Lyapunov-filtered vacuum energy: VAC-1..4.

Settles the arithmetic in ``vacuum_geff_sim.py``. The suite there reports three
"Tests passed" assertions. All three pass for random matrices.

VAC-1 -- THE SURVIVAL TEST IS A STRICT TAUTOLOGY
------------------------------------------------
``lam = ln(|mu| / rho)`` with ``rho = max|mu|``, so the dominant mode has
``|mu| = rho`` and ``lam = ln(1) = 0`` exactly, for **any** matrix whatsoever.
The filter admits modes with ``|lam| < epsilon``, so at least one mode always
survives. "At least one mode survives" cannot fail.

The other two assertions are nearly as weak. ``E_eff < E_raw`` is a subset-sum
of positive numbers, and ``surviving_frac < 1`` fails only when every ``|mu|``
is equal -- the identity matrix. No real coupling matrix is degenerate that
way. So the suite validates the arithmetic of ``ln`` and a subset sum; random
noise passes it. Same shape as NEG-7: random inputs reproduce the result.

VAC-4 -- AND NO EXPONENTIAL SUPPRESSION IS AVAILABLE AT ALL
-----------------------------------------------------------
Not in the audit, and it is stronger than the mode-count argument. Because the
dominant mode always survives, ``E_eff >= omega_max``, so

    E_eff / E_raw  >=  omega_max / sum(omega)  >  0

and with ``omega_n = |mu_n|/rho <= 1`` that floor is at best ``1/N``. The
suppression is a ratio of positive numbers with a hard positive floor: the
functional form cannot produce exponential suppression, at any lattice size.

VAC-2 -- 30 MODES CANNOT REACH 1e-120
--------------------------------------
The minimum nonzero surviving fraction is ``1/N``:

    5 shells        N = 30        3.3e-02
    100 shells      N = 600       1.7e-03
    1,000,000 shells N = 6e6      1.7e-07

Reaching 1e-120 needs ``N >= 1e120`` modes, i.e. ~1.7e119 shells. The gap from
the 30-mode floor is 119 orders. "Requires a physical mapping of lattice units
to eV" does not close it: the binding constraint is the mode COUNT, which is
combinatorial, not a unit conversion.

VAC-3 -- DIMENSIONS AND DENSITY OF STATES
-----------------------------------------
``omega_n = |mu_n| / rho`` is a normalised eigenvalue: dimensionless, in (0,1].
For an oscillator system ``omega = sqrt(eigenvalue)`` of the dynamical matrix
and ``E_vac = sum (1/2) hbar omega``. "E_vac = sum omega" is a sum of
dimensionless numbers.

And ``g(omega) ~ omega^2`` is a continuum 3D result from counting k-states in a
sphere. Thirty eigenvalues histogrammed into forty bins is not a density of
states.

Finally, "measure the spectral gap as a function of xi" measures the simulation
against its own parameter. That is evaluating a function, not testing it.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

__all__ = [
    "EPSILON_DEFAULT", "lyapunov_spectrum", "run_suite", "assertion_report",
    "suppression_floor", "modes_for_suppression", "shells_for_suppression",
    "reference_matrices", "main",
]

EPSILON_DEFAULT = 0.15


def lyapunov_spectrum(K, eps: float = 1e-300):
    """``(mu, lam, omega)`` with ``lam = ln(|mu|/rho)``, ``omega = |mu|/rho``."""
    K = np.asarray(K, dtype=float)
    if K.ndim != 2 or K.shape[0] != K.shape[1]:
        raise ValueError("need a square matrix")
    mu = np.linalg.eigvalsh((K + K.T) / 2.0)
    rho = float(np.max(np.abs(mu)))
    if rho <= 0.0:
        raise ValueError("matrix has no nonzero eigenvalue")
    omega = np.abs(mu) / rho
    return mu, np.log(omega + eps), omega


def run_suite(K, epsilon: float = EPSILON_DEFAULT) -> Dict[str, object]:
    """The three assertions, plus the numbers behind them."""
    mu, lam, omega = lyapunov_spectrum(K)
    surviving = np.abs(lam) < epsilon
    e_raw = float(omega.sum())
    e_eff = float(omega[surviving].sum())
    return {
        "n_modes": int(omega.size),
        "max_lambda": float(lam.max()),
        "E_raw": e_raw, "E_eff": e_eff,
        "suppression": e_eff / e_raw,
        "surviving_frac": float(surviving.mean()),
        "assert_energy_reduced": e_eff < e_raw,
        "assert_frac_below_one": float(surviving.mean()) < 1.0,
        "assert_one_survives": int(surviving.sum()) >= 1,
    }


def assertion_report(matrices: Optional[Dict[str, object]] = None,
                     epsilon: float = EPSILON_DEFAULT) -> List[Dict[str, object]]:
    """Run the suite across a set of matrices, tautologies exposed."""
    if matrices is None:
        matrices = reference_matrices()
    out = []
    for name, K in matrices.items():
        r = run_suite(K, epsilon)
        r["matrix"] = name
        out.append(r)
    return out


def reference_matrices(n: int = 30, seed: int = 0) -> Dict[str, np.ndarray]:
    """Matrices that are emphatically not phi-lattices."""
    if n < 2:
        raise ValueError("need at least a 2x2")
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(n)
    raw = {
        "random gaussian": rng.standard_normal((n, n)),
        "random uniform [0,1]": rng.random((n, n)),
        "diag(1..n)": np.diag(np.arange(1.0, n + 1)),
        "random rank-1 outer(v,v)": np.outer(v, v),
        "all-ones": np.ones((n, n)),
        "identity": np.eye(n),
    }
    return {k: (m + m.T) / 2.0 for k, m in raw.items()}


def suppression_floor(n_modes: int) -> float:
    """``1/N`` -- the best the mechanism can do, since one mode always survives."""
    if n_modes < 1:
        raise ValueError("need at least one mode")
    return 1.0 / n_modes


def modes_for_suppression(target: float) -> float:
    """Modes needed to reach a target suppression. 1e120 for 1e-120."""
    if not 0.0 < target < 1.0:
        raise ValueError("target must lie in (0, 1)")
    return 1.0 / target


def shells_for_suppression(target: float, modes_per_shell: int = 6) -> float:
    if modes_per_shell < 1:
        raise ValueError("need at least one mode per shell")
    return modes_for_suppression(target) / modes_per_shell


def main() -> None:
    print("LYAPUNOV-FILTERED VACUUM ENERGY\n" + "=" * 74)
    print("\nVAC-1/VAC-3  the suite, run on matrices that are not phi-lattices")
    print(f"  {'matrix':<26}{'E<E':>6}{'f<1':>6}{'>=1':>6}"
          f"{'supp':>10}{'surv':>8}{'max lam':>11}")
    for r in assertion_report():
        print(f"  {r['matrix']:<26}{str(r['assert_energy_reduced']):>6}"
              f"{str(r['assert_frac_below_one']):>6}"
              f"{str(r['assert_one_survives']):>6}"
              f"{r['suppression']:>10.6f}{r['surviving_frac']:>8.3f}"
              f"{r['max_lambda']:>11.2e}")
    print("\n  max lam == 0 in EVERY row, exactly: lam = ln(|mu|/rho) and the")
    print("  dominant mode has |mu| = rho, so lam = ln(1) = 0. By construction.")
    print("  'at least one mode survives' is a STRICT TAUTOLOGY.")
    print("  'E_eff < E_raw' is a subset sum of positives; 'frac < 1' fails")
    print("  only for the identity, where every |mu| is equal.")

    print("\nVAC-4  no exponential suppression is available at all")
    r = run_suite(reference_matrices()["random gaussian"])
    print("  the dominant mode always survives, so E_eff >= omega_max and")
    print("  suppression >= omega_max/sum(omega). For this matrix that floor")
    print(f"  is {1.0 / r['n_modes']:.4f} at best (1/N), measured "
          f"{r['suppression']:.4f}.")

    print("\nVAC-2  mode count against the 1e-120 target")
    for shells, n in ((5, 30), (100, 600), (1_000_000, 6_000_000)):
        print(f"  {shells:>11,} shells   N = {n:>10,}   floor "
              f"{suppression_floor(n):.1e}")
    print(f"  1e-120 needs N >= {modes_for_suppression(1e-120):.0e} modes "
          f"= {shells_for_suppression(1e-120):.1e} shells")
    print(f"  gap from the 30-mode floor: "
          f"{math.log10(suppression_floor(30) / 1e-120):.0f} orders")
    print("  the binding constraint is the mode COUNT, which is combinatorial.")
    print("  a physical mapping of lattice units to eV does not close it.")

    print("\nVAC-3  units")
    print("  omega_n = |mu_n|/rho is dimensionless, in (0,1].")
    print("  for oscillators omega = sqrt(eigenvalue) and E_vac = sum (1/2) h w.")
    print("  'E_vac = sum omega' sums dimensionless numbers.")
    print("  g(omega) ~ omega^2 is a continuum 3D k-space count; 30 eigenvalues")
    print("  in 40 bins is not a density of states.")


if __name__ == "__main__":
    main()
