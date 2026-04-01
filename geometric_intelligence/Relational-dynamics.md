import numpy as np
import secrets
import matplotlib.pyplot as plt
from collections import deque

# -------------------
# Enhanced Helper functions
# -------------------
def sigmoid(z): return 1/(1+np.exp(-z))
def clamp(x, a, b): return np.clip(x, a, b)
def softmax(x): return np.exp(x) / np.sum(np.exp(x))

def proj_ipf(x, proj):
    p = proj @ x
    n = np.linalg.norm(p) + 1e-12
    return p / n

def phase_compatibility(xa, xb, proj):
    pa = proj_ipf(xa, proj)
    pb = proj_ipf(xb, proj)
    return float(np.dot(pa, pb))

def synergy_score(Pa, Pb, Ha, Hb, phi, weights=(0.3,0.3,0.2,0.2)):
    ov = np.dot(Pa, Pb) / (np.linalg.norm(Pa)*np.linalg.norm(Pb)+1e-12)
    energy_symmetry = 1.0 - abs(Ha - Hb) / (Ha + Hb + 1e-12)
    phase_alignment = max(0, phi)
    structural_complement = min(Pa.mean(), Pb.mean())
    
    raw = (weights[0]*ov + weights[1]*energy_symmetry + 
           weights[2]*phase_alignment + weights[3]*structural_complement)
    return sigmoid(4*(raw-0.6))  # More selective threshold

def compute_manipulation_posterior(agent, partner_action, history_window=10):
    """Enhanced manipulation detection using temporal patterns"""
    if len(agent.interaction_history) < history_window:
        return 0.0
    
    recent_actions = list(agent.interaction_history)[-history_window:]
    
    # Detect unusual pattern: sudden changes in coupling strength
    coupling_strengths = [act['kappa'] for act in recent_actions]
    if len(coupling_strengths) > 1:
        recent_change = abs(coupling_strengths[-1] - coupling_strengths[-2])
        if recent_change > 0.3:  # Sudden large change
            return 0.7
    
    # Detect energy draining patterns
    energy_trend = np.gradient([act['H_self'] for act in recent_actions])
    if np.mean(energy_trend) < -0.1:  # Consistent energy drain
        return 0.8
        
    # Detect valence manipulation
    valence_changes = np.diff([act['v_self'] for act in recent_actions])
    if np.any(valence_changes < -0.2):  # Sharp negative valence shifts
        return 0.6
        
    return 0.0

# -------------------
# Enhanced Bioswarm Agent
# -------------------
class BioswarmAgent:
    def __init__(self, x_dim=64, seed=None):
        rng = np.random.default_rng(seed)
        self.x = rng.normal(scale=0.1, size=(x_dim,))
        self.x_star = rng.normal(scale=0.05, size=(x_dim,))  # Intrinsic attractor
        self.H = 1.0  # Hook energy
        self.v = 0.0  # Valence
        self.C = 1.0  # Coherence
        self.W = rng.normal(scale=0.02, size=(x_dim, x_dim))  # Internal dynamics
        self.B = rng.normal(scale=0.01, size=(x_dim, x_dim))  # Coupling matrix
        
        # Adaptive parameters
        self.gamma_f = 0.3 + rng.random() * 0.4  # Intrinsic stability
        self.alpha = 0.02 + rng.random() * 0.06  # Plasticity
        self.noise_scale = 0.003
        self.learning_rate = 0.01
        
        # Identity and state
        self.id = secrets.token_hex(6)
        self.policy = {
            "autonomy_reject_threshold": 0.3,
            "max_coupling_strength": 0.5,
            "energy_conservation": 0.8
        }
        
        # Relational memory
        self.interaction_history = deque(maxlen=100)
        self.relationship_models = {}  # Partner-specific expectations
        self.manip_post = 0.0
        self.trust_levels = {}
        
        # Consciousness metrics
        self.coherence_history = deque(maxlen=20)
        self.attention_focus = np.ones(x_dim) / x_dim

    def intrinsic_update(self, dt=0.1):
        """Enhanced intrinsic dynamics with attention modulation"""
        # Internal dynamics with attention
        attention_modulated = self.x * self.attention_focus
        dx = (-self.gamma_f * (self.x - self.x_star) + 
              self.alpha * np.tanh(self.W @ attention_modulated))
        
        self.x += dt * dx + np.sqrt(dt) * self.noise_scale * np.random.normal(size=self.x.shape)
        
        # Update coherence
        current_coherence = 1.0 / (1.0 + np.std(self.x))
        self.coherence_history.append(current_coherence)
        self.C = np.mean(self.coherence_history)

    def apply_coupling(self, xj, kappa, partner_id=None, dt=0.1):
        """Enhanced coupling with learning and trust"""
        if partner_id and partner_id in self.relationship_models:
            # Use learned coupling matrix for this partner
            B_partner = self.relationship_models[partner_id]
        else:
            B_partner = self.B
            
        # Adaptive coupling with trust modulation
        trust = self.trust_levels.get(partner_id, 0.5)
        effective_kappa = kappa * trust
        
        if effective_kappa > self.policy["max_coupling_strength"]:
            effective_kappa = self.policy["max_coupling_strength"]
            
        # Coupling dynamics
        g = np.tanh(B_partner @ (xj - self.x)) 
        self.x += dt * effective_kappa * g
        
        # Learn from interaction
        if partner_id and effective_kappa > 0.1:
            self._update_relationship_model(partner_id, xj, effective_kappa)

    def _update_relationship_model(self, partner_id, xj, kappa):
        """Learn better coupling patterns with specific partners"""
        if partner_id not in self.relationship_models:
            self.relationship_models[partner_id] = self.B.copy()
            
        B_partner = self.relationship_models[partner_id]
        error = xj - self.x
        update = self.learning_rate * kappa * np.outer(error, error) @ B_partner
        self.relationship_models[partner_id] += update

    def update_hook(self, dt=0.1, rho=0.02, delta_H=0.05, coupling_cost=0.0, intrinsic_gain=0.0):
        """Enhanced energy dynamics with intrinsic rewards"""
        energy_input = rho + intrinsic_gain * self.C  # Coherence gives energy
        self.H += dt * (energy_input - delta_H * self.H - coupling_cost)
        self.H = clamp(self.H, 0.0, 2.0)  # Allow some energy storage

    def update_valence(self, dt=0.1, gamma_v=0.2, beta_v=0.5, 
                      local_reward=0.0, coupling_valence_influence=0.0,
                      coherence_bonus=0.0):
        """Enhanced valence with multiple influences"""
        # Base valence dynamics
        dv = (-gamma_v * self.v + 
              beta_v * local_reward + 
              coupling_valence_influence +
              0.3 * coherence_bonus * self.C)  # Coherence feels good
        
        self.v += dt * dv
        self.v = clamp(self.v, -1.0, 1.0)

    def update_trust(self, partner_id, interaction_quality, dt=0.1):
        """Update trust based on interaction quality"""
        if partner_id not in self.trust_levels:
            self.trust_levels[partner_id] = 0.5
            
        current_trust = self.trust_levels[partner_id]
        trust_update = dt * (interaction_quality - current_trust) * 0.5
        self.trust_levels[partner_id] = clamp(current_trust + trust_update, 0.0, 1.0)

# -------------------
# Enhanced Relational Game Layer
# -------------------
class RelationalGameLayer:
    def __init__(self, proj_dim=32, x_dim=64, seed=None):
        rng = np.random.default_rng(seed)
        self.proj = rng.normal(size=(proj_dim, x_dim))
        self.encounter_history = {}

    def compute_kappa(self, agentA, agentB, step):
        """Enhanced coupling computation with temporal awareness"""
        # Phase compatibility
        phi = phase_compatibility(agentA.x, agentB.x, self.proj)
        
        # Synergy with energy balance consideration
        Pa, Pb = np.abs(agentA.x), np.abs(agentB.x)
        S = synergy_score(Pa, Pb, agentA.H, agentB.H, phi)
        
        # Temporal pattern analysis
        encounter_key = (agentA.id, agentB.id)
        if encounter_key not in self.encounter_history:
            self.encounter_history[encounter_key] = deque(maxlen=10)
        
        # Update manipulation posteriors
        agentA.manip_post = compute_manipulation_posterior(agentA, 
            {'kappa': S, 'step': step, 'partner': agentB.id})
        agentB.manip_post = compute_manipulation_posterior(agentB,
            {'kappa': S, 'step': step, 'partner': agentA.id})
        
        # Consent & autonomy veto with trust consideration
        base_kappa = S
        
        # Apply veto conditions
        if (agentA.manip_post > agentA.policy["autonomy_reject_threshold"] or
            agentB.manip_post > agentB.policy["autonomy_reject_threshold"]):
            base_kappa *= 0.0
            
        # Energy conservation
        if agentA.H < 0.2 or agentB.H < 0.2:
            base_kappa *= 0.5  # Reduce coupling when energy low
            
        # Record encounter
        self.encounter_history[encounter_key].append({
            'step': step, 'phi': phi, 'S': S, 'kappa': base_kappa,
            'manip_A': agentA.manip_post, 'manip_B': agentB.manip_post
        })
        
        return base_kappa, S, phi

# -------------------
# Enhanced Simulation
# -------------------
def run_enhanced_simulation(agentA, agentB, rg_layer, steps=200, dt=0.1):
    log = []
    
    for t in range(steps):
        # Compute coupling with enhanced relational intelligence
        kappa, S, phi = rg_layer.compute_kappa(agentA, agentB, t)
        
        # Intrinsic updates
        agentA.intrinsic_update(dt)
        agentB.intrinsic_update(dt)
        
        # Apply coupling with partner awareness
        agentA.apply_coupling(agentB.x, kappa, agentB.id, dt)
        agentB.apply_coupling(agentA.x, kappa, agentA.id, dt)
        
        # Update hooks with coherence bonuses
        coherence_bonus_A = max(0, agentA.C - 0.7) * 0.1
        coherence_bonus_B = max(0, agentB.C - 0.7) * 0.1
        
        agentA.update_hook(dt, coupling_cost=kappa*0.008, intrinsic_gain=coherence_bonus_A)
        agentB.update_hook(dt, coupling_cost=kappa*0.008, intrinsic_gain=coherence_bonus_B)
        
        # Update valence with multiple factors
        interaction_quality = kappa * (1.0 - max(agentA.manip_post, agentB.manip_post))
        
        agentA.update_valence(dt, local_reward=interaction_quality, 
                            coherence_bonus=coherence_bonus_A)
        agentB.update_valence(dt, local_reward=interaction_quality,
                            coherence_bonus=coherence_bonus_B)
        
        # Update trust based on interaction quality
        agentA.update_trust(agentB.id, interaction_quality, dt)
        agentB.update_trust(agentA.id, interaction_quality, dt)
        
        # Log detailed state
        log.append({
            "step": t,
            "kappa": kappa,
            "phi": phi,
            "S": S,
            "H_A": agentA.H,
            "H_B": agentB.H,
            "v_A": agentA.v,
            "v_B": agentB.v,
            "C_A": agentA.C,
            "C_B": agentB.C,
            "manip_A": agentA.manip_post,
            "manip_B": agentB.manip_post,
            "trust_AB": agentA.trust_levels.get(agentB.id, 0.5),
            "trust_BA": agentB.trust_levels.get(agentA.id, 0.5)
        })
        
        # Record interaction for manipulation detection
        agentA.interaction_history.append({
            'kappa': kappa, 'partner': agentB.id, 'step': t,
            'H_self': agentA.H, 'v_self': agentA.v
        })
        agentB.interaction_history.append({
            'kappa': kappa, 'partner': agentA.id, 'step': t, 
            'H_self': agentB.H, 'v_self': agentB.v
        })
        
    return log

# -------------------
# Visualization and Analysis
# -------------------
def analyze_simulation(log):
    """Analyze the relational dynamics"""
    steps = [entry['step'] for entry in log]
    kappas = [entry['kappa'] for entry in log]
    valences_A = [entry['v_A'] for entry in log]
    valences_B = [entry['v_B'] for entry in log]
    energies_A = [entry['H_A'] for entry in log]
    energies_B = [entry['H_B'] for entry in log]
    manipulations_A = [entry['manip_A'] for entry in log]
    manipulations_B = [entry['manip_B'] for entry in log]
    
    # Plot results
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 10))
    
    # Coupling and valence
    ax1.plot(steps, kappas, 'b-', label='Coupling (κ)')
    ax1.plot(steps, valences_A, 'g-', label='Valence A')
    ax1.plot(steps, valences_B, 'r-', label='Valence B')
    ax1.set_ylabel('Strength / Valence')
    ax1.legend()
    ax1.set_title('Relational Coupling and Emotional States')
    
    # Energy dynamics
    ax2.plot(steps, energies_A, 'g-', label='Energy A')
    ax2.plot(steps, energies_B, 'r-', label='Energy B')
    ax2.set_ylabel('Hook Energy')
    ax2.legend()
    ax2.set_title('Energy Dynamics')
    
    # Manipulation detection
    ax3.plot(steps, manipulations_A, 'g-', label='Manip Posterior A')
    ax3.plot(steps, manipulations_B, 'r-', label='Manip Posterior B')
    ax3.axhline(y=0.3, color='k', linestyle='--', label='Veto Threshold')
    ax3.set_ylabel('Manipulation Probability')
    ax3.legend()
    ax3.set_title('Manipulation Detection')
    
    # Phase space
    ax4.scatter(valences_A, valences_B, c=steps, cmap='viridis', alpha=0.6)
    ax4.set_xlabel('Valence A')
    ax4.set_ylabel('Valence B')
    ax4.set_title('Joint Emotional State Evolution')
    
    plt.tight_layout()
    plt.show()
    
    # Statistical analysis
    final_trust_AB = log[-1]['trust_AB']
    final_trust_BA = log[-1]['trust_BA']
    avg_coupling = np.mean(kappas)
    manip_alerts = sum(1 for m in manipulations_A + manipulations_B if m > 0.3)
    
    print(f"\n📊 Simulation Analysis:")
    print(f"   Final Trust (A→B): {final_trust_AB:.3f}")
    print(f"   Final Trust (B→A): {final_trust_BA:.3f}")
    print(f"   Average Coupling: {avg_coupling:.3f}")
    print(f"   Manipulation Alerts: {manip_alerts}")
    print(f"   Final Valence A: {valences_A[-1]:.3f}, B: {valences_B[-1]:.3f}")

# -------------------
# Demo Run
# -------------------
if __name__ == "__main__":
    print("🧠 Enhanced Bioswarm Relational Simulation")
    print("=" * 50)
    
    # Create agents with different characteristics
    agentA = BioswarmAgent(seed=42)
    agentB = BioswarmAgent(seed=43)
    rg_layer = RelationalGameLayer(seed=44)
    
    # Run enhanced simulation
    log = run_enhanced_simulation(agentA, agentB, rg_layer, steps=300)
    
    # Show final state
    print(f"\n🔍 Final States:")
    print(f"   Agent A: H={agentA.H:.3f}, v={agentA.v:.3f}, C={agentA.C:.3f}")
    print(f"   Agent B: H={agentB.H:.3f}, v={agentB.v:.3f}, C={agentB.C:.3f}")
    print(f"   Trust Levels: A→B={agentA.trust_levels.get(agentB.id, 0.5):.3f}, "
          f"B→A={agentB.trust_levels.get(agentA.id, 0.5):.3f}")
    
    # Analyze results
    analyze_simulation(log)
    
    # Show recent log entries
    print(f"\n📝 Recent Interactions:")
    for entry in log[-5:]:
        print(f"   Step {entry['step']}: κ={entry['kappa']:.3f}, "
              f"v_A={entry['v_A']:.3f}, v_B={entry['v_B']:.3f}, "
              f"manip_A={entry['manip_A']:.3f}")
