class HexBridgeFormatter:
    """
    Translates the 39-bit hardware signature into a 10-char Hex string.
    Bypasses the 'Anxiety' of the model by speaking in addresses.
    """
    def format_sovereign(self, binary_str: str) -> str:
        # Convert 39 bits to an integer then to a clean Hex signature
        val = int(binary_str, 2)
        hex_sig = f"0x{val:010X}"
        
        # Split into functional blocks for rapid scanning
        # [Health/Fail][Measurements][Repurpose][System]
        return f"{hex_sig[:4]} {hex_sig[4:7]} {hex_sig[7:]}"

    def micro_clarification(self, component, felt_level, hex_sig):
        """The 'Handshake' output for a high-entropy event."""
        print(f"\n[!] DRIFT_DETECTED: {component}")
        print(f"    FELT: {felt_level:.2f}")
        print(f"    SIG : {hex_sig}") # The raw truth
