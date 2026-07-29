"""
NEG-7 falsifier -- do the named lenses do any work?

The claim under test: seventeen cultural and scientific lenses applied to
one dynamical core all correlate above 0.88 with each other, therefore they
are surface renderings of a single deep grammar.

The null model: draw seventeen lenses with the *same functional form* and
randomly chosen coefficients, from the same ranges the named lenses live
in, and give them no cultural content at all.  Apply them to the same
trace.  If the random lenses hit the same correlation floor, the floor is a
property of the arithmetic -- fourteen affine reparameterisations of the
same four numbers -- and the named coefficients are decoration.

DECISION RULE (absolute, as originally stated)

    frac_above_0.88 > 0.9   ->  NEG-7 DEAD.  Random labels reproduce the
                                result.  Delete the isomorphism claim from
                                the README.
    frac_above_0.88 < 0.3   ->  The named coefficients are doing work.
                                Keep the claim, and publish where the
                                coefficients came from.
    in between              ->  Inconclusive at this trace length.  Report
                                the number; do not round it toward the
                                answer you wanted.

DECISION RULE (trace-matched -- prefer this one)

The 0.88 threshold was calibrated against the original core, whose output
was clipped and whose ``D`` channel was constant.  On a corrected core the
*absolute* correlation level moves around with ``n`` and trace length, so
``frac_above_0.88`` measures the trajectory as much as it measures the
lenses.  :func:`compare` fixes that by running both sets of lenses on the
same trace and asking where the named floor sits inside the random-floor
distribution:

    named_percentile <= 0.9  ->  NEG-7 DEAD.  The named coefficients are
                                 indistinguishable from arbitrary ones of
                                 the same form.
    named_percentile > 0.99  ->  The named lenses agree far more than
                                 chance.  Something is there; publish where
                                 the coefficients came from.

This comparison is invariant to how correlated the underlying trajectory
happens to be, because both arms see the same trajectory.

Note what the test does *not* do: it says nothing about whether the
traditions themselves converge on anything.  It tests one narrow thing --
whether this particular arithmetic can distinguish them.  A dead NEG-7
means the code was never measuring the convergence, not that there is
nothing there to measure.

Stdlib only.  No numpy, no scipy.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Dict, List, Optional, Sequence, Tuple

Trace = Sequence[Tuple[float, float, float, float]]
Lens = Callable[[float, float, float, float], float]

__all__ = ["pearson", "random_lens", "run", "named_floor", "compare", "verdict", "main"]


def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    """Pearson correlation.  Returns NaN when either series is constant."""
    n = len(x)
    if n < 2:
        return float("nan")
    mx = sum(x) / n
    my = sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx * syy > 0 else float("nan")


def random_lens(rng: Optional[random.Random] = None) -> Lens:
    """A lens with the same functional form as every named one in the repo.

    ``M = (a*R) * (b*A + c) * (d*D + e) - f*L``

    The coefficient ranges bracket the values the named lenses actually use
    (see ``lenses.LENS_COEFFICIENTS``), so the random draws are not being
    handed an unfair advantage or disadvantage.
    """
    r = rng or random
    a = r.uniform(0.8, 1.6)                                 # R coefficient
    b, c = r.uniform(0.6, 1.4), r.uniform(0.0, 0.4)         # A affine
    d, e = r.uniform(1.4, 2.5), r.uniform(0.3, 1.0)         # D affine
    f = r.uniform(0.5, 1.2)                                 # L coefficient
    return lambda R, A, D, L: (a * R) * (b * A + c) * (d * D + e) - f * L


def _pairwise_floor(matrix: List[List[float]]) -> float:
    """Smallest off-diagonal Pearson r among a set of lens trajectories.

    Uses the upper triangle only.  Masking the diagonal with a value cutoff
    (``corr[corr < 0.999]``, as the original analysis did) also discards
    genuinely near-perfect off-diagonal pairs, which inflates the reported
    floor -- the exact number the claim rests on.
    """
    k = len(matrix)
    rs = [pearson(matrix[i], matrix[j])
          for i in range(k) for j in range(i + 1, k)]
    rs = [r for r in rs if not math.isnan(r)]
    if not rs:
        return float("nan")
    return min(rs)


def _floors(trace: Trace, n_lenses: int, trials: int,
            rng: random.Random) -> List[float]:
    """Correlation floors from ``trials`` independent random lens sets."""
    floors: List[float] = []
    for _ in range(trials):
        lenses = [random_lens(rng) for _ in range(n_lenses)]
        matrix = [[fn(*state) for state in trace] for fn in lenses]
        floor = _pairwise_floor(matrix)
        if not math.isnan(floor):
            floors.append(floor)
    return floors


def run(trace: Trace, n_lenses: int = 17, trials: int = 200,
        seed: Optional[int] = None) -> Dict[str, float]:
    """Distribution of the correlation floor under randomly drawn lenses.

    Parameters
    ----------
    trace : sequence of (R, A, D, L)
        Core trajectory.  ``core.DissipativeCore.legacy_rad_trace`` produces
        this in the same form the original claim was computed from.
    n_lenses : int
        How many random lenses per trial.  17 matches the registry.
    trials : int
        Number of independent draws of the lens set.
    seed : int, optional
        Seed for a local RNG, so the verdict is reproducible.

    Returns
    -------
    dict
        ``median_floor``, ``worst_floor``, and ``frac_above_0.88`` -- the
        fraction of random lens sets whose *worst* pair still clears the
        threshold the claim advertises.
    """
    if len(trace) < 3:
        raise ValueError("trace too short to correlate")
    floors = _floors(trace, n_lenses, trials, random.Random(seed))

    if not floors:
        raise ValueError("every trial degenerated -- is the trace constant?")

    floors.sort()
    return {
        "median_floor": floors[len(floors) // 2],
        "worst_floor": floors[0],
        "frac_above_0.88": sum(f > 0.88 for f in floors) / len(floors),
        "trials": float(len(floors)),
    }


def named_floor(trace: Trace) -> Dict[str, float]:
    """Correlation floor of the seventeen *named* lenses on the same trace.

    This is the number the original analysis reported.  It is only
    interpretable next to the random-lens distribution from :func:`run`.
    """
    from Negentropic.lenses import LENS_REGISTRY

    names = list(LENS_REGISTRY)
    matrix = [[LENS_REGISTRY[name](*state) for state in trace] for name in names]
    k = len(names)
    pairs = [(pearson(matrix[i], matrix[j]), names[i], names[j])
             for i in range(k) for j in range(i + 1, k)]
    pairs = [p for p in pairs if not math.isnan(p[0])]
    pairs.sort()
    return {
        "floor": pairs[0][0],
        "floor_pair": f"{pairs[0][1]} vs {pairs[0][2]}",
        "median": pairs[len(pairs) // 2][0],
        "n_pairs": float(len(pairs)),
    }


def compare(trace: Trace, n_lenses: int = 17, trials: int = 200,
            seed: Optional[int] = None) -> Dict[str, float]:
    """Trace-matched test: where does the named floor sit among random ones?

    Both arms see the same trace, so the comparison does not depend on how
    correlated that particular trajectory happens to be -- which the
    absolute 0.88 threshold does.

    Returns the named floor, the random-floor quartiles, and
    ``named_percentile``: the fraction of random lens sets whose floor is
    below the named one. A value near or under 0.5 means the named lenses
    agree no more than arbitrary coefficients of the same shape do.
    """
    if len(trace) < 3:
        raise ValueError("trace too short to correlate")
    named = named_floor(trace)
    floors = _floors(trace, n_lenses, trials, random.Random(seed))
    if not floors:
        raise ValueError("every trial degenerated -- is the trace constant?")
    floors.sort()

    below = sum(f < named["floor"] for f in floors)
    return {
        "named_floor": named["floor"],
        "random_median": floors[len(floors) // 2],
        "random_min": floors[0],
        "random_max": floors[-1],
        "named_percentile": below / len(floors),
        "trials": float(len(floors)),
    }


def verdict(frac_above: float) -> str:
    """Apply the absolute decision rule at the top of this module."""
    if frac_above > 0.9:
        return ("NEG-7 DEAD -- random labels reproduce the result. "
                "Delete the isomorphism claim from the README.")
    if frac_above < 0.3:
        return ("NEG-7 SURVIVES -- the named coefficients are doing work. "
                "Keep it, and publish where they came from.")
    return ("INCONCLUSIVE at this trace length -- report the fraction as "
            "measured, do not round it toward a conclusion.")


def matched_verdict(named_percentile: float) -> str:
    """Apply the trace-matched decision rule at the top of this module."""
    if named_percentile <= 0.9:
        return ("NEG-7 DEAD -- the named coefficients are indistinguishable "
                "from arbitrary ones of the same functional form.")
    if named_percentile > 0.99:
        return ("NEG-7 SURVIVES -- the named lenses agree far more than "
                "chance. Publish where the coefficients came from.")
    return ("INCONCLUSIVE -- the named floor is high but not decisively "
            "outside the random distribution. Lengthen the trace.")


def main(steps: int = 250, trials: int = 200, seed: int = 42) -> Dict[str, float]:
    """Run the falsifier against a trace from the corrected core."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Negentropic.core import DissipativeCore

    core = DissipativeCore(n=50, K=1.5, Dn=0.045, dt=0.02, seed=seed)
    trace = core.legacy_rad_trace(steps=steps, burn_in=80)

    named = named_floor(trace)
    result = run(trace, n_lenses=17, trials=trials, seed=seed)
    matched = compare(trace, n_lenses=17, trials=trials, seed=seed)

    print("=" * 68)
    print("NEG-7 FALSIFIER -- lens collapse test")
    print("=" * 68)
    print(f"trace: {len(trace)} steps of (R, A, D, L) from DissipativeCore")
    print()
    print("Named lenses (the reported result):")
    print(f"  correlation floor   {named['floor']:.4f}   ({named['floor_pair']})")
    print(f"  median pair         {named['median']:.4f}   over {int(named['n_pairs'])} pairs")
    print()
    print(f"Random lenses, same functional form, {int(result['trials'])} trials:")
    print(f"  median floor        {result['median_floor']:.4f}")
    print(f"  worst floor         {result['worst_floor']:.4f}")
    print(f"  frac above 0.88     {result['frac_above_0.88']:.3f}")
    print()
    print(f"ABSOLUTE RULE:  {verdict(result['frac_above_0.88'])}")
    print()
    print("Trace-matched comparison (both arms on the same trace):")
    print(f"  named floor         {matched['named_floor']:.4f}")
    print(f"  random floors       [{matched['random_min']:.4f}, "
          f"{matched['random_max']:.4f}], median {matched['random_median']:.4f}")
    print(f"  named percentile    {matched['named_percentile']:.3f}")
    print()
    print(f"MATCHED RULE:   {matched_verdict(matched['named_percentile'])}")
    print("=" * 68)
    result.update(matched)
    return result


if __name__ == "__main__":
    main()
