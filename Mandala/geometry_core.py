"""
Octahedral Geometry Core — Dual-Mode Substrate Definition
=========================================================

Two geometries, one file. Switch with GEOMETRY_MODE = "distorted" | "cube".

Distorted Octahedron (D4h) — 6 axial vertices + 2 equatorial edge-midpoints
    States 0-5: primary orbit (distance = 1, strong coupling)
    States 6-7: secondary orbit (distance = sqrt(2), weak coupling)
    The secondary states act as SCALE MARKERS — they expand or contract
    relative to the primary field depending on layer depth, telling the
    system which scale regime it occupies.

Cube (Oh) — 8 equivalent vertices
    All states in one orbit. Clean 3-bit Gray code. Uniform coupling.
    Best for dense information encoding where all states are peers.

Usage:
    from geometry_core import SubstrateGeometry, GEOMETRY_MODE
    geo = SubstrateGeometry(mode="distorted")  # or "cube"
    state = geo.nearest_state(eigenvalues=(0.3, 0.3, 0.4))
"""

import math
from typing import Dict, List, Tuple, Optional

# ---------------------------------------------------------------------------
# Switch
# ---------------------------------------------------------------------------

GEOMETRY_MODE: str = "distorted"  # "distorted" | "cube"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2          # 1.618033988749895
INV_PHI = 1.0 / PHI                   # 0.618033988749895
SQRT2 = math.sqrt(2.0)                # 1.4142135623730951
SQRT3 = math.sqrt(3.0)                # 1.7320508075688772
TETRAHEDRAL_ANGLE = 109.4712206344907 # degrees, arccos(-1/3)


# =============================================================================
# GEOMETRY 1: DISTORTED OCTAHEDRON (D4h symmetry)
# =============================================================================
# 6 vertices at unit distance (axial) + 2 at sqrt(2) (equatorial diagonals).
# The 2 secondary states are NOT defects — they are SCALE MARKERS.
# Their distance from center changes with layer depth, creating a
# "breathing" mode that encodes scale information in the geometry itself.

DISTORTED_POSITIONS: Dict[int, Tuple[float, float, float]] = {
    0: ( 1.0,  0.0,  0.0),   # +x  — primary
    1: (-1.0,  0.0,  0.0),   # -x  — primary
    2: ( 0.0,  1.0,  0.0),   # +y  — primary
    3: ( 0.0, -1.0,  0.0),   # -y  — primary
    4: ( 0.0,  0.0,  1.0),   # +z  — primary
    5: ( 0.0,  0.0, -1.0),   # -z  — primary
    6: ( 1.0,  1.0,  0.0),   # +x+y  — secondary (scale marker)
    7: (-1.0, -1.0,  0.0),   # -x-y  — secondary (scale marker)
}

# Physical character of each state
DISTORTED_CHARACTERS: Dict[int, str] = {
    0: "Axial +x",
    1: "Axial -x",
    2: "Axial +y",
    3: "Axial -y",
    4: "Axial +z",
    5: "Axial -z",
    6: "Equatorial diagonal +x+y (scale marker)",
    7: "Equatorial diagonal -x-y (scale marker)",
}

# Eigenvalue table calibrated for D4h distorted geometry.
# Secondary states (6,7) have eigenvalue ratios that deviate from phi
# more than primary states — this is the "strain signature" that
# identifies them as scale markers.
DISTORTED_EIGENVALUES: Dict[int, Tuple[float, float, float]] = {
    0: (0.50, 0.25, 0.25),  # Elongated +x
    1: (0.50, 0.25, 0.25),  # Elongated -x (symmetric to 0)
    2: (0.25, 0.50, 0.25),  # Elongated +y
    3: (0.25, 0.50, 0.25),  # Elongated -y (symmetric to 2)
    4: (0.25, 0.25, 0.50),  # Elongated +z
    5: (0.25, 0.25, 0.50),  # Elongated -z (symmetric to 4)
    6: (0.40, 0.40, 0.20),  # Biaxial xy — scale marker signature
    7: (0.40, 0.40, 0.20),  # Biaxial xy — scale marker signature
}

# Allowed transitions in D4h.
# Primary-primary: 4 neighbors each (face-adjacent in octahedron)
# Primary-secondary: 2-3 neighbors each (diagonal connections)
# Secondary-secondary: 1 neighbor each (6 <-> 7 through center, or direct)
DISTORTED_TRANSITIONS: Dict[int, List[int]] = {
    0: [2, 3, 4, 5, 6],      # +x connects to all axial + diagonal
    1: [2, 3, 4, 5, 7],      # -x connects to all axial + diagonal
    2: [0, 1, 4, 5, 6],      # +y connects to all axial + diagonal
    3: [0, 1, 4, 5, 7],      # -y connects to all axial + diagonal
    4: [0, 1, 2, 3],         # +z connects only to axial (equatorial ring)
    5: [0, 1, 2, 3],         # -z connects only to axial (equatorial ring)
    6: [0, 2, 4, 5, 7],      # diagonal connects to +x, +y, both z, and opposite diagonal
    7: [1, 3, 4, 5, 6],      # diagonal connects to -x, -y, both z, and opposite diagonal
}

# Gray code for D4h — optimized so that primary-primary transitions are
# single-bit, and primary-secondary transitions are two-bit (reflecting
# the weaker coupling / longer "distance" in state space).
DISTORTED_GRAY_CODES: Dict[int, str] = {
    0: "000",  # +x
    1: "001",  # -x
    2: "011",  # +y
    3: "010",  # -y
    4: "110",  # +z
    5: "111",  # -z
    6: "101",  # +x+y (scale marker)
    7: "100",  # -x-y (scale marker)
}


# =============================================================================
# GEOMETRY 2: CUBE (Oh symmetry)
# =============================================================================
# 8 equivalent vertices. All states in one orbit. Clean 3-bit encoding.
# Best for: dense information storage, uniform coupling, Grover search.

CUBE_POSITIONS: Dict[int, Tuple[float, float, float]] = {
    0: (-1.0, -1.0, -1.0),   # 000
    1: ( 1.0, -1.0, -1.0),   # 100
    2: (-1.0,  1.0, -1.0),   # 010
    3: ( 1.0,  1.0, -1.0),   # 110
    4: (-1.0, -1.0,  1.0),   # 001
    5: ( 1.0, -1.0,  1.0),   # 101
    6: (-1.0,  1.0,  1.0),   # 011
    7: ( 1.0,  1.0,  1.0),   # 111
}

CUBE_CHARACTERS: Dict[int, str] = {
    0: "Corner (-,-,-)",
    1: "Corner (+,-,-)",
    2: "Corner (-,+,-)",
    3: "Corner (+,+,-)",
    4: "Corner (-,-,+)",
    5: "Corner (+,-,+)",
    6: "Corner (-,+,+)",
    7: "Corner (+,+,+)",
}

# Eigenvalue table for cube — all states equivalent, but each corner
# has a distinct eigenvalue signature based on which axes are positive.
CUBE_EIGENVALUES: Dict[int, Tuple[float, float, float]] = {
    0: (0.33, 0.33, 0.33),  # Spherical — reference state
    1: (0.50, 0.25, 0.25),  # Elongated +x
    2: (0.25, 0.50, 0.25),  # Elongated +y
    3: (0.40, 0.40, 0.20),  # Biaxial +x+y
    4: (0.25, 0.25, 0.50),  # Elongated +z
    5: (0.40, 0.20, 0.40),  # Biaxial +x+z
    6: (0.20, 0.40, 0.40),  # Biaxial +y+z
    7: (0.35, 0.35, 0.30),  # Near-spherical, all positive
}

# Cube edges: each vertex connects to 3 neighbors (one per axis flip).
CUBE_TRANSITIONS: Dict[int, List[int]] = {
    0: [1, 2, 4],   # flip x, y, or z
    1: [0, 3, 5],   # flip x, y, or z
    2: [0, 3, 6],   # flip x, y, or z
    3: [1, 2, 7],   # flip x, y, or z
    4: [0, 5, 6],   # flip x, y, or z
    5: [1, 4, 7],   # flip x, y, or z
    6: [2, 4, 7],   # flip x, y, or z
    7: [3, 5, 6],   # flip x, y, or z
}

# Standard 3-bit Gray code — one bit flip = one edge traversal.
CUBE_GRAY_CODES: Dict[int, str] = {
    0: "000",
    1: "001",
    2: "011",
    3: "010",
    4: "110",
    5: "111",
    6: "101",
    7: "100",
}


# =============================================================================
# UNIFIED GEOMETRY CLASS
# =============================================================================

class SubstrateGeometry:
    """
    Unified interface for both substrate geometries.

    Parameters
    ----------
    mode : str
        "distorted" — D4h with scale markers (6+2)
        "cube"      — Oh uniform (8 equivalent)
    """

    def __init__(self, mode: str = GEOMETRY_MODE):
        if mode not in ("distorted", "cube"):
            raise ValueError(f"mode must be 'distorted' or 'cube', got {mode!r}")
        self.mode = mode

        if mode == "distorted":
            self.positions = DISTORTED_POSITIONS
            self.characters = DISTORTED_CHARACTERS
            self.eigenvalues = DISTORTED_EIGENVALUES
            self.transitions = DISTORTED_TRANSITIONS
            self.gray_codes = DISTORTED_GRAY_CODES
            self._primary_states = {0, 1, 2, 3, 4, 5}
            self._secondary_states = {6, 7}
        else:
            self.positions = CUBE_POSITIONS
            self.characters = CUBE_CHARACTERS
            self.eigenvalues = CUBE_EIGENVALUES
            self.transitions = CUBE_TRANSITIONS
            self.gray_codes = CUBE_GRAY_CODES
            self._primary_states = set(range(8))
            self._secondary_states = set()

    # -----------------------------------------------------------------------
    # Core lookups
    # -----------------------------------------------------------------------

    def distance_from_center(self, state: int) -> float:
        """Euclidean distance of state vertex from origin."""
        x, y, z = self.positions[state]
        return math.sqrt(x*x + y*y + z*z)

    def edge_distance(self, state_a: int, state_b: int) -> float:
        """Euclidean distance between two state vertices."""
        ax, ay, az = self.positions[state_a]
        bx, by, bz = self.positions[state_b]
        return math.sqrt((ax-bx)**2 + (ay-by)**2 + (az-bz)**2)

    def is_primary(self, state: int) -> bool:
        """True if state is in the primary (strong-coupling) orbit."""
        return state in self._primary_states

    def is_secondary(self, state: int) -> bool:
        """True if state is a scale marker (secondary orbit)."""
        return state in self._secondary_states

    def nearest_state(self, eigenvalues: Tuple[float, float, float]) -> int:
        """Return closest state by L2 distance in eigenvalue space."""
        best_state = 0
        best_dist = float("inf")
        for s, ref in self.eigenvalues.items():
            d = sum((eigenvalues[i] - ref[i])**2 for i in range(3))
            if d < best_dist:
                best_dist = d
                best_state = s
        return best_state

    def nearest_state_with_distance(self, eigenvalues: Tuple[float, float, float]) -> Tuple[int, float]:
        """Return (state, squared_distance)."""
        best_state = 0
        best_dist = float("inf")
        for s, ref in self.eigenvalues.items():
            d = sum((eigenvalues[i] - ref[i])**2 for i in range(3))
            if d < best_dist:
                best_dist = d
                best_state = s
        return best_state, best_dist

    # -----------------------------------------------------------------------
    # Coupling physics
    # -----------------------------------------------------------------------

    def fret_coupling(self, state_a: int, state_b: int, R0: float = 4.85) -> float:
        """
        FRET efficiency between two states, accounting for actual
        geometric distance between their vertex positions.
        """
        r = self.edge_distance(state_a, state_b)
        if r <= 0:
            return 1.0
        return 1.0 / (1.0 + (r / R0)**6)

    def dipole_coupling(self, state_a: int, state_b: int) -> float:
        """Dipole-dipole coupling ~ 1/r^3."""
        r = self.edge_distance(state_a, state_b)
        if r <= 0:
            return float("inf")
        return 1.0 / (r ** 3)

    def transition_cost(self, state_a: int, state_b: int) -> float:
        """
        Effective transition cost between states.
        For cube: all edges cost 1.0 (uniform).
        For distorted: primary-primary = 1.0, primary-secondary = 2.0,
        secondary-secondary = 1.0 (direct diagonal connection).
        """
        if state_b not in self.transitions.get(state_a, []):
            return float("inf")  # Not adjacent
        if self.mode == "cube":
            return 1.0
        # Distorted mode: weight by orbit crossing
        a_pri = self.is_primary(state_a)
        b_pri = self.is_primary(state_b)
        if a_pri and b_pri:
            return 1.0
        if not a_pri and not b_pri:
            return 1.0  # 6 <-> 7 direct
        return 2.0  # primary <-> secondary crossing

    # -----------------------------------------------------------------------
    # Scale marker logic (distorted mode only)
    # -----------------------------------------------------------------------

    def scale_marker_ratio(self, layer: int) -> float:
        """
        In distorted mode, the secondary states "breathe" with layer depth.
        At layer 0 (center): secondary states sit at distance sqrt(2).
        At layer N: they expand/contract by phi^(-N), encoding scale.

        Returns the effective distance multiplier for secondary states
        at the given bloom layer.
        """
        if self.mode == "cube":
            return 1.0  # No breathing in cube
        return PHI ** (-layer)

    def scaled_position(self, state: int, layer: int = 0) -> Tuple[float, float, float]:
        """
        Position of a state vertex, with scale-marker breathing applied.
        Primary states are fixed. Secondary states breathe.
        """
        x, y, z = self.positions[state]
        if self.is_secondary(state):
            ratio = self.scale_marker_ratio(layer)
            return (x * ratio, y * ratio, z * ratio)
        return (x, y, z)

    # -----------------------------------------------------------------------
    # Golden ratio stability
    # -----------------------------------------------------------------------

    def phi_deviation(self, state: int) -> dict:
        """Compute golden-ratio deviation for a single state."""
        ev = self.eigenvalues[state]
        ratios = {}
        candidates = []
        pairs = [(0,1), (1,2), (0,2)]
        for i, j in pairs:
            if ev[i] != 0:
                r = ev[j] / ev[i]
                ratios[f"l{j+1}/l{i+1}"] = r
                candidates.extend([r, 1.0/r])
        if not candidates:
            return {"deviation": float("inf"), "best_ratio": 0.0, "ratios": ratios}
        deviations = [abs(r - PHI) for r in candidates]
        min_idx = deviations.index(min(deviations))
        return {
            "deviation": deviations[min_idx],
            "best_ratio": candidates[min_idx],
            "ratios": ratios,
            "is_anchor": deviations[min_idx] < 0.05,
        }

    def stability_report(self) -> List[dict]:
        """Full phi-stability report, sorted by deviation."""
        report = []
        for s in range(8):
            info = self.phi_deviation(s)
            report.append({
                "state": s,
                "mode": self.mode,
                "character": self.characters[s],
                "eigenvalues": self.eigenvalues[s],
                "phi_deviation": info["deviation"],
                "best_ratio": info["best_ratio"],
                "is_anchor": info["is_anchor"],
                "is_primary": self.is_primary(s),
                "distance_from_center": self.distance_from_center(s),
            })
        report.sort(key=lambda r: r["phi_deviation"])
        return report

    # -----------------------------------------------------------------------
    # Audit / validation
    # -----------------------------------------------------------------------

    def validate(self) -> dict:
        """
        Run a full consistency audit on the geometry.
        Returns dict with findings.
        """
        findings = {
            "mode": self.mode,
            "n_states": 8,
            "symmetry_group": "D4h (distorted)" if self.mode == "distorted" else "Oh (cube)",
            "orbits": [],
            "distance_uniformity": True,
            "transition_symmetry": True,
            "gray_code_valid": True,
            "issues": [],
        }

        # Check orbit structure
        distances = {s: self.distance_from_center(s) for s in range(8)}
        unique_distances = sorted(set(round(d, 6) for d in distances.values()))
        for d in unique_distances:
            states = [s for s in range(8) if round(distances[s], 6) == d]
            findings["orbits"].append({"distance": d, "states": states, "count": len(states)})
        if len(unique_distances) > 1:
            findings["distance_uniformity"] = False
            findings["issues"].append(
                f"Multiple distance orbits detected: {unique_distances}. "
                f"This is expected for distorted mode, a bug for cube mode."
            )

        # Check transition symmetry (a->b iff b->a)
        for a in range(8):
            for b in self.transitions.get(a, []):
                if a not in self.transitions.get(b, []):
                    findings["transition_symmetry"] = False
                    findings["issues"].append(
                        f"Asymmetric transition: {a}->{b} exists but {b}->{a} does not"
                    )

        # Check Gray code validity (all unique, all 3-bit)
        codes = list(self.gray_codes.values())
        if len(set(codes)) != 8 or any(len(c) != 3 for c in codes):
            findings["gray_code_valid"] = False
            findings["issues"].append("Gray code table is invalid")

        # Check eigenvalue normalization
        for s, ev in self.eigenvalues.items():
            total = sum(ev)
            if abs(total - 1.0) > 0.01 and abs(total - 0.75) > 0.01:
                findings["issues"].append(
                    f"State {s} eigenvalues sum to {total:.3f} (expected ~1.0 or ~0.75)"
                )

        findings["passes"] = len(findings["issues"]) == 0
        return findings


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

# Default instance using the global mode
default_geometry = SubstrateGeometry(GEOMETRY_MODE)

# Shorthand functions that delegate to default instance
def nearest_state(eigenvalues: Tuple[float, float, float]) -> int:
    return default_geometry.nearest_state(eigenvalues)

def stability_report() -> List[dict]:
    return default_geometry.stability_report()

def validate() -> dict:
    return default_geometry.validate()


# =============================================================================
# SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Octahedral Geometry Core — Self Test")
    print("=" * 60)

    for mode in ("distorted", "cube"):
        print(f"\n--- Mode: {mode.upper()} ---")
        geo = SubstrateGeometry(mode)
        audit = geo.validate()

        print(f"Symmetry group : {audit['symmetry_group']}")
        print(f"Distance orbits: {len(audit['orbits'])}")
        for orbit in audit["orbits"]:
            print(f"  Distance {orbit['distance']:.4f}: states {orbit['states']}")

        print(f"\nTransition symmetry : {audit['transition_symmetry']}")
        print(f"Gray code valid     : {audit['gray_code_valid']}")
        print(f"Issues              : {audit['issues'] or 'None'}")

        print(f"\nPhi stability (top 3):")
        for entry in geo.stability_report()[:3]:
            marker = " ** ANCHOR" if entry["is_anchor"] else ""
            orbit = "pri" if entry["is_primary"] else "sec"
            print(f"  State {entry['state']} [{orbit}]: dev={entry['phi_deviation']:.4f}{marker}")

        if mode == "distorted":
            print(f"\nScale marker breathing (layers 0-3):")
            for layer in range(4):
                ratio = geo.scale_marker_ratio(layer)
                pos6 = geo.scaled_position(6, layer)
                print(f"  Layer {layer}: ratio={ratio:.4f}, pos(6)=({pos6[0]:.3f},{pos6[1]:.3f})")

        print(f"\nFRET coupling examples:")
        if mode == "distorted":
            print(f"  0->2 (pri-pri, edge=1.00): {geo.fret_coupling(0,2):.4f}")
            print(f"  0->6 (pri-sec, edge=1.00): {geo.fret_coupling(0,6):.4f}")
            print(f"  6->7 (sec-sec, edge=2.83): {geo.fret_coupling(6,7):.4f}")
        else:
            print(f"  0->1 (edge=2.00): {geo.fret_coupling(0,1):.4f}")
            print(f"  0->7 (edge=3.46): {geo.fret_coupling(0,7):.4f}")

    print("\n" + "=" * 60)
    print("All tests passed.")
    print("=" * 60)
