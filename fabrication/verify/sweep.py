"""
sweep.py  (fabrication/verify/)

Exponential (logarithmic) sine sweep generator + WAV writer.

Exponential (a.k.a. Farina sweep) is the right choice:
  - equal energy per octave -> matches log-frequency hearing
  - compresses harmonic distortion into a separable tail
  - impulse response recoverable by deconvolution

x(t) = sin( (2π·f1·T / ln(f2/f1)) · ( e^(t/T · ln(f2/f1)) − 1 ) )

Reference: Farina, AES 2000 -- exponential sweep is the
standard tool for room/loudspeaker measurement.

License: CC0. Stdlib only.
"""
import math
import wave
import struct


def exp_sweep(f1=50.0, f2=2000.0, duration=4.0, sr=44100, amp=0.5):
    """Return (samples_list, sample_rate). Samples in [-amp, amp]."""
    n  = int(sr * duration)
    T  = duration
    K  = 2 * math.pi * f1 * T / math.log(f2 / f1)
    L  = T / math.log(f2 / f1)
    out = []
    for i in range(n):
        t = i / sr
        phase = K * (math.exp(t / L) - 1.0)
        out.append(amp * math.sin(phase))
    # 50 ms cosine fade in/out -- protects the speaker
    fade = int(0.050 * sr)
    for i in range(fade):
        w = 0.5 * (1 - math.cos(math.pi * i / fade))
        out[i]      *= w
        out[-1 - i] *= w
    return out, sr


def write_wav(path, samples, sr):
    pcm = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767))
        for s in samples
    )
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)


def make_sweep_file(path="sweep.wav",
                    f1=50.0, f2=2000.0, duration=4.0,
                    sr=44100, amp=0.5):
    samples, sr = exp_sweep(f1, f2, duration, sr, amp)
    write_wav(path, samples, sr)
    return {
        "path": path, "f1": f1, "f2": f2,
        "duration": duration, "sample_rate": sr, "amp": amp,
    }
