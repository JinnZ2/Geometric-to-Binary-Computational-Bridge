# SOUND / SONIC Modality

The sound bridge converts waveforms into binary encodings using field laws of vibration, phase, and resonance.

---

## Capture

- Input: audio waveform (samples, sample_rate).
- Typical: 1D array of values, e.g. 44.1 kHz PCM or simulated waveforms.
- Minimum window: enough samples for FFT to resolve <20 Hz – 20 kHz.

---

## Normalize

- Convert to frequency domain via FFT.
- Scale band energies so total = 1.0.
- Extract root-mean-square (RMS) amplitude.

---

## Features

1. **Frequency Bands**  
   - 16 logarithmic bins (20 Hz → Nyquist).  
   - Energy distribution per band.  

2. **Phase**  
   - Mean sign of FFT phase angles.  
   - Binary: in-phase vs out-of-phase.  

3. **Amplitude**  
   - RMS quantized into 16 levels.  

---

## Quantize

- Gray-code each band energy (0–15).  
- 4 bits × 16 bands = 64 bits.  
- RMS amplitude = 4 bits.  
- Phase = 1 bit.  

---

## Encode

- Concatenate → repeat until 256-bit payload.  
- Encoding profile: `enc.sound.gray.256.v1`.  
- Output: stable bitstring suitable for comparison.  

---

## Compare

- Hamming distance = similarity measure.  
- Related to psychoacoustic Δ-perception (approximate).  
- Harmonic consonance → low bit difference.  
- Dissonance or noise → higher bit difference.  
