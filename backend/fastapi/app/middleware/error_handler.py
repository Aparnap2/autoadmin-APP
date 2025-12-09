"""
Global exception handler for FastAPI application
Provides consistent error responses and logging with correlation IDs
"""

import logging
import traceback
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ErrorCodes:
    """Standardized error codes for AutoAdmin API"""

    # Validation Errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST_FORMAT = "INVALID_REQUEST_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"
    INVALID_QUERY_PARAMETER = "INVALID_QUERY_PARAMETER"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"

    # Authentication Errors (401)
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"

    # Authorization Errors (403)
    ACCESS_DENIED = "ACCESS_DENIED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    RESOURCE_ACCESS_DENIED = "RESOURCE_ACCESS_DENIED"

    # Not Found Errors (404)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Conflict Errors (409)
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"

    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

    # Server Errors (500)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    AGENT_EXECUTION_ERROR = "AGENT_EXECUTION_ERROR"
    TASK_PROCESSING_ERROR = "TASK_PROCESSING_ERROR"

    # Bad Gateway (502)
    BAD_GATEWAY = "BAD_GATEWAY"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"

    # Service Unavailable (503)
    SERVICE_TEMPORARILY_UNAVAILABLE = "SERVICE_TEMPORARILY_UNAVAILABLE"
    MAINTENANCE_MODE = "MAINTENANCE_MODE"


class AutoAdminException(Exception):
    """Base exception for AutoAdmin application with structured error data"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = ErrorCodes.INTERNAL_SERVER_ERROR,
        details: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        should_log: bool = True
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        self.headers = headers or {}
        self.should_log = should_log
        super().__init__(self.message)


class ValidationException(AutoAdminException):
    """Exception for validation errors"""

    def __init__(self, message: str, field_errors: list = None, details: Dict[str, Any] = None):
        error_details = details or {}
        if field_errors:
            error_details["field_errors"] = field_errors
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=ErrorCodes.VALIDATION_ERROR,
            details=error_details
        )


class AuthenticationException(AutoAdminException):
    """Exception for authentication errors"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCodes.AUTHENTICATION_REQUIRED,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(AutoAdminException):
    """Exception for authorization errors"""

    def __init__(self, message: str = "Access denied", resource: str = None):
        details = {}
        if resource:
            details["resource"] = resource
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCodes.ACCESS_DENIED,
            details=details
        )


class ResourceNotFoundException(AutoAdminException):
    """Exception for resource not found errors"""

    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f" with identifier: {identifier}"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCodes.RESOURCE_NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )


class ConflictException(AutoAdminException):
    """Exception for resource conflict errors"""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCodes.RESOURCE_CONFLICT,
            details=details
        )


class RateLimitException(AutoAdminException):
    """Exception for rate limiting errors"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCodes.RATE_LIMIT_EXCEEDED,
            headers=headers,
            details={"retry_after": retry_after} if retry_after else {}
        )


class ExternalServiceException(AutoAdminException):
    """Exception for external service errors"""

    def __init__(self, service: str, message: str, details: Dict[str, Any] = None):
        error_details = {"service": service}
        if details:
            error_details.update(details)
        super().__init__(
            message=f"{service} error: {message}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=ErrorCodes.EXTERNAL_SERVICE_ERROR,
            details=error_details
        )


class DatabaseException(AutoAdminException):
    """Exception for database errors"""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            message=f"Database error: {message}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCodes.DATABASE_ERROR,
            details=details
        )


def get_correlation_id(request: Request) -> str:
    """Get or generate correlation ID for request tracking"""
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    return correlation_id


def create_error_response(
    error_code: str,
    message: str,
    status_code: int,
    correlation_id: str,
    details: Dict[str, Any] = None,
    timestamp: datetime = None
) -> Dict[str, Any]:
    """Create standardized error response format"""

    if timestamp is None:
        timestamp = datetime.utcnow()

    error_response = {
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code,
            "timestamp": timestamp.isoformat() + "Z",
            "correlation_id": correlation_id
        }
    }

    # Add details if provided
    if details:
        error_response["error"]["details"] = details

    # Add request information in development mode
    if settings.ENVIRONMENT == "development":
        error_response["error"]["debug_info"] = {
            "environment": settings.ENVIRONMENT,
            "docs_url": "/docs" if settings.ENVIRONMENT != "production" else None
        }

    return error_response


async def autoadmin_exception_handler(request: Request, exc: AutoAdminException) -> JSONResponse:
    """Handle custom AutoAdmin exceptions"""

    correlation_id = get_correlation_id(request)

    if exc.should_log:
        logger.error(
            f"AutoAdmin exception: {exc.error_code}",
            error_code=exc.error_code,
            status_code=exc.status_code,
            message=exc.message,
            details=exc.details,
            correlation_id=correlation_id,
            path=str(request.url),
            method=request.method,
            client_ip=request.client.host if request.client else None
        )

    error_response = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        correlation_id=correlation_id,
        details=exc.details
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
        headers=exc.headers
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation exceptions"""

    correlation_id = get_correlation_id(request)

    # Format field errors for better readability
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })

    logger.warning(
        "Validation error",
        errors=formatted_errors,
        correlation_id=correlation_id,
        path=str(request.url),
        method=request.method
    )

    error_response = create_error_response(
        error_code=ErrorCodes.VALIDATION_ERROR,
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        correlation_id=correlation_id,
        details={"field_errors": formatted_errors}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions"""

    correlation_id = get_correlation_id(request)

    # Map HTTP status codes to error codes
    error_code_map = {
        400: ErrorCodes.INVALID_REQUEST_FORMAT,
        401: ErrorCodes.AUTHENTICATION_REQUIRED,
        403: ErrorCodes.ACCESS_DENIED,
        404: ErrorCodes.RESOURCE_NOT_FOUND,
        409: ErrorCodes.RESOURCE_CONFLICT,
        429: ErrorCodes.RATE_LIMIT_EXCEEDED,
        500: ErrorCodes.INTERNAL_SERVER_ERROR,
        502: ErrorCodes.BAD_GATEWAY,
        503: ErrorCodes.SERVICE_TEMPORARILY_UNAVAILABLE
    }

    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

    logger.warning(
        f"HTTP {exc.status_code} error",
        detail=exc.detail,
        correlation_id=correlation_id,
        path=str(request.url),
        method=request.method
    )

    error_response = create_error_response(
        error_code=error_code,
        message=exc.detail,
        status_code=exc.status_code,
        correlation_id=correlation_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation exceptions"""

    correlation_id = get_correlation_id(request)

    logger.warning(
        "Pydantic validation error",
        errors=exc.errors(),
        correlation_id=correlation_id,
        path=str(request.url),
        method=request.method
    )

    error_response = create_error_response(
        error_code=ErrorCodes.PYDANTIC_VALIDATION_ERROR,
        message="Data validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        correlation_id=correlation_id,
        details={"field_errors": exc.errors()}
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions"""

    correlation_id = get_correlation_id(request)

    logger.exception(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        correlation_id=correlation_id,
        path=str(request.url),
        method=request.method,
        client_ip=request.client.host if request.client else None,
        traceback=traceback.format_exc()
    )

    # Don't expose internal errors in production
    if settings.ENVIRONMENT == "production":
        message = "An internal error occurred"
        details = {}
    else:
        message = str(exc)
        details = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }

    error_response = create_error_response(
        error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        correlation_id=correlation_id,
        details=details
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response
    )


async def correlation_id_middleware(request: Request, call_next):
    """Middleware to add correlation ID to request state"""

    correlation_id = get_correlation_id(request)
    request.state.correlation_id = correlation_id

    # Add correlation ID to response headers
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id

    return response


def add_exception_handlers(app: FastAPI):
    """Add all exception handlers to FastAPI application"""

    # Add correlation ID middleware
    app.middleware("http")(correlation_id_middleware)

    # Custom exception handlers
    app.add_exception_handler(AutoAdminException, autoadmin_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)

    # Fallback handler for uncaught exceptions
    app.add_exception_handler(Exception, general_exception_handler)


# Error response examples for OpenAPI documentation
ERROR_RESPONSES = {
    400: {
        "description": "Bad Request - Invalid request format or parameters",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INVALID_REQUEST_FORMAT",
                        "message": "Invalid request format",
                        "status_code": 400,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "details": {
                            "invalid_field": "value",
                            "expected_format": "string"
                        }
                    }
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Authentication required",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "Authentication required",
                        "status_code": 401,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000"
                    }
                }
            }
        }
    },
    403: {
        "description": "Forbidden - Insufficient permissions",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "Access denied",
                        "status_code": 403,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "details": {
                            "resource": "admin_endpoint",
                            "required_permission": "admin"
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found - Resource not found",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RESOURCE_NOT_FOUND",
                        "message": "Agent not found with identifier: agent-123",
                        "status_code": 404,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "details": {
                            "resource": "Agent",
                            "identifier": "agent-123"
                        }
                    }
                }
            }
        }
    },
    422: {
        "description": "Unprocessable Entity - Validation error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "status_code": 422,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "details": {
                            "field_errors": [
                                {
                                    "field": "agent_id",
                                    "message": "field required",
                                    "type": "value_error.missing"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Rate limit exceeded",
                        "status_code": 429,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "details": {
                            "retry_after": 60
                        }
                    }
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An internal error occurred",
                        "status_code": 500,
                        "timestamp": "2024-01-01T00:00:00Z",
                        "correlation_id": "123e4567-e89b-12d3-a456-426614174000"
                    }
                }
            }
        }
    }
}