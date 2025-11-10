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
import logging
from pydub.utils import mediainfo

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
        # Extract audio metadata before upload
        # Write to temp file for pydub to read
        metadata = {}
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        try:
            info = mediainfo(temp_path)
            metadata = {
                'sample_rate': int(info.get('sample_rate', 0)),
                'channels': int(info.get('channels', 0)),
                'duration': float(info.get('duration', 0)),
                'codec': info.get('codec_name', 'unknown'),
                'bit_rate': info.get('bit_rate', 'unknown')
            }
            logger.info(f"Audio metadata: {metadata['sample_rate']}Hz, {metadata['channels']} channels, {metadata['duration']:.1f}s")
        except Exception as e:
            logger.warning(f"Could not extract audio metadata: {e}")
            # Provide defaults if extraction fails
            metadata = {
                'sample_rate': 16000,  # Fallback to optimal speech rate
                'channels': 1,         # Fallback to mono
                'duration': 0,
                'codec': 'unknown',
                'bit_rate': 'unknown'
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

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

        # Upload with extended timeout for large files (500MB max @ ~5 Mbps = ~13 min)
        # Set 15-minute timeout to handle slow connections
        file_size_mb = len(audio_bytes) / (1024 * 1024)
        logger.info(f"Uploading {file_size_mb:.1f} MB to GCS...")

        blob.upload_from_string(audio_bytes, content_type=content_type, timeout=900)

        # Verify upload succeeded by checking blob metadata
        blob.reload()  # Refresh metadata from GCS
        logger.info(f"Verified upload - size: {blob.size} bytes, content-type: {blob.content_type}, exists: {blob.exists()}")

        # Get GCS URI
        gcs_uri = f"gs://{self.bucket_name}/{blob_name}"

        logger.info(f"Uploaded audio to GCS: {gcs_uri} ({len(audio_bytes)} bytes)")

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
