"""
FP-4 autopilot: the one field-propulsion measurement that can return "no".

Runs the discriminating test from ``field_propulsion_protocol.md`` §5 and the
Bridge communication test from §9.1. Talks to ``field_propulsion_fp4.ino``, or
to a built-in simulator when no hardware is attached.

WHAT THIS MEASURES
------------------
Not a phase sweep. The test is a regression::

    F  =  k * (P_rad / v)  +  c * P_elec  +  b

* ``k`` is the anomaly factor. ``F <= P_rad/v`` is momentum conservation, so
  H0 predicts ``k <= 1`` and H1 requires ``k > margin``. This is the whole
  claim, in one slope.
* ``c`` absorbs confounders that scale with *electrical* power rather than
  radiated power -- thermal plume, ohmic heating, convection. These are the
  most common false positives in thrust measurement.
* ``b`` absorbs amplitude-independent offsets: balance drift, electrostatic
  pull toward nearby surfaces, mount preload.

Ratios are NOT averaged. ``mean(F/(P/v))`` is a biased estimator and blows up
whenever ``P`` is small. The slope of a regression through many operating
points uses all the data and has an honest confidence interval.

THE DESIGN CONSTRAINT THAT MAKES OR BREAKS THIS
-----------------------------------------------
Sweeping drive amplitude alone does not work, and this module's own self-test
is what established that. On a fixed driver, ``P_rad = eta * P_elec`` with
``eta`` constant, so the two regressors are collinear to within power-meter
noise: measured ``corr = 0.996``, ``VIF = 134``. In that design an anomaly of
``k = 4`` was absorbed almost entirely by ``c`` (fitted 2.56e-4 N/W, which is
the 2.33e-4 anomaly plus the 2.0e-5 real thermal term) and ``k`` came back
as ``-0.06 +- 0.09`` -- a *confident* NULL on a world where H1 was true.
False-negative rate 40/40.

Worse, the noise is on the regressor ``P_rad``, so errors-in-variables pulls
``k`` toward zero on top of the collinearity. Both failures point the same
way, which is why the wrong answer looked precise.

The fix is physical. The campaign must contain operating points where
radiated power is decoupled from electrical power:

* ``open``    -- normal radiation, ``eta`` at its full value
* ``detuned`` -- driven off resonance, or into a mismatched load: same
                 electrical draw, a fraction of the radiated power
* ``muted``   -- acoustically blocked (absorber cap, sealed enclosure) so
                 ``P_rad -> 0`` while ``P_elec`` is unchanged

The muted point is the classical thrust-balance control and it is what makes
``c`` and ``b`` identifiable from data rather than from assumption. A real
muted control has to be *verified* to draw the same electrical power as the
open state; if blocking the output changes the driver's impedance enough to
change ``P_elec``, it is not a control, and the fitted ``c`` will be wrong in
a direction nobody can sign. Measure ``P_elec`` in every state and report it.

``fit_thrust_model`` computes the variance-inflation factor for ``k`` and
marks the fit non-identifiable when the design cannot separate the two terms.
``verdict_from_fit`` then returns ``NON-IDENTIFIABLE`` instead of a confident
NULL. A design that cannot answer should say so, not answer wrongly.

WHY THERE IS A SELF-TEST IN HERE
--------------------------------
``ASIS/README.md`` records the rule this repository arrived at after finding
the same defect three times:

    Before trusting an autopilot, run it against a world where the null is
    true. If H0 does not win there, the loop is not measuring the world.

The corollary earned here: it must also *lose* on a world where the null is
false. ``null_world_test()`` runs both directions and reports both error
rates. It runs before any real measurement, and if it does not pass, the
autopilot refuses to report a verdict on data.

The simulator is deliberately not handed the answer: ``_Simulator`` holds its
own ``anomaly_factor`` and the fitter never sees it.

Stdlib only. Serial I/O is optional and imported lazily.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence

__all__ = [
    "C_AIR", "RADIATION_STATES", "MAX_VIF", "Trial", "variance_inflation",
    "fit_thrust_model", "check_muted_control", "verdict_from_fit",
    "run_campaign", "null_world_test", "ber_sweep", "read_serial_campaign",
    "main",
]

C_AIR = 343.0

#: Radiation states and their fractional radiated power at fixed drive.
#: ``muted`` is the control: same electrical power, no acoustic output.
RADIATION_STATES: Dict[str, float] = {"open": 1.0, "detuned": 0.35, "muted": 0.0}

#: Above this variance-inflation factor, ``k`` and ``c`` are not separable and
#: the fit is reported as non-identifiable rather than resolved. VIF 20 is
#: |corr| = 0.974 between the two regressors.
MAX_VIF = 20.0


# ---------------------------------------------------------------------------
# Linear least squares, stdlib
# ---------------------------------------------------------------------------

def _solve(a: List[List[float]], b: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting. Raises if singular."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-18:
            raise ValueError("singular design matrix: vary the operating point more")
        m[col], m[piv] = m[piv], m[col]
        p = m[col][col]
        for c in range(col, n + 1):
            m[col][c] /= p
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                f = m[r][col]
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] for i in range(n)]


def _lstsq(X: Sequence[Sequence[float]], y: Sequence[float]) -> Dict[str, object]:
    """Ordinary least squares with per-coefficient standard errors."""
    n, p = len(y), len(X[0])
    if n <= p:
        raise ValueError(f"need more than {p} trials to fit {p} parameters")
    xtx = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(p)]
           for a in range(p)]
    xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(p)]
    beta = _solve([row[:] for row in xtx], xty[:])

    resid = [y[i] - sum(beta[a] * X[i][a] for a in range(p)) for i in range(n)]
    dof = n - p
    s2 = sum(r * r for r in resid) / dof
    # standard errors from the diagonal of s2 * (X'X)^-1
    inv_diag = []
    for a in range(p):
        e = [1.0 if i == a else 0.0 for i in range(p)]
        inv_diag.append(_solve([row[:] for row in xtx], e)[a])
    se = [math.sqrt(max(s2 * d, 0.0)) for d in inv_diag]

    ybar = sum(y) / n
    ss_tot = sum((v - ybar) ** 2 for v in y)
    ss_res = sum(r * r for r in resid)
    r_squared = (1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    return {"beta": beta, "se": se, "dof": dof, "sigma": math.sqrt(s2),
            "r_squared": r_squared}


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson correlation. Returns 0.0 if either series is constant."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    sxx = math.sqrt(sum((v - mx) ** 2 for v in xs))
    syy = math.sqrt(sum((v - my) ** 2 for v in ys))
    if sxx <= 0.0 or syy <= 0.0:
        return 0.0
    return sxy / (sxx * syy)


def variance_inflation(bound: Sequence[float],
                       p_elec: Sequence[float]) -> float:
    """VIF for the ``k`` coefficient: ``1 / (1 - r^2)``.

    With an intercept in the model and one other regressor, the auxiliary
    R-squared of ``bound`` on ``P_elec`` is just their squared correlation.
    VIF is how much the collinearity inflates ``var(k)`` relative to an
    orthogonal design; it also measures how freely ``c`` can steal ``k``'s
    signal, which is the failure this guards against.
    """
    r = _pearson(bound, p_elec)
    denom = 1.0 - r * r
    if denom <= 1e-15:
        return float("inf")
    return 1.0 / denom


# ---------------------------------------------------------------------------
# Trials and the FP-4 fit
# ---------------------------------------------------------------------------

class Trial:
    """One measurement at one operating point.

    Attributes
    ----------
    force_n : float
        Axial force from the balance, newtons. Signed.
    p_rad_w : float
        Total RADIATED acoustic power, watts, from a closed-surface survey.
        Not electrical input -- see the module docstring.
    p_elec_w : float
        Electrical input power, watts. Its own regressor, and it must be
        measured in every state including ``muted``.
    amplitude : float
        Drive amplitude 0..1, recorded for provenance.
    dphi : float
        Phase gradient in radians, recorded for provenance. FP-4 does not
        depend on it.
    state : str
        Radiation state: ``open``, ``detuned``, ``muted``, or a bench-specific
        label. Provenance only -- the fit uses the measured powers, never the
        label, so a mislabelled state cannot bias ``k``.
    """

    __slots__ = ("force_n", "p_rad_w", "p_elec_w", "amplitude", "dphi",
                 "state", "meta")

    def __init__(self, force_n: float, p_rad_w: float, p_elec_w: float,
                 amplitude: float = 0.0, dphi: float = 0.0,
                 state: str = "open", meta: Optional[Dict] = None):
        if p_rad_w < 0.0 or p_elec_w < 0.0:
            raise ValueError("powers must be non-negative")
        self.force_n = float(force_n)
        self.p_rad_w = float(p_rad_w)
        self.p_elec_w = float(p_elec_w)
        self.amplitude = float(amplitude)
        self.dphi = float(dphi)
        self.state = str(state)
        self.meta = meta or {}

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return (f"Trial(F={self.force_n:+.3e}N, P_rad={self.p_rad_w:.3e}W, "
                f"P_elec={self.p_elec_w:.3e}W, {self.state})")


def fit_thrust_model(trials: Sequence[Trial], carrier_v: float = C_AIR,
                     fit_confounders: bool = True,
                     max_vif: float = MAX_VIF) -> Dict[str, object]:
    """Fit ``F = k*(P_rad/v) + c*P_elec + b`` and return ``k`` with its error.

    ``k`` is the anomaly factor: the measured thrust as a multiple of the
    momentum bound. Momentum conservation caps it at 1.

    The returned dict carries ``vif_k`` and ``identifiable``. When ``vif_k``
    exceeds ``max_vif`` the operating points do not separate radiated power
    from electrical power, and ``k`` is not interpretable no matter how small
    its standard error looks. Add muted and detuned points.

    Set ``fit_confounders=False`` to drop the ``P_elec`` and intercept terms.
    That is only appropriate when a muted control has already shown both to be
    negligible; with one regressor there is nothing to be collinear with, so
    ``vif_k`` is 1 by construction and the flag means less.
    """
    if carrier_v <= 0.0:
        raise ValueError("carrier speed must be positive")
    if len(trials) < (4 if fit_confounders else 2):
        raise ValueError("too few trials for this fit")

    bound = [t.p_rad_w / carrier_v for t in trials]
    p_elec = [t.p_elec_w for t in trials]
    y = [t.force_n for t in trials]
    if fit_confounders:
        X = [[bound[i], p_elec[i], 1.0] for i in range(len(trials))]
        names = ["k", "c_elec", "offset"]
        vif = variance_inflation(bound, p_elec)
    else:
        X = [[b] for b in bound]
        names = ["k"]
        vif = 1.0

    fit = _lstsq(X, y)
    beta, se = fit["beta"], fit["se"]
    out: Dict[str, object] = {names[i]: beta[i] for i in range(len(names))}
    out.update({f"{names[i]}_se": se[i] for i in range(len(names))})
    out["n_trials"] = len(trials)
    out["dof"] = fit["dof"]
    out["residual_sigma_n"] = fit["sigma"]
    out["r_squared"] = fit["r_squared"]
    out["confounders_fitted"] = fit_confounders
    out["carrier_v"] = carrier_v
    out["vif_k"] = vif
    out["max_vif"] = max_vif
    out["identifiable"] = vif <= max_vif
    out["states"] = sorted({t.state for t in trials})
    return out


def check_muted_control(trials: Sequence[Trial], muted_state: str = "muted",
                        open_state: str = "open",
                        p_elec_tol: float = 0.10,
                        p_rad_frac: float = 0.05) -> Dict[str, object]:
    """Verify the muted control is actually a control.

    Two things have to hold, and neither is safe to assume:

    * ``P_elec`` in the muted state matches the open state at the same drive
      amplitude, within ``p_elec_tol``. Blocking a driver's output changes its
      acoustic load and therefore its electrical impedance; if the muted state
      draws different power, it is a different operating point and the ``c``
      it constrains is not the ``c`` acting in the open state.
    * ``P_rad`` in the muted state is a small fraction of the open state's at
      the same amplitude. A leaky mute constrains nothing.

    Returns a report with ``ok``. Called by ``run_campaign`` when a muted
    state is present, and worth calling by hand on hardware data before
    trusting a verdict.
    """
    by_state: Dict[str, Dict[float, List[Trial]]] = {}
    for t in trials:
        by_state.setdefault(t.state, {}).setdefault(round(t.amplitude, 6),
                                                    []).append(t)
    if muted_state not in by_state or open_state not in by_state:
        return {"ok": True, "checked": False,
                "note": f"no {muted_state}/{open_state} pair present; not checked"}

    def mean(vals):
        return sum(vals) / len(vals)

    worst_elec, worst_rad, shared = 0.0, 0.0, 0
    for amp, muted in by_state[muted_state].items():
        opened = by_state[open_state].get(amp)
        if not opened:
            continue
        shared += 1
        pe_m, pe_o = mean([t.p_elec_w for t in muted]), mean([t.p_elec_w for t in opened])
        if pe_o > 0.0:
            worst_elec = max(worst_elec, abs(pe_m - pe_o) / pe_o)
        pr_m, pr_o = mean([t.p_rad_w for t in muted]), mean([t.p_rad_w for t in opened])
        if pr_o > 0.0:
            worst_rad = max(worst_rad, pr_m / pr_o)

    if shared == 0:
        return {"ok": False, "checked": False,
                "note": "muted and open states share no drive amplitude: they "
                        "cannot be compared, so the control is unverified"}
    elec_ok, rad_ok = worst_elec <= p_elec_tol, worst_rad <= p_rad_frac
    return {
        "ok": elec_ok and rad_ok, "checked": True,
        "amplitudes_compared": shared,
        "worst_p_elec_mismatch": worst_elec,
        "worst_p_rad_leakage": worst_rad,
        "note": ("muted control verified" if elec_ok and rad_ok else
                 ("muted state draws different electrical power "
                  f"({worst_elec:.1%} > {p_elec_tol:.0%}): not a control"
                  if not elec_ok else
                  f"mute leaks {worst_rad:.1%} of open radiated power "
                  f"(> {p_rad_frac:.0%}): constrains little")),
    }


def verdict_from_fit(fit: Dict[str, object], margin: float = 1.0,
                     z: float = 2.0, bound: float = 1.0) -> Dict[str, object]:
    """Decide FP-4 from a fit. Four outcomes; two of them are decisions.

    The decision is deliberately ASYMMETRIC, because the two claims are not
    mirror images::

        ANOMALY   k - z*se >  margin     (margin >= bound)
        NULL      k + z*se <= bound
        UNRESOLVED  anything between

    Claiming the momentum bound is violated requires clearing it with slack:
    ``margin`` is where the calibration allowance goes. Being *consistent*
    with the bound requires no such slack -- it only requires the interval to
    sit under ``P/v``. A single threshold for both was this function's first
    version and it was wrong: with the null simulated at exactly ``k = 1`` the
    NULL condition ``k + z*se < 1`` is unreachable for any nonzero ``se``, so
    a correct loop scored 7/30 NULL on a world where H0 held. Nothing was
    wrong with the loop; the decision rule had no room for the answer.

    Note also that ``k = 1`` is not what an ordinary radiator does. ``F = P/v``
    is the perfectly collimated limit; a real source with finite directivity
    sits well below it. H0 is ``k <= 1``, not ``k == 1``.

    ``NON-IDENTIFIABLE`` the operating points cannot separate ``k`` from
    ``c``; the interval is meaningless. Add muted and detuned points.

    It is checked first, on purpose. In the collinear design ``k`` came back
    with a *tighter* interval than the good design's, excluding the margin
    from below -- a confident NULL on a world where H1 held. A narrow interval
    on an unidentified parameter is not evidence.

    ``z=2`` is roughly 95% for a well-conditioned fit. It is a *decision*
    threshold and should be fixed before data collection, not after.
    """
    if margin <= 0.0:
        raise ValueError("margin must be positive")
    if bound <= 0.0:
        raise ValueError("bound must be positive")
    if margin < bound:
        raise ValueError("margin must be at least the momentum bound: a "
                         "violation claim cannot need less slack than the bound")
    k, se = float(fit["k"]), float(fit["k_se"])
    lo, hi = k - z * se, k + z * se
    vif = float(fit.get("vif_k", 1.0))

    if not fit.get("identifiable", True):
        status = "NON-IDENTIFIABLE"
        note = (f"VIF(k) = {vif:.1f} > {float(fit.get('max_vif', MAX_VIF)):.0f}: "
                "P_rad and P_elec are collinear over these operating points, "
                "so c can absorb the anomaly. Add muted and detuned points.")
    elif lo > margin:
        status, note = "ANOMALY", ("thrust exceeds the momentum bound: the only "
                                   "result that supports H1")
    elif hi <= bound:
        status, note = "NULL", ("bounded by P/v at this precision: consistent "
                                "with ordinary radiation")
    else:
        status, note = "UNRESOLVED", ("interval spans the bound without "
                                      "clearing the margin: more trials or "
                                      "better calibration needed")
    return {"status": status, "k": k, "k_se": se, "ci": (lo, hi),
            "margin": margin, "bound": bound, "vif_k": vif,
            "identifiable": bool(fit.get("identifiable", True)), "note": note}


# ---------------------------------------------------------------------------
# Simulator -- ground truth is drawn here and never shown to the fitter
# ---------------------------------------------------------------------------

class _Simulator:
    """A synthetic bench. The fitter never sees ``anomaly_factor``.

    Includes the confounders that produce most real false positives: a
    thermal term proportional to *electrical* power, a constant balance
    offset, and independent noise on force and power.

    ``measure`` takes a radiation scale so the caller can build the decoupled
    operating points the fit requires. Electrical power does NOT change with
    the radiation state here, which is the idealisation a real muted control
    has to be checked against rather than assumed.
    """

    def __init__(self, anomaly_factor: float = 1.0, seed: Optional[int] = None,
                 efficiency: float = 0.02, thermal_coeff: float = 2.0e-5,
                 offset_n: float = 3.0e-6, force_noise_n: float = 2.0e-6,
                 power_noise_frac: float = 0.05, carrier_v: float = C_AIR):
        self.k = anomaly_factor
        self.rng = random.Random(seed)
        self.eff = efficiency              # radiated / electrical, open state
        self.thermal = thermal_coeff       # N per electrical watt
        self.offset = offset_n
        self.f_noise = force_noise_n
        self.p_noise = power_noise_frac
        self.v = carrier_v

    def measure(self, amplitude: float, dphi: float = 0.0,
                radiation_scale: float = 1.0, state: str = "open") -> Trial:
        p_elec = 2.0 * amplitude ** 2                      # drivers, V^2 law
        p_rad_true = self.eff * p_elec * radiation_scale
        p_rad_meas = max(0.0, p_rad_true *
                         (1.0 + self.rng.gauss(0.0, self.p_noise)))
        force = (self.k * p_rad_true / self.v
                 + self.thermal * p_elec
                 + self.offset
                 + self.rng.gauss(0.0, self.f_noise))
        return Trial(force, p_rad_meas, p_elec, amplitude, dphi, state)


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

def run_campaign(bench,
                 amplitudes: Sequence[float] = (0.35, 0.5, 0.65, 0.8, 1.0),
                 states: Optional[Dict[str, float]] = None,
                 repeats: int = 3, dphi: float = 0.0,
                 carrier_v: float = C_AIR, margin: float = 1.0,
                 z: float = 2.0, bound: float = 1.0,
                 max_vif: float = MAX_VIF) -> Dict[str, object]:
    """Sweep amplitude *and* radiation state, fit the model, return the verdict.

    Amplitude alone is not enough -- see the module docstring. ``states`` maps
    a label to the fraction of radiated power at fixed drive; the default
    includes the muted control, which is what makes ``c`` and ``b``
    identifiable. Phase is not swept: FP-4 does not depend on ``dphi``.
    """
    if states is None:
        states = RADIATION_STATES
    if not states:
        raise ValueError("need at least one radiation state")
    trials: List[Trial] = []
    for label, scale in states.items():
        for amp in amplitudes:
            for _ in range(repeats):
                trials.append(bench.measure(amp, dphi, scale, label))
    fit = fit_thrust_model(trials, carrier_v=carrier_v, max_vif=max_vif)
    verdict = verdict_from_fit(fit, margin=margin, z=z, bound=bound)
    control = check_muted_control(trials)
    return {"fit": fit, "verdict": verdict, "trials": trials,
            "muted_control": control}


# ---------------------------------------------------------------------------
# The self-test that has to pass first
# ---------------------------------------------------------------------------

def null_world_test(runs: int = 40, anomaly_factor: float = 4.0,
                    seed: int = 0, margin: float = 1.0, z: float = 2.0,
                    states: Optional[Dict[str, float]] = None,
                    null_k_range: tuple = (0.15, 0.85),
                    max_error_rate: float = 0.10,
                    min_power: float = 0.5,
                    repeats: int = 3) -> Dict[str, object]:
    """Run the analysis against worlds where the null is TRUE and where it is not.

    The check ``ASIS/README.md`` says to run before trusting any autopilot,
    plus the corollary this module earned: the loop must also *lose* on a
    world where the null is false. Ground truth is drawn per run and never
    passed to the fitter.

    The null world's ``k`` is drawn uniformly from ``null_k_range``, which
    lies below the momentum bound. That is what H0 asserts -- ``k <= 1`` for a
    source of finite directivity -- and it is a different statement from
    ``k == 1``. Simulating the null at exactly the bound is a degenerate test:
    the boundary is by construction unresolvable, and the first version of
    this function scored a correct loop as failing because of it. Use
    ``null_k_range=(1.0, 1.0)`` to exercise that boundary deliberately, and
    expect UNRESOLVED.

    Returns the false-positive rate (null world called ANOMALY), the
    false-negative rate (anomalous world called NULL), and ``passed``.
    UNRESOLVED and NON-IDENTIFIABLE are counted separately: they are not
    errors, but a design that only ever produces them has no power, so
    ``passed`` also requires each world to resolve correctly at least
    ``min_power`` of the time.
    """
    lo_k, hi_k = float(null_k_range[0]), float(null_k_range[1])
    if not 0.0 <= lo_k <= hi_k:
        raise ValueError("null_k_range must be a non-negative ordered pair")
    rng = random.Random(seed)
    fp = fn = 0
    null_calls = {"ANOMALY": 0, "NULL": 0, "UNRESOLVED": 0, "NON-IDENTIFIABLE": 0}
    anom_calls = dict.fromkeys(null_calls, 0)
    null_truth: List[float] = []

    for _ in range(runs):
        k_null = rng.uniform(lo_k, hi_k)
        null_truth.append(k_null)
        bench = _Simulator(anomaly_factor=k_null, seed=rng.randrange(1 << 30))
        v = run_campaign(bench, states=states, repeats=repeats,
                         margin=margin, z=z)["verdict"]
        null_calls[v["status"]] += 1
        if v["status"] == "ANOMALY":
            fp += 1

        bench = _Simulator(anomaly_factor=anomaly_factor,
                           seed=rng.randrange(1 << 30))
        v = run_campaign(bench, states=states, repeats=repeats,
                         margin=margin, z=z)["verdict"]
        anom_calls[v["status"]] += 1
        if v["status"] == "NULL":
            fn += 1

    fpr, fnr = fp / runs, fn / runs
    power_null = null_calls["NULL"] / runs
    power_anom = anom_calls["ANOMALY"] / runs
    passed = (fpr <= max_error_rate and fnr <= max_error_rate
              and power_null >= min_power and power_anom >= min_power)
    return {
        "runs": runs, "anomaly_factor": anomaly_factor,
        "null_k_range": (lo_k, hi_k),
        "null_k_mean": sum(null_truth) / len(null_truth),
        "false_positive_rate": fpr, "false_negative_rate": fnr,
        "null_world_calls": null_calls, "anomalous_world_calls": anom_calls,
        "power_null": power_null, "power_anomaly": power_anom,
        "passed": passed,
        "note": ("both worlds resolve correctly" if passed else
                 "SELF-TEST FAILED: do not report a verdict on real data"),
    }


# ---------------------------------------------------------------------------
# Bridge test -- BER against phase gradient
# ---------------------------------------------------------------------------

def ber_sweep(bench, gradients: Sequence[float], bits: int = 2000,
              seed: Optional[int] = None) -> List[Dict[str, float]]:
    """Bit error rate against phase gradient. The §9.1 Bridge test.

    Independent of the thrust claim: this measures whether the phase pattern
    that maximises array coherence also minimises errors in a channel
    modulated by it. A monotone relationship supports the Bridge premise; no
    relationship refutes it for this channel, and either way the result does
    not depend on FP-4.

    Requires the bench to implement ``transmit(dphi, bits)`` returning the
    number of bit errors. The simulator does not, so this raises there --
    deliberately, rather than returning a fabricated curve.
    """
    if bits <= 0:
        raise ValueError("bits must be positive")
    if not hasattr(bench, "transmit"):
        raise NotImplementedError(
            "this bench has no transmit(); BER requires hardware or a channel "
            "model. Returning a synthetic BER curve would be exactly the "
            "rigged-simulator defect recorded in ASIS/README.md."
        )
    out = []
    for dphi in gradients:
        errors = bench.transmit(dphi, bits)
        if not 0 <= errors <= bits:
            raise ValueError(f"transmit() returned {errors} errors out of {bits}")
        out.append({"dphi": dphi, "bits": bits, "errors": errors,
                    "ber": errors / bits})
    return out


# ---------------------------------------------------------------------------
# Hardware ingest
# ---------------------------------------------------------------------------

def read_serial_campaign(lines: Sequence[str]) -> List[Trial]:
    """Parse ``field_propulsion_fp4.ino`` telemetry into trials.

    Line format, comma separated, one per settled measurement::

        DATA,<state>,<amplitude>,<dphi_rad>,<force_N>,<p_rad_W>,<p_elec_W>

    Anything not starting with ``DATA`` is ignored, so the firmware is free to
    interleave human-readable status. Malformed ``DATA`` lines raise rather
    than being skipped: a silently dropped operating point changes the design
    matrix, and that is the failure this module exists to avoid.
    """
    trials: List[Trial] = []
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line.startswith("DATA"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 7:
            raise ValueError(f"line {lineno}: expected 7 fields, got {len(parts)}")
        try:
            state = parts[1]
            amp, dphi, force, p_rad, p_elec = (float(x) for x in parts[2:])
        except ValueError as exc:
            raise ValueError(f"line {lineno}: {exc}") from exc
        trials.append(Trial(force, p_rad, p_elec, amp, dphi, state))
    if not trials:
        raise ValueError("no DATA lines found")
    return trials


# ---------------------------------------------------------------------------

def _report(label: str, res: Dict[str, object], k_true: float) -> None:
    f, v = res["fit"], res["verdict"]
    print(f"{label}")
    print(f"  k        = {f['k']:+.4f} +- {f['k_se']:.4f}   "
          f"(true {k_true}, hidden from the fit)")
    print(f"  c_elec   = {f['c_elec']:+.3e} N/W  <- thermal confounder")
    print(f"  offset   = {f['offset']:+.3e} N     <- balance/electrostatic")
    print(f"  VIF(k)   = {f['vif_k']:.2f}  ({'identifiable' if f['identifiable'] else 'NOT identifiable'})")
    print(f"  r^2      = {f['r_squared']:.4f}, residual "
          f"{f['residual_sigma_n']:.2e} N over {f['n_trials']} trials")
    ctl = res.get("muted_control", {})
    print(f"  control  : {ctl.get('note', 'not checked')}")
    print(f"  VERDICT  : {v['status']}")
    print(f"             k in [{v['ci'][0]:+.3f}, {v['ci'][1]:+.3f}] "
          f"vs margin {v['margin']}")
    print(f"             {v['note']}\n")


def main() -> None:
    print("FP-4 AUTOPILOT\n")
    print("Step 0 -- the self-test that has to pass before anything else.")
    st = null_world_test(runs=30, seed=7)
    print(f"  runs per world        : {st['runs']}")
    print(f"  null world k drawn in : {st['null_k_range']} (H0 is k <= 1)")
    print(f"  null world calls      : {st['null_world_calls']}")
    print(f"  anomalous world calls : {st['anomalous_world_calls']}")
    print(f"  false positive rate   : {st['false_positive_rate']:.3f}")
    print(f"  false negative rate   : {st['false_negative_rate']:.3f}")
    print(f"  PASSED                : {st['passed']}  -- {st['note']}\n")
    if not st["passed"]:
        print("Refusing to report a verdict on data. Fix the loop first.")
        return

    at_bound = null_world_test(runs=20, seed=3, null_k_range=(1.0, 1.0))
    print("Same loop with the null placed exactly ON the bound (k=1):")
    print(f"  {at_bound['null_world_calls']}")
    print("  Mostly UNRESOLVED, and that is correct -- an interval centred on")
    print("  the bound cannot exclude it. A test whose null sits at the")
    print("  decision boundary measures the boundary, not the world.\n")

    for label, k_true in (("null world (k=0.6, ordinary directivity)", 0.6),
                          ("anomalous world (k=4)", 4.0)):
        _report(label, run_campaign(_Simulator(anomaly_factor=k_true, seed=11)),
                k_true)

    print("What the decoupled design buys, shown against the design it replaced:")
    print("amplitude-only sweep, no muted or detuned control, k=4 world --")
    _report("  amplitude-only (broken by construction)",
            run_campaign(_Simulator(anomaly_factor=4.0, seed=11),
                         states={"open": 1.0}, repeats=18),
            4.0)
    print("The broken design's interval is TIGHTER than the good one's and it")
    print("excludes the margin from below. Without the VIF guard it reports a")
    print("confident NULL on a world where H1 is true. That is the whole")
    print("reason NON-IDENTIFIABLE is a verdict and is checked first.\n")

    try:
        ber_sweep(_Simulator(), [0.0, math.pi / 2])
    except NotImplementedError as exc:
        print(f"Bridge test: {str(exc)[:72]}...")


if __name__ == "__main__":
    main()
