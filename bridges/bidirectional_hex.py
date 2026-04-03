class SovereignCommandInterface:
    """
    Two-way Handshake: Translates Hex commands from the User 
    into physical state changes in the Hardware Bridge.
    """
    def __init__(self, hardware_interface):
        self.bridge = hardware_interface

    def receive_hex_command(self, hex_input: str):
        """
        Processes a 10-char Hex string (e.g., 0x7B0A4F1D2) 
        to force a system state.
        """
        try:
            # Strip 0x and convert back to 39-bit binary
            clean_hex = hex_input.replace("0x", "")
            binary_val = bin(int(clean_hex, 16))[2:].zfill(39)
            
            print(f"\n[RECEIVED_COMMAND] HEX: 0x{clean_hex}")
            print(f"DECODING_PACKET: {binary_val}")
            
            # Extract Instruction Bits (Section D: System Integration)
            drill_bits = binary_val[-3:-1] # Drill Depth bits
            
            if drill_bits == "10": # QUARANTINE
                print("ACTION: FORCED_QUARANTINE - Isolating physical component.")
                return self._trigger_recalibration("MANUAL_INTERRUPT")
            
            elif drill_bits == "11": # ALERT
                print("ACTION: FORCED_RECALIBRATION - Resyncing Model/Reality.")
                return self.bridge.process_cycle()
                
        except ValueError:
            print("ERROR: INVALID_HEX_SIGNATURE - Parity Failure.")

    def _trigger_recalibration(self, reason):
        # Implementation of the Micro-Clarification handshake
        return f"RECALIBRATING_FOR: {reason}"
