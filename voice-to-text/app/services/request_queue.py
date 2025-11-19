"""
Request Queue Service

Manages queuing of transcription requests until metadata discovery completes.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """Represents a queued transcription request."""
    file_path: str
    filename: str
    model: Optional[str]
    request_id: str
    job_id: str  # Link back to job record
    queued_at: datetime


class RequestQueueService:
    """Manages queue of pending transcription requests."""
    
    def __init__(self, max_size: int = 100):
        """
        Initialize request queue.
        
        Args:
            max_size: Maximum number of queued requests (default: 100)
        """
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self.processing: bool = False
        self.max_size = max_size
        logger.info(f"RequestQueueService initialized (max_size={max_size})")
    
    async def enqueue(
        self,
        file_path: str,
        filename: str,
        model: Optional[str],
        request_id: str,
        job_id: str
    ) -> bool:
        """
        Add a request to the queue.
        
        Args:
            file_path: Path to audio file
            filename: Original filename
            model: Model to use (optional)
            request_id: Unique request identifier
            job_id: Job record ID (links back to job record)
            
        Returns:
            bool: True if queued successfully, False if queue is full
        """
        try:
            queued_request = QueuedRequest(
                file_path=file_path,
                filename=filename,
                model=model,
                request_id=request_id,
                job_id=job_id,
                queued_at=datetime.now()
            )
            
            # Non-blocking put - raises QueueFull if queue is full
            self.queue.put_nowait(queued_request)
            logger.info(f"Queued transcription request: {request_id} (filename={filename}, queue_size={self.queue.qsize()})")
            return True
            
        except asyncio.QueueFull:
            logger.error(f"Queue is full (max_size={self.max_size}), cannot queue request {request_id}")
            return False
    
    async def dequeue(self) -> Optional[QueuedRequest]:
        """
        Get next request from queue (blocking).
        
        Returns:
            QueuedRequest or None if queue is empty and processing stopped
        """
        try:
            request = await self.queue.get()
            logger.debug(f"Dequeued request: {request.request_id}")
            return request
        except Exception as e:
            logger.error(f"Error dequeuing request: {e}")
            return None
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()
    
    def start_processing(self):
        """Mark queue as processing."""
        self.processing = True
        logger.info("Request queue processing started")
    
    def stop_processing(self):
        """Mark queue as stopped."""
        self.processing = False
        logger.info("Request queue processing stopped")


# Singleton instance
_request_queue: Optional[RequestQueueService] = None


def get_request_queue() -> RequestQueueService:
    """Get the global request queue instance."""
    global _request_queue
    
    if _request_queue is None:
        _request_queue = RequestQueueService()
    
    return _request_queue

