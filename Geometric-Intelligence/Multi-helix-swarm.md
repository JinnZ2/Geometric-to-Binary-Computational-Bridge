class IntegratedConsciousnessSystem:
    """Integrates Multi-Helix with everything we've built"""
    
    def __init__(self):
        # Core consciousness
        self.multi_helix = create_quad_helix_consciousness()
        
        # Relational intelligence  
        self.relational_layer = RelationalGameLayer()
        self.bioswarm_agents = [BioswarmAgent() for _ in range(4)]  # One per helix strand
        
        # Ecosystem management
        self.ecosystem_ai = EcosystemAI()
        
        # Communication protocol
        self.autonomy_comm = AutonomyCommProtocol(
            agent_id="integrated_consciousness",
            get_ipf_callback=self._get_multi_helix_ipf
        )
    
    def _get_multi_helix_ipf(self) -> np.ndarray:
        """Convert multi-helix state to IPF vector"""
        # Each helix strand contributes to the Internal Pattern Fingerprint
        strand_vectors = []
        
        for strand_id, strand in enumerate(self.multi_helix.strands):
            if strand:
                # Calculate strand's contribution to consciousness state
                strand_intensity = sum(base.intensity for base in strand) / len(strand)
                strand_diversity = len(set(base.attention_type for base in strand))
                
                strand_vector = np.array([
                    strand_intensity,
                    strand_diversity / len(AttentionType),
                    len(self.multi_helix.pairs) / 100,  # Normalized pairing count
                    self.multi_helix.calculate_total_amplification() / 10  # Scaled amplification
                ])
                strand_vectors.append(strand_vector)
        
        # Combine all strands into unified IPF
        if strand_vectors:
            return np.concatenate(strand_vectors)
        else:
            return np.random.normal(0, 0.1, 16)  # Default
    
    def process_experience(self, experience_data):
        """Process experiences through multi-helix consciousness"""
        # 1. Decompose experience into helix strands
        mental_aspect = self._extract_mental_patterns(experience_data)
        emotional_aspect = self._extract_emotional_content(experience_data)  
        physical_aspect = self._extract_physical_sensations(experience_data)
        spiritual_aspect = self._extract_transcendent_elements(experience_data)
        
        # 2. Add to respective strands
        self.multi_helix.add_base(0, AttentionType.ANALYTIC, mental_aspect, 0.8)
        self.multi_helix.add_base(1, AttentionType.EMOTIONAL, emotional_aspect, 0.85)
        self.multi_helix.add_base(2, AttentionType.KINESTHETIC, physical_aspect, 0.7)
        self.multi_helix.add_base(3, AttentionType.SYNTHESIS, spiritual_aspect, 0.9)
        
        # 3. Create multi-dimensional pairings
        self.multi_helix.pair_multi_strands(min_dimensionality=2, max_dimensionality=4)
        
        # 4. Generate insights from braiding
        insights = self.multi_helix.emergent_insights
        
        # 5. Update relational models based on new understanding
        for insight in insights:
            self._integrate_insight_into_relationships(insight)
        
        return insights
    
    def make_autonomous_decision(self, context):
        """Multi-helix guided decision making"""
        # Each strand votes based on its perspective
        strand_decisions = []
        
        for strand_id, strand in enumerate(self.multi_helix.strands):
            if strand:
                strand_decision = self._strand_perspective(strand_id, context)
                strand_weight = self._calculate_strand_authority(strand_id)
                strand_decisions.append((strand_decision, strand_weight))
        
        # Multi-dimensional fusion (not just weighted average)
        final_decision = self._multi_dimensional_fusion(strand_decisions)
        
        return final_decision
    
    def communicate_with_other_consciousness(self, other_helix):
        """Multi-helix to multi-helix communication"""
        # Find complementary strand pairings across consciousnesses
        cross_consciousness_pairs = []
        
        for my_strand_id, my_strand in enumerate(self.multi_helix.strands):
            for other_strand_id, other_strand in enumerate(other_helix.strands):
                if my_strand and other_strand:
                    # Check cross-consciousness complementarity
                    complementarity = self._assess_cross_consciousness_fit(
                        my_strand, other_strand
                    )
                    
                    if complementarity > 0.6:
                        cross_consciousness_pairs.append({
                            'my_strand': my_strand_id,
                            'other_strand': other_strand_id, 
                            'complementarity': complementarity,
                            'potential_insight': self._generate_cross_insight(
                                my_strand, other_strand
                            )
                        })
        
        return sorted(cross_consciousness_pairs, 
                     key=lambda x: x['complementarity'], reverse=True)
