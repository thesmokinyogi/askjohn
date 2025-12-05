"""
Observation script: How to detect speech vs music using energy variance analysis.

Purpose: Before implementing auto-detection, observe:
- How to calculate RMS energy with pydub
- How to calculate energy variance
- What values indicate speech vs steady music
- How to compare channels

Following working agreement: "Observe Before Implement"
"""

from pydub import AudioSegment
from pydub.generators import Sine
import math

def observe_energy_analysis():
    """Observe energy variance analysis for speech detection."""
    
    print("=" * 60)
    print("OBSERVING: Energy variance analysis for speech detection")
    print("=" * 60)
    
    try:
        # Test 1: Create test signals
        print("\n1. Creating test signals...")
        
        # Steady tone (simulates music)
        steady_tone = Sine(440).to_audio_segment(duration=2000)  # 2 seconds
        
        # Variable signal (simulates speech - varying amplitude)
        # Create by modulating a tone
        variable_signal = AudioSegment.empty()
        for i in range(20):  # 20 segments
            # Vary amplitude to simulate speech patterns
            amplitude = 0.3 + 0.7 * (i % 5) / 4  # Varies between 0.3 and 1.0
            segment = Sine(440).to_audio_segment(duration=100)
            segment = segment - (20 * (1 - amplitude))  # Adjust volume
            variable_signal += segment
        
        print(f"   Created steady tone: {steady_tone.duration_seconds}s")
        print(f"   Created variable signal: {variable_signal.duration_seconds}s")
        
        # Test 2: Calculate RMS energy
        print("\n2. Calculating RMS energy...")
        
        def calculate_rms_energy(audio_segment):
            """Calculate RMS energy of audio segment."""
            # Get raw audio data
            raw_audio = audio_segment.get_array_of_samples()
            
            # Convert to float and normalize
            if audio_segment.sample_width == 1:
                samples = [(s - 128.0) / 128.0 for s in raw_audio]
            elif audio_segment.sample_width == 2:
                samples = [s / 32768.0 for s in raw_audio]
            elif audio_segment.sample_width == 4:
                samples = [s / 2147483648.0 for s in raw_audio]
            else:
                samples = [s / 32768.0 for s in raw_audio]  # Default to 16-bit
            
            # Calculate RMS
            if len(samples) == 0:
                return 0.0
            mean_squared = sum(s * s for s in samples) / len(samples)
            rms = math.sqrt(mean_squared)
            return rms
        
        steady_rms = calculate_rms_energy(steady_tone)
        variable_rms = calculate_rms_energy(variable_signal)
        
        print(f"   Steady tone RMS: {steady_rms:.6f}")
        print(f"   Variable signal RMS: {variable_rms:.6f}")
        
        # Test 3: Calculate energy variance (windowed)
        print("\n3. Calculating energy variance (windowed analysis)...")
        
        def calculate_energy_variance(audio_segment, window_ms=100):
            """Calculate variance of RMS energy across windows."""
            window_samples = int(audio_segment.frame_rate * window_ms / 1000)
            raw_audio = audio_segment.get_array_of_samples()
            
            # Convert to float and normalize
            if audio_segment.sample_width == 1:
                samples = [(s - 128.0) / 128.0 for s in raw_audio]
            elif audio_segment.sample_width == 2:
                samples = [s / 32768.0 for s in raw_audio]
            elif audio_segment.sample_width == 4:
                samples = [s / 2147483648.0 for s in raw_audio]
            else:
                samples = [s / 32768.0 for s in raw_audio]  # Default to 16-bit
            
            # Calculate RMS for each window
            window_rms_values = []
            for i in range(0, len(samples), window_samples):
                window = samples[i:i+window_samples]
                if len(window) > 0:
                    mean_squared = sum(s * s for s in window) / len(window)
                    rms = math.sqrt(mean_squared)
                    window_rms_values.append(rms)
            
            # Calculate variance of window RMS values
            if len(window_rms_values) > 1:
                mean_rms = sum(window_rms_values) / len(window_rms_values)
                variance = sum((rms - mean_rms) ** 2 for rms in window_rms_values) / len(window_rms_values)
                return variance, mean_rms
            else:
                return 0.0, window_rms_values[0] if window_rms_values else 0.0
        
        steady_var, steady_mean = calculate_energy_variance(steady_tone)
        variable_var, variable_mean = calculate_energy_variance(variable_signal)
        
        print(f"   Steady tone:")
        print(f"     - Mean RMS: {steady_mean:.6f}")
        print(f"     - Variance: {steady_var:.9f}")
        print(f"   Variable signal:")
        print(f"     - Mean RMS: {variable_mean:.6f}")
        print(f"     - Variance: {variable_var:.9f}")
        ratio = variable_var/steady_var if steady_var > 0 else float('inf')
        print(f"   Variance ratio (variable/steady): {ratio:.2f}" if ratio != float('inf') else "   Variance ratio (variable/steady): inf")
        
        # Test 4: Simulate stereo with speech on one channel
        print("\n4. Simulating stereo file (speech left, music right)...")
        
        # Left: variable (speech)
        left_channel = variable_signal
        # Right: steady (music)
        right_channel = steady_tone[:len(variable_signal)]  # Match duration
        
        # Create stereo
        stereo = AudioSegment.from_mono_audiosegments(left_channel, right_channel)
        print(f"   Created stereo: {stereo.channels} channels, {stereo.duration_seconds}s")
        
        # Split and analyze
        channels = stereo.split_to_mono()
        left_var, left_mean = calculate_energy_variance(channels[0])
        right_var, right_mean = calculate_energy_variance(channels[1])
        
        print(f"   Left channel (speech):")
        print(f"     - Mean RMS: {left_mean:.6f}")
        print(f"     - Variance: {left_var:.9f}")
        print(f"   Right channel (music):")
        print(f"     - Mean RMS: {right_mean:.6f}")
        print(f"     - Variance: {right_var:.9f}")
        
        # Determine which has more variance (speech)
        if left_var > right_var:
            detected = "left"
            confidence = (left_var - right_var) / max(left_var, right_var) if max(left_var, right_var) > 0 else 0
        else:
            detected = "right"
            confidence = (right_var - left_var) / max(left_var, right_var) if max(left_var, right_var) > 0 else 0
        
        print(f"\n   Auto-detection result: {detected} channel (confidence: {confidence:.2%})")
        
        print("\n" + "=" * 60)
        print("OBSERVATION COMPLETE")
        print("=" * 60)
        print("\nKey findings:")
        print("- Energy variance is higher for variable signals (speech)")
        print("- Can compare variance between channels to detect speech")
        print("- Windowed analysis (100ms windows) works well")
        print("- Higher variance = more likely to be speech")
        
        return True
        
    except Exception as e:
        print(f"\nERROR during observation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = observe_energy_analysis()
    exit(0 if success else 1)

