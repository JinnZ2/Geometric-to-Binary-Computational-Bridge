"""
wav_reader.py  (fabrication/verify/)

Stdlib WAV reader. PCM 16-bit mono or stereo (auto-mixes to mono).
Returns: (samples: list[float] in [-1,1], sample_rate: int)

License: CC0. Stdlib only.
"""
import wave
import struct


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        n_ch   = w.getnchannels()
        sw     = w.getsampwidth()
        sr     = w.getframerate()
        n      = w.getnframes()
        raw    = w.readframes(n)

    if sw != 2:
        raise ValueError(f"Only 16-bit PCM supported (got {sw*8}-bit).")

    fmt   = "<" + "h" * (len(raw) // 2)
    ints  = struct.unpack(fmt, raw)

    if n_ch == 1:
        samples = [v / 32768.0 for v in ints]
    else:
        # de-interleave + average channels
        samples = [
            sum(ints[i:i+n_ch]) / (n_ch * 32768.0)
            for i in range(0, len(ints), n_ch)
        ]
    return samples, sr
