#!/usr/bin/env python3
"""
Test GCS connectivity using gsutil command-line tool.

This script tests whether the issue is with the Python client library
or a broader connectivity/authentication problem.

Usage:
    python scripts/test_gcs_connectivity.py
"""

import os
import subprocess
import tempfile
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_gsutil_installed() -> bool:
    """Check if gsutil is installed and accessible."""
    try:
        result = subprocess.run(
            ["gsutil", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ gsutil is installed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ gsutil command failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ gsutil is not installed or not in PATH")
        print("   Install: https://cloud.google.com/sdk/docs/install")
        return False
    except subprocess.TimeoutExpired:
        print("❌ gsutil version check timed out")
        return False

def get_bucket_name() -> str:
    """Get GCS bucket name from environment."""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        print("❌ GCS_BUCKET_NAME environment variable is not set")
        sys.exit(1)
    print(f"📦 Bucket name: {bucket_name}")
    return bucket_name

def check_credentials() -> bool:
    """Check if Google Cloud credentials are configured."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        if os.path.exists(creds_path):
            print(f"✅ Credentials file found: {creds_path}")
            return True
        else:
            print(f"❌ Credentials file not found: {creds_path}")
            return False
    else:
        print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set (using default credentials)")
        return True  # Default credentials might work

def test_bucket_access(bucket_name: str) -> bool:
    """Test if we can access the bucket using gsutil."""
    print(f"\n🔍 Testing bucket access: gs://{bucket_name}")
    
    try:
        result = subprocess.run(
            ["gsutil", "ls", f"gs://{bucket_name}"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print(f"✅ Bucket access successful")
            if result.stdout.strip():
                print(f"   Bucket contents preview:")
                for line in result.stdout.strip().split('\n')[:5]:
                    print(f"   {line}")
            else:
                print("   (Bucket is empty)")
            return True
        else:
            print(f"❌ Bucket access failed")
            print(f"   Exit code: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ Bucket access check timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"❌ Error testing bucket access: {e}")
        return False

def test_file_upload(bucket_name: str) -> bool:
    """Test uploading a small file to GCS using gsutil."""
    print(f"\n📤 Testing file upload to gs://{bucket_name}")
    
    # Create a small test file
    test_content = b"This is a test file for GCS connectivity check.\n"
    test_filename = "gcs_connectivity_test.txt"
    
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            temp_path = temp_file.name
            temp_file.write(test_content)
        
        print(f"   Created test file: {temp_path} ({len(test_content)} bytes)")
        
        # Upload using gsutil
        gcs_path = f"gs://{bucket_name}/test/{test_filename}"
        print(f"   Uploading to: {gcs_path}")
        
        result = subprocess.run(
            ["gsutil", "cp", temp_path, gcs_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        if result.returncode == 0:
            print(f"✅ File upload successful!")
            print(f"   Uploaded: {gcs_path}")
            
            # Try to verify the file exists
            verify_result = subprocess.run(
                ["gsutil", "stat", gcs_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if verify_result.returncode == 0:
                print(f"✅ File verification successful")
                
                # Clean up test file
                cleanup_result = subprocess.run(
                    ["gsutil", "rm", gcs_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if cleanup_result.returncode == 0:
                    print(f"✅ Test file cleaned up")
                else:
                    print(f"⚠️  Could not clean up test file (you may want to delete it manually)")
            else:
                print(f"⚠️  File upload succeeded but verification failed")
            
            return True
        else:
            print(f"❌ File upload failed")
            print(f"   Exit code: {result.returncode}")
            print(f"   Error output: {result.stderr}")
            if result.stdout:
                print(f"   Output: {result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ File upload timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error during file upload test: {e}")
        return False

def main():
    """Run GCS connectivity tests."""
    print("=" * 60)
    print("GCS Connectivity Test")
    print("=" * 60)
    print()
    
    # Step 1: Check gsutil installation
    print("Step 1: Checking gsutil installation...")
    if not check_gsutil_installed():
        print("\n❌ Cannot proceed without gsutil")
        sys.exit(1)
    
    # Step 2: Check credentials
    print("\nStep 2: Checking credentials...")
    check_credentials()
    
    # Step 3: Get bucket name
    print("\nStep 3: Getting bucket configuration...")
    bucket_name = get_bucket_name()
    
    # Step 4: Test bucket access
    print("\nStep 4: Testing bucket access...")
    bucket_accessible = test_bucket_access(bucket_name)
    
    # Step 5: Test file upload
    if bucket_accessible:
        print("\nStep 5: Testing file upload...")
        upload_successful = test_file_upload(bucket_name)
    else:
        print("\n⏭️  Skipping file upload test (bucket not accessible)")
        upload_successful = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"gsutil installed: {'✅' if True else '❌'}")
    print(f"Bucket accessible: {'✅' if bucket_accessible else '❌'}")
    print(f"File upload works: {'✅' if upload_successful else '❌'}")
    print()
    
    if bucket_accessible and upload_successful:
        print("✅ GCS connectivity is working via gsutil")
        print("   → The issue is likely with the Python client library")
        print("   → Next step: Research google-cloud-storage==2.10.0 issues")
    elif bucket_accessible:
        print("⚠️  Bucket is accessible but file upload failed")
        print("   → May be a permissions issue or network problem")
    else:
        print("❌ GCS connectivity is not working")
        print("   → Check credentials, network, and bucket configuration")
        print("   → This may be the root cause of the upload hanging")
    
    return 0 if (bucket_accessible and upload_successful) else 1

if __name__ == "__main__":
    sys.exit(main())

