"""
Light Bridge Encoder
====================
Encodes optical geometry into binary using physics equations
and Gray-coded magnitude bands for all continuous quantities.

Equations implemented
---------------------
  Photon energy     :  E = hc/λ  (using hc = 1240 eV·nm)
  Fringe visibility :  V = (I_max − I_min) / (I_max + I_min)
  Malus's law       :  I = I₀ · cos²(θ)
  Brewster's angle  :  θ_B = arctan(n₂/n₁)
  Beer-Lambert law  :  I = I₀ · exp(−α·l)

Bit layout
----------
Per photon sample  (8 bits each):
  [polarization 1b]       V=1 / H=0
  [wavelength   3b Gray]  8 spectral bands (UV-C → Red+)
  [interference 3b Gray]  8 intensity bands [0.0, 1.0]
  [spin         1b]       R=1 / L=0

Summary  (7 bits — appended when samples present):
  [energy_sign  1b]       mean E_photon > 2.5 eV = 1
  [energy_mag   3b Gray]  mean photon energy across 8 log eV bands
  [visibility   3b Gray]  fringe visibility across 8 linear bands [0,1]
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

HC_EV_NM = 1240.0        # hc in eV·nm (convenient form)

# ---------------------------------------------------------------------------
# Band thresholds  (8 bands each → 3 bits Gray)
# ---------------------------------------------------------------------------

_WAVELENGTH_BANDS    = [0.0, 280.0, 315.0, 400.0, 450.0, 495.0, 570.0, 620.0]   # nm  (UV-C → Red+)
_INTERFERENCE_BANDS  = [0.0, 0.125, 0.25,  0.375, 0.5,   0.625, 0.75,  0.875]   # normalised [0, 1]
_ENERGY_BANDS        = [0.0, 0.1,   0.5,   1.0,   2.0,   3.0,   5.0,   10.0]    # eV
_VISIBILITY_BANDS    = [0.0, 0.125, 0.25,  0.375, 0.5,   0.625, 0.75,  0.875]   # normalised [0, 1]

# ---------------------------------------------------------------------------
# Gray-code helpers
# ---------------------------------------------------------------------------

def _gray(n: int) -> int:
    return n ^ (n >> 1)


def _gray_bits(value: float, bands: list, n_bits: int = 3) -> str:
    """Map non-negative scalar to Gray-coded binary string. Scans edges highest→lowest."""
    band = 0
    for i in range(len(bands) - 1, -1, -1):
        if value >= bands[i]:
            band = i
            break
    return format(_gray(band), f'0{n_bits}b')

# ---------------------------------------------------------------------------
# Physics functions  (pure, importable)
# ---------------------------------------------------------------------------

def photon_energy_eV(wavelength_nm: float) -> float:
    """E = hc/λ  (hc = 1240 eV·nm). Returns 0 if wavelength <= 0."""
    if wavelength_nm <= 0:
        return 0.0
    return HC_EV_NM / wavelength_nm


def fringe_visibility(intensities: list) -> float:
    """V = (I_max − I_min) / (I_max + I_min). Returns 0 if list empty or sum=0."""
    if not intensities:
        return 0.0
    i_max = max(intensities)
    i_min = min(intensities)
    total = i_max + i_min
    if total == 0:
        return 0.0
    return (i_max - i_min) / total


def malus_intensity(I0: float, theta_deg: float) -> float:
    """I = I₀ · cos²(θ)   (Malus's law through a polarizer)."""
    theta_rad = math.radians(theta_deg)
    return I0 * (math.cos(theta_rad) ** 2)


def brewster_angle(n1: float, n2: float) -> float:
    """θ_B = arctan(n₂/n₁)  in degrees. Returns 0 if n1=0."""
    if n1 == 0:
        return 0.0
    return math.degrees(math.atan(n2 / n1))


def beer_lambert(I0: float, alpha: float, path_length: float) -> float:
    """I = I₀ · exp(−α·l)   (Beer-Lambert attenuation)."""
    return I0 * math.exp(-alpha * path_length)

# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class LightBridgeEncoder(BinaryBridgeEncoder):
    """Encodes optical geometry (photon samples) into a binary bitstring."""

    def __init__(self):
        super().__init__("light")

    def from_geometry(self, geometry_data):
        """Load optical geometry data dict and return self for chaining."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert photon sample geometry to a binary bitstring.

        Expected keys in geometry_data:
          polarization              : list of str, each "V" or "H"
          spectrum_nm               : list of float, wavelength in nm per photon
          interference_intensity    : list of float, normalised intensity [0, 1]
          photon_spin               : list of str, each "R" or "L"

        Returns a string of '0'/'1' characters.
        Raises ValueError if input_geometry has not been set.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry data loaded. Call from_geometry() before to_binary()."
            )

        geometry_data = self.input_geometry
        polarization               = geometry_data.get("polarization", [])
        spectrum_nm                = geometry_data.get("spectrum_nm", [])
        interference_intensity     = geometry_data.get("interference_intensity", [])
        photon_spin                = geometry_data.get("photon_spin", [])

        n = len(polarization)
        bits = []

        # -- Per-photon samples (8 bits each) --------------------------------
        for pol, lam, intensity, spin in zip(
            polarization, spectrum_nm, interference_intensity, photon_spin
        ):
            # 1b polarization: V=1, H=0
            bits.append("1" if pol == "V" else "0")

            # 3b wavelength Gray-coded
            bits.append(_gray_bits(lam, _WAVELENGTH_BANDS))

            # 3b interference intensity Gray-coded
            bits.append(_gray_bits(intensity, _INTERFERENCE_BANDS))

            # 1b spin: R=1, L=0
            bits.append("1" if spin == "R" else "0")

        # -- Summary (7 bits, only when at least one photon) -----------------
        if n > 0:
            energies = [photon_energy_eV(lam) for lam in spectrum_nm]
            E_mean = sum(energies) / len(energies)
            vis = fringe_visibility(interference_intensity)

            # 1b energy sign
            bits.append("1" if E_mean > 2.5 else "0")

            # 3b mean photon energy band
            bits.append(_gray_bits(E_mean, _ENERGY_BANDS))

            # 3b fringe visibility band
            bits.append(_gray_bits(vis, _VISIBILITY_BANDS))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Light Bridge Encoder — physics equation demo")
    print("=" * 60)

    # 1. Photon energy  E = hc/λ
    for wl in [254.0, 532.0, 700.0]:
        E = photon_energy_eV(wl)
        print(f"  photon_energy_eV({wl} nm)  = {E:.4f} eV")

    print()

    # 2. Fringe visibility  V = (I_max − I_min) / (I_max + I_min)
    pattern = [0.1, 0.5, 0.9, 0.5, 0.1]
    V = fringe_visibility(pattern)
    print(f"  fringe_visibility({pattern})  = {V:.4f}")

    print()

    # 3. Malus's law  I = I₀ · cos²(θ)
    for theta in [0.0, 45.0, 90.0]:
        I = malus_intensity(1.0, theta)
        print(f"  malus_intensity(I0=1.0, theta={theta}°)  = {I:.4f}")

    print()

    # 4. Brewster's angle  θ_B = arctan(n₂/n₁)
    theta_B = brewster_angle(1.0, 1.5)
    print(f"  brewster_angle(n1=1.0, n2=1.5)  = {theta_B:.4f}°")

    print()

    # 5. Beer-Lambert  I = I₀ · exp(−α·l)
    for alpha, l in [(0.1, 5.0), (1.0, 2.0), (0.5, 10.0)]:
        I = beer_lambert(1.0, alpha, l)
        print(f"  beer_lambert(I0=1.0, alpha={alpha}, l={l})  = {I:.4f}")

    print()

    # Full encoding demo
    geometry = {
        "polarization":           ["V", "H", "V"],
        "spectrum_nm":            [450.0, 532.0, 650.0],
        "interference_intensity": [0.8,   0.4,   0.6],
        "photon_spin":            ["R",   "L",   "R"],
    }

    encoder = LightBridgeEncoder()
    result = encoder.from_geometry(geometry).to_binary()
    print(f"  Encoded bitstring ({len(result)} bits):")
    print(f"    {result}")
    print(f"  Report: {encoder.report()}")
