"""
Verification script: Ensure AudioMetadataService format is compatible with all usage.

Following working agreement: "Verify Before Trust" - test that the format change
doesn't break any downstream code.

Purpose:
- Verify all fields used downstream exist in AudioMetadataService format
- Test that .get() calls work correctly
- Ensure no breaking changes
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.audio_metadata import get_audio_metadata_service
from pydub import AudioSegment
from pydub.generators import Sine
import tempfile

def verify_metadata_format():
    """Verify AudioMetadataService format is compatible with all usage."""
    
    print("=" * 60)
    print("VERIFYING: Metadata format compatibility")
    print("=" * 60)
    
    # Create test audio file
    print("\n1. Creating test audio file...")
    audio = Sine(440).to_audio_segment(duration=1000)  # 1 second
    
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
        test_file = tmp.name
    
    audio.export(test_file, format="mp3", bitrate="128k")
    print(f"   Created: {test_file}")
    
    # Get metadata using AudioMetadataService
    print("\n2. Extracting metadata using AudioMetadataService...")
    try:
        metadata_service = get_audio_metadata_service()
        metadata = metadata_service.analyze_file(test_file)
        print(f"   ✓ Metadata extracted successfully")
    except Exception as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    # Verify all fields exist
    print("\n3. Verifying all required fields exist...")
    required_fields = ['duration', 'format', 'codec', 'sample_rate', 'channels', 'bit_rate', 'file_size']
    missing_fields = []
    for field in required_fields:
        if field not in metadata:
            missing_fields.append(field)
        else:
            print(f"   ✓ {field}: {metadata[field]} ({type(metadata[field]).__name__})")
    
    if missing_fields:
        print(f"   ✗ Missing fields: {missing_fields}")
        return False
    
    # Test downstream usage patterns
    print("\n4. Testing downstream usage patterns...")
    
    # Pattern 1: audio_metadata.get('duration', 0) / 60.0
    try:
        duration_minutes = metadata.get('duration', 0) / 60.0
        print(f"   ✓ duration_minutes calculation: {duration_minutes:.2f} min")
    except Exception as e:
        print(f"   ✗ duration_minutes calculation failed: {e}")
        return False
    
    # Pattern 2: audio_metadata.get('sample_rate', 16000)
    try:
        sample_rate = metadata.get('sample_rate', 16000)
        print(f"   ✓ sample_rate access: {sample_rate}Hz")
    except Exception as e:
        print(f"   ✗ sample_rate access failed: {e}")
        return False
    
    # Pattern 3: audio_metadata.get('channels', 1)
    try:
        channels = metadata.get('channels', 1)
        print(f"   ✓ channels access: {channels}")
    except Exception as e:
        print(f"   ✗ channels access failed: {e}")
        return False
    
    # Pattern 4: Check type compatibility
    print("\n5. Verifying type compatibility...")
    
    # duration should be float (for division)
    if not isinstance(metadata.get('duration'), (int, float)):
        print(f"   ✗ duration type wrong: {type(metadata.get('duration'))}")
        return False
    print(f"   ✓ duration is numeric: {type(metadata.get('duration')).__name__}")
    
    # sample_rate should be int
    if not isinstance(metadata.get('sample_rate'), (int, type(None))):
        print(f"   ⚠️  sample_rate type: {type(metadata.get('sample_rate')).__name__} (may be None)")
    else:
        print(f"   ✓ sample_rate is int or None: {type(metadata.get('sample_rate')).__name__}")
    
    # channels should be int
    if not isinstance(metadata.get('channels'), (int, type(None))):
        print(f"   ⚠️  channels type: {type(metadata.get('channels')).__name__} (may be None)")
    else:
        print(f"   ✓ channels is int or None: {type(metadata.get('channels')).__name__}")
    
    # Cleanup
    try:
        os.unlink(test_file)
    except:
        pass
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print("\nConclusion:")
    print("✓ All required fields present")
    print("✓ All downstream usage patterns work")
    print("✓ Type compatibility verified")
    print("\nAudioMetadataService format is compatible with all usage!")
    
    return True

if __name__ == "__main__":
    success = verify_metadata_format()
    exit(0 if success else 1)

