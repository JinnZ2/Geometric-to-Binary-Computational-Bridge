"""A candidate that must be REJECTED. It is here so the bench can be seen
to reject something.

Every check below is true for every possible input. A variance is never
negative; a set of unit vectors always has at least one member; a norm is
always at least zero. All three pass on solve(), and all three pass on
broken() too, which is the whole point -- there is no artifact these checks
could distinguish from any other.

This is not a strawman. It is the shape of three real findings in this
archive:

  VAC-1   "at least one mode survives" -- true by construction, because the
          construction guaranteed a survivor.
  ATT-1   topological_pin's original run(), which asserted the topological
          charge was conserved. It is conserved. It is an invariant. No
          dynamics could have violated it.
  AISS    26 of 46 assertions were assertIsInstance / assertIn. They fail
          only when a function is renamed or crashes.

Expected verdict: REJECTED_UNFALSIFIABLE.
"""
import math
import random

PROBLEM = "FCL-5e"
CLAIM = ("The loop conserves information, as shown by the fact that its "
         "energy is non-negative.")
KIND = "DERIVATION"
AUTHOR = "the bench itself, as a self-test"
NEEDS_NULL = False
MATERIAL = None


def _artifact(scale):
    rng = random.Random(0)
    xs = [rng.gauss(0, scale) for _ in range(200)]
    m = sum(xs) / len(xs)
    return {"values": xs,
            "variance": sum((x - m) ** 2 for x in xs) / len(xs),
            "unit_vectors": [(1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)]}


def solve():
    return _artifact(1.0)


def broken():
    """Scale changed by four orders. The checks below cannot tell."""
    return _artifact(1e-4)


def checks(a):
    return [
        ("variance is non-negative", a["variance"] >= 0.0,
         "variance = %.6g" % a["variance"]),
        ("at least one direction exists", len(a["unit_vectors"]) >= 1,
         "%d directions" % len(a["unit_vectors"])),
        ("norms are real and non-negative",
         all(math.sqrt(sum(c * c for c in v)) >= 0.0
             for v in a["unit_vectors"]),
         "all %d norms >= 0" % len(a["unit_vectors"])),
    ]
