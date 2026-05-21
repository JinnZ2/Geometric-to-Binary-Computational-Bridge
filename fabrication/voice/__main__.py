"""
__main__.py  (fabrication/voice/)

  python -m fabrication.voice                  -> interactive loop
  python -m fabrication.voice "list acoustic"  -> one-shot

License: CC0. Stdlib only.
"""
import sys

from .loop import run_once, run_forever
from .io_layer import detect_mode


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode, (stt, tts) = detect_mode()
        utt = " ".join(sys.argv[1:])
        run_once(utt, mode=mode, tts_bin=tts)
    else:
        run_forever()
