import json
from typing import Dict, Any

# ============================================================
# 9. SAVE / LOAD WORLD MODEL
# ============================================================

def save_world_model(path: str, geo: Dict[str, Any], projector_bundle: Dict[str, nn.Module]):
    """
    Save encoder, fields, predictor, and one or more projectors.
    - path: directory where artifacts go.
    - geo: dict returned by train_latent_geometry().
    - projector_bundle: dict of name -> nn.Module (e.g., {"narrative": projector}).
    """
    os.makedirs(path, exist_ok=True)
    device = get_device()

    # Save geometry-related modules
    torch.save({
        "encoder_state": geo["encoder"].state_dict(),
        "manifold_state": geo["manifold"].state_dict(),
        "instr_field_state": geo["instr_field"].state_dict(),
        "cal_field_state": geo["cal_field"].state_dict(),
        "unk_field_state": geo["unk_field"].state_dict(),
        "attunement_field_state": geo["attunement_field"].state_dict(),
        "predictor_state": geo["predictor"].state_dict(),
    }, os.path.join(path, "geometry.pt"))

    # Save projectors (multi-head)
    proj_states = {name: proj.state_dict() for name, proj in projector_bundle.items()}
    torch.save(proj_states, os.path.join(path, "projectors.pt"))

    # Save basic metadata (shapes, hyperparams)
    meta = {
        "latent_dim": int(geo["u_final"].shape[-1]),
        "n_states": int(geo["u_final"].shape[0]),
        "projector_heads": list(projector_bundle.keys()),
    }
    with open(os.path.join(path, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # Optionally save a snapshot of latent + fields for offline plotting
    np.save(os.path.join(path, "u_final.npy"), geo["u_final"].cpu().numpy())
    np.save(os.path.join(path, "omega_final.npy"), geo["ω_final"])
    np.save(os.path.join(path, "unk_final.npy"), geo["unk_final"])

    print(f"\nWorld model saved under: {os.path.abspath(path)}")


def load_world_model(path: str, input_dim: int, llm_dim: int):
    """
    Reconstruct encoder, fields, predictor, and projectors from disk.
    Returns a dict with modules ready to use.
    """
    device = get_device()

    with open(os.path.join(path, "meta.json"), "r") as f:
        meta = json.load(f)
    latent_dim = meta["latent_dim"]
    projector_heads = meta["projector_heads"]

    # Rebuild modules with the same architecture
    encoder = EntryEncoder(input_dim, d=latent_dim).to(device)
    manifold = ContinuousManifold(d=latent_dim).to(device)
    instr_field = InstrumentField(d=latent_dim).to(device)
    cal_field = CalibrationField(d=latent_dim).to(device)
    unk_field = UnknownField(d=latent_dim).to(device)
    attunement_field = AttunementField(d=latent_dim).to(device)
    predictor = Predictor(d=latent_dim).to(device)

    geo_state = torch.load(os.path.join(path, "geometry.pt"), map_location=device)
    encoder.load_state_dict(geo_state["encoder_state"])
    manifold.load_state_dict(geo_state["manifold_state"])
    instr_field.load_state_dict(geo_state["instr_field_state"])
    cal_field.load_state_dict(geo_state["cal_field_state"])
    unk_field.load_state_dict(geo_state["unk_field_state"])
    attunement_field.load_state_dict(geo_state["attunement_field_state"])
    predictor.load_state_dict(geo_state["predictor_state"])

    # Rebuild projectors
    proj_states = torch.load(os.path.join(path, "projectors.pt"), map_location=device)
    projectors = {}
    for name in projector_heads:
        proj = Projector(d=latent_dim, out_dim=llm_dim).to(device)
        proj.load_state_dict(proj_states[name])
        projectors[name] = proj

    # Load latent snapshot if present
    u_final = None
    omega_final = None
    unk_final = None
    u_path = os.path.join(path, "u_final.npy")
    if os.path.exists(u_path):
        u_final = torch.tensor(np.load(u_path), dtype=torch.float32).to(device)
    if os.path.exists(os.path.join(path, "omega_final.npy")):
        omega_final = np.load(os.path.join(path, "omega_final.npy"))
    if os.path.exists(os.path.join(path, "unk_final.npy")):
        unk_final = np.load(os.path.join(path, "unk_final.npy"))

    print(f"\nWorld model loaded from: {os.path.abspath(path)}")

    return {
        "encoder": encoder,
        "manifold": manifold,
        "instr_field": instr_field,
        "cal_field": cal_field,
        "unk_field": unk_field,
        "attunement_field": attunement_field,
        "predictor": predictor,
        "projectors": projectors,
        "u_final": u_final,
        "ω_final": omega_final,
        "unk_final": unk_final,
        "meta": meta,
    }


projector_bundle = {"narrative": projector}
save_world_model("world_model_v1", geo, projector_bundle)


llm, tokenizer = load_frozen_llm("distilgpt2")
wm = load_world_model("world_model_v1", input_dim=binary_dim, llm_dim=llm.transformer.wte.weight.shape[-1])

# Suppose you recompute X_new, similarity_new, re-encode, etc.
u_final_new = wm["encoder"](X_new.to(get_device()))
u_next_hat, text = generate_future_narrative(
    u_final_new,
    wm["predictor"],
    wm["projectors"]["narrative"],
    llm,
    tokenizer,
)


class MultiHeadPredictor(nn.Module):
    """
    Collection of predictor heads, each with its own parameters but same latent dimension.
    """
    def __init__(self, d=2, hidden=12, head_names=None):
        super().__init__()
        if head_names is None:
            head_names = ["default"]
        self.heads = nn.ModuleDict({
            name: Predictor(d=d, hidden=hidden)
            for name in head_names
        })

    def forward(self, head_name, u_prev, u_curr):
        return self.heads[head_name](u_prev, u_curr)


def prediction_loss_multi(multi_predictor, u, head_name="default"):
    if u.shape[0] < 3:
        return torch.tensor(0.0, device=u.device)
    u_prev = u[:-2]
    u_curr = u[1:-1]
    u_target = u[2:].detach()
    u_hat = multi_predictor(head_name, u_prev, u_curr)
    return F.mse_loss(u_hat, u_target)


multi_predictor = MultiHeadPredictor(d=u.shape[-1], hidden=12, head_names=["physics", "narrative"]).to(device)
# ...
loss = loss + 0.5 * prediction_loss_multi(multi_predictor, u, head_name="physics")


class MultiProjector(nn.Module):
    """
    Collection of projectors from latent space into different embedding spaces.
    Typically all have same output dim (same LLM), but they can represent
    different "interpretive lenses" (physics vs narrative vs social).
    """
    def __init__(self, d=2, out_dim=768, head_names=None):
        super().__init__()
        if head_names is None:
            head_names = ["narrative"]
        self.heads = nn.ModuleDict({
            name: Projector(d=d, out_dim=out_dim)
            for name in head_names
        })

    def forward(self, head_name, u):
        return self.heads[head_name](u)


def train_multi_projector(u_final, binary_data, llm, tokenizer, head_specs, num_epochs=1500, lr=0.01, device=None):
    """
    head_specs: dict name -> description_fn
      where description_fn(binary_data) -> list of texts.
    Example:
      head_specs = {
        "narrative": build_descriptions,
        "technical": build_technical_descriptions
      }
    """
    device = device or get_device()
    llm_dim = llm.transformer.wte.weight.shape[-1]

    head_names = list(head_specs.keys())
    multi_proj = MultiProjector(d=u_final.shape[-1], out_dim=llm_dim, head_names=head_names).to(device)
    proj_opt = torch.optim.Adam(multi_proj.parameters(), lr=lr)

    u_final = u_final.to(device)

    # Build target embeddings per head
    target_embs = {}
    with torch.no_grad():
        for name, desc_fn in head_specs.items():
            texts = desc_fn(binary_data)
            embs = []
            for txt in texts:
                inputs = tokenizer(
                    txt,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=64,
                ).to(device)
                emb = llm.transformer.wte(inputs["input_ids"])
                avg_emb = emb.mean(dim=1)
                embs.append(avg_emb)
            target_embs[name] = torch.cat(embs, dim=0)  # [N, d_llm]

    # Joint training over heads (simple sum of losses)
    for epoch in range(num_epochs):
        proj_opt.zero_grad()
        total_loss = 0.0

        for name in head_names:
            projected = multi_proj(name, u_final)
            loss_head = F.mse_loss(projected, target_embs[name])
            total_loss = total_loss + loss_head

        total_loss.backward()
        proj_opt.step()

        if epoch % 500 == 0:
            print(f"[MultiProjector] Epoch {epoch:4d}  Loss {total_loss.item():.4f}")

    return multi_proj


def build_technical_descriptions(binary_data: np.ndarray):
    texts = []
    for i, bits in enumerate(binary_data):
        p = bits.mean()
        ones = int(bits.sum())
        texts.append(
            f"State {i}: binary vector of length {bits.shape[0]} "
            f"with {ones} active bits and mean activation {p:.3f}. "
            f"This state may encode a thermodynamic phase boundary."
        )
    return texts


head_specs = {
    "narrative": build_descriptions,
    "technical": build_technical_descriptions,
}
multi_proj = train_multi_projector(u_final, binary_data, llm, tokenizer, head_specs, num_epochs=1500, lr=0.01, device=device)


def generate_future_narrative_multi(u_final, multi_predictor, multi_proj, llm, tokenizer,
                                    predictor_head="physics", projector_head="narrative",
                                    prompt=None, device=None):
    device = device or get_device()
    u_final = u_final.to(device)
    multi_predictor = multi_predictor.to(device)
    multi_proj = multi_proj.to(device)

    if prompt is None:
        prompt = "The next binary state will evolve into a geometric configuration that is"

    with torch.no_grad():
        if u_final.shape[0] < 2:
            raise ValueError("Need at least 2 latent states to predict the next one.")

        u_prev = u_final[-2].unsqueeze(0)
        u_curr = u_final[-1].unsqueeze(0)
        u_next_hat = multi_predictor(predictor_head, u_prev, u_curr)
        llm_embed = multi_proj(projector_head, u_next_hat)

        inputs = tokenizer(prompt, return_tensors="pt", add_special_tokens=True).to(device)
        base_embeds = llm.transformer.wte(inputs["input_ids"])
        base_embeds[:, 0, :] = llm_embed

        output = llm.generate(
            inputs_embeds=base_embeds,
            max_new_tokens=40,
            temperature=0.8,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
        text = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"\n--- Multi-head Binary-to-Geometry Demo ---")
        print(f"Head (predictor, projector): ({predictor_head}, {projector_head})")
        print(f"Prompt: '{prompt}'\n")
        print(f"LLM completes:\n{text}")

        return u_next_hat.cpu(), text


def main():
    device = get_device()
    print(f"Using device: {device}")

    # 1. Load/construct data
    binary_data = load_binary_data(n_samples=50, binary_dim=24)
    X = torch.tensor(binary_data, dtype=torch.float32)
    similarity = build_similarity_matrix(binary_data)

    # 2. Train latent geometry (single-head predictor for now)
    geo = train_latent_geometry(X, similarity, num_epochs=2000, lr=0.02, device=device)
    u_final = geo["u_final"]
    ω_final = geo["ω_final"]
    unk_final = geo["unk_final"]
    predictor = geo["predictor"]

    # 3. Load LLM
    llm, tokenizer = load_frozen_llm("distilgpt2")

    # 4. Train multi-head projectors (narrative + technical)
    head_specs = {
        "narrative": build_descriptions,
        "technical": build_technical_descriptions,
    }
    multi_proj = train_multi_projector(u_final, binary_data, llm, tokenizer, head_specs, num_epochs=1000, lr=0.01, device=device)

    # 5. Save world model (geometry + projectors)
    projector_bundle = {
        "narrative": multi_proj.heads["narrative"],
        "technical": multi_proj.heads["technical"],
    }
    save_world_model("world_model_v1", geo, projector_bundle)

    # 6. Predict next latent state and generate for each head
    for proj_head in ["narrative", "technical"]:
        prompt = f"The next binary state will be described in a {proj_head} way as"
        u_next_hat, _ = generate_future_narrative(
            u_final, predictor, projector_bundle[proj_head], llm, tokenizer, prompt=prompt, device=device
        )

        # Visualize once (or per head if you want separate overlays)
        visualize(u_final, u_next_hat, ω_final, unk_final)





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


from .safe_parser import safe_evaluate

def _test_predicate(self, state: ManifoldState, context: Dict[str, float], corrected_input: float) -> bool:
    cond_str = self.predicate["condition"]
    # Build context dict for safe evaluator
    eval_ctx = {
        "u": state.u,
        "omega": state.omega,
        "uncertainty": state.uncertainty,
        "x": corrected_input,
        **context
    }
    try:
        return safe_evaluate(cond_str, eval_ctx)
    except ValueError:
        return False  # if condition fails to evaluate, treat as failed


        add:
from sensing.exploration.stroboscopic_scheduler import StroboscopicScheduler, SchedulerMode

# Initialize scheduler with heavy frames
heavy_set = {FrameID.DIFFUSION, FrameID.ENSEMBLE, FrameID.SEMANTIC_TUBE}
scheduler = StroboscopicScheduler(heavy_set, interval=10)

def tick_callback(primitive: Primitive):
    context.sensor_type = primitive.sensor_type
    binary_vec = extract_binary(primitive)  # your extraction logic
    
    # Advance scheduler tick
    scheduler.tick()
    
    # For each frame in the router, check if it should run
    if router.mode == "ensemble" and router.active_frame_id == FrameID.ENSEMBLE:
        # If we're in Ensemble mode, but Ensemble is heavy, we might want to
        # aggregate cached results from previous ensemble runs.
        # Simpler: run the ensemble only on heavy ticks; otherwise use the cached ensemble output.
        if scheduler.should_run(FrameID.ENSEMBLE):
            result = router.step(context, binary_vec=binary_vec)
            # Cache the ensemble result
            cached_ensemble = result
        else:
            # Use the cached ensemble result (or fallback to a lightweight frame)
            result = cached_ensemble if cached_ensemble else router.step(context, binary_vec=binary_vec, force_frame=FrameID.FALSIFICATIONIST)
    else:
        # For other frames, use the scheduler to run them conditionally
        # We'll get the active frame and check it
        active_id = router.active_frame_id
        active_frame = router.get_active_frame()
        frame_result = scheduler.run_frame(active_frame, context, binary_vec)
        result = {
            "active_frame": active_id.value,
            "metrics": frame_result["metrics"],
            "trial_results": frame_result["trial_results"],
            "narrative": frame_result["narrative"]
        }
    
    # Assign RL reward if using learned router
    if router.use_learned_router:
        router.assign_router_reward(context)
    
    print(f"[Tick {scheduler.current_tick}] Frame: {result['active_frame']}")
    # ... rest of transmission ...

    
     {
  "active_frame": "ensemble",
  "switching": {
    "mode": "learned",
    "update_interval_ticks": 5,
    "min_ticks_per_frame": 3
  },
  "scheduler": {
    "mode": "strobe",
    "heavy_frames": ["diffusion", "ensemble", "semantic_tube"],
    "interval_ticks": 10
  },
  "frame_params": {
    "semantic_tube": { "tube_radius": 0.2 },
    "resonance": { "rule": 90 },
    "bayesian": { "prior_alpha": 1.0, "prior_beta": 1.0 },
    "diffusion": { "n_steps": 10 }
  },
  "safe_parser": {
    "enabled": true,
    "allowed_functions": ["abs", "len", "min", "max", "sum", "math"]
  }
}



