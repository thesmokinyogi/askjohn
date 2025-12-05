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
import os
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
from app.services.events import get_event_publisher
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
        max_file_size_mb: Optional[int] = None,  # None means no limit
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
        # No file size validation - we stream files and let Google's API reject if needed
        # If max_file_size_mb is None, skip validation (let API handle it)
        if self.max_file_size_mb is not None:
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
            
            # Publish job started event for downstream services
            event_publisher = get_event_publisher()
            event_publisher.publish_job_started(job_id, {
                "filename": filename,
                "model": selected_model,
                "duration_minutes": duration_minutes,
                "gcs_uri": gcs_uri
            })
            
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
    
    def submit_transcription_from_file(
        self,
        file_path: str,
        filename: str,
        model: Optional[str] = None,
        existing_job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a transcription job from a file path (streaming upload).
        
        This is the streaming version that works with files on disk instead of
        loading them into memory. This allows handling large files efficiently.
        
        This orchestrates the complete submission workflow:
        1. Validate file (get size from disk)
        2. Upload to storage (streaming from disk)
        3. Extract metadata
        4. Estimate cost
        5. Submit job
        6. Create job record
        
        Args:
            file_path: Path to file on disk
            filename: Original filename
            model: Optional model name (uses default if not provided)
            existing_job_id: Optional existing job ID (for updating queued jobs)
            
        Returns:
            Dict with job_id, status, filename, model, duration_minutes,
            estimated_cost, submitted_at, check_status_url
            
        Raises:
            ValueError: If file validation fails
            Exception: If submission fails
        """
        # Step 1: Validate file (get size from disk)
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {file_path}")
        
        try:
            file_size = Path(file_path).stat().st_size
        except OSError as e:
            raise ValueError(f"Cannot access file: {file_path} - {e}")
        
        self.validate_file(filename, file_size)
        logger.info(f"Processing file from disk: {filename} ({file_size} bytes)")
        
        # Step 2: Upload to storage and extract metadata (streaming from disk)
        gcs_uri = None
        try:
            if self.test_mode:
                logger.warning("⚠️  TEST MODE: Skipping upload, using cached file")
                gcs_uri = self.test_gcs_uri
                audio_metadata = self.test_audio_metadata or {}
            else:
                logger.info("Uploading to Cloud Storage (streaming from disk)...")
                gcs_uri, audio_metadata = self.storage_service.upload_audio_from_file(
                    file_path, filename
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
            
            google_operation_id = operation.operation.name
            logger.info(f"Job submitted successfully: {google_operation_id}")
            
            # Publish job started event for downstream services
            event_publisher = get_event_publisher()
            event_publisher.publish_job_started(google_operation_id, {
                "filename": filename,
                "model": selected_model,
                "duration_minutes": duration_minutes,
                "gcs_uri": gcs_uri
            })
            
            # Step 6: Create or update job record
            if existing_job_id:
                # Update existing job record (from queue)
                logger.info(f"Updating existing job record: {existing_job_id}")
                self.job_storage.update_job(existing_job_id, {
                    "google_operation_id": google_operation_id,
                    "status": "processing",
                    "model": selected_model,
                    "tier": tier,
                    "duration_minutes": duration_minutes,
                    "estimated_cost": cost_estimate['total_cost'],
                    "gcs_uri": gcs_uri,
                    "processing_started_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })
                job_id = existing_job_id  # Use existing job_id for response
                job_record = self.job_storage.get_job(existing_job_id)
            else:
                # Create new job record (normal flow)
                job_id = google_operation_id  # Use Google operation ID as job_id
                job_record = self.job_storage.create_job(
                    job_id=job_id,
                    filename=filename,
                    model=selected_model,
                    tier=tier,
                    duration_minutes=duration_minutes,
                    estimated_cost=cost_estimate['total_cost'],
                    gcs_uri=gcs_uri
                )
                # Set google_operation_id (same as job_id for new jobs)
                self.job_storage.update_job(job_id, {
                    "google_operation_id": google_operation_id
                })
            
            # Step 7: Return result
            return {
                "job_id": job_id,
                "status": "processing",
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
        # job_id might be internal job_id or google_operation_id
        # Try to find by job_id first, then by google_operation_id
        job_record = self.job_storage.get_job(job_id, include_transcript=False)
        
        # If not found by job_id, try finding by google_operation_id
        if not job_record:
            # Search all jobs for matching google_operation_id
            all_jobs = self.job_storage.list_jobs()
            for job in all_jobs.values():
                if job.get("google_operation_id") == job_id:
                    job_record = job
                    job_id = job["job_id"]  # Use internal job_id
                    break
        
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
        # billed_duration comes from operation response, not GCS JSON metadata
        billed_duration_minutes = status_result.get("billed_duration_minutes")
        
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
        
        # CRITICAL: Check if job was already completed and recorded
        # This prevents duplicate cost recording and library entries
        # Check BEFORE updating job record to avoid race conditions
        # BUT: Allow re-adding to library if library_id is missing (e.g., if library addition failed)
        if job_record.get("actual_cost") is not None and job_record.get("library_id") is not None:
            logger.warning(f"Job {job_id} already has actual_cost recorded (${job_record.get('actual_cost'):.2f}) and is in library ({job_record.get('library_id')}). Skipping duplicate completion processing.")
            # Return the existing job data
            updated_job = self.job_storage.get_job(job_id, include_transcript=True)
            return {
                "job_id": job_id,
                "done": True,
                "status": "complete",
                "filename": updated_job["filename"],
                "model": updated_job["model"],
                "submitted_at": updated_job["submitted_at"],
                "completed_at": updated_job.get("completed_at"),
                "transcript": updated_job.get("transcript"),
                "confidence": updated_job.get("confidence"),
                "actual_cost": updated_job.get("actual_cost"),
                "metadata": updated_job.get("metadata", {})
            }
        
        # If job has actual_cost but no library_id, we'll re-add it to library
        if job_record.get("actual_cost") is not None and job_record.get("library_id") is None:
            logger.info(f"Job {job_id} has actual_cost but no library_id. Re-adding to library.")
        
        # Update job record with results
        # Note: "words" is transcript content, not metadata - it's stored separately in transcript file
        # Note: billed_duration is NOT added to metadata - it comes from operation response, not GCS JSON
        # It will be extracted separately and stored in job record (not transcript file metadata)
        
        # Get metadata model from status_result (should already be a TranscriptMetadata model)
        metadata = status_result.get("metadata")
        if not isinstance(metadata, TranscriptMetadata):
            # Fallback: convert dict to model if not already a model
            from app.models.transcript import dict_to_transcript_metadata
            metadata = dict_to_transcript_metadata(metadata if metadata else {})
        
        self.job_storage.mark_complete(
            job_id=job_id,
            transcript=status_result["transcript"],
            confidence=status_result["confidence"],
            actual_cost=actual_cost,
            metadata=metadata,
            # Pass billed_duration separately to preserve data provenance
            billed_duration_minutes=status_result.get("billed_duration_minutes"),
            billed_duration_seconds=status_result.get("billed_duration_seconds")
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
        
        # Update budget - only record once (we already checked actual_cost is None above)
        logger.info(f"Recording transcription cost for job {job_id}: ${actual_cost:.2f}")
        self.budget_service.record_transcription(
            provider=self.provider,
            model=job_record["model"],
            duration_minutes=billed_duration_minutes,
            cost=actual_cost,
            free_minutes_used=actual_free_minutes_used
        )
        
        # Add to library
        # Wrap in try/except to prevent library addition failure from blocking job completion
        library_id = None
        try:
            updated_job = self.job_storage.get_job(job_id)
            transcript_file = updated_job.get("transcript_file")
            
            if not transcript_file:
                logger.warning(f"Job {job_id} has no transcript_file, cannot add to library")
            else:
                file_size_bytes = 0
                transcript_path = self.job_storage.TRANSCRIPTS_DIR / transcript_file
                if transcript_path.exists():
                    file_size_bytes = transcript_path.stat().st_size
                else:
                    logger.warning(f"Transcript file not found: {transcript_path}, cannot add to library")
                
                # Get metadata model (should already be a TranscriptMetadata model from transcribe_v2)
                library_metadata = status_result.get("metadata")
                if not isinstance(library_metadata, TranscriptMetadata):
                    # Fallback: convert dict to model if not already a model
                    from app.models.transcript import dict_to_transcript_metadata
                    library_metadata = dict_to_transcript_metadata(library_metadata if library_metadata else {})
                
                library_id = self.library_service.add_entry(
                    filename=job_record["filename"],
                    transcript_file=transcript_file,
                    duration_minutes=job_record["duration_minutes"],
                    model=job_record["model"],
                    cost=actual_cost,
                    file_size_bytes=file_size_bytes,
                    metadata=library_metadata
                )
                
                if library_id:
                    self.job_storage.update_job(job_id, {
                        "in_library": True,
                        "library_id": library_id
                    })
                    logger.info(f"Added job {job_id} to library as {library_id}")
                else:
                    logger.error(f"Failed to add job {job_id} to library: library_service.add_entry() returned None")
                    # Set a flag so cleanup can retry
                    self.job_storage.update_job(job_id, {
                        "library_add_failed": True
                    })
        
        except Exception as e:
            logger.error(f"Exception while adding job {job_id} to library: {e}", exc_info=True)
            # Set a flag so cleanup can retry
            self.job_storage.update_job(job_id, {
                "library_add_failed": True,
                "library_add_error": str(e)
            })
        
        # Publish job completion event for downstream services (Content Cockpit, Contextual Librarian)
        # Use unified TranscriptOutput model for standardized cross-service format
        from app.models.transcript import (
            TranscriptOutput, TranscriptContent, TranscriptMetadata,
            WordTimestamp
        )
        from datetime import datetime
        
        # Get metadata model (should already be a TranscriptMetadata model from transcribe_v2)
        transcript_metadata = status_result.get("metadata")
        if not isinstance(transcript_metadata, TranscriptMetadata):
            # Fallback: convert dict to model if not already a model
            from app.models.transcript import dict_to_transcript_metadata
            transcript_metadata = dict_to_transcript_metadata(transcript_metadata if transcript_metadata else {})
        
        # Build word timestamps
        words = status_result.get("words", [])
        word_timestamps = [
            WordTimestamp(
                word=w.get("word", ""),
                start_time=w.get("start_time", 0.0),
                end_time=w.get("end_time", 0.0),
                confidence=w.get("confidence")
            )
            for w in words
        ]
        
        # Build TranscriptOutput for event publishing
        transcript_output = TranscriptOutput(
            transcript_id=library_id,  # Use library_id as transcript_id
            source_filename=job_record["filename"],
            source_uri=updated_job.get("gcs_uri"),
            content=TranscriptContent(
                transcript=status_result.get("transcript", ""),
                words=word_timestamps
            ),
            metadata=transcript_metadata,
            confidence=status_result.get("confidence"),
            duration_seconds=job_record["duration_minutes"] * 60,
            cost_usd=actual_cost,
            processing_time_seconds=processing_time_seconds,
            created_at=datetime.fromisoformat(job_record["submitted_at"]),
            completed_at=datetime.now() if updated_job.get("completed_at") else None
        )
        
        # Pass model directly to event publisher
        event_publisher = get_event_publisher()
        event_publisher.publish_job_completed(job_id, transcript_output)
        
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
        error_message = status_result.get("error", "Unknown error")
        logger.error(f"Job {job_id} failed: {error_message}")
        
        self.job_storage.mark_failed(
            job_id=job_id,
            error=error_message
        )
        
        # Publish job failure event for downstream services
        event_publisher = get_event_publisher()
        event_publisher.publish_job_failed(job_id, error_message, {
            "filename": job_record["filename"],
            "model": job_record["model"],
            "submitted_at": job_record["submitted_at"]
        })
        
        return {
            "job_id": job_id,
            "status": "failed",
            "filename": job_record["filename"],
            "model": job_record["model"],
            "submitted_at": job_record["submitted_at"],
            "completed_at": datetime.now().isoformat(),
            "error": error_message
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

