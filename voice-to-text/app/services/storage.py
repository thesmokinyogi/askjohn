"""
Cloud Storage service for managing audio file uploads and downloads.

This service handles:
- Uploading audio files to Google Cloud Storage
- Downloading transcription results
- Cleaning up temporary files
- Managing bucket operations

Required for V2 batch recognition.
"""

from google.cloud import storage
from typing import Optional, Dict, Tuple
import os
import tempfile
from datetime import datetime, timedelta
from io import BytesIO
import logging
from pydub import AudioSegment
from app.services.audio_processing import get_audio_processing_service
from app.services.audio_metadata import get_audio_metadata_service

logger = logging.getLogger(__name__)


class CloudStorageService:
    """
    Manages Google Cloud Storage operations for audio transcription.

    Audio files must be in GCS for V2 batch recognition to work.
    This service makes that transparent to the user.
    """

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize Cloud Storage client.

        Args:
            bucket_name: GCS bucket name (from .env)
            project_id: Google Cloud project ID (optional, from credentials)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id

        # Initialize client (uses GOOGLE_APPLICATION_CREDENTIALS)
        self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket_name)

        logger.info(f"Initialized Cloud Storage service: bucket={bucket_name}")

    def upload_audio(self, audio_bytes: bytes, filename: str) -> Tuple[str, Dict]:
        """
        Upload audio file to Cloud Storage and extract audio metadata.

        Args:
            audio_bytes: Audio file content
            filename: Original filename (for extension/metadata)

        Returns:
            Tuple of (GCS URI, audio metadata dict)
            Metadata includes: sample_rate, channels, duration, codec
        """
        # Extract audio metadata before upload using AudioMetadataService
        # Write to temp file for metadata service to read
        metadata = {}
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            # Use AudioMetadataService for consistent metadata extraction
            metadata_service = get_audio_metadata_service()
            metadata = metadata_service.analyze_file(temp_path)
            logger.info(f"Audio metadata: {metadata['sample_rate']}Hz, {metadata['channels']} channels, {metadata['duration']:.1f}s")
        except Exception as e:
            logger.warning(f"Could not extract audio metadata: {e}")
            # Provide defaults if extraction fails (matching AudioMetadataService format)
            metadata = {
                'duration': 0.0,
                'format': os.path.splitext(filename)[1].lstrip('.') or 'unknown',
                'codec': 'unknown',
                'sample_rate': 16000,  # Fallback to optimal speech rate
                'channels': 1,         # Fallback to mono
                'bit_rate': None,
                'file_size': len(audio_bytes)
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

        # Convert M4A to MP3 (M4A has issues with Google Speech batch_recognize)
        file_extension = os.path.splitext(filename)[1].lower()
        if file_extension == '.m4a':
            logger.warning("⚠️  M4A file detected - converting to MP3 for compatibility")
            try:
                # Load M4A audio
                with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as m4a_temp:
                    m4a_temp.write(audio_bytes)
                    m4a_path = m4a_temp.name

                # Convert to MP3
                audio = AudioSegment.from_file(m4a_path, format="m4a")
                mp3_buffer = BytesIO()
                audio.export(mp3_buffer, format="mp3", bitrate="128k")
                audio_bytes = mp3_buffer.getvalue()

                # Update filename to .mp3
                filename = filename.rsplit('.', 1)[0] + '.mp3'

                logger.info(f"✓ Converted M4A to MP3: {len(audio_bytes)} bytes")

                # Clean up temp M4A file
                try:
                    os.unlink(m4a_path)
                except:
                    pass

            except Exception as e:
                logger.error(f"Failed to convert M4A to MP3: {e}")
                logger.warning("Attempting upload as M4A anyway...")

        # Sanitize filename - replace spaces and special chars with underscores
        # Keep only alphanumeric, dots, hyphens, underscores
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Create unique path with timestamp to avoid collisions
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"uploads/{timestamp}_{safe_filename}"

        # Upload to GCS
        blob = self.bucket.blob(blob_name)

        # Set content type based on file extension
        content_type = self._get_content_type(filename)

        # Upload with extended timeout for large files
        # For 215MB @ 5 Mbps = ~6 min, but allow up to 30 minutes for slow connections
        file_size_mb = len(audio_bytes) / (1024 * 1024)
        logger.info(f"Uploading {file_size_mb:.1f} MB to GCS...")

        # Use longer timeout for large files (30 minutes = 1800 seconds)
        # Calculate timeout: 1 minute per 10MB, minimum 5 minutes, maximum 30 minutes
        timeout_seconds = max(300, min(1800, int(file_size_mb * 6)))
        logger.info(f"Using upload timeout: {timeout_seconds}s ({timeout_seconds/60:.1f} minutes)")

        blob.upload_from_string(audio_bytes, content_type=content_type, timeout=timeout_seconds)

        # Verify upload succeeded by checking blob metadata
        blob.reload()  # Refresh metadata from GCS
        logger.info(f"Verified upload - size: {blob.size} bytes, content-type: {blob.content_type}, exists: {blob.exists()}")

        # Get GCS URI
        gcs_uri = f"gs://{self.bucket_name}/{blob_name}"

        logger.info(f"Uploaded audio to GCS: {gcs_uri} ({len(audio_bytes)} bytes)")

        return gcs_uri, metadata

    def _upload_with_enforced_timeout(
        self,
        blob,
        file_path: str,
        content_type: str,
        timeout_seconds: int
    ) -> None:
        """
        Upload file with thread-based timeout enforcement.
        
        The library's timeout parameter doesn't work for resumable uploads
        (used automatically for large files), so we enforce our own timeout
        using threading to prevent indefinite hangs.
        
        Args:
            blob: GCS blob object to upload to
            file_path: Path to file on disk
            content_type: MIME content type
            timeout_seconds: Maximum time to wait for upload (enforced)
        
        Raises:
            TimeoutError: If upload exceeds timeout_seconds
            Exception: Any exception raised by the upload operation
        """
        import threading
        
        logger.info(f"Using thread-based timeout wrapper (timeout={timeout_seconds}s)")
        
        upload_complete = threading.Event()
        upload_exception = [None]
        
        def upload_worker():
            try:
                logger.info("Upload worker thread started - calling upload_from_filename()")
                # Still set library timeout (may help with initial connection)
                blob.upload_from_filename(
                    file_path,
                    content_type=content_type,
                    timeout=timeout_seconds
                )
                logger.info("Upload worker thread completed successfully")
            except Exception as e:
                logger.error(f"Upload worker thread caught exception: {type(e).__name__}: {e}")
                upload_exception[0] = e
            finally:
                upload_complete.set()
                logger.info("Upload worker thread finished (event set)")
        
        # Start upload in daemon thread (cleans up if main thread exits)
        upload_thread = threading.Thread(target=upload_worker, daemon=True)
        upload_thread.start()
        logger.info("Upload thread started, waiting for completion or timeout...")
        
        # Wait with our enforced timeout, using polling to allow Ctrl-C interruption
        # Poll every 1 second instead of one long wait, so Ctrl-C can interrupt
        elapsed = 0
        poll_interval = 1.0  # Check every second
        while elapsed < timeout_seconds:
            if upload_complete.wait(timeout=poll_interval):
                # Upload completed
                break
            elapsed += poll_interval
            # Check if thread is still alive (if it died, we'll catch exception below)
            if not upload_thread.is_alive() and not upload_complete.is_set():
                # Thread died unexpectedly
                logger.error("Upload thread died unexpectedly")
                break
        
        if not upload_complete.is_set():
            # Timeout occurred - raise exception
            logger.error(f"GCS upload timed out after {timeout_seconds}s - raising TimeoutError")
            raise TimeoutError(
                f"GCS upload timed out after {timeout_seconds}s "
                f"(file={file_path})"
            )
        
        logger.info("Upload completed or exception occurred, checking result...")
        
        # Check for exceptions from upload thread
        if upload_exception[0]:
            logger.info(f"Re-raising exception from upload thread: {upload_exception[0]}")
            raise upload_exception[0]
        
        logger.info("Upload completed successfully via thread wrapper")

    def upload_audio_from_file(
        self,
        file_path: str,
        filename: str,
        channel: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Upload audio file to Cloud Storage from file path (streaming upload).
        
        This method streams the file from disk to GCS without loading it into memory,
        making it suitable for large files (200MB+).
        
        Args:
            file_path: Path to file on disk
            filename: Original filename (for extension/metadata)
            channel: Optional channel selection for stereo files:
                    - "left" or "0": Extract left channel only
                    - "right" or "1": Extract right channel only
                    - None or "auto": Use all channels (default)
        
        Returns:
            Tuple of (GCS URI, audio metadata dict)
            Metadata includes: sample_rate, channels, duration, codec
        """
        # Use AudioProcessingService to handle all audio processing
        # This includes: video extraction, channel extraction, format conversion
        logger.info(f"Storage service received channel parameter: {channel} (type: {type(channel).__name__})")
        audio_processing = get_audio_processing_service()
        upload_file_path, metadata = audio_processing.prepare_for_upload(
            file_path,
            filename,
            channel=channel
        )
        
        logger.info(f"Audio processing complete: {metadata['sample_rate']}Hz, {metadata['channels']} channels, {metadata['duration']:.1f}s")
        
        # Determine the actual file being uploaded (may be extracted audio, not original video)
        upload_filename = os.path.basename(upload_file_path)
        logger.info(f"Uploading processed file: {upload_filename} (original: {filename})")

        # Sanitize filename - replace spaces and special chars with underscores
        # Keep only alphanumeric, dots, hyphens, underscores
        # Use the actual upload filename (extracted audio) not original video filename
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', upload_filename)

        # Create unique path with timestamp to avoid collisions
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        blob_name = f"uploads/{timestamp}_{safe_filename}"

        # Upload to GCS (streaming from disk)
        blob = self.bucket.blob(blob_name)

        # Set content type based on actual file being uploaded (extracted audio, not original video)
        content_type = self._get_content_type(upload_filename)

        # Get file size for logging and timeout calculation
        if not os.path.exists(upload_file_path):
            raise FileNotFoundError(f"File not found for upload: {upload_file_path}")
        
        if not os.path.isfile(upload_file_path):
            raise ValueError(f"Path is not a file: {upload_file_path}")
        
        try:
            file_size = os.path.getsize(upload_file_path)
        except OSError as e:
            raise OSError(f"Cannot access file size: {upload_file_path} - {e}")
        
        # Validate duration (Google's actual limit for batch API is 8 hours per file)
        # Reference: https://cloud.google.com/speech-to-text/docs/quotas
        # Batch requests: up to 8 hours per file, stored in Cloud Storage
        # No file size limit - only duration limit
        duration_seconds = metadata.get('duration', 0)
        duration_hours = duration_seconds / 3600
        max_duration_hours = 8.0  # Google's limit for batch API
        
        if duration_hours > max_duration_hours:
            raise ValueError(
                f"Audio duration too long: {duration_hours:.1f} hours. "
                f"Maximum duration: {max_duration_hours} hours per file. "
                f"Please split your audio file into smaller segments."
            )
        
        file_size_mb = file_size / (1024 * 1024)
        logger.info(
            f"Uploading {file_size_mb:.1f} MB ({duration_hours:.2f} hours) to GCS "
            f"(processed_file={os.path.basename(upload_file_path)}, original_filename={filename})..."
        )

        # Use longer timeout for large files (30 minutes = 1800 seconds)
        # Calculate timeout: More generous for slow connections
        # Formula: 1 minute per 5MB (12 seconds per MB), minimum 10 minutes, maximum 30 minutes
        # This accounts for slow upload speeds and network variability
        timeout_seconds = max(600, min(1800, int(file_size_mb * 12)))  # 12 sec/MB = 1 min per 5MB
        logger.info(f"Using upload timeout: {timeout_seconds}s ({timeout_seconds/60:.1f} minutes)")

        # Stream from disk to GCS (no memory loading!)
        # Use upload_from_filename() which is more reliable than upload_from_file()
        # For large files (>5MB), explicitly set chunk_size for resumable uploads
        try:
            import time
            
            upload_start = time.time()
            logger.info(f"Starting GCS upload from {upload_file_path}...")
            logger.info(f"Upload diagnostic: file_size={file_size} bytes ({file_size_mb:.1f} MB), timeout={timeout_seconds}s")
            
            # Use thread-based timeout wrapper to enforce timeout
            # The library's timeout parameter doesn't work for resumable uploads,
            # so we wrap it in a thread with our own timeout enforcement
            self._upload_with_enforced_timeout(
                blob,
                upload_file_path,
                content_type,
                timeout_seconds
            )
            
            upload_end = time.time()
            upload_duration = upload_end - upload_start
            upload_speed_mbps = (file_size * 8) / (upload_duration * 1_000_000)  # Convert to Mbps
            
            logger.info(f"GCS upload completed successfully in {upload_duration:.1f}s ({upload_duration/60:.1f} minutes)")
            logger.info(f"Upload speed: {upload_speed_mbps:.2f} Mbps (file_size={file_size_mb:.1f} MB)")
            
            if upload_speed_mbps < 5.0:
                logger.warning(f"⚠️  Upload speed is very slow ({upload_speed_mbps:.2f} Mbps). This may indicate:")
                logger.warning("   - Network connectivity issues")
                logger.warning("   - GCS bucket region is far from server")
        except Exception as e:
            logger.error(
                f"GCS upload failed: {type(e).__name__}: {e} "
                f"(file={upload_file_path}, size={file_size_mb:.1f}MB, "
                f"timeout={timeout_seconds}s, filename={filename})",
                exc_info=True
            )
            raise

        # Verify upload succeeded by checking blob metadata
        try:
            blob.reload()  # Refresh metadata from GCS
            logger.info(f"Verified upload - size: {blob.size} bytes, content-type: {blob.content_type}, exists: {blob.exists()}")
        except Exception as e:
            logger.warning(f"Could not verify upload metadata: {e}")
            # Continue anyway - upload might have succeeded even if reload fails

        # Get GCS URI
        gcs_uri = f"gs://{self.bucket_name}/{blob_name}"

        logger.info(f"Uploaded audio to GCS: {gcs_uri} ({file_size} bytes)")

        # Clean up temp files (converted audio files)
        if upload_file_path != file_path:
            try:
                os.unlink(upload_file_path)
                logger.debug(f"Cleaned up temp file: {upload_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {upload_file_path}: {e}")

        return gcs_uri, metadata

    def delete_file(self, gcs_uri: str) -> bool:
        """
        Delete file from Cloud Storage.

        Args:
            gcs_uri: Full GCS URI (gs://bucket-name/path/to/file)

        Returns:
            True if deleted successfully
        """
        try:
            # Extract blob name from URI
            blob_name = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
            blob = self.bucket.blob(blob_name)
            blob.delete()

            logger.info(f"Deleted file from GCS: {gcs_uri}")
            return True

        except Exception as e:
            logger.error(f"Error deleting file {gcs_uri}: {e}")
            return False

    def cleanup_old_files(self, days_old: int = 7) -> int:
        """
        Clean up audio files older than specified days.

        Args:
            days_old: Delete files older than this many days

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = 0

        try:
            # List all blobs in uploads folder
            blobs = self.bucket.list_blobs(prefix="uploads/")

            for blob in blobs:
                # Check if older than cutoff
                if blob.time_created < cutoff_date:
                    blob.delete()
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old files from GCS")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return deleted_count

    def cleanup_old_transcripts(self, days_old: int = 30) -> int:
        """
        Clean up transcript result files older than specified days.

        Google does NOT auto-delete incomplete/failed job result files.
        This method cleans up old transcript files from the transcripts/ folder.

        Args:
            days_old: Delete files older than this many days (default: 30)

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = 0

        try:
            # List all blobs in transcripts folder
            blobs = self.bucket.list_blobs(prefix="transcripts/")

            for blob in blobs:
                # Check if older than cutoff
                if blob.time_created < cutoff_date:
                    blob.delete()
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old transcript files from GCS")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during transcript cleanup: {e}")
            return deleted_count

    def list_transcript_files(self) -> list:
        """
        List all transcript files in GCS (for manual inspection/cleanup).

        Returns:
            List of blob names in transcripts/ folder
        """
        try:
            blobs = self.bucket.list_blobs(prefix="transcripts/")
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing transcript files: {e}")
            return []

    def _get_content_type(self, filename: str) -> str:
        """
        Determine content type from filename extension.

        Args:
            filename: File name with extension

        Returns:
            MIME type string
        """
        extension = filename.lower().split(".")[-1] if "." in filename else ""

        content_types = {
            "mp3": "audio/mpeg",
            "m4a": "audio/mp4",  # M4A is audio-only MP4
            "wav": "audio/wav",
            "flac": "audio/flac",
            "ogg": "audio/ogg",
            "mp4": "video/mp4",
            "mov": "video/quicktime",
        }

        return content_types.get(extension, "application/octet-stream")

    def verify_bucket_access(self) -> bool:
        """
        Verify we can access the bucket.
        Useful for startup validation.

        Returns:
            True if bucket is accessible
        """
        try:
            self.bucket.reload()
            logger.info(f"Verified access to bucket: {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Cannot access bucket {self.bucket_name}: {e}")
            return False

    def detect_speech_location(self) -> str:
        """
        Detect the optimal Speech V2 API location based on bucket location.

        This aligns the Speech API region with the bucket region for optimal
        latency and data locality. Uses a smart fallback chain for robustness.

        Mapping strategy:
        - If bucket region supports Speech V2 → use it directly
        - If not → map to nearest Speech V2-supported region
        - Ultimate fallback → multi-region endpoint

        Returns:
            Speech V2 location string (e.g., 'us-central1', 'us', 'eu')
        """
        try:
            # Get bucket location (cached by the client, minimal overhead)
            self.bucket.reload()
            bucket_location = self.bucket.location.lower()

            logger.info(f"Bucket location: {bucket_location}")

            # Try to get discovered Speech V2 locations from metadata cache
            # This is the single source of truth - query the API instead of hardcoding
            speech_v2_regions = None
            try:
                from app.services.transcribe_v2 import get_available_locations
                speech_v2_regions = get_available_locations()

                if speech_v2_regions:
                    logger.info(f"Using {len(speech_v2_regions)} discovered Speech V2 locations")

                    # Direct match - bucket region supports Speech V2
                    if bucket_location in speech_v2_regions:
                        logger.info(f"✓ Bucket region {bucket_location} supports Speech V2, using it directly")
                        return bucket_location
                else:
                    logger.warning("No locations discovered yet, using fallback mapping")

            except Exception as e:
                logger.warning(f"Could not query discovered locations: {e}. Using fallback mapping.")

            # If discovery unavailable, continue with mapping logic

            # Nearest region mapping for common cases
            # NOTE: This is a FALLBACK only. Actual mappings are validated against
            # discovered locations from Locations API. This table is only used when
            # discovery is unavailable or for initial mapping suggestions.
            REGION_MAPPING = {
                # US West regions → us-central1 (us-west1 not supported)
                'us-west1': 'us-central1',   # Oregon → Iowa
                'us-west2': 'us-central1',   # LA → Iowa
                'us-west3': 'us-central1',   # Salt Lake → Iowa
                'us-west4': 'us-central1',   # Las Vegas → Iowa
                # US East regions
                'us-east4': 'us-east1',      # Northern Virginia → South Carolina
                # US South regions
                'us-south1': 'us-central1',  # Dallas → Iowa

                # Europe regions → nearest Speech V2 region
                'europe-north1': 'europe-west1',      # Finland → Belgium
                'europe-central2': 'europe-west3',    # Warsaw → Frankfurt
                'europe-southwest1': 'europe-west2',  # Madrid → London

                # Asia regions → nearest Speech V2 region
                'asia-east1': 'asia-northeast1',      # Taiwan → Tokyo
                'asia-east2': 'asia-southeast1',      # Hong Kong → Singapore
                'asia-northeast2': 'asia-northeast1', # Osaka → Tokyo
                'asia-northeast3': 'asia-northeast1', # Seoul → Tokyo
            }

            # Check mapping table
            if bucket_location in REGION_MAPPING:
                mapped_location = REGION_MAPPING[bucket_location]

                # If we have discovered locations, validate the mapping
                if speech_v2_regions and mapped_location not in speech_v2_regions:
                    logger.warning(
                        f"Mapped location {mapped_location} not in discovered locations. "
                        f"Available: {sorted(speech_v2_regions)}"
                    )
                    # Try to find a better match from discovered locations
                    # Prefer locations with same prefix
                    prefix = mapped_location.split('-')[0]  # 'us', 'europe', 'asia'
                    fallback_options = [loc for loc in speech_v2_regions if loc.startswith(prefix)]
                    if fallback_options:
                        mapped_location = sorted(fallback_options)[0]
                        logger.info(f"Using discovered location: {mapped_location}")

                logger.info(f"✓ Mapped bucket region {bucket_location} → Speech V2 region {mapped_location}")
                return mapped_location

            # Multi-region fallback based on location prefix
            if bucket_location.startswith('us') or bucket_location == 'nam':
                logger.info(f"⚠️  Using 'us' multi-region fallback for bucket location: {bucket_location}")
                return 'us'
            elif bucket_location.startswith('europe') or bucket_location == 'eu':
                logger.info(f"⚠️  Using 'eu' multi-region fallback for bucket location: {bucket_location}")
                return 'eu'
            elif bucket_location.startswith('asia'):
                logger.info(f"⚠️  Using 'asia-southeast1' fallback for bucket location: {bucket_location}")
                return 'asia-southeast1'

            # Ultimate fallback - US multi-region
            logger.warning(f"⚠️  Unknown bucket location '{bucket_location}', defaulting to 'us' multi-region")
            return 'us'

        except Exception as e:
            logger.error(f"Error detecting Speech location: {e}")
            logger.warning("Defaulting to 'us' multi-region")
            return 'us'
