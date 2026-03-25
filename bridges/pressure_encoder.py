"""
Pressure / Haptic Bridge Encoder
=================================
Encodes pressure and mechanical stress geometry into binary using core
continuum-mechanics equations and Gray-coded magnitude bands.

Equations implemented
---------------------
  Hydrostatic pressure     :  P = ρ·g·h              (fluid column)
  Young's modulus stress   :  σ = E · ε              (linear elasticity)
  Bulk modulus compression :  ΔP = -B · (ΔV/V)       (volumetric)
  Acoustic radiation force :  F_rad = P_acous / c     (radiation pressure)
  Piezoelectric voltage    :  V_pz = g · σ · t        (sensing element output)

Bit layout (39 bits for 3-sample canonical input)
--------------------------------------------------
Per pressure sample  (8 bits each):
  [above_atm  1b]       P > 101325 Pa (above 1 atm) = 1
  [pres_mag   3b Gray]  P across 8 log bands (0 Pa → 1 GPa)
  [compres    1b]       stress is compressive (σ < 0) = 1
  [stress_mag 3b Gray]  |σ| across 8 log bands (0 → 1 GPa)

Per strain sample  (4 bits each):
  [yielding   1b]       ε > yield_threshold = 1
  [strain_mag 3b Gray]  ε across 8 linear bands [0, 1]

Summary  (7 bits — appended when any section present):
  [net_compress  1b]       majority of pressures above atm = 1
  [bulk_band     3b Gray]  mean bulk stress magnitude (8 log Pa bands)
  [piezo_band    3b Gray]  piezoelectric output at mean stress (8 log µV bands)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
G_STD    = 9.80665   # Standard gravity (m/s²)
ATM      = 101325.0  # Standard atmosphere (Pa)
RHO_W    = 1000.0    # Water density (kg/m³)
C_SOUND  = 343.0     # Speed of sound in air (m/s)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_PRES_BANDS   = [0.0, 1.0, 100.0, 1e3, 1e4, ATM, 1e6, 1e9]        # Pa
_STRESS_BANDS = [0.0, 1.0, 1e3, 1e5, 1e6, 1e7, 1e8, 1e9]          # Pa
_STRAIN_BANDS = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2]   # dimensionless
_BULK_BANDS   = [0.0, 1.0, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8]          # Pa
_PIEZO_BANDS  = [0.0, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]  # V


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def hydrostatic_pressure(rho: float, depth_m: float) -> float:
    """
    P = ρ·g·h  — gauge pressure at depth h in a fluid of density ρ (kg/m³).

    Returns pressure in Pascals above the surface reference.
    """
    return rho * G_STD * depth_m


def elastic_stress(E_pa: float, strain: float) -> float:
    """
    σ = E · ε  — Hooke's law for uniaxial stress (Pa).

    E_pa   : Young's modulus (Pa)
    strain : dimensionless linear strain  (ΔL/L)
    Positive = tension, negative = compression.
    """
    return E_pa * strain


def bulk_compression(B_pa: float, delta_V_over_V: float) -> float:
    """
    ΔP = -B · (ΔV/V)  — bulk modulus pressure change (Pa).

    B_pa            : bulk modulus (Pa)
    delta_V_over_V  : fractional volume change ΔV/V (negative = compression)
    Returns the pressure increase caused by compression.
    """
    return -B_pa * delta_V_over_V


def acoustic_radiation_pressure(intensity_W_m2: float) -> float:
    """
    P_rad = I / c  — radiation pressure from an acoustic wave (Pa).

    intensity_W_m2 : acoustic intensity (W/m²)
    Uses speed of sound in air (343 m/s); divide by your medium's c if needed.
    """
    if C_SOUND == 0.0:
        return 0.0
    return intensity_W_m2 / C_SOUND


def piezoelectric_voltage(g_constant: float, stress_pa: float,
                           thickness_m: float) -> float:
    """
    V_pz = g · σ · t  — open-circuit piezoelectric output voltage (V).

    g_constant   : piezoelectric voltage coefficient (V·m/N), e.g. PZT ≈ 0.025
    stress_pa    : applied stress (Pa)
    thickness_m  : sensor element thickness (m)
    """
    return g_constant * stress_pa * thickness_m


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class PressureBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes pressure / haptic field geometry into a binary bitstring.

    Input geometry dict keys
    ------------------------
    pressures_Pa      : list of floats — measured pressure values (Pa)
    stresses_Pa       : list of floats — mechanical stress values (Pa);
                        negative = compressive, positive = tensile
    strains           : list of floats — dimensionless strain values
    yield_threshold   : float — strain level above which material yields
                        (default 0.002 — typical metal yield strain)
    piezo_g           : float — piezoelectric g-constant for summary (default 0.025 V·m/N)
    piezo_thickness_m : float — sensor thickness for piezo summary (default 1e-3 m)
    """

    def __init__(self, yield_threshold: float = 0.002,
                 piezo_g: float = 0.025,
                 piezo_thickness_m: float = 1e-3):
        super().__init__("pressure")
        self.yield_threshold   = yield_threshold
        self.piezo_g           = piezo_g
        self.piezo_thickness_m = piezo_thickness_m

    def from_geometry(self, geometry_data: dict):
        """Load pressure/haptic geometry data dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded pressure geometry into a binary bitstring.

        Returns
        -------
        str
            A string of ``"0"`` and ``"1"`` characters.

        Raises
        ------
        ValueError
            If ``from_geometry`` has not been called first.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry loaded. Call from_geometry(data) before to_binary()."
            )

        data         = self.input_geometry
        pressures    = data.get("pressures_Pa", [])
        stresses     = data.get("stresses_Pa", [])
        strains      = data.get("strains", [])
        bits         = []
        any_section  = False

        # ------------------------------------------------------------------
        # Section 1: pressure + stress pairs  →  8 bits each
        #   [above_atm 1b][pres_mag 3b Gray][compres 1b][stress_mag 3b Gray]
        # ------------------------------------------------------------------
        n_pairs = max(len(pressures), len(stresses))
        for i in range(n_pairs):
            any_section = True
            P  = pressures[i] if i < len(pressures) else 0.0
            sig = stresses[i] if i < len(stresses) else 0.0

            above_atm  = "1" if P > ATM else "0"
            pres_mag   = _gray_bits(abs(P), _PRES_BANDS)
            compres    = "1" if sig < 0.0 else "0"
            stress_mag = _gray_bits(abs(sig), _STRESS_BANDS)

            bits.append(above_atm)
            bits.append(pres_mag)
            bits.append(compres)
            bits.append(stress_mag)

        # ------------------------------------------------------------------
        # Section 2: strain values  →  4 bits each
        #   [yielding 1b][strain_mag 3b Gray]
        # ------------------------------------------------------------------
        for eps in strains:
            any_section = True
            yielding   = "1" if abs(eps) > self.yield_threshold else "0"
            strain_mag = _gray_bits(abs(eps), _STRAIN_BANDS)
            bits.append(yielding)
            bits.append(strain_mag)

        # ------------------------------------------------------------------
        # Summary  (7 bits)
        # ------------------------------------------------------------------
        if any_section:
            # net_compress: majority of pressures above 1 atm
            if pressures:
                n_high = sum(1 for P in pressures if P > ATM)
                net_compress = "1" if n_high > len(pressures) - n_high else "0"
                mean_P = sum(abs(P) for P in pressures) / len(pressures)
            else:
                net_compress = "0"
                mean_P = 0.0

            # mean stress for bulk band
            mean_sig = (sum(abs(s) for s in stresses) / len(stresses)) if stresses else 0.0

            # piezoelectric output at mean stress
            piezo_V = piezoelectric_voltage(self.piezo_g, mean_sig, self.piezo_thickness_m)

            bits.append(net_compress)
            bits.append(_gray_bits(mean_P, _BULK_BANDS))
            bits.append(_gray_bits(abs(piezo_V), _PIEZO_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Pressure / Haptic Bridge Encoder — Physics Demo")
    print("=" * 60)

    # 1. Hydrostatic pressure at ocean depths
    print("\n1. Hydrostatic pressure  P = ρ·g·h")
    for depth, label in [(10, "1 m"), (100, "10 m"), (1000, "100 m"), (10000, "1000 m (deep ocean)")]:
        P = hydrostatic_pressure(RHO_W, depth)
        print(f"   depth={depth:6.0f} m  ({label:22s})  P = {P/1e6:.4f} MPa  ({P/ATM:.1f} atm)")

    # 2. Elastic stress in steel under 0.1% strain
    E_steel = 200e9   # Pa (200 GPa)
    eps = 0.001
    sig = elastic_stress(E_steel, eps)
    print(f"\n2. Elastic stress (steel, E=200 GPa, ε=0.1%)")
    print(f"   σ = E·ε = {sig/1e6:.1f} MPa  (yield ≈ 250–500 MPa)")

    # 3. Bulk compression of water
    B_water = 2.2e9   # Pa
    delta_VV = -0.001  # 0.1% compression
    dP = bulk_compression(B_water, delta_VV)
    print(f"\n3. Bulk compression (water, B=2.2 GPa, ΔV/V=-0.1%)")
    print(f"   ΔP = -B·(ΔV/V) = {dP/1e6:.2f} MPa")

    # 4. Acoustic radiation pressure (ultrasound, 1 W/cm²)
    I_us = 1e4   # W/m²  (1 W/cm²)
    P_rad = acoustic_radiation_pressure(I_us)
    print(f"\n4. Acoustic radiation pressure (I = 1 W/cm²)")
    print(f"   P_rad = I/c = {P_rad:.4f} Pa  (~{P_rad/ATM:.2e} atm)")

    # 5. Piezoelectric sensor output (PZT, 1 MPa stress, 1 mm thick)
    g_pzt = 0.025   # V·m/N (typical PZT)
    V_pz = piezoelectric_voltage(g_pzt, stress_pa=1e6, thickness_m=1e-3)
    print(f"\n5. Piezoelectric voltage (PZT g=0.025, σ=1 MPa, t=1 mm)")
    print(f"   V_pz = g·σ·t = {V_pz:.1f} V")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "pressures_Pa":  [ATM, 5e5, 1e7],              # 1 atm, 5 bar, 100 bar
        "stresses_Pa":   [-2e6, 1.5e5, -8e7],           # compressive, tensile, compressive
        "strains":       [0.001, 0.003],                 # elastic, just yielding
    }

    encoder = PressureBridgeEncoder(yield_threshold=0.002)
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
