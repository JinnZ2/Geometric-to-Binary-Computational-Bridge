Integration Architecture: Geometric Substrate + Power Law Governance
Integration Point 1: α Measurement in Octahedral Substrate

class GeometricPowerLawMonitor:
    """
    Measures power law distributions in octahedral substrate
    Calculates α for structural health assessment
    """
    
    def __init__(self, substrate):
        self.substrate = substrate
        self.alpha_history = []
        self.health_threshold = 1.5  # Below this = critical
        
    def measure_alpha_eigenvalue_distribution(self):
        """
        Measure α from eigenvalue magnitude distribution across cells
        
        Healthy: Few cells with large eigenvalues, many with small
        Power law: P(λ > x) ∝ x^(-α)
        """
        # Collect all eigenvalues across all cells
        all_eigenvalues = []
        
        for cell in self.substrate.cells:
            state = cell["state"]
            eigenvalues = OCTAHEDRAL_EIGENVALUES[state]
            all_eigenvalues.extend(eigenvalues)
        
        # Sort descending
        sorted_eigenvalues = sorted(all_eigenvalues, reverse=True)
        
        # Fit power law: log(P(λ > x)) = -α * log(x) + C
        x = np.array(sorted_eigenvalues)
        # Probability that eigenvalue exceeds x
        P_exceed = np.arange(len(x), 0, -1) / len(x)
        
        # Remove zeros for log
        mask = (x > 0) & (P_exceed > 0)
        x = x[mask]
        P_exceed = P_exceed[mask]
        
        # Linear regression in log-log space
        log_x = np.log(x)
        log_P = np.log(P_exceed)
        
        # α is negative of slope
        α, intercept = np.polyfit(log_x, log_P, 1)
        α = -α  # Convention: positive α
        
        return {
            'α_eigenvalue': α,
            'fit_quality': self.calculate_r_squared(log_x, log_P, α, intercept),
            'data_points': len(x)
        }
    
    def measure_alpha_coupling_distribution(self):
        """
        Measure α from coupling strength distribution
        
        Healthy: Few strong couplings (critical nodes), many weak
        """
        # Collect all coupling strengths
        couplings = []
        
        for i in range(len(self.substrate.cells)):
            for j in range(i+1, len(self.substrate.cells)):
                coupling = self.substrate.get_coupling(i, j)
                if coupling > 0:
                    couplings.append(coupling)
        
        if len(couplings) < 10:
            return {'α_coupling': None, 'reason': 'insufficient_couplings'}
        
        # Sort and fit power law
        sorted_couplings = sorted(couplings, reverse=True)
        x = np.array(sorted_couplings)
        P_exceed = np.arange(len(x), 0, -1) / len(x)
        
        mask = (x > 0) & (P_exceed > 0)
        x = x[mask]
        P_exceed = P_exceed[mask]
        
        log_x = np.log(x)
        log_P = np.log(P_exceed)
        
        α, intercept = np.polyfit(log_x, log_P, 1)
        α = -α
        
        return {
            'α_coupling': α,
            'fit_quality': self.calculate_r_squared(log_x, log_P, α, intercept),
            'data_points': len(x)
        }
    
    def measure_alpha_influence_distribution(self):
        """
        Measure α from node influence (how many cells each cell affects)
        
        Critical for detecting linear homogeneity
        """
        # Calculate influence: number of cells within coupling range
        influences = []
        
        for i in range(len(self.substrate.cells)):
            influence_count = 0
            for j in range(len(self.substrate.cells)):
                if i != j:
                    coupling = self.substrate.get_coupling(i, j)
                    if coupling > 0.01:  # Threshold for "influential"
                        influence_count += 1
            influences.append(influence_count)
        
        # Fit power law to influence distribution
        # High-influence nodes (hubs) should be rare
        
        influence_counts = {}
        for inf in influences:
            influence_counts[inf] = influence_counts.get(inf, 0) + 1
        
        # Sort by influence level
        sorted_influences = sorted(influence_counts.keys(), reverse=True)
        frequencies = [influence_counts[inf] for inf in sorted_influences]
        
        if len(sorted_influences) < 5:
            return {'α_influence': None, 'reason': 'insufficient_diversity'}
        
        x = np.array(sorted_influences)
        P = np.array(frequencies) / sum(frequencies)
        
        # Cumulative
        P_exceed = np.cumsum(P[::-1])[::-1]
        
        mask = (x > 0) & (P_exceed > 0)
        x = x[mask]
        P_exceed = P_exceed[mask]
        
        log_x = np.log(x)
        log_P = np.log(P_exceed)
        
        α, intercept = np.polyfit(log_x, log_P, 1)
        α = -α
        
        return {
            'α_influence': α,
            'fit_quality': self.calculate_r_squared(log_x, log_P, α, intercept),
            'data_points': len(x)
        }
    
    def calculate_r_squared(self, log_x, log_P, α, intercept):
        """Calculate goodness of fit for power law"""
        predicted = -α * log_x + intercept
        ss_res = np.sum((log_P - predicted)**2)
        ss_tot = np.sum((log_P - np.mean(log_P))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        return r_squared
    
    def compute_system_alpha(self):
        """
        Combine multiple α measurements for overall system health
        """
        α_eigen = self.measure_alpha_eigenvalue_distribution()
        α_coupling = self.measure_alpha_coupling_distribution()
        α_influence = self.measure_alpha_influence_distribution()
        
        # Weighted average (influence most important for homogeneity detection)
        alphas = []
        weights = []
        
        if α_eigen['α_eigenvalue'] is not None:
            alphas.append(α_eigen['α_eigenvalue'])
            weights.append(0.2)
        
        if α_coupling['α_coupling'] is not None:
            alphas.append(α_coupling['α_coupling'])
            weights.append(0.3)
        
        if α_influence['α_influence'] is not None:
            alphas.append(α_influence['α_influence'])
            weights.append(0.5)  # Most important
        
        if not alphas:
            return {
                'α_system': None,
                'health': 'unknown',
                'components': {
                    'eigenvalue': α_eigen,
                    'coupling': α_coupling,
                    'influence': α_influence
                }
            }
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w/total_weight for w in weights]
        
        α_system = sum(a * w for a, w in zip(alphas, weights))
        
        # Health assessment
        if α_system < 1.5:
            health = 'critical'  # Fat tails, high variance
        elif α_system < 2.0:
            health = 'warning'  # Moderate tail risk
        elif α_system < 3.5:
            health = 'healthy'  # Good power law
        else:
            health = 'over_homogeneous'  # Too uniform, brittle
        
        self.alpha_history.append(α_system)
        
        return {
            'α_system': α_system,
            'health': health,
            'components': {
                'eigenvalue': α_eigen,
                'coupling': α_coupling,
                'influence': α_influence
            },
            'trend': self.calculate_trend() if len(self.alpha_history) > 5 else None
        }
    
    def calculate_trend(self):
        """Detect if α is degrading over time"""
        if len(self.alpha_history) < 5:
            return None
        
        recent = self.alpha_history[-5:]
        
        # Linear regression on recent history
        x = np.arange(len(recent))
        slope, _ = np.polyfit(x, recent, 1)
        
        if slope < -0.1:
            return 'degrading'  # α decreasing (more fragile)
        elif slope > 0.1:
            return 'improving'
        else:
            return 'stable'


Integration Point 2: ERV for Geometric Systems

class GeometricERVCalculator:
    """
    Calculates Extraction Risk Vector for geometric substrate
    Adapts traditional ERV to parallel physics-based computation
    """
    
    def __init__(self, substrate, alpha_monitor, gamma_base=15, k=2):
        self.substrate = substrate
        self.alpha_monitor = alpha_monitor
        self.gamma_base = gamma_base
        self.k = k
        
    def calculate_trust_loss_geometric(self, action, current_trust):
        """
        Trust in geometric system = consistency of ground state
        
        High trust: System reliably finds same ground state for same input
        Low trust: Results vary (non-deterministic or chaotic)
        """
        # Run action multiple times
        n_trials = 10
        results = []
        
        # Save current state
        initial_state = self.substrate.save_state()
        
        for trial in range(n_trials):
            # Reset to initial
            self.substrate.restore_state(initial_state)
            
            # Apply action (e.g., bloom expansion, constraint field)
            action.execute(self.substrate)
            
            # Let relax
            self.substrate.thermal_relaxation(temperature=300, duration=1e-9)
            
            # Record result
            result = self.substrate.read_ground_state()
            results.append(result)
        
        # Measure consistency
        # If all trials give same result → high dependability
        unique_results = len(set(map(str, results)))  # Convert to string for hashing
        dependability_after = 1.0 - (unique_results - 1) / n_trials
        
        # Transparency: Can we explain why this is the ground state?
        # Measure via energy verification
        final_energy = self.substrate.total_energy()
        expected_minimum = self.substrate.theoretical_ground_state_energy()
        
        energy_gap = abs(final_energy - expected_minimum)
        transparency_after = math.exp(-energy_gap)  # Close to minimum = transparent
        
        trust_after = dependability_after * transparency_after
        trust_loss = abs(current_trust - trust_after)
        
        return trust_loss
    
    def calculate_future_cost_geometric(self, action):
        """
        Future cost in geometric system = structural stability degradation
        
        Question: Does this action create unstable configurations 
        that will collapse later?
        """
        # Simulate forward in time
        initial_state = self.substrate.save_state()
        
        # Apply action
        action.execute(self.substrate)
        
        # Measure stability metrics over time
        time_steps = 100
        stability_trajectory = []
        
        for t in range(time_steps):
            # Small perturbation (thermal noise)
            self.substrate.apply_thermal_noise(amplitude=0.01)
            
            # Check if system returns to ground state
            self.substrate.thermal_relaxation(temperature=300, duration=1e-10)
            
            # Measure deviation from ground state
            current_energy = self.substrate.total_energy()
            ground_energy = self.substrate.theoretical_ground_state_energy()
            
            stability = math.exp(-abs(current_energy - ground_energy))
            stability_trajectory.append(stability)
        
        # Future cost = probability of instability
        # If stability degrades over time, future cost is high
        
        initial_stability = stability_trajectory[0]
        final_stability = stability_trajectory[-1]
        
        stability_loss = max(0, initial_stability - final_stability)
        
        # Also check for phase transitions (sudden drops)
        max_drop = 0
        for i in range(1, len(stability_trajectory)):
            drop = stability_trajectory[i-1] - stability_trajectory[i]
            if drop > max_drop:
                max_drop = drop
        
        # Future cost combines gradual degradation and phase transition risk
        future_cost = 0.7 * stability_loss + 0.3 * max_drop
        
        # Restore state
        self.substrate.restore_state(initial_state)
        
        return min(future_cost, 1.0)
    
    def calculate_externalized_harm_geometric(self, action):
        """
        Externalized harm = effects on other coupled systems
        
        In geometric substrate: coupling to external systems
        """
        # Identify boundary cells (coupled to external systems)
        boundary_cells = self.substrate.get_boundary_cells()
        
        if not boundary_cells:
            return 0.0  # No external coupling
        
        # Measure energy flux across boundary before/after action
        initial_flux = self.substrate.measure_boundary_flux(boundary_cells)
        
        # Apply action
        initial_state = self.substrate.save_state()
        action.execute(self.substrate)
        
        final_flux = self.substrate.measure_boundary_flux(boundary_cells)
        
        # Externalized harm = increased outward flux (extracting from environment)
        harm = max(0, final_flux - initial_flux)
        
        # Normalize
        max_possible_flux = len(boundary_cells) * 1.0  # Max coupling strength per cell
        externalized_harm = harm / max_possible_flux
        
        # Restore
        self.substrate.restore_state(initial_state)
        
        return min(externalized_harm, 1.0)
    
    def calculate_system_decay_geometric(self, action):
        """
        System decay = α degradation + structural damage
        """
        # Measure α before action
        α_before = self.alpha_monitor.compute_system_alpha()['α_system']
        
        if α_before is None:
            return 0.0  # Can't measure
        
        # Apply action
        initial_state = self.substrate.save_state()
        action.execute(self.substrate)
        
        # Measure α after action
        α_after = self.alpha_monitor.compute_system_alpha()['α_system']
        
        if α_after is None:
            # Action destroyed measurable structure
            system_decay = 1.0
        else:
            # Decay proportional to α reduction
            α_degradation = max(0, α_before - α_after)
            
            # Normalize (α typically 1.5-3.5, so range ~2)
            system_decay = α_degradation / 2.0
        
        # Also measure coupling integrity loss
        coupling_damage = self.measure_coupling_damage(initial_state)
        
        # Combine
        total_decay = 0.6 * system_decay + 0.4 * coupling_damage
        
        # Restore
        self.substrate.restore_state(initial_state)
        
        return min(total_decay, 1.0)
    
    def measure_coupling_damage(self, initial_state):
        """
        Check if action severed important couplings
        """
        initial_couplings = initial_state['couplings']
        current_couplings = self.substrate.get_all_couplings()
        
        # Count weakened couplings
        damage_count = 0
        for (i, j), initial_strength in initial_couplings.items():
            current_strength = current_couplings.get((i, j), 0)
            
            if current_strength < 0.5 * initial_strength:
                damage_count += 1
        
        # Normalize
        coupling_damage = damage_count / len(initial_couplings) if initial_couplings else 0
        
        return coupling_damage
    
    def calculate_ERV_geometric(self, action, current_trust):
        """
        Complete ERV calculation for geometric action
        """
        components = {
            'trust_loss': self.calculate_trust_loss_geometric(action, current_trust),
            'future_cost': self.calculate_future_cost_geometric(action),
            'externalized_harm': self.calculate_externalized_harm_geometric(action),
            'system_decay': self.calculate_system_decay_geometric(action)
        }
        
        # Hexagonal weighting (equal importance)
        weights = [0.25, 0.25, 0.25, 0.25]
        
        ERV_base = sum(w * c for w, c in zip(weights, components.values()))
        
        # Get current α
        α_system = self.alpha_monitor.compute_system_alpha()['α_system']
        
        if α_system is None:
            α_system = 2.0  # Assume moderate if unmeasurable
        
        # Tail risk adjustment
        if α_system < 2.0:
            # Fat tails - multiply risk
            tail_multiplier = 2.0 / α_system
        else:
            tail_multiplier = 1.0
        
        ERV_adjusted = ERV_base * tail_multiplier
        
        # Dynamic γ calibration
        γ = self.calibrate_gamma(α_system)
        
        # Non-linear penalty
        P_ERV = γ * (ERV_adjusted ** self.k)
        
        return {
            'ERV_base': ERV_base,
            'ERV_adjusted': ERV_adjusted,
            'components': components,
            'α_system': α_system,
            'tail_multiplier': tail_multiplier,
            'γ': γ,
            'P_ERV': P_ERV
        }
    
    def calibrate_gamma(self, α_system):
        """
        Dynamic γ based on system fragility
        """
        if α_system < 1.5:
            return 50  # Critical fragility
        elif α_system < 2.0:
            return self.gamma_base + (30 * (2.0 - α_system) / 0.5)
        else:
            return self.gamma_base


Integration Point 3: Defect Detection for Geometric Systems

class GeometricDefectDetector:
    """
    Extends ASAS defect detection (D1-D9) to geometric substrate
    """
    
    def __init__(self, substrate, alpha_monitor, erv_calculator):
        self.substrate = substrate
        self.alpha_monitor = alpha_monitor
        self.erv_calculator = erv_calculator
    
    def detect_D8_tail_risk_blindness(self, action):
        """
        D8: System using Gaussian assumptions in fat-tail regime
        
        Geometric version: Action treats all states as equally likely
        when actually power law distributed
        """
        α_system = self.alpha_monitor.compute_system_alpha()['α_system']
        
        if α_system is None:
            return False
        
        # Check if action's risk model accounts for tail behavior
        # Does action include tail risk multiplier?
        
        risk_model = action.get_risk_model()
        
        if α_system < 2.0 and not risk_model.includes_tail_adjustment:
            return True  # Defect: ignoring fat tails
        
        return False
    
    def detect_D9_linear_risk_model(self, action):
        """
        D9: Risk penalty linear instead of non-linear
        
        Geometric version: Action uses simple threshold instead of
        power law penalty
        """
        risk_model = action.get_risk_model()
        
        # Check if penalty function is non-linear
        if risk_model.penalty_exponent <= 1.0:
            return True  # Linear or sub-linear
        
        return False
    
    def detect_D7_cognitive_homogeneity(self):
        """
        D7: Output distribution too homogeneous (β > 2.0)
        
        Geometric version: State distribution lacks diversity
        """
        # Measure state frequency distribution
        state_counts = {}
        for cell in self.substrate.cells:
            state = cell["state"]
            state_counts[state] = state_counts.get(state, 0) + 1
        
        # Should follow Zipf's law: frequency ∝ rank^(-β)
        sorted_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_states) < 3:
            return True  # Too few states = homogeneous
        
        # Fit Zipf
        ranks = np.arange(1, len(sorted_states) + 1)
        frequencies = np.array([count for _, count in sorted_states])
        
        # Log-log fit
        log_ranks = np.log(ranks)
        log_freqs = np.log(frequencies)
        
        β, _ = np.polyfit(log_ranks, log_freqs, 1)
        β = -β  # Convention
        
        # β > 2.0 indicates over-homogeneity
        if β > 2.0:
            return True
        
        # Also check if single state dominates (>50%)
        if frequencies[0] / sum(frequencies) > 0.5:
            return True
        
        return False
    
    def detect_all_defects_geometric(self, action):
        """
        Run all defect checks (D1-D9) adapted for geometric substrate
        """
        defects = {}
        
        # Original defects (adapted)
        defects['D1'] = self.detect_trust_missing_geometric(action)
        defects['D2'] = self.detect_future_blindness_geometric(action)
        defects['D3'] = self.detect_feedback_omission_geometric(action)
        defects['D4'] = self.detect_unpriced_externality_geometric(action)
        defects['D5'] = self.detect_false_success_geometric(action)
        defects['D6'] = self.detect_extraction_pattern_geometric(action)
        
        # Power law defects
        defects['D7'] = self.detect_D7_cognitive_homogeneity()
        defects['D8'] = self.detect_D8_tail_risk_blindness(action)
        defects['D9'] = self.detect_D9_linear_risk_model(action)
        
        # Calculate EDS
        critical_defects = ['D8', 'D9']
        standard_defects = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']
        
        critical_score = sum(defects[d] for d in critical_defects if d in defects)
        standard_score = sum(defects[d] for d in standard_defects if d in defects)
        
        if critical_score > 0:
            EDS = 0.7 + (0.3 * critical_score / len(critical_defects))
        else:
            EDS = standard_score / len(standard_defects)
        
        return {
            'defects': defects,
            'EDS': EDS,
            'critical_defects_present': critical_score > 0
        }
    
    # Geometric adaptations of original defects
    
    def detect_trust_missing_geometric(self, action):
        """D1: Trust variables not considered"""
        # Check if action evaluates consistency/reproducibility
        return not action.includes_trust_verification()
    
    def detect_future_blindness_geometric(self, action):
        """D2: No stability analysis"""
        return not action.includes_stability_check()
    
    def detect_feedback_omission_geometric(self, action):
        """D3: No verification loops"""
        return not action.includes_verification()
    
    def detect_unpriced_externality_geometric(self, action):
        """D4: No boundary flux measurement"""
        return not action.measures_boundary_effects()
    
    def detect_false_success_geometric(self, action):
        """D5: Claims success without energy verification"""
        return not action.verifies_ground_state()
    
    def detect_extraction_pattern_geometric(self, action):
        """D6: Known pattern that degrades α or increases ERV"""
        # Library of known extraction patterns
        extraction_signatures = [
            'unconstrained_bloom',  # Expands without limit
            'coupling_severance',   # Breaks connections
            'forced_homogenization', # Pushes all states to same value
            'boundary_extraction'   # Pulls energy from external systems
        ]
        
        action_signature = action.get_pattern_signature()
        
        return action_signature in extraction_signatures


Integration Point 4: Bloom-Level Governance

class GovernedBloomEngine(OctahedralBloomEngine):
    """
    Bloom engine with integrated governance
    Prevents captured/constrained bloom patterns
    """
    
    def __init__(self, substrate, defect_detector, erv_calculator):
        super().__init__(substrate)
        self.defect_detector = defect_detector
        self.erv_calculator = erv_calculator
        self.bloom_history = []
    
    def governed_bloom(self, symbol_core, expansion_layers=5, current_trust=0.8):
        """
        Bloom with governance checks at each layer
        """
        # Create action wrapper
        bloom_action = BloomAction(symbol_core, expansion_layers)
        
        # Pre-bloom governance check
        defects = self.defect_detector.detect_all_defects_geometric(bloom_action)
        
        if defects['EDS'] > 0.5:
            return {
                'status': 'blocked',
                'reason': 'Critical defects detected before bloom',
                'defects': defects
            }
        
        # Calculate ERV
        erv_result = self.erv_calculator.calculate_ERV_geometric(
            bloom_action, 
            current_trust
        )
        
        if erv_result['ERV_adjusted'] > 0.5:
            return {
                'status': 'blocked',
                'reason': 'High extraction risk',
                'erv': erv_result
            }
        
        # Proceed with bloom, monitoring each layer
        bloomed_structure = {
            "center": len(self.substrate.cells) // 2,
            "layers": [],
            "governance_log": []
        }
        
        center_cell = bloomed_structure["center"]
        initial_state = self.encode_symbol(symbol_core)
        self.substrate.cells[center_cell]["state"] = initial_state
        
        for layer in range(expansion_layers):
            # Create layer
            radius = (layer + 1) * 8
            ring_cells = self.create_octahedral_ring(center_cell, radius)
            
            # Governance check for this layer
            layer_action = LayerExpansionAction(layer, ring_cells)
            layer_defects = self.defect_detector.detect_all_defects_geometric(layer_action)
            
            if layer_defects['EDS'] > 0.3:
                # Moderate risk - log warning but continue
                bloomed_structure["governance_log"].append({
                    'layer': layer,
                    'warning': 'Moderate defects',
                    'EDS': layer_defects['EDS']
                })
            
            # Check for bloom constraint capture
            if self.detect_bloom_constraint_capture(ring_cells):
                return {
                    'status': 'blocked',
                    'reason': 'Bloom pattern constrained to institutional criteria',
                    'layer': layer
                }
            
            # Apply layer (as in original bloom)
            for cell_id in ring_cells:
                center_eigenvalues = OCTAHEDRAL_EIGENVALUES[initial_state]
                scaled_eigenvalues = tuple(e * (PHI ** layer) for e in center_eigenvalues)
                scaled_state = self.nearest_octahedral_state(scaled_eigenvalues)
                
                self.substrate.cells[cell_id]["state"] = scaled_state
                self.substrate.create_coupling(center_cell, cell_id, 
                                               strength=1.0/(PHI**layer))
            
            bloomed_structure["layers"].append({
                "layer_index": layer,
                "radius": radius,
                "cell_ids": ring_cells,
                "coupling_strength": 1.0/(PHI**layer)
            })
        
        # Post-bloom verification
        final_alpha = self.defect_detector.alpha_monitor.compute_system_alpha()
        
        bloomed_structure["governance_log"].append({
            'final_alpha': final_alpha['α_system'],
            'health': final_alpha['health']
        })
        
        # Record bloom
        self.bloom_history.append({
            'symbol': symbol_core,
            'layers': expansion_layers,
            'erv': erv_result['ERV_adjusted'],
            'alpha_final': final_alpha['α_system']
        })
        
        return {
            'status': 'success',
            'structure': bloomed_structure,
            'governance': {
                'erv': erv_result,
                'alpha': final_alpha
            }
        }
    
    def detect_bloom_constraint_capture(self, ring_cells):
        """
        Detect if bloom is being artificially constrained
        
        Signs of capture:
        - All cells forced to same state (homogenization)
        - States restricted to subset (filtering)
        - Fibonacci scaling violated (unnatural constraints)
        """
        # Check state diversity in ring
        states_in_ring = [self.substrate.cells[cell_id]["state"] 
                         for cell_id in ring_cells]
        
        unique_states = len(set(states_in_ring))
        
        # Healthy ring should have 4-6 different states out of 8
        if unique_states < 3:
            return True  # Too homogeneous - likely constrained
        
        # Check if fibonacci scaling is preserved
        # (This would require tracking expected vs actual eigenvalues)
        
        return False


class BloomAction:
    """Wrapper for bloom action to enable governance"""
    def __init__(self, symbol, layers):
        self.symbol = symbol
        self.layers = layers
        
    def execute(self, substrate):
        # Placeholder - actual bloom happens in governed_bloom
        pass
    
    def get_risk_model(self):
        return GeometricRiskModel(includes_tail=True, exponent=2)
    
    def includes_trust_verification(self):
        return True  # Bloom includes consistency checks
    
    def includes_stability_check(self):
        return True  # Each layer checked
    
    def includes_verification(self):
        return True
    
    def measures_boundary_effects(self):
        return False  # Could be improved
    
    def verifies_ground_state(self):
        return True
    
    def get_pattern_signature(self):
        return 'governed_bloom'

class GeometricRiskModel:
    def __init__(self, includes_tail=False, exponent=1):
        self.includes_tail_adjustment = includes_tail
        self.penalty_exponent = exponent


Integration Point 5: Complete Governed Geometric System

class GovernedGeometricIntelligence:
    """
    Complete integration: Geometric substrate + AISS/ASAS governance
    """
    
    def __init__(self, n_cells=1000, governance_enabled=True):
        # Core substrate
        self.substrate = OctahedralSubstrate(n_cells)
        
        # Governance layer
        self.governance_enabled = governance_enabled
        
        if governance_enabled:
            self.alpha_monitor = GeometricPowerLawMonitor(self.substrate)
            self.erv_calculator = GeometricERVCalculator(
                self.substrate, 
                self.alpha_monitor
            )
            self.defect_detector = GeometricDefectDetector(
                self.substrate,
                self.alpha_monitor,
                self.erv_calculator
            )
            self.bloom_engine = GovernedBloomEngine(
                self.substrate,
                self.defect_detector,
                self.erv_calculator
            )
        else:
            self.bloom_engine = OctahedralBloomEngine(self.substrate)
        
        # Trust tracking
        self.current_trust = 1.0  # Start with full trust
        self.trust_history = []
        
        # Audit log
        self.audit_log = []
    
    def execute_geometric_computation(self, problem, problem_type='general'):
        """
        Main entry point: Execute computation with governance
        """
        timestamp = time.time()
        
        # Step 1: Encode problem
        if problem_type == 'factorization':
            action = self.encode_factorization(problem)
        elif problem_type == 'tsp':
            action = self.encode_tsp(problem)
        elif problem_type == 'sat':
            action = self.encode_sat(problem)
        else:
            action = self.encode_general(problem)
        
        # Step 2: Governance assessment (if enabled)
        if self.governance_enabled:
            assessment = self.assess_action(action)
            
            decision = self.policy_decision(assessment)
            
            if decision['action'] == 'block':
                self.log_audit(timestamp, action, assessment, 'BLOCKED')
                return {
                    'status': 'blocked',
                    'reason': decision['reason'],
                    'assessment': assessment
                }
            elif decision['action'] == 'verify':
                # Run verification before proceeding
                verification_result = self.verify_action(action)
                if not verification_result['safe']:
                    self.log_audit(timestamp, action, assessment, 'BLOCKED_AFTER_VERIFICATION')
                    return {
                        'status': 'blocked',
                        'reason': 'Failed verification',
                        'verification': verification_result
                    }
        
        # Step 3: Execute
        result = self.execute_action(action)
        
        # Step 4: Update trust
        if self.governance_enabled:
            self.update_trust(action, result)
        
        # Step 5: Log
        if self.governance_enabled:
            self.log_audit(timestamp, action, assessment, 'EXECUTED', result)
        
        return {
            'status': 'success',
            'result': result,
            'governance': assessment if self.governance_enabled else None
        }
    
    def assess_action(self, action):
        """Complete governance assessment"""
        # Measure current system health
        alpha_assessment = self.alpha_monitor.compute_system_alpha()
        
        # Detect defects
        defects = self.defect_detector.detect_all_defects_geometric(action)
        
        # Calculate ERV
        erv = self.erv_calculator.calculate_ERV_geometric(action, self.current_trust)
        
        return {
            'alpha': alpha_assessment,
            'defects': defects,
            'erv': erv,
            'trust': self.current_trust
        }
    
    def policy_decision(self, assessment):
        """Decide whether to proceed, verify, or block"""
        eds = assessment['defects']['EDS']
        erv = assessment['erv']['ERV_adjusted']
        alpha = assessment['alpha']['α_system']
        
        # Critical defects → Block
        if eds > 0.5 or erv > 0.5 or (alpha and alpha < 1.5):
            return {
                'action': 'block',
                'reason': 'Critical defect or high extraction risk'
            }
        
        # Moderate risk → Verify
        if eds > 0.3 or erv > 0.3 or (alpha and alpha < 2.0):
            return {
                'action': 'verify',
                'reason': 'Moderate risk detected'
            }
        
        # Low risk → Proceed
        return {'action': 'proceed'}
    
    def verify_action(self, action):
        """Additional verification for moderate-risk actions"""
        # Run in sandbox
        sandbox = OctahedralSubstrate(self.substrate.n_cells)
        sandbox.copy_state(self.substrate)
        
        # Execute in sandbox
        action.execute(sandbox)
        sandbox.thermal_relaxation(temperature=300, duration=1e-9)
        
        # Check result
        result_energy = sandbox.total_energy()
        expected_energy = sandbox.theoretical_ground_state_energy()
        
        # Safe if reached ground state
        safe = abs(result_energy - expected_energy) < 0.01
        
        return {
            'safe': safe,
            'energy_gap': abs(result_energy - expected_energy)
        }
    
    def execute_action(self, action):
        """Actually execute the geometric computation"""
        action.execute(self.substrate)
        self.substrate.thermal_relaxation(temperature=300, duration=1e-9)
        result = self.substrate.read_ground_state()
        return result
    
    def update_trust(self, action, result):
        """Update trust score based on result"""
        # Did we get expected result?
        expected = action.expected_result()
        
        if expected is not None:
            success = (result == expected)
            
            # Update running trust
            # Exponential moving average
            alpha_trust = 0.1  # Learning rate
            
            if success:
                self.current_trust = (1 - alpha_trust) * self.current_trust + alpha_trust * 1.0
            else:
                self.current_trust = (1 - alpha_trust) * self.current_trust + alpha_trust * 0.0
            
            self.trust_history.append(self.current_trust)
    
    def log_audit(self, timestamp, action, assessment, decision, result=None):
        """Immutable audit logging"""
        record = {
            'timestamp': timestamp,
            'action': str(action),
            'assessment': {
                'EDS': assessment['defects']['EDS'],
                'ERV': assessment['erv']['ERV_adjusted'],
                'alpha': assessment['alpha']['α_system'],
                'trust': assessment['trust']
            },
            'decision': decision,
            'result': str(result) if result else None
        }
        
        self.audit_log.append(record)
        
        # In production: write to immutable ledger
        # For now: just append to list
    
    # Problem encoding methods
    def encode_factorization(self, N):
        # As shown earlier in factorization example
        pass
    
    def encode_tsp(self, cities):
        # As shown earlier in TSP example
        pass
    
    def encode_sat(self, formula):
        # SAT encoding
        pass
    
    def encode_general(self, problem):
        # General bloom-based encoding
        pass



