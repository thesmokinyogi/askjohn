"""
Transcription Orchestrator Service

Orchestrates the complete transcription workflow:
- File validation and upload
- Cost estimation
- Job submission
- Status checking
- Completion handling (cost calculation, budget updates, library integration)

This service extracts business logic from API endpoints, making them thin and focused.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.services.storage import CloudStorageService  # storage.py, not storage/ package
from app.services.pricing import PricingService
from app.services.budget import BudgetService
from app.services.jobs import JobStorageService
from app.services.library import LibraryService
from app.services.processing_time import ProcessingTimeService
from app.services.audio_metadata import AudioMetadataService
from app.services.transcribe_v2 import GoogleSpeechV2Service, get_transcription_service_v2
from app.services.cost_calculation import CostCalculationService
from typing import Callable

logger = logging.getLogger(__name__)


class TranscriptionOrchestrator:
    """Orchestrates transcription workflow."""
    
    # Model mapping: UI model names -> Google API model names
    MODEL_MAPPING = {
        'chirp_batch': 'chirp',
        'chirp_standard': 'chirp',
        'long_batch': 'long',
        'long_standard': 'long',
        'short_batch': 'short',
        'short_standard': 'short',
        # Also support direct API names
        'chirp': 'chirp',
        'long': 'long',
        'short': 'short'
    }
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = ["mp3", "wav", "m4a", "ogg", "flac", "mp4", "mov"]
    
    def __init__(
        self,
        storage_service: CloudStorageService,
        transcription_service_factory: Callable[[str, str, str], GoogleSpeechV2Service],
        pricing_service: PricingService,
        budget_service: BudgetService,
        cost_calculation_service: CostCalculationService,
        job_storage: JobStorageService,
        library_service: LibraryService,
        processing_time_service: ProcessingTimeService,
        audio_metadata_service: AudioMetadataService,
        provider: str,
        default_model: str,
        project_id: str,
        speech_location: str,
        max_file_size_mb: int = 500,
        test_mode: bool = False,
        test_gcs_uri: Optional[str] = None,
        test_audio_metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize orchestrator with all required services.
        
        Args:
            transcription_service_factory: Function to create transcription service for a model
            cost_calculation_service: Service for calculating actual costs
            project_id: Google Cloud project ID
            speech_location: Speech API location
        """
        self.storage_service = storage_service
        self.transcription_service_factory = transcription_service_factory
        self.pricing_service = pricing_service
        self.budget_service = budget_service
        self.cost_calculation_service = cost_calculation_service
        self.job_storage = job_storage
        self.library_service = library_service
        self.processing_time_service = processing_time_service
        self.audio_metadata_service = audio_metadata_service
        self.provider = provider
        self.default_model = default_model
        self.project_id = project_id
        self.speech_location = speech_location
        self.max_file_size_mb = max_file_size_mb
        self.test_mode = test_mode
        self.test_gcs_uri = test_gcs_uri
        self.test_audio_metadata = test_audio_metadata
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[str, None]:
        """
        Validate uploaded file.
        
        Returns:
            Tuple of (file_extension, None) if valid
            Raises ValueError if invalid
        """
        # Extract extension
        file_extension = filename.split(".")[-1].lower() if "." in filename else ""
        
        # Validate extension
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Invalid file type. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )
        
        # Validate file size
        max_size_bytes = self.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise ValueError(
                f"File too large. Maximum size: {self.max_file_size_mb}MB"
            )
        
        return file_extension, None
    
    def map_model_name(self, ui_model: Optional[str]) -> Tuple[str, str, str]:
        """
        Map UI model name to Google API model name and extract tier.
        
        Args:
            ui_model: UI model name (e.g., 'chirp_batch') or None
            
        Returns:
            Tuple of (google_api_model, selected_model, tier)
            e.g., ('chirp', 'chirp_batch', 'batch')
        """
        selected_model = ui_model or self.default_model
        google_api_model = self.MODEL_MAPPING.get(selected_model, 'long')
        
        # Extract tier from model name
        if selected_model.endswith('_batch'):
            tier = 'batch'
        elif selected_model.endswith('_standard'):
            tier = 'standard'
        else:
            # Default to batch for backward compatibility
            tier = 'batch'
            logger.warning(f"Model name '{selected_model}' doesn't specify tier, defaulting to 'batch'")
        
        logger.info(f"Model selection: UI={selected_model}, API={google_api_model}, Tier={tier}")
        return google_api_model, selected_model, tier
    
    def submit_transcription(
        self,
        filename: str,
        audio_bytes: bytes,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a transcription job.
        
        This orchestrates the complete submission workflow:
        1. Validate file
        2. Upload to storage
        3. Extract metadata
        4. Estimate cost
        5. Submit job
        6. Create job record
        
        Args:
            filename: Original filename
            audio_bytes: File contents
            model: Optional model name (uses default if not provided)
            
        Returns:
            Dict with job_id, status, filename, model, duration_minutes,
            estimated_cost, submitted_at, check_status_url
            
        Raises:
            ValueError: If file validation fails
            Exception: If submission fails
        """
        # Step 1: Validate file
        self.validate_file(filename, len(audio_bytes))
        logger.info(f"Processing file: {filename} ({len(audio_bytes)} bytes)")
        
        # Step 2: Upload to storage and extract metadata
        gcs_uri = None
        try:
            if self.test_mode:
                logger.warning("⚠️  TEST MODE: Skipping upload, using cached file")
                gcs_uri = self.test_gcs_uri
                audio_metadata = self.test_audio_metadata or {}
            else:
                logger.info("Uploading to Cloud Storage...")
                gcs_uri, audio_metadata = self.storage_service.upload_audio(
                    audio_bytes, filename
                )
                logger.info(f"Uploaded to: {gcs_uri}")
            
            # Step 3: Map model name and extract tier
            google_api_model, selected_model, tier = self.map_model_name(model)
            
            # Step 4: Calculate estimated cost
            duration_minutes = audio_metadata.get('duration', 0) / 60.0
            free_tier_remaining = self.budget_service.get_free_tier_remaining(self.provider)
            
            cost_estimate = self.pricing_service.estimate_cost(
                provider=self.provider,
                model=selected_model,
                duration_minutes=duration_minutes,
                free_tier_remaining=free_tier_remaining
            )
            
            logger.info(
                f"Estimated cost: ${cost_estimate['total_cost']:.2f} "
                f"({cost_estimate['billable_minutes']:.1f} min @ ${cost_estimate['cost_per_minute']}/min)"
            )
            
            # Step 5: Submit transcription job
            # Create transcription service with the correct model
            model_transcription_service = self.transcription_service_factory(
                project_id=self.project_id,
                model=google_api_model,
                location=self.speech_location
            )
            logger.info(f"Submitting transcription job with model: {google_api_model}")
            operation = model_transcription_service.submit_job(
                gcs_uri=gcs_uri,
                audio_metadata=audio_metadata
            )
            
            job_id = operation.operation.name
            logger.info(f"Job submitted successfully: {job_id}")
            
            # Step 6: Create job record
            job_record = self.job_storage.create_job(
                job_id=job_id,
                filename=filename,
                model=selected_model,
                tier=tier,
                duration_minutes=duration_minutes,
                estimated_cost=cost_estimate['total_cost'],
                gcs_uri=gcs_uri
            )
            
            # Step 7: Return result
            return {
                "job_id": job_id,
                "status": "queued",
                "filename": filename,
                "model": selected_model,
                "duration_minutes": round(duration_minutes, 1),
                "estimated_cost": cost_estimate['total_cost'],
                "submitted_at": job_record["submitted_at"],
                "check_status_url": f"/api/jobs/{job_id}/status"
            }
            
        except Exception as e:
            logger.error(f"Error submitting transcription job: {e}")
            
            # Clean up uploaded file on error
            if gcs_uri and not self.test_mode:
                try:
                    self.storage_service.delete_file(gcs_uri)
                except:
                    pass  # Best effort cleanup
            
            raise
    
    def check_job_status(
        self,
        job_id: str,
        transcription_service: Optional[GoogleSpeechV2Service] = None
    ) -> Dict[str, Any]:
        """
        Check the status of a transcription job and handle completion.
        
        This orchestrates:
        1. Get job record
        2. Check Google operation status
        3. If complete: calculate costs, update budget, add to library
        4. If processing: track processing_started_at
        5. Return status
        
        Args:
            job_id: Job identifier
            transcription_service: Transcription service (required for checking status)
            
        Returns:
            Dict with job status and results
        """
        if transcription_service is None:
            raise ValueError("transcription_service is required for status checking")
        
        service = transcription_service
        
        # Step 1: Get job record
        job_record = self.job_storage.get_job(job_id, include_transcript=False)
        
        if not job_record:
            raise ValueError(f"Job not found: {job_id}")
        
        # Step 2: If already complete/failed, return cached result
        if job_record["status"] in ["complete", "failed"]:
            logger.info(f"Returning cached status for job {job_id}: {job_record['status']}")
            
            if job_record["status"] == "complete":
                job_with_transcript = self.job_storage.get_job(job_id, include_transcript=True)
                return {
                    "job_id": job_id,
                    "status": job_with_transcript["status"],
                    "in_library": job_with_transcript.get("in_library", False),
                    "library_id": job_with_transcript.get("library_id"),
                    "filename": job_with_transcript["filename"],
                    "model": job_with_transcript["model"],
                    "submitted_at": job_with_transcript["submitted_at"],
                    "completed_at": job_with_transcript.get("completed_at"),
                    "transcript": job_with_transcript.get("transcript"),
                    "confidence": job_with_transcript.get("confidence"),
                    "actual_cost": job_with_transcript.get("actual_cost")
                }
            else:
                return {
                    "job_id": job_id,
                    "status": job_record["status"],
                    "filename": job_record["filename"],
                    "model": job_record["model"],
                    "submitted_at": job_record["submitted_at"],
                    "completed_at": job_record.get("completed_at"),
                    "error": job_record.get("error")
                }
        
        # Step 3: Check Google operation status
        logger.info(f"Checking Google operation status for job {job_id}")
        status_result = service.check_job_status(
            job_id=job_id,
            gcs_uri=job_record.get("gcs_uri")
        )
        
        # Step 4: Track processing_started_at if transitioning to processing
        if status_result.get("status") == "processing" and not job_record.get("processing_started_at"):
            self.job_storage.update_job(job_id, {
                "processing_started_at": datetime.now().isoformat()
            })
            logger.info(f"Detected job {job_id} is processing, setting processing_started_at")
        
        # Step 5: Handle completion
        if status_result["done"]:
            if status_result["status"] == "complete":
                return self._handle_job_completion(job_id, job_record, status_result)
            else:
                return self._handle_job_failure(job_id, job_record, status_result)
        
        # Step 6: Job still processing
        return self._handle_job_processing(job_id, job_record, status_result)
    
    def _handle_job_completion(
        self,
        job_id: str,
        job_record: Dict[str, Any],
        status_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle job completion: calculate costs, update budget, add to library."""
        logger.info(f"Job {job_id} completed successfully")
        
        # Calculate actual cost from billed duration using cost calculation service
        metadata = status_result.get("metadata", {})
        billed_duration_minutes = metadata.get("billed_duration_minutes")
        
        cost_result = self.cost_calculation_service.calculate_actual_cost(
            provider=self.provider,
            model=job_record["model"],
            billed_duration_minutes=billed_duration_minutes,
            estimated_duration_minutes=job_record["duration_minutes"],
            estimated_cost=job_record["estimated_cost"]
        )
        
        actual_cost = cost_result["actual_cost"]
        actual_free_minutes_used = cost_result["actual_free_minutes_used"]
        billed_duration_minutes = cost_result["billed_duration_minutes"]  # Use the value from result (may be estimated)
        
        # Update job record with results
        metadata_with_words = status_result.get("metadata", {}).copy()
        if "words" in status_result:
            metadata_with_words["words"] = status_result["words"]
        
        self.job_storage.mark_complete(
            job_id=job_id,
            transcript=status_result["transcript"],
            confidence=status_result["confidence"],
            actual_cost=actual_cost,
            metadata=metadata_with_words
        )
        
        # Record processing time for feedback loop
        completed_at = datetime.now()
        if job_record.get("processing_started_at"):
            start_time = datetime.fromisoformat(job_record["processing_started_at"])
            processing_time_seconds = (completed_at - start_time).total_seconds()
            logger.info(f"Using processing_started_at for time calculation (excludes queueing)")
        else:
            submitted_at = datetime.fromisoformat(job_record["submitted_at"])
            processing_time_seconds = (completed_at - submitted_at).total_seconds()
            logger.warning(f"processing_started_at not available, using submitted_at (includes queueing)")
        
        self.processing_time_service.record_processing_time(
            model=job_record["model"],
            audio_duration_minutes=job_record["duration_minutes"],
            processing_time_seconds=processing_time_seconds,
            job_id=job_id
        )
        
        # Update budget
        self.budget_service.record_transcription(
            provider=self.provider,
            model=job_record["model"],
            duration_minutes=billed_duration_minutes,
            cost=actual_cost,
            free_minutes_used=actual_free_minutes_used
        )
        
        # Add to library
        updated_job = self.job_storage.get_job(job_id)
        transcript_file = updated_job.get("transcript_file")
        
        file_size_bytes = 0
        if transcript_file:
            transcript_path = self.job_storage.TRANSCRIPTS_DIR / transcript_file
            if transcript_path.exists():
                file_size_bytes = transcript_path.stat().st_size
        
        library_id = self.library_service.add_entry(
            filename=job_record["filename"],
            transcript_file=transcript_file,
            duration_minutes=job_record["duration_minutes"],
            model=job_record["model"],
            cost=actual_cost,
            file_size_bytes=file_size_bytes,
            metadata=status_result.get("metadata")
        )
        
        # Update job record to indicate it's in library
        if library_id:
            self.job_storage.update_job(job_id, {
                "in_library": True,
                "library_id": library_id
            })
            logger.info(f"Added job {job_id} to library as {library_id}")
        
        # Return complete result
        return {
            "job_id": job_id,
            "status": "complete",
            "in_library": True,
            "library_id": library_id,
            "filename": job_record["filename"],
            "model": job_record["model"],
            "submitted_at": job_record["submitted_at"],
            "completed_at": completed_at.isoformat(),
            "transcript": status_result["transcript"],
            "confidence": status_result["confidence"],
            "actual_cost": actual_cost,
            "metadata": status_result.get("metadata")
        }
    
    def _handle_job_failure(
        self,
        job_id: str,
        job_record: Dict[str, Any],
        status_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle job failure."""
        logger.error(f"Job {job_id} failed: {status_result.get('error')}")
        
        self.job_storage.mark_failed(
            job_id=job_id,
            error=status_result.get("error", "Unknown error")
        )
        
        return {
            "job_id": job_id,
            "status": "failed",
            "filename": job_record["filename"],
            "model": job_record["model"],
            "submitted_at": job_record["submitted_at"],
            "completed_at": datetime.now().isoformat(),
            "error": status_result.get("error")
        }
    
    def _handle_job_processing(
        self,
        job_id: str,
        job_record: Dict[str, Any],
        status_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle job still processing."""
        # Update status if transitioning from queued to processing
        updates = {}
        
        if job_record["status"] == "queued":
            updates["status"] = "processing"
            updates["processing_started_at"] = datetime.now().isoformat()
            logger.info(f"Job {job_id} transitioned from queued to processing")
        elif job_record["status"] == "processing" and not job_record.get("processing_started_at"):
            updates["processing_started_at"] = datetime.now().isoformat()
            logger.info(f"Job {job_id} was already processing, setting processing_started_at now (approximation)")
        
        if updates:
            self.job_storage.update_job(job_id, updates)
        
        return {
            "job_id": job_id,
            "status": "processing",
            "filename": job_record["filename"],
            "model": job_record["model"],
            "submitted_at": job_record["submitted_at"],
            "message": "Transcription in progress. Check again in a few seconds."
        }

