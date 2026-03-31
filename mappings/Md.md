# Regenerative System Tracking — Reference

All prose from the original analysis is now executable code.

## Module Map

| Module | What it does |
|--------|-------------|
| `field_system.py` | Rule-field engine: constraints, drift, yield, thermal limit, **scenario library** |
| `six_sigma_audit.py` | Tolerances, defect rate, process capability, **handshake diagnostic**, **stress test pipeline** |
| `ai_dataset_delusion_checker.py` | Basic systemic assumption detector |
| `ai_delusion_econ_checker.py` | Extended checker with economic plausibility scoring |

## Quick Start

```bash
# Compare all built-in scenarios (Big Ag-Bot, Sovereign Steward, Corporate 270%)
python -m mappings.field_system

# Run full Six Sigma audit with narrative + field analysis
python -m mappings.six_sigma_audit
```

## Scenarios (field_system.SCENARIOS)

| Key | Label | H_total | Score | Thermal |
|-----|-------|---------|-------|---------|
| `big_ag_bot` | 200 Acres Monocrop | 19.20 | 0.00 | CRITICAL |
| `sovereign_steward` | 30 Prod + 170 Wild | 48.99 | 0.75 | nominal |
| `corporate_270` | "270% Productivity" Claim | 25.92 | 0.50 | CRITICAL |

## API

### field_system

```python
from mappings.field_system import report, compare_scenarios, SCENARIOS

# Single scenario
result = report(SCENARIOS["sovereign_steward"]["state"])

# Side-by-side
comparison = compare_scenarios("big_ag_bot", "sovereign_steward")
```

### six_sigma_audit

```python
from mappings.six_sigma_audit import handshake, stress_test, defect_rate, process_capability

# Handshake: combined narrative + field diagnostic
diag = handshake(text="some claim text", state=my_state)
# -> {"verdict": "ALERT"|"NOMINAL", "flags": [...], "narrative": {...}, "field": {...}}

# Stress test: full claim-to-audit pipeline
result = stress_test(
    claim_text="We will maximize efficiency...",
    claimed_state=my_state,
    label="My Claim",
)
# -> includes h_total, benchmarks, ratio_vs_steward

# Individual tools
dr = defect_rate(my_state)    # {"defect_rate": 0.57, "defects": 4, "total": 7, ...}
cp = process_capability(my_state)  # per-variable Cp values
```

### Adding New Scenarios

```python
from mappings.field_system import SCENARIOS

SCENARIOS["my_scenario"] = {
    "label": "My Custom Scenario",
    "description": "...",
    "state": {
        "soil_trend": 0.0,
        "water_retention": 0.5,
        # ... all 11 fields
    },
}
```

### Adding New Tolerances

```python
from mappings.six_sigma_audit import TOLERANCES

# ("ge", limit) = value must be >= limit
# ("le", limit) = value must be <= limit
TOLERANCES["my_new_variable"] = ("ge", 0.5)
```

## Key Findings (from original analysis)

- Steward produces **2.55x** more nourishment on 15% of the land
- Corporate 270% claim: 57% defect rate, 4/7 variables out of spec
- Industrial model fails because it assumes Maximize Yield while Shedding Cost
- "Energy is conserved; utility is lost when structure collapses into thermal equilibrium"
