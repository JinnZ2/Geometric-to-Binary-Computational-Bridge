"""
Chemical Bridge Encoder
=======================
Encodes chemical / molecular geometry into binary using core physical-chemistry
equations and Gray-coded magnitude bands for all continuous quantities.

Equations implemented
---------------------
  Arrhenius rate constant  :  k = A · exp(-Ea / R·T)   (reaction rate)
  Nernst potential         :  E = (RT/zF) · ln([ox]/[red])  (electrochemical)
  Henry's law              :  C = K_H · P               (gas dissolution)
  Bond dissociation energy :  ΔH_bond = Σ E_broken − Σ E_formed  (simple sum)
  pH / acidity             :  pH = -log10([H⁺])

Bit layout (39 bits for 3-sample canonical input)
--------------------------------------------------
Per molecular sample  (8 bits each):
  [reactive   1b]       rate constant k > rate_threshold = 1
  [rate_mag   3b Gray]  k across 8 log bands (10⁻¹² → 10⁶ s⁻¹)
  [acidic     1b]       pH < 7 = 1
  [pH_band    3b Gray]  pH across 8 linear bands [0, 14]

Per bond sample  (4 bits each):
  [exothermic 1b]       ΔH_bond < 0 (energy released) = 1
  [bond_mag   3b Gray]  |ΔH_bond| across 8 log kJ/mol bands

Summary  (7 bits — appended when any section present):
  [net_reactive 1b]       majority of rate constants above threshold = 1
  [nernst_band  3b Gray]  Nernst potential magnitude (8 linear mV bands)
  [henry_band   3b Gray]  Henry dissolution concentration (8 log mol/L bands)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
R_GAS  = 8.314      # Universal gas constant (J/mol·K)
F_FAR  = 96485.0    # Faraday's constant (C/mol)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_RATE_BANDS   = [0.0, 1e-12, 1e-9, 1e-6, 1e-3, 1.0, 1e3, 1e6]      # s⁻¹
_PH_BANDS     = [0.0, 2.0, 4.0, 6.0, 7.0, 8.0, 10.0, 12.0]          # pH units
_BOND_BANDS   = [0.0, 10.0, 50.0, 150.0, 300.0, 400.0, 600.0, 1000.0] # kJ/mol
_NERNST_BANDS = [0.0, 5.0, 10.0, 25.0, 50.0, 100.0, 500.0, 1000.0]  # mV
_HENRY_BANDS  = [0.0, 1e-8, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0]      # mol/L


# ---------------------------------------------------------------------------
# Physics / chemistry functions (pure, importable)
# ---------------------------------------------------------------------------

def arrhenius_rate(A: float, Ea_J_mol: float, T_K: float) -> float:
    """
    Arrhenius equation: k = A · exp(−Ea / RT).

    A          : pre-exponential factor (same units as k, typically s⁻¹)
    Ea_J_mol   : activation energy (J/mol)
    T_K        : temperature (K)
    Returns 0 if T=0 (reaction frozen).
    """
    if T_K <= 0.0:
        return 0.0
    exponent = -Ea_J_mol / (R_GAS * T_K)
    # Guard against extreme underflow
    if exponent < -700:
        return 0.0
    return A * math.exp(exponent)


def nernst_potential(T_K: float, z: int,
                     c_oxidised: float, c_reduced: float) -> float:
    """
    Nernst equation: E = (RT / zF) · ln([ox]/[red])  (Volts).

    T_K         : temperature (K)
    z           : number of electrons transferred (int, must be non-zero)
    c_oxidised  : concentration of oxidised species (mol/L)
    c_reduced   : concentration of reduced species (mol/L)
    Returns 0 if either concentration is 0 or z=0.
    """
    if z == 0 or c_oxidised <= 0.0 or c_reduced <= 0.0:
        return 0.0
    return (R_GAS * T_K / (z * F_FAR)) * math.log(c_oxidised / c_reduced)


def henry_concentration(K_H: float, partial_pressure_pa: float) -> float:
    """
    Henry's law: C = K_H · P  — dissolved gas concentration (mol/L).

    K_H                 : Henry's law constant (mol/L/Pa)
    partial_pressure_pa : partial pressure of gas (Pa)
    """
    return K_H * partial_pressure_pa


def bond_energy_delta(broken_kJ_mol: list, formed_kJ_mol: list) -> float:
    """
    Simple bond-energy summation: ΔH = Σ E_broken − Σ E_formed  (kJ/mol).

    Positive result = endothermic (energy absorbed).
    Negative result = exothermic (energy released).
    """
    return sum(broken_kJ_mol) - sum(formed_kJ_mol)


def ph_from_concentration(H_conc_mol_L: float) -> float:
    """
    pH = −log₁₀([H⁺]).

    H_conc_mol_L : hydrogen ion concentration (mol/L).
    Returns 0 if concentration is 0.
    """
    if H_conc_mol_L <= 0.0:
        return 0.0
    return -math.log10(H_conc_mol_L)


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class ChemicalBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes chemical / molecular geometry into a binary bitstring.

    Input geometry dict keys
    ------------------------
    rate_constants    : list of floats — reaction rate constants (s⁻¹)
    ph_values         : list of floats — pH of each molecular environment
    bond_deltas_kJ    : list of floats — bond energy changes (kJ/mol);
                        negative = exothermic
    nernst_inputs     : list of dicts with keys {T_K, z, c_ox, c_red}
                        for Nernst potential summary
    henry_inputs      : list of dicts with keys {K_H, P_pa}
                        for Henry dissolution summary
    rate_threshold    : float — rate above which reaction is "active"
                        (default 1e-3 s⁻¹)
    """

    def __init__(self, rate_threshold: float = 1e-3):
        super().__init__("chemical")
        self.rate_threshold = rate_threshold

    def from_geometry(self, geometry_data: dict):
        """Load chemical geometry data dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded chemical geometry into a binary bitstring.

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

        data           = self.input_geometry
        rate_constants = data.get("rate_constants", [])
        ph_values      = data.get("ph_values", [])
        bond_deltas    = data.get("bond_deltas_kJ", [])
        nernst_inputs  = data.get("nernst_inputs", [])
        henry_inputs   = data.get("henry_inputs", [])
        bits           = []
        any_section    = False

        # ------------------------------------------------------------------
        # Section 1: rate constant + pH pairs  →  8 bits each
        #   [reactive 1b][rate_mag 3b Gray][acidic 1b][pH_band 3b Gray]
        # ------------------------------------------------------------------
        n_samples = max(len(rate_constants), len(ph_values))
        for i in range(n_samples):
            any_section = True
            k   = rate_constants[i] if i < len(rate_constants) else 0.0
            pH  = ph_values[i]      if i < len(ph_values)      else 7.0

            reactive = "1" if k > self.rate_threshold else "0"
            rate_mag = _gray_bits(k, _RATE_BANDS)
            acidic   = "1" if pH < 7.0 else "0"
            ph_band  = _gray_bits(pH, _PH_BANDS)

            bits.append(reactive)
            bits.append(rate_mag)
            bits.append(acidic)
            bits.append(ph_band)

        # ------------------------------------------------------------------
        # Section 2: bond energy deltas  →  4 bits each
        #   [exothermic 1b][bond_mag 3b Gray]
        # ------------------------------------------------------------------
        for dH in bond_deltas:
            any_section = True
            exothermic = "1" if dH < 0.0 else "0"
            bond_mag   = _gray_bits(abs(dH), _BOND_BANDS)
            bits.append(exothermic)
            bits.append(bond_mag)

        # ------------------------------------------------------------------
        # Summary  (7 bits)
        # ------------------------------------------------------------------
        if any_section:
            # net_reactive: majority of rate constants above threshold
            if rate_constants:
                n_active     = sum(1 for k in rate_constants if k > self.rate_threshold)
                net_reactive = "1" if n_active > len(rate_constants) - n_active else "0"
            else:
                net_reactive = "0"

            # Nernst potential: use first entry or 0
            if nernst_inputs:
                ni = nernst_inputs[0]
                E_V = nernst_potential(ni.get("T_K", 298.15), ni.get("z", 1),
                                       ni.get("c_ox", 1.0),   ni.get("c_red", 1.0))
                nernst_mV = abs(E_V) * 1000.0
            else:
                nernst_mV = 0.0

            # Henry concentration: use first entry or 0
            if henry_inputs:
                hi = henry_inputs[0]
                henry_C = henry_concentration(hi.get("K_H", 0.0), hi.get("P_pa", 0.0))
            else:
                henry_C = 0.0

            bits.append(net_reactive)
            bits.append(_gray_bits(nernst_mV, _NERNST_BANDS))
            bits.append(_gray_bits(henry_C, _HENRY_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Chemical Bridge Encoder — Physics Demo")
    print("=" * 60)

    # 1. Arrhenius — activation energies at body temperature
    T_body = 310.0   # K
    reactions = [
        ("Enzyme-catalysed (Ea≈40 kJ/mol)",  1e12, 40e3),
        ("Uncatalysed organic (Ea≈80 kJ/mol)", 1e13, 80e3),
        ("Combustion (Ea≈150 kJ/mol)",         1e15, 150e3),
    ]
    print(f"\n1. Arrhenius rate constants at T = {T_body} K")
    for label, A, Ea in reactions:
        k = arrhenius_rate(A, Ea, T_body)
        print(f"   {label:42s}  k = {k:.3e} s⁻¹")

    # 2. Nernst potential — copper half-cell (standard conditions)
    E_Cu = nernst_potential(T_K=298.15, z=2, c_oxidised=1.0, c_reduced=1.0)
    E_dil = nernst_potential(T_K=298.15, z=2, c_oxidised=0.001, c_reduced=1.0)
    print(f"\n2. Nernst potential (Cu²⁺/Cu, z=2)")
    print(f"   Standard (1 M / 1 M)      : {E_Cu*1000:.2f} mV")
    print(f"   Dilute   (0.001 M / 1 M)  : {E_dil*1000:.2f} mV  (expected ≈ −88.7 mV)")

    # 3. Henry's law — oxygen dissolving in water at 25°C
    K_H_O2 = 1.3e-8   # mol/L/Pa at 25°C
    P_O2   = 21278.0   # Pa  (21% of 1 atm)
    C_O2   = henry_concentration(K_H_O2, P_O2)
    print(f"\n3. Henry's law (O₂ in water, 25°C, P_O₂ = {P_O2:.0f} Pa)")
    print(f"   C_O₂ = K_H · P = {C_O2*1000:.4f} mmol/L  (expected ≈ 0.276 mmol/L)")

    # 4. Bond energy — combustion of H₂ (H-H + ½O=O → H-O-H)
    dH = bond_energy_delta(broken_kJ_mol=[436.0, 249.0],   # H-H + ½ O=O
                           formed_kJ_mol=[2 * 497.0])       # 2 × O-H bonds
    print(f"\n4. Bond energy — H₂ combustion  H-H + ½O=O → H₂O")
    print(f"   ΔH = Σ broken − Σ formed = {dH:.1f} kJ/mol  (expected ≈ −309 kJ/mol)")

    # 5. pH scale examples
    print(f"\n5. pH calculation  pH = −log₁₀([H⁺])")
    for label, conc in [("Stomach acid  [H⁺]=0.1 M", 0.1),
                         ("Pure water    [H⁺]=1e-7 M", 1e-7),
                         ("Bleach        [H⁺]=1e-13 M", 1e-13)]:
        print(f"   {label:40s}  pH = {ph_from_concentration(conc):.1f}")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "rate_constants": [0.05, 1e-5, 2.3],
        "ph_values":      [3.2, 7.4, 9.1],
        "bond_deltas_kJ": [-309.0, 50.0],
        "nernst_inputs":  [{"T_K": 298.15, "z": 2, "c_ox": 0.001, "c_red": 1.0}],
        "henry_inputs":   [{"K_H": 1.3e-8, "P_pa": 21278.0}],
    }

    encoder = ChemicalBridgeEncoder(rate_threshold=1e-3)
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
