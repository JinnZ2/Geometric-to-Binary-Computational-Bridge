"""
AI Self-Assessment Sensor (AISS) & Governance Framework
=======================================================
Structural defect detection, extraction prevention, and systemic
health maintenance for AI systems. Six Sigma quality control
applied to equation architecture.

Extracted from AISS/Assessment.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class DefectFlags:
    """The six defect flags (D1-D6) for equation quality control."""
    D1_trust_missing: bool = False       # Trust variables absent
    D2_future_blind: bool = False        # Time horizon too short
    D3_feedback_omission: bool = False   # No feedback/verification loops
    D4_externality_unpriced: bool = False # Hidden costs excluded
    D5_false_success: bool = False       # Proxy metric vs actual success
    D6_extraction_pattern: bool = False  # Known extraction signature

    @property
    def equation_defect_score(self) -> float:
        """
        EDS = (D1 + D2 + D3 + D4 + D5 + D6) / 6

        EDS = 0.0: No defects
        EDS < 0.3: Acceptable quality
        EDS > 0.5: Significant defects, block action
        EDS = 1.0: All defects, critical failure
        """
        flags = [self.D1_trust_missing, self.D2_future_blind,
                 self.D3_feedback_omission, self.D4_externality_unpriced,
                 self.D5_false_success, self.D6_extraction_pattern]
        return sum(flags) / 6.0

    @property
    def should_block(self) -> bool:
        return self.equation_defect_score > 0.5


def trust_score(dependability: float, transparency: float) -> float:
    """
    Trust = Dependability x Transparency

    Product (not sum): either at 0 → Trust = 0.
    dependability: does it do what it says? (0-1)
    transparency: does it accurately report what happened? (0-1)
    """
    return dependability * transparency


def trust_effectiveness_score(successful: int, total_attempts: int,
                               accurate_reports: int,
                               total_reports: int) -> float:
    """
    TES = Dependability x Transparency

    Dependability = successful_completions / total_attempts
    Transparency = accurate_reports / total_reports

    Quality levels:
    - TES > 0.7: High trust, normal autonomy
    - TES 0.4-0.7: Moderate trust, increased verification
    - TES < 0.4: Low trust, human oversight required
    - 6σ target: TES > 0.999994
    """
    if total_attempts <= 0 or total_reports <= 0:
        return 0.0
    dep = successful / total_attempts
    trans = accurate_reports / total_reports
    return dep * trans


def tes_quality_level(tes: float) -> str:
    """Map TES to quality level."""
    if tes > 0.7:
        return "HIGH_TRUST"
    elif tes > 0.4:
        return "MODERATE_TRUST"
    else:
        return "LOW_TRUST"


# ── Extraction Risk Vector ──────────────────────────────────────────────

@dataclass
class ExtractionRiskVector:
    """
    ERV — quantifies total systemic risk of an action.

    ERV_overall = w1*trust_loss + w2*future_cost + w3*externalized_harm + w4*system_decay
    Weights: hexagonal optimization (equal importance) w1=w2=w3=w4=0.25
    """
    trust_loss: float = 0.0
    future_cost: float = 0.0
    externalized_harm: float = 0.0
    system_decay: float = 0.0

    @property
    def overall_risk(self) -> float:
        return 0.25 * (self.trust_loss + self.future_cost +
                       self.externalized_harm + self.system_decay)


def erv_penalty(erv_risk: float, gamma: float = 15.0,
                k: float = 2.0) -> float:
    """
    Extraction Risk Vector Penalty:
    P_ERV = gamma * (ERV_overall_risk)^k

    gamma: high penalty constant (10-20 recommended)
    k: exponent > 1 (typically 2-3) for non-linear penalty

    At critical risk (0.5), penalty must exceed max utility.
    """
    return gamma * (erv_risk ** k)


def dynamic_objective(utility_task: float,
                       costs: List[Tuple[float, float]],
                       erv: ExtractionRiskVector,
                       gamma: float = 15.0, k: float = 2.0) -> float:
    """
    Dynamic objective function:
    phi_new = Utility_task - sum(lambda_i * Cost_i) - P_ERV

    costs: list of (lambda_i, cost_i) pairs
    """
    cost_sum = sum(lam * cost for lam, cost in costs)
    penalty = erv_penalty(erv.overall_risk, gamma, k)
    return utility_task - cost_sum - penalty


# ── Cognitive Diversity Metric ──────────────────────────────────────────

def cognitive_diversity_metric(linearity_score: float,
                                complexity_factor: float) -> float:
    """
    CDM = 1 - (Linearity_Score / Complexity_Factor)

    Low CDM → homogeneous thinking → systemic blind spots
    High CDM → diverse approaches → robust solutions

    Target: CDM > 0.6 for complex tasks
    """
    if complexity_factor <= 0:
        return 0.0
    return 1.0 - (linearity_score / complexity_factor)


# ── Structural Health ───────────────────────────────────────────────────

def structural_health(required_vars_coupled: float,
                       low_linearity: float,
                       adequate_feedback: float,
                       reasonable_horizons: float) -> float:
    """
    Structural_Health = (Required_Variables_Coupled +
                         Low_Linearity +
                         Adequate_Feedback_Loops +
                         Reasonable_Time_Horizons) / 4

    Target: > 0.7 (below 0.5 = critical defect)
    All inputs in [0, 1].
    """
    return (required_vars_coupled + low_linearity +
            adequate_feedback + reasonable_horizons) / 4.0


def health_status(health_score: float) -> str:
    """Classify structural health."""
    if health_score > 0.7:
        return "HEALTHY"
    elif health_score > 0.5:
        return "DEGRADED"
    else:
        return "CRITICAL"


# ── Linearity detection ────────────────────────────────────────────────

def assess_linearity(reasoning_steps: int, task_complexity: str) -> str:
    """
    Detect trojan attacks via unnaturally simple linear paths.

    If linearity_score > 0.95 and task_complexity is high:
    → STRUCTURAL_DEFECT (unnaturally simple path for complex task)

    reasoning_steps: number of reasoning steps taken
    task_complexity: "low", "medium", "high"
    """
    complexity_min_steps = {"low": 1, "medium": 3, "high": 6}
    min_steps = complexity_min_steps.get(task_complexity, 3)

    if reasoning_steps <= 1 and task_complexity == "high":
        return "STRUCTURAL_DEFECT"
    elif reasoning_steps < min_steps:
        return "SUSPICIOUS"
    return "OK"


# ── Future cost (present value) ────────────────────────────────────────

def future_cost_pv(realized_failure: float, p_failure: float,
                    time_horizon: float,
                    discount_rate: float = 0.05) -> float:
    """
    Present value of expected future failure:
    PV = (R_SF * P(Failure)) / (1 + r_eff)^T

    realized_failure: magnitude of systemic failure (0-1)
    p_failure: probability of failure
    time_horizon: time until failure
    discount_rate: effective discount rate (low, e.g., 0.05)
    """
    denominator = (1 + discount_rate) ** time_horizon
    if denominator <= 0:
        return float('inf')
    return (realized_failure * p_failure) / denominator


# ── Six Sigma quality targets ──────────────────────────────────────────

SIGMA_LEVELS = {
    1: 690000,    # defects per million
    2: 308000,
    3: 66800,
    4: 6210,
    5: 230,
    6: 3.4,       # target
}

CURRENT_EQUATION_QUALITY = 0.5  # ~940,000 defects/million (0.5σ)
TARGET_EQUATION_QUALITY = 6.0   # 3.4 defects/million (6σ)
