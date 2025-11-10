#!/usr/bin/env python3
"""
Test script to verify GCS bucket access and file readability.
"""
from google.cloud import storage
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials and project from .env
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
bucket_name = os.getenv("GCS_BUCKET_NAME")
test_file = "uploads/20251110_060943_Voice_Memo_-_2014-06-28_16_33_27_-_Chelsea_And_The_Magician.m4a"

print(f"Project: {project_id}")
print(f"Bucket: {bucket_name}")
print(f"Testing file: {test_file}")
print("-" * 60)

# Initialize client
client = storage.Client(project=project_id)
bucket = client.bucket(bucket_name)

# Test 1: Check if bucket exists
print("\n1. Checking bucket access...")
try:
    bucket.reload()
    print(f"✓ Bucket exists: {bucket.name}")
    print(f"  Location: {bucket.location}")
    print(f"  Storage class: {bucket.storage_class}")
except Exception as e:
    print(f"✗ Cannot access bucket: {e}")
    exit(1)

# Test 2: Check if file exists
print("\n2. Checking if test file exists...")
blob = bucket.blob(test_file)
try:
    blob.reload()
    print(f"✓ File exists")
    print(f"  Size: {blob.size} bytes ({blob.size / 1024 / 1024:.2f} MB)")
    print(f"  Content-Type: {blob.content_type}")
    print(f"  Created: {blob.time_created}")
except Exception as e:
    print(f"✗ File not found or not accessible: {e}")
    exit(1)

# Test 3: Try to download a small portion (first 1KB)
print("\n3. Testing file readability...")
try:
    chunk = blob.download_as_bytes(start=0, end=1024)
    print(f"✓ Can read file data")
    print(f"  First bytes (hex): {chunk[:20].hex()}")
except Exception as e:
    print(f"✗ Cannot read file: {e}")
    exit(1)

# Test 4: Check bucket IAM policy
print("\n4. Checking bucket IAM policy...")
try:
    policy = bucket.get_iam_policy(requested_policy_version=3)
    print(f"✓ Retrieved IAM policy")
    print(f"  Total bindings: {len(policy.bindings)}")
    for binding in policy.bindings:
        print(f"  Role: {binding['role']}")
        print(f"    Members: {len(binding.get('members', []))} member(s)")
        for member in binding.get('members', [])[:3]:  # Show first 3
            print(f"      - {member}")
except Exception as e:
    print(f"⚠ Cannot retrieve IAM policy (might need admin permissions): {e}")

print("\n" + "=" * 60)
print("✓ All basic access tests passed!")
print("File is accessible and readable by your service account.")
