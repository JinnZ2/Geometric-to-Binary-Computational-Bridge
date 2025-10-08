# GRAVITY Modality

The gravity bridge encodes states of curvature, attraction, and stability into binary.  
Where magnetic works through polarity, and light through wavelength, gravity works through mass-curvature and thresholds.

---

## Capture

- Input: simulated or measured gravitational field parameters.  
- Example: orbital dynamics, potential wells, local acceleration, curvature tensor approximations.  

---

## Normalize

- Scale potential relative to reference mass or frame.  
- Normalize curvature values into bounded ranges.  
- Distinguish stable vs unstable orbital states.

---

## Features

1. **Direction**  
   - Attraction (toward center) vs escape (beyond threshold).  
   - Binary: 0 = bound, 1 = unbound.  

2. **Curvature**  
   - Concave vs convex field.  
   - Binary: 0 = well, 1 = saddle/expansion.  

3. **Orbit Stability**  
   - Stable vs unstable orbits.  
   - Encoded as 2-bit state.  

4. **Mass Threshold**  
   - Below vs above binding threshold.  
   - Binary 0/1.  

---

## Quantize

- Gravity well depth mapped to 16 levels (4-bit Gray).  
- Orbital stability encoded as 2 bits.  
- Direction + curvature as 2 bits.  

---

## Encode

- Concatenate → repeat until 256-bit payload.  
- Encoding profile: `enc.gravity.gray.256.v1`.  

---

## Compare

- Hamming distance reflects system-level stability difference.  
- Similar wells = low distance.  
- Collapse vs escape = large distance.  
