"""
Configuration management for Voice-to-Text service.

Centralizes all configuration with validation on startup.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Application configuration with validation."""
    
    # ============================================================================
    # Strategic Configuration (Provider Selection)
    # ============================================================================
    
    @property
    def stt_provider(self) -> str:
        """Transcription provider (google, whisper, etc.)."""
        provider = os.getenv("STT_PROVIDER", "google")
        if provider not in ["google", "whisper"]:
            raise ValueError(f"Invalid STT_PROVIDER: {provider}. Supported: google, whisper")
        return provider
    
    # ============================================================================
    # Budget Configuration
    # ============================================================================
    
    @property
    def monthly_budget(self) -> float:
        """Monthly budget limit in USD."""
        budget = float(os.getenv("MONTHLY_BUDGET", "250.0"))
        if budget <= 0:
            raise ValueError(f"MONTHLY_BUDGET must be > 0, got {budget}")
        return budget
    
    # ============================================================================
    # Google-Specific Configuration (Tactical)
    # ============================================================================
    
    @property
    def google_model(self) -> str:
        """Google Speech-to-Text model (long, chirp, short)."""
        return os.getenv("GOOGLE_MODEL", "long")
    
    @property
    def gcs_bucket_name(self) -> Optional[str]:
        """Google Cloud Storage bucket name."""
        return os.getenv("GCS_BUCKET_NAME")
    
    @property
    def google_cloud_project(self) -> Optional[str]:
        """Google Cloud project ID."""
        return os.getenv("GOOGLE_CLOUD_PROJECT")
    
    @property
    def google_application_credentials(self) -> Optional[str]:
        """Path to Google Cloud credentials file."""
        return os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    # ============================================================================
    # Test Mode Configuration
    # ============================================================================
    
    @property
    def test_mode_skip_upload(self) -> bool:
        """Whether to skip GCS upload in test mode."""
        return os.getenv("TEST_MODE_SKIP_UPLOAD", "false").lower() == "true"
    
    @property
    def test_gcs_uri(self) -> Optional[str]:
        """Test GCS URI (used when test mode is enabled)."""
        return os.getenv("TEST_GCS_URI")
    
    @property
    def test_audio_metadata(self) -> Dict[str, Any]:
        """Test audio metadata (used when test mode is enabled)."""
        # Default test metadata
        return {
            'sample_rate': 44100,
            'channels': 1,
            'duration': 336.8,
            'codec': 'aac',
            'bit_rate': 'unknown'
        }
    
    # ============================================================================
    # File Upload Configuration
    # ============================================================================
    
    @property
    def max_file_size_mb(self) -> int:
        """Maximum file size in MB."""
        if self.stt_provider == "google":
            return 500
        else:
            return 10
    
    @property
    def allowed_extensions(self) -> list[str]:
        """Allowed file extensions."""
        return ["mp3", "wav", "m4a", "ogg", "flac", "mp4", "mov"]
    
    # ============================================================================
    # Logging Configuration
    # ============================================================================
    
    @property
    def log_dir(self) -> Path:
        """Directory for log files."""
        return Path(__file__).parent.parent / "logs"
    
    @property
    def log_file(self) -> Path:
        """Path to log file."""
        return self.log_dir / "server.log"
    
    @property
    def log_max_bytes(self) -> int:
        """Maximum log file size in bytes."""
        return 10 * 1024 * 1024  # 10MB
    
    @property
    def log_backup_count(self) -> int:
        """Number of log file backups to keep."""
        return 5
    
    # ============================================================================
    # Validation
    # ============================================================================
    
    def validate(self) -> None:
        """
        Validate configuration on startup.
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        errors = []
        
        # Validate provider-specific requirements
        if self.stt_provider == "google":
            if not self.gcs_bucket_name:
                errors.append("GCS_BUCKET_NAME must be set when using Google provider")
            if not self.google_cloud_project:
                errors.append("GOOGLE_CLOUD_PROJECT must be set when using Google provider")
            if not self.google_application_credentials:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set - using default credentials")
        
        # Validate test mode
        if self.test_mode_skip_upload:
            if not self.test_gcs_uri:
                errors.append("TEST_GCS_URI must be set when TEST_MODE_SKIP_UPLOAD is true")
            logger.warning("⚠️  TEST MODE ENABLED - GCS uploads will be skipped")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for debugging."""
        return {
            "stt_provider": self.stt_provider,
            "monthly_budget": self.monthly_budget,
            "google_model": self.google_model,
            "gcs_bucket_name": self.gcs_bucket_name,
            "google_cloud_project": self.google_cloud_project,
            "test_mode_skip_upload": self.test_mode_skip_upload,
            "max_file_size_mb": self.max_file_size_mb,
            "allowed_extensions": self.allowed_extensions,
        }


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        # Load environment variables
        load_dotenv()
        
        # Create and validate config
        _config = Config()
        _config.validate()
        
        logger.info("Configuration loaded and validated")
    
    return _config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None

