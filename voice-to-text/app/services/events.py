"""
Event Publishing Service - Notifies downstream services of transcription events.

This service provides an abstraction for publishing transcription lifecycle events
to downstream services (Content Cockpit, Contextual Librarian, etc.).

Current implementation: Local event publisher (logs events).
Future: Cloud Tasks, Pub/Sub, or direct HTTP callbacks.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

# Import models for type hints
from app.models.transcript import TranscriptOutput

logger = logging.getLogger(__name__)


class EventPublisher(ABC):
    """Abstract event publisher for transcription lifecycle events."""
    
    @abstractmethod
    def publish_job_completed(self, job_id: str, transcript_data: TranscriptOutput) -> bool:
        """
        Publish event when transcription job completes successfully.
        
        Args:
            job_id: Unique job identifier
            transcript_data: TranscriptOutput model instance (standardized transcript data)
            
        Returns:
            True if event published successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def publish_job_failed(self, job_id: str, error: str, error_details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Publish event when transcription job fails.
        
        Args:
            job_id: Unique job identifier
            error: Error message
            error_details: Additional error context
            
        Returns:
            True if event published successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def publish_job_started(self, job_id: str, job_metadata: Dict[str, Any]) -> bool:
        """
        Publish event when transcription job starts processing.
        
        Args:
            job_id: Unique job identifier
            job_metadata: Job metadata (filename, model, etc.)
            
        Returns:
            True if event published successfully, False otherwise
        """
        pass


class LocalEventPublisher(EventPublisher):
    """
    Local event publisher - logs events for now.
    
    This is a stub implementation that logs events. In the future, this can be
    extended to:
    - Publish to Cloud Tasks for async processing
    - Publish to Pub/Sub for event-driven architecture
    - Make HTTP callbacks to downstream services
    - Write to event log for processing
    """
    
    def __init__(self):
        """Initialize local event publisher."""
        logger.info("LocalEventPublisher initialized (stub implementation)")
    
    def publish_job_completed(self, job_id: str, transcript_data: TranscriptOutput) -> bool:
        """Log job completion event."""
        try:
            logger.info(
                f"EVENT: Job completed - job_id={job_id}, "
                f"transcript_id={transcript_data.transcript_id}, "
                f"filename={transcript_data.source_filename}, "
                f"word_count={transcript_data.metadata.total_words}"
            )
            
            # TODO: Future implementation
            # - Publish to Cloud Tasks
            # - Publish to Pub/Sub
            # - HTTP callback to Content Cockpit
            # - HTTP callback to Contextual Librarian
            
            return True
        except Exception as e:
            logger.error(f"Error publishing job_completed event: {e}")
            return False
    
    def publish_job_failed(self, job_id: str, error: str, error_details: Optional[Dict[str, Any]] = None) -> bool:
        """Log job failure event."""
        try:
            logger.warning(
                f"EVENT: Job failed - job_id={job_id}, error={error}, "
                f"details={error_details}"
            )
            
            # TODO: Future implementation
            # - Publish to Cloud Tasks for retry
            # - Notify monitoring system
            # - Alert downstream services
            
            return True
        except Exception as e:
            logger.error(f"Error publishing job_failed event: {e}")
            return False
    
    def publish_job_started(self, job_id: str, job_metadata: Dict[str, Any]) -> bool:
        """Log job started event."""
        try:
            logger.info(
                f"EVENT: Job started - job_id={job_id}, "
                f"filename={job_metadata.get('filename', 'N/A')}, "
                f"model={job_metadata.get('model', 'N/A')}"
            )
            
            # TODO: Future implementation
            # - Track job lifecycle
            # - Update job status in monitoring
            # - Notify downstream services of start
            
            return True
        except Exception as e:
            logger.error(f"Error publishing job_started event: {e}")
            return False


# Singleton instance
_event_publisher: Optional[EventPublisher] = None


def get_event_publisher() -> EventPublisher:
    """
    Get the global event publisher instance.
    
    Returns:
        EventPublisher instance (currently LocalEventPublisher)
    """
    global _event_publisher
    
    if _event_publisher is None:
        _event_publisher = LocalEventPublisher()
    
    return _event_publisher


def set_event_publisher(publisher: EventPublisher) -> None:
    """
    Set a custom event publisher (for testing or custom implementations).
    
    Args:
        publisher: EventPublisher instance to use
    """
    global _event_publisher
    _event_publisher = publisher

