import numpy as np
from .common import gray_code, bits_from_int

N_BINS = 16  # frequency bins for pitch mapping
AMP_LEVELS = 16  # quantization for amplitude

def sound_features(samples: np.ndarray, sample_rate: int) -> dict:
    """
    Extract features from an audio waveform.
    - samples: 1D numpy array of audio values
    - sample_rate: sampling rate in Hz
    """
    # FFT for frequency domain
    freqs = np.fft.rfftfreq(len(samples), d=1.0/sample_rate)
    spectrum = np.abs(np.fft.rfft(samples))

    # normalize
    spectrum = spectrum / (np.sum(spectrum) + 1e-12)

    # bin frequencies (e.g., log-scale bins)
    bins = np.logspace(np.log10(20), np.log10(sample_rate/2), N_BINS+1)
    band_energy = []
    for i in range(N_BINS):
        mask = (freqs >= bins[i]) & (freqs < bins[i+1])
        band_energy.append(float(np.sum(spectrum[mask])))

    # phase: compare sign of imaginary parts
    phase_info = np.angle(np.fft.rfft(samples))
    mean_phase = float(np.mean(np.sign(phase_info)))

    return {
        "band_energy": band_energy,
        "phase": mean_phase,
        "rms_amplitude": float(np.sqrt(np.mean(samples**2)))
    }

def encode_sound_gray(features: dict, target_bits: int = 256) -> str:
    """
    Encode sound features → binary bitstring.
    """
    # normalize band energy
    vals = np.array(features["band_energy"])
    vals = vals / (np.sum(vals) + 1e-12)

    # Gray code per bin
    bins = (vals * (AMP_LEVELS-1)).astype(int)
    band_bits = ''.join(bits_from_int(gray_code(int(b)), 4) for b in bins)

    # amplitude quantization
    amp_q = int(np.clip(features["rms_amplitude"]*15, 0, 15))
    amp_bits = bits_from_int(gray_code(amp_q), 4)

    # phase: sign → 0/1
    phase_bit = '1' if features["phase"] >= 0 else '0'

    payload = band_bits + amp_bits + phase_bit
    return (payload * ((target_bits // len(payload)) + 1))[:target_bits]
