# earth-systems-physics / claim_playground

**CC0 — No Rights Reserved**

A claim registry, versioning system, and T1–T4 reality-test harness for evaluating assertions across physics, climate science, epistemology, economics, and institutional analysis.

## Core Idea

Every claim carries its own:
- **Scope** (micro → meso → macro → cosmic)
- **Ontology** (substance, process, field, relational, pre-linguistic, institutional)
- **Geometry** (euclidean, network, fractal, field, pre-linguistic)
- **Green / Yellow / Red boundaries** — where it holds, degrades, or breaks
- **Couplings** — cross-references to other claims
- **Test history** — accumulated evidence

## The Four Mandatory Tests (T1–T4)

| Test | Name | Question |
|------|------|----------|
| **T1** | Thermodynamic Closure | Does the claim close its own energy/entropy budget? |
| **T2** | Cascade Exposure | What 2nd/3rd order effects appear at scale? |
| **T3** | Scale Invariance (Zoom) | Where does the claim hold, degrade, or shatter? |
| **T4** | Ontology Translation | Is the claim valid under different ontological frames? |

## Quick Start

```bash
# Install
pip install -e .

# Run all tests
pytest tests/ -v

# List seeded claims
python -m claim_playground.cli --list-registry

# Evaluate a seeded claim
python -m claim_playground.cli -r amoc_collapse --waste-entropy 5.0

# Evaluate raw text
python -m claim_playground.cli -c "The bridge is safe for full load."   --waste-entropy 50.0 --hidden-subsidies 10.0

# Evaluate from JSON file
python -m claim_playground.cli -f my_claim.json --json-output
```

## Seeded Claims (12)

| ID | Domain | Source |
|----|--------|--------|
| `emergence_beats_design` | systems_theory | McClure, 2026 |
| `body_as_instrument` | epistemology | Practitioner field notes |
| `thermodynamic_closure` | thermodynamics | substrate_audit |
| `amoc_collapse` | climate_physics | van Westen et al. 2024; Ditlevsen 2023 |
| `permafrost_carbon` | climate_physics | Schuur et al. 2022; ICCI 2026 |
| `gauge_as_proxy` | epistemology | Practitioner + McClure |
| `economic_decoupling` | economics | Georgescu-Roegen 1971 |
| `institutional_gatekeeping` | institutional_epistemology | constraint_accountability_chain |
| `dyslexia_geometry` | cognition | Practitioner field notes |
| `consciousness_as_process` | philosophy_of_mind | Practitioner + McClure |
| `scale_dependence` | physics | cascade_engine |
| `calibration_loop` | cybernetics | Practitioner field notes |

## The 9 Ontological Collision Stages

The test suite `tests/test_collisions.py` encodes 9 failure modes that appear when institutional reasoning collides with physical substrate:

0. **Accommodation Masking** — Human absorbs friction; instrument reads nominal.
1. **Arity / Category Absence** — 3-place relation flattened to 1-place scalar.
2. **Scope Shift / Scaling Error** — Micro rule applied to Macro network.
3. **Thermodynamic Neglect** — Heat-sink saturation ignored.
4. **Static Frame vs. Process Dynamic** — Snapshot treated as equilibrium.
5. **Signal / Noise Inversion** — Terrain vibration read as collision signal.
6. **Structural Lock-In** — Policy metric forces reality into compliant records.
7. **Substrate Erasure** — Material decay ignored; original print treated as current state.
8. **Systemic Cascade Blindness** — 2nd/3rd order feedback loops unmodeled.

## Science Notes

- **AMOC Collapse**: The 0.8 kg/m³ density-gradient threshold derives from van Westen et al. (2024, *Phys. Rev. Lett.*) and the buoyancy-flux early-warning signal. However, 2026 CESM research suggests AMOC tipping may be *rate-induced* (forcing-rate dependent) rather than purely threshold-driven. The seeded claim includes both mechanisms.
- **Permafrost Feedback**: Permafrost stores ~1,500 GtC. Current ESMs project additional warming of 0.05–0.7 °C by 2100 from this feedback. The ICCI (2026) reports that including permafrost carbon–climate feedback increases tipping-point probability by up to 50% and can advance timing by centuries.
- **Economic Decoupling**: Based on Georgescu-Roegen’s entropy economics and subsequent empirical work (Wiedmann et al. 2015; Haberl et al. 2020). Absolute decoupling of GDP from energy/throughput has never been observed at macro scale.

## License

CC0 — No Rights Reserved. This is public-domain research infrastructure.

## New in v0.2.0

### JSON Schema Validation
All JSON claim payloads are validated against a strict schema before hydration into Claim objects:
- `scope_valid` must be from `["micro", "meso", "macro", "cosmic", "contextual"]`
- `ontology_assumed` must be from `["substance", "relational", "process", "field", "pre_linguistic", "institutional", "unspecified"]`
- `geometry_assumed` must be from `["euclidean", "riemannian", "fractal", "network", "field", "pre_linguistic", "relational", "unspecified"]`

Invalid payloads raise `ValidationError` with a detailed path to the offending field.

### Additional Physics Seeds (3)

| ID | Domain | Key Equation | T1–T4 Relevance |
|----|--------|--------------|-----------------|
| `plasma_frequency` | space_physics | ωₚ = √(nₑ e² / ε₀ mₑ) | Gauge flattens 3D e⁻ density into binary skip/no-skip (T2 arity flattening + T4 institutional bias) |
| `coriolis_scale` | atmospheric_physics | Ro = U / (fL), f = 2Ω sin φ | Stage-2 scope shift: synoptic model applied to local weather / drone nav (T3 scale violation) |
| `lod_change` | geodesy | ΔLOD = ΔAAM / (Cₘ Ω) + ΔH_core / (Cₘ Ω) | T1 thermodynamic leak: models treat rotation as constant, externalizing angular-momentum debt |

### CI
GitHub Actions runs pytest on Python 3.10–3.12 plus CLI smoke tests on every push/PR.

### Test Coverage
```
tests/test_collisions.py     — 13 tests (9 ontological collision stages + 4 unit tests)
tests/test_json_schema.py    — 9 tests (schema validation edge cases)
```

## Example JSON Claim Payload

```json
{
  "name": "Custom Field Observation",
  "domain": "field_observation",
  "description": "Practitioner observation of coolant system behavior",
  "version": {
    "statement": "Coolant temperature scalar is within green threshold range.",
    "scope_valid": ["micro"],
    "ontology_assumed": "substance",
    "geometry_assumed": "euclidean",
    "green_range": {"temp_c": [70, 90]},
    "yellow_range": {"temp_c": [90, 110]},
    "red_threshold": {"temp_c": 110}
  }
}
```

Validate and evaluate via CLI:
```bash
python -m claim_playground.cli -f my_claim.json --waste-entropy 30.0 --json-output
```

