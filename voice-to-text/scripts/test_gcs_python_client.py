#!/usr/bin/env python3
"""
Test GCS connectivity using Python client library with detailed diagnostics.

This script tests the Python client library behavior to understand
why uploads are hanging.

Usage:
    python scripts/test_gcs_python_client.py
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

def test_imports():
    """Test if required libraries are available."""
    print("Step 1: Checking Python client library...")
    try:
        from google.cloud import storage
        print(f"✅ google-cloud-storage imported successfully")
        
        # Check version
        try:
            import google.cloud.storage
            version = getattr(google.cloud.storage, '__version__', 'unknown')
            print(f"   Version: {version}")
        except:
            pass
        
        return storage
    except ImportError as e:
        print(f"❌ Failed to import google-cloud-storage: {e}")
        print("   Install: pip install google-cloud-storage")
        return None

def test_credentials():
    """Test if credentials are configured."""
    print("\nStep 2: Checking credentials...")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        if os.path.exists(creds_path):
            print(f"✅ Credentials file found: {creds_path}")
            return True
        else:
            print(f"❌ Credentials file not found: {creds_path}")
            return False
    else:
        print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
        print("   Will try default credentials")
        return True

def test_client_initialization():
    """Test if we can initialize the storage client."""
    print("\nStep 3: Testing client initialization...")
    try:
        from google.cloud import storage
        from app.config import get_config
        
        config = get_config()
        bucket_name = config.gcs_bucket_name
        project_id = config.google_cloud_project
        
        if not bucket_name:
            print("❌ GCS_BUCKET_NAME not set")
            return None, None
        
        print(f"   Bucket: {bucket_name}")
        print(f"   Project: {project_id or 'default'}")
        
        # Initialize client
        print("   Initializing storage client...")
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        
        print("✅ Client initialized successfully")
        return client, bucket
        
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_bucket_access(bucket):
    """Test if we can access the bucket."""
    print("\nStep 4: Testing bucket access...")
    if not bucket:
        print("❌ No bucket object available")
        return False
    
    try:
        # Try to check if bucket exists
        print("   Checking if bucket exists...")
        exists = bucket.exists()
        
        if exists:
            print("✅ Bucket exists and is accessible")
            
            # Try to list a few blobs
            print("   Listing blobs (first 5)...")
            blobs = list(bucket.list_blobs(max_results=5))
            print(f"   Found {len(blobs)} blob(s)")
            for blob in blobs[:3]:
                print(f"     - {blob.name} ({blob.size} bytes)")
            
            return True
        else:
            print("❌ Bucket does not exist or is not accessible")
            return False
            
    except Exception as e:
        print(f"❌ Bucket access failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_small_upload(bucket, timeout_seconds=30):
    """Test uploading a small file with timeout monitoring."""
    print(f"\nStep 5: Testing small file upload (timeout: {timeout_seconds}s)...")
    if not bucket:
        print("❌ No bucket object available")
        return False
    
    # Create a small test file
    test_content = b"This is a test file for GCS Python client connectivity check.\n" * 10
    test_filename = f"test_connectivity_{int(time.time())}.txt"
    
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            temp_path = temp_file.name
            temp_file.write(test_content)
        
        file_size = len(test_content)
        print(f"   Created test file: {temp_path} ({file_size} bytes)")
        
        # Create blob
        blob = bucket.blob(f"test/{test_filename}")
        print(f"   Target: gs://{bucket.name}/test/{test_filename}")
        
        # Upload with timeout monitoring
        print(f"   Starting upload...")
        start_time = time.time()
        
        # Use threading to monitor for hangs
        upload_complete = threading.Event()
        upload_exception = [None]
        
        def upload_worker():
            try:
                blob.upload_from_filename(
                    temp_path,
                    content_type='text/plain',
                    timeout=timeout_seconds
                )
                upload_exception[0] = None
            except Exception as e:
                upload_exception[0] = e
            finally:
                upload_complete.set()
        
        # Start upload in thread
        upload_thread = threading.Thread(target=upload_worker, daemon=True)
        upload_thread.start()
        
        # Monitor progress
        print("   Monitoring upload...")
        check_interval = 2  # Check every 2 seconds
        elapsed = 0
        
        while not upload_complete.is_set() and elapsed < timeout_seconds:
            time.sleep(check_interval)
            elapsed = time.time() - start_time
            if elapsed % 5 == 0 or elapsed < 5:  # Print every 5 seconds or in first 5
                print(f"     ... {elapsed:.1f}s elapsed")
        
        # Wait for completion or timeout
        upload_complete.wait(timeout=max(0, timeout_seconds - elapsed))
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check result
        if upload_exception[0]:
            print(f"❌ Upload failed after {duration:.1f}s")
            print(f"   Error: {upload_exception[0]}")
            import traceback
            traceback.print_exc()
            result = False
        elif upload_complete.is_set():
            print(f"✅ Upload completed in {duration:.1f}s")
            result = True
        else:
            print(f"❌ Upload timed out after {duration:.1f}s")
            print("   This indicates the same hanging issue!")
            result = False
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        # If upload succeeded, try to verify and clean up
        if result:
            try:
                # Verify file exists
                if blob.exists():
                    print("✅ Uploaded file verified in GCS")
                    
                    # Delete test file
                    blob.delete()
                    print("✅ Test file cleaned up")
                else:
                    print("⚠️  Upload reported success but file not found in GCS")
            except Exception as e:
                print(f"⚠️  Could not verify/cleanup: {e}")
        
        return result
        
    except Exception as e:
        print(f"❌ Upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_large_upload(bucket, timeout_seconds=120):
    """Test uploading a larger file (simulating the actual use case)."""
    print(f"\nStep 6: Testing larger file upload (timeout: {timeout_seconds}s)...")
    if not bucket:
        print("❌ No bucket object available")
        return False
    
    # Create a larger test file (~5MB to simulate real upload)
    chunk = b"X" * 1024 * 1024  # 1MB chunk
    test_content = chunk * 5  # 5MB total
    test_filename = f"test_large_{int(time.time())}.bin"
    
    try:
        # Create temp file
        print("   Creating test file (5MB)...")
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as temp_file:
            temp_path = temp_file.name
            temp_file.write(test_content)
        
        file_size = len(test_content)
        file_size_mb = file_size / (1024 * 1024)
        print(f"   Created test file: {temp_path} ({file_size_mb:.1f} MB)")
        
        # Create blob
        blob = bucket.blob(f"test/{test_filename}")
        print(f"   Target: gs://{bucket.name}/test/{test_filename}")
        
        # Upload with timeout monitoring
        print(f"   Starting upload...")
        start_time = time.time()
        
        # Use threading to monitor for hangs
        upload_complete = threading.Event()
        upload_exception = [None]
        
        def upload_worker():
            try:
                blob.upload_from_filename(
                    temp_path,
                    content_type='application/octet-stream',
                    timeout=timeout_seconds
                )
                upload_exception[0] = None
            except Exception as e:
                upload_exception[0] = e
            finally:
                upload_complete.set()
        
        # Start upload in thread
        upload_thread = threading.Thread(target=upload_worker, daemon=True)
        upload_thread.start()
        
        # Monitor progress
        print("   Monitoring upload...")
        check_interval = 5  # Check every 5 seconds
        elapsed = 0
        last_print = 0
        
        while not upload_complete.is_set() and elapsed < timeout_seconds:
            time.sleep(check_interval)
            elapsed = time.time() - start_time
            if elapsed - last_print >= 5:  # Print every 5 seconds
                print(f"     ... {elapsed:.1f}s elapsed")
                last_print = elapsed
        
        # Wait for completion or timeout
        remaining_timeout = max(0, timeout_seconds - elapsed)
        upload_complete.wait(timeout=remaining_timeout)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Check result
        if upload_exception[0]:
            print(f"❌ Upload failed after {duration:.1f}s")
            print(f"   Error: {upload_exception[0]}")
            import traceback
            traceback.print_exc()
            result = False
        elif upload_complete.is_set():
            upload_speed_mbps = (file_size * 8) / (duration * 1_000_000)
            print(f"✅ Upload completed in {duration:.1f}s")
            print(f"   Speed: {upload_speed_mbps:.2f} Mbps")
            result = True
        else:
            print(f"❌ Upload timed out after {duration:.1f}s")
            print("   ⚠️  THIS IS THE HANGING ISSUE!")
            print("   The upload started but never completed or errored")
            result = False
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        # If upload succeeded, try to verify and clean up
        if result:
            try:
                # Verify file exists
                if blob.exists():
                    print("✅ Uploaded file verified in GCS")
                    
                    # Delete test file
                    blob.delete()
                    print("✅ Test file cleaned up")
                else:
                    print("⚠️  Upload reported success but file not found in GCS")
            except Exception as e:
                print(f"⚠️  Could not verify/cleanup: {e}")
        
        return result
        
    except Exception as e:
        print(f"❌ Large upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run GCS Python client connectivity tests."""
    print("=" * 60)
    print("GCS Python Client Connectivity Test")
    print("=" * 60)
    print()
    
    # Step 1: Test imports
    storage = test_imports()
    if not storage:
        sys.exit(1)
    
    # Step 2: Test credentials
    if not test_credentials():
        print("\n⚠️  Credentials issue - tests may fail")
    
    # Step 3: Test client initialization
    client, bucket = test_client_initialization()
    if not bucket:
        print("\n❌ Cannot proceed without bucket access")
        sys.exit(1)
    
    # Step 4: Test bucket access
    bucket_accessible = test_bucket_access(bucket)
    if not bucket_accessible:
        print("\n❌ Cannot proceed - bucket not accessible")
        sys.exit(1)
    
    # Step 5: Test small upload
    small_upload_works = test_small_upload(bucket, timeout_seconds=30)
    
    # Step 6: Test large upload (this is where the issue likely occurs)
    large_upload_works = test_large_upload(bucket, timeout_seconds=120)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Client initialized: ✅")
    print(f"Bucket accessible: {'✅' if bucket_accessible else '❌'}")
    print(f"Small upload works: {'✅' if small_upload_works else '❌'}")
    print(f"Large upload works: {'✅' if large_upload_works else '❌'}")
    print()
    
    if not large_upload_works:
        print("❌ LARGE UPLOAD HANGS - This confirms the issue!")
        print("\nNext steps:")
        print("1. Research known issues with google-cloud-storage==2.10.0")
        print("2. Check if timeout parameter is being respected")
        print("3. Try alternative upload methods (upload_from_string, resumable uploads)")
        print("4. Check network/firewall/proxy settings")
    elif not small_upload_works:
        print("⚠️  Small uploads fail - may be a broader connectivity issue")
    else:
        print("✅ All uploads work - issue may be file-specific or intermittent")
    
    return 0 if (small_upload_works and large_upload_works) else 1

if __name__ == "__main__":
    sys.exit(main())

