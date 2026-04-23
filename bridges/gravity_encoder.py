"""
Gravity Bridge Encoder
======================
Encodes coupling to gravitational potential structure into binary using
physics equations and Gray-coded magnitude bands for the continuous quantities.

Equations implemented
---------------------
  Gravitational acceleration :  g = GM / r²
  Escape velocity            :  v_esc = √(2·|U|)   (U = specific potential energy, J/kg)
  Orbital velocity           :  v_orb = √(|U|)      (circular orbit: v = √(GM/r) = √(|U|))
  Schwarzschild radius       :  r_s = 2GM / c²
  Tidal acceleration         :  a_tidal = 2GM·d / r³

Bit layout
----------
Per gravity vector  (4 bits each):
  [inward    1b]       radial/y-component < 0 = 1
  [accel_mag 3b Gray]  |g| across 8 log m/s² bands

Per curvature value  (4 bits each):
  [curv_sign 1b]       κ > 0 = 1
  [curv_mag  3b Gray]  |κ| across 8 log bands

Per orbital_stability value  (4 bits each):
  [stable    1b]       s ≥ 0.5 = 1
  [stab_mag  3b Gray]  |s| across 8 linear bands [0,1]

Per potential_energy value  (4 bits each):
  [bound     1b]       E < 0 = 1  (gravitationally bound)
  [energy_mag 3b Gray] |E| across 8 log J/kg bands

Summary  (7 bits — appended when any section present):
  [net_bound    1b]       majority of energies < 0 = 1
  [v_esc_band   3b Gray]  escape velocity from mean |potential| (8 log m/s bands)
  [v_orb_band   3b Gray]  orbital velocity from mean |potential| (8 log m/s bands)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
G       = 6.674e-11   # Gravitational constant (N·m²/kg²)
C_LIGHT = 2.998e8     # Speed of light (m/s)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_ACCEL_BANDS     = [0.0, 0.01, 0.1, 1.0, 5.0, 10.0, 50.0, 100.0]             # m/s²
_CURV_BANDS      = [0.0, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0, 100.0]            # m⁻¹
_STAB_BANDS      = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]        # normalised
_POTENTIAL_BANDS = [0.0, 1e3, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10]                 # J/kg
_VEL_BANDS       = [0.0, 10.0, 100.0, 1000.0, 5000.0, 11200.0, 30000.0, 3e5] # m/s

# ---------------------------------------------------------------------------
# Gray-code helpers
# ---------------------------------------------------------------------------

# _gray_bits imported from bridges.common — canonical highest-edge Gray encoder


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def gravitational_acceleration(M: float, r: float) -> float:
    """g = GM/r². Returns 0 if r=0."""
    if r == 0:
        return 0.0
    return G * M / (r * r)


def escape_velocity(specific_potential: float) -> float:
    """v_esc = sqrt(2·|U|)  where U is specific potential energy (J/kg). Returns 0 if U=0."""
    if specific_potential == 0:
        return 0.0
    return math.sqrt(2.0 * abs(specific_potential))


def orbital_velocity(specific_potential: float) -> float:
    """v_orb = sqrt(|U|)  (circular orbit approximation). Returns 0 if U=0."""
    if specific_potential == 0:
        return 0.0
    return math.sqrt(abs(specific_potential))


def schwarzschild_radius(M: float) -> float:
    """r_s = 2GM/c². Returns 0 if M=0."""
    if M == 0:
        return 0.0
    return 2.0 * G * M / (C_LIGHT * C_LIGHT)


def tidal_acceleration(M: float, r: float, d: float) -> float:
    """a_tidal = 2GM·d/r³. Returns 0 if r=0."""
    if r == 0:
        return 0.0
    return 2.0 * G * M * d / (r ** 3)


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class GravityBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes gravitational potential, curvature, tidal response, and bound-state structure into a binary bitstring.

    Input geometry dict keys
    ------------------------
    vectors          : list of vector tuples/lists — each represents a local gravitational field direction; the y-component (index 1) is used as a simple inward/outward sign proxy.
    curvature        : list of floats — spacetime curvature values (m⁻¹).
    orbital_stability: list of floats in [0, 1] — stability metric for orbits.
    potential_energy : list of floats — specific gravitational potential energy
                       (J/kg); negative values indicate a bound system.
    """

    def __init__(self):
        super().__init__("gravity")

    # ------------------------------------------------------------------
    # BinaryBridgeEncoder interface
    # ------------------------------------------------------------------

    def from_geometry(self, geometry_data: dict):
        """Load gravitational field data from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded gravitational coupling geometry into a binary bitstring.

        Returns
        -------
        str
            A string of ``"0"`` and ``"1"`` characters.  Length depends on the
            number of values supplied in each section.

        Raises
        ------
        ValueError
            If ``from_geometry`` has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        data = self.input_geometry
        bits = []
        any_section = False

        # ------------------------------------------------------------------
        # Section 1: gravity vectors  →  [inward 1b][accel_mag 3b Gray]
        # ------------------------------------------------------------------
        vectors = data.get("vectors", [])
        for vec in vectors:
            any_section = True
            # Inward: use y-component (index 1) if available, else x (index 0)
            if len(vec) > 1:
                inward = "1" if vec[1] < 0 else "0"
            else:
                inward = "1" if vec[0] < 0 else "0"
            accel_mag = math.sqrt(sum(x * x for x in vec))
            bits.append(inward)
            bits.append(_gray_bits(accel_mag, _ACCEL_BANDS))

        # ------------------------------------------------------------------
        # Section 2: curvature  →  [curv_sign 1b][curv_mag 3b Gray]
        # ------------------------------------------------------------------
        curvature = data.get("curvature", [])
        for kappa in curvature:
            any_section = True
            curv_sign = "1" if kappa > 0 else "0"
            bits.append(curv_sign)
            bits.append(_gray_bits(abs(kappa), _CURV_BANDS))

        # ------------------------------------------------------------------
        # Section 3: orbital stability  →  [stable 1b][stab_mag 3b Gray]
        # ------------------------------------------------------------------
        orbital_stability = data.get("orbital_stability", [])
        for s in orbital_stability:
            any_section = True
            stable = "1" if s >= 0.5 else "0"
            bits.append(stable)
            bits.append(_gray_bits(abs(s), _STAB_BANDS))

        # ------------------------------------------------------------------
        # Section 4: potential energy  →  [bound 1b][energy_mag 3b Gray]
        # ------------------------------------------------------------------
        potential_energy = data.get("potential_energy", [])
        for E in potential_energy:
            any_section = True
            bound = "1" if E < 0 else "0"
            bits.append(bound)
            bits.append(_gray_bits(abs(E), _POTENTIAL_BANDS))

        # ------------------------------------------------------------------
        # Summary  (7 bits, appended when at least one section has data)
        # ------------------------------------------------------------------
        if any_section:
            # net_bound: majority of potential_energy values < 0
            if potential_energy:
                count_bound = sum(1 for E in potential_energy if E < 0)
                net_bound = "1" if count_bound > len(potential_energy) - count_bound else "0"
                mean_potential = sum(abs(E) for E in potential_energy) / len(potential_energy)
            else:
                net_bound = "0"
                mean_potential = 0.0

            v_esc  = escape_velocity(mean_potential)
            v_orb  = orbital_velocity(mean_potential)

            bits.append(net_bound)
            bits.append(_gray_bits(v_esc, _VEL_BANDS))
            bits.append(_gray_bits(v_orb, _VEL_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Gravity Bridge Encoder — Physics Demo")
    print("=" * 60)

    # 1. Gravitational acceleration (Earth surface)
    M_earth = 5.972e24   # kg
    r_earth = 6.371e6    # m
    g = gravitational_acceleration(M_earth, r_earth)
    print(f"\n1. Gravitational acceleration (Earth surface)")
    print(f"   g = GM/r² = {g:.4f} m/s²  (expected ≈ 9.82 m/s²)")

    # 2. Escape velocity from Earth surface
    U_earth = -G * M_earth / r_earth   # specific potential energy (J/kg)
    v_esc = escape_velocity(U_earth)
    print(f"\n2. Escape velocity from Earth surface")
    print(f"   U = {U_earth:.4e} J/kg")
    print(f"   v_esc = √(2|U|) = {v_esc:.2f} m/s  (expected ≈ 11,186 m/s)")

    # 3. Orbital velocity at Earth surface (circular orbit approximation)
    v_orb = orbital_velocity(U_earth)
    print(f"\n3. Orbital velocity (circular orbit at Earth surface)")
    print(f"   v_orb = √|U| = {v_orb:.2f} m/s  (expected ≈ 7,909 m/s)")

    # 4. Schwarzschild radius of the Sun
    M_sun = 1.989e30  # kg
    r_s = schwarzschild_radius(M_sun)
    print(f"\n4. Schwarzschild radius of the Sun")
    print(f"   r_s = 2GM/c² = {r_s:.2f} m  (expected ≈ 2,953 m)")

    # 5. Tidal acceleration (Moon on Earth's oceans, d = 1 m test separation)
    M_moon = 7.342e22  # kg
    r_moon = 3.844e8   # m  (Earth-Moon distance)
    d_test = 1.0       # m
    a_tidal = tidal_acceleration(M_moon, r_moon, d_test)
    print(f"\n5. Tidal acceleration at Earth's surface (d = {d_test} m)")
    print(f"   a_tidal = 2GM·d/r³ = {a_tidal:.4e} m/s²  (expected ≈ 2.26×10⁻⁶ m/s²)")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "vectors": [
            [0.0, -9.81, 0.0],   # downward (inward) Earth-like gravity
            [0.0,  1.62, 0.0],   # upward (outward) — Moon surface, pointing up
        ],
        "curvature": [0.5, -0.05, 2.3],
        "orbital_stability": [0.9, 0.3, 0.55],
        "potential_energy": [U_earth, -5.0e7, 1.2e6],
    }

    encoder = GravityBridgeEncoder()
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
