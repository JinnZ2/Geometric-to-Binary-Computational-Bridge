"""
loop.py  (fabrication/voice/)

Ties the five sub-modules into one runtime loop.

License: CC0. Stdlib only.
"""
from . import (constraint_gate as G,
               dispatcher       as D,
               coating_detector as C,
               optics           as O,
               io_layer         as IO)


def run_once(utterance, mode="text", tts_bin=None):
    gated      = G.gate(utterance)
    dispatched = D.dispatch(gated)
    coating    = C.detect()
    rendered   = O.render(dispatched, coating_report=coating,
                          form="short")
    if mode in ("tts", "stt+tts"):
        IO.speak(rendered, tts_bin=tts_bin)
    else:
        print(rendered)
    return {
        "gated":      gated,
        "dispatched": dispatched,
        "coating":    coating,
        "rendered":   rendered,
    }


def run_forever():
    mode, (stt_bin, tts_bin) = IO.detect_mode()
    IO.speak(f"voice wrapper online -- mode={mode}", tts_bin)
    while True:
        utt = IO.listen(stt_bin)
        if not utt or utt.strip().lower() in ("quit", "exit", "stop"):
            IO.speak("voice wrapper stopping.", tts_bin)
            return
        run_once(utt, mode=mode, tts_bin=tts_bin)
