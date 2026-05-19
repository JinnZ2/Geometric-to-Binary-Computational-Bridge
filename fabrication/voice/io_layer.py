"""
io_layer.py  (fabrication/voice/)

Auto-detected voice I/O. Three modes:

  "text"      stdin / stdout only
  "tts"       stdin in, system TTS out
  "stt+tts"   full voice loop using locally-available CLIs

Probes for STT candidates: whisper, vosk-cli
Probes for TTS candidates: say (macOS), espeak / espeak-ng (Linux),
                           termux-tts-speak (Android Termux)

Falls back to text-only if no binary is found. Pure subprocess --
no pip packages required.

License: CC0. Stdlib only.
"""
import shutil
import subprocess


def _which(*candidates):
    for c in candidates:
        if shutil.which(c):
            return c
    return None


def detect_mode():
    stt = _which("whisper", "vosk-cli")
    tts = _which("say", "espeak", "espeak-ng", "termux-tts-speak")
    if stt and tts:
        return "stt+tts", (stt, tts)
    if tts:
        return "tts", (None, tts)
    return "text", (None, None)


def speak(text, tts_bin=None):
    if not tts_bin:
        print(text)
        return
    try:
        subprocess.run([tts_bin, text], check=False, timeout=30)
    except Exception:
        print(text)


def listen(stt_bin=None, prompt=">> "):
    if not stt_bin:
        try:
            return input(prompt)
        except EOFError:
            return ""
    # Audio capture is hardware-specific; for now, fall back to
    # stdin with a note. A proper STT integration would invoke
    # arecord / sox / similar to capture, then pipe to the binary.
    return input(prompt + "(STT not auto-piped; type for now) ")
