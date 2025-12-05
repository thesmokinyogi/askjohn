"""
Test script: Verify AudioProcessingService handles mono files correctly.

Tests:
1. Mono file + channel=None (should use original)
2. Mono file + channel="left" (should skip extraction, use original)
3. Mono file + channel="auto" (should skip extraction, use original)
4. Mono file + channel="right" (should skip extraction, use original)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.audio_processing import AudioProcessingService
from pydub import AudioSegment
from pydub.generators import Sine
import tempfile

def test_mono_file_handling():
    """Test that mono files are handled correctly."""
    
    print("=" * 60)
    print("TESTING: Mono file handling in AudioProcessingService")
    print("=" * 60)
    
    service = AudioProcessingService()
    
    # Create a mono test file
    print("\n1. Creating mono test file...")
    mono_audio = Sine(440).to_audio_segment(duration=1000)  # 1 second, mono
    
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        mono_file = tmp.name
    
    mono_audio.export(mono_file, format="mp3", bitrate="128k")
    print(f"   Created mono file: {mono_file}")
    print(f"   Channels: {mono_audio.channels}")
    
    # Test 1: channel=None
    print("\n2. Test: channel=None (should use original)")
    try:
        result_path, metadata = service.prepare_for_upload(mono_file, "test.mp3", channel=None)
        print(f"   ✓ Result: {result_path}")
        print(f"   ✓ Metadata channels: {metadata.get('channels')}")
        assert metadata.get('channels') == 1, "Should be mono"
        assert result_path == mono_file, "Should return original file"
        print("   ✓ PASSED")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Test 2: channel="left"
    print("\n3. Test: channel='left' (should skip extraction)")
    try:
        result_path, metadata = service.extract_channel(mono_file, "left")
        print(f"   ✓ Result: {result_path}")
        print(f"   ✓ Metadata channels: {metadata.get('channels')}")
        assert metadata.get('channels') == 1, "Should be mono"
        assert result_path == mono_file, "Should return original file"
        print("   ✓ PASSED")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Test 3: channel="auto"
    print("\n4. Test: channel='auto' (should skip extraction)")
    try:
        result_path, metadata = service.extract_channel(mono_file, "auto")
        print(f"   ✓ Result: {result_path}")
        print(f"   ✓ Metadata channels: {metadata.get('channels')}")
        assert metadata.get('channels') == 1, "Should be mono"
        assert result_path == mono_file, "Should return original file"
        print("   ✓ PASSED")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Test 4: channel="right"
    print("\n5. Test: channel='right' (should skip extraction)")
    try:
        result_path, metadata = service.extract_channel(mono_file, "right")
        print(f"   ✓ Result: {result_path}")
        print(f"   ✓ Metadata channels: {metadata.get('channels')}")
        assert metadata.get('channels') == 1, "Should be mono"
        assert result_path == mono_file, "Should return original file"
        print("   ✓ PASSED")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Cleanup
    try:
        os.unlink(mono_file)
    except:
        pass
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)
    print("\nConclusion: AudioProcessingService correctly handles mono files")
    print("- Returns original file unchanged")
    print("- Preserves metadata")
    print("- Skips channel extraction (no error)")
    
    return True

if __name__ == "__main__":
    success = test_mono_file_handling()
    exit(0 if success else 1)

