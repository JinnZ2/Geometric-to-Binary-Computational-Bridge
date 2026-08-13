"""
temperature.py  (fabrication/)

Central temperature compensation. Every physical property shifts with
temperature; this module holds the corrections so a prediction made at one
temperature can be verified at another.

Entry point for normalising a reading before a verdict:

    normalize_measurement(value, domain, var, temp_c, ref_temp_c)

=====================================================================
AUDIT
=====================================================================
Behaviour is UNCHANGED from the file as supplied. Two of the five findings
below make a correction actively wrong rather than merely imprecise, so read
TMP-1 and TMP-2 before threading this into a verifier.

What is right and is the point of the file: `c_air`, `rho_air`,
`thermal_expand`, and the acoustic frequency scaling. Those cover the case the
whole exercise started from -- a prediction made at +20 C read at -40 C is
10.6 % off in frequency -- and `acoustic_f_correct` fixes it.

TMP-1  The mechanical resonance correction is ~20x too small and points the
       wrong way.
       `k_correct` returns `k * (1 + alpha*dT)` on the stated reasoning that
       "E changes slightly with temperature; dominant effect is length". For
       steel the two coefficients are alpha = 12e-6/C and dE/E ~ -2.4e-4/C:
       the modulus term is TWENTY TIMES larger and opposite in sign, so the
       reasoning is inverted and the magnitude is off by the same factor.

         dT = +40 C   this module: df/f = +0.024 %
                      physics:     df/f = -0.480 %

       `normalize_measurement(..., "mechanical", "resonance_freq_Hz", ...)`
       divides the reading by sqrt(k_corr), so a resonance measured in a cold
       shop is moved the wrong direction by 1/20 of the right amount. Against
       the +/-8 % mechanical band that is not yet decisive -- which is exactly
       why it would survive a bench test and stay wrong. Open problem TMP-A.

TMP-2  Three reference temperatures inside one module, and one crossing.
       `thermal_expand`, `r_correct`, `c_correct`, `l_correct` and `k_correct`
       default `ref_temp_c = 20.0`; `helmholtz_f_correct`, `acoustic_f_correct`
       and `normalize_measurement` default to 15.0. `normalize_measurement`
       then passes its 15.0 into `r_correct`, whose TCR of 0.00393 is the
       copper value SPECIFIED at 20 C. This is the same defect the field
       guide's contraction table had -- percentages with no stated reference,
       back-solving to three different ones -- now in executable form, where
       it silently biases every electrical normalisation by
       TCR * 5 C = 2 %.

TMP-3  Two different corrections for one physics, and the docstrings are
       swapped. `acoustic_f_correct` uses the linear `c_air` ratio;
       `helmholtz_f_correct` uses the exact sqrt(T_ref/T_meas). A Helmholtz
       resonance is an acoustic mode, so the same reading corrected by the two
       functions differs -- 0.28 % at -40 C. And `helmholtz_f_correct`'s
       docstring says "simplified linear approximation for small dT" while its
       body is the exact form; `acoustic_f_correct`, which is the linear one,
       says nothing.

TMP-4  `mu_water` has no stated range and returns a constant below 0 C.
       Measured against tabulated values: +0 % at 0 C, +6 % at 20 C, -11 % at
       50 C, -53 % at 100 C. And `if temp_c < 0: return 1.79e-3` gives the
       same number for -1 C and -40 C -- water is ice there, so the honest
       answer is a refusal or an explicit antifreeze model, not the 0 C value.

TMP-5  `c_air` claims validity from -50 to +50 C without a number. Measured
       against 331.3*sqrt(1 + T/273.15): 0.52 % at -50 C, 0.32 % at -40 C,
       0.08 % at -20 C, 0.35 % at +50 C. The claim is true; it is worth
       carrying the figure, because 0.5 % against a +/-8 % acoustic band is
       fine and against a +/-1 % electrical band is not.

Also unsourced rather than wrong: `c_correct`'s default of -200 ppm/C is
labelled X7R, which is a +/-15 % nonlinear characteristic over its range, not
a linear tempco; C0G is +/-30 ppm/C. Neither is -200. Same for `l_correct`'s
+300 ppm/C ferrite figure. Both are placeholders and neither says so.

License: CC0. Stdlib only.
"""
import math

# Speed of sound in air (m/s) as function of temperature (°C)
def c_air(temp_c: float = 15.0) -> float:
    """
    Approximate speed of sound in dry air.
    Valid from -50°C to +50°C.
    """
    return 331.3 + 0.606 * temp_c

# Air density (kg/m³) as function of temperature (°C) at 1 atm
def rho_air(temp_c: float = 15.0) -> float:
    """
    Approximate density of dry air at sea level.
    """
    t_k = temp_c + 273.15
    return 101325.0 / (287.05 * t_k)

# Thermal expansion: linear dimension correction
def thermal_expand(length_m: float, temp_c: float, 
                   ref_temp_c: float = 20.0,
                   alpha: float = 12e-6) -> float:
    """
    Correct a length measurement to reference temperature.

    length_m: measured length at temp_c
    alpha: linear thermal expansion coefficient (default steel)

    Returns: equivalent length at ref_temp_c
    """
    return length_m / (1.0 + alpha * (temp_c - ref_temp_c))

# Material expansion coefficients (per °C)
ALPHA = {
    "steel": 12e-6,
    "aluminum": 23e-6,
    "copper": 17e-6,
    "concrete": 10e-6,
    "wood_parallel": 4e-6,
    "wood_perp": 40e-6,
    "glass": 9e-6,
    "pla": 70e-6,      # 3D print filament
    "abs": 90e-6,
    "petg": 65e-6,
}

# Electrical: resistor temperature coefficient
def r_correct(r_measured: float, temp_c: float,
              tcr: float = 0.00393, ref_temp_c: float = 20.0) -> float:
    """
    Correct resistance measurement to reference temperature.
    Default TCR for copper; use 0.00429 for aluminum.
    """
    return r_measured / (1.0 + tcr * (temp_c - ref_temp_c))

# Capacitor temperature coefficient (simplified)
def c_correct(c_measured: float, temp_c: float,
              tempco_ppm: float = -200.0, ref_temp_c: float = 20.0) -> float:
    """
    Correct capacitance measurement. 
    tempco_ppm: ppm/°C (negative for ceramic X7R, near-zero for C0G)
    """
    return c_measured / (1.0 + tempco_ppm * 1e-6 * (temp_c - ref_temp_c))

# Inductor: core permeability drops with temperature
def l_correct(l_measured: float, temp_c: float,
              tempco_ppm: float = 300.0, ref_temp_c: float = 20.0) -> float:
    """
    Correct inductance. Ferrite cores typically increase then
    decrease; this is a simplified linear model.
    """
    return l_measured / (1.0 + tempco_ppm * 1e-6 * (temp_c - ref_temp_c))

# Spring constant temperature dependence (steel)
def k_correct(k_measured: float, temp_c: float,
            ref_temp_c: float = 20.0, alpha: float = ALPHA["steel"]) -> float:
    """
    Spring constant k ∝ E (Young's modulus) / L.
    E changes slightly with temperature; dominant effect is length.
    Simplified: k changes inversely with thermal expansion.
    """
    return k_measured * (1.0 + alpha * (temp_c - ref_temp_c))

# Helmholtz resonator: frequency temperature correction
def helmholtz_f_correct(f_measured: float, temp_c: float,
                        ref_temp_c: float = 15.0) -> float:
    """
    Correct measured Helmholtz frequency to reference temperature.
    f ∝ c ∝ √T, so f_ref = f_meas * √(T_ref / T_meas) in Kelvin.
    Simplified linear approximation for small ΔT.
    """
    t_meas = temp_c + 273.15
    t_ref = ref_temp_c + 273.15
    return f_measured * math.sqrt(t_ref / t_meas)

# Generic frequency correction for acoustic modes
def acoustic_f_correct(f_measured: float, temp_c: float,
                       ref_temp_c: float = 15.0) -> float:
    """All acoustic frequencies scale with c_air."""
    return f_measured * c_air(ref_temp_c) / c_air(temp_c)

# Fluid viscosity (water approximation)
def mu_water(temp_c: float) -> float:
    """Dynamic viscosity of water in Pa·s. Approximate."""
    if temp_c < 0:
        return 1.79e-3
    return 1.79e-3 * math.exp(-0.026 * temp_c)

# Complete measurement normalization
def normalize_measurement(value: float, domain: str, var: str,
                           temp_c: float, ref_temp_c: float = 15.0,
                           material: str = "steel") -> dict:
    """
    Normalize a measurement to reference temperature.

    Returns dict with:
      raw: original value
      normalized: corrected value
      correction_factor: normalized / raw
      domain, var, temp_c, ref_temp_c
    """
    corr = 1.0

    if domain == "acoustic" and var == "resonance_freq_Hz":
        normalized = acoustic_f_correct(value, temp_c, ref_temp_c)
        corr = normalized / value
    elif domain == "thermal" and var == "delta_T_steady_K":
        normalized = value
    elif domain == "electrical":
        if var == "R_value":
            normalized = r_correct(value, temp_c, ref_temp_c=ref_temp_c)
        elif var == "C_value":
            normalized = c_correct(value, temp_c, ref_temp_c=ref_temp_c)
        elif var == "L_value":
            normalized = l_correct(value, temp_c, ref_temp_c=ref_temp_c)
        else:
            normalized = value
        corr = normalized / value if value != 0 else 1.0
    elif domain == "mechanical" and var == "resonance_freq_Hz":
        alpha = ALPHA.get(material, ALPHA["steel"])
        k_corr = k_correct(1.0, temp_c, ref_temp_c, alpha)
        normalized = value / math.sqrt(k_corr)
        corr = normalized / value
    else:
        normalized = value

    return {
        "raw": value,
        "normalized": normalized,
        "correction_factor": round(corr, 6),
        "domain": domain,
        "var": var,
        "temp_c": temp_c,
        "ref_temp_c": ref_temp_c,
        "material": material,
    }
