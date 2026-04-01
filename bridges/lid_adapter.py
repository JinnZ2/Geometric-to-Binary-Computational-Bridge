"""
lid_adapter.py
==============
Adapter connecting the Living Intelligence Database (LID) ontology to the
Geometric-to-Binary bridge encoders.

Integration points
------------------
1. **Concept ↔ Encoder mapping**: LID energy entities map 1:1 to bridge encoders.
   Load an ontology entity, get back a configured encoder instance.

2. **Interaction matrix cross-validation**: LID's INTERACTION_MATRIX and the
   bridge repo's physical_coupling_matrix share the same energy-coupling idea.
   This adapter translates between them.

3. **Ontology-driven discovery**: Use LID's categorize() to auto-classify new
   physical phenomena and suggest which bridge encoder to route them through.

Usage
-----
    from bridges.lid_adapter import LIDAdapter

    adapter = LIDAdapter("/path/to/Living-Intelligence-Database")

    # Get a bridge encoder for a LID entity
    encoder = adapter.encoder_for("MAG_BRIDGE")

    # Classify raw text and get the best bridge
    bridge_name = adapter.classify_to_bridge("magnetic field resonance at 40T")

    # Cross-validate coupling matrices
    report = adapter.cross_validate_couplings()
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# ── Encoder registry ──────────────────────────────────────────────────────

# Map LID entity IDs → bridge encoder module + class
ENTITY_ENCODER_MAP: Dict[str, Tuple[str, str]] = {
    "MAG_BRIDGE":       ("bridges.magnetic_encoder",      "MagneticBridgeEncoder"),
    "LIGHT_BR":         ("bridges.light_encoder",         "LightBridgeEncoder"),
    "CONSCIOUSNESS_BR": ("bridges.consciousness_encoder", "ConsciousnessBridgeEncoder"),
    "EMOTION_BR":       ("bridges.emotion_encoder",       "EmotionBridgeEncoder"),
    "ELECTRIC_FIELD":   ("bridges.electric_encoder",      "ElectricBridgeEncoder"),
    "GRAVITATIONAL":    ("bridges.gravity_encoder",       "GravityBridgeEncoder"),
    "THERMAL":          ("bridges.thermal_encoder",       "ThermalBridgeEncoder"),
    "FLUX":             ("bridges.wave_encoder",          "WaveBridgeEncoder"),
    "RES_SENSOR":       ("bridges.sound_encoder",         "SoundBridgeEncoder"),
}

# Map LID ontology categories → bridge modality names
CATEGORY_BRIDGE_MAP: Dict[str, List[str]] = {
    "energy":   ["magnetic", "electric", "thermal", "wave", "light"],
    "crystal":  ["magnetic", "light"],
    "plasma":   ["electric", "wave", "thermal"],
    "shape":    ["gravity", "pressure"],
    "temporal": ["wave", "consciousness"],
    "animal":   ["sound", "consciousness", "emotion"],
    "plant":    ["chemical", "thermal"],
}


# ── Adapter ───────────────────────────────────────────────────────────────

class LIDAdapter:
    """
    Bridge between the Living Intelligence Database ontology and the
    Geometric-to-Binary encoder suite.
    """

    def __init__(self, lid_root: str | Path = None):
        """
        lid_root: path to the Living-Intelligence-Database repo root.
                  If None, tries common sibling locations.
        """
        self.lid_root = self._resolve_root(lid_root)
        self._ontology: Dict[str, dict] = {}
        self._index: Optional[dict] = None
        self._lid_available = self.lid_root is not None

    @staticmethod
    def _resolve_root(lid_root) -> Optional[Path]:
        if lid_root is not None:
            p = Path(lid_root)
            if p.is_dir():
                return p
            return None
        # Try sibling directories
        here = Path(__file__).resolve().parent.parent
        for candidate in [
            here.parent / "Living-Intelligence-Database",
            Path.home() / "Living-Intelligence-Database",
        ]:
            if candidate.is_dir() and (candidate / "ontology").is_dir():
                return candidate
        return None

    # ── Ontology access ───────────────────────────────────────────────

    def load_index(self) -> dict:
        """Load the LID ontology index."""
        if self._index is not None:
            return self._index
        if not self._lid_available:
            return {"entities": []}
        idx_path = self.lid_root / "ontology_index.json"
        if not idx_path.exists():
            return {"entities": []}
        with open(idx_path) as f:
            self._index = json.load(f)
        return self._index

    def load_entity(self, entity_id: str) -> Optional[dict]:
        """Load a single entity by ID from the LID ontology."""
        if entity_id in self._ontology:
            return self._ontology[entity_id]
        if not self._lid_available:
            return None
        index = self.load_index()
        for entry in index.get("entities", []):
            if entry["id"] == entity_id:
                filepath = self.lid_root / entry["path"]
                if filepath.exists():
                    with open(filepath) as f:
                        data = json.load(f)
                    self._ontology[entity_id] = data
                    return data
        return None

    def list_bridge_entities(self) -> List[dict]:
        """List all LID entities that have a known bridge encoder mapping."""
        index = self.load_index()
        results = []
        for entry in index.get("entities", []):
            if entry["id"] in ENTITY_ENCODER_MAP:
                results.append(entry)
        return results

    # ── Encoder instantiation ─────────────────────────────────────────

    def encoder_for(self, entity_id: str) -> Any:
        """
        Get a bridge encoder instance for a LID entity.

        Returns an instantiated BinaryBridgeEncoder subclass, or None
        if the entity has no known encoder mapping.
        """
        if entity_id not in ENTITY_ENCODER_MAP:
            return None

        module_path, class_name = ENTITY_ENCODER_MAP[entity_id]
        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            return cls()
        except (ImportError, AttributeError) as e:
            return None

    def encoders_for_category(self, category: str) -> List[str]:
        """
        Get bridge modality names suitable for a LID ontology category.

        Example: encoders_for_category("plasma") → ["electric", "wave", "thermal"]
        """
        return CATEGORY_BRIDGE_MAP.get(category, [])

    # ── Classification ────────────────────────────────────────────────

    def classify_to_bridge(self, text: str) -> Optional[str]:
        """
        Classify free text and return the best bridge modality name.

        Uses keyword matching similar to LID's expand.py categorize().
        """
        text_lower = text.lower()

        # Direct modality keyword detection (most specific wins)
        modality_keywords = {
            "magnetic":      ["magnetic", "polarity", "ferromagnet", "coil", "gauss", "tesla"],
            "electric":      ["electric", "charge", "voltage", "current", "coulomb", "capacit"],
            "light":         ["light", "photon", "wavelength", "spectrum", "polariz", "optical"],
            "sound":         ["sound", "acoustic", "pitch", "frequency", "resonan", "vibrat"],
            "gravity":       ["gravity", "gravitation", "orbit", "curvature", "mass", "geodesic"],
            "wave":          ["quantum", "wave function", "psi", "momentum", "schrodinger"],
            "thermal":       ["thermal", "temperature", "heat", "radiation", "infrared", "boltzmann"],
            "pressure":      ["pressure", "stress", "strain", "haptic", "force", "pascal"],
            "chemical":      ["chemical", "reaction", "molecule", "bond", "ph ", "catalyst"],
            "consciousness": ["consciousness", "awareness", "entropy", "attention", "phi"],
            "emotion":       ["emotion", "affect", "pleasure", "arousal", "dominance", "pad"],
        }

        scores: Dict[str, int] = {}
        for modality, keywords in modality_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[modality] = scores.get(modality, 0) + 1

        if not scores:
            return None

        return max(scores, key=scores.get)

    # ── Coupling cross-validation ─────────────────────────────────────

    def cross_validate_couplings(self) -> Dict[str, Any]:
        """
        Compare LID's INTERACTION_MATRIX with physical_coupling_matrix.py
        efficiencies. Returns a report of agreements and discrepancies.
        """
        # LID interaction coefficients (from playground.py)
        lid_matrix = {
            ("crystal", "energy"): 0.8,
            ("crystal", "shape"):  0.9,
            ("energy", "plasma"):  0.9,
            ("energy", "energy"):  0.7,
            ("energy", "shape"):   0.8,
            ("animal", "shape"):   0.7,
            ("plant", "energy"):   0.7,
            ("crystal", "crystal"): 0.6,
        }

        # Bridge coupling matrix node mapping:
        #   LID category → physical_coupling_matrix node
        lid_to_pcm = {
            "energy":  "EM",
            "crystal": "C",
            "plasma":  "T",  # thermal/plasma overlap
            "shape":   "G",  # geometric/gravity
        }

        try:
            from physical_coupling_matrix import PhysicalCouplingMatrix
            pcm = PhysicalCouplingMatrix()
        except ImportError:
            return {
                "status": "physical_coupling_matrix not importable",
                "comparisons": [],
            }

        comparisons = []
        for (cat_a, cat_b), lid_coeff in lid_matrix.items():
            node_a = lid_to_pcm.get(cat_a)
            node_b = lid_to_pcm.get(cat_b)
            if node_a and node_b and node_a != node_b:
                try:
                    pcm_eff = pcm.get_efficiency(node_a, node_b)
                except (KeyError, IndexError):
                    pcm_eff = None
                delta = abs(lid_coeff - pcm_eff) if pcm_eff is not None else None
                comparisons.append({
                    "lid_pair": (cat_a, cat_b),
                    "lid_coeff": lid_coeff,
                    "pcm_pair": (node_a, node_b),
                    "pcm_eff": pcm_eff,
                    "delta": delta,
                    "aligned": delta is not None and delta < 0.2,
                })

        aligned = sum(1 for c in comparisons if c["aligned"])
        return {
            "status": "ok",
            "total": len(comparisons),
            "aligned": aligned,
            "divergent": len(comparisons) - aligned,
            "comparisons": comparisons,
        }

    # ── Summary ───────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a text summary of the adapter state."""
        lines = [
            f"LID available: {self._lid_available}",
            f"LID root: {self.lid_root}",
        ]
        if self._lid_available:
            index = self.load_index()
            total = len(index.get("entities", []))
            bridge = len(self.list_bridge_entities())
            lines.append(f"Total LID entities: {total}")
            lines.append(f"Bridge-mapped entities: {bridge}")
            lines.append(f"Entity→Encoder map: {len(ENTITY_ENCODER_MAP)} entries")
        return "\n".join(lines)
