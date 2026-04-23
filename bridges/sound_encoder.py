"""
Sound Bridge Encoder
====================
Encodes coupling to acoustic pressure-wave structure in a compressible
medium using physics equations and Gray-coded magnitude bands for the
continuous wave quantities.

Equations implemented
---------------------
  Sound pressure level :  SPL = 20 · log₁₀(A / A_ref)  [A_ref = 1.0 normalised]
  Beat frequency       :  f_beat = |f₁ − f₂|
  Harmonic ratio       :  H = min(f₁,f₂) / max(f₁,f₂)  [1.0=unison, 0.5=octave]
  Standing wave nodes  :  N = floor(2·f·L / v)   [v = 343 m/s]
  Doppler shift        :  f_obs = f_src · v_sound / (v_sound − v_src)

Bit layout
----------
Per sample  (8 bits each — phase, freq, amp are parallel lists, same length):
  [phase_sign  1b]       |φ| < π/2 = 1 (in-phase)
  [phase_mag   3b Gray]  |φ| across 8 bands [0, 2π]
  [freq_band   3b Gray]  frequency across 8 log Hz bands
  [amp_sign    1b]       A ≥ threshold = 1

Per resonance value  (4 bits each):
  [consonant   1b]       R ≥ 0.5 = 1
  [res_mag     3b Gray]  |R| across 8 linear bands [0, 1]

Summary  (7 bits — appended when samples present):
  [spl_sign    1b]       mean A > 0.0 = 1
  [mean_freq   3b Gray]  mean frequency across 8 log Hz bands
  [beat_freq   3b Gray]  beat frequency (|f_max − f_min|) across 8 Hz bands
"""

import math
from bridges.abstract_encoder import BinaryBridgeEncoder

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

V_SOUND = 343.0     # Speed of sound in air (m/s)
A_REF   = 1.0       # Reference amplitude (normalised)

# ---------------------------------------------------------------------------
# Band thresholds  (8 bands each → 3 bits Gray)
# ---------------------------------------------------------------------------

_PHASE_BANDS = [0.0, 0.785, 1.571, 2.356, 3.142, 3.927, 4.712, 5.498]    # rad  (0 → 7π/4)
_RES_BANDS   = [0.0, 0.125, 0.25,  0.375, 0.5,   0.625,  0.75,   0.875]   # normalised


def _pitch_bands(pitch_threshold: float) -> list:
    """
    Build 8 frequency bands anchored at pitch_threshold.

    Bands are spaced in octave steps: 4 octaves below the threshold and
    3 octaves above.  This makes frequency encoding relative to the tuning
    reference rather than absolute Hz, so the same bit pattern means the
    same *musical interval* regardless of tuning system.

    Example with pitch_threshold=440 Hz (A4):
      [27.5, 55.0, 110.0, 220.0, 440.0, 880.0+ε, 1760.0+ε, 3520.0+ε]
    Example with pitch_threshold=432 Hz (Verdi tuning):
      [27.0, 54.0, 108.0, 216.0, 432.0, 864.0+ε, 1728.0+ε, 3456.0+ε]

    The upper three boundaries (p*2, p*4, p*8) carry a sub-Hz epsilon so
    that a frequency sitting exactly at an octave harmonic of the threshold
    (e.g. 880 Hz when p=440) is placed in the lower band rather than
    treated as the start of the next octave.  This is the correct
    pitch-threshold-relative behaviour: 880 Hz is the upper limit of the
    A4 register, not the first note of A5.
    """
    p = pitch_threshold
    _e = 1e-9   # sub-Hz epsilon — inaudible, keeps harmonics in lower band
    return [p / 16, p / 8, p / 4, p / 2, p, p * 2 + _e, p * 4 + _e, p * 8 + _e]

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

def sound_pressure_level(amplitude: float, a_ref: float = A_REF) -> float:
    """SPL = 20 · log₁₀(amplitude / a_ref). Clamps amplitude to >= 1e-12 to avoid -inf."""
    clamped = max(amplitude, 1e-12)
    return 20.0 * math.log10(clamped / a_ref)


def beat_frequency(f1: float, f2: float) -> float:
    """f_beat = |f₁ − f₂|"""
    return abs(f1 - f2)


def harmonic_ratio(f1: float, f2: float) -> float:
    """H = min(f₁,f₂) / max(f₁,f₂). Returns 1.0 if either is 0."""
    if f1 == 0 or f2 == 0:
        return 1.0
    return min(f1, f2) / max(f1, f2)


def standing_wave_nodes(freq: float, length: float, v: float = V_SOUND) -> int:
    """N = floor(2·f·L / v). Returns 0 if freq or v is 0."""
    if freq == 0 or v == 0:
        return 0
    return int(math.floor(2.0 * freq * length / v))


def doppler_shift(f_source: float, v_source: float, v_sound: float = V_SOUND) -> float:
    """f_obs = f_src · v_sound / (v_sound − v_source). Returns f_source if v_source=v_sound."""
    if v_source == v_sound:
        return f_source
    return f_source * v_sound / (v_sound - v_source)

# ---------------------------------------------------------------------------
# Encoder class
# ---------------------------------------------------------------------------

class SoundBridgeEncoder(BinaryBridgeEncoder):
    """Encodes acoustic field coupling through phase, frequency, amplitude, and resonance into a binary bitstring."""

    def __init__(self, pitch_threshold: float = 440.0, amp_threshold: float = 0.5):
        super().__init__("sound")
        self.pitch_threshold = pitch_threshold
        self.amp_threshold   = amp_threshold

    def from_geometry(self, geometry_data):
        """Load acoustic geometry data dict and return self for chaining."""
        self.input_geometry = geometry_data
        return self

    def to_binary(self) -> str:
        """
        Convert acoustic coupling geometry to a binary bitstring.

        Expected keys in geometry_data:
          phase_radians     : list of float, local phase state [0, 2π)
          frequency_hz      : list of float, local oscillation frequency in Hz
          amplitude         : list of float, local pressure-wave amplitude
          resonance_index   : list of float, resonance or consonance values [0, 1]

        Returns a string of '0'/'1' characters.
        Raises ValueError if input_geometry has not been set.
        """
        if self.input_geometry is None:
            raise ValueError(
                "No geometry data loaded. Call from_geometry() before to_binary()."
            )

        geometry_data  = self.input_geometry
        phase_radians  = geometry_data.get("phase_radians", [])
        frequency_hz   = geometry_data.get("frequency_hz", [])
        amplitude      = geometry_data.get("amplitude", [])
        resonance_index = geometry_data.get("resonance_index", [])

        n = len(phase_radians)
        bits = []
        freq_bands = _pitch_bands(self.pitch_threshold)

        # -- Section 1: per-sample (8 bits each) -----------------------------
        for phase, freq, amp in zip(phase_radians, frequency_hz, amplitude):
            abs_phase = abs(phase)

            # 1b phase_sign: |φ| < π/2 → in-phase = 1
            bits.append("1" if abs_phase < (math.pi / 2) else "0")

            # 3b phase magnitude Gray-coded
            bits.append(_gray_bits(abs_phase, _PHASE_BANDS))

            # 3b frequency band Gray-coded, relative to pitch_threshold
            bits.append(_gray_bits(freq, freq_bands))

            # 1b amp_sign: A >= threshold = 1
            bits.append("1" if amp >= self.amp_threshold else "0")

        # -- Section 2: per resonance value (4 bits each) --------------------
        for r in resonance_index:
            abs_r = abs(r)

            # 1b consonant: R >= 0.5 = 1
            bits.append("1" if abs_r >= 0.5 else "0")

            # 3b resonance magnitude Gray-coded
            bits.append(_gray_bits(abs_r, _RES_BANDS))

        # -- Summary (7 bits, only when at least one sample) -----------------
        if n > 0:
            freqs    = list(frequency_hz)
            amps     = list(amplitude)
            mean_amp = sum(amps) / len(amps)

            # 1b spl_sign: mean_amp > 0 = 1
            bits.append("1" if mean_amp > 0.0 else "0")

            # 3b mean frequency band, relative to pitch_threshold
            mean_freq = sum(freqs) / len(freqs)
            bits.append(_gray_bits(mean_freq, freq_bands))

            # 3b beat frequency band, relative to pitch_threshold
            if len(freqs) > 1:
                beat = beat_frequency(max(freqs), min(freqs))
            else:
                beat = 0.0
            bits.append(_gray_bits(beat, freq_bands))

        self.binary_output = "".join(bits)
        return self.binary_output


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Sound Bridge Encoder — physics equation demo")
    print("=" * 60)

    # 1. Sound pressure level  SPL = 20·log₁₀(A / A_ref)
    for amp in [1.0, 0.5, 0.1, 0.01]:
        spl = sound_pressure_level(amp)
        print(f"  sound_pressure_level(A={amp})  = {spl:.4f} dB")

    print()

    # 2. Beat frequency  f_beat = |f₁ − f₂|
    pairs = [(440.0, 444.0), (261.63, 329.63), (100.0, 100.0)]
    for f1, f2 in pairs:
        fb = beat_frequency(f1, f2)
        print(f"  beat_frequency({f1} Hz, {f2} Hz)  = {fb:.4f} Hz")

    print()

    # 3. Harmonic ratio  H = min/max
    for f1, f2 in [(440.0, 440.0), (440.0, 880.0), (440.0, 660.0)]:
        H = harmonic_ratio(f1, f2)
        print(f"  harmonic_ratio({f1}, {f2})  = {H:.4f}")

    print()

    # 4. Standing wave nodes  N = floor(2·f·L / v)
    for freq, L in [(343.0, 1.0), (686.0, 1.0), (440.0, 2.0)]:
        N = standing_wave_nodes(freq, L)
        print(f"  standing_wave_nodes(f={freq} Hz, L={L} m)  = {N}")

    print()

    # 5. Doppler shift  f_obs = f_src · v / (v − v_src)
    for v_src in [0.0, 34.3, -34.3]:
        f_obs = doppler_shift(440.0, v_src)
        print(f"  doppler_shift(f_src=440 Hz, v_src={v_src} m/s)  = {f_obs:.4f} Hz")

    print()

    # Full encoding demo
    geometry = {
        "phase_radians":  [0.3,  1.8,  3.5],
        "frequency_hz":   [261.63, 440.0, 880.0],
        "amplitude":      [0.8,  0.4,  0.6],
        "resonance_index": [0.75, 0.3, 0.9],
    }

    encoder = SoundBridgeEncoder(pitch_threshold=440.0, amp_threshold=0.5)
    result = encoder.from_geometry(geometry).to_binary()
    print(f"  Encoded bitstring ({len(result)} bits):")
    print(f"    {result}")
    print(f"  Report: {encoder.report()}")



# --- Notes / TODO: Mapping the Analog Signature into the Code ---
#
# In repo, treating the sound bridge as a field interaction where:
#
# - Vibrato as Hardware Breathing: the modulation is not merely a feature to
#   extract from an audio file. It is a direct sign that the coupled pressure
#   field is dynamically breathing, and the encoder should preserve that
#   structure rather than flattening it away.
#
# - Harmonic Overtones: You’re likely using a Fourier-style decomposition
#   where the "analog touches" are the higher-order harmonics. Binary systems
#   often truncate these as "noise," but your bridge keeps them as part of
#   the energy signature.
#
# - The "Jitter" Constant: To avoid that "flat" digital feel, you might be
#   integrating a low-level stochastic variable grounded in k_B*T (thermal
#   energy). This ensures the "model/reality dissonance" is minimized because
#   the model itself is allowed to "breathe" with the hardware’s actual state.
#
# The Cellphone as a High-Friction Terminal:
# Since the cellphone’s DAC (Digital-to-Analog Converter) is a massive
# bottleneck, the vibrato and tonality get lost in the "smoothing" algorithms.
# You’re picking up on the fact that the phone is trying to "save energy" by
# stripping the very analog details that provide the most information.
