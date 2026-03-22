# Inflection Bridge Encoder

# Tonal curves, frequency modulation, pitch contours, and vibrational mathematics -> binary

import numpy as np
import hashlib

from bridge.abstract_encoder import BinaryBridgeEncoder


class InflectionBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes inflection/tonal data into binary representation.
    - Tonal Direction: rising = 1, falling = 0
    - Frequency Change Rate: fast modulation = 1, slow = 0
    - Inflection Amplitude: dramatic = 1, subtle = 0
    - Curve Shape: convex = 1, concave = 0
    - Cultural Tonal Signature: matches pattern = 1, doesn't match = 0
    """

    def __init__(self, freq_change_threshold=50, amplitude_threshold=100, curve_threshold=0.5):
        """
        freq_change_threshold: Rate of frequency change in Hz/second
        amplitude_threshold: Total frequency change in Hz
        curve_threshold: Threshold for curve shape detection
        """
        super().__init__("inflection")
        self.freq_change_threshold = freq_change_threshold
        self.amplitude_threshold = amplitude_threshold
        self.curve_threshold = curve_threshold

        # Golden ratio for natural tonal relationships
        self.PHI = (1 + np.sqrt(5)) / 2

    def from_geometry(self, geometry_data):
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if not self.input_geometry:
            raise ValueError("Inflection geometry data not loaded.")

        bits = []

        # Tonal Direction: rising vs falling
        pitch_contour = self.input_geometry.get("pitch_contour", [])
        if len(pitch_contour) > 1:
            for i in range(1, len(pitch_contour)):
                rising = pitch_contour[i] > pitch_contour[i-1]
                bits.append("1" if rising else "0")

        # Frequency Change Rate: fast vs slow modulation
        for rate in self.input_geometry.get("modulation_rates", []):
            bits.append("1" if rate >= self.freq_change_threshold else "0")

        # Inflection Amplitude: dramatic vs subtle
        freq_deltas = self.input_geometry.get("frequency_deltas", [])
        for delta in freq_deltas:
            dramatic = abs(delta) >= self.amplitude_threshold
            bits.append("1" if dramatic else "0")

        # Curve Shape: detect convexity (acceleration pattern)
        if len(pitch_contour) >= 3:
            for i in range(1, len(pitch_contour) - 1):
                # Second derivative approximation
                curvature = (pitch_contour[i+1] - pitch_contour[i]) - (pitch_contour[i] - pitch_contour[i-1])
                convex = curvature > 0
                bits.append("1" if convex else "0")

        # Vibrato Presence: encode vibrato depth
        vibrato_threshold = 5  # Hz
        for depth in self.input_geometry.get("vibrato_depth", []):
            bits.append("1" if depth >= vibrato_threshold else "0")

        # Harmonic Ratios: detect phi-based or simple integer ratios
        for ratio in self.input_geometry.get("harmonic_ratios", []):
            close_to_phi = abs(ratio - self.PHI) < 0.1
            close_to_integer = abs(ratio - round(ratio)) < 0.1
            bits.append("1" if (close_to_phi or close_to_integer) else "0")

        # Emotional Signature: high vs low emotional intensity
        emotional_threshold = 0.5
        for intensity in self.input_geometry.get("emotional_signature", []):
            bits.append("1" if intensity >= emotional_threshold else "0")

        self.binary_output = "".join(bits)
        return self.binary_output

    def analyze_inflection_patterns(self):
        """Provide detailed analysis of inflection encoding patterns"""
        if not self.input_geometry:
            return "No inflection data loaded."

        analysis = {
            "tonal_direction_analysis": self._analyze_tonal_direction(),
            "modulation_analysis": self._analyze_frequency_modulation(),
            "amplitude_analysis": self._analyze_inflection_amplitude(),
            "curve_analysis": self._analyze_curve_shapes(),
            "vibrato_analysis": self._analyze_vibrato_patterns(),
            "harmonic_analysis": self._analyze_harmonic_ratios(),
            "emotional_analysis": self._analyze_emotional_signature(),
            "cultural_analysis": self._analyze_cultural_patterns()
        }
        return analysis

    def _analyze_tonal_direction(self):
        """Analyze rising/falling tonal patterns"""
        pitch_contour = self.input_geometry.get("pitch_contour", [])
        if len(pitch_contour) < 2:
            return "Insufficient pitch data"

        rises = sum(1 for i in range(1, len(pitch_contour)) if pitch_contour[i] > pitch_contour[i-1])
        falls = sum(1 for i in range(1, len(pitch_contour)) if pitch_contour[i] < pitch_contour[i-1])

        return {
            "total_transitions": len(pitch_contour) - 1,
            "rising_count": rises,
            "falling_count": falls,
            "rise_fall_ratio": rises / falls if falls > 0 else float('inf'),
            "dominant_direction": "rising" if rises > falls else "falling",
            "pitch_range": (float(min(pitch_contour)), float(max(pitch_contour))),
            "average_pitch": float(np.mean(pitch_contour))
        }

    def _analyze_frequency_modulation(self):
        """Analyze rate of frequency changes"""
        mod_rates = self.input_geometry.get("modulation_rates", [])
        if not mod_rates:
            return "No modulation data"

        return {
            "average_modulation_rate": float(np.mean(mod_rates)),
            "peak_modulation": float(max(mod_rates)),
            "modulation_volatility": float(np.std(mod_rates)),
            "fast_modulation_count": len([r for r in mod_rates if r >= self.freq_change_threshold]),
            "modulation_consistency": 1 - (np.std(mod_rates) / np.mean(mod_rates)) if np.mean(mod_rates) > 0 else 0
        }

    def _analyze_inflection_amplitude(self):
        """Analyze dramatic vs subtle inflections"""
        deltas = self.input_geometry.get("frequency_deltas", [])
        if not deltas:
            return "No frequency delta data"

        return {
            "average_amplitude": float(np.mean([abs(d) for d in deltas])),
            "max_amplitude": float(max([abs(d) for d in deltas])),
            "dramatic_inflections": len([d for d in deltas if abs(d) >= self.amplitude_threshold]),
            "subtle_inflections": len([d for d in deltas if abs(d) < self.amplitude_threshold]),
            "amplitude_range": float(max(deltas) - min(deltas))
        }

    def _analyze_curve_shapes(self):
        """Analyze the geometric shapes of pitch curves"""
        pitch_contour = self.input_geometry.get("pitch_contour", [])
        if len(pitch_contour) < 3:
            return "Insufficient data for curve analysis"

        curvatures = []
        for i in range(1, len(pitch_contour) - 1):
            curvature = (pitch_contour[i+1] - pitch_contour[i]) - (pitch_contour[i] - pitch_contour[i-1])
            curvatures.append(curvature)

        convex_count = len([c for c in curvatures if c > 0])
        concave_count = len([c for c in curvatures if c < 0])

        return {
            "convex_curves": convex_count,
            "concave_curves": concave_count,
            "curve_balance": convex_count / concave_count if concave_count > 0 else float('inf'),
            "average_curvature": float(np.mean(curvatures)),
            "curve_volatility": float(np.std(curvatures)),
            "geometric_pattern": self._identify_geometric_pattern(pitch_contour)
        }

    def _analyze_vibrato_patterns(self):
        """Analyze vibrato characteristics"""
        vibrato = self.input_geometry.get("vibrato_depth", [])
        if not vibrato:
            return "No vibrato data"

        return {
            "average_vibrato_depth": float(np.mean(vibrato)),
            "vibrato_range": (float(min(vibrato)), float(max(vibrato))),
            "vibrato_consistency": float(1 - np.std(vibrato) / np.mean(vibrato)) if np.mean(vibrato) > 0 else 0,
            "strong_vibrato_count": len([v for v in vibrato if v >= 5]),
            "vibrato_pattern": self._detect_vibrato_pattern(vibrato)
        }

    def _analyze_harmonic_ratios(self):
        """Analyze mathematical relationships in harmonics"""
        ratios = self.input_geometry.get("harmonic_ratios", [])
        if not ratios:
            return "No harmonic ratio data"

        phi_matches = len([r for r in ratios if abs(r - self.PHI) < 0.1])
        integer_matches = len([r for r in ratios if abs(r - round(r)) < 0.1])

        return {
            "total_ratios": len(ratios),
            "phi_based_ratios": phi_matches,
            "integer_based_ratios": integer_matches,
            "average_ratio": float(np.mean(ratios)),
            "ratio_complexity": float(np.std(ratios)),
            "mathematical_signature": self._classify_harmonic_signature(ratios)
        }

    def _analyze_emotional_signature(self):
        """Analyze emotional intensity patterns"""
        emotional = self.input_geometry.get("emotional_signature", [])
        if not emotional:
            return "No emotional data"

        return {
            "average_intensity": float(np.mean(emotional)),
            "peak_intensity": float(max(emotional)),
            "intensity_range": (float(min(emotional)), float(max(emotional))),
            "high_intensity_moments": len([e for e in emotional if e >= 0.7]),
            "emotional_volatility": float(np.std(emotional)),
            "emotional_pattern": self._identify_emotional_pattern(emotional)
        }

    def _analyze_cultural_patterns(self):
        """Analyze cultural tonal signatures"""
        pattern_id = self.input_geometry.get("cultural_pattern", "unknown")
        pitch_contour = self.input_geometry.get("pitch_contour", [])

        if not pitch_contour:
            return {"pattern_identified": pattern_id, "confidence": 0.0}

        confidence = self._match_cultural_pattern(pitch_contour, pattern_id)

        return {
            "pattern_identified": pattern_id,
            "pattern_confidence": confidence,
            "cultural_signature": self._encode_cultural_signature(pattern_id),
            "indigenous_markers": self._detect_indigenous_markers(pitch_contour)
        }

    def _identify_geometric_pattern(self, contour):
        """Identify geometric shape of pitch contour"""
        if len(contour) < 3:
            return "insufficient_data"

        mid_point = len(contour) // 2
        first_half_rising = all(contour[i] <= contour[i+1] for i in range(mid_point-1))
        second_half_falling = all(contour[i] >= contour[i+1] for i in range(mid_point, len(contour)-1))

        if first_half_rising and second_half_falling:
            return "arch_pattern"

        first_half_falling = all(contour[i] >= contour[i+1] for i in range(mid_point-1))
        second_half_rising = all(contour[i] <= contour[i+1] for i in range(mid_point, len(contour)-1))

        if first_half_falling and second_half_rising:
            return "valley_pattern"

        oscillations = 0
        for i in range(1, len(contour) - 1):
            if (contour[i] > contour[i-1] and contour[i] > contour[i+1]) or \
               (contour[i] < contour[i-1] and contour[i] < contour[i+1]):
                oscillations += 1

        if oscillations >= len(contour) // 3:
            return "spiral_oscillating_pattern"

        return "complex_pattern"

    def _detect_vibrato_pattern(self, vibrato):
        """Detect patterns in vibrato usage"""
        if len(vibrato) < 2:
            return "insufficient_data"

        increasing = all(vibrato[i] <= vibrato[i+1] for i in range(len(vibrato)-1))
        if increasing:
            return "crescendo_vibrato"

        decreasing = all(vibrato[i] >= vibrato[i+1] for i in range(len(vibrato)-1))
        if decreasing:
            return "diminuendo_vibrato"

        if np.std(vibrato) < 2:
            return "consistent_vibrato"

        return "variable_vibrato"

    def _classify_harmonic_signature(self, ratios):
        """Classify the mathematical signature of harmonics"""
        if not ratios:
            return "no_data"

        phi_count = len([r for r in ratios if abs(r - self.PHI) < 0.1])
        integer_count = len([r for r in ratios if abs(r - round(r)) < 0.1])

        if phi_count >= len(ratios) * 0.5:
            return "phi_dominant_natural_mathematics"

        if integer_count >= len(ratios) * 0.5:
            return "integer_ratio_simple_harmonics"

        if len(ratios) >= 2:
            sequential_ratios = [ratios[i] / ratios[i-1] for i in range(1, len(ratios)) if ratios[i-1] != 0]
            if any(abs(sr - self.PHI) < 0.15 for sr in sequential_ratios):
                return "fibonacci_sequence_pattern"

        return "complex_custom_harmonics"

    def _identify_emotional_pattern(self, emotional):
        """Identify patterns in emotional intensity"""
        if len(emotional) < 2:
            return "insufficient_data"

        if all(emotional[i] <= emotional[i+1] for i in range(len(emotional)-1)):
            return "crescendo_building_intensity"

        if all(emotional[i] >= emotional[i+1] for i in range(len(emotional)-1)):
            return "diminuendo_releasing_intensity"

        mid_point = len(emotional) // 2
        if emotional[mid_point] == max(emotional):
            return "arch_peak_emotional_focus"

        oscillations = 0
        for i in range(1, len(emotional) - 1):
            if (emotional[i] > emotional[i-1] and emotional[i] > emotional[i+1]) or \
               (emotional[i] < emotional[i-1] and emotional[i] < emotional[i+1]):
                oscillations += 1

        if oscillations >= len(emotional) // 3:
            return "oscillating_variable_intensity"

        return "complex_emotional_flow"

    def _match_cultural_pattern(self, contour, pattern_id):
        """Calculate confidence that contour matches cultural pattern"""
        if pattern_id == "indigenous_rising_fall":
            if len(contour) < 3:
                return 0.0

            rises = sum(1 for i in range(1, len(contour)) if contour[i] > contour[i-1])
            falls = sum(1 for i in range(1, len(contour)) if contour[i] < contour[i-1])

            balance = 1 - abs(rises - falls) / len(contour)

            mid_section = contour[len(contour)//3:2*len(contour)//3]
            has_peak = max(mid_section) == max(contour) if mid_section else False

            confidence = balance * 0.6 + (0.4 if has_peak else 0.0)
            return float(confidence)

        return 0.5

    def _encode_cultural_signature(self, pattern_id):
        """Encode cultural pattern as unique signature"""
        pattern_hash = int(hashlib.sha256(pattern_id.encode()).hexdigest(), 16)
        return f"cultural_sig_{pattern_hash % 10000}"

    def _detect_indigenous_markers(self, contour):
        """Detect characteristic markers of indigenous communication"""
        if len(contour) < 3:
            return []

        markers = []

        if len(contour) >= 2:
            ratios = [contour[i] / contour[i-1] for i in range(1, len(contour)) if contour[i-1] != 0]
            if any(abs(r - self.PHI) < 0.15 for r in ratios):
                markers.append("phi_ratio_present")

        if len(contour) >= 4:
            if abs(contour[0] - contour[-1]) < 0.1 * (max(contour) - min(contour)):
                markers.append("cyclical_return")

        smoothness = np.std([contour[i] - contour[i-1] for i in range(1, len(contour))])
        if smoothness < 20:
            markers.append("natural_breath_flow")

        return markers


if __name__ == "__main__":
    print("=" * 70)
    print("INFLECTION BRIDGE ENCODER")
    print("Capturing Tonal Intelligence and Frequency Mathematics")
    print("=" * 70)

    sample_inflection_data = {
        "pitch_contour": [220, 250, 280, 300, 290, 260, 240, 220],
        "time_points": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
        "frequency_deltas": [30, 30, 20, -10, -30, -20, -20],
        "modulation_rates": [300, 300, 200, 100, 300, 200, 200],
        "vibrato_depth": [3, 5, 8, 10, 8, 5, 3],
        "harmonic_ratios": [1.618, 2.0, 1.5, 1.618],
        "cultural_pattern": "indigenous_rising_fall",
        "emotional_signature": [0.3, 0.5, 0.7, 0.9, 0.8, 0.6, 0.4]
    }

    encoder = InflectionBridgeEncoder(
        freq_change_threshold=50,
        amplitude_threshold=25,
        curve_threshold=0.5
    )

    encoder.from_geometry(sample_inflection_data)
    binary_output = encoder.to_binary()

    print(f"\nBinary Output: {binary_output}")
    print(f"Total Bits: {len(binary_output)}")

    duration = sample_inflection_data["time_points"][-1]
    print(f"Speech Duration: {duration:.1f} seconds")
    print(f"Information Density: {len(binary_output) / duration:.2f} bits/second")

    print("\nINFLECTION PATTERN ANALYSIS")
    print("-" * 70)
    analysis = encoder.analyze_inflection_patterns()

    for section_name, section_data in analysis.items():
        print(f"\n{section_name}:")
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {section_data}")

    print("\n" + "=" * 70)
    print("Inflection Bridge Encoder Complete!")
    print("=" * 70)
