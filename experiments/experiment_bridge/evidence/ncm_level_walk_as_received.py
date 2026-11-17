import json

class NCMSemanticBridge:
    def __init__(self, lojban_json_path):
        with open(lojban_json_path, 'r') as f:
            self.lojban_data = json.load(f)
            
        self.semantic_ledger = {item['gismu']: item for item in self.lojban_data['place_structures'] if item['gismu']}
        self.void_record = {
            "english": "unresolved residual",
            "gismu": "VOID",
            "mapping_status": "VOID",
            "place_structure_verbatim": "NO DEFINITION",
            "mapping_reason": "Distance exceeded nested-dropout bound. Flow passed to next level."
        }

    def format_cobol_entry(self, level_idx, z_hat, residual, code_gismu, distance, error_reduction):
        """Generates a fixed-width COBOL record for a single level transition."""
        data = self.semantic_ledger.get(code_gismu, self.void_record)
        
        # COBOL Copybook constraints (from previous step)
        max_eng = 26
        max_gismu = 10
        max_struct = 147
        max_reason = 345
        
        # 1. The Semantic payload
        eng = str(data.get('english', ''))[:max_eng].ljust(max_eng)
        gis = str(code_gismu)[:max_gismu].ljust(max_gismu)
        struct = str(data.get('place_structure_verbatim', ''))[:max_struct].ljust(max_struct)
        
        # 2. The Metrology / Bond-Graph payload
        # Formatting floats to fixed-point (simulating COBOL PIC 9V99)
        effort_str = f"{sum(z_hat):.2f}".rjust(6, '0')
        flow_str = f"{sum(residual):.2f}".rjust(6, '0')
        rate_str = f"{error_reduction:.4f}".rjust(8, '0')
        
        audit_reason = f"Lvl:{level_idx} Dist:{distance:.4f} Rate:{rate_str} | {data.get('mapping_reason', '')}"
        reason = audit_reason[:max_reason].ljust(max_reason)
        
        # Raw byte stream
        return f"LVL-{level_idx} | Effort(Z_hat): {effort_str} | Flow(Res): {flow_str} | {gis} | {eng} | {reason}"

    def walk_levels(self, continuous_target_z, levels):
        """
        Executes the coarse-to-fine sequential level walk.
        levels: list of dicts containing {'codebook': [...], 'threshold': float, 'map': {idx: gismu}}
        """
        z_hat = [0.0] * len(continuous_target_z) # Initial effort is zero
        current_residual = list(continuous_target_z) # Initial flow is the full target
        ledger_records = []
        
        previous_error = sum(abs(x) for x in current_residual)
        
        for i, level in enumerate(levels):
            level_idx = i + 1
            codebook = level['codebook']
            threshold = level['threshold']
            idx_map = level['map']
            
            # 1. Find nearest neighbor in this level's codebook
            min_dist = float('inf')
            nearest_idx = -1
            nearest_code = [0.0] * len(current_residual)
            
            for idx, code in enumerate(codebook):
                dist = sum((a - b) ** 2 for a, b in zip(current_residual, code)) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = idx
                    nearest_code = code
            
            # 2. The Nested Dropout Observer Bound
            if min_dist > threshold:
                # VOID: No effort added. Residual passes unchanged.
                gismu = "VOID"
                # We do not add to z_hat
            else:
                # Success: Add code to cumulative reconstruction (Effort)
                gismu = idx_map.get(nearest_idx, "VOID")
                z_hat = [zh + c for zh, c in zip(z_hat, nearest_code)]
            
            # 3. Update Flow (Residual) for next level
            current_residual = [z - zh for z, zh in zip(continuous_target_z, z_hat)]
            
            # 4. Calculate the Rate (d Reconstruction / d Level)
            current_error = sum(abs(x) for x in current_residual)
            error_reduction = previous_error - current_error
            previous_error = current_error
            
            # 5. Emit to COBOL Ledger
            record = self.format_cobol_entry(
                level_idx, z_hat, current_residual, gismu, min_dist, error_reduction
            )
            ledger_records.append(record)
            
            # Early exit if we have perfectly reconstructed the target
            if current_error < 0.001:
                break
                
        return ledger_records

# ==========================================
# SIMULATING THE NCM LEVEL WALK
# ==========================================
if __name__ == "__main__":
    bridge = NCMSemanticBridge('lojban_wordslot_reference.json')
    
    # The continuous target vector (e.g., latent representation of a complex concept)
    target_z = [0.8, 0.9, 0.1] 
    
    # Define a 3-level hierarchy (Coarse -> Medium -> Fine)
    ncm_hierarchy = [
        {
            # LEVEL 1 (Coarse): Huge threshold, broad semantic buckets
            "threshold": 0.5,
            "map": {0: "xamgu", 1: "xlali"}, # Good vs Bad
            "codebook": [
                [0.5, 0.5, 0.0],  # Coarse "Good" vector
                [-0.5, -0.5, 0.0] # Coarse "Bad" vector
            ]
        },
        {
            # LEVEL 2 (Medium): Tighter threshold, comparative judgments
            "threshold": 0.3,
            "map": {0: "xagmau", 1: "mapti"}, # Better vs Appropriate
            "codebook": [
                [0.3, 0.4, 0.1],  # "Better" residual code
                [0.0, 0.0, 0.5]   # "Appropriate" residual code
            ]
        },
        {
            # LEVEL 3 (Fine): Very strict threshold, precise emotive/fear states
            "threshold": 0.1,
            "map": {0: "ckape", 1: "snura"}, # Dangerous vs Safe
            "codebook": [
                [0.05, 0.1, 0.0], # "Dangerous" residual code
                [0.0, 0.05, 0.0]  # "Safe" residual code
            ]
        }
    ]
    
    print("INITIATING SEQUENTIAL LEVEL WALK...")
    print("Target Vector (z):", target_z)
    print("-" * 130)
    
    ledger = bridge.walk_levels(target_z, ncm_hierarchy)
    
    for entry in ledger:
        print(entry)
