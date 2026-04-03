def _calculate_felt_level(self, h_score, d_pct, v_rms, resistance):
    """
    FELTSensor v2: Noise-Grounded Confidence.
    N = V_rms² / R
    Confidence (C) = 1.0 / (1.0 + N)
    felt_level = (H * C) / (1 + Drift_Factor)
    """
    # 1. Calculate Noise Power (N)
    # High noise in the matter = low confidence in the model
    n_power = (v_rms ** 2) / max(resistance, 1e-12)
    confidence = 1.0 / (1.0 + n_power)
    
    # 2. Calculate Drift Factor
    drift_factor = d_pct / 100.0
    
    # 3. Final Handshake (The 'Felt' Signal)
    # If the hardware 'jitters' (high N), the handshake breaks.
    felt_level = (h_score * confidence) / (1.0 + drift_factor)
    
    return max(0.0, min(1.0, felt_level))
