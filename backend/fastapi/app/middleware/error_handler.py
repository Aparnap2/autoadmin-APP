"""
Global exception handler for FastAPI application
Provides consistent error responses and logging
"""

import logging
import traceback
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class AutoAdminException(Exception):
    """Base exception for AutoAdmin application"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = None,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AutoAdminException):
    """Exception for validation errors"""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationException(AutoAdminException):
    """Exception for authentication errors"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )


class AuthorizationException(AutoAdminException):
    """Exception for authorization errors"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )


class ResourceNotFoundException(AutoAdminException):
    """Exception for resource not found errors"""

    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )


class ConflictException(AutoAdminException):
    """Exception for resource conflict errors"""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="RESOURCE_CONFLICT",
            details=details
        )


class RateLimitException(AutoAdminException):
    """Exception for rate limiting errors"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )


class ExternalServiceException(AutoAdminException):
    """Exception for external service errors"""

    def __init__(self, service: str, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=f"{service} error: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})}
        )


class DatabaseException(AutoAdminException):
    """Exception for database errors"""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=f"Database error: {message}",
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details
        )


async def autoadmin_exception_handler(request: Request, exc: AutoAdminException) -> JSONResponse:
    """Handle custom AutoAdmin exceptions"""
    logger.error(
        f"AutoAdmin exception: {exc.error_code}",
        error_code=exc.error_code,
        status_code=exc.status_code,
        message=exc.message,
        details=exc.details,
        path=str(request.url),
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "timestamp": logger.logger.bind().info()
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation exceptions"""
    logger.warning(
        "Validation error",
        errors=exc.errors(),
        path=str(request.url),
        method=request.method
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {
                    "field_errors": exc.errors()
                }
            }
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(
        f"HTTP {exc.status_code} error",
        detail=exc.detail,
        path=str(request.url),
        method=request.method
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
            }
        }
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation exceptions"""
    logger.warning(
        "Pydantic validation error",
        errors=exc.errors(),
        path=str(request.url),
        method=request.method
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "PYDANTIC_VALIDATION_ERROR",
                "message": "Data validation failed",
                "details": {
                    "field_errors": exc.errors()
                }
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions"""
    logger.exception(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=str(request.url),
        method=request.method,
        traceback=traceback.format_exc()
    )

    # Don't expose internal errors in production
    if logger.settings.ENVIRONMENT == "production":
        message = "An internal error occurred"
        details = {}
    else:
        message = str(exc)
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": message,
                "details": details
            }
        }
    )


def add_exception_handlers(app: FastAPI):
    """Add all exception handlers to FastAPI application"""

    # Custom exception handlers
    app.add_exception_handler(AutoAdminException, autoadmin_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

    # Fallback handler for uncaught exceptions
    app.add_exception_handler(Exception, general_exception_handler)