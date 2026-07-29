"""
Precession: dating a sky datum, and computing when it has to be re-established.

A datum aligned to the celestial pole is not stable. The pole traces a
circle of angular radius equal to the obliquity (~23.44 deg) around the
ecliptic pole, once per ~25,772 years -- about one degree of travel every
71.6 years. Any tradition that maintains a pole-aligned reference monument
across more than a few generations must therefore contain a **re-datum
protocol**, or it accumulates error at a computable rate.

That cuts both ways, and the second way is the useful one:

    If a tradition names a SPECIFIC configuration -- a named star at a
    named position -- that alignment was exact in a computable year.

Precession dates the claim. No excavation, no radiocarbon, no site access:
the stories alone carry a timestamp, to roughly +-100 years for a tight
alignment. :func:`alignment_window` computes it.

The same machinery answers a question the reconstruction in
``08-oral-technology.md`` depends on and which is *not* epoch-independent:
whether a given star was circumpolar (never set) at a given latitude at a
given epoch. A star is circumpolar at latitude ``phi`` exactly when its
angular separation from the pole is less than ``phi``, and that separation
changes by tens of degrees over the precession cycle.

MODEL AND ITS LIMITS
--------------------
Simple, deliberately. The pole circles the ecliptic pole uniformly at fixed
obliquity. That reproduces the standard reference epochs to within a few
decades (validated in ``__main__``), and it is wrong in four ways that
matter if you push it:

* **No proper motion.** Stars move. Over 14,000 years this is the dominant
  error for anything in Ursa Major -- Alkaid and Dubhe travel opposite to
  the other five Plough stars, so the asterism visibly deforms and the
  Dubhe-Merak pointer geometry degrades from proper motion, not from
  precession. Do not use this module to evaluate pointer alignment deep in
  time.
* **Fixed obliquity.** It actually oscillates between about 22.0 and 24.5
  degrees on a ~41,000-year cycle. Minimum separations are good to a few
  tenths of a degree, no better.
* **Uniform precession rate.** The real rate varies slowly.
* **No nutation, aberration, or refraction.** Irrelevant at this precision;
  refraction matters for the *observation*, not for where the pole is.

Good to a few decades in epoch and a few tenths of a degree in separation.
Not an ephemeris. If a result depends on more precision than that, use one.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

__all__ = [
    "OBLIQUITY",
    "PRECESSION_PERIOD",
    "PRECESSION_RATE",
    "POLE_ECLIPTIC_LATITUDE",
    "CATALOG",
    "equatorial_to_ecliptic",
    "pole_ecliptic_longitude",
    "separation_from_pole",
    "declination_at",
    "is_circumpolar",
    "limiting_latitude",
    "closest_approach",
    "alignment_window",
    "drift_years_per_degree",
]

OBLIQUITY = 23.4393                       # degrees, J2000 mean obliquity
PRECESSION_PERIOD = 25772.0               # years, one full circuit of the pole
PRECESSION_RATE = 360.0 / PRECESSION_PERIOD   # degrees per year along the circle
POLE_ECLIPTIC_LATITUDE = 90.0 - OBLIQUITY     # 66.5607 deg, constant in this model

#: J2000 equatorial coordinates (RA degrees, Dec degrees) of the stars this
#: reconstruction refers to. Proper motion is NOT applied -- see the module
#: docstring before using these deep in time.
CATALOG: Dict[str, Tuple[float, float]] = {
    "Polaris": (37.9545, 89.2641),        # alpha UMi
    "Thuban": (211.0973, 64.3758),        # alpha Dra
    "Vega": (279.2347, 38.7837),          # alpha Lyr
    "Kochab": (222.6764, 74.1555),        # beta UMi
    "Alkaid": (206.8852, 49.3133),        # eta UMa, the Bear's limiting star
    "Dubhe": (165.9319, 61.7511),         # alpha UMa, pointer
    "Merak": (165.4603, 56.3824),         # beta UMa, pointer
}


def equatorial_to_ecliptic(ra_deg: float, dec_deg: float,
                           obliquity: float = OBLIQUITY) -> Tuple[float, float]:
    """Convert J2000 equatorial coordinates to ecliptic ``(lambda, beta)``.

    Ecliptic latitude ``beta`` is what the rest of this module works in,
    because precession leaves it unchanged -- the pole moves, the star's
    position relative to the *ecliptic* pole does not. That invariance is
    what makes the whole calculation a one-parameter problem.
    """
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    eps = math.radians(obliquity)

    sin_beta = math.sin(dec) * math.cos(eps) - math.cos(dec) * math.sin(eps) * math.sin(ra)
    sin_beta = max(-1.0, min(1.0, sin_beta))
    beta = math.asin(sin_beta)

    y = math.sin(dec) * math.sin(eps) + math.cos(dec) * math.cos(eps) * math.sin(ra)
    x = math.cos(dec) * math.cos(ra)
    lam = math.degrees(math.atan2(y, x)) % 360.0
    return lam, math.degrees(beta)


def pole_ecliptic_longitude(year: float) -> float:
    """Ecliptic longitude of the north celestial pole at ``year`` (CE).

    At J2000 the pole sits at ecliptic longitude 90 degrees, latitude
    ``90 - obliquity``. In a frame fixed to the stars its longitude
    *decreases* at the precession rate. Negative years are BCE in
    astronomical numbering (year 0 = 1 BCE).
    """
    return (90.0 - PRECESSION_RATE * (year - 2000.0)) % 360.0


def _separation(lam1: float, beta1: float, lam2: float, beta2: float) -> float:
    """Angular separation of two points on a sphere, in degrees."""
    b1, b2 = math.radians(beta1), math.radians(beta2)
    dlam = math.radians(lam1 - lam2)
    cos_sep = math.sin(b1) * math.sin(b2) + math.cos(b1) * math.cos(b2) * math.cos(dlam)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep))))


def separation_from_pole(lam: float, beta: float, year: float) -> float:
    """Angular distance, in degrees, from the star to the pole at ``year``."""
    return _separation(lam, beta, pole_ecliptic_longitude(year), POLE_ECLIPTIC_LATITUDE)


def declination_at(lam: float, beta: float, year: float) -> float:
    """Declination of the star at ``year``, in degrees.

    Polar distance is ``90 - dec`` by definition, so declination falls
    straight out of the separation from the pole with no second calculation.
    """
    return 90.0 - separation_from_pole(lam, beta, year)


def is_circumpolar(lam: float, beta: float, latitude: float,
                   year: float) -> bool:
    """Whether the star never sets at ``latitude`` in ``year``.

    Circumpolar means ``dec > 90 - latitude``, which is the same statement
    as ``separation_from_pole < latitude``. Ignores refraction, which
    slightly extends circumpolarity near the limit, and horizon obstruction,
    which does the opposite and by more.
    """
    return separation_from_pole(lam, beta, year) < latitude


def limiting_latitude(lam: float, beta: float, year: float) -> float:
    """Lowest latitude at which the star is circumpolar in ``year``.

    Equal to its separation from the pole. This is epoch-dependent and the
    dependence is strong: a star comfortably circumpolar today can set at
    the same site ten thousand years either side.
    """
    return separation_from_pole(lam, beta, year)


def closest_approach(lam: float, beta: float,
                     near_year: float = 2000.0) -> Tuple[float, float]:
    """Epoch of the star's closest approach to the pole, and that separation.

    Returns ``(year, min_separation_deg)``. The minimum is
    ``|beta - (90 - obliquity)|``, reached when the pole's ecliptic
    longitude matches the star's. The cycle repeats every
    ``PRECESSION_PERIOD`` years; the epoch returned is the one nearest
    ``near_year``.
    """
    min_sep = abs(beta - POLE_ECLIPTIC_LATITUDE)
    base = 2000.0 + ((90.0 - lam) % 360.0) / PRECESSION_RATE
    cycles = round((near_year - base) / PRECESSION_PERIOD)
    return base + cycles * PRECESSION_PERIOD, min_sep


def alignment_window(lam: float, beta: float, tolerance: float,
                     near_year: float = 2000.0) -> Optional[Dict[str, float]]:
    """Years during which the star sits within ``tolerance`` of the pole.

    This is two things at once:

    * **A dating method.** A tradition naming a specific star-at-pole
      configuration is naming this window. Tighten the tolerance to the
      precision the description implies and read the epoch off.
    * **A re-datum interval.** For a monument aligned on this star, the
      window width is how long the alignment holds to that tolerance
      before it has to be re-established. NEG-4's ``recenter`` in years.

    Returns ``None`` when the star never comes within ``tolerance`` of the
    pole -- which is the answer for most stars and is not an error.
    ``duration`` is ``inf`` in the degenerate case where the star never
    leaves the tolerance either.
    """
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    center, min_sep = closest_approach(lam, beta, near_year)
    if tolerance < min_sep:
        return None

    b_p = math.radians(POLE_ECLIPTIC_LATITUDE)
    b_s = math.radians(beta)
    a = math.sin(b_p) * math.sin(b_s)
    b = math.cos(b_p) * math.cos(b_s)

    if b <= 0.0:                                  # star at an ecliptic pole
        return {"center": center, "start": float("-inf"), "end": float("inf"),
                "duration": float("inf"), "min_separation": min_sep}

    c = (math.cos(math.radians(tolerance)) - a) / b
    if c <= -1.0:                                 # never outside tolerance
        return {"center": center, "start": float("-inf"), "end": float("inf"),
                "duration": float("inf"), "min_separation": min_sep}

    half_angle = math.degrees(math.acos(min(1.0, c)))
    half_years = half_angle / PRECESSION_RATE
    return {
        "center": center,
        "start": center - half_years,
        "end": center + half_years,
        "duration": 2.0 * half_years,
        "min_separation": min_sep,
    }


def drift_years_per_degree() -> float:
    """Years for the pole to travel one degree along its circle: ~71.6."""
    return 1.0 / PRECESSION_RATE


def _fmt_year(year: float) -> str:
    """Astronomical year numbering to CE/BCE, for printing."""
    if year > 0:
        return f"{year:.0f} CE"
    return f"{1 - year:.0f} BCE"


if __name__ == "__main__":
    print("MODEL VALIDATION -- known pole stars")
    print(f"  pole travels 1 deg per {drift_years_per_degree():.1f} yr; "
          f"full circuit {PRECESSION_PERIOD:.0f} yr\n")
    print(f"  {'star':10s} {'closest approach':>18s} {'min sep':>9s}   reference")
    references = [
        ("Polaris", 2000, "~2100 CE, ~0.45 deg"),
        ("Thuban", 0, "~2700 BCE"),
        ("Vega", -12000, "~12000 BCE, late glacial"),
        ("Vega", 14000, "same star, next circuit"),
    ]
    for name, near, ref in references:
        lam, beta = equatorial_to_ecliptic(*CATALOG[name])
        year, sep = closest_approach(lam, beta, near_year=near)
        print(f"  {name:10s} {_fmt_year(year):>18s} {sep:8.2f} deg   {ref}")
    print("  Vega appears twice because the pole returns: any 'star at the pole'")
    print("  claim is periodic, and dating one needs the right circuit chosen.")

    print("\nRE-DATUM INTERVAL -- how long an alignment holds")
    print("  (window width at a given tolerance = years before re-aiming)")
    for name in ("Polaris", "Thuban"):
        lam, beta = equatorial_to_ecliptic(*CATALOG[name])
        for tol in (0.5, 1.0, 2.0):
            w = alignment_window(lam, beta, tol)
            if w is None:
                print(f"  {name:10s} tol {tol:>4.1f} deg   never within tolerance")
            else:
                print(f"  {name:10s} tol {tol:>4.1f} deg   "
                      f"{_fmt_year(w['start'])} to {_fmt_year(w['end'])}"
                      f"   ({w['duration']:.0f} yr)")

    print("\nCIRCUMPOLARITY IS EPOCH-DEPENDENT -- Alkaid, the Bear's limiting star")
    lam, beta = equatorial_to_ecliptic(*CATALOG["Alkaid"])
    print(f"  {'epoch':>12s} {'circumpolar above':>19s}  {'never sets at 55N?':>19s}")
    for year in (2000, -2000, -6000, -10000, -12000, -14000):
        limit = limiting_latitude(lam, beta, year)
        cp = is_circumpolar(lam, beta, 55.0, year)
        print(f"  {_fmt_year(year):>12s} {limit:16.1f}N  {'yes' if cp else 'NO':>19s}")
    print("  The Bear is circumpolar above ~41N today, and was circumpolar from")
    print("  ~17N around 6000 BCE -- it was far closer to the pole then. By the")
    print("  late glacial it needed ~48N, and at 14000 BCE the margin at a 55N")
    print("  site was under a degree. 'The Bear never sets' is a true statement")
    print("  about a latitude AND an epoch, not about the Bear.")
