"""GIES codec: a true bijection over all 128 tokens. Stdlib only.

Supersedes ``geometric_encoder.py``. That file is left in place for provenance
and still passes its suite; the defects below are why it should not be used for
new work.

WHAT WAS WRONG, having traced the actual file rather than the spec
-----------------------------------------------------------------
1. ``':'`` and ``'/'`` both map to the bit ``'0'``, so ``'001:O'`` and
   ``'001/O'`` both encode to ``'001000'`` and both decode to ``'001/O'``.
   The colon operator is documented in GIES.md §4.2 and is silently lost. The
   file's own comment concedes it: "Reverse map uses '/' as canonical form for
   bit '0' (not ':')". That is a non-bijection by construction, not an
   oversight.

2. **The output is variable-length and not prefix-free.** ``'|'`` encodes to
   ``'1'`` and ``'||'`` to ``'11'``, so a single-token round-trip works only
   because ``decode_from_binary`` infers the operator width from the total
   string length. Concatenate two tokens and the stream is ambiguous:
   ``'0011100001100'`` parses as ``('001||O', '001|O')`` or as
   ``('001|X', '000||O')``. Any stream of GIES tokens is unparseable.

   This is the defect that matters, and it is not the one an inspection of
   §8.2 predicts -- ``'||'`` does *not* collapse onto ``'|'``, because both
   files special-case it before the single-character lookup. The collapse is in
   ``':'``, and the ambiguity is in the widths.

3. All three worked examples in GIES.md quote 5 bits -- ``'00110'``,
   ``'01010'``, ``'01110'`` -- where the code emits 6, and
   ``decode_from_binary`` rejects anything under 6 with "Binary string too
   short". Every worked example in the document crashes the document's own
   decoder.

THE FIX
-------
Fixed-width fields: ``vertex(3) + operator(2) + symbol(2) = 7 bits``. Fixed
width is prefix-free for free, so streams concatenate and parse. Operators are
matched longest-first, which is what a variable-width scheme would have needed
and did not do.

128 tokens, 128 distinct codes, verified exhaustively rather than on the single
example ``'011|O'`` that the original suite happened to check.
"""

from __future__ import annotations

from typing import Dict, Iterator, List

__all__ = [
    "OPS", "SYMS", "IOPS", "ISYMS", "TOKEN_BITS",
    "encode", "decode", "all_tokens", "encode_stream", "decode_stream",
    "main",
]

#: Operators from GIES.md §4.2. All four, at a fixed two bits.
OPS: Dict[str, str] = {"|": "00", "||": "01", "/": "10", ":": "11"}

#: Symbols. 'D' is the ASCII spelling of the Delta state; the Unicode form is
#: accepted on input and normalised, because a codec that depends on the source
#: file's encoding is not a codec.
SYMS: Dict[str, str] = {"O": "00", "I": "01", "X": "10", "D": "11"}

IOPS: Dict[str, str] = {v: k for k, v in OPS.items()}
ISYMS: Dict[str, str] = {v: k for k, v in SYMS.items()}

_SYM_ALIASES = {"Δ": "D", "δ": "D", "Δ": "D"}

TOKEN_BITS = 7          # 3 vertex + 2 operator + 2 symbol


def _normalise_symbol(sym: str) -> str:
    return _SYM_ALIASES.get(sym, sym)


def encode(token: str, width: int = 3) -> str:
    """``'001||O' -> '0010100'``.

    Operators are matched longest-first, so ``'||'`` is tried before ``'|'``.
    """
    if width < 1:
        raise ValueError("width must be at least 1")
    vertex = token[:width]
    if len(vertex) != width or any(c not in "01" for c in vertex):
        raise ValueError(f"bad vertex bits in {token!r}")
    rest = token[width:]
    if not rest:
        raise ValueError(f"no operator or symbol in {token!r}")
    for op in sorted(OPS, key=len, reverse=True):
        if rest.startswith(op):
            sym = _normalise_symbol(rest[len(op):])
            if sym not in SYMS:
                raise ValueError(f"unknown symbol {rest[len(op):]!r}")
            return vertex + OPS[op] + SYMS[sym]
    raise ValueError(f"unknown operator in {rest!r}")


def decode(bits: str, width: int = 3) -> str:
    """Inverse of ``encode``. Rejects wrong lengths rather than guessing."""
    expected = width + 4
    if len(bits) != expected:
        raise ValueError(f"need {expected} bits, got {len(bits)}")
    if any(c not in "01" for c in bits):
        raise ValueError("non-binary input")
    op = IOPS[bits[width:width + 2]]
    sym = ISYMS[bits[width + 2:]]
    return bits[:width] + op + sym


def all_tokens(width: int = 3) -> Iterator[str]:
    """Every legal token, in a stable order. 8 * 4 * 4 = 128 at width 3."""
    for v in range(1 << width):
        for op in OPS:
            for sym in SYMS:
                yield format(v, f"0{width}b") + op + sym


def encode_stream(tokens: List[str], width: int = 3) -> str:
    """Concatenate encoded tokens. Safe because the width is fixed."""
    return "".join(encode(t, width) for t in tokens)


def decode_stream(bits: str, width: int = 3) -> List[str]:
    """Split a stream back into tokens. Impossible with variable-width codes."""
    n = width + 4
    if len(bits) % n:
        raise ValueError(f"stream length {len(bits)} is not a multiple of {n}")
    return [decode(bits[i:i + n], width) for i in range(0, len(bits), n)]


def main() -> None:
    print("GIES CODEC\n" + "=" * 60)
    seen: Dict[str, str] = {}
    for tok in all_tokens():
        b = encode(tok)
        if b in seen:
            raise AssertionError(f"COLLISION: {seen[b]} and {tok} -> {b}")
        seen[b] = tok
        if decode(b) != tok:
            raise AssertionError(f"round trip: {tok} -> {b} -> {decode(b)}")
    print(f"  bijection over all {len(seen)} tokens: OK")

    print("\n  the four operators, all distinct:")
    for op in OPS:
        tok = "001" + op + "O"
        print(f"    {tok!r:10} -> {encode(tok)!r}")

    print("\n  streams parse, which the variable-width scheme could not:")
    toks = ["001||O", "001|O", "111:D"]
    s = encode_stream(toks)
    print(f"    {toks} -> {s!r} ({len(s)} bits) -> {decode_stream(s)}")

    print("\n  the ambiguity this removes, in the old encoding:")
    print("    '0011100001100' was both ('001||O','001|O') and "
          "('001|X','000||O')")


if __name__ == "__main__":
    main()
