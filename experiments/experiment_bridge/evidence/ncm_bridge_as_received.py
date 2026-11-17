import json
import math

class NCMBridge:
    def __init__(self, codebook_path, lojban_json_path, dropout_threshold=0.5):
        # Load the Lojban semantic map
        with open(lojban_json_path, 'r') as f:
            self.lojban_data = json.load(f)
            
        # Load the NCM Codebook (simulated as a list of vectors)
        # In a real NCM, this is the VQ dictionary (e.g., shape [1024, 128])
        self.codebook = [
            [0.1, 0.2, 0.3], # Index 0 -> maps to "better" (xagmau)
            [0.9, 0.8, 0.7], # Index 1 -> maps to "worse" (xagme'a)
            [0.0, 0.0, 0.0]  # Index 2 -> Reserved for VOID
        ]
        
        # The semantic mapping between codebook index and Lojban gismu
        self.index_to_gismu = {
            0: "xagmau", 
            1: "xagme'a",
            2: "VOID"
        }
        
        self.threshold = dropout_threshold
        
        # Pull the exact verbatim structures from the JSON for the COBOL bridge
        self.semantic_ledger = {item['gismu']: item for item in self.lojban_data['place_structures'] if item['gismu']}
        self.void_record = {
            "english": "unresolved residual",
            "class": "void",
            "gismu": "VOID",
            "structure_status": "VOID",
            "mapping_status": "VOID",
            "place_structure_verbatim": "NO DEFINITION",
            "mapping_reason": "Distance to nearest codebook vector exceeded nested-dropout bound."
        }

    def _euclidean_distance(self, vec1, vec2):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))

    def process_residual(self, continuous_residual, evidential_cmavo="za'a"):
        """
        Takes the continuous residual (Flow), snaps it to the codebook (Coupler),
        and generates the fixed-width ledger entry.
        """
        # 1. Find the nearest codebook vector (Argmin)
        min_dist = float('inf')
        nearest_idx = -1
        
        for idx, code in enumerate(self.codebook):
            dist = self._euclidean_distance(continuous_residual, code)
            if dist < min_dist:
                min_dist = dist
                nearest_idx = idx

        # 2. Apply the Nested-Dropout Threshold Check
        if min_dist > self.threshold:
            # THE VOID PROTOCOL
            record_data = self.void_record
            # We override the mapping reason to include the exact measured distance
            record_data["mapping_reason"] = f"VOID threshold exceeded. Distance: {min_dist:.4f} > {self.threshold}"
        else:
            # SUCCESSFUL QUANTIZATION
            gismu = self.index_to_gismu.get(nearest_idx, "VOID")
            record_data = self.semantic_ledger.get(gismu, self.void_record)

        # 3. Format for the COBOL Ledger (Fixed-Width Apertures)
        # We emulate the PIC X(n) space-padding here
        return self._generate_cobol_record(record_data, evidential_cmavo, min_dist)

    def _generate_cobol_record(self, data, evidential, distance):
        # Based on the max lengths generated in the previous Copybook step
        max_eng = 26
        max_class = 15
        max_gismu = 10
        max_struct = 147
        max_reason = 345

        eng = str(data.get('english', ''))[:max_eng].ljust(max_eng)
        cls = str(data.get('class', ''))[:max_class].ljust(max_class)
        gis = str(data.get('gismu', ''))[:max_gismu].ljust(max_gismu)
        stat = str(data.get('structure_status', ''))[:10].ljust(10)
        map_stat = str(data.get('mapping_status', ''))[:10].ljust(10)
        struct = str(data.get('place_structure_verbatim', ''))[:max_struct].ljust(max_struct)
        
        # Inject the evidential and distance metric into the audit reason
        audit_reason = f"[{evidential}] Dist: {distance:.4f} | {data.get('mapping_reason', '')}"
        reason = audit_reason[:max_reason].ljust(max_reason)

        # Simulating the raw byte stream that would be written to the COBOL file
        return f"{eng}{cls}{gis}{stat}{map_stat}{struct}{reason}"

# ==========================================
# TEST DRIVE THE BRIDGE
# ==========================================
if __name__ == "__main__":
    # Initialize the bridge with a strict threshold of 0.3
    bridge = NCMBridge('lojban_wordslot_reference.json', 'lojban_wordslot_reference.json', dropout_threshold=0.3)

    print("--- TEST 1: Good Quantization (Hits 'better' vector) ---")
    # Residual is close to [0.1, 0.2, 0.3]
    residual_1 = [0.15, 0.22, 0.28] 
    cobol_record_1 = bridge.process_residual(residual_1)
    print(cobol_record_1)
    print("\n")

    print("--- TEST 2: The VOID Intercept (Residual doesn't fit) ---")
    # Residual is far from any codebook vector
    residual_2 = [0.8, 0.1, 0.5] 
    cobol_record_2 = bridge.process_residual(residual_2, evidential_cmavo="ru'a") # ru'a = I postulate
    print(cobol_record_2)
    print("\n")
