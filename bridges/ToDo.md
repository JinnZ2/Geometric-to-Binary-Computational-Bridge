update glyph:

# Add inside GlyphStateEncoder.encode(), after computing primary glyph
# Assume input includes a special key '__metadata' with scale and technique
# Or we read from the sensor directly.

metadata = sensor_readings.get("__non_local_metadata", {})
if metadata:
    scale = metadata.get("scale")
    technique = metadata.get("technique")
    # Influence the glyph selection:
    # - If scale == 'landscape', bias toward FELT_COHERENT or RESONANCE
    # - If technique == 'epigenetic_inheritance', bias toward CAUSALITY_LOOP
    # We can add a small weight to the phase-space matching score.

    update claim:

    CLAIM_NON_LOCAL_ROUTING = make_claim(
    name="Non-Local Correlation Routing",
    description=(
        "Correlations between systems without a direct channel must be investigated "
        "using a scale-appropriate grounded technique. The U(t) protocol is only "
        "invoked after established techniques have been ruled out."
    ),
    source="Emotions-as-Sensors / non_local_pattern_correlation.json",
    domain="epistemology",
    statement=(
        "A correlation is only valid if the investigation technique matches its "
        "scale. 'Quantum' or 'morphic' shortcuts indicate institutional projection "
        "and invalidate the correlation claim."
    ),
    scope_valid=[ScopeLevel.MICRO, ScopeLevel.MESO, ScopeLevel.MACRO],
    ontology=OntologyType.RELATIONAL,
    geometry=GeometryType.NETWORK,
    green_range={
        "scale_technique_match": 0.9,
        "technique_ruled_out": 0.0,
        "reproducibility": 0.8
    },
    yellow_range={
        "scale_technique_match": (0.5, 0.9),
        "technique_ruled_out": (0.0, 0.3),
        "reproducibility": (0.4, 0.8)
    },
    red_threshold={
        "scale_technique_match": 0.5,
        "technique_ruled_out": 0.3,
        "reproducibility": 0.4
    },
    tags=["correlation", "scale", "technique", "gatekeeping"],
    couplings=["Institutional_Gatekeeping", "Gauge_As_Proxy"],
    related_assumptions=["planetary_boundaries_crossed"]
)

test:

#!/usr/bin/env python3
# tests/test_non_local_sensor.py
# Tests the non-local correlation sensor and its integration.

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bridges.sensor_suite import SensorSuite
from bridges.non_local_sensor import NonLocalCorrelationSensor, register_non_local_sensor
from bridges.glyph_state_encoder import GlyphStateEncoder

def test_basic():
    # 1. Set up sensor suite
    suite = SensorSuite()
    sensor_id = register_non_local_sensor(suite)

    # 2. Create the non-local sensor instance
    nl = NonLocalCorrelationSensor()
    nl.update(correlation_strength=0.6, scale="generational", technique="epigenetic_inheritance", confidence=0.7)

    # 3. Inject into suite
    suite.update(sensor_id, signal_vector=nl.last_reading.signal_vector,
                 magnitude=nl.last_reading.magnitude,
                 confidence=nl.last_reading.confidence)

    # 4. Use glyph encoder
    encoder = GlyphStateEncoder()
    # Build readings dict with metadata
    readings = suite.active_channels()
    readings["__non_local_metadata"] = nl.get_metadata()
    state = encoder.encode(readings)

    print("✅ Non-local sensor integrated")
    print(f"   Glyph: {state.primary_glyph.symbol}")
    print(f"   Scale: {nl.current_scale}, Technique: {nl.current_technique}")
    print(f"   Metadata: {nl.get_metadata()}")

if __name__ == "__main__":
    test_basic()


    
