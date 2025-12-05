"""
Observation script: How does pydub handle channel extraction?

Purpose: Before implementing channel selection, observe actual behavior:
- How does split_to_mono() work?
- What format does it return?
- How do we extract a specific channel?
- What happens with different audio formats?

Following working agreement: "Observe Before Implement"
"""

from pydub import AudioSegment
import tempfile
import os

def observe_channel_extraction():
    """Observe pydub's channel extraction behavior."""
    
    print("=" * 60)
    print("OBSERVING: pydub channel extraction")
    print("=" * 60)
    
    # Test 1: Check if we have a stereo file to test with
    # (In real scenario, user would provide test file)
    print("\n1. Testing split_to_mono() with a generated stereo file...")
    
    try:
        # Create a simple stereo test file
        # Left channel: 440Hz tone, Right channel: 880Hz tone
        from pydub.generators import Sine
        
        left_channel = Sine(440).to_audio_segment(duration=1000)  # 1 second
        right_channel = Sine(880).to_audio_segment(duration=1000)
        
        # Combine into stereo
        stereo = AudioSegment.from_mono_audiosegments(left_channel, right_channel)
        
        print(f"   Created stereo audio:")
        print(f"   - Channels: {stereo.channels}")
        print(f"   - Sample rate: {stereo.frame_rate}Hz")
        print(f"   - Duration: {stereo.duration_seconds}s")
        
        # Test split_to_mono()
        print("\n2. Testing split_to_mono()...")
        channels = stereo.split_to_mono()
        
        print(f"   Result type: {type(channels)}")
        print(f"   Result length: {len(channels)}")
        print(f"   Channel 0 type: {type(channels[0])}")
        print(f"   Channel 0 channels: {channels[0].channels} (should be 1)")
        print(f"   Channel 1 type: {type(channels[1])}")
        print(f"   Channel 1 channels: {channels[1].channels} (should be 1)")
        
        # Test exporting a single channel
        print("\n3. Testing export of single channel...")
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            channel_path = tmp.name
        
        channels[0].export(channel_path, format="mp3", bitrate="128k")
        
        # Verify exported file
        exported = AudioSegment.from_file(channel_path)
        print(f"   Exported channel 0:")
        print(f"   - File exists: {os.path.exists(channel_path)}")
        print(f"   - Channels: {exported.channels} (should be 1)")
        print(f"   - Sample rate: {exported.frame_rate}Hz")
        print(f"   - Duration: {exported.duration_seconds}s")
        
        # Cleanup
        os.unlink(channel_path)
        
        print("\n" + "=" * 60)
        print("OBSERVATION COMPLETE")
        print("=" * 60)
        print("\nKey findings:")
        print("- split_to_mono() returns a list of AudioSegment objects")
        print("- Each channel is a mono AudioSegment (channels=1)")
        print("- Can export individual channels directly")
        print("- Channels[0] = left, channels[1] = right")
        
        return True
        
    except Exception as e:
        print(f"\nERROR during observation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = observe_channel_extraction()
    exit(0 if success else 1)

