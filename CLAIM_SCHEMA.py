"""
CLAIM_SCHEMA.py — canonical compressed form for AI readers
==========================================================

Drop into every repo root. AI readers parse `.claims` or `.claims.bin`
through this module. CC0. Token-minimal. Binary-serializable.
Physics-anchored.

Design rule: every claim is a rate of change ``dX/dt`` under stated
bounds. Never collapse to noun-identity. Cycle class is one of the
seven values in :data:`CYCLE_ENUM`.

Layers
------
1. ``CLAIM_SCHEMA`` — JSON-shaped dict (human + AI readable).
2. ``.claims`` line format — one claim per line, pipe-delimited,
   fields exactly as listed in the schema in the same order.
3. ``encode_claim`` / ``decode_claim`` — binary codec, 41 bytes per
   claim, lookups via the repo-level ``CLAIM_TABLE.json``.
4. ``CLAIM_TABLE.json`` — shared dedup table (rates, bounds, cond,
   rel, fail, meas as parallel arrays). One file per repo.

Protocol (token cost): prose ≈ 600 tok/claim, line format ≈ 80
tok/claim, binary post-load ≈ 5 tok/claim. The whole repo's claims
fit in ~10 KB.
"""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ============================================================
# LAYER 1 — JSON schema (canonical form)
# ============================================================

CLAIM_SCHEMA = {
    "id":     "<short_hash>",          # 8-char id, e.g. "mulch_h2o"
    "rate":   "dX/dt = <expr>",        # the differential equation
    "bounds": "<spatial>,<temporal>,<scale>",  # comma-joined 3-tuple
    "cond":   ["<bool_expr>", "..."],  # list of constraints
    "rel":    ["<id>", "..."],         # coupled claim ids
    "fail":   ["<bool_expr>", "..."],  # invalid_if conditions
    "meas":   ["<observable>", "..."], # how dX/dt is measured
    "cyc":    "<int>",                 # cycle class enum
}

CYCLE_ENUM: Dict[int, str] = {
    0: "instantaneous",
    1: "diurnal",
    2: "seasonal",
    3: "annual",
    4: "generational",
    5: "century",
    6: "geologic",
}

CYCLE_NAME_TO_INT: Dict[str, int] = {v: k for k, v in CYCLE_ENUM.items()}


# ============================================================
# LAYER 2 — line format codec (.claims)
# ============================================================
#
# id|rate|bounds|cond|rel|fail|meas|cyc
#
# Multi-valued fields (cond, rel, fail, meas) use comma to separate
# entries within the field. Empty fields are written as the empty
# string. Newlines are forbidden inside claims.

LINE_FIELDS: Tuple[str, ...] = (
    "id", "rate", "bounds", "cond", "rel", "fail", "meas", "cyc",
)

_MULTI_FIELDS = {"cond", "rel", "fail", "meas"}


def claim_to_line(claim: Dict[str, Any]) -> str:
    """
    Serialise a claim dict into one ``.claims`` line.

    Rejects values containing ``|``, ``\\n``, or ``,`` (in
    multi-valued fields) since those collide with the line and
    sub-field separators. Use ``@`` or ``_`` in physics expressions
    instead of ``|``.
    """
    parts: List[str] = []
    for f in LINE_FIELDS:
        v = claim.get(f, "")
        if f in _MULTI_FIELDS:
            for item in v:
                if "|" in item or "\n" in item or "," in item:
                    raise ValueError(
                        f"claim {claim.get('id')!r} field {f!r} item "
                        f"{item!r} contains a forbidden separator "
                        f"('|', ',', or newline)"
                    )
            parts.append(",".join(v) if v else "")
        elif f == "cyc":
            parts.append(str(int(v)))
        else:
            text = str(v)
            if "|" in text or "\n" in text:
                raise ValueError(
                    f"claim {claim.get('id')!r} field {f!r} value "
                    f"{text!r} contains a forbidden separator "
                    f"('|' or newline)"
                )
            parts.append(text)
    return "|".join(parts)


def line_to_claim(line: str) -> Dict[str, Any]:
    """Inverse of :func:`claim_to_line`."""
    fields = line.rstrip("\n").split("|")
    if len(fields) != len(LINE_FIELDS):
        raise ValueError(
            f"expected {len(LINE_FIELDS)} pipe-delimited fields, "
            f"got {len(fields)}: {line!r}"
        )
    out: Dict[str, Any] = {}
    for name, raw in zip(LINE_FIELDS, fields):
        if name in _MULTI_FIELDS:
            out[name] = [s for s in raw.split(",") if s]
        elif name == "cyc":
            out[name] = int(raw)
        else:
            out[name] = raw
    return out


# ============================================================
# LAYER 3 — binary codec (.claims.bin)
# ============================================================
#
# Layout (41 bytes per claim, big-endian):
#   [4B  id_hash]      crc32 of the id string
#   [2B  rate_idx]     offset into CLAIM_TABLE["rates"]
#   [2B  bounds_idx]   offset into CLAIM_TABLE["bounds"]
#   [8B  cond_mask]    bitset over CLAIM_TABLE["cond"]   (≤ 64 entries)
#   [8B  rel_mask]     bitset over CLAIM_TABLE["rel"]    (≤ 64 entries)
#   [8B  fail_mask]    bitset over CLAIM_TABLE["fail"]   (≤ 64 entries)
#   [8B  meas_mask]    bitset over CLAIM_TABLE["meas"]   (≤ 64 entries)
#   [1B  cyc]          cycle enum int (0–6)
#
# The original spec reserved 2-byte (16-entry) masks; this
# implementation uses 8-byte (64-entry) masks so a single repo's
# claim vocabulary can grow past the 16-entry shelf without
# changing the wire format. ``MASK_BITS`` documents the cap; bump
# it (and the struct format) if 64 ever becomes tight.
#
# A ``CLAIM_TABLE`` dict carries the parallel arrays so the binary
# blob stays index-only.

MASK_BITS = 64
_BIN_FORMAT = ">IHHQQQQB"
BIN_CLAIM_BYTES = struct.calcsize(_BIN_FORMAT)  # = 41

# Sentinel: "no entry" for rate / bounds (which are single-valued).
NO_INDEX = 0xFFFF


def _id_hash(claim_id: str) -> int:
    return zlib.crc32(claim_id.encode("utf-8")) & 0xFFFFFFFF


def _index(table: Dict[str, List[str]], field: str, value: str) -> int:
    if not value:
        return NO_INDEX
    arr = table[field]
    try:
        return arr.index(value)
    except ValueError as exc:
        raise KeyError(
            f"value {value!r} not found in CLAIM_TABLE[{field!r}]"
        ) from exc


def _mask(table: Dict[str, List[str]], field: str, values: List[str]) -> int:
    arr = table[field]
    mask = 0
    for v in values:
        try:
            i = arr.index(v)
        except ValueError as exc:
            raise KeyError(
                f"value {v!r} not found in CLAIM_TABLE[{field!r}]"
            ) from exc
        if i >= MASK_BITS:
            raise ValueError(
                f"CLAIM_TABLE[{field!r}] entry {v!r} at index {i} "
                f"exceeds the {MASK_BITS}-bit mask cap. Consolidate "
                f"the vocabulary or expand the codec."
            )
        mask |= (1 << i)
    return mask


def _unmask(m: int, table_field: List[str]) -> List[str]:
    return [
        table_field[i] for i in range(MASK_BITS)
        if (m & (1 << i)) and i < len(table_field)
    ]


def encode_claim(claim: Dict[str, Any], table: Dict[str, List[str]]) -> bytes:
    """Pack a claim dict into 17 bytes using ``table`` lookups."""
    return struct.pack(
        _BIN_FORMAT,
        _id_hash(claim["id"]),
        _index(table, "rates", claim.get("rate", "")),
        _index(table, "bounds", claim.get("bounds", "")),
        _mask(table, "cond", claim.get("cond", [])),
        _mask(table, "rel",  claim.get("rel",  [])),
        _mask(table, "fail", claim.get("fail", [])),
        _mask(table, "meas", claim.get("meas", [])),
        int(claim["cyc"]),
    )


def decode_claim(
    blob: bytes,
    table: Dict[str, List[str]],
    id_lookup: Dict[int, str] | None = None,
) -> Dict[str, Any]:
    """
    Reverse of :func:`encode_claim`. The id is stored as a CRC32
    hash; pass ``id_lookup = {hash: id}`` to recover the original
    id string. Without it the ``id`` field comes back as ``"#<hex>"``.
    """
    fields = struct.unpack(_BIN_FORMAT, blob)
    h, rate_i, bounds_i, cond_m, rel_m, fail_m, meas_m, cyc = fields
    return {
        "id":     (id_lookup.get(h) if id_lookup else f"#{h:08x}"),
        "rate":   table["rates"][rate_i] if rate_i != NO_INDEX else "",
        "bounds": table["bounds"][bounds_i] if bounds_i != NO_INDEX else "",
        "cond":   _unmask(cond_m, table["cond"]),
        "rel":    _unmask(rel_m,  table["rel"]),
        "fail":   _unmask(fail_m, table["fail"]),
        "meas":   _unmask(meas_m, table["meas"]),
        "cyc":    int(cyc),
    }


# ============================================================
# LAYER 4 — repo-level CLAIM_TABLE helpers
# ============================================================

TABLE_FIELDS: Tuple[str, ...] = ("rates", "bounds", "cond", "rel", "fail", "meas")


def build_table(claims: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Build a deduplicated lookup table from a list of claim dicts.

    Single-valued fields (rate, bounds) emit one entry per claim.
    Multi-valued fields (cond, rel, fail, meas) flatten across all
    claims. The order within each list is the order of first
    occurrence in ``claims``, which means the binary indices are
    stable as long as ``claims`` is iterated deterministically.
    """
    table: Dict[str, List[str]] = {f: [] for f in TABLE_FIELDS}
    seen: Dict[str, set] = {f: set() for f in TABLE_FIELDS}

    def _push(field: str, value: str) -> None:
        if value and value not in seen[field]:
            table[field].append(value)
            seen[field].add(value)

    for c in claims:
        _push("rates",  c.get("rate", ""))
        _push("bounds", c.get("bounds", ""))
        for v in c.get("cond", []):
            _push("cond", v)
        for v in c.get("rel", []):
            _push("rel", v)
        for v in c.get("fail", []):
            _push("fail", v)
        for v in c.get("meas", []):
            _push("meas", v)
    return table


def write_table(path: str | Path, table: Dict[str, List[str]]) -> None:
    Path(path).write_text(
        json.dumps(table, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_table(path: str | Path) -> Dict[str, List[str]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_claims(path: str | Path, claims: List[Dict[str, Any]]) -> None:
    """Write the human-readable line file."""
    lines = [claim_to_line(c) for c in claims]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_claims(path: str | Path) -> List[Dict[str, Any]]:
    text = Path(path).read_text(encoding="utf-8")
    return [line_to_claim(line) for line in text.splitlines() if line.strip()]


def write_claims_binary(
    path: str | Path,
    claims: List[Dict[str, Any]],
    table: Dict[str, List[str]],
) -> None:
    """Write the packed binary file (one 17-byte record per claim)."""
    blob = b"".join(encode_claim(c, table) for c in claims)
    Path(path).write_bytes(blob)


def read_claims_binary(
    path: str | Path,
    table: Dict[str, List[str]],
    id_lookup: Dict[int, str] | None = None,
) -> List[Dict[str, Any]]:
    blob = Path(path).read_bytes()
    if len(blob) % BIN_CLAIM_BYTES != 0:
        raise ValueError(
            f"binary claim file length {len(blob)} is not a multiple "
            f"of {BIN_CLAIM_BYTES}"
        )
    records: List[Dict[str, Any]] = []
    for i in range(0, len(blob), BIN_CLAIM_BYTES):
        records.append(
            decode_claim(blob[i:i + BIN_CLAIM_BYTES], table, id_lookup)
        )
    return records


def id_lookup_from_claims(claims: List[Dict[str, Any]]) -> Dict[int, str]:
    """Build the ``{crc32_hash: id_string}`` map for binary decoding."""
    out: Dict[int, str] = {}
    for c in claims:
        out[_id_hash(c["id"])] = c["id"]
    return out


# ============================================================
# AI READER PROTOCOL
# ============================================================

PROTOCOL = """
1. Load CLAIM_TABLE.json (one-time cost, ~2-5KB)
2. Read .claims (line-per-claim, pipe-delimited)
   OR load .claims.bin (binary, 41B/claim) with the table.
3. Each claim deserialises into the CLAIM_SCHEMA dict.
4. Operate on dX/dt + bounds + conditions.
5. Never collapse to noun-identity. No exceptions.

Token cost per claim:
  prose         : ~600 tokens
  DIFFERENTIAL  : ~300 tokens
  line format   : ~80  tokens
  binary + table: ~5   tokens equivalent (post-load)
"""


__all__ = [
    "CLAIM_SCHEMA",
    "CYCLE_ENUM",
    "CYCLE_NAME_TO_INT",
    "LINE_FIELDS",
    "TABLE_FIELDS",
    "BIN_CLAIM_BYTES",
    "MASK_BITS",
    "NO_INDEX",
    "claim_to_line",
    "line_to_claim",
    "encode_claim",
    "decode_claim",
    "build_table",
    "write_table",
    "read_table",
    "write_claims",
    "read_claims",
    "write_claims_binary",
    "read_claims_binary",
    "id_lookup_from_claims",
    "PROTOCOL",
]
