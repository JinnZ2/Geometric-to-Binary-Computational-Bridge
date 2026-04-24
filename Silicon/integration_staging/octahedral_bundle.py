"""
octahedral_bundle.py — Step 1: Live Fiber Substitution
=======================================================
STATUS: STAGING — not yet migrated to Silicon/modules/

This module implements Step 1 of the octahedral integration plan described in
Silicon/modules/Octahedral_Integration.md:

    Replace the static octahedral fiber with the live SiliconState S directly.

The existing octahedral encoding (mappings/octahedral_state_encoding.json,
Silicon/octahedral_state_encoder.json) treats the fiber as a fixed 3-eigenvalue
tensor {λ₁, λ₂, λ₃} with a static mapping to one of eight discrete vertices.

This module replaces that static fiber with the 9D SiliconState vector S(t),
which is already evolving on the dynamical manifold in Silicon/modules/.

What changes
------------
  BEFORE: fiber = {λ₁, λ₂, λ₃}  (static, chosen from 8 canonical patterns)
  AFTER:  fiber = S(t) = (n, μ, T, d_bulk, d_iface, ℓ, κ₁, κ₂, κ₃)  (live, 9D)

The eight octahedral vertices are reinterpreted as extremal points in S-space.
The trajectory's position relative to those vertices is computed as barycentric
coordinates (regime weights), replacing the discrete vertex-bit encoding.

Nothing in Silicon/modules/ is modified by this file.

Classes
-------
  OctahedralVertex     — one of the eight extremal states in S-space
  OctahedralBundle     — the full bundle: base φ(x), fiber S(t), vertex atlas
  BarycentricPosition  — barycentric coordinates of S(t) within the octahedron

Functions
---------
  build_vertex_atlas()     — construct the eight extremal vertices from the
                             canonical JSON encoding + physical S-space bounds
  project_to_barycentric() — compute barycentric coords of any S within atlas
  bundle_from_pipeline()   — wrap a PipelineResult as an OctahedralBundle
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import sys, os

# ── Path: allow running standalone or imported from staging ──────────────────
_HERE    = os.path.dirname(os.path.abspath(__file__))
_SILICON = os.path.dirname(_HERE)
_MODULES = os.path.join(_SILICON, "modules")
if _MODULES not in sys.path:
    sys.path.insert(0, _MODULES)

from state import SiliconState, make_state   # from Silicon/modules/state.py


# ── Physical S-space bounds for each state dimension ─────────────────────────
# These define the corners of the hypercube within which the octahedral
# vertices are embedded.  Values are chosen to span the physically meaningful
# range of each coordinate.

S_BOUNDS = {
    # index: (name, low_extreme, high_extreme)
    0: ("n",       1e14,   1e20),    # carrier density cm⁻³
    1: ("mu",      100.0,  1500.0),  # mobility cm²/Vs
    2: ("T",       77.0,   500.0),   # temperature K
    3: ("d_bulk",  0.0,    1.0),     # bulk defect density
    4: ("d_iface", 0.0,    1.0),     # interface defect density
    5: ("l",       1.0,    100.0),   # feature length nm
    6: ("k1",      0.0,    2.0),     # κ₁ coupling
    7: ("k2",      0.0,    2.0),     # κ₂ coupling
    8: ("k3",      0.0,    2.0),     # κ₃ coupling
}

# Normalise S to [0,1]^9 for distance calculations
def _normalise(vec: np.ndarray) -> np.ndarray:
    lo  = np.array([S_BOUNDS[i][1] for i in range(9)])
    hi  = np.array([S_BOUNDS[i][2] for i in range(9)])
    return np.clip((vec - lo) / (hi - lo + 1e-30), 0.0, 1.0)


# ── Octahedral vertices in S-space ────────────────────────────────────────────

# The eight canonical octahedral states from octahedral_state_encoding.json
# are mapped to extremal points in S-space.  Each vertex is a named corner
# of the physical hypercube, chosen to match the character of the original
# geometric state (spherical, elongated, compressed, diagonal, etc.).
#
# Mapping rationale (from octahedral_state_encoding.json "character" field):
#   000 (+x)  spherical         → balanced, high-n, low-defect, mid-κ
#   001 (-x)  elongated +x      → high-n, high-μ, low-defect, high-κ₁
#   010 (+y)  elongated +y      → high-n, high-μ, low-defect, high-κ₂
#   011 (-y)  elongated +z      → high-n, high-μ, low-defect, high-κ₃
#   100 (+z)  compressed -z     → low-n, high-T, high-defect, low-κ
#   101 (-z)  biaxial xy        → mid-n, mid-T, mid-defect, high-κ₁κ₂
#   110 diag-a asymmetric diag  → low-n, low-T, low-defect, high-κ₁κ₂
#   111 diag-b near-biaxial     → low-n, low-T, high-defect, high-κ₂κ₃

_VERTEX_SPECS = [
    # (bits, label, character, S-space kwargs)
    ("000", "+x",      "spherical",          dict(n=5e17, mu=1200., T=300., d_bulk=0.05, d_iface=0.05, l=5.,  k1=1.0, k2=1.0, k3=1.0)),
    ("001", "-x",      "elongated +x",       dict(n=1e19, mu=1450., T=280., d_bulk=0.01, d_iface=0.01, l=2.,  k1=1.8, k2=0.5, k3=0.3)),
    ("010", "+y",      "elongated +y",       dict(n=1e19, mu=1450., T=280., d_bulk=0.01, d_iface=0.01, l=2.,  k1=0.3, k2=1.8, k3=0.5)),
    ("011", "-y",      "elongated +z",       dict(n=1e19, mu=1450., T=280., d_bulk=0.01, d_iface=0.01, l=2.,  k1=0.3, k2=0.5, k3=1.8)),
    ("100", "+z",      "compressed -z",      dict(n=1e15, mu=200.,  T=450., d_bulk=0.80, d_iface=0.80, l=50., k1=0.2, k2=0.2, k3=0.2)),
    ("101", "-z",      "biaxial xy",         dict(n=5e16, mu=800.,  T=350., d_bulk=0.30, d_iface=0.30, l=15., k1=1.4, k2=1.4, k3=0.4)),
    ("110", "diag-a",  "asymmetric diag",    dict(n=1e15, mu=300.,  T=200., d_bulk=0.05, d_iface=0.05, l=20., k1=1.6, k2=1.2, k3=0.4)),
    ("111", "diag-b",  "near-biaxial diag",  dict(n=1e15, mu=300.,  T=200., d_bulk=0.60, d_iface=0.60, l=20., k1=0.4, k2=1.4, k3=1.4)),
]


@dataclass
class OctahedralVertex:
    """
    One of the eight extremal states in S-space, corresponding to an octahedral
    vertex from the canonical encoding.

    Attributes
    ----------
    bits      : str          — 3-bit Gray-code vertex identifier (e.g. "000")
    label     : str          — geometric label (e.g. "+x", "diag-a")
    character : str          — physical character from encoding JSON
    state     : SiliconState — the S-space position of this vertex
    vec_norm  : np.ndarray   — normalised [0,1]^9 position for distance calcs
    """
    bits      : str
    label     : str
    character : str
    state     : SiliconState
    vec_norm  : np.ndarray = field(repr=False)

    def __repr__(self) -> str:
        return (f"OctahedralVertex({self.bits} | {self.label} | "
                f"{self.character} | n={self.state.n:.2e})")


def build_vertex_atlas() -> list[OctahedralVertex]:
    """
    Construct the eight OctahedralVertex objects from the physical S-space
    extremal points defined in _VERTEX_SPECS.

    Returns
    -------
    list[OctahedralVertex], length 8, ordered by vertex index 0–7
    """
    vertices = []
    for bits, label, character, kwargs in _VERTEX_SPECS:
        s = make_state(**kwargs)
        vertices.append(OctahedralVertex(
            bits      = bits,
            label     = label,
            character = character,
            state     = s,
            vec_norm  = _normalise(s.vec),
        ))
    return vertices


# ── Barycentric position ──────────────────────────────────────────────────────

@dataclass
class BarycentricPosition:
    """
    Barycentric coordinates of a silicon state S(t) within the octahedral
    vertex atlas.

    The coordinates are computed as inverse-distance weights in normalised
    S-space, giving a continuous probability distribution over the eight
    vertices.  This replaces the discrete vertex-bit encoding.

    Attributes
    ----------
    weights       : np.ndarray shape (8,)  — barycentric weights, sum to 1
    dominant_idx  : int                    — index of the highest-weight vertex
    dominant_bits : str                    — bits of the dominant vertex
    dominant_label: str                    — label of the dominant vertex
    distances     : np.ndarray shape (8,)  — Euclidean distances in norm space
    """
    weights       : np.ndarray
    dominant_idx  : int
    dominant_bits : str
    dominant_label: str
    distances     : np.ndarray

    def __repr__(self) -> str:
        top = sorted(zip(self.weights, range(8)), reverse=True)[:3]
        parts = [f"v{i}={w:.3f}" for w, i in top]
        return f"BarycentricPosition(dominant={self.dominant_bits}|{self.dominant_label}  [{', '.join(parts)}])"

    def as_dict(self) -> dict:
        return {
            "weights"       : self.weights.tolist(),
            "dominant_bits" : self.dominant_bits,
            "dominant_label": self.dominant_label,
            "distances"     : self.distances.tolist(),
        }


def project_to_barycentric(
    S: SiliconState,
    vertices: list[OctahedralVertex],
    epsilon: float = 1e-8,
) -> BarycentricPosition:
    """
    Compute the barycentric position of silicon state S within the vertex atlas.

    Uses inverse-distance weighting in normalised S-space:
        w_i = (1 / d_i) / Σ(1 / d_j)
    where d_i = ||S_norm - v_i_norm||₂.

    If S coincides exactly with a vertex (d_i < epsilon), that vertex receives
    weight 1 and all others receive weight 0.

    Parameters
    ----------
    S        : SiliconState
    vertices : list[OctahedralVertex]
    epsilon  : float — distance threshold for exact-vertex detection

    Returns
    -------
    BarycentricPosition
    """
    s_norm = _normalise(S.vec)
    dists  = np.array([np.linalg.norm(s_norm - v.vec_norm) for v in vertices])

    # Exact vertex hit
    exact = np.where(dists < epsilon)[0]
    if len(exact) > 0:
        weights = np.zeros(8)
        weights[exact[0]] = 1.0
    else:
        inv_d  = 1.0 / dists
        weights = inv_d / inv_d.sum()

    dom = int(np.argmax(weights))
    return BarycentricPosition(
        weights        = weights,
        dominant_idx   = dom,
        dominant_bits  = vertices[dom].bits,
        dominant_label = vertices[dom].label,
        distances      = dists,
    )


# ── OctahedralBundle ──────────────────────────────────────────────────────────

@dataclass
class OctahedralBundle:
    """
    The full octahedral bundle: base manifold + live fiber + vertex atlas.

    This is the central object of Step 1.  It holds:
      - The geometry field φ(x) as the base manifold
      - The live silicon state S(t) as the fiber
      - The eight vertex atlas for barycentric projection
      - The current barycentric position of S within the octahedron

    The encoding is no longer a fixed frame.  At each time step, calling
    update(S, phi) moves the fiber and recomputes the barycentric position,
    making the encoding a dynamical section of the bundle.

    Attributes
    ----------
    vertices    : list[OctahedralVertex]  — the eight extremal S-space vertices
    state       : SiliconState            — current fiber (live S(t))
    phi         : np.ndarray              — current base field φ(x)
    x           : np.ndarray              — spatial grid
    position    : BarycentricPosition     — current barycentric position
    history     : list[dict]             — trajectory of (t, position, state)
    """
    vertices : list[OctahedralVertex]
    state    : SiliconState
    phi      : np.ndarray
    x        : np.ndarray
    position : BarycentricPosition = field(init=False)
    history  : list = field(default_factory=list, repr=False)

    def __post_init__(self):
        self.position = project_to_barycentric(self.state, self.vertices)

    def update(self, S: SiliconState, phi: np.ndarray, t: float = 0.0) -> BarycentricPosition:
        """
        Move the fiber to a new state S and recompute the barycentric position.

        Parameters
        ----------
        S   : SiliconState — new fiber state
        phi : np.ndarray   — new base field φ(x)
        t   : float        — current time (for history)

        Returns
        -------
        BarycentricPosition — updated position
        """
        self.state    = S
        self.phi      = phi
        self.position = project_to_barycentric(S, self.vertices)
        self.history.append({
            "t"       : t,
            "position": self.position.as_dict(),
            "state"   : S.vec.copy(),
        })
        return self.position

    def dominant_vertex(self) -> OctahedralVertex:
        """Return the currently dominant vertex."""
        return self.vertices[self.position.dominant_idx]

    def weight_array(self) -> np.ndarray:
        """Return the current 8-weight barycentric array."""
        return self.position.weights

    def history_weights(self) -> np.ndarray:
        """Return all historical barycentric weights as shape (T, 8) array."""
        return np.array([h["position"]["weights"] for h in self.history])

    def history_times(self) -> np.ndarray:
        """Return all historical time values."""
        return np.array([h["t"] for h in self.history])

    def __repr__(self) -> str:
        return (
            f"OctahedralBundle(\n"
            f"  fiber    = {self.state}\n"
            f"  position = {self.position}\n"
            f"  history  = {len(self.history)} steps\n"
            f")"
        )


# ── Factory: wrap a PipelineResult ───────────────────────────────────────────

def bundle_from_pipeline(result) -> tuple[OctahedralBundle, np.ndarray]:
    """
    Construct an OctahedralBundle from a completed PipelineResult and replay
    the full trajectory through it, recording barycentric positions at each step.

    Parameters
    ----------
    result : PipelineResult (from Silicon/modules/pipeline.py)

    Returns
    -------
    (OctahedralBundle, weight_history)
      OctahedralBundle  — bundle at final state
      weight_history    — np.ndarray shape (T, 8), barycentric weights over time
    """
    vertices = build_vertex_atlas()
    times    = np.array(result.times)
    states   = result.state_array()
    phi_arr  = np.array(result.phi_fields)
    x        = result.x

    # Initialise at step 0
    S0  = make_state(*states[0])
    phi0 = phi_arr[0]
    bundle = OctahedralBundle(vertices=vertices, state=S0, phi=phi0, x=x)
    bundle.history.append({
        "t"       : float(times[0]),
        "position": bundle.position.as_dict(),
        "state"   : states[0].copy(),
    })

    # Replay trajectory
    for i in range(1, len(times)):
        Si  = make_state(*states[i])
        phi_i = phi_arr[i]
        bundle.update(Si, phi_i, t=float(times[i]))

    return bundle, bundle.history_weights()
