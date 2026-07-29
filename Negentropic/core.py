"""
Dissipative core -- corrected Kuramoto + overdamped Langevin.

Replaces ``UniversalCore`` (formerly in ``bridge.py``, deleted).  See
``corrections.md`` for the defect list that motivated the rewrite; the
short version is that the old core had an inverted coupling sign, a
missing order-parameter weight, silent output clipping, and emitted
normalised scores whose units did not survive being multiplied together.

This module emits DIMENSIONED quantities and nothing else:

  ``R``      order parameter, dimensionless, [0, 1]
  ``H``      phase-distribution Shannon entropy, nats, [0, ln(bins)]
  ``sigma``  entropy production rate estimate, 1/time (nats per unit time)
  ``w_abs``  cumulative work absorbed from the external drive, phase^2

``H`` is not an exact function of ``R``.  A multimodal phase distribution
can hold ``R`` low while ``H`` stays well below ``ln(bins)``, so the two
decouple, and ``H`` -- not ``R`` -- is the channel that carries diversity.
The old ``D`` slot was the variance of the natural frequencies, which is
fixed at construction and therefore constant along any trajectory; that
constancy is a large part of why every lens in the repository correlated
with every other one (see ``lens_collapse_test.py``).

Stdlib only.  No numpy, no scipy, no matplotlib.

Dynamics
--------
Overdamped Langevin on the phase circle, Ito convention, unit mobility::

    dtheta_i = F_i dt + sqrt(2 Dn) dW_i

    F_i = omega_i + K R sin(psi - theta_i) + A_d sin(Omega_d t - theta_i)

with ``(R, psi)`` the Kuramoto order parameter.  The mean-field term
carries the sign and the ``R`` weight of the standard Kuramoto model:
attractive, vanishing when the population is incoherent.

Entropy production
------------------
``sigma = sum_i F_i^2 / (2 Dn)`` is the housekeeping (mean-velocity)
estimator: it approximates the local mean velocity by the drift ``F`` and
so drops the ``-Dn d/dtheta ln P`` contribution.  It is an estimator with
a known sign bias, not the exact entropy production rate, and it is
reported in nats per unit time.  Multiply by ``k_B`` to reach W/K -- see
``persistence.sigma_to_watts_per_kelvin``.

The drive term makes this a *driven* system, which is the setting
dissipative adaptation actually talks about: structure is selected by the
drive it has absorbed work from, so ``w_abs`` is a path functional and
belongs in the trace next to the state variables.  See
``07-thermodynamics.md``.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Tuple

TWO_PI = 2.0 * math.pi

__all__ = [
    "DissipativeCore",
    "TWO_PI",
    "wrap_phase",
    "phase_alignment",
    "distance_kernel",
]


# ---------------------------------------------------------------------------
# Coupling kernels
#
# The framework had one kernel, ``0.5 * (cos(d) + 1)``, applied to two
# different kinds of argument.  On a signed phase difference that is
# correct.  On a Euclidean distance ``d = ||p_i - p_j|| >= 0`` it is not:
# cosine wraps, so ``d = 0``, ``2*pi`` and ``4*pi`` all score 1.0 and
# maximally distant agents read as maximally coherent.  Two arguments, two
# kernels.
# ---------------------------------------------------------------------------

def wrap_phase(delta: float) -> float:
    """Wrap a phase difference into (-pi, pi]."""
    wrapped = (delta + math.pi) % TWO_PI - math.pi
    return math.pi if wrapped == -math.pi else wrapped


def phase_alignment(delta: float) -> float:
    """Raised-cosine alignment of a signed *phase* difference, in [0, 1].

    1.0 when the phases coincide, 0.0 when they are antiphase.  The argument
    is wrapped first, so this is single-valued on the circle -- which is the
    only domain where a cosine kernel means anything.
    """
    return 0.5 * (math.cos(wrap_phase(delta)) + 1.0)


def distance_kernel(distance: float, scale: float = 1.0) -> float:
    """Monotone coupling kernel for a non-negative *distance*, in (0, 1].

    ``exp(-distance / scale)``.  Strictly decreasing and strictly positive,
    so it neither wraps nor sends a log-geometric mean to negative infinity
    the moment one pair of agents drifts apart.
    """
    if distance < 0.0:
        raise ValueError("distance must be non-negative")
    if scale <= 0.0:
        raise ValueError("scale must be positive")
    return math.exp(-distance / scale)


class DissipativeCore:
    """Coupled phase oscillators with noise, an optional drive, and honest units.

    Parameters
    ----------
    n : int
        Number of oscillators.
    K : float
        Mean-field coupling strength, 1/time.
    Dn : float
        Phase diffusion coefficient, phase^2/time.  Must be > 0; it appears
        in the denominator of the entropy production estimator.
    dt : float
        Integration step, time.
    bins : int
        Histogram resolution for the phase entropy.  ``H`` is bounded above
        by ``ln(bins)``, so this sets the ceiling of the diversity channel.
    drive_amp, drive_freq : float
        Amplitude (1/time) and angular frequency (1/time) of an external
        periodic drive.  Zero amplitude recovers the undriven model.
    seed : int, optional
        Seed for the internal RNG.  The RNG is per-instance, so two cores
        with the same seed produce identical trajectories regardless of
        global random state.
    """

    def __init__(
        self,
        n: int = 50,
        K: float = 1.5,
        Dn: float = 0.045,
        dt: float = 0.02,
        bins: int = 24,
        drive_amp: float = 0.0,
        drive_freq: float = 0.0,
        seed: Optional[int] = 0,
    ) -> None:
        if n < 2:
            raise ValueError("n must be at least 2")
        if Dn <= 0.0:
            raise ValueError("Dn must be positive (it divides the entropy production)")
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        if bins < 2:
            raise ValueError("bins must be at least 2")

        self.n = n
        self.K = K
        self.Dn = Dn
        self.dt = dt
        self.bins = bins
        self.drive_amp = drive_amp
        self.drive_freq = drive_freq

        self.rng = random.Random(seed)
        self.omega = [self.rng.gauss(0.0, 1.0) for _ in range(n)]
        self.theta = [self.rng.uniform(-math.pi, math.pi) for _ in range(n)]

        self.t = 0.0
        self.w_abs = 0.0  # cumulative work absorbed from the drive

    # -- observables ------------------------------------------------------

    def order(self) -> Tuple[float, float]:
        """Kuramoto order parameter ``(R, psi)``.

        ``R`` is dimensionless in [0, 1]; ``psi`` is the mean phase in
        (-pi, pi].  Nothing downstream may take a power of ``psi`` -- it
        wraps, so any quantity quadratic in ``psi`` jumps discontinuously
        at the branch cut.  That was one of the defects in the old core.
        """
        c = sum(math.cos(t) for t in self.theta) / self.n
        s = sum(math.sin(t) for t in self.theta) / self.n
        return math.hypot(c, s), math.atan2(s, c)

    def entropy(self) -> float:
        """Shannon entropy of the binned phase distribution, in nats.

        Range [0, ln(bins)].  Zero when every oscillator sits in one bin.
        """
        counts = [0] * self.bins
        for t in self.theta:
            idx = int(((t + math.pi) % TWO_PI) / TWO_PI * self.bins) % self.bins
            counts[idx] += 1
        h = 0.0
        for k in counts:
            if k:
                p = k / self.n
                h -= p * math.log(p)
        return h

    # -- dynamics ---------------------------------------------------------

    def step(self) -> Dict[str, float]:
        """Advance one Euler-Maruyama step and return the observables.

        The returned ``R`` and ``H`` describe the state *before* the update;
        ``sigma`` and ``dw`` describe the transition just taken.
        """
        R, psi = self.order()
        H = self.entropy()
        amp = math.sqrt(2.0 * self.Dn * self.dt)

        forces: List[float] = []
        drive_forces: List[float] = []
        new_theta: List[float] = []

        for i in range(self.n):
            f_drive = 0.0
            if self.drive_amp:
                f_drive = self.drive_amp * math.sin(
                    self.drive_freq * self.t - self.theta[i]
                )
            # Attractive, R-weighted mean field: K R sin(psi - theta_i).
            f = self.omega[i] + self.K * R * math.sin(psi - self.theta[i]) + f_drive
            forces.append(f)
            drive_forces.append(f_drive)
            new_theta.append(self.theta[i] + f * self.dt + amp * self.rng.gauss(0.0, 1.0))

        # Work absorbed from the drive: f_drive * dtheta, summed over the
        # population.  Path functional, not a state variable.
        dw = sum(
            fd * (new - old)
            for fd, new, old in zip(drive_forces, new_theta, self.theta)
        )
        self.w_abs += dw

        self.theta = new_theta
        self.t += self.dt

        sigma = sum(f * f for f in forces) / (2.0 * self.Dn)
        return {"t": self.t, "R": R, "H": H, "sigma": sigma, "dw": dw, "w_abs": self.w_abs}

    def run(self, steps: int = 300, burn_in: int = 100) -> List[Dict[str, float]]:
        """Burn in, reset the work accumulator, then record ``steps`` samples."""
        for _ in range(burn_in):
            self.step()
        self.w_abs = 0.0
        return [self.step() for _ in range(steps)]

    # -- legacy adapter ---------------------------------------------------

    def legacy_rad_trace(
        self,
        steps: int = 250,
        burn_in: int = 80,
        noise_amp: Optional[float] = None,
        clip: bool = False,
    ) -> List[Tuple[float, float, float, float]]:
        """Emit the old ``(R, A, D, L)`` 4-tuples the lens layer was built on.

        This exists for one purpose: ``lens_collapse_test.py`` has to test
        the isomorphism claim against the quantities the claim was actually
        made about.  Do not build anything new on these numbers.  Three of
        them are known to be defective:

        * ``D`` is ``var(omega)``, fixed at construction, so it is constant
          along the whole trajectory.
        * ``A`` is an affine function of ``R`` alone, so it carries no
          information ``R`` does not already carry.
        * ``L`` is quadratic in ``omega - psi``, and ``psi`` wraps at +-pi,
          so ``L`` jumps at the branch cut.

        Parameters
        ----------
        noise_amp : float, optional
            Legacy noise amplitude entering ``L``.  Defaults to
            ``sqrt(2 Dn)`` so the two parameterisations line up.
        clip : bool
            Reproduce the old ``min(A, 1.0)`` / ``min(L, 2.0)`` saturation.
            Off by default: saturated runs turn into constants, which
            inflates every correlation computed downstream.
        """
        if noise_amp is None:
            noise_amp = math.sqrt(2.0 * self.Dn)

        mean_omega = sum(self.omega) / self.n
        var_omega = sum((w - mean_omega) ** 2 for w in self.omega) / self.n
        std_omega = math.sqrt(var_omega)

        for _ in range(burn_in):
            self.step()

        trace: List[Tuple[float, float, float, float]] = []
        for _ in range(steps):
            R, psi = self.order()
            a = std_omega * (1.0 - R) + 0.1
            d = var_omega
            kinetic = sum((w - psi) ** 2 for w in self.omega) / self.n
            loss = noise_amp ** 2 + 0.2 * kinetic
            if clip:
                a = min(a, 1.0)
                loss = min(loss, 2.0)
            trace.append((R, a, d, loss))
            self.step()
        return trace


if __name__ == "__main__":
    core = DissipativeCore(n=50, K=1.5, Dn=0.045, dt=0.02, seed=7)
    trace = core.run(steps=200, burn_in=100)
    first, last = trace[0], trace[-1]
    print("DissipativeCore -- undriven")
    print(f"  R:     {first['R']:.4f} -> {last['R']:.4f}   (dimensionless)")
    print(f"  H:     {first['H']:.4f} -> {last['H']:.4f}   nats, ceiling {math.log(24):.4f}")
    print(f"  sigma: {first['sigma']:.2f} -> {last['sigma']:.2f}   1/time")

    driven = DissipativeCore(n=50, K=1.5, Dn=0.045, dt=0.02,
                             drive_amp=0.8, drive_freq=1.0, seed=7)
    dtrace = driven.run(steps=200, burn_in=100)
    print("\nDissipativeCore -- driven at Omega_d = 1.0")
    print(f"  R:     {dtrace[-1]['R']:.4f}")
    print(f"  w_abs: {dtrace[-1]['w_abs']:.4f}   absorbed work (path functional)")
