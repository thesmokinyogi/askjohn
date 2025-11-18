#!/usr/bin/env python3
"""
Test TranscriptionOrchestrator structure and imports.

Note: This tests structure only, not full functionality (requires services).
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.orchestrator import TranscriptionOrchestrator


def test_orchestrator_import():
    """Test that orchestrator can be imported."""
    print("Testing TranscriptionOrchestrator import...")
    
    try:
        from app.services.orchestrator import TranscriptionOrchestrator
        print("  ✓ Orchestrator imported successfully")
        
        # Check class attributes
        assert hasattr(TranscriptionOrchestrator, 'MODEL_MAPPING')
        assert hasattr(TranscriptionOrchestrator, 'ALLOWED_EXTENSIONS')
        print("  ✓ Class attributes present")
        
        # Check methods
        assert hasattr(TranscriptionOrchestrator, 'validate_file')
        assert hasattr(TranscriptionOrchestrator, 'map_model_name')
        assert hasattr(TranscriptionOrchestrator, 'submit_transcription')
        assert hasattr(TranscriptionOrchestrator, 'check_job_status')
        print("  ✓ Required methods present")
        
        # Check MODEL_MAPPING
        mapping = TranscriptionOrchestrator.MODEL_MAPPING
        assert 'chirp_batch' in mapping
        assert 'long_standard' in mapping
        assert mapping['chirp_batch'] == 'chirp'
        print("  ✓ MODEL_MAPPING correct")
        
        # Check ALLOWED_EXTENSIONS
        extensions = TranscriptionOrchestrator.ALLOWED_EXTENSIONS
        assert 'mp3' in extensions
        assert 'wav' in extensions
        assert 'm4a' in extensions
        print("  ✓ ALLOWED_EXTENSIONS correct")
        
        print("  ✓ Import tests passed\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orchestrator_structure():
    """Test orchestrator class structure."""
    print("Testing TranscriptionOrchestrator structure...")
    
    # Check that it's a class
    assert isinstance(TranscriptionOrchestrator, type)
    print("  ✓ Is a class")
    
    # Check docstring
    assert TranscriptionOrchestrator.__doc__
    print("  ✓ Has docstring")
    
    print("  ✓ Structure tests passed\n")
    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing TranscriptionOrchestrator Structure")
    print("=" * 70)
    print()
    
    try:
        success = True
        success &= test_orchestrator_import()
        success &= test_orchestrator_structure()
        
        if success:
            print("=" * 70)
            print("✓ All orchestrator structure tests passed!")
            print("=" * 70)
            print("\nNote: Full functionality tests require:")
            print("  - Running server")
            print("  - Google Cloud credentials")
            print("  - Actual file uploads")
            return 0
        else:
            print("=" * 70)
            print("✗ Some tests failed")
            print("=" * 70)
            return 1
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

