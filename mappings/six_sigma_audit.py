# six_sigma_audit.py
# Six Sigma audit engine for regenerative system claims
# Wires together: field_system (physics) + delusion checkers (narrative)

from typing import Dict, Any, List
from mappings.field_system import (
    report, fill_state, regen_capacity, effective_yield,
    thermal_limit_check, SCENARIOS, compare_scenarios,
)
from mappings.ai_delusion_econ_checker import (
    extract_delusions, plausibility_score,
)

# ---------------------------
# 1. Tolerance Spec (Six Sigma CTQ)
# ---------------------------

TOLERANCES = {
    # key: (direction, limit)
    #   "ge" = value must be >= limit
    #   "le" = value must be <= limit
    "soil_trend":              ("ge", 0.0),
    "water_retention":         ("ge", 0.4),
    "disturbance":             ("le", 0.2),
    "waste_factor":            ("le", 0.3),
    "nutrient_density":        ("ge", 0.7),
    "coupling_strength":       ("ge", 0.0),   # informational, no hard floor
    "ecological_amplification": ("ge", 1.0),   # g(k) >= 1 always
}


def _in_spec(value: float, direction: str, limit: float) -> bool:
    if direction == "ge":
        return value >= limit
    return value <= limit


# ---------------------------
# 2. Defect Rate
# ---------------------------

def defect_rate(state: Dict[str, float]) -> Dict[str, Any]:
    """
    Fraction of CTQ variables out of tolerance.
    Returns per-variable pass/fail and aggregate rate.
    """
    s = fill_state(state)
    results = {}
    defects = 0
    total = 0
    for key, (direction, limit) in TOLERANCES.items():
        passed = _in_spec(s[key], direction, limit)
        results[key] = {"value": s[key], "limit": limit, "direction": direction, "pass": passed}
        if not passed:
            defects += 1
        total += 1
    return {
        "details": results,
        "defects": defects,
        "total": total,
        "defect_rate": defects / total if total else 0.0,
    }


# ---------------------------
# 3. Process Capability (Cp analog)
# ---------------------------

def process_capability(state: Dict[str, float]) -> Dict[str, Any]:
    """
    Cp analog: how far each variable sits from its spec limit,
    normalized to the variable's natural range.

    Cp > 1 = comfortably in spec
    Cp ~ 0 = on the edge
    Cp < 0 = out of spec
    """
    s = fill_state(state)
    caps = {}
    for key, (direction, limit) in TOLERANCES.items():
        val = s[key]
        if direction == "ge":
            # margin = how far above the floor
            margin = val - limit
            range_est = max(abs(limit), 1.0)  # avoid /0
        else:
            # margin = how far below the ceiling
            margin = limit - val
            range_est = max(abs(limit), 1.0)
        cp = margin / range_est
        caps[key] = {"value": val, "margin": margin, "cp": round(cp, 3)}
    return caps


# ---------------------------
# 4. Handshake Diagnostic
# ---------------------------

def handshake(text: str = "", state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Combined diagnostic pass:
      - Narrative analysis (delusion counts + plausibility) if text provided
      - Field-system report if state provided
      - System verdict

    This is the single entry point that replaces the prose "Handshake Diagnostic."
    """
    result = {"narrative": None, "field": None, "verdict": "NOMINAL"}
    flags = []

    # --- Narrative leg ---
    if text:
        delusions = dict(extract_delusions(text))
        plausibility = plausibility_score(text)
        total_noise = sum(delusions.values())
        result["narrative"] = {
            "delusion_counts": delusions,
            "plausibility_flags": plausibility,
            "total_noise": total_noise,
        }
        if any(v == 1 for v in plausibility.values()):
            flags.append("PLAUSIBILITY_FAIL")
        if total_noise > 5:
            flags.append("HIGH_NOISE")

    # --- Field leg ---
    if state is not None:
        field_report = report(state)
        dr = defect_rate(state)
        cp = process_capability(state)
        thermal = field_report["thermal_limit"]
        result["field"] = {
            "report": field_report,
            "defect_rate": dr,
            "process_capability": cp,
        }
        if thermal["critical_alert"]:
            flags.append("THERMAL_CRITICAL")
        if dr["defect_rate"] > 0.5:
            flags.append("MAJORITY_OUT_OF_SPEC")
        if field_report["score"] < 0.5:
            flags.append("CONSTRAINT_FAILURE")

    # --- Verdict ---
    if flags:
        result["verdict"] = "ALERT"
    result["flags"] = flags
    return result


# ---------------------------
# 5. Stress Test (Claim Pipeline)
# ---------------------------

def stress_test(claim_text: str, claimed_state: Dict[str, Any],
                label: str = "unnamed") -> Dict[str, Any]:
    """
    Full claim-to-audit pipeline:
      1. Parse narrative for delusions / plausibility
      2. Run field_system report on the claimed state
      3. Compute defect rate and process capability
      4. Return combined verdict

    This replaces the prose "Stress Test" sections.
    """
    diag = handshake(text=claim_text, state=claimed_state)

    # Comparative context: how does this claim stack up vs known scenarios?
    field = diag["field"]
    h_total = field["report"]["yield_analysis"]["total_nourishment_units"]

    benchmarks = {}
    for name in ("big_ag_bot", "sovereign_steward"):
        sc = SCENARIOS[name]
        sc_yield = effective_yield(fill_state(sc["state"]))
        benchmarks[name] = sc_yield["total_nourishment_units"]

    return {
        "label": label,
        "handshake": diag,
        "h_total": h_total,
        "benchmarks": benchmarks,
        "ratio_vs_steward": (h_total / benchmarks["sovereign_steward"]
                             if benchmarks["sovereign_steward"] else 0),
    }


# ---------------------------
# Example Run
# ---------------------------

if __name__ == "__main__":
    from pprint import pprint

    # --- 1. Handshake on clean state ---
    print("=" * 60)
    print("HANDSHAKE: Sovereign Steward (no claim text)")
    print("=" * 60)
    h1 = handshake(state=SCENARIOS["sovereign_steward"]["state"])
    print(f"  Verdict: {h1['verdict']}")
    print(f"  Flags:   {h1['flags']}")
    print(f"  Defect rate: {h1['field']['defect_rate']['defect_rate']:.0%}")
    print(f"  H_total: {h1['field']['report']['yield_analysis']['total_nourishment_units']:.2f}")
    print()

    # --- 2. Stress test: corporate 270% claim ---
    print("=" * 60)
    print("STRESS TEST: Corporate 270% Productivity Claim")
    print("=" * 60)
    claim = (
        "AI-managed precision ag will increase productivity 270% by 2030. "
        "The company will maximize efficiency and shareholder value through "
        "top-down management of scalable soil health products. "
        "Profits always increase with optimization."
    )
    st = stress_test(
        claim_text=claim,
        claimed_state=SCENARIOS["corporate_270"]["state"],
        label="Corporate 270%",
    )
    print(f"  Verdict: {st['handshake']['verdict']}")
    print(f"  Flags:   {st['handshake']['flags']}")
    dr = st["handshake"]["field"]["defect_rate"]
    print(f"  Defect rate: {dr['defect_rate']:.0%} ({dr['defects']}/{dr['total']})")
    print(f"  H_total: {st['h_total']:.2f}")
    print(f"  vs Steward: {st['ratio_vs_steward']:.2f}x")
    print()
    print("  Narrative noise:")
    pprint(st["handshake"]["narrative"], indent=4)
    print()
    print("  Process capability:")
    for k, v in st["handshake"]["field"]["process_capability"].items():
        status = "OK" if v["cp"] >= 0 else "OUT"
        print(f"    {k:28s}  Cp={v['cp']:+.3f}  [{status}]")
