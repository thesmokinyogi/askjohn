"""
Test script to verify AudioProcessingService refactoring.

Tests each new method independently and the full pipeline.
"""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.audio_processing import get_audio_processing_service
from app.services.audio_metadata import get_audio_metadata_service

def test_extract_audio_from_video():
    """Test video extraction method."""
    print("\n=== Testing extract_audio_from_video() ===")
    
    # Check if we have a test video file
    # For now, just test that the method exists and has correct signature
    service = get_audio_processing_service()
    
    if not hasattr(service, 'extract_audio_from_video'):
        print("❌ Method extract_audio_from_video() not found")
        return False
    
    print("✅ Method exists")
    print(f"   Signature: {service.extract_audio_from_video.__doc__}")
    return True

def test_convert_format():
    """Test format conversion method."""
    print("\n=== Testing convert_format() ===")
    
    service = get_audio_processing_service()
    
    if not hasattr(service, 'convert_format'):
        print("❌ Method convert_format() not found")
        return False
    
    print("✅ Method exists")
    print(f"   Signature: {service.convert_format.__doc__}")
    
    # Test with a real file if available
    # For now, just verify method exists and is callable
    return True

def test_get_metadata_with_fallback():
    """Test metadata extraction helper."""
    print("\n=== Testing _get_metadata_with_fallback() ===")
    
    service = get_audio_processing_service()
    
    if not hasattr(service, '_get_metadata_with_fallback'):
        print("❌ Method _get_metadata_with_fallback() not found")
        return False
    
    print("✅ Method exists (private helper)")
    return True

def test_prepare_for_upload_structure():
    """Test that prepare_for_upload() uses the new methods."""
    print("\n=== Testing prepare_for_upload() structure ===")
    
    service = get_audio_processing_service()
    
    # Read the source code to verify it calls the new methods
    import inspect
    source = inspect.getsource(service.prepare_for_upload)
    
    checks = {
        'extract_audio_from_video': 'extract_audio_from_video' in source,
        'convert_format': 'convert_format' in source,
        '_get_metadata_with_fallback': '_get_metadata_with_fallback' in source,
    }
    
    all_passed = True
    for method, found in checks.items():
        if found:
            print(f"✅ prepare_for_upload() calls {method}()")
        else:
            print(f"❌ prepare_for_upload() does NOT call {method}()")
            all_passed = False
    
    return all_passed

def test_method_signatures():
    """Verify all methods have correct signatures."""
    print("\n=== Testing method signatures ===")
    
    service = get_audio_processing_service()
    
    import inspect
    
    # Check extract_audio_from_video
    sig = inspect.signature(service.extract_audio_from_video)
    params = list(sig.parameters.keys())
    if params == ['file_path']:
        print("✅ extract_audio_from_video(file_path) - correct signature")
    else:
        print(f"❌ extract_audio_from_video has wrong params: {params}")
        return False
    
    # Check convert_format
    sig = inspect.signature(service.convert_format)
    params = list(sig.parameters.keys())
    expected = ['file_path', 'target_format', 'bitrate']
    if params == expected:
        print("✅ convert_format(file_path, target_format, bitrate) - correct signature")
    else:
        print(f"❌ convert_format has wrong params: {params}, expected: {expected}")
        return False
    
    # Check _get_metadata_with_fallback
    sig = inspect.signature(service._get_metadata_with_fallback)
    params = list(sig.parameters.keys())
    if params == ['file_path']:
        print("✅ _get_metadata_with_fallback(file_path) - correct signature")
    else:
        print(f"❌ _get_metadata_with_fallback has wrong params: {params}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("AudioProcessingService Refactoring Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Method existence", test_extract_audio_from_video()))
    results.append(("Method existence", test_convert_format()))
    results.append(("Method existence", test_get_metadata_with_fallback()))
    results.append(("Structure check", test_prepare_for_upload_structure()))
    results.append(("Signature check", test_method_signatures()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ All structural checks passed!")
        print("   Next: Test with actual files to verify functionality")
    else:
        print("\n❌ Some checks failed - refactoring incomplete")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

