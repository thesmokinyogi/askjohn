"""
Storage adapters package.

Provides interfaces for storage operations, allowing future migration
from JSON files to database without changing business logic.
"""

from app.services.storage_adapters.adapter import (
    JobStorageAdapter,
    LibraryStorageAdapter,
    TranscriptStorageAdapter,
)

__all__ = [
    "JobStorageAdapter",
    "LibraryStorageAdapter",
    "TranscriptStorageAdapter",
]

