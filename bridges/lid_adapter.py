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

import importlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


# ── Encoder registry ──────────────────────────────────────────────────────

# Map LID entity IDs → bridge encoder module + class  (legacy hard-coded)
ENTITY_ENCODER_MAP: Dict[str, Tuple[str, str]] = {
    "MAG_BRIDGE":       ("bridges.magnetic_encoder",      "MagneticBridgeEncoder"),
    "LIGHT_BR":         ("bridges.light_encoder",         "LightBridgeEncoder"),
    "CONSCIOUSNESS_BR": ("bridges.cognitive.consciousness_encoder", "ConsciousnessBridgeEncoder"),
    "EMOTION_BR":       ("bridges.cognitive.emotion_encoder",       "EmotionBridgeEncoder"),
    "ELECTRIC_FIELD":   ("bridges.electric_encoder",      "ElectricBridgeEncoder"),
    "GRAVITATIONAL":    ("bridges.gravity_encoder",       "GravityBridgeEncoder"),
    "THERMAL":          ("bridges.thermal_encoder",       "ThermalBridgeEncoder"),
    "FLUX":             ("bridges.wave_encoder",          "WaveBridgeEncoder"),
    "RES_SENSOR":       ("bridges.sound_encoder",         "SoundBridgeEncoder"),
}

# Map modality name → (module, class) for all 11 bridge encoders
MODALITY_ENCODER_MAP: Dict[str, Tuple[str, str]] = {
    "magnetic":      ("bridges.magnetic_encoder",      "MagneticBridgeEncoder"),
    "light":         ("bridges.light_encoder",         "LightBridgeEncoder"),
    "sound":         ("bridges.sound_encoder",         "SoundBridgeEncoder"),
    "gravity":       ("bridges.gravity_encoder",       "GravityBridgeEncoder"),
    "electric":      ("bridges.electric_encoder",      "ElectricBridgeEncoder"),
    "wave":          ("bridges.wave_encoder",          "WaveBridgeEncoder"),
    "thermal":       ("bridges.thermal_encoder",       "ThermalBridgeEncoder"),
    "pressure":      ("bridges.pressure_encoder",      "PressureBridgeEncoder"),
    "chemical":      ("bridges.chemical_encoder",      "ChemicalBridgeEncoder"),
    "consciousness": ("bridges.cognitive.consciousness_encoder", "ConsciousnessBridgeEncoder"),
    "emotion":       ("bridges.cognitive.emotion_encoder",       "EmotionBridgeEncoder"),
}

# ── Pattern/keyword → modality inference tables ──────────────────────────

# Keywords found in entity descriptions, patterns, and core_attributes that
# signal affinity with a particular bridge modality.
_PATTERN_MODALITY_KEYWORDS: Dict[str, List[str]] = {
    "magnetic": [
        "magnetic", "polarity", "ferromagnet", "magnetosphere", "dipole",
        "field line", "flux stabiliz", "spin symmetry", "gauss", "tesla",
    ],
    "electric": [
        "electric", "charge", "voltage", "current", "coulomb", "capacit",
        "discharge", "potential difference", "ioniz", "signal propagation",
    ],
    "light": [
        "light", "photon", "wavelength", "spectrum", "polariz", "optical",
        "luminous", "refract", "dispers", "glow", "photon emission",
        "bioluminescen", "chromatophore", "iridescen", "pigment",
    ],
    "sound": [
        "sound", "acoustic", "pitch", "resonan", "vibrat", "echolocat",
        "ultrasonic", "infrasound", "harmonic", "stridulat", "song",
        "sonar", "piezoelectric",
    ],
    "gravity": [
        "gravity", "gravitation", "orbit", "curvature", "mass", "geodesic",
        "tidal", "centripetal", "weight", "freefall",
    ],
    "wave": [
        "quantum", "wave function", "psi", "momentum", "schrodinger",
        "superposition", "entangle", "decoher", "phase coherence",
        "interference", "diffraction",
    ],
    "thermal": [
        "thermal", "temperature", "heat", "infrared", "boltzmann",
        "thermoregulat", "endotherm", "exotherm", "radiat", "cooling",
        "solar", "photovoltaic",
    ],
    "pressure": [
        "pressure", "stress", "strain", "haptic", "force", "pascal",
        "tension", "elastic", "compression", "hardness", "turgor",
        "hydraulic",
    ],
    "chemical": [
        "chemical", "reaction", "molecule", "bond", "catalyst", "ph ",
        "enzyme", "metabol", "nutrient", "photosynthes", "oxidat",
        "ferment", "digest", "symbiosis", "toxin", "venom", "secretion",
        "chemoreception", "pheromone", "biofilm",
    ],
    "consciousness": [
        "consciousness", "awareness", "entropy", "attention", "phi",
        "self-organiz", "negentrop", "emergence", "cogniti", "intelligence",
        "threshold", "information", "sentien", "neurology",
    ],
    "emotion": [
        "emotion", "affect", "pleasure", "arousal", "dominance", "pad",
        "play", "social bonding", "empathy", "cooperative", "culture",
    ],
}

# Ontology category → guaranteed baseline modalities (always assigned)
_ONTOLOGY_BASELINE: Dict[str, List[str]] = {
    "energy":   ["wave"],
    "crystal":  ["magnetic", "light", "pressure"],
    "plasma":   ["electric", "thermal", "wave"],
    "shape":    ["gravity", "pressure"],
    "temporal": ["wave", "consciousness"],
    "animal":   ["sound", "consciousness", "emotion"],
    "plant":    ["chemical", "thermal"],
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
        self._auto_wired: Optional[Dict[str, List[str]]] = None

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

    def load_all_entities(self) -> Dict[str, dict]:
        """
        Walk the ``ontology/`` directory tree and load every entity JSON.

        Skips collection files (top-level arrays) and non-entity files.
        Results are merged into ``self._ontology`` and returned.
        """
        if not self._lid_available:
            return {}
        ontology_dir = self.lid_root / "ontology"
        if not ontology_dir.is_dir():
            return {}
        for root, _dirs, files in os.walk(ontology_dir):
            for fname in files:
                if not fname.endswith(".json"):
                    continue
                fpath = Path(root) / fname
                try:
                    with open(fpath) as f:
                        data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
                # Skip collection files (arrays) and files without an id
                if not isinstance(data, dict) or "id" not in data:
                    continue
                eid = data["id"]
                if eid not in self._ontology:
                    self._ontology[eid] = data
        return self._ontology

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

    # ── Auto-wiring ─────────────────────────────────────────────────

    def _infer_modalities(self, entity: dict) -> List[str]:
        """Infer bridge modalities from an entity's text content."""
        # Build a single searchable text blob from all relevant fields
        parts = [
            entity.get("description", ""),
            json.dumps(entity.get("core_attributes", {})),
            json.dumps(entity.get("patterns", [])),
        ]
        blob = " ".join(parts).lower()

        hits: Dict[str, int] = {}
        for modality, keywords in _PATTERN_MODALITY_KEYWORDS.items():
            for kw in keywords:
                if kw in blob:
                    hits[modality] = hits.get(modality, 0) + 1

        # Start with baseline modalities for this ontology category
        category = entity.get("ontology", "")
        baseline = list(_ONTOLOGY_BASELINE.get(category, []))

        # Add any keyword-inferred modalities
        for modality in hits:
            if modality not in baseline:
                baseline.append(modality)

        return baseline

    def auto_wire(self) -> Dict[str, List[str]]:
        """
        Map **every** LID entity to its bridge modality(ies) based on
        category baselines + keyword inference from descriptions/patterns.

        Iterates all entity files under ``ontology/`` (not just the
        14-entity index), so all 78 entities get wired.

        Returns dict of entity_id → sorted list of modality names.
        Caches result on ``self._auto_wired``.
        """
        if self._auto_wired is not None:
            return self._auto_wired

        if not self._lid_available:
            self._auto_wired = {}
            return self._auto_wired

        all_entities = self.load_all_entities()
        result: Dict[str, List[str]] = {}

        for entity_id, entity in all_entities.items():
            modalities = self._infer_modalities(entity)

            # Layer: also honour hard-coded ENTITY_ENCODER_MAP entries
            if entity_id in ENTITY_ENCODER_MAP:
                mod_path = ENTITY_ENCODER_MAP[entity_id][0]
                mod_name = mod_path.rsplit(".", 1)[-1].replace("_encoder", "")
                if mod_name not in modalities:
                    modalities.append(mod_name)

            # Layer: classify_to_bridge on description as catch-all
            desc = entity.get("description", "")
            if desc:
                classified = self.classify_to_bridge(desc)
                if classified and classified not in modalities:
                    modalities.append(classified)

            result[entity_id] = sorted(modalities)

        self._auto_wired = result
        return result

    def get_all_bridge_routes(self) -> Dict[str, List[str]]:
        """Return the full auto-wired mapping (calls auto_wire if needed)."""
        return self.auto_wire()

    def encoder_for_modality(self, modality: str) -> Any:
        """Instantiate a bridge encoder by modality name."""
        if modality not in MODALITY_ENCODER_MAP:
            return None
        module_path, class_name = MODALITY_ENCODER_MAP[modality]
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            return cls()
        except (ImportError, AttributeError):
            return None

    def encode_entity(self, entity_id: str,
                      geometry_data: Any = None) -> Dict[str, Any]:
        """
        Look up an entity's bridge routes and return encoder instances.

        Returns dict of {modality: encoder_instance}.
        If geometry_data is provided, calls from_geometry() + to_binary()
        on each encoder.
        """
        routes = self.get_all_bridge_routes()
        modalities = routes.get(entity_id, [])

        encoders: Dict[str, Any] = {}
        for modality in modalities:
            enc = self.encoder_for_modality(modality)
            if enc is None:
                continue
            if geometry_data is not None:
                enc.from_geometry(geometry_data)
                enc.to_binary()
            encoders[modality] = enc

        return encoders

    # ── Summary ───────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a text summary of the adapter state."""
        lines = [
            f"LID available: {self._lid_available}",
            f"LID root: {self.lid_root}",
        ]
        if self._lid_available:
            all_ents = self.load_all_entities()
            bridge = len(self.list_bridge_entities())
            wired = self.get_all_bridge_routes()
            lines.append(f"Total LID entities: {len(all_ents)}")
            lines.append(f"Hard-mapped entities (ENTITY_ENCODER_MAP): {bridge}")
            lines.append(f"Auto-wired entities: {len(wired)}")
            lines.append(f"Modality encoders available: {len(MODALITY_ENCODER_MAP)}")
        return "\n".join(lines)
