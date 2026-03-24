"""
Electric Bridge Encoder
=======================
Encodes electrical field and circuit geometry into binary using physics equations
and Gray-coded magnitude bands for all continuous quantities.

Equations implemented
---------------------
  Ohm's law            :  R = V / I
  Power dissipation    :  P = V · I  (equivalently P = I²R = V²/R)
  Coulomb's law        :  F = k · q₁q₂ / r²  (k = 8.9875×10⁹ N·m²/C²)
  Electric field       :  E = k · q / r²
  Skin depth           :  δ = √(2 / (ω · μ₀ · σ))   (ω = 2πf)

Bit layout
----------
Per charge value  (4 bits each):
  [positive    1b]       q > 0 = 1
  [charge_mag  3b Gray]  |q| across 8 log Coulomb bands

Per current value  (4 bits each):
  [flowing     1b]       I > 0 = 1
  [current_mag 3b Gray]  |I| across 8 log Ampere bands

Per voltage value  (4 bits each):
  [above_vref  1b]       V ≥ Vref = 1
  [voltage_mag 3b Gray]  |V| across 8 log Volt bands

Per conductivity value  (4 bits each):
  [conducting  1b]       σ ≥ conduction_threshold = 1
  [conduct_mag 3b Gray]  |σ| across 8 log Siemens bands

Summary  (7 bits — appended when any section present):
  [dissipative  1b]       mean power > 0 = 1
  [power_band   3b Gray]  mean P = V·I across 8 log Watt bands
  [impedance_band 3b Gray] mean Z = V/I across 8 log Ohm bands
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
K_COULOMB = 8.9875e9              # Coulomb constant (N·m²/C²)
MU_0      = 4 * math.pi * 1e-7   # Permeability of free space (H/m)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_CHARGE_BANDS    = [0.0, 1e-12, 1e-9, 1e-6, 1e-3, 0.01, 0.1, 1.0]   # Coulombs
_CURRENT_BANDS   = [0.0, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0, 100.0]   # Amperes
_VOLTAGE_BANDS   = [0.0, 0.01, 0.1, 1.0, 5.0, 10.0, 50.0, 100.0]    # Volts
_CONDUCT_BANDS   = [0.0, 1e-9, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0]    # Siemens
_POWER_BANDS     = [0.0, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0, 100.0]   # Watts
_IMPEDANCE_BANDS = [0.0, 0.01, 0.1, 1.0, 10.0, 100.0, 1e4, 1e6]     # Ohms

# ---------------------------------------------------------------------------
# Gray-code helpers
# ---------------------------------------------------------------------------

# _gray_bits imported from bridges.common — canonical highest-edge Gray encoder


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def ohms_law(V: float, I: float) -> float:
    """R = V/I. Returns float('inf') if I=0."""
    if I == 0:
        return float("inf")
    return V / I


def power_dissipation(V: float, I: float) -> float:
    """P = V · I (Watts)."""
    return V * I


def coulomb_force(q1: float, q2: float, r: float) -> float:
    """F = k·q₁q₂/r². Returns 0 if r=0."""
    if r == 0:
        return 0.0
    return K_COULOMB * q1 * q2 / (r * r)


def electric_field_magnitude(q: float, r: float) -> float:
    """E = k·|q|/r². Returns 0 if r=0."""
    if r == 0:
        return 0.0
    return K_COULOMB * abs(q) / (r * r)


def skin_depth(frequency_hz: float, conductivity_S: float) -> float:
    """δ = sqrt(2/(ω·μ₀·σ))  where ω = 2πf. Returns float('inf') if freq or sigma = 0."""
    if frequency_hz == 0 or conductivity_S == 0:
        return float("inf")
    omega = 2.0 * math.pi * frequency_hz
    return math.sqrt(2.0 / (omega * MU_0 * conductivity_S))


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class ElectricBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes electrical field and circuit geometry into a binary bitstring.

    Input geometry dict keys
    ------------------------
    charge         : list of floats — electric charges (Coulombs).
    current_A      : list of floats — electric currents (Amperes).
    voltage_V      : list of floats — voltages (Volts).
    conductivity_S : list of floats — conductivities (Siemens/m).

    Parameters
    ----------
    Vref : float
        Reference voltage for the ``above_vref`` flag (default 1.0 V).
    conduction_threshold : float
        Conductivity threshold for the ``conducting`` flag (default 1e-6 S).
    """

    def __init__(self, Vref: float = 1.0, conduction_threshold: float = 1e-6):
        super().__init__("electric")
        self.Vref = Vref
        self.conduction_threshold = conduction_threshold

    # ------------------------------------------------------------------
    # BinaryBridgeEncoder interface
    # ------------------------------------------------------------------

    def from_geometry(self, geometry_data: dict):
        """Load electrical field data from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded electrical geometry into a binary bitstring.

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
        # Section 1: charge  →  [positive 1b][charge_mag 3b Gray]
        # ------------------------------------------------------------------
        charge = data.get("charge", [])
        for q in charge:
            any_section = True
            positive = "1" if q > 0 else "0"
            bits.append(positive)
            bits.append(_gray_bits(abs(q), _CHARGE_BANDS))

        # ------------------------------------------------------------------
        # Section 2: current  →  [flowing 1b][current_mag 3b Gray]
        # ------------------------------------------------------------------
        current_A = data.get("current_A", [])
        for I in current_A:
            any_section = True
            flowing = "1" if I > 0 else "0"
            bits.append(flowing)
            bits.append(_gray_bits(abs(I), _CURRENT_BANDS))

        # ------------------------------------------------------------------
        # Section 3: voltage  →  [above_vref 1b][voltage_mag 3b Gray]
        # ------------------------------------------------------------------
        voltage_V = data.get("voltage_V", [])
        for V in voltage_V:
            any_section = True
            above_vref = "1" if V >= self.Vref else "0"
            bits.append(above_vref)
            bits.append(_gray_bits(abs(V), _VOLTAGE_BANDS))

        # ------------------------------------------------------------------
        # Section 4: conductivity  →  [conducting 1b][conduct_mag 3b Gray]
        # ------------------------------------------------------------------
        conductivity_S = data.get("conductivity_S", [])
        for sigma in conductivity_S:
            any_section = True
            conducting = "1" if sigma >= self.conduction_threshold else "0"
            bits.append(conducting)
            bits.append(_gray_bits(abs(sigma), _CONDUCT_BANDS))

        # ------------------------------------------------------------------
        # Summary  (7 bits, appended when at least one section has data)
        # ------------------------------------------------------------------
        if any_section:
            # Pair-wise power and impedance from voltage_V and current_A
            power_values = []
            impedance_values = []
            for V, I in zip(voltage_V, current_A):
                P = power_dissipation(V, I)
                Z = ohms_law(V, I)
                power_values.append(P)
                if math.isfinite(Z):
                    impedance_values.append(Z)

            n_power = len(power_values)
            mean_P = sum(power_values) / n_power if n_power > 0 else 0.0

            n_z = len(impedance_values)
            mean_Z = sum(impedance_values) / n_z if n_z > 0 else 0.0

            dissipative = "1" if mean_P > 0 else "0"
            bits.append(dissipative)
            bits.append(_gray_bits(mean_P, _POWER_BANDS))
            # Use mean_Z if finite (it is, having filtered inf above), else 0
            bits.append(_gray_bits(mean_Z if n_z > 0 else 0.0, _IMPEDANCE_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Electric Bridge Encoder — Physics Demo")
    print("=" * 60)

    # 1. Ohm's law
    V_demo = 12.0   # Volts
    I_demo = 0.5    # Amperes
    R = ohms_law(V_demo, I_demo)
    print(f"\n1. Ohm's law")
    print(f"   R = V/I = {V_demo} / {I_demo} = {R:.2f} Ω")

    # 2. Power dissipation
    P = power_dissipation(V_demo, I_demo)
    print(f"\n2. Power dissipation")
    print(f"   P = V·I = {V_demo} × {I_demo} = {P:.2f} W")

    # 3. Coulomb's law
    q1, q2 = 1e-6, -2e-6   # Coulombs
    r_c = 0.05             # metres
    F = coulomb_force(q1, q2, r_c)
    print(f"\n3. Coulomb's law")
    print(f"   q₁ = {q1:.1e} C,  q₂ = {q2:.1e} C,  r = {r_c} m")
    print(f"   F = k·q₁q₂/r² = {F:.4f} N  (attractive, expected ≈ -7.19 N)")

    # 4. Electric field magnitude
    q_src = 1e-9   # 1 nC
    r_ef  = 0.1    # m
    E_field = electric_field_magnitude(q_src, r_ef)
    print(f"\n4. Electric field magnitude")
    print(f"   q = {q_src:.1e} C,  r = {r_ef} m")
    print(f"   E = k|q|/r² = {E_field:.2f} V/m  (expected ≈ 899.75 V/m)")

    # 5. Skin depth (copper at 50 Hz)
    freq_hz   = 50.0        # Hz
    sigma_cu  = 5.96e7      # S/m  (copper conductivity)
    delta = skin_depth(freq_hz, sigma_cu)
    print(f"\n5. Skin depth (copper at {freq_hz} Hz)")
    print(f"   σ = {sigma_cu:.2e} S/m")
    print(f"   δ = √(2/(ω·μ₀·σ)) = {delta*1e3:.4f} mm  (expected ≈ 9.22 mm)")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "charge":         [1e-6, -3e-9, 5e-3],
        "current_A":      [0.5, -0.02, 10.0],
        "voltage_V":      [12.0, 0.5, 230.0],
        "conductivity_S": [5.96e7, 1e-8, 1e-3],
    }

    encoder = ElectricBridgeEncoder(Vref=1.0, conduction_threshold=1e-6)
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nVref                : {encoder.Vref} V")
    print(f"Conduction threshold: {encoder.conduction_threshold} S")
    print(f"Input geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
