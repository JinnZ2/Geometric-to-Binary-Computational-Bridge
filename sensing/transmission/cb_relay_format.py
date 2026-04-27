"""
cb_relay_format — frame a Primitive for spoken relay over CB.

CB radio is voice-only and has no data sidecar. This module turns a
Primitive into a short (≤ 50 word) script that an operator can read
out over the air. The receiving operator transcribes it back to
text and feeds it into the network manually.

Format (callsign, time-of-day, concept, key values, confidence, end)::

    "KV BREAK FIVE OVER. SOIL REGIME. SURFACE ELEVEN POINT TWO C.
     MOISTURE THIRTY PERCENT. CONFIDENCE EIGHT FIVE. KV OUT."

Numbers are spelled out in NATO-phonetic-friendly form so a tired
operator on a noisy channel does not have to guess decimals or signs.
"""

from __future__ import annotations

import math
from typing import Iterable, List

from sensing.processing.primitives_encoder import Primitive

# Map each digit 0-9 to its NATO-phonetic-style spoken form. Decimal
# point becomes "POINT". Negative numbers prefix with "NEGATIVE".
_DIGIT_WORDS = {
    "0": "ZERO", "1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR",
    "5": "FIVE", "6": "SIX", "7": "SEVEN", "8": "EIGHT", "9": "NINE",
    ".": "POINT", "-": "NEGATIVE",
}


def _say_number(value: float, decimals: int = 1) -> str:
    """Render a float as a spoken-form string."""
    if math.isnan(value):
        return "UNKNOWN"
    fmt = f"{{:.{decimals}f}}"
    text = fmt.format(value)
    return " ".join(_DIGIT_WORDS.get(ch, ch.upper()) for ch in text)


def _say_word(text: str) -> str:
    """Turn a snake_case_or_lower identifier into a spoken phrase."""
    return text.replace("_", " ").upper()


def _confidence_phrase(c: float) -> str:
    pct = round(c * 100)
    return f"CONFIDENCE {_say_number(pct, 0)}"


def _values_phrase(primitive: Primitive, max_values: int = 3) -> str:
    """
    Pick up to ``max_values`` numeric values and render them as
    spoken phrases.

    Source order:
      1. ``primitive.readings`` (full SensorReading list — only set on
         in-memory Primitives that have not yet been serialised).
      2. ``primitive.form`` (JSON snapshot — survives disk round-trip).
    """
    parts: List[str] = []

    # 1. In-memory readings
    for reading in primitive.readings:
        for chan, val in reading.values.items():
            if len(parts) < max_values:
                parts.append(
                    f"{_say_word(chan)} {_say_number(float(val), 1)}"
                )
        if len(parts) >= max_values:
            break

    # 2. Form-JSON fallback (post-serialisation)
    if not parts and primitive.form:
        import json
        try:
            form = json.loads(primitive.form)
        except (json.JSONDecodeError, ValueError):
            form = {}
        if isinstance(form, dict):
            for sensor_id, channels in form.items():
                if not isinstance(channels, dict):
                    continue
                for chan, val in channels.items():
                    if len(parts) < max_values and isinstance(
                        val, (int, float),
                    ):
                        parts.append(
                            f"{_say_word(chan)} {_say_number(float(val), 1)}"
                        )
                if len(parts) >= max_values:
                    break

    return " ; ".join(parts) if parts else "NO VALUES"


def format_for_cb_relay(
    primitive: Primitive,
    callsign: str = "NOCALL",
    *,
    break_count: int = 5,
) -> str:
    """
    Render a Primitive as a one-shot CB voice script.

    Parameters
    ----------
    callsign
        Spoken callsign for the operator. Repeated at start and end.
    break_count
        Channel-19 etiquette: how many "BREAK" calls before the
        message body. Five is conservative; tune to local protocol.
    """
    breaks = " ".join(["BREAK"] * max(1, break_count))
    return (
        f"{_say_word(callsign)} {breaks} OVER. "
        f"{_say_word(primitive.concept_id)}. "
        f"{_values_phrase(primitive)}. "
        f"{_confidence_phrase(primitive.epi_confidence)}. "
        f"{_say_word(callsign)} OUT."
    )


__all__ = ["format_for_cb_relay"]
