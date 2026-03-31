# field_system.py
# Minimal portable rule-field engine for regenerative system tracking
# Added ecological field coupling and effective nourishment calculation

from typing import Dict, Any

# ---------------------------
# Defaults / Baselines
# ---------------------------

DEFAULTS = {
    "soil_trend": 0.0,          # change per unit time
    "water_retention": 0.5,     # 0-1 proxy
    "input_energy": 1.0,        # arbitrary units
    "output_yield": 1.0,        # arbitrary units
    "disturbance": 0.0,         # 0-1 proxy
    "waste_factor": 0.4,        # 0-1
    "nutrient_density": 0.8,    # 0-1
    "production_area": 30,       # acres
    "ecological_area": 170,      # acres
    "coupling_strength": 1.0,    # 0-1
    "ecological_amplification": 2.0  # max factor g(k) = 1 + alpha * k
}

BASELINES = {
    "water_retention_min": 0.4,
    "energy_ratio_min": 1.0
}

# ---------------------------
# Helpers
# ---------------------------

def fill_state(state: Dict[str, Any]) -> Dict[str, float]:
    """Fill missing values with defaults."""
    return {k: float(state.get(k, DEFAULTS[k])) for k in DEFAULTS}


def regen_capacity(state: Dict[str, float]) -> float:
    """Proxy regeneration capacity."""
    base = 1.0
    soil_factor = 1.0 + state["soil_trend"]
    water_factor = state["water_retention"]
    disturbance_penalty = 1.0 - state["disturbance"]
    return base * soil_factor * water_factor * disturbance_penalty


# ---------------------------
# Constraint Layer (Invariant)
# ---------------------------

def constraints(state: Dict[str, float]) -> Dict[str, bool]:
    rc = regen_capacity(state)
    return {
        "soil_positive": state["soil_trend"] >= 0,
        "water_non_degrading": state["water_retention"] >= BASELINES["water_retention_min"],
        "no_overextraction": state["output_yield"] <= rc,
        "energy_ratio": (
            state["output_yield"] / state["input_energy"]
            if state["input_energy"] > 0 else 0
        ) >= BASELINES["energy_ratio_min"]
    }


# ---------------------------
# Drift Detection
# ---------------------------

def drift(state: Dict[str, float]) -> Dict[str, bool]:
    c = constraints(state)
    return {k: not v for k, v in c.items()}


# ---------------------------
# Adaptive Suggestions
# ---------------------------

def suggest(state: Dict[str, float]) -> Dict[str, Any]:
    issues = drift(state)
    actions = []

    if issues["soil_positive"]:
        actions.append("Increase biomass input, reduce tillage/disturbance")
    if issues["water_non_degrading"]:
        actions.append("Improve water retention (mulch, contouring, infiltration)")
    if issues["no_overextraction"]:
        actions.append("Reduce yield pressure or increase regeneration capacity")
    if issues["energy_ratio"]:
        actions.append("Reduce external inputs or improve system efficiency")

    return {
        "issues": issues,
        "actions": actions
    }


# ---------------------------
# Effective Yield & Coupling
# ---------------------------

def effective_yield(state: Dict[str, float]) -> Dict[str, float]:
    """Calculate yield adjusted for waste, nutrients, and ecological coupling."""
    Wf = state["waste_factor"]
    Nd = state["nutrient_density"]
    Yg = state["output_yield"]

    # Adjust for waste and nutrient density
    Y_adj = Yg * (1 - Wf) * Nd**2

    # Ecological coupling amplification
    alpha = state["ecological_amplification"]
    k = state["coupling_strength"]
    gk = 1 + alpha * k

    Y_eff = Y_adj * gk

    # Total system output
    H_total = Y_eff * state["production_area"]

    return {
        "adjusted_yield": Y_adj,
        "ecological_amplification_factor": gk,
        "effective_yield_per_acre": Y_eff,
        "total_nourishment_units": H_total
    }


# ---------------------------
# Thermal Limit Check
# ---------------------------

def thermal_limit_check(state: Dict[str, float]) -> Dict[str, Any]:
    """
    Detects when the system is 'Redlining' or leaking heat.
    High Prediction Error = Model/Reality Dissonance.
    """
    pe = abs(state["output_yield"] - regen_capacity(state))
    thermal_load = state["disturbance"] * state["input_energy"]
    limit_reached = thermal_load > 0.8 or pe > 0.5

    return {
        "prediction_error": pe,
        "thermal_load": thermal_load,
        "critical_alert": limit_reached,
        "instruction": "REDUCE VELOCITY / INCREASE REST" if limit_reached else "NOMINAL"
    }


# ---------------------------
# Scoring / Diagnostics
# ---------------------------

def score(state: Dict[str, float]) -> float:
    c = constraints(state)
    return sum(c.values()) / len(c)


def report(state: Dict[str, Any]) -> Dict[str, Any]:
    s = fill_state(state)
    return {
        "state": s,
        "constraints": constraints(s),
        "drift": drift(s),
        "score": score(s),
        "suggestions": suggest(s),
        "yield_analysis": effective_yield(s),
        "thermal_limit": thermal_limit_check(s)
    }


# ---------------------------
# Scenario Library
# ---------------------------

SCENARIOS = {
    "big_ag_bot": {
        "label": "Big Ag-Bot (200 Acres Monocrop)",
        "description": "Industrial monocrop: maximizes gross tonnage via massive "
                       "input energy, no ecological coupling, mines soil.",
        "state": {
            "soil_trend": -0.2,
            "water_retention": 0.35,
            "input_energy": 3.0,
            "output_yield": 2.0,
            "disturbance": 0.4,
            "waste_factor": 0.7,
            "nutrient_density": 0.4,
            "production_area": 200,
            "ecological_area": 0,
            "coupling_strength": 0.0,
            "ecological_amplification": 1.0,
        },
    },
    "sovereign_steward": {
        "label": "Sovereign Steward (30 Prod + 170 Wild)",
        "description": "30 acres production, 170 acres wild bio-battery. "
                       "Builds soil, closed-loop waste, high nutrient density.",
        "state": {
            "soil_trend": 0.1,
            "water_retention": 0.7,
            "input_energy": 0.5,
            "output_yield": 0.8,
            "disturbance": 0.05,
            "waste_factor": 0.1,
            "nutrient_density": 0.9,
            "production_area": 30,
            "ecological_area": 170,
            "coupling_strength": 0.9,
            "ecological_amplification": 2.0,
        },
    },
    "corporate_270": {
        "label": 'Corporate "270% Productivity" Claim',
        "description": "Maps the claim 'AI-managed precision ag will increase "
                       "productivity 270% by 2030 while keeping emissions in check' "
                       "to system state. Forces S_e = 0.",
        "state": {
            "soil_trend": -0.05,
            "water_retention": 0.5,
            "input_energy": 2.0,
            "output_yield": 2.7,
            "disturbance": 0.25,
            "waste_factor": 0.7,
            "nutrient_density": 0.4,
            "production_area": 200,
            "ecological_area": 0,
            "coupling_strength": 0.0,
            "ecological_amplification": 1.0,
        },
    },
}


def compare_scenarios(*names: str) -> Dict[str, Any]:
    """Run report() on named scenarios and return side-by-side results."""
    results = {}
    for name in names:
        scenario = SCENARIOS[name]
        r = report(scenario["state"])
        r["label"] = scenario["label"]
        r["description"] = scenario["description"]
        results[name] = r
    return results


# ---------------------------
# Example Run
# ---------------------------

if __name__ == "__main__":
    from pprint import pprint

    print("=== Scenario Comparison ===\n")
    comparison = compare_scenarios("big_ag_bot", "sovereign_steward", "corporate_270")
    for name, result in comparison.items():
        h = result["yield_analysis"]["total_nourishment_units"]
        s = result["score"]
        thermal = result["thermal_limit"]
        violations = [k for k, v in result["drift"].items() if v]
        print(f"  {result['label']}")
        print(f"    H_total: {h:.2f}  |  Score: {s:.2f}  |  "
              f"Thermal: {'CRITICAL' if thermal['critical_alert'] else 'nominal'}")
        if violations:
            print(f"    Violations: {', '.join(violations)}")
        print()
