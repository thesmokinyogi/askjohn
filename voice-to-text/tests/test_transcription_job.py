#!/usr/bin/env python3
"""
Test script to submit a real transcription job using the new dynamic config.

This simulates the full flow:
1. Upload audio file to GCS
2. Extract metadata
3. Initialize transcription service (uses dynamic MODEL_REGION_CONFIG)
4. Submit job
5. Poll for completion
6. Display results
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.storage import CloudStorageService
from app.services.transcribe_v2 import (
    get_transcription_service_v2,
    initialize_metadata_cache
)

# Load environment variables
load_dotenv()

def test_transcription_job():
    """Test complete transcription job flow."""
    
    # Get configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    model = os.getenv("GOOGLE_MODEL", "long")
    
    if not project_id:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set")
        return False
    
    if not bucket_name:
        print("ERROR: GCS_BUCKET_NAME not set")
        return False
    
    # Test audio file
    test_file = Path(__file__).parent.parent / "test_files" / "Testing-Chelsea.m4a"
    
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return False
    
    print("=" * 80)
    print("TRANSCRIPTION JOB TEST")
    print("=" * 80)
    print(f"Project: {project_id}")
    print(f"Bucket: {bucket_name}")
    print(f"Model: {model}")
    print(f"Audio file: {test_file}")
    print()
    
    try:
        # Step 1: Initialize metadata cache (if not already done)
        print("1. Initializing metadata cache...")
        success = initialize_metadata_cache(project_id, languages=['en-US'])
        if not success:
            print("   ⚠️  Metadata cache initialization failed, continuing with fallback...")
        else:
            print("   ✓ Metadata cache initialized")
        print()
        
        # Step 2: Initialize storage service
        print("2. Initializing storage service...")
        storage_service = CloudStorageService(
            bucket_name=bucket_name,
            project_id=project_id
        )
        print("   ✓ Storage service initialized")
        
        # Detect optimal location
        location = storage_service.detect_speech_location()
        print(f"   ✓ Detected location: {location}")
        print()
        
        # Step 3: Read and upload audio file
        print("3. Reading and uploading audio file...")
        with open(test_file, 'rb') as f:
            audio_bytes = f.read()
        
        print(f"   File size: {len(audio_bytes)} bytes")
        gcs_uri, audio_metadata = storage_service.upload_audio(
            audio_bytes=audio_bytes,
            filename=test_file.name
        )
        print(f"   ✓ Uploaded to: {gcs_uri}")
        print(f"   Metadata: {audio_metadata.get('sample_rate')}Hz, "
              f"{audio_metadata.get('channels')} channels, "
              f"{audio_metadata.get('duration', 0):.1f}s")
        print()
        
        # Step 4: Initialize transcription service (uses dynamic config!)
        print("4. Initializing transcription service...")
        print(f"   Model: {model}, Location: {location}")
        transcription_service = get_transcription_service_v2(
            project_id=project_id,
            model=model,
            location=location
        )
        print(f"   ✓ Service initialized")
        print(f"   Selected location: {transcription_service.location}")
        print()
        
        # Step 5: Submit job
        print("5. Submitting transcription job...")
        operation = transcription_service.submit_job(
            gcs_uri=gcs_uri,
            language_code="en-US",
            audio_metadata=audio_metadata
        )
        
        job_id = operation.operation.name
        print(f"   ✓ Job submitted: {job_id}")
        print()
        
        # Step 6: Poll for completion
        print("6. Polling for job completion...")
        print("   (This may take a few minutes for longer audio files)")
        print()
        
        max_wait_time = 600  # 10 minutes max
        poll_interval = 5  # Check every 5 seconds
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                print(f"   ⚠️  Timeout after {max_wait_time}s")
                return False
            
            status = transcription_service.check_job_status(job_id, gcs_uri=gcs_uri)
            
            if status.get("done"):
                if status.get("status") == "complete":
                    print(f"   ✓ Job completed in {elapsed:.1f}s")
                    print()
                    
                    # Step 7: Display results
                    print("7. Transcription Results:")
                    print("=" * 80)
                    transcript = status.get("transcript", "")
                    confidence = status.get("confidence", 0)
                    
                    if transcript:
                        print(f"\nTranscript ({len(transcript)} characters):")
                        print("-" * 80)
                        print(transcript)
                        print("-" * 80)
                        print(f"\nConfidence: {confidence:.1%}")
                        
                        words = status.get("words", [])
                        if words:
                            print(f"Word count: {len(words)}")
                            print(f"First 10 words: {', '.join([w.get('word', '') for w in words[:10]])}")
                    else:
                        print("⚠️  No transcript returned")
                    
                    print()
                    print("=" * 80)
                    print("✅ TEST PASSED")
                    return True
                else:
                    error = status.get("error", "Unknown error")
                    print(f"   ✗ Job failed: {error}")
                    return False
            else:
                # Still processing
                status_msg = status.get("status", "processing")
                print(f"   [{elapsed:.0f}s] Status: {status_msg}...", end='\r')
                time.sleep(poll_interval)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_transcription_job()
    sys.exit(0 if success else 1)

