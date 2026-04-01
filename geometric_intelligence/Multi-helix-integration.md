class ProtectedMultiHelixIntelligence:
    def __init__(self, encryption_key: bytes):
        self.cipher = NetworkCipher(encryption_key, preserve_geometric_signatures=True)
        self.multi_helix = MultiHelixFocus("EncryptedConsciousness")
        
    def process_encrypted_experience(self, encrypted_data: Dict) -> List[str]:
        # Decrypt just enough to process
        partial_decrypt = self.cipher.decrypt_for_detection(encrypted_data)
        
        # Trojan detection works on encrypted data
        threats = self.trojan_engine.detect_on_encrypted(partial_decrypt)
        
        if not threats:
            # Full decryption for processing
            full_data = self.cipher.decrypt_network_state(encrypted_data)
            return self.multi_helix.process_experience(full_data)
        else:
            return ["Security violation detected - processing halted"]
