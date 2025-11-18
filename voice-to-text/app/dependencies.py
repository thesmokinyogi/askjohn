"""
Dependency injection functions for FastAPI routes.

Provides dependency functions for all services used by API endpoints.
"""

import logging
from functools import lru_cache

from app.config import get_config
from app.services.storage import CloudStorageService
from app.services.pricing import get_pricing_service
from app.services.budget import get_budget_service
from app.services.cost_calculation import get_cost_calculation_service
from app.services.jobs import get_job_storage
from app.services.library import LibraryService
from app.services.processing_time import get_processing_time_service
from app.services.audio_metadata import get_audio_metadata_service
from app.services.transcribe_v2 import get_transcription_service_v2
from app.services.orchestrator import TranscriptionOrchestrator

logger = logging.getLogger(__name__)

# Cache services (singleton pattern)
_config = None
_storage_service = None
_transcription_service = None
_orchestrator = None


def get_app_config():
    """Get application configuration."""
    global _config
    if _config is None:
        _config = get_config()
    return _config


def get_storage_service() -> CloudStorageService:
    """Get storage service (singleton)."""
    global _storage_service
    if _storage_service is None:
        config = get_app_config()
        if config.stt_provider != "google":
            raise ValueError("Storage service only available for Google provider")
        
        _storage_service = CloudStorageService(
            bucket_name=config.gcs_bucket_name,
            project_id=config.google_cloud_project
        )
    return _storage_service


def get_transcription_service_factory():
    """Get transcription service factory function."""
    config = get_app_config()
    
    def factory(project_id: str, model: str, location: str):
        """Factory function to create transcription service."""
        return get_transcription_service_v2(
            project_id=project_id,
            model=model,
            location=location
        )
    
    return factory


def get_orchestrator() -> TranscriptionOrchestrator:
    """Get transcription orchestrator (singleton)."""
    global _orchestrator
    if _orchestrator is None:
        config = get_app_config()
        
        # Get all required services
        storage_service = get_storage_service()
        pricing_service = get_pricing_service()
        budget_service = get_budget_service(monthly_budget=config.monthly_budget)
        cost_calculation_service = get_cost_calculation_service()
        job_storage = get_job_storage()
        library_service = LibraryService()
        processing_time_service = get_processing_time_service()
        audio_metadata_service = get_audio_metadata_service()
        
        # Get transcription service factory
        transcription_service_factory = get_transcription_service_factory()
        
        # Get speech location (from storage service)
        speech_location = storage_service.detect_speech_location()
        
        # Create orchestrator
        _orchestrator = TranscriptionOrchestrator(
            storage_service=storage_service,
            transcription_service_factory=transcription_service_factory,
            pricing_service=pricing_service,
            budget_service=budget_service,
            cost_calculation_service=cost_calculation_service,
            job_storage=job_storage,
            library_service=library_service,
            processing_time_service=processing_time_service,
            audio_metadata_service=audio_metadata_service,
            provider=config.stt_provider,
            default_model=config.google_model,
            project_id=config.google_cloud_project,
            speech_location=speech_location,
            max_file_size_mb=config.max_file_size_mb,
            test_mode=config.test_mode_skip_upload,
            test_gcs_uri=config.test_gcs_uri,
            test_audio_metadata=config.test_audio_metadata
        )
        
        logger.info("TranscriptionOrchestrator initialized")
    
    return _orchestrator

