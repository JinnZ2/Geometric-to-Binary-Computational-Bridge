# LIGHT Modality

- **Capture:** SPD (380–780 nm @ 5 nm step) or tristimulus XYZ.
- **Normalize:** unit area or exposure baseline → xyY.
- **Features:** band integrals (violet–red), chromaticity cell, top-2 peaks.
- **Quantize:** Gray-code bins (0..15 per band, 5 bits each for x,y).
- **Encode:** concat → 256-bit bitstring.
- **Compare:** Hamming distance; ΔE correlates with few-bit flips.
