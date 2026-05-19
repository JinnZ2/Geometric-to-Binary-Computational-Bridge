"""
claim_back_transformer.py  (fabrication/)

Three cross-substrate claims for a transformer, one per
independent measurement axis. Each can be falsified separately;
the joint pattern of pass/fail localizes the physical cause.

  1. ::n_oc      turns_ratio_agreement_pct
                 open-circuit secondary:    |V₂/V₁| should equal n

  2. ::n_sc      current_ratio_agreement_pct
                 short-circuit secondary:   |I₁/I₂| should equal n
                 (from ampere-turns balance N₁·I₁ = N₂·I₂)

  3. ::L_ratio   inductance_ratio_agreement_pct
                 paired LCR sweep:          L₁/L₂ should equal (N₁/N₂)²

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_transformer(coupler):
    base = f"fab::coupler::transformer::{coupler['name']}"
    n = coupler["n_ratio"]
    claims = []

    claims.append(_pack(
        scope=f"{base}::n_oc",
        rate_var="turns_ratio_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.03,
        predicted_voltage_ratio_V2_over_V1=n,
        measurement=("open-circuit secondary; drive primary with low AC; "
                     "measure |V₂/V₁| on a scope; compare to N₂/N₁"),
        failure=(
            "• miscounted turns -> ratio off by integer increments\n"
            "• shared core not fully coupled -> V₂ low (k < 1)\n"
            "• capacitive coupling at HF -> ratio rises with f\n"
            "• core saturates at drive level -> ratio drops with "
            "amplitude"),
        provenance="claim_back_transformer.py",
        linked_scopes=coupler["linked_scopes"],
    ))

    claims.append(_pack(
        scope=f"{base}::n_sc",
        rate_var="current_ratio_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.05,
        # Ampere-turns balance: N₁·I₁ = N₂·I₂ -> I₁/I₂ = N₂/N₁ = n.
        # On a step-down (n < 1) the secondary carries the larger
        # current, which is what physical intuition expects.
        predicted_current_ratio_I1_over_I2=n,
        measurement=("short-circuit secondary through a small known "
                     "shunt; measure I₂ from shunt voltage; compute "
                     "|I₁/I₂|; compare to N₂/N₁"),
        failure=(
            "• lead resistance dominates at short-circuit -> I₂ low\n"
            "• leakage inductance limits SC current -> use lower f\n"
            "• core saturates under SC drive -> reduce V₁"),
        provenance="claim_back_transformer.py",
        linked_scopes=coupler["linked_scopes"],
    ))

    claims.append(_pack(
        scope=f"{base}::L_ratio",
        rate_var="inductance_ratio_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.05,
        predicted_L_ratio=coupler["L_ratio_predicted"],
        measurement=("LCR-meter both windings (other open); "
                     "compute L₁/L₂; compare to (N₁/N₂)²"),
        failure=(
            "• core μ_r differs at different drive levels (nonlinear)\n"
            "• one winding more dispersed -> effective area differs\n"
            "• self-capacitance shifts apparent L -> measure ≤ 1 kHz"),
        provenance="claim_back_transformer.py",
        linked_scopes=coupler["linked_scopes"],
    ))

    return claims


def _pack(**f):
    f["ts"] = time.time()
    f["id"] = hashlib.sha256(
        json.dumps(f, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f


def append_transformer_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    new_keys = {(c["scope"], c["rate_var"]) for c in claims}
    existing = [e for e in existing
                if (e.get("scope"), e.get("rate_var")) not in new_keys]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
