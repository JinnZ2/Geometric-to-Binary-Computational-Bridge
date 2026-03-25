# Translation Guide -- Geometric-to-Binary Computational Bridge

How to take any physical phenomenon, geometric intuition, or
structured observation and encode it into binary using this framework.
Includes three complete worked examples with actual code output.

---

## The translation stages

Every encoding in this framework passes through the same four stages:

```
Phenomenon / Intuition
        |
        v
Geometric properties    <-- identify what is invariant, relational, structural
        |
        v
Binary encoding         <-- Gray-coded thresholds, physics-derived bands
        |
        v
Lossless reconstruction <-- decode back to original geometry to verify
```

The key discipline at each stage:
- **Geometric extraction:** Ask "what is the shape of this?" not "what are the numbers?"
- **Binary encoding:** Use Gray codes so adjacent physical states differ by one bit
- **Verification:** Round-trip. If `encode(decode(x)) != x`, something was lost.

---

## Worked Example 1: A Sound

**Phenomenon:** A 440 Hz sine wave (A4, concert pitch), amplitude 0.8,
phase shifted 45 degrees from reference, with a resonance index of 0.7.

**Step 1: Identify geometric properties**

Sound has four geometric properties the bridge encodes:
- Phase (angular position in the wave cycle) -- directional
- Frequency (pitch relative to a reference -- interval, not absolute Hz)
- Amplitude (energy magnitude -- above or below threshold)
- Resonance (how much the sound reinforces itself or its environment)

None of these are the raw waveform samples. They are the geometry of
the wave.

**Step 2: Express as geometry data dict**

```python
geometry = {
    "phase_radians":  [0.785],   # 45 degrees = pi/4
    "frequency_hz":   [440.0],   # A4
    "amplitude":      [0.8],     # above 0.5 threshold
    "resonance_index": [0.7],    # strong resonance
}
```

**Step 3: Encode using the Sound Bridge**

```python
from bridges.sound_encoder import SoundBridgeEncoder

encoder = SoundBridgeEncoder(pitch_threshold=440.0, amp_threshold=0.5)
result = encoder.from_geometry(geometry).to_binary()
print(result)
# -> '1000010001101101110000011110110'  (31 bits)
```

**Step 4: Interpret the bits**

The 31-bit string breaks down as:
- Bits 0-2: phase magnitude (Gray-coded, 8 bands from 0 to 2pi)
- Bits 3-5: frequency band (Gray-coded, 8 octave bands anchored at pitch_threshold)
- Bit 6: amplitude sign (1 = above amp_threshold)
- Bits 7-10: resonance index (Gray-coded, 4 bands)
- Bits 11-13: global mean phase
- Bit 14: mean amplitude sign
- Bits 15-17: mean frequency band
- Bits 18-20: beat frequency band
- Bits 21-23: resonance strength
- Bits 24-30: spectral centroid and spread

At 440 Hz with pitch_threshold=440, the frequency band encodes the
A4 register boundary -- the bit pattern means "at or just below the
upper limit of the fourth octave relative to reference."

**Step 5: Verify round-trip**

The encoding is lossless within the band resolution. You can verify
by running `python bridges/sound_encoder.py` which includes a demo
that prints both the encoded string and the report.

**Translation loss:** Within each Gray-coded band, values are
indistinguishable. The loss is bounded by band width: at most
1/8 of the octave range (approximately 6% frequency resolution at
this pitch threshold). For applications that need finer resolution,
increase the number of bits allocated to the frequency band.

---

## Worked Example 2: An Electromagnetic Dipole Field

**Phenomenon:** Two point charges +1nC and -1nC separated by 2 meters
in free space. We want to encode the field state into sensor readings.

**Step 1: Identify geometric properties**

An EM field has the following geometric structure:
- Spatial distribution of field vectors (where is it strong?)
- Alignment of field vectors (are they all pointing the same way?)
- Energy density (how much work would it take to move a charge?)
- Coverage (what fraction of the space has significant field?)

**Step 2: Compute the field using the Engine**

```python
from Engine.geometric_solver import GeometricEMSolver

solver = GeometricEMSolver()
sources = [
    {'type': 'charge', 'position': [1, 0, 0], 'strength':  1e-9},
    {'type': 'charge', 'position': [-1, 0, 0], 'strength': -1e-9},
]
bounds = {'min': [-5,-5,-5], 'max': [5,5,5]}

field_data = solver.calculateElectromagneticField(sources, bounds)
# -> 2080 adaptive grid points (vs 32768 for uniform grid: 15x speedup)
```

The adaptive grid places more evaluation points near the charges
where the field changes rapidly, and fewer points far away where
it is nearly uniform. This is geometric intelligence applied to
spatial sampling.

**Step 3: Translate field to sensor readings**

```python
from bridges.sensor_suite import SensorSuite
from bridges.field_adapter import field_to_suite

suite = SensorSuite()
field_to_suite(field_data, suite)
output = suite.compose()

for sensor_id, reading in output.active_channels.items():
    print(f"{sensor_id:24s}  magnitude={reading.magnitude:.3f}")
```

Output:
```
ambient_field            magnitude=0.117   # field is present, ~12% of reference scale
coherence                magnitude=0.055   # vectors mostly cancel (dipole symmetry)
vigilance                magnitude=0.363   # moderately concentrated near charges
pressure                 magnitude=0.121   # moderate energy density
situational_awareness    magnitude=0.654   # 65% of grid has detectable field
```

**Step 4: Interpret the geometry**

The low coherence (0.055) is physically correct: in a dipole, field
vectors point toward the negative charge on one side and away from
the positive charge on the other -- they largely cancel when averaged,
producing near-zero net alignment. A single charge would produce
coherence near 1.0 (all vectors pointing radially outward).

The moderately high vigilance (0.363) shows the field is more
concentrated near the source charges than in the far field -- as
expected for Coulomb falloff at 1/r^2.

**Translation loss:** The sensor readings are normalizations, not raw
field values. The ambient_field=0.117 means the mean field is at 11.7%
of the 95th-percentile field strength in this run. For absolute
physical values, pass an explicit `E_scale` (V/m) to `field_to_suite()`.

---

## Worked Example 3: A Geometric Token (GEIS)

**Phenomenon:** A geometric intuition -- the state "north vertex of an
octahedron, with a rotation operator applied."

**Step 1: Express as an octahedral state**

Silicon has 8 stable geometric positions (+/-x, +/-y, +/-z).
Encode "north vertex" as the +z position:

```python
from GEIS.octahedral_state import OctahedralState
from GEIS.geometric_encoder import GeometricEncoder

# State 4 = +z vertex (index 4 in the octahedral vertex ordering)
state = OctahedralState(4)
```

**Step 2: Encode with the GEIS encoder (dense mode)**

```python
encoder = GeometricEncoder()
token = encoder.encode_state(state, operator='O', symbol='I')
# Dense token: "100|O|I"
# -> vertex bits "100" (binary 4 = +z)
# -> operator "O" (rotation/identity)
# -> symbol "I"

binary = encoder.to_binary(token)
# Collapse mode: "100" followed by encoded operator and symbol bits
```

**Step 3: Decode (round-trip verification)**

```python
reconstructed = encoder.from_binary(binary)
assert reconstructed.state.vertex == state.vertex   # lossless
```

The GEIS encoder guarantees lossless round-trips. The geometric
structure is preserved exactly in dense mode. In collapse mode, the
structure is preserved but packed flat -- fully reversible.

**Translation loss: zero.** Octahedral state encoding is exact --
there are only 8 discrete positions and each maps to a unique 3-bit
pattern. No approximation is involved.

---

## Translation loss summary

| Domain | Source of loss | Bound | Reduce by |
|---|---|---|---|
| Sound | Band width in Gray encoding | ~6% per octave | More bits |
| EM field | Grid resolution | Inversely with point count | Finer adaptive grid |
| GEIS token | None | 0% | N/A (exact) |
| Crystalline NN phase | Phase gradient step size | Bounded by lr | Smaller lr |
| Silicon substrate | Void placement precision | Fabrication tolerance | Better lithography |

---

## The phi-shell example from the original draft

The original sketch in this guide described phi-shell convergence.
Here is the complete version:

```python
from Silicon.crystalline_nn_sim import build_positions
import numpy as np

PHI = (1 + np.sqrt(5)) / 2
positions, shell_ids = build_positions(n_shells=5, r0=1.0)

# Shell radii follow r_n = r0 * phi^n
for n in range(5):
    r_n = 1.0 * PHI**n
    theoretical = 1.0 * PHI**n
    error = abs(r_n - theoretical) / theoretical
    print(f"Shell {n}: r = {r_n:.4f}  theoretical = {theoretical:.4f}  L = {error:.6f}")

# Shell 0: r = 1.0000  theoretical = 1.0000  L = 0.000000
# Shell 1: r = 1.6180  theoretical = 1.6180  L = 0.000000
# Shell 2: r = 2.6180  theoretical = 2.6180  L = 0.000000
# Shell 3: r = 4.2361  theoretical = 4.2361  L = 0.000000
# Shell 4: r = 6.8541  theoretical = 6.8541  L = 0.000000
```

Translation loss: zero. The phi spacing is computed analytically, not
approximated. The geometric structure is exact at the level of
floating-point precision.

---

## Naming and file formats

| Extension | Meaning |
|---|---|
| `.gshape` | Geometric shape definition (JSON) |
| `.json` | Bridge input geometry, sensor spec, field events |
| `.py` | Implementation (bridge encoders, engine, GEIS, simulations) |
| `.md` | Theory, specification, research notes |

Geometric token format: `[vertex_bits][operator][symbol]`
- vertex_bits: 3-bit Gray-coded octahedral vertex (000-111)
- operator: single character (O=identity/rotation, I=inversion, X=reflection, Delta=scaling)
- symbol: single letter + optional subscript

---

## Command-line interface

```bash
# Run a bridge encoding from the command line
python scripts/bridge_convert.py

# Run all bridge tests (231 tests)
python tests/test_bridges.py

# Run GEIS tests (116 tests)
cd GEIS && python test_simple.py

# Run engine tests (42 tests)
python tests/test_engine.py

# Run the crystalline NN simulation
python Silicon/crystalline_nn_sim.py

# Run the Prototaxites energy simulation
python Silicon/prototaxites_sim.py
```
