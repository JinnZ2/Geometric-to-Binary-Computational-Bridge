"""Energy-pattern claims: what is settled by symmetry and arithmetic.

Settles EPG-4, EPG-6, EPG-7, EPG-8 from Energy-pattern.md. Stdlib only.
EPG-1, EPG-2, EPG-3 need two copper samples and are not addressable here.
"""

from __future__ import annotations

import itertools
import math
from typing import Dict, List, Sequence, Set, Tuple

__all__ = [
    "KB_EV", "TETRAHEDRAL_DEG", "SI_LATTICE_A", "MECHANISMS", "PARITY",
    "cubic_rotations", "reynolds_average", "cubic_isotropic",
    "diamond_cubic_basis", "nearest_neighbours", "bond_angles",
    "tetrahedral_vectors", "min_pairwise_angle", "maximin_bound",
    "sampled_maximin_never_exceeds_bound", "defect_floor",
    "surviving_mechanisms", "degenerate_pairs", "discriminator_power", "main",
]

KB_EV = 8.617333262e-5              # eV/K
TETRAHEDRAL_DEG = math.degrees(math.acos(-1.0 / 3.0))
SI_LATTICE_A = 5.431

#: Candidate mechanisms for the 1990s observation, with their parity in the
#: substrate current. ``none`` means the mechanism does not involve the current
#: at all. ``needs_plasma`` marks mechanisms that vanish without a sheath.
MECHANISMS: Dict[str, Dict[str, object]] = {
    "M0": {"name": "substrate rolling texture", "parity": "none",
           "needs_plasma": False, "tracks": "foil"},
    "M1": {"name": "lateral sheath potential gradient", "parity": "odd",
           "needs_plasma": True, "tracks": "current"},
    "M2": {"name": "Joule heating gradient", "parity": "even",
           "needs_plasma": False, "tracks": "current"},
    "M3": {"name": "surface electromigration", "parity": "odd",
           "needs_plasma": False, "tracks": "current"},
    "M4": {"name": "thermomigration (Soret)", "parity": "even",
           "needs_plasma": False, "tracks": "current"},
}

PARITY = {k: v["parity"] for k, v in MECHANISMS.items()}


# ---------------------------------------------------------------------------
# EPG-7: cubic symmetry forbids transport anisotropy
# ---------------------------------------------------------------------------

def cubic_rotations() -> List[List[List[int]]]:
    """The 24 proper rotations of O: signed permutation matrices with det +1."""
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            m = [[0, 0, 0] for _ in range(3)]
            for i in range(3):
                m[i][perm[i]] = signs[i]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                   - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            if det == 1:
                out.append(m)
    return out


def reynolds_average(tensor: Sequence[Sequence[float]]) -> List[List[float]]:
    """Average R.T.R^T over the cubic group -- the part of T symmetry allows."""
    group = cubic_rotations()
    acc = [[0.0] * 3 for _ in range(3)]
    for r in group:
        rt = [[sum(r[i][k] * tensor[k][l] for k in range(3)) for l in range(3)]
              for i in range(3)]
        m = [[sum(rt[i][l] * r[j][l] for l in range(3)) for j in range(3)]
             for i in range(3)]
        for i in range(3):
            for j in range(3):
                acc[i][j] += m[i][j] / len(group)
    return acc


def cubic_isotropic(tensor: Sequence[Sequence[float]],
                    tol: float = 1e-12) -> Dict[str, object]:
    """Is a rank-2 tensor cubic-invariant, and is the invariant part isotropic?

    Neumann's principle: a material property tensor must be invariant under the
    crystal point group. For a rank-2 tensor in a cubic crystal the only
    invariant form is lambda*I, so conductivity -- thermal or electrical -- has
    no direction to be anisotropic in. This is a theorem, so no measurement can
    return a 1.5x [111]/[100] ratio.
    """
    avg = reynolds_average(tensor)
    off = max(abs(avg[i][j]) for i in range(3) for j in range(3) if i != j)
    spread = max(avg[i][i] for i in range(3)) - min(avg[i][i] for i in range(3))
    return {"averaged": avg, "worst_offdiagonal": off,
            "diagonal_spread": spread,
            "lambda": sum(avg[i][i] for i in range(3)) / 3.0,
            "isotropic": off <= tol and spread <= tol}


# ---------------------------------------------------------------------------
# EPG-6: 8 atoms, 6 vertices, 8 corners, and one angle
# ---------------------------------------------------------------------------

def diamond_cubic_basis() -> List[Tuple[float, float, float]]:
    """The 8 fractional sites of the conventional diamond-cubic cell.

    Two interpenetrating FCC lattices offset by (1/4,1/4,1/4). Eight ATOMS,
    not eight vertices: a cube has 8 corners and an octahedron has 6 vertices,
    and the three counts were merged in the documents this settles.
    """
    fcc = [(0.0, 0.0, 0.0), (0.0, .5, .5), (.5, 0.0, .5), (.5, .5, 0.0)]
    return fcc + [((x + .25) % 1, (y + .25) % 1, (z + .25) % 1)
                  for x, y, z in fcc]


def nearest_neighbours(a: float = SI_LATTICE_A,
                       cutoff_a: float = 3.0) -> List[Tuple[float, Tuple]]:
    """Neighbours of the origin site within ``cutoff_a`` angstroms, sorted."""
    basis = diamond_cubic_basis()
    out = []
    for shift in itertools.product((-1, 0, 1), repeat=3):
        for p in basis:
            q = ((p[0] + shift[0]) * a, (p[1] + shift[1]) * a,
                 (p[2] + shift[2]) * a)
            d = math.sqrt(sum(x * x for x in q))
            if 1e-6 < d < cutoff_a:
                out.append((d, q))
    out.sort(key=lambda t: t[0])
    return out


def bond_angles(a: float = SI_LATTICE_A) -> List[float]:
    """The six angles between the four nearest-neighbour bonds, degrees."""
    nn = [q for _, q in nearest_neighbours(a)[:4]]
    if len(nn) != 4:
        raise ValueError("did not find four nearest neighbours")
    angles = []
    for i in range(4):
        for j in range(i + 1, 4):
            u, v = nn[i], nn[j]
            nu = math.sqrt(sum(x * x for x in u))
            nv = math.sqrt(sum(x * x for x in v))
            c = sum(x * y for x, y in zip(u, v)) / (nu * nv)
            angles.append(math.degrees(math.acos(max(-1.0, min(1.0, c)))))
    return angles


def tetrahedral_vectors() -> List[Tuple[float, float, float]]:
    """Four unit vectors along the sp3 bond directions, pairwise dot = -1/3."""
    s = 1.0 / math.sqrt(3.0)
    return [(s, s, s), (-s, -s, s), (-s, s, -s), (s, -s, -s)]


def min_pairwise_angle(vs: Sequence[Sequence[float]]) -> float:
    """Smallest angle between any two of the given vectors, degrees."""
    n = len(vs)
    if n < 2:
        raise ValueError("need at least two vectors")
    unit = []
    for v in vs:
        m = math.sqrt(sum(x * x for x in v))
        if m <= 0.0:
            raise ValueError("zero-length vector")
        unit.append([x / m for x in v])
    return math.degrees(min(
        math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(unit[i], unit[j])))))
        for i in range(n) for j in range(i + 1, n)))


def maximin_bound() -> Dict[str, float]:
    """Prove the tetrahedral angle is the maximum of the minimum separation.

    Not a numerical search -- a two-line identity. For any four unit vectors,

        |sum(v_i)|^2 = 4 + 2 * sum_{i<j} v_i . v_j  >=  0

    so the six pairwise dot products sum to at least -2 and their mean is at
    least -1/3. The smallest dot in any configuration is at most the mean, so
    it is at most -1/3 only when every dot equals -1/3 -- otherwise some pair
    sits above the mean and closes the minimum angle. Maximising the smallest
    separation therefore forces all six dots equal to -1/3, which is the
    regular tetrahedron, at arccos(-1/3) = 109.47 deg.

    This is what EPG-6 means by "derived in one line". Nothing searched, nothing
    competed, and the same identity holds in any dimension. A configuration
    beating this bound would falsify it, which is what
    ``sampled_maximin_never_exceeds_bound`` checks.
    """
    vs = tetrahedral_vectors()
    dots = [sum(a * b for a, b in zip(vs[i], vs[j]))
            for i in range(4) for j in range(i + 1, 4)]
    resultant = [sum(v[k] for v in vs) for k in range(3)]
    return {
        "dot_sum": sum(dots),
        "dot_mean": sum(dots) / len(dots),
        "min_dot": min(dots),
        "max_dot": max(dots),
        "resultant_norm": math.sqrt(sum(x * x for x in resultant)),
        "angle_deg": min_pairwise_angle(vs),
        "bound_deg": TETRAHEDRAL_DEG,
    }


def sampled_maximin_never_exceeds_bound(samples: int = 20000,
                                        seed: int = 0) -> Dict[str, float]:
    """Sample four-vector configurations; none may beat arccos(-1/3).

    The falsifiable direction. A search that fell short of the bound would only
    mean the search was weak, so what is tested is that nothing EXCEEDS it.
    """
    import random
    rng = random.Random(seed)
    best = 0.0
    for _ in range(samples):
        vs = []
        for _ in range(4):
            v = [rng.gauss(0, 1) for _ in range(3)]
            n = math.sqrt(sum(x * x for x in v))
            if n <= 0.0:
                n = 1.0
            vs.append([x / n for x in v])
        best = max(best, min_pairwise_angle(vs))
    return {"samples": samples, "best_deg": best, "bound_deg": TETRAHEDRAL_DEG,
            "exceeded": best > TETRAHEDRAL_DEG + 1e-9}


# ---------------------------------------------------------------------------
# EPG-4: the free-energy floor on self-assembled defect density
# ---------------------------------------------------------------------------

def defect_floor(pitch_nm: float = 25.0, target_per_cm2: float = 0.01,
                 temp_c: float = 250.0) -> Dict[str, float]:
    """Formation energy a self-assembled phase needs to hit a defect target.

    Equilibrium defect probability per site is exp(-E_f/kT), so a target
    density fixes a required E_f/kT. For logic at 0.01 defects/cm^2 this lands
    near 30 kT, against measured block-copolymer dislocation and disclination
    energies of a few kT to ~10 kT. The gap is a free-energy statement, which
    is why tighter process control does not close it.
    """
    if pitch_nm <= 0.0 or target_per_cm2 <= 0.0:
        raise ValueError("need pitch > 0 and target > 0")
    features = (1e7 / pitch_nm) ** 2          # 1 cm = 1e7 nm
    p_allowed = target_per_cm2 / features
    ratio = -math.log(p_allowed)
    kt = KB_EV * (temp_c + 273.15)
    return {"features_per_cm2": features, "p_allowed": p_allowed,
            "required_ef_over_kt": ratio, "kt_ev": kt,
            "required_ef_ev": ratio * kt}


# ---------------------------------------------------------------------------
# EPG-8: the discriminator matrix
# ---------------------------------------------------------------------------

def surviving_mechanisms(tracks_current_under_rotation: bool,
                         reverses_with_polarity: bool,
                         survives_without_plasma: bool) -> Dict[str, object]:
    """Mechanisms compatible with three binary observations.

    The three tests are the ones the document specifies:

    * rotate the foil 90 deg -- does the pattern follow the current or the foil
    * reverse the polarity   -- does the pattern direction reverse
    * remove the plasma      -- does the effect survive with evaporated Si

    Four discriminators against five mechanisms is over-determined, so some
    observation sets are compatible with nothing. An empty result means the
    model is incomplete or a measurement is wrong; it does not mean "pick the
    closest". That distinction is the point of returning a set.
    """
    survivors: Set[str] = set()
    for mid, m in MECHANISMS.items():
        if not tracks_current_under_rotation:
            if m["tracks"] == "foil":
                survivors.add(mid)
            continue
        if m["tracks"] != "current":
            continue
        if reverses_with_polarity and m["parity"] != "odd":
            continue
        if not reverses_with_polarity and m["parity"] != "even":
            continue
        if not survives_without_plasma and not m["needs_plasma"]:
            continue
        if survives_without_plasma and m["needs_plasma"]:
            continue
        survivors.add(mid)
    return {
        "surviving": sorted(survivors),
        "names": [MECHANISMS[m]["name"] for m in sorted(survivors)],
        "resolved": len(survivors) == 1,
        "consistent": len(survivors) > 0,
        "note": ("no mechanism matches: model incomplete or a measurement is "
                 "wrong" if not survivors else
                 "uniquely resolved" if len(survivors) == 1 else
                 "ambiguous: more discriminators needed"),
    }


def degenerate_pairs() -> List[Tuple[str, str]]:
    """Mechanism pairs no observation in the matrix can separate.

    M2 and M4 come out degenerate: both are EVEN in I and both survive without
    a plasma, because both are driven by the same grad-T that Joule heating
    produces. The document lists "external heater, same dT, I = 0" as M4's
    separator, but that test reproduces M2 equally well -- it separates thermal
    from electrical, not Soret drift from nucleation-density variation.

    This does not affect EPG-1, which only asks current-or-foil. It does mean
    the matrix resolves four of five mechanisms, not five.
    """
    seen: Dict[Tuple, List[str]] = {}
    for mid, m in MECHANISMS.items():
        key = (m["tracks"], m["parity"], m["needs_plasma"])
        seen.setdefault(key, []).append(mid)
    pairs = []
    for group in seen.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pairs.append((group[i], group[j]))
    return sorted(pairs)


def discriminator_power() -> Dict[str, object]:
    """Enumerate the whole 2^3 observation space and report what it resolves."""
    rows = []
    resolved = 0
    for rot in (False, True):
        for pol in (False, True):
            for pla in (False, True):
                r = surviving_mechanisms(rot, pol, pla)
                rows.append({"tracks_current": rot, "reverses": pol,
                             "no_plasma_ok": pla,
                             "surviving": r["surviving"]})
                if r["resolved"]:
                    resolved += 1
    return {"rows": rows, "cases": len(rows), "uniquely_resolved": resolved,
            "mechanisms": len(MECHANISMS)}


# ---------------------------------------------------------------------------

def main() -> None:
    print("ENERGY-PATTERN BOUNDS\n" + "=" * 58)

    print("\nEPG-6  the tetrahedral angle is forced, not selected")
    mb = maximin_bound()
    print(f"  arccos(-1/3)              = {TETRAHEDRAL_DEG:.6f} deg")
    print(f"  sum of 6 pairwise dots    = {mb['dot_sum']:+.1f} (identity floor -2)")
    print(f"  resultant |sum(v_i)|      = {mb['resultant_norm']:.2e} (equality case)")
    print(f"  min separation achieved   = {mb['angle_deg']:.6f} deg")
    sm = sampled_maximin_never_exceeds_bound(samples=5000)
    print(f"  {sm['samples']} random configs: best {sm['best_deg']:.4f} deg,"
          f" exceeded bound = {sm['exceeded']}")
    basis = diamond_cubic_basis()
    nn = nearest_neighbours()
    ang = bond_angles()
    print(f"  atoms in conventional cell = {len(set(basis))} (not 8 vertices)")
    print(f"  nearest neighbours = {len([1 for d, _ in nn if d < 2.4])}"
          f" at {nn[0][0]:.4f} A")
    print(f"  bond angles = {min(ang):.4f}..{max(ang):.4f} deg")
    print("  cube corners 8, octahedron vertices 6, octahedron faces 8")

    print("\nEPG-7  cubic symmetry forbids transport anisotropy")
    t = [[2.0, 0.7, -0.3], [0.7, 1.0, 0.4], [-0.3, 0.4, -1.0]]
    r = cubic_isotropic(t)
    print(f"  worst off-diagonal after group average = {r['worst_offdiagonal']:.2e}")
    print(f"  diagonal spread                        = {r['diagonal_spread']:.2e}")
    print(f"  isotropic = {r['isotropic']}, lambda = {r['lambda']:.4f}")
    print("  no 1.5x [111]/[100] ratio is available to align vias to")

    print("\nEPG-4  defect-density free-energy floor")
    for pitch in (20.0, 25.0, 30.0):
        d = defect_floor(pitch)
        print(f"  pitch {pitch:4.0f} nm: {d['features_per_cm2']:.2e} features/cm^2,"
              f" need E_f/kT >= {d['required_ef_over_kt']:.1f}"
              f" = {d['required_ef_ev']:.2f} eV at 250 C")
    print("  measured BCP defect energies are a few kT to ~10 kT")

    print("\nEPG-8  discriminator matrix")
    dp = discriminator_power()
    print(f"  {dp['cases']} observation cases,"
          f" {dp['uniquely_resolved']} uniquely resolve one of"
          f" {dp['mechanisms']} mechanisms")
    for row in dp["rows"]:
        flag = "" if row["surviving"] else "   <- consistent with nothing"
        print(f"    current={int(row['tracks_current'])}"
              f" reverses={int(row['reverses'])}"
              f" no_plasma={int(row['no_plasma_ok'])}"
              f" -> {row['surviving'] or '[]'}{flag}")
    print("  M1 and M3 are both ODD in I, so polarity reversal cannot")
    print("  separate them; removing the plasma does.")
    print(f"  degenerate pairs, unseparable by this matrix: {degenerate_pairs()}")
    print("  M2/M4 are both thermal and both even; the external-heater test")
    print("  separates thermal from electrical, not Soret from nucleation.")


if __name__ == "__main__":
    main()
