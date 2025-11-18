"""
Error handlers for API v1.

Provides standardized error response format and exception handling.
"""

import logging
import uuid
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.models.responses import ErrorResponse

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """Generate a unique request ID for tracking."""
    return f"req_{uuid.uuid4().hex[:8]}"


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException with standardized error response.
    
    Args:
        request: FastAPI request object
        exc: HTTPException that was raised
        
    Returns:
        JSONResponse with ErrorResponse format
    """
    request_id = generate_request_id()
    
    # Determine error code from status code
    error_codes = {
        400: "INVALID_REQUEST",
        401: "AUTHENTICATION_REQUIRED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    
    error_code = error_codes.get(exc.status_code, "UNKNOWN_ERROR")
    
    error_response = ErrorResponse(
        error={
            "code": error_code,
            "message": exc.detail or "An error occurred",
            "details": {},
            "request_id": request_id
        }
    )
    
    logger.error(
        f"HTTP {exc.status_code} error: {error_code} - {exc.detail} "
        f"(request_id: {request_id}, path: {request.url.path})"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors with standardized format.
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError from Pydantic
        
    Returns:
        JSONResponse with ErrorResponse format
    """
    request_id = generate_request_id()
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = ErrorResponse(
        error={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {
                "validation_errors": errors
            },
            "request_id": request_id
        }
    )
    
    logger.warning(
        f"Validation error: {errors} "
        f"(request_id: {request_id}, path: {request.url.path})"
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.dict()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with standardized format.
    
    Args:
        request: FastAPI request object
        exc: Unexpected exception
        
    Returns:
        JSONResponse with ErrorResponse format
    """
    request_id = generate_request_id()
    
    error_response = ErrorResponse(
        error={
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
            "request_id": request_id
        }
    )
    
    logger.exception(
        f"Unexpected error: {exc} "
        f"(request_id: {request_id}, path: {request.url.path})"
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers registered")

