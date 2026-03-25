"""
Thermal Bridge Encoder
======================
Encodes thermal field geometry into binary using core thermodynamics equations
and Gray-coded magnitude bands for all continuous quantities.

Equations implemented
---------------------
  Wien's displacement law   :  λ_max = b / T           (peak emission wavelength)
  Stefan-Boltzmann radiance :  M = ε·σ·T⁴             (total radiated power)
  Fourier heat conduction   :  q = -k · dT/dx          (heat flux)
  Newton cooling            :  Q̇ = h · (T_obj − T_env) (convective cooling rate)
  Johnson-Nyquist noise     :  V_n = √(4·k_B·T·R·Δf)  (thermal noise voltage)

Bit layout (39 bits for 3-sample canonical input)
--------------------------------------------------
Per temperature sample  (8 bits each):
  [above_bio  1b]       T > 310 K (above biological threshold) = 1
  [temp_mag   3b Gray]  T across 8 log bands (1 K → 6000 K)
  [infrared   1b]       λ_peak > 700 nm (infrared emitter) = 1
  [wien_band  3b Gray]  λ_peak across 8 log bands (100 nm → 100 µm)

Per heat-flux sample  (4 bits each):
  [heating    1b]       q > 0 (net heat gain) = 1
  [flux_mag   3b Gray]  |q| across 8 log W/m² bands

Summary  (7 bits — appended when any section present):
  [hot_majority  1b]       majority of temperatures above 273 K (above freezing) = 1
  [radiance_band 3b Gray]  mean Stefan-Boltzmann radiance (8 log W/m² bands)
  [noise_band    3b Gray]  Johnson-Nyquist noise voltage at mean T (8 log µV bands)
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
K_B       = 1.381e-23   # Boltzmann constant (J/K)
SIGMA     = 5.670e-8    # Stefan-Boltzmann constant (W/m²·K⁴)
WIEN_B    = 2.898e-3    # Wien's displacement constant (m·K)

# ---------------------------------------------------------------------------
# Band thresholds
# ---------------------------------------------------------------------------
_TEMP_BANDS   = [0.0, 1.0, 10.0, 100.0, 273.0, 310.0, 1000.0, 6000.0]      # K
_WIEN_BANDS   = [0.0, 1e-7, 2e-7, 4e-7, 7e-7, 1e-6, 1e-5, 1e-4]           # m (UV→IR)
_FLUX_BANDS   = [0.0, 1e-2, 1.0, 10.0, 100.0, 1e3, 1e5, 1e7]              # W/m²
_RAD_BANDS    = [0.0, 1e-4, 1e-1, 1.0, 10.0, 1e3, 1e5, 1e7]               # W/m²
_NOISE_BANDS  = [0.0, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]          # V


# ---------------------------------------------------------------------------
# Physics functions (pure, importable)
# ---------------------------------------------------------------------------

def blackbody_peak_wavelength(T_K: float) -> float:
    """
    Wien's displacement law: λ_max = b / T.

    Returns peak emission wavelength in metres. Returns inf if T=0.
    """
    if T_K <= 0.0:
        return float("inf")
    return WIEN_B / T_K


def stefan_boltzmann_radiance(T_K: float, emissivity: float = 1.0) -> float:
    """
    Total radiated power: M = ε·σ·T⁴  (W/m²).

    emissivity is in [0, 1]; a perfect blackbody has ε = 1.
    """
    return emissivity * SIGMA * T_K ** 4


def heat_flux_fourier(k: float, dT_dx: float) -> float:
    """
    Fourier's law of heat conduction: q = -k · (dT/dx)  (W/m²).

    k      : thermal conductivity (W/m·K)
    dT_dx  : temperature gradient (K/m); positive = temperature increases with x
    Returns signed heat flux (negative = flows in +x direction when gradient is positive).
    """
    return -k * dT_dx


def newton_cooling_rate(h: float, T_obj: float, T_env: float) -> float:
    """
    Newton's law of cooling: Q̇ = h · (T_obj − T_env)  (W/m²).

    h      : convective heat-transfer coefficient (W/m²·K)
    Positive result means the object is losing heat to the environment.
    """
    return h * (T_obj - T_env)


def johnson_nyquist_noise(T_K: float, R_ohm: float, bandwidth_hz: float) -> float:
    """
    Johnson-Nyquist thermal noise voltage: V_n = √(4·k_B·T·R·Δf)  (V).

    The RMS noise voltage across a resistor R at temperature T over bandwidth Δf.
    Connects thermal energy directly to information-layer noise — relevant for
    AI sensing and the consciousness bridge.
    """
    if T_K <= 0.0 or R_ohm <= 0.0 or bandwidth_hz <= 0.0:
        return 0.0
    return math.sqrt(4.0 * K_B * T_K * R_ohm * bandwidth_hz)


# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class ThermalBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes thermal field geometry into a binary bitstring.

    Input geometry dict keys
    ------------------------
    temperatures_K  : list of floats — temperature values in Kelvin
    emissivity      : list of floats in [0, 1] — surface emissivities
                      (defaults to 1.0 / blackbody if shorter than temperatures_K)
    heat_flux_W_m2  : list of floats — signed heat flux values (W/m²);
                      positive = net heat gain by the surface
    reference_R_ohm : float — resistance for Johnson-Nyquist summary (default 1000 Ω)
    bandwidth_hz    : float — noise bandwidth for summary (default 1000 Hz)
    """

    def __init__(self, reference_R_ohm: float = 1000.0, bandwidth_hz: float = 1000.0):
        super().__init__("thermal")
        self.reference_R_ohm = reference_R_ohm
        self.bandwidth_hz    = bandwidth_hz

    def from_geometry(self, geometry_data: dict):
        """Load thermal field data from a geometry dict."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert loaded thermal geometry into a binary bitstring.

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
        temperatures = data.get("temperatures_K", [])
        emissivities = data.get("emissivity", [])
        heat_fluxes  = data.get("heat_flux_W_m2", [])
        bits         = []
        any_section  = False

        # ------------------------------------------------------------------
        # Section 1: temperature samples  →  8 bits each
        #   [above_bio 1b][temp_mag 3b Gray][infrared 1b][wien_band 3b Gray]
        # ------------------------------------------------------------------
        for i, T in enumerate(temperatures):
            any_section = True
            eps  = emissivities[i] if i < len(emissivities) else 1.0
            lam  = blackbody_peak_wavelength(T)

            above_bio = "1" if T > 310.0 else "0"
            temp_mag  = _gray_bits(T, _TEMP_BANDS)
            infrared  = "1" if (math.isfinite(lam) and lam > 700e-9) else "0"
            clamp_lam = lam if math.isfinite(lam) else 0.0
            wien_band = _gray_bits(clamp_lam, _WIEN_BANDS)

            bits.append(above_bio)
            bits.append(temp_mag)
            bits.append(infrared)
            bits.append(wien_band)

        # ------------------------------------------------------------------
        # Section 2: heat-flux samples  →  4 bits each
        #   [heating 1b][flux_mag 3b Gray]
        # ------------------------------------------------------------------
        for q in heat_fluxes:
            any_section = True
            heating  = "1" if q > 0.0 else "0"
            flux_mag = _gray_bits(abs(q), _FLUX_BANDS)
            bits.append(heating)
            bits.append(flux_mag)

        # ------------------------------------------------------------------
        # Summary  (7 bits, appended when any section has data)
        # ------------------------------------------------------------------
        if any_section:
            # hot_majority: more than half of temperatures above freezing (273 K)
            if temperatures:
                n_above = sum(1 for T in temperatures if T > 273.0)
                hot_majority = "1" if n_above > len(temperatures) - n_above else "0"
                mean_T = sum(temperatures) / len(temperatures)
            else:
                hot_majority = "0"
                mean_T = 0.0

            # mean Stefan-Boltzmann radiance (use mean emissivity or 1.0)
            mean_eps = (sum(emissivities) / len(emissivities)) if emissivities else 1.0
            mean_rad = stefan_boltzmann_radiance(mean_T, mean_eps)

            # Johnson-Nyquist noise voltage at mean temperature
            noise_V = johnson_nyquist_noise(mean_T, self.reference_R_ohm, self.bandwidth_hz)

            bits.append(hot_majority)
            bits.append(_gray_bits(mean_rad, _RAD_BANDS))
            bits.append(_gray_bits(noise_V, _NOISE_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Thermal Bridge Encoder — Physics Demo")
    print("=" * 60)

    # 1. Wien's displacement — peak wavelengths for common sources
    sources = [("Human body", 310.0), ("Incandescent bulb", 2800.0),
               ("Sun surface", 5778.0), ("Liquid nitrogen", 77.0)]
    print("\n1. Wien's displacement law  λ_max = b/T")
    for name, T in sources:
        lam = blackbody_peak_wavelength(T)
        print(f"   {name:20s}  T={T:6.0f} K → λ_max = {lam*1e6:.3f} µm")

    # 2. Stefan-Boltzmann radiance
    print("\n2. Stefan-Boltzmann radiance  M = ε·σ·T⁴")
    for name, T in sources:
        M = stefan_boltzmann_radiance(T, emissivity=1.0)
        print(f"   {name:20s}  T={T:6.0f} K → M = {M:.3e} W/m²")

    # 3. Fourier conduction through a steel wall
    k_steel = 50.0       # W/m·K
    dT_dx   = -100.0     # K/m  (100°C drop per metre)
    q = heat_flux_fourier(k_steel, dT_dx)
    print(f"\n3. Fourier conduction (steel, k=50 W/m·K, ΔT/Δx=-100 K/m)")
    print(f"   q = -k·dT/dx = {q:.0f} W/m²  (positive = flows in +x direction)")

    # 4. Newton cooling — hot coffee (360 K) in room (295 K)
    h_coffee = 10.0   # W/m²·K  (natural convection)
    rate = newton_cooling_rate(h_coffee, T_obj=360.0, T_env=295.0)
    print(f"\n4. Newton cooling (coffee at 360 K, room at 295 K, h=10 W/m²·K)")
    print(f"   Q̇ = h·ΔT = {rate:.1f} W/m²")

    # 5. Johnson-Nyquist noise — 1 kΩ resistor at room temperature
    V_n = johnson_nyquist_noise(T_K=293.0, R_ohm=1000.0, bandwidth_hz=1000.0)
    print(f"\n5. Johnson-Nyquist noise  (1 kΩ, T=293 K, BW=1 kHz)")
    print(f"   V_n = √(4k_B·T·R·Δf) = {V_n*1e9:.2f} nV  (spectral density ≈ 4 nV/√Hz × √1000)")

    # Full encoding demo
    print("\n" + "=" * 60)
    print("Encoding demo")
    print("=" * 60)

    geometry = {
        "temperatures_K":  [77.0, 293.0, 5778.0],      # liquid N₂, room, solar
        "emissivity":      [0.95, 0.85, 1.0],
        "heat_flux_W_m2":  [500.0, -120.0],             # gain, loss
    }

    encoder = ThermalBridgeEncoder(reference_R_ohm=1000.0, bandwidth_hz=1000.0)
    encoder.from_geometry(geometry)
    binary = encoder.to_binary()

    print(f"\nInput geometry keys : {list(geometry.keys())}")
    print(f"Binary output       : {binary}")
    print(f"Total bits          : {len(binary)}")
    print(f"Report              : {encoder.report()}")
