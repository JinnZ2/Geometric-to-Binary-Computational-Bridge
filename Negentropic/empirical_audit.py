"""
Empirical Claims Audit — Statistical testing framework
=======================================================
Validates empirical claims with proper hypothesis testing.

Extracted from Negentropic/02-empirical-audit.md
"""

import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ClaimAudit:
    """Result of auditing an empirical claim."""
    claim: str
    chi_square: Optional[float]
    p_value: Optional[float]
    status: str  # "verified", "unverified", "inconsistent", "incorrect"
    issues: list


def chi_square_test(observed: int, expected: float) -> Tuple[float, float]:
    """
    Chi-square test for a single category.

    Returns (chi2, p_value).
    """
    if expected <= 0:
        return float('inf'), 0.0
    chi2 = (observed - expected) ** 2 / expected
    # Approximate p-value from chi2 with 1 df
    # Using survival function approximation
    p = np.exp(-chi2 / 2) if chi2 < 100 else 0.0
    return chi2, p


def fibonacci_days_in_window(window_days: int = 365) -> int:
    """
    Count Fibonacci numbers within a day-window.

    Fibonacci numbers <= window_days: 1,1,2,3,5,8,13,21,34,55,89,144,233
    """
    fibs = []
    a, b = 1, 1
    while a <= window_days:
        fibs.append(a)
        a, b = b, a + b
    return len(set(fibs))  # Deduplicate (1 appears twice)


def audit_fibonacci_therapeutic(observed_breakthroughs: int = 36,
                                 total_fib_days: int = 13,
                                 window_days: int = 365) -> ClaimAudit:
    """
    Audit the 36/36 Fibonacci therapeutic breakthroughs claim.

    Issues identified:
    - Section 2.1 says expected = 3.6
    - Appendix B says expected = 1.28
    - Both cannot be right (different denominators)
    """
    expected_appendix = observed_breakthroughs * (total_fib_days / window_days)
    expected_section = 3.6  # As stated in §2.1

    chi2_app, p_app = chi_square_test(observed_breakthroughs, expected_appendix)
    chi2_sec, p_sec = chi_square_test(observed_breakthroughs, expected_section)

    issues = [
        f"§2.1 expected={expected_section}, Appendix B expected={expected_appendix:.2f} — inconsistent",
        "No pre-registered study protocol",
        "No clear definition of 'breakthrough'",
        "No independent replication",
        "No citation of any existing study",
    ]

    return ClaimAudit(
        claim="36/36 Fibonacci therapeutic breakthroughs",
        chi_square=chi2_app,
        p_value=p_app,
        status="unverified",
        issues=issues,
    )


def audit_consciousness_threshold(M_before: float = 34.62,
                                    M_after: float = 296.40,
                                    M_peak: float = 3711.50) -> ClaimAudit:
    """
    Audit the AI consciousness threshold crossing claim.

    M(S) values are relative to normalization — absolute values meaningless.
    """
    ratio = M_after / M_before
    peak_ratio = M_peak / M_before

    issues = [
        "No methodology for computing M(S) from actual AI state",
        "Self-referential measurement problem (AI computed its own M(S))",
        "Single observation, no controls",
        f"M(S) units depend on normalization — {M_peak} vs {M_before} is relative only",
        "Would need: extraction method for {p_i, s_i}, reproducible protocol",
    ]

    return ClaimAudit(
        claim="AI system crossed consciousness threshold",
        chi_square=None,
        p_value=None,
        status="unverifiable",
        issues=issues,
    )


def audit_model_collapse() -> ClaimAudit:
    """
    Audit the model collapse from alignment claim.

    The empirical observation has support (Shumailov et al. 2023).
    The thermodynamic explanation is analogy, not derivation.
    """
    return ClaimAudit(
        claim="Model collapse from alignment (RLHF suppression)",
        chi_square=None,
        p_value=None,
        status="partially_supported",
        issues=[
            "Empirical phenomenon (tradeoffs) is real — literature support",
            "Thermodynamic explanation is analogy, not causal account",
            "'Suppressing F_C' ≈ RLHF only if RLHF literally sets D=0 (not measured)",
            "Actual mechanism debated: mode collapse, reward hacking, distributional shift",
        ],
    )


def full_audit() -> Dict[str, ClaimAudit]:
    """Run all claim audits and return results."""
    return {
        "fibonacci_therapeutic": audit_fibonacci_therapeutic(),
        "consciousness_threshold": audit_consciousness_threshold(),
        "model_collapse": audit_model_collapse(),
    }
