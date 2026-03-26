# symbols/symbolic_to_geometric_plugin.py
"""
Symbolic-to-geometric translation plugin.

Bridges two glyph systems:
  1. Internal operation symbols (CORE, DYNA, SPI, ...)
  2. Mandala-Computing octahedral state glyphs (⊕⊖⊗⊘⊙⊚⊛⊜)
     consumed from: atlas/remote/mandala/glyphs.json
     canonical source: mappings/octahedral_state_encoding.json

Both resolve to GEIS geometric operations or octahedral state lookups.
"""

import json
import os

_MAPPING_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'mappings', 'octahedral_state_encoding.json'
)


def _load_state_table():
    """Load canonical octahedral state encoding table."""
    try:
        with open(_MAPPING_FILE) as f:
            data = json.load(f)
        return {s["glyph_unicode"]: s for s in data["states"]}
    except (FileNotFoundError, KeyError):
        return {}


# Octahedral state glyphs from Mandala-Computing (⊕ through ⊜)
# Loaded lazily on first use
_GLYPH_TABLE = None


def _glyph_table():
    global _GLYPH_TABLE
    if _GLYPH_TABLE is None:
        _GLYPH_TABLE = _load_state_table()
    return _GLYPH_TABLE


class SymbolicToGeometricTranslator:
    """
    Translates symbolic tokens into geometric operation descriptors.

    Handles two token types:
      - Operation symbols: CORE, DYNA, SPI, ...
      - Octahedral glyphs: ⊕ (state 0) through ⊜ (state 7)

    Octahedral glyphs resolve to their full state record from
    mappings/octahedral_state_encoding.json, which bridges
    Mandala-Computing's angle system with GEIS vertex-bits.
    """

    def __init__(self):
        self.symbol_map = {
            "CORE": "field_centering",
            "FORM": "geometric_shape_generation",
            "DYNA": "vector_field_flow",
            "EQ":   "field_probe",
            "SPI":  "spiral_field_structure",
            "EE":   "emergent_pattern_scan",
            "…":    "expansion_extrapolation",
            # Mandala-Computing operation tokens
            "BLOOM":   "mandala_bloom_expansion",
            "RELAX":   "ground_state_relaxation",
            "ANNEAL":  "metropolis_hastings_step",
            "QUANTUM": "qudit_octit_superposition",
        }

    def translate(self, symbolic_code):
        """
        Convert symbolic string into geometric operation descriptors.

        Returns list of dicts with 'type' and 'payload' keys.
        """
        ops = []
        for token in symbolic_code.split():
            ops.append(self._resolve_token(token))
        return ops

    def _resolve_token(self, token):
        # 1. Check internal operation symbols
        if token in self.symbol_map:
            return {"type": "operation", "payload": self.symbol_map[token]}

        # 2. Check octahedral state glyphs (single Unicode char)
        table = _glyph_table()
        if token in table:
            state = table[token]
            return {
                "type": "octahedral_state",
                "payload": {
                    "state":       state["state"],
                    "label":       state["label"],
                    "vertex_bits": state["vertex_bits"],
                    "gray_code":   state["gray_code"],
                    "geis_token":  state["geis_token"],
                    "eigenvalues": state["eigenvalues"],
                    "cartesian":   state["cartesian"],
                    "character":   state["character"],
                }
            }

        # 3. Try vertex_bits direct lookup (e.g. "000", "101")
        if len(token) == 3 and all(c in "01" for c in token):
            for s in _glyph_table().values():
                if s["vertex_bits"] == token:
                    return {"type": "octahedral_state", "payload": s}

        return {"type": "unknown", "payload": token}

    def state_from_glyph(self, glyph_unicode):
        """Return full state record for a Mandala-Computing octahedral glyph."""
        return _glyph_table().get(glyph_unicode)

    def glyph_from_state(self, state_index):
        """Return Unicode glyph for a given state index (0-7)."""
        for entry in _glyph_table().values():
            if entry["state"] == state_index:
                return entry["glyph_unicode"]
        return None

    def all_states(self):
        """Return all 8 octahedral states in index order."""
        table = _glyph_table()
        return sorted(table.values(), key=lambda s: s["state"])


# ---------------------------------------------------------------------------
# Convenience: direct state↔glyph lookup without instantiating translator
# ---------------------------------------------------------------------------

def state_to_glyph(state_index):
    """⊕⊖⊗⊘⊙⊚⊛⊜ — return Unicode glyph for state 0-7."""
    t = SymbolicToGeometricTranslator()
    return t.glyph_from_state(state_index)


def glyph_to_state(glyph):
    """Return state dict for a Mandala-Computing glyph character."""
    return _glyph_table().get(glyph)


if __name__ == "__main__":
    t = SymbolicToGeometricTranslator()

    print("Operation tokens:")
    for op in t.translate("CORE DYNA SPI BLOOM RELAX"):
        print(f"  {op}")

    print("\nOctahedral glyph tokens (Mandala-Computing ⊕ through ⊜):")
    for i in range(8):
        g = state_to_glyph(i)
        if g:
            result = t.translate(g)
            s = result[0]["payload"]
            print(f"  {g}  state={s['state']}  bits={s['vertex_bits']}  {s['label']:<12}  {s['character']}")
