"""
Library-related API endpoints.

Handles library entry listing, retrieval, and deletion.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response, JSONResponse

from app.models.responses import LibraryListResponse, LibraryEntryResponse, SuccessResponse
from app.services.library import LibraryService

logger = logging.getLogger(__name__)

# Create router for this module
router = APIRouter()


def get_library_service() -> LibraryService:
    """Dependency: Get library service."""
    from app.services.library import get_library_service as _get_library_service
    return _get_library_service()


@router.get("/library", response_model=LibraryListResponse)
async def list_library(
    library_service: LibraryService = Depends(get_library_service)
):
    """
    Get all library entries (sorted by date, newest first).
    
    Returns:
        LibraryListResponse with entries list and total count
    """
    try:
        entries = library_service.get_all_entries()
        
        return LibraryListResponse(
            entries=entries,
            total=len(entries)
        )
        
    except Exception as e:
        logger.error(f"Error listing library: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing library: {str(e)}"
        )


@router.get("/library/{library_id}", response_model=LibraryEntryResponse)
async def get_library_entry(
    library_id: str = Path(..., description="Library entry identifier"),
    library_service: LibraryService = Depends(get_library_service)
):
    """
    Get a specific library entry with full transcript.
    
    Args:
        library_id: Library entry ID
        
    Returns:
        LibraryEntryResponse with transcript loaded
    """
    try:
        entry = library_service.get_entry(library_id)
        
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )
        
        # Load transcript from file
        transcript_file = entry.get("transcript_file")
        if transcript_file:
            transcript_path = library_service.TRANSCRIPTS_DIR / transcript_file
            if transcript_path.exists():
                with open(transcript_path, 'r') as f:
                    transcript_data = json.load(f)
                entry["transcript"] = transcript_data.get("transcript")
                entry["words"] = transcript_data.get("words")
        
        return LibraryEntryResponse(**entry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting library entry {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting library entry: {str(e)}"
        )


@router.get("/library/{library_id}/download/text")
async def download_library_text(
    library_id: str = Path(..., description="Library entry identifier"),
    library_service: LibraryService = Depends(get_library_service)
):
    """
    Download library entry transcript as plain text.
    
    Args:
        library_id: Library entry ID
        
    Returns:
        Plain text file download
    """
    try:
        entry = library_service.get_entry(library_id)
        
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )
        
        # Load transcript from file
        transcript_file = entry.get("transcript_file")
        if not transcript_file:
            raise HTTPException(
                status_code=404,
                detail="No transcript available for this entry"
            )
        
        transcript_path = library_service.TRANSCRIPTS_DIR / transcript_file
        if not transcript_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Transcript file not found"
            )
        
        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)
        
        transcript_text = transcript_data.get("transcript", "")
        
        # Return as downloadable text file
        filename = entry.get("filename", "transcript")
        filename_base = filename.rsplit('.', 1)[0]
        
        return Response(
            content=transcript_text,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.txt"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading library text {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading text: {str(e)}"
        )


@router.get("/library/{library_id}/download/json")
async def download_library_json(
    library_id: str = Path(..., description="Library entry identifier"),
    library_service: LibraryService = Depends(get_library_service)
):
    """
    Download library entry transcript as JSON.
    
    Args:
        library_id: Library entry ID
        
    Returns:
        JSON file download with full transcript data
    """
    try:
        entry = library_service.get_entry(library_id)
        
        if not entry:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )
        
        # Load transcript from file
        transcript_file = entry.get("transcript_file")
        if not transcript_file:
            raise HTTPException(
                status_code=404,
                detail="No transcript available for this entry"
            )
        
        transcript_path = library_service.TRANSCRIPTS_DIR / transcript_file
        if not transcript_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Transcript file not found"
            )
        
        with open(transcript_path, 'r') as f:
            transcript_data = json.load(f)
        
        # Return as downloadable JSON file
        filename = entry.get("filename", "transcript")
        filename_base = filename.rsplit('.', 1)[0]
        
        return Response(
            content=json.dumps(transcript_data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.json"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading library JSON {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading JSON: {str(e)}"
        )


@router.delete("/library/{library_id}", response_model=SuccessResponse)
async def delete_library_entry(
    library_id: str = Path(..., description="Library entry identifier"),
    library_service: LibraryService = Depends(get_library_service)
):
    """
    Permanently delete a library entry and its transcript file.
    
    This is the ONLY place where transcripts are permanently deleted.
    
    Args:
        library_id: Library entry ID
        
    Returns:
        SuccessResponse confirming deletion
    """
    try:
        success = library_service.delete_entry(library_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Library entry not found: {library_id}"
            )
        
        return SuccessResponse(
            success=True,
            message="Library entry deleted permanently",
            library_id=library_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting library entry {library_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting library entry: {str(e)}"
        )

