"""
Magnetic Bridge Encoder
=======================
Encodes magnetic field geometry into binary using physics equations
and Gray-coded magnitude bands for all continuous quantities.

Equations implemented
---------------------
  Biot-Savart Law   :  dB = (μ₀ / 4π) · I · |dl × r̂| / r²
                        = (μ₀ / 4π) · I · |dl| · sin(α) / r²
                        where α is the angle between dl and r̂
  Magnetic flux     :  Φ = B · A · cos(θ)
                        A defaults to 1 m² if not supplied; θ defaults to 0
  Magnetic pressure :  P_mag = B² / (2μ₀)
  Larmor frequency  :  ω_L = eB / (2mₑ)   [rad/s, electron precession]
  Field curvature   :  κ = |curvature|  (m⁻¹ — inverse radius of curvature)

Bit layout
----------
Per field line  (8 bits each):
  [polarity    1b]      N=1 / S=0
  [curv_sign   1b]      curvature > 0 (convex) = 1
  [curv_mag    3b Gray] |curvature| across 8 log bands (m⁻¹)
  [B_mag       3b Gray] field magnitude across 8 log Tesla bands

Per current element  (7 bits each, Biot-Savart result):
  [I_mag       3b Gray] current magnitude (8 log Ampere bands)
  [B_biot      3b Gray] B at origin from Biot-Savart (8 log Tesla bands)
  [I_sign      1b]      dl_z > 0 = 1 (current flow direction)

Per resonance value  (4 bits each):
  [constructive 1b]     value > 0 = constructive = 1
  [res_mag     3b Gray] |resonance| across 8 linear bands [0, 1]

Summary  (7 bits — appended when field_lines are present):
  [flux_sign   1b]      mean Φ ≥ 0 = 1
  [flux_mag    3b Gray] mean |Φ| across 8 log Weber bands
  [P_mag       3b Gray] mean magnetic pressure across 8 log Pascal bands
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge.abstract_encoder import BinaryBridgeEncoder

# ── Physical constants ────────────────────────────────────────────────────────
MU_0        = 4 * math.pi * 1e-7      # Permeability of free space (H/m)
E_CHARGE    = 1.602176634e-19         # Elementary charge (C)
M_ELECTRON  = 9.1093837015e-31        # Electron rest mass (kg)
_MU_0_4PI   = MU_0 / (4 * math.pi)   # μ₀/4π — Biot-Savart prefactor (T·m/A)

# ── Gray-coded magnitude band edges (8 bands → 3 bits each) ──────────────────
# Band i covers [BANDS[i], BANDS[i+1]).  Values below BANDS[0] → band 0.
# Values above the last edge → top band.  Adjacent bands differ by 1 Gray bit.

_B_BANDS        = [0.0, 1e-9, 1e-6, 1e-3, 0.01, 0.1,  1.0,  10.0 ]  # Tesla
_KAPPA_BANDS    = [0.0, 0.01, 0.1,  0.5,  1.0,  2.0,  5.0,  10.0 ]  # m⁻¹
_I_BANDS        = [0.0, 1e-6, 1e-4, 1e-2, 0.1,  1.0,  10.0, 100.0]  # Amperes
_FLUX_BANDS     = [0.0, 1e-12,1e-9, 1e-6, 1e-3, 0.01, 0.1,  1.0  ]  # Weber
_PRESSURE_BANDS = [0.0, 1e-3, 0.01, 0.1,  1.0,  10.0, 100.0,1e4  ]  # Pascal
_RES_BANDS      = [0.0, 0.125,0.25, 0.375,0.5,  0.625,0.75, 0.875]  # normalised


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gray(n: int) -> int:
    """Integer → Gray code integer (single-bit transitions between adjacent values)."""
    return n ^ (n >> 1)


def _gray_bits(value: float, bands: list, n_bits: int = 3) -> str:
    """
    Map a non-negative scalar to a Gray-coded binary string.

    Scans band edges from highest to lowest; returns the index of the highest
    edge the value meets or exceeds, Gray-encoded to n_bits.

    Gray-code property: adjacent bands differ by exactly 1 bit, so a physical
    value near a band boundary never causes more than 1-bit change.
    """
    band = 0
    for i in range(len(bands) - 1, -1, -1):
        if value >= bands[i]:
            band = i
            break
    return format(_gray(band), f'0{n_bits}b')


# ── Physics equations ─────────────────────────────────────────────────────────

def biot_savart_magnitude(current: float, dl: list, position: list) -> float:
    """
    Magnitude of B at the origin from a single current element.

      dB = (μ₀ / 4π) · I · |dl × r̂| / r²
         = (μ₀ / 4π) · I · |dl| · sin(α) / r²

    where r_vec points from element `position` to the field point (origin),
    and α is the angle between dl and r̂.

    Args:
        current  : current magnitude (A)
        dl       : current element direction vector [dx, dy, dz]
        position : element position [x, y, z]; field evaluated at origin

    Returns:
        |B| in Tesla
    """
    r_vec = [-position[i] for i in range(3)]
    r_sq  = sum(x * x for x in r_vec)
    if r_sq == 0.0:
        return 0.0
    r_mag  = math.sqrt(r_sq)
    dl_mag = math.sqrt(sum(x * x for x in dl))
    if dl_mag == 0.0:
        return 0.0
    cos_alpha = sum(dl[i] * r_vec[i] for i in range(3)) / (dl_mag * r_mag)
    sin_alpha = math.sqrt(max(0.0, 1.0 - cos_alpha ** 2))
    return _MU_0_4PI * abs(current) * dl_mag * sin_alpha / r_sq


def magnetic_flux(B_mag: float, area: float = 1.0, theta: float = 0.0) -> float:
    """
    Magnetic flux through a surface.

      Φ = B · A · cos(θ)

    Args:
        B_mag : field magnitude (T)
        area  : surface area (m²)
        theta : angle between B and area normal (radians)

    Returns:
        Φ in Weber (T·m²)
    """
    return B_mag * area * math.cos(theta)


def magnetic_pressure(B_mag: float) -> float:
    """
    Magnetic pressure (energy density) of a field.

      P = B² / (2μ₀)

    Args:
        B_mag : field magnitude (T)

    Returns:
        P in Pascal (J/m³)
    """
    return (B_mag ** 2) / (2.0 * MU_0)


def larmor_frequency(B_mag: float) -> float:
    """
    Electron Larmor (cyclotron precession) frequency.

      ω_L = eB / (2mₑ)

    Args:
        B_mag : field magnitude (T)

    Returns:
        ω_L in rad/s
    """
    return (E_CHARGE * B_mag) / (2.0 * M_ELECTRON)


# ── Encoder ───────────────────────────────────────────────────────────────────

class MagneticBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes magnetic field geometry into binary using physics equations
    and Gray-coded magnitude bands for all continuous quantities.

    Input geometry dict keys
    ------------------------
    field_lines : list of dicts, each containing:
        "direction"  : "N" or "S"          polarity
        "curvature"  : float (m⁻¹)         signed curvature: + convex, − concave
        "magnitude"  : float (T)            B field strength  [optional, default 0.0]
        "area"       : float (m²)           surface area for flux [optional, default 1.0]
        "flux_theta" : float (rad)          B-to-normal angle   [optional, default 0.0]

    current_elements : list of dicts, each containing:
        "current"    : float (A)            current magnitude
        "dl"         : [dx, dy, dz]         current element direction vector
        "position"   : [x, y, z]            element position (field point = origin)

    resonance_map : list of float
        Positive = constructive interference; negative = destructive.
    """

    def __init__(self):
        super().__init__("magnetic")

    def from_geometry(self, geometry_data: dict):
        """Load geometry data.  Returns self for chaining."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Encode loaded geometry to a binary string.

        Sections (in order):
          1. Field lines    — 8 bits each
          2. Current elements (Biot-Savart) — 7 bits each
          3. Resonance values — 4 bits each
          4. Summary (flux + pressure) — 7 bits (only when field_lines present)
        """
        if self.input_geometry is None:
            raise ValueError("Geometry data not loaded. Call from_geometry() first.")

        bits: list[str] = []
        field_lines      = self.input_geometry.get("field_lines", [])
        current_elements = self.input_geometry.get("current_elements", [])
        resonance_map    = self.input_geometry.get("resonance_map", [])

        # ── Section 1: Field lines ────────────────────────────────────────────
        # 8 bits per line: polarity(1) + curv_sign(1) + curv_mag(3) + B_mag(3)
        for line in field_lines:
            direction  = line.get("direction", "N").upper()
            curvature  = float(line.get("curvature", 0.0))
            B_mag      = float(line.get("magnitude", 0.0))

            bits.append("1" if direction == "N" else "0")           # polarity
            bits.append("1" if curvature > 0.0 else "0")            # curvature sign
            bits.append(_gray_bits(abs(curvature), _KAPPA_BANDS))   # κ magnitude (3b)
            bits.append(_gray_bits(abs(B_mag),     _B_BANDS))       # B magnitude (3b)

        # ── Section 2: Current elements — Biot-Savart ─────────────────────────
        # 7 bits per element: I_mag(3) + B_biot(3) + flow_sign(1)
        for elem in current_elements:
            current  = float(elem.get("current", 0.0))
            dl       = elem.get("dl",       [0.0, 0.0, 1.0])
            position = elem.get("position", [1.0, 0.0, 0.0])

            B_biot = biot_savart_magnitude(current, dl, position)

            bits.append(_gray_bits(abs(current), _I_BANDS))         # I magnitude (3b)
            bits.append(_gray_bits(B_biot,       _B_BANDS))         # B_biot     (3b)
            bits.append("1" if len(dl) > 2 and dl[2] > 0 else "0") # flow sign  (1b)

        # ── Section 3: Resonance ──────────────────────────────────────────────
        # 4 bits per value: constructive(1) + res_mag(3)
        for val in resonance_map:
            val = float(val)
            bits.append("1" if val > 0.0 else "0")                  # constructive
            bits.append(_gray_bits(abs(val), _RES_BANDS))           # magnitude (3b)

        # ── Section 4: Summary — flux and pressure ────────────────────────────
        # 7 bits: flux_sign(1) + flux_mag(3) + pressure(3)
        # Uses mean B across all field lines; skipped when no field_lines present.
        if field_lines:
            B_values  = [float(l.get("magnitude", 0.0)) for l in field_lines]
            area_vals = [float(l.get("area",       1.0)) for l in field_lines]
            theta_vals= [float(l.get("flux_theta", 0.0)) for l in field_lines]
            n         = len(field_lines)
            B_mean    = sum(B_values)  / n
            A_mean    = sum(area_vals) / n
            θ_mean    = sum(theta_vals)/ n

            flux = magnetic_flux(B_mean, A_mean, θ_mean)
            P    = magnetic_pressure(B_mean)

            bits.append("1" if flux >= 0.0 else "0")                # flux sign
            bits.append(_gray_bits(abs(flux), _FLUX_BANDS))         # flux mag  (3b)
            bits.append(_gray_bits(P,         _PRESSURE_BANDS))     # pressure  (3b)

        self.binary_output = "".join(bits)
        return self.binary_output


# ── Demo ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    encoder = MagneticBridgeEncoder()
    sample = {
        "field_lines": [
            {"direction": "N", "curvature":  0.3, "magnitude": 0.05, "area": 0.01},
            {"direction": "S", "curvature": -0.8, "magnitude": 0.002},
        ],
        "current_elements": [
            {"current": 5.0, "dl": [0.0, 0.0, 1.0], "position": [0.1, 0.0, 0.0]},
        ],
        "resonance_map": [0.7, -0.4],
    }
    encoder.from_geometry(sample)
    bits = encoder.to_binary()
    print(f"Bitstring ({len(bits)} bits): {bits}")
    print("Report:", encoder.report())
    print()

    B_ex = 0.05
    print(f"--- Equation values for B = {B_ex} T ---")
    print(f"  Magnetic flux  (A=1m², θ=0):  {magnetic_flux(B_ex):.6e} Wb")
    print(f"  Magnetic pressure:            {magnetic_pressure(B_ex):.4f} Pa")
    print(f"  Larmor frequency:             {larmor_frequency(B_ex):.4e} rad/s")
    B_bs = biot_savart_magnitude(5.0, [0, 0, 1], [0.1, 0.0, 0.0])
    print(f"  Biot-Savart B (5A @ 10cm):    {B_bs:.4e} T")
