"""
TRI-1..4 -- the triangle as the smallest self-verifying archive unit.

STORAGE RULE: angles only. One declared length for the whole net.
    Shape needs no units. Scale needs exactly one datum.
    Lose the datum -> you lose SIZE, never SHAPE.

Pairs with ``rebase.py``: a triangle that fails closure is a node that must
be revalidated or demoted from base. :func:`to_rebase` is that hook.

WHY A TRIANGLE, DERIVED RATHER THAN ASSERTED
--------------------------------------------
============  ====================================================
RIGID         The only polygon rigid without bracing. Deform any
              side and the figure reports it. Tamper detection is
              built into the shape.
SELF-CHECKING Interior angles sum to pi. Every single triangle
              carries its own error check, verifiable by anyone,
              forever, with no reference to the builder. A
              quadrilateral does not have this -- 2*pi constrains
              nothing about its shape. The triangle is the
              SMALLEST SELF-VERIFYING UNIT.
UNIT-FREE     Shape is fixed by angles alone. Size needs one
              length; relationship needs none. A preserved standard
              length rots, burns, or is stolen; an angle reproduces
              from the figure itself indefinitely, with cord and
              stakes. No metrological dependency, nothing to lose.
MINIMUM PLANE Three points is the least that fixes a plane AND an
              orientation. Two give a line with no handedness.
              Four or more is over-determined and can go
              inconsistent.
ARTIFICIAL    Nature rarely makes an equilateral triangle. The
              figure IS the "this is deliberate" flag -- signal/
              noise discrimination encoded in the geometry rather
              than in a label someone has to remember how to read.
COMPOSABLE    Triangles chain into a network; position propagates
              through angles alone. This is exactly how geodetic
              survey worked until satellites.
============  ====================================================

CONVENTION: GEOMETRY STAYS GEOMETRY UNTIL THE LAST STEP
-------------------------------------------------------
Geometry is SIMULTANEOUS -- all relations hold at once.
Tokens are SEQUENTIAL -- relations get serialised, and an order gets
imposed that was never in the object.

The seventeen lens functions in ``lenses.py`` did exactly this: they
collapsed a figure to four scalars at step one, and everything downstream
operated on the shadow. That is *why* their coefficients could be random
without changing the result (``lens_collapse_test.py``) -- there was no
geometry left for them to be sensitive to.

``rebase.py`` did not do that. It kept the graph as a graph and computed on
structure, which is why it produced a real operation -- cycle detection
reading as contradiction detection -- instead of a tuned constant. This
module does the same: it computes on the figure.

    DIAGNOSTIC: if a module takes a figure and returns a number in one hop,
    the figure was the content and the number is the loss.

Never scalarise before you have to.

Stdlib only. Phone-buildable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

PI = math.pi

__all__ = [
    "ARCSEC",
    "Triangle",
    "d2r", "r2d", "cot",
    "misclosure", "closure_ok", "adjusted",
    "pair_strength", "strength", "rel_scale_var",
    "Net", "deform_check", "to_rebase",
]


def d2r(d: float) -> float:
    """Degrees to radians."""
    return d * PI / 180.0


def r2d(r: float) -> float:
    """Radians to degrees."""
    return r * 180.0 / PI


def cot(x: float) -> float:
    """Cotangent. Raises on a degenerate (zero-sine) angle."""
    s = math.sin(x)
    if s == 0.0:
        raise ValueError("cot undefined at a multiple of pi")
    return math.cos(x) / s


ARCSEC = d2r(1.0 / 3600.0)


@dataclass
class Triangle:
    """A measured figure. Angles only -- no lengths, no coordinates.

    Attributes
    ----------
    name : str
        Identifier for the figure.
    verts : tuple
        ``(v0, v1, v2)`` node ids. Order matters: ``angles[i]`` is the
        interior angle AT ``verts[i]``.
    angles : tuple
        Interior angles in radians.
    sigma : float
        Per-angle 1-sigma measurement uncertainty, radians.
    epoch : int
        When measured.
    """

    name: str
    verts: Tuple
    angles: Tuple[float, float, float]
    sigma: float = d2r(0.5)
    epoch: int = 0

    def __post_init__(self) -> None:
        if len(self.verts) != 3 or len(self.angles) != 3:
            raise ValueError("a triangle has exactly three vertices and angles")
        if len(set(self.verts)) != 3:
            raise ValueError("vertices must be distinct")
        if any(a <= 0.0 for a in self.angles):
            raise ValueError("interior angles must be positive")
        if self.sigma <= 0.0:
            raise ValueError("sigma must be positive")


# ---------------------------------------------------------------------------
# SELF-VERIFICATION
#
# The property nothing else in plane geometry has: the figure checks itself,
# forever, with no reference to the builder and no preserved standard.
# ---------------------------------------------------------------------------

def misclosure(t: Triangle) -> float:
    """Sum of interior angles minus pi, in radians. THE self-check."""
    return sum(t.angles) - PI


def closure_ok(t: Triangle, k: float = 3.0) -> bool:
    """Whether misclosure is consistent with measurement noise alone.

    Three independent angles each with 1-sigma ``sigma`` give a sum with
    standard deviation ``sigma*sqrt(3)``, so the test is
    ``|misclosure| <= k * sigma * sqrt(3)``.
    """
    return abs(misclosure(t)) <= k * t.sigma * math.sqrt(3.0)


def adjusted(t: Triangle) -> Tuple[float, float, float]:
    """Distribute misclosure equally across the three angles.

    Valid when all three angles were observed at equal precision. Returns a
    new tuple; does not mutate the triangle.
    """
    w = misclosure(t) / 3.0
    return tuple(a - w for a in t.angles)


# ---------------------------------------------------------------------------
# STRENGTH OF FIGURE -- why equilateral, derived rather than asserted
# ---------------------------------------------------------------------------

def pair_strength(a1: float, a2: float) -> float:
    """Variance factor for scale carried between the sides opposite a1, a2.

    ``cot^2(a1) + cot(a1)cot(a2) + cot^2(a2)``, the classical geodetic
    strength-of-figure term, under the sum constraint that correlates the
    angles after adjustment. Returns ``inf`` for a degenerate angle.
    """
    if math.sin(a1) == 0.0 or math.sin(a2) == 0.0:
        return float("inf")
    c1, c2 = cot(a1), cot(a2)
    return c1 * c1 + c1 * c2 + c2 * c2


def strength(t: Triangle) -> float:
    """Worst-case variance factor over all three routings through the figure.

    MINIMISED AT EQUILATERAL, where it equals exactly 1.0. A chain may enter
    and exit on any pair of sides, so the *maximum* over routings is what
    binds -- a figure that is strong one way and weak another is weak.
    """
    a = t.angles
    return max(pair_strength(a[0], a[1]),
               pair_strength(a[1], a[2]),
               pair_strength(a[0], a[2]))


def rel_scale_var(t: Triangle) -> float:
    """Relative variance of a length carried through this triangle."""
    return strength(t) * t.sigma * t.sigma


# ---------------------------------------------------------------------------
# NET: scale and bearing from a declared base
# ---------------------------------------------------------------------------

class Net:
    """A chain of triangles sharing edges, with ONE base length.

    Everything except size is derived from angles. "The base is the
    important part" falls out numerically rather than being asserted: base
    error is common-mode to every derived length, and closure error
    propagates only upward from base to dependents, never downward.
    """

    def __init__(self, base_length: float, base_sigma_rel: float = 0.0) -> None:
        if base_length <= 0.0:
            raise ValueError("base_length must be positive")
        if base_sigma_rel < 0.0:
            raise ValueError("base_sigma_rel must be non-negative")
        self.L0 = base_length
        self.var0 = base_sigma_rel ** 2
        self.chain: List[Tuple[Triangle, int, int]] = []

    def extend(self, t: Triangle, in_i: int, out_i: int) -> "Net":
        """Append a triangle, entering at angle ``in_i`` and leaving at ``out_i``."""
        if in_i not in (0, 1, 2) or out_i not in (0, 1, 2):
            raise ValueError("angle indices must be 0, 1 or 2")
        if in_i == out_i:
            raise ValueError("entry and exit angles must differ")
        self.chain.append((t, in_i, out_i))
        return self

    def carry(self) -> List[Dict[str, float]]:
        """Propagate length and bearing along the chain.

        Returns per-step length, relative sigma, and cumulative bearing
        sigma. Nothing here needs a preserved standard except ``self.L0``,
        and that only sets SIZE.
        """
        length = self.L0
        var = self.var0
        az_var = 0.0
        out: List[Dict[str, float]] = []
        for t, i, j in self.chain:
            a = adjusted(t)
            length = length * math.sin(a[j]) / math.sin(a[i])
            var += pair_strength(a[i], a[j]) * t.sigma * t.sigma
            az_var += t.sigma * t.sigma            # one turned angle per step
            out.append({
                "tri": t.name,
                "length": length,
                "rel_sigma": math.sqrt(var),
                "bearing_sigma_arcsec": math.sqrt(az_var) / ARCSEC,
            })
        return out


# ---------------------------------------------------------------------------
# DEFORMATION vs MEASUREMENT ERROR
#
# The discrimination that matters for a centuries-scale archive:
#   closure BAD                   -> the observation is bad, or a vertex lost
#   closure GOOD but record drift -> the FIGURE MOVED. archive event.
# ---------------------------------------------------------------------------

def deform_check(recorded: Triangle, remeasured: Triangle,
                 k: float = 3.0) -> Dict[str, object]:
    """Compare a stored figure against a fresh measurement of it.

    Returns a verdict dict: GREEN stable, YELLOW the figure deformed, RED
    the observation cannot be trusted or a vertex is gone.

    The order of the tests matters. Closure is checked *before* per-angle
    drift, because a figure that fails its own self-check cannot be used to
    conclude anything about movement -- a bad observation would otherwise
    be reported as a moved monument.
    """
    if tuple(recorded.verts) != tuple(remeasured.verts):
        return {"verdict": "RED", "why": "VERTEX_SET_CHANGED"}

    if not closure_ok(remeasured, k):
        return {"verdict": "RED",
                "why": "CLOSURE_FAIL",
                "misclosure_arcsec": misclosure(remeasured) / ARCSEC,
                "action": "REMEASURE_OR_DEMOTE"}

    s = math.sqrt(recorded.sigma ** 2 + remeasured.sigma ** 2)
    dev = [b - a for a, b in zip(recorded.angles, remeasured.angles)]
    moved = [recorded.verts[i] for i, d in enumerate(dev) if abs(d) > k * s]

    if moved:
        return {"verdict": "YELLOW",
                "why": "FIGURE_DEFORMED",
                "moved": moved,
                "dev_arcsec": [d / ARCSEC for d in dev],
                "action": "REVALIDATE"}

    return {"verdict": "GREEN",
            "why": "STABLE",
            "strength": strength(remeasured),
            "dev_arcsec": [d / ARCSEC for d in dev]}


# ---------------------------------------------------------------------------
# HOOK INTO rebase.py
# ---------------------------------------------------------------------------

def to_rebase(node, check: Dict[str, object], archive, now: int) -> Dict[str, object]:
    """Translate a figure verdict into an archive operation.

    Closure failure at a node means that node cannot carry the archive,
    which is the same condition the V-gate in ``rebase.recenter`` already
    enforces -- here it arrives from physical measurement rather than from
    a validation epoch.
    """
    verdict = check["verdict"]
    if verdict == "GREEN":
        archive.validated[node] = now
        return {"op": "VALIDATE", "node": node}
    if verdict == "YELLOW":
        return {"op": "HOLD", "node": node, "why": check["why"]}
    if node == archive.center:
        return {"op": "RECENTER_REQUIRED", "node": node,
                "why": "base figure failed closure"}
    return {"op": "QUARANTINE", "node": node, "why": check["why"]}


if __name__ == "__main__":
    E = d2r(60.0)
    # A surveyed monument is measured far better than the 0.5-degree default.
    # Ten arcseconds is a theodolite; the default is a hand compass, and at
    # that precision none of the effects below are visible at all.
    S = 10 * ARCSEC

    good = Triangle("T1", ("a", "b", "c"),
                    (E + 4 * ARCSEC, E - 2 * ARCSEC, E - 1 * ARCSEC), sigma=S)
    weak = Triangle("W1", ("a", "b", "c"),
                    (d2r(15.0), d2r(15.0), d2r(150.0)), sigma=S)

    print("TRI-1: strength of figure is minimised at equilateral")
    print(f"  equilateral   strength = {strength(good):.3f}   (exact minimum)")
    print(f"  15/15/150     strength = {strength(weak):.1f}")
    print(f"  penalty       = {strength(weak) / strength(good):.1f}x "
          f"the scale variance per hop")

    print("\nTRI-4: the figure checks itself, with no standard and no builder")
    print(f"  closure ok    = {closure_ok(good)}")
    print(f"  misclosure    = {misclosure(good) / ARCSEC:.2f} arcsec"
          f"   (tolerance {3 * S * math.sqrt(3) / ARCSEC:.1f})")

    print("\nTRI-3: deformation and measurement error are separable")
    moved = Triangle("T1", ("a", "b", "c"),
                     (E + 84 * ARCSEC, E - 42 * ARCSEC, E - 42 * ARCSEC),
                     sigma=S, epoch=1)
    result = deform_check(good, moved)
    print(f"  closure holds, angles moved -> {result['verdict']} / {result['why']}")
    print(f"  moved vertices : {result.get('moved')}")
    print(f"  deviations     : "
          f"{[round(d, 1) for d in result.get('dev_arcsec', [])]} arcsec")

    broken = Triangle("T1", ("a", "b", "c"),
                      (E + 300 * ARCSEC, E, E), sigma=S, epoch=1)
    result = deform_check(good, broken)
    print(f"  closure fails               -> {result['verdict']} / {result['why']}")
    print(f"  misclosure     : {result.get('misclosure_arcsec', 0):.0f} arcsec")
    print(f"  action         : {result.get('action')}")
    print("  Same magnitude of angle change, two different diagnoses. The")
    print("  first says the monument moved; the second says the survey is bad.")

    print("\nTRI-2 consequence: chain shape decides how fast error accumulates")
    for label, angles in (("equilateral", (E, E, E)),
                          ("thin 15/15/150", (d2r(15.0), d2r(15.0), d2r(150.0)))):
        net = Net(base_length=100.0, base_sigma_rel=0.0)
        for i in range(6):
            net.extend(Triangle(f"{label[0]}{i}", (f"p{i}", f"q{i}", f"r{i}"),
                                angles, sigma=S), 0, 1)
        final = net.carry()[-1]
        print(f"  {label:15s} after 6 hops: rel_sigma = "
              f"{final['rel_sigma']:.3e}, bearing = "
              f"{final['bearing_sigma_arcsec']:.1f} arcsec")
    print("  A net of thin figures accumulates error until it stops closing")
    print("  and gets rebuilt or abandoned. Surviving nets are equilateral")
    print("  BY SELECTION -- a claim about surviving structures, not intent.")
    print("\n  Shape came from angles alone. Only the base 100.0 needed a datum.")
