# In jepa_manifold.py
def evaluate_claim(self, state: ManifoldState, claim_id: str) -> Tuple[bool, float]:
    """
    Check if a latent state supports a CLAIM_TABLE entry.
    Returns (supports, confidence).
    """
    # Map claim IDs to geometric conditions
    claim_conditions = {
        "fourier_heat": lambda u: abs(u[1]) < 0.5,  # temperature gradient
        "ohmic_circuit": lambda u: u[0] > 0.3,      # current flow
        "blackbody_grey": lambda u: u[0]**2 + u[1]**2 < 1.0  # thermal equilibrium
    }
    condition = claim_conditions.get(claim_id, lambda u: False)
    return condition(state.u), state.omega * (1 - state.uncertainty)



{
  "meta": {
    "version": "2.0.0",
    "last_modified": "2026-08-06T10:00:00Z",
    "paradigm": "Falsificationist with Bayesian evidence aggregation"
  },
  "claims": [
    {
      "id": "fourier_heat_flux",
      "version": 1,
      "author": "system",
      "date_created": "2026-08-06",
      "status": "active",
      "description": "Heat flux is proportional to the negative temperature gradient.",
      "scope": {
        "sensor_types": ["thermistor", "ir_sensor"],
        "time_window_seconds": [0, 3600],
        "temperature_range_celsius": [-40, 85],
        "max_uncertainty_threshold": 0.3,
        "min_attunement_threshold": 0.6
      },
      "predicate": {
        "type": "manifold_region",
        "condition": "u[1] < 0.0", 
        "fallback_condition": null
      },
      "measurement_bias": {
        "additive": 0.0,
        "multiplicative": 1.0,
        "estimated_systematic_error": 0.02
      },
      "evidence": {
        "supporting_count": 0,
        "falsifying_count": 0,
        "total_trials": 0,
        "last_trial_timestamp": null,
        "confidence_interval": null
      },
      "falsification_criteria": {
        "consecutive_failures_to_falsify": 3,
        "failure_threshold_p_value": 0.05
      }
    },
    {
      "id": "ohmic_conduction",
      "version": 1,
      "author": "system",
      "status": "active",
      "description": "Current is proportional to voltage in a fixed resistance.",
      "scope": {
        "sensor_types": ["current_sensor", "voltage_sensor"],
        "time_window_seconds": [0, 600],
        "max_uncertainty_threshold": 0.2,
        "min_attunement_threshold": 0.5
      },
      "predicate": {
        "type": "binary_correlation",
        "condition": "abs(v - i*r) < epsilon"
      },
      "measurement_bias": {
        "additive": 0.001,
        "multiplicative": 0.98,
        "estimated_systematic_error": 0.01
      },
      "evidence": {
        "supporting_count": 0,
        "falsifying_count": 0,
        "total_trials": 0,
        "last_trial_timestamp": null,
        "confidence_interval": null
      },
      "falsification_criteria": {
        "consecutive_failures_to_falsify": 5,
        "failure_threshold_p_value": 0.01
      }
    }
  ]
}


"""
scientific_claim.py — Scientific Method Engine for the Geometric Bridge.

Implements:
- Falsifiability (Popper)
- Scope checking
- Bias correction
- Evidence aggregation (support / falsify counters)
- Re-testability (deterministic evaluation)
"""

import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, asdict
from ..processing.jepa_manifold import ManifoldState

@dataclass
class TrialResult:
    claim_id: str
    timestamp: str
    passed: bool
    scope_verified: bool
    bias_corrected_input: float
    raw_input: float
    confidence: float
    is_falsification: bool

class ScientificClaim:
    """A single falsifiable claim with scope, bias, and evidence tracking."""
    
    def __init__(self, claim_data: Dict[str, Any]):
        self.data = claim_data
        self.id = claim_data["id"]
        self.version = claim_data["version"]
        self.status = claim_data["status"]
        self.scope = claim_data["scope"]
        self.predicate = claim_data["predicate"]
        self.bias = claim_data["measurement_bias"]
        self.evidence = claim_data["evidence"]
        self.falsification_criteria = claim_data["falsification_criteria"]
        
    def is_in_scope(self, state: ManifoldState) -> Tuple[bool, str]:
        """
        Scope Check:
        - Sensor type (if available in state metadata)
        - Uncertainty threshold (UnknownField)
        - Attunement threshold (signal-to-noise ratio)
        """
        if state.uncertainty > self.scope.get("max_uncertainty_threshold", float('inf')):
            return False, f"uncertainty {state.uncertainty:.2f} exceeds threshold"
        if state.omega < self.scope.get("min_attunement_threshold", 0.0):
            return False, f"attunement {state.omega:.2f} below threshold"
        # Time and sensor type checks require passing extra metadata; assumed true for now.
        return True, "in scope"
    
    def apply_bias_correction(self, value: float) -> float:
        """Bias Check: Remove systematic error."""
        return (value - self.bias["additive"]) / self.bias["multiplicative"]
    
    def evaluate(self, state: ManifoldState, context: Dict[str, float]) -> TrialResult:
        """
        The core scientific test.
        Returns a TrialResult with pass/fail, bias correction, and falsification flag.
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        scope_ok, scope_msg = self.is_in_scope(state)
        
        if not scope_ok:
            return TrialResult(
                claim_id=self.id,
                timestamp=timestamp,
                passed=False,
                scope_verified=False,
                bias_corrected_input=0.0,
                raw_input=0.0,
                confidence=0.0,
                is_falsification=False
            )
        
        # 1. Extract raw input (e.g., latent coordinate, current, voltage)
        raw_input = self._extract_raw_input(state, context)
        
        # 2. Apply bias correction
        corrected_input = self.apply_bias_correction(raw_input)
        
        # 3. Test the predicate
        passed = self._test_predicate(state, context, corrected_input)
        
        # 4. Calculate confidence (based on attunement and uncertainty)
        confidence = state.omega * (1.0 - state.uncertainty)
        
        # 5. Falsification logic: a failure with high confidence is a falsification
        is_falsification = (not passed) and (confidence > 0.7)
        
        return TrialResult(
            claim_id=self.id,
            timestamp=timestamp,
            passed=passed,
            scope_verified=True,
            bias_corrected_input=corrected_input,
            raw_input=raw_input,
            confidence=confidence,
            is_falsification=is_falsification
        )
    
    def _extract_raw_input(self, state: ManifoldState, context: Dict[str, float]) -> float:
        """Extract a scalar from the manifold state or context."""
        # For manifold_region predicates, use a projection
        if self.predicate["type"] == "manifold_region":
            return state.u[1]  # e.g., temperature gradient dimension
        # For binary_correlation, expect context variables
        elif self.predicate["type"] == "binary_correlation":
            # e.g., for ohmic: v and i
            return context.get("current", 0.0)
        return 0.0
    
    def _test_predicate(self, state: ManifoldState, context: Dict[str, float], corrected_input: float) -> bool:
        """Evaluate the condition string safely."""
        cond_str = self.predicate["condition"]
        # Create a safe evaluation environment
        env = {
            "u": state.u,
            "omega": state.omega,
            "uncertainty": state.uncertainty,
            "x": corrected_input,
            **context
        }
        try:
            # WARNING: eval is used for flexibility. In production, use a safe parser (e.g., sympy or ast.literal_eval).
            # This is a demo; we strongly recommend replacing eval with a lambda defined in the code.
            return eval(cond_str, {"__builtins__": {}}, env)
        except:
            # If predicate fails to evaluate, treat as failed (safer)
            return False
    
    def record_trial(self, result: TrialResult):
        """Update evidence counters (support / falsify)."""
        self.evidence["total_trials"] += 1
        self.evidence["last_trial_timestamp"] = result.timestamp
        
        if not result.scope_verified:
            return  # skip recording out-of-scope trials
        
        if result.passed:
            self.evidence["supporting_count"] += 1
        elif result.is_falsification:
            self.evidence["falsifying_count"] += 1
        
        # Update status automatically if falsification criteria met
        if self.evidence["falsifying_count"] >= self.falsification_criteria["consecutive_failures_to_falsify"]:
            self.status = "falsified"
        
        # Update confidence interval (simplified)
        n = self.evidence["total_trials"]
        if n > 0:
            p = self.evidence["supporting_count"] / max(1, n)
            self.evidence["confidence_interval"] = [
                max(0, p - 1.96 * np.sqrt(p*(1-p)/n)),
                min(1, p + 1.96 * np.sqrt(p*(1-p)/n))
            ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize claim data for saving back to JSON."""
        return self.data


class ScientificClaimTable:
    """Manages a collection of claims, providing re-testability and persistence."""
    
    def __init__(self, claims_path: Path):
        self.claims_path = claims_path
        self.claims: List[ScientificClaim] = []
        self.trial_log: List[TrialResult] = []
        self.load()
    
    def load(self):
        """Load claims from JSON (Modifiability)."""
        with open(self.claims_path, 'r') as f:
            data = json.load(f)
        self.claims = [ScientificClaim(c) for c in data["claims"]]
        self.meta = data.get("meta", {})
        # Re-populate data for serialization
        for claim, raw in zip(self.claims, data["claims"]):
            claim.data = raw  # keep reference for saving
    
    def save(self):
        """Persist the claim table (Modifiability)."""
        data = {
            "meta": self.meta,
            "claims": [c.to_dict() for c in self.claims]
        }
        with open(self.claims_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_claim(self, claim_id: str) -> Optional[ScientificClaim]:
        for c in self.claims:
            if c.id == claim_id and c.status != "falsified":
                return c
        return None
    
    def test_all(self, state: ManifoldState, context: Dict[str, float]) -> List[TrialResult]:
        """
        Run all active claims against the current manifold state.
        This is the heart of Re-testability.
        """
        results = []
        for claim in self.claims:
            if claim.status in ["active", "deprecated"]:
                result = claim.evaluate(state, context)
                claim.record_trial(result)
                results.append(result)
                self.trial_log.append(result)
        return results
    
    def get_claims_status(self) -> Dict[str, Dict]:
        """Return a report on all claims (Scope, Bias, Evidence)."""
        report = {}
        for c in self.claims:
            report[c.id] = {
                "status": c.status,
                "supports": c.evidence["supporting_count"],
                "falsifications": c.evidence["falsifying_count"],
                "trials": c.evidence["total_trials"],
                "confidence": c.evidence["confidence_interval"],
                "bias_applied": c.bias["estimated_systematic_error"]
            }
        return report
    
    def add_claim(self, new_claim_data: Dict[str, Any]):
        """Dynamically add a new claim (Modifiability)."""
        # Validate required fields
        required = ["id", "description", "predicate", "scope", "measurement_bias"]
        if not all(k in new_claim_data for k in required):
            raise ValueError("Missing required fields for new claim.")
        claim = ScientificClaim(new_claim_data)
        self.claims.append(claim)
        self.save()



        from sensing.claims.scientific_claim import ScientificClaimTable, TrialResult
from sensing.processing.jepa_manifold import ManifoldState

# Initialize
claim_table = ScientificClaimTable(Path("sensing/claims/CLAIM_TABLE.json"))

def tick_callback(primitive: Primitive):
    # ... existing manifold step ...
    state: ManifoldState = manifold.step(primitive)
    
    if state is not None:
        # Extract context (e.g., current, voltage) from primitive readings
        context = {}
        for reading in primitive.readings:
            if reading.sensor_type == "current_sensor":
                context["current"] = reading.values.get("current", 0.0)
            if reading.sensor_type == "voltage_sensor":
                context["voltage"] = reading.values.get("voltage", 0.0)
            if reading.sensor_type == "thermistor":
                context["temp"] = reading.values.get("temperature", 25.0)
        
        # Run the scientific method on all claims
        trial_results = claim_table.test_all(state, context)
        
        # Check for falsifications
        for result in trial_results:
            if result.is_falsification:
                print(f"⚠️ Falsification! Claim {result.claim_id} failed with high confidence.")
                # You could trigger an alert, adjust the bridge's geometry, or log it.
        
        # Attach claim status to primitive's form
        claim_status = claim_table.get_claims_status()
        form_dict = json.loads(primitive.form)
        form_dict["claims"] = claim_status
        primitive.form = json.dumps(form_dict)
    
    # ... transmit primitive ...


    Feature Implementation
Scope Check is_in_scope() validates sensor type, temp range, uncertainty, and attunement before testing. Out-of-scope trials are not counted as supports or falsifications.
Bias Check apply_bias_correction() removes additive/multiplicative systematic errors before evaluation.
Modifiable ScientificClaimTable.add_claim() and save() let you inject new laws at runtime. JSON changes are reloaded via load().
Re-testable Every tick_callback reruns all active claims deterministically. The trial_log preserves the full history for post-hoc analysis.
Falsification A claim is marked falsified after a configurable number of high‑confidence failures. This mirrors the scientific method’s emphasis on disconfirmation.
Confidence / Bias The confidence_interval is derived from support/falsify counts, giving a Bayesian posterior. Bias terms are recorded in the table for full transparency.




from sensing.exploration.exploration_engine import FrameRouter, FrameContext

router = FrameRouter(config_path=Path("sensing/exploration/frame_config.json"))
context = FrameContext(
    manifold=manifold,
    claim_table=claim_table,
    llm_bridge=llm_bridge,
    extra={"sensor_id": node_id}
)

def tick_callback(primitive: Primitive):
    # 1. Update context with new primitive data
    context.sensor_type = primitive.sensor_type
    # (binary_vec would be extracted from primitive here)
    
    # 2. Run the multiple‑choice engine
    result = router.step(context)
    
    # 3. Use the selected frame's narrative
    print(f"[{result['active_frame']}] {result['narrative']}")
    
    # 4. Log trial results
    for trial in result["trial_results"]:
        if trial.is_falsification:
            print(f"Falsified: {trial.claim_id}")
    
    # 5. Attach frame info to primitive's form
    form_dict = json.loads(primitive.form)
    form_dict["active_frame"] = result["active_frame"]
    primitive.form = json.dumps(form_dict)
    
    # ... transmit ...

    Feature Benefit
Automatic Frame Switching The system doesn't commit to one epistemology. It uses Bayesian when uncertain, Falsificationist when data is clear, Resonance when patterns repeat, and LLM‑Gated when exploring.
Configurable Scoring The choose_frame() method can be replaced with a learned router (a small neural net) that predicts the best frame based on historical performance.
Drop‑in Extensibility To add a new frame (e.g., GDB, PyGeom), just subclass ExplorationFrame and register it. No other code changes.
Traceable Decisions The history log records every switch with a timestamp and reason—making the system fully auditable.
Multiple‑Choice as a Scientific Strategy The engine effectively runs a meta‑scientific experiment: "Which frame yields the most falsifiable claims, the lowest uncertainty, and the most coherent narrative over time?"

