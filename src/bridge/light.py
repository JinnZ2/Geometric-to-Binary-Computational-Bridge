import numpy as np
from .common import gray_code, bits_from_int

GRID = 32  # chromaticity grid size

def spd_to_xyY(wavelength_nm: np.ndarray, power: np.ndarray):
    """
    Convert Spectral Power Distribution (SPD) → approximate chromaticity (x, y, Y).
    For now: stub normalization; replace with proper CIE 1931 integration later.
    """
    power = np.array(power, dtype=float)
    norm = power / (np.sum(power) + 1e-12)

    # crude approximations (replace with real color matching functions)
    x = float(np.clip(np.sum(norm[:len(norm)//2]), 0, 1))
    y = float(np.clip(np.sum(norm[len(norm)//4:3*len(norm)//4]), 0, 1))
    Y = float(np.max(norm))

    return x, y, Y

def light_features(wavelength_nm: np.ndarray, power: np.ndarray) -> dict:
    """
    Extract normalized feature set from SPD.
    """
    x, y, Y = spd_to_xyY(wavelength_nm, power)

    bands = {
        "violet": float(np.sum(power[(wavelength_nm>=380)&(wavelength_nm<430)])),
        "blue":   float(np.sum(power[(wavelength_nm>=430)&(wavelength_nm<500)])),
        "green":  float(np.sum(power[(wavelength_nm>=500)&(wavelength_nm<570)])),
        "yellow": float(np.sum(power[(wavelength_nm>=570)&(wavelength_nm<590)])),
        "orange": float(np.sum(power[(wavelength_nm>=590)&(wavelength_nm<620)])),
        "red":    float(np.sum(power[(wavelength_nm>=620)&(wavelength_nm<=780)]))
    }

    # find top-2 peaks
    peaks_idx = np.argsort(power)[-2:][::-1]
    peaks_nm = [float(wavelength_nm[i]) for i in peaks_idx]

    return {
        "bands": bands,
        "chromaticity_xy": [x, y],
        "peaks_nm": peaks_nm,
        "luminance_Y": Y
    }

def encode_light_gray(features: dict, target_bits: int = 256) -> str:
    """
    Encode light features → stable Gray-coded bitstring.
    """
    bands = ["violet","blue","green","yellow","orange","red"]
    vals = np.array([features["bands"][b] for b in bands])
    vals = vals / (np.sum(vals) + 1e-12)

    # 4-bit Gray code per band (0..15)
    bins = (vals * 15).astype(int)
    band_bits = ''.join(bits_from_int(gray_code(int(b)), 4) for b in bins)

    # quantize chromaticity into GRID×GRID
    x, y = features["chromaticity_xy"]
    cx = int(np.clip(x*(GRID-1), 0, GRID-1))
    cy = int(np.clip(y*(GRID-1), 0, GRID-1))
    xy_bits = bits_from_int(gray_code(cx), 5) + bits_from_int(gray_code(cy), 5)

    payload = band_bits + xy_bits
    return (payload * ((target_bits // len(payload)) + 1))[:target_bits]
