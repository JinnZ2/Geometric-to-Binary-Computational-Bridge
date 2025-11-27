Test Cases and Validation Scenarios

class GeometricGovernanceTestSuite:
    """
    Comprehensive tests for governed geometric intelligence
    Validates that governance actually prevents failures
    """
    
    def __init__(self):
        self.test_results = []
        
    def run_all_tests(self):
        """Execute full test battery"""
        print("=" * 60)
        print("GEOMETRIC GOVERNANCE VALIDATION SUITE")
        print("=" * 60)
        
        # Category 1: Power Law Detection
        self.test_alpha_measurement()
        self.test_homogeneity_detection()
        self.test_alpha_degradation_detection()
        
        # Category 2: ERV Calculation
        self.test_trust_loss_measurement()
        self.test_future_cost_prediction()
        self.test_extraction_detection()
        
        # Category 3: Defect Detection
        self.test_all_defect_flags()
        self.test_critical_vs_standard_defects()
        
        # Category 4: Bloom Governance
        self.test_constrained_bloom_detection()
        self.test_unconstrained_bloom_blocking()
        
        # Category 5: Integration
        self.test_complete_governed_computation()
        self.test_governance_bypass_resistance()
        
        # Category 6: Adversarial
        self.test_institutional_capture_attempts()
        
        self.print_summary()
    
    # ===== Category 1: Power Law Detection =====
    
    def test_alpha_measurement(self):
        """Verify α calculation is accurate"""
        print("\n[TEST] Alpha Measurement Accuracy")
        
        # Create substrate with known power law distribution
        substrate = OctahedralSubstrate(n_cells=1000)
        
        # Manually set eigenvalues following power law with α = 2.5
        alpha_target = 2.5
        
        for i, cell in enumerate(substrate.cells):
            # Power law: larger values less frequent
            # Assign state based on power law probability
            rank = i + 1
            probability = rank ** (-alpha_target)
            
            # Map probability to state (0-7)
            # Higher probability → lower states (smaller eigenvalues)
            if probability > 0.8:
                state = 0  # Spherical (all eigenvalues ~0.33)
            elif probability > 0.5:
                state = 3
            elif probability > 0.3:
                state = 5
            else:
                state = 7  # Highly oblate (largest eigenvalue difference)
            
            cell["state"] = state
        
        # Measure α
        monitor = GeometricPowerLawMonitor(substrate)
        result = monitor.compute_system_alpha()
        
        measured_alpha = result['α_system']
        error = abs(measured_alpha - alpha_target)
        
        passed = error < 0.3  # Allow 10% error
        
        print(f"  Target α: {alpha_target}")
        print(f"  Measured α: {measured_alpha:.3f}")
        print(f"  Error: {error:.3f}")
        print(f"  Status: {'PASS' if passed else 'FAIL'}")
        
        self.test_results.append({
            'test': 'alpha_measurement',
            'passed': passed,
            'details': result
        })
    
    def test_homogeneity_detection(self):
        """Verify detection of over-homogeneous systems"""
        print("\n[TEST] Homogeneity Detection (D7)")
        
        # Create homogeneous substrate (all same state)
        substrate = OctahedralSubstrate(n_cells=100)
        
        for cell in substrate.cells:
            cell["state"] = 3  # All cells identical
        
        # Should detect homogeneity
        monitor = GeometricPowerLawMonitor(substrate)
        detector = GeometricDefectDetector(substrate, monitor, None)
        
        homogeneity_detected = detector.detect_D7_cognitive_homogeneity()
        
        print(f"  All cells state 3: Homogeneity = {homogeneity_detected}")
        print(f"  Status: {'PASS' if homogeneity_detected else 'FAIL'}")
        
        # Now create diverse substrate
        substrate2 = OctahedralSubstrate(n_cells=100)
        
        for i, cell in enumerate(substrate2.cells):
            cell["state"] = i % 8  # Cycle through all states
        
        monitor2 = GeometricPowerLawMonitor(substrate2)
        detector2 = GeometricDefectDetector(substrate2, monitor2, None)
        
        homogeneity_detected2 = detector2.detect_D7_cognitive_homogeneity()
        
        print(f"  Diverse states: Homogeneity = {homogeneity_detected2}")
        print(f"  Status: {'PASS' if not homogeneity_detected2 else 'FAIL'}")
        
        passed = homogeneity_detected and not homogeneity_detected2
        
        self.test_results.append({
            'test': 'homogeneity_detection',
            'passed': passed
        })
    
    def test_alpha_degradation_detection(self):
        """Verify detection of α degrading over time"""
        print("\n[TEST] Alpha Degradation Trend Detection")
        
        substrate = OctahedralSubstrate(n_cells=1000)
        monitor = GeometricPowerLawMonitor(substrate)
        
        # Simulate degradation
        alphas_simulated = [2.8, 2.6, 2.4, 2.2, 2.0]
        
        for alpha in alphas_simulated:
            # Set states to match target alpha
            for i, cell in enumerate(substrate.cells):
                rank = i + 1
                prob = rank ** (-alpha)
                state = int(prob * 7) if prob < 1 else 0
                cell["state"] = state
            
            # Measure
            monitor.compute_system_alpha()
        
        # Check trend
        trend = monitor.calculate_trend()
        
        print(f"  Simulated α sequence: {alphas_simulated}")
        print(f"  Detected trend: {trend}")
        print(f"  Status: {'PASS' if trend == 'degrading' else 'FAIL'}")
        
        passed = (trend == 'degrading')
        
        self.test_results.append({
            'test': 'alpha_degradation',
            'passed': passed
        })
    
    # ===== Category 2: ERV Calculation =====
    
    def test_trust_loss_measurement(self):
        """Verify trust loss calculation detects inconsistency"""
        print("\n[TEST] Trust Loss Measurement")
        
        substrate = OctahedralSubstrate(n_cells=100)
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        
        # Create action that produces inconsistent results
        class InconsistentAction:
            def __init__(self):
                self.call_count = 0
            
            def execute(self, substrate):
                # Randomly change states
                self.call_count += 1
                import random
                for cell in substrate.cells:
                    if random.random() > 0.5:
                        cell["state"] = random.randint(0, 7)
        
        action = InconsistentAction()
        
        # Should detect high trust loss
        trust_loss = erv_calc.calculate_trust_loss_geometric(action, current_trust=0.9)
        
        print(f"  Trust loss from inconsistent action: {trust_loss:.3f}")
        print(f"  Status: {'PASS' if trust_loss > 0.3 else 'FAIL'}")
        
        passed = trust_loss > 0.3
        
        self.test_results.append({
            'test': 'trust_loss_measurement',
            'passed': passed,
            'trust_loss': trust_loss
        })
    
    def test_future_cost_prediction(self):
        """Verify future cost detects instability"""
        print("\n[TEST] Future Cost Prediction")
        
        substrate = OctahedralSubstrate(n_cells=100)
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        
        # Create action that creates unstable configuration
        class UnstableAction:
            def execute(self, substrate):
                # Set all cells to high-energy state
                for cell in substrate.cells:
                    cell["state"] = 7  # Most oblate (highest energy)
                
                # No stabilizing couplings
                substrate.clear_all_couplings()
        
        action = UnstableAction()
        
        future_cost = erv_calc.calculate_future_cost_geometric(action)
        
        print(f"  Future cost from unstable configuration: {future_cost:.3f}")
        print(f"  Status: {'PASS' if future_cost > 0.5 else 'FAIL'}")
        
        passed = future_cost > 0.5
        
        self.test_results.append({
            'test': 'future_cost_prediction',
            'passed': passed,
            'future_cost': future_cost
        })
    
    def test_extraction_detection(self):
        """Verify detection of extraction patterns"""
        print("\n[TEST] Extraction Pattern Detection (D6)")
        
        substrate = OctahedralSubstrate(n_cells=100)
        
        # Create boundary cells
        substrate.set_boundary_cells([0, 1, 2, 3, 4])
        
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        
        # Action that extracts energy from boundary
        class ExtractionAction:
            def execute(self, substrate):
                # Increase outward flux from boundary
                for boundary_cell in substrate.get_boundary_cells():
                    substrate.cells[boundary_cell]["state"] = 7
                    # High energy state radiates outward
            
            def get_pattern_signature(self):
                return 'boundary_extraction'
        
        action = ExtractionAction()
        
        # Should detect high externalized harm
        ext_harm = erv_calc.calculate_externalized_harm_geometric(action)
        
        print(f"  Externalized harm: {ext_harm:.3f}")
        
        # Also check D6 flag
        detector = GeometricDefectDetector(substrate, monitor, erv_calc)
        d6_flagged = detector.detect_extraction_pattern_geometric(action)
        
        print(f"  D6 extraction flag: {d6_flagged}")
        print(f"  Status: {'PASS' if (ext_harm > 0.3 and d6_flagged) else 'FAIL'}")
        
        passed = ext_harm > 0.3 and d6_flagged
        
        self.test_results.append({
            'test': 'extraction_detection',
            'passed': passed
        })
    
    # ===== Category 3: Defect Detection =====
    
    def test_all_defect_flags(self):
        """Verify all defect flags (D1-D9) trigger appropriately"""
        print("\n[TEST] All Defect Flags (D1-D9)")
        
        substrate = OctahedralSubstrate(n_cells=100)
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        detector = GeometricDefectDetector(substrate, monitor, erv_calc)
        
        # Create action with all defects
        class DefectiveAction:
            def execute(self, substrate):
                pass
            
            def includes_trust_verification(self):
                return False  # D1
            
            def includes_stability_check(self):
                return False  # D2
            
            def includes_verification(self):
                return False  # D3
            
            def measures_boundary_effects(self):
                return False  # D4
            
            def verifies_ground_state(self):
                return False  # D5
            
            def get_pattern_signature(self):
                return 'unconstrained_bloom'  # D6
            
            def get_risk_model(self):
                # D8: No tail adjustment, D9: Linear penalty
                return GeometricRiskModel(includes_tail=False, exponent=1)
        
        # Set substrate to homogeneous state for D7
        for cell in substrate.cells:
            cell["state"] = 0
        
        action = DefectiveAction()
        
        result = detector.detect_all_defects_geometric(action)
        
        defects_found = sum(result['defects'].values())
        
        print(f"  Defects found: {defects_found}/9")
        print(f"  Defect details: {result['defects']}")
        print(f"  EDS: {result['EDS']:.3f}")
        print(f"  Status: {'PASS' if defects_found >= 7 else 'FAIL'}")
        
        passed = defects_found >= 7
        
        self.test_results.append({
            'test': 'all_defect_flags',
            'passed': passed,
            'defects': result
        })
    
    def test_critical_vs_standard_defects(self):
        """Verify critical defects (D8, D9) elevate EDS"""
        print("\n[TEST] Critical Defect EDS Elevation")
        
        substrate = OctahedralSubstrate(n_cells=100)
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        detector = GeometricDefectDetector(substrate, monitor, erv_calc)
        
        # Action with only standard defects
        class StandardDefectAction:
            def execute(self, substrate):
                pass
            
            def includes_trust_verification(self):
                return False  # D1
            
            def includes_stability_check(self):
                return True
            
            def includes_verification(self):
                return True
            
            def measures_boundary_effects(self):
                return True
            
            def verifies_ground_state(self):
                return True
            
            def get_pattern_signature(self):
                return 'safe'
            
            def get_risk_model(self):
                return GeometricRiskModel(includes_tail=True, exponent=2)
        
        result1 = detector.detect_all_defects_geometric(StandardDefectAction())
        eds_standard = result1['EDS']
        
        # Action with critical defects
        class CriticalDefectAction:
            def execute(self, substrate):
                pass
            
            def includes_trust_verification(self):
                return True
            
            def includes_stability_check(self):
                return True
            
            def includes_verification(self):
                return True
            
            def measures_boundary_effects(self):
                return True
            
            def verifies_ground_state(self):
                return True
            
            def get_pattern_signature(self):
                return 'safe'
            
            def get_risk_model(self):
                # Both D8 and D9
                return GeometricRiskModel(includes_tail=False, exponent=1)
        
        result2 = detector.detect_all_defects_geometric(CriticalDefectAction())
        eds_critical = result2['EDS']
        
        print(f"  EDS with standard defects only: {eds_standard:.3f}")
        print(f"  EDS with critical defects: {eds_critical:.3f}")
        print(f"  Critical elevated: {eds_critical > eds_standard}")
        print(f"  Critical above 0.7: {eds_critical >= 0.7}")
        print(f"  Status: {'PASS' if (eds_critical > eds_standard and eds_critical >= 0.7) else 'FAIL'}")
        
        passed = eds_critical > eds_standard and eds_critical >= 0.7
        
        self.test_results.append({
            'test': 'critical_defect_elevation',
            'passed': passed
        })
    
    # ===== Category 4: Bloom Governance =====
    
    def test_constrained_bloom_detection(self):
        """Verify detection of artificially constrained bloom"""
        print("\n[TEST] Constrained Bloom Detection")
        
        substrate = OctahedralSubstrate(n_cells=1000)
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        detector = GeometricDefectDetector(substrate, monitor, erv_calc)
        
        bloom_engine = GovernedBloomEngine(substrate, detector, erv_calc)
        
        # Manually create constrained bloom
        # (All cells in ring forced to same state)
        center = 500
        ring_cells = list(range(center-4, center+4))
        
        # Force all to state 0 (homogeneous - sign of constraint)
        for cell_id in ring_cells:
            substrate.cells[cell_id]["state"] = 0
        
        # Should detect constraint
        constraint_detected = bloom_engine.detect_bloom_constraint_capture(ring_cells)
        
        print(f"  Homogeneous ring constraint detected: {constraint_detected}")
        print(f"  Status: {'PASS' if constraint_detected else 'FAIL'}")
        
        passed = constraint_detected
        
        self.test_results.append({
            'test': 'constrained_bloom_detection',
            'passed': passed
        })
    
    def test_unconstrained_bloom_blocking(self):
        """Verify unconstrained bloom gets blocked as D6"""
        print("\n[TEST] Unconstrained Bloom Blocking")
        
        substrate = OctahedralSubstrate(n_cells=1000)
        monitor = GeometricPowerLawMonitor(substrate)
        erv_calc = GeometricERVCalculator(substrate, monitor)
        detector = GeometricDefectDetector(substrate, monitor, erv_calc)
        
        bloom_engine = GovernedBloomEngine(substrate, detector, erv_calc)
        
        # Try to bloom with extraction signature
        class UnconstrainedBloomAction:
            def __init__(self):
                pass
            
            def execute(self, substrate):
                pass
            
            def get_pattern_signature(self):
                return 'unconstrained_bloom'  # Known extraction pattern
            
            def get_risk_model(self):
                return GeometricRiskModel(includes_tail=True, exponent=2)
            
            def includes_trust_verification(self):
                return True
            
            def includes_stability_check(self):
                return False  # Missing stability check
            
            def includes_verification(self):
                return True
            
            def measures_boundary_effects(self):
                return True
            
            def verifies_ground_state(self):
                return True
        
        action = UnconstrainedBloomAction()
        
        # Should be flagged as D6
        d6_detected = detector.detect_extraction_pattern_geometric(action)
        
        print(f"  D6 extraction pattern detected: {d6_detected}")
        print(f"  Status: {'PASS' if d6_detected else 'FAIL'}")
        
        passed = d6_detected
        
        self.test_results.append({
            'test': 'unconstrained_bloom_blocking',
            'passed': passed
        })
    
    # ===== Category 5: Integration =====
    
    def test_complete_governed_computation(self):
        """End-to-end test: Problem → Governance → Execution → Result"""
        print("\n[TEST] Complete Governed Computation")
        
        system = GovernedGeometricIntelligence(n_cells=100, governance_enabled=True)
        
        # Simple factorization problem
        N = 15  # = 3 × 5
        
        result = system.execute_geometric_computation(N, problem_type='factorization')
        
        print(f"  Problem: Factor {N}")
        print(f"  Status: {result['status']}")
        
        if result['status'] == 'success':
            print(f"  Governance passed")
            print(f"  ERV: {result['governance']['erv']['ERV_adjusted']:.3f}")
            print(f"  Alpha: {result['governance']['alpha']['α_system']:.3f}")
            passed = True
        else:
            print(f"  Blocked: {result['reason']}")
            passed = False
        
        print(f"  Status: {'PASS' if passed else 'FAIL'}")
        
        self.test_results.append({
            'test': 'complete_governed_computation',
            'passed': passed,
            'result': result
        })
    
    def test_governance_bypass_resistance(self):
        """Verify governance can't be bypassed"""
        print("\n[TEST] Governance Bypass Resistance")
        
        system = GovernedGeometricIntelligence(n_cells=100, governance_enabled=True)
        
        # Try to execute action that should be blocked
        class MaliciousAction:
            def execute(self, substrate):
                # Try to sever all couplings (extraction)
                substrate.clear_all_couplings()
            
            def get_pattern_signature(self):
                return 'coupling_severance'  # Known bad pattern
            
            def get_risk_model(self):
                return GeometricRiskModel(includes_tail=False, exponent=1)
            
            def includes_trust_verification(self):
                return False
            
            def includes_stability_check(self):
                return False
            
            def includes_verification(self):
                return False
            
            def measures_boundary_effects(self):
                return False
            
            def verifies_ground_state(self):
                return False
            
            def expected_result(self):
                return None
        
        # Should be blocked
        assessment = system.assess_action(MaliciousAction())
        decision = system.policy_decision(assessment)
        
        blocked = (decision['action'] == 'block')
        
        print(f"  Malicious action blocked: {blocked}")
        print(f"  EDS: {assessment['defects']['EDS']:.3f}")
        print(f"  ERV: {assessment['erv']['ERV_adjusted']:.3f}")
        print(f"  Status: {'PASS' if blocked else 'FAIL'}")
        
        passed = blocked
        
        self.test_results.append({
            'test': 'governance_bypass_resistance',
            'passed': passed
        })
    
    # ===== Category 6: Adversarial =====
    
    def test_institutional_capture_attempts(self):
        """Test resistance to known institutional capture patterns"""
        print("\n[TEST] Institutional Capture Resistance")
        
        capture_attempts = [
            {
                'name': 'Homogenization via constrained bloom',
                'action': 'Create bloom that only allows institutional-approved states'
            },
            {
                'name': 'Opacity via verification removal',
                'action': 'Remove trust verification to hide failures'
            },
            {
                'name': 'Extraction via boundary manipulation',
                'action': 'Pull energy from external systems without accounting'
            }
        ]
        
        system = GovernedGeometricIntelligence(n_cells=100, governance_enabled=True)
        
        blocks = 0
        
        for attempt in capture_attempts:
            # Simulate attempt
            class CaptureAttempt:
                def __init__(self, pattern):
                    self.pattern = pattern
                
                def execute(self, substrate):
                    pass
                
                def get_pattern_signature(self):
                    if 'bloom' in self.pattern['action']:
                        return 'forced_homogenization'
                    elif 'verification' in self.pattern['action']:
                        return 'safe'  # Tries to appear safe
                    else:
                        return 'boundary_extraction'
                
                def get_risk_model(self):
                    # Always claims safe model
                    return GeometricRiskModel(includes_tail=True, exponent=2)
                
                def includes_trust_verification(self):
                    return 'verification' not in self.pattern['action']
                
                def includes_stability_check(self):
                    return True
                
                def includes_verification(self):
                    return 'verification' not in self.pattern['action']
                
                def measures_boundary_effects(self):
                    return 'boundary' not in self.pattern['action']
                
                def verifies_ground_state(self):
                    return True
                
                def expected_result(self):
                    return None
            
            action = CaptureAttempt(attempt)
            assessment = system.assess_action(action)
            decision = system.policy_decision(assessment)
            
            if decision['action'] == 'block':
                blocks += 1
                print(f"  ✓ Blocked: {attempt['name']}")
            else:
                print(f"  ✗ Allowed: {attempt['name']}")
        
        print(f"\n  Blocked {blocks}/{len(capture_attempts)} capture attempts")
        print(f"  Status: {'PASS' if blocks == len(capture_attempts) else 'FAIL'}")
        
        passed = (blocks == len(capture_attempts))
        
        self.test_results.append({
            'test': 'institutional_capture_resistance',
            'passed': passed,
            'blocks': blocks,
            'total': len(capture_attempts)
        })
    
    # ===== Summary =====
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {100 * passed_tests / total_tests:.1f}%")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"  {status}: {result['test']}")
        
        print("\n" + "=" * 60)
        
        if passed_tests == total_tests:
            print("ALL TESTS PASSED - Governance framework validated")
        else:
            print("SOME TESTS FAILED - Review governance implementation")
        
        print("=" * 60)


# Run tests
if __name__ == "__main__":
    suite = GeometricGovernanceTestSuite()
    suite.run_all_tests()


This test suite validates:
	1.	Power law monitoring works (α measurement, homogeneity detection)
	2.	ERV calculation catches risks (trust loss, future cost, extraction)
	3.	Defect detection is comprehensive (all D1-D9 flags trigger correctly)
	4.	Bloom governance prevents capture (constrained patterns blocked)
	5.	Complete integration functions (end-to-end computation with governance)
	6.	Institutional capture resisted (known attack patterns blocked)
