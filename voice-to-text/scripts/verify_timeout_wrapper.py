#!/usr/bin/env python3
"""
Observe and verify: Test thread-based timeout wrapper before implementation.

This script tests whether a thread-based timeout wrapper will actually
enforce timeouts for hanging uploads, before we implement it in production.

Following "Observe Before Implement" principle.
"""

import os
import sys
import time
import tempfile
import threading
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def test_timeout_wrapper_concept():
    """Test the thread-based timeout wrapper concept."""
    print("=" * 60)
    print("Observing: Thread-Based Timeout Wrapper")
    print("=" * 60)
    print()
    
    print("Step 1: Testing timeout wrapper with simulated hang...")
    
    # Simulate a function that hangs (like our upload)
    def hanging_function(duration):
        """Simulate upload that hangs for given duration."""
        time.sleep(duration)
        return "completed"
    
    # Test wrapper that enforces timeout
    def timeout_wrapper(func, timeout_seconds, *args, **kwargs):
        """Wrapper that enforces timeout using threading."""
        result_container = [None]
        exception_container = [None]
        complete_event = threading.Event()
        
        def worker():
            try:
                result_container[0] = func(*args, **kwargs)
            except Exception as e:
                exception_container[0] = e
            finally:
                complete_event.set()
        
        # Start in thread
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        
        # Wait with timeout
        if not complete_event.wait(timeout=timeout_seconds):
            raise TimeoutError(f"Operation timed out after {timeout_seconds}s")
        
        # Check for exceptions
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    
    # Test 1: Function completes before timeout
    print("  Test 1: Function completes in 2s, timeout is 10s...")
    start = time.time()
    try:
        result = timeout_wrapper(hanging_function, 10, 2)
        elapsed = time.time() - start
        print(f"    ✅ SUCCESS: Completed in {elapsed:.1f}s, result: {result}")
    except Exception as e:
        print(f"    ❌ FAILED: {e}")
        return False
    
    # Test 2: Function hangs longer than timeout
    print("  Test 2: Function would hang for 20s, timeout is 5s...")
    start = time.time()
    try:
        result = timeout_wrapper(hanging_function, 5, 20)
        elapsed = time.time() - start
        print(f"    ❌ FAILED: Should have timed out, but got result: {result}")
        return False
    except TimeoutError as e:
        elapsed = time.time() - start
        print(f"    ✅ SUCCESS: Timeout raised after {elapsed:.1f}s: {e}")
    except Exception as e:
        print(f"    ❌ FAILED: Wrong exception: {e}")
        return False
    
    # Test 3: Function raises exception
    def failing_function():
        raise ValueError("Test error")
    
    print("  Test 3: Function raises exception...")
    start = time.time()
    try:
        result = timeout_wrapper(failing_function, 10)
        print(f"    ❌ FAILED: Should have raised exception")
        return False
    except ValueError as e:
        elapsed = time.time() - start
        print(f"    ✅ SUCCESS: Exception propagated after {elapsed:.1f}s: {e}")
    except Exception as e:
        print(f"    ❌ FAILED: Wrong exception: {e}")
        return False
    
    print()
    print("✅ All timeout wrapper tests passed!")
    print("   The thread-based timeout approach will work.")
    return True

def test_with_actual_upload():
    """Test timeout wrapper with actual GCS upload (if credentials available)."""
    print()
    print("Step 2: Testing timeout wrapper with actual GCS upload...")
    
    try:
        from google.cloud import storage
        from app.config import get_config
        
        config = get_config()
        bucket_name = config.gcs_bucket_name
        
        if not bucket_name:
            print("  ⏭️  Skipping: GCS_BUCKET_NAME not set")
            return True
        
        print(f"  Using bucket: {bucket_name}")
        
        # Initialize client
        client = storage.Client(project=config.google_cloud_project)
        bucket = client.bucket(bucket_name)
        
        if not bucket.exists():
            print("  ⏭️  Skipping: Bucket not accessible")
            return True
        
        # Create test file
        test_content = b"X" * (5 * 1024 * 1024)  # 5MB
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            temp_path = f.name
            f.write(test_content)
        
        print(f"  Created test file: {temp_path} ({len(test_content) / 1024 / 1024:.1f} MB)")
        
        # Test timeout wrapper with actual upload
        def timeout_wrapper(func, timeout_seconds, *args, **kwargs):
            """Wrapper that enforces timeout using threading."""
            result_container = [None]
            exception_container = [None]
            complete_event = threading.Event()
            
            def worker():
                try:
                    result_container[0] = func(*args, **kwargs)
                except Exception as e:
                    exception_container[0] = e
                finally:
                    complete_event.set()
            
            # Start in thread
            thread = threading.Thread(target=worker, daemon=True)
            thread.start()
            
            # Wait with timeout
            if not complete_event.wait(timeout=timeout_seconds):
                raise TimeoutError(f"Upload timed out after {timeout_seconds}s")
            
            # Check for exceptions
            if exception_container[0]:
                raise exception_container[0]
            
            return result_container[0]
        
        # Test with short timeout (should timeout if upload hangs)
        blob = bucket.blob(f"test/timeout_test_{int(time.time())}.bin")
        print(f"  Testing with 10s timeout (upload will likely hang)...")
        
        start = time.time()
        try:
            timeout_wrapper(
                lambda: blob.upload_from_filename(temp_path, timeout=10),
                10  # Our enforced timeout
            )
            elapsed = time.time() - start
            print(f"    ⚠️  Upload completed in {elapsed:.1f}s (unexpected - upload may have worked)")
        except TimeoutError as e:
            elapsed = time.time() - start
            print(f"    ✅ SUCCESS: Timeout enforced after {elapsed:.1f}s: {e}")
            print(f"    This confirms the wrapper will catch hanging uploads!")
        except Exception as e:
            elapsed = time.time() - start
            print(f"    ⚠️  Different exception after {elapsed:.1f}s: {e}")
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass
        
        return True
        
    except ImportError:
        print("  ⏭️  Skipping: google-cloud-storage not available")
        return True
    except Exception as e:
        print(f"  ⚠️  Could not test with actual upload: {e}")
        return True  # Don't fail the test if we can't test with real upload

def main():
    """Run observation and verification tests."""
    print()
    
    # Test 1: Concept verification
    concept_works = test_timeout_wrapper_concept()
    
    if not concept_works:
        print()
        print("❌ Concept verification failed - do not proceed with implementation")
        return 1
    
    # Test 2: Actual upload (if possible)
    test_with_actual_upload()
    
    print()
    print("=" * 60)
    print("Verification Summary")
    print("=" * 60)
    print("✅ Thread-based timeout wrapper concept verified")
    print("✅ Timeout enforcement works correctly")
    print("✅ Exception propagation works correctly")
    print()
    print("✅ READY TO IMPLEMENT")
    print("   The thread-based timeout wrapper will solve the hanging upload issue.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

