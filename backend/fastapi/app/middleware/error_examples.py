"""
Error handling examples and test scenarios for AutoAdmin API
Demonstrates various error responses and their formats
"""

from typing import Dict, Any
from datetime import datetime
from app.middleware.error_handler import (
    AutoAdminException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    RateLimitException,
    ExternalServiceException,
    DatabaseException,
    ErrorCodes
)


class ErrorExamples:
    """Example error scenarios and their expected responses"""

    @staticmethod
    def validation_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of a validation error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.VALIDATION_ERROR,
                "message": "Agent {agent_id} does not support task type {task_type}",
                "status_code": 422,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "agent_id": "marketing-001",
                    "task_type": "code_deployment",
                    "supported_types": [
                        "content_creation",
                        "research",
                        "social_media",
                        "email_outreach"
                    ]
                }
            }
        }

    @staticmethod
    def authentication_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of an authentication error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.AUTHENTICATION_REQUIRED,
                "message": "Authentication required",
                "status_code": 401,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id
            }
        }

    @staticmethod
    def authorization_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of an authorization error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.ACCESS_DENIED,
                "message": "Access denied",
                "status_code": 403,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "resource": "admin_endpoint",
                    "required_permission": "admin"
                }
            }
        }

    @staticmethod
    def not_found_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of a resource not found error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.RESOURCE_NOT_FOUND,
                "message": "Agent not found with identifier: agent-999",
                "status_code": 404,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "resource": "Agent",
                    "identifier": "agent-999"
                }
            }
        }

    @staticmethod
    def conflict_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of a conflict error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.RESOURCE_CONFLICT,
                "message": "Agent with this ID already exists",
                "status_code": 409,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "existing_agent_id": "marketing-001",
                    "conflict_field": "id"
                }
            }
        }

    @staticmethod
    def rate_limit_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of a rate limit error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                "message": "Agent marketing-001 is at maximum capacity (3 tasks)",
                "status_code": 429,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "retry_after": 300,
                    "current_load": 3,
                    "max_capacity": 3
                }
            }
        }

    @staticmethod
    def external_service_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of an external service error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.EXTERNAL_SERVICE_ERROR,
                "message": "OpenAI error: Service temporarily unavailable",
                "status_code": 502,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "service": "OpenAI",
                    "service_error_code": "service_unavailable",
                    "retry_after": 60
                }
            }
        }

    @staticmethod
    def database_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of a database error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.DATABASE_ERROR,
                "message": "Database error: Connection timeout",
                "status_code": 500,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id,
                "details": {
                    "database": "postgresql",
                    "error_code": "connection_timeout",
                    "query_duration_ms": 30000
                }
            }
        }

    @staticmethod
    def internal_server_error_example(correlation_id: str = None) -> Dict[str, Any]:
        """Example of an internal server error response"""
        if not correlation_id:
            correlation_id = "123e4567-e89b-12d3-a456-426614174000"

        return {
            "error": {
                "code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "An internal error occurred",
                "status_code": 500,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "correlation_id": correlation_id
            }
        }


class ErrorTesting:
    """Test scenarios for error handling"""

    @staticmethod
    def trigger_validation_exception():
        """Triggers a validation exception for testing"""
        raise ValidationException(
            "Invalid agent configuration",
            field_errors=[
                {
                    "field": "max_concurrent_tasks",
                    "message": "Must be greater than 0",
                    "type": "value_error.number.not_gt",
                    "input": -1
                }
            ],
            details={
                "agent_id": "test-agent",
                "invalid_field": "max_concurrent_tasks"
            }
        )

    @staticmethod
    def trigger_authentication_exception():
        """Triggers an authentication exception for testing"""
        raise AuthenticationException("Invalid or missing authentication token")

    @staticmethod
    def trigger_authorization_exception():
        """Triggers an authorization exception for testing"""
        raise AuthorizationException(
            "Insufficient permissions to access this resource",
            resource="admin_endpoint"
        )

    @staticmethod
    def trigger_resource_not_found_exception():
        """Triggers a resource not found exception for testing"""
        raise ResourceNotFoundException("Agent", "nonexistent-agent-123")

    @staticmethod
    def trigger_conflict_exception():
        """Triggers a conflict exception for testing"""
        raise ConflictException(
            "Agent already exists with this configuration",
            details={
                "conflicting_field": "email",
                "existing_value": "agent@example.com"
            }
        )

    @staticmethod
    def trigger_rate_limit_exception():
        """Triggers a rate limit exception for testing"""
        raise RateLimitException(
            "API rate limit exceeded",
            retry_after=60
        )

    @staticmethod
    def trigger_external_service_exception():
        """Triggers an external service exception for testing"""
        raise ExternalServiceException(
            service="OpenAI",
            message="Service temporarily unavailable",
            details={
                "service_error_code": "503",
                "retry_after": 30
            }
        )

    @staticmethod
    def trigger_database_exception():
        """Triggers a database exception for testing"""
        raise DatabaseException(
            "Failed to execute query",
            details={
                "query": "SELECT * FROM agents WHERE id = ?",
                "error": "Connection timeout"
            }
        )


# HTTP status code reference for developers
HTTP_STATUS_REFERENCE = {
    400: {
        "title": "Bad Request",
        "description": "The request is malformed or contains invalid parameters",
        "autoadmin_codes": [
            ErrorCodes.INVALID_REQUEST_FORMAT,
            ErrorCodes.MISSING_REQUIRED_FIELD,
            ErrorCodes.INVALID_FIELD_VALUE,
            ErrorCodes.INVALID_QUERY_PARAMETER
        ]
    },
    401: {
        "title": "Unauthorized",
        "description": "Authentication is required but has not been provided or is invalid",
        "autoadmin_codes": [
            ErrorCodes.AUTHENTICATION_REQUIRED,
            ErrorCodes.INVALID_TOKEN,
            ErrorCodes.TOKEN_EXPIRED,
            ErrorCodes.INVALID_CREDENTIALS
        ]
    },
    403: {
        "title": "Forbidden",
        "description": "Authentication is provided but the user does not have permission to access this resource",
        "autoadmin_codes": [
            ErrorCodes.ACCESS_DENIED,
            ErrorCodes.INSUFFICIENT_PERMISSIONS,
            ErrorCodes.RESOURCE_ACCESS_DENIED
        ]
    },
    404: {
        "title": "Not Found",
        "description": "The requested resource could not be found",
        "autoadmin_codes": [
            ErrorCodes.RESOURCE_NOT_FOUND,
            ErrorCodes.ENDPOINT_NOT_FOUND,
            ErrorCodes.AGENT_NOT_FOUND,
            ErrorCodes.TASK_NOT_FOUND,
            ErrorCodes.USER_NOT_FOUND
        ]
    },
    409: {
        "title": "Conflict",
        "description": "The request could not be completed due to a conflict with the current state of the resource",
        "autoadmin_codes": [
            ErrorCodes.RESOURCE_CONFLICT,
            ErrorCodes.DUPLICATE_RESOURCE,
            ErrorCodes.RESOURCE_ALREADY_EXISTS
        ]
    },
    422: {
        "title": "Unprocessable Entity",
        "description": "The request was well-formed but unable to be followed due to semantic errors",
        "autoadmin_codes": [
            ErrorCodes.VALIDATION_ERROR,
            ErrorCodes.INVALID_FILE_FORMAT,
            ErrorCodes.FILE_TOO_LARGE
        ]
    },
    429: {
        "title": "Too Many Requests",
        "description": "The user has sent too many requests in a given amount of time",
        "autoadmin_codes": [
            ErrorCodes.RATE_LIMIT_EXCEEDED,
            ErrorCodes.TOO_MANY_REQUESTS
        ]
    },
    500: {
        "title": "Internal Server Error",
        "description": "An unexpected error occurred on the server",
        "autoadmin_codes": [
            ErrorCodes.INTERNAL_SERVER_ERROR,
            ErrorCodes.DATABASE_ERROR,
            ErrorCodes.AGENT_EXECUTION_ERROR,
            ErrorCodes.TASK_PROCESSING_ERROR
        ]
    },
    502: {
        "title": "Bad Gateway",
        "description": "The server received an invalid response from the upstream server",
        "autoadmin_codes": [
            ErrorCodes.BAD_GATEWAY,
            ErrorCodes.EXTERNAL_SERVICE_ERROR,
            ErrorCodes.EXTERNAL_SERVICE_UNAVAILABLE
        ]
    },
    503: {
        "title": "Service Unavailable",
        "description": "The server is currently unable to handle the request",
        "autoadmin_codes": [
            ErrorCodes.SERVICE_TEMPORARILY_UNAVAILABLE,
            ErrorCodes.SERVICE_UNAVAILABLE,
            ErrorCodes.MAINTENANCE_MODE
        ]
    }
}


# Error handling best practices guidelines
ERROR_HANDLING_GUIDELINES = """
## AutoAdmin API Error Handling Guidelines

### 1. Use Custom Exceptions
Always use the custom exceptions from `app.middleware.error_handler` instead of generic HTTPException:

```python
# Bad
raise HTTPException(status_code=404, detail="Agent not found")

# Good
raise ResourceNotFoundException("Agent", agent_id)
```

### 2. Provide Detailed Error Information
Include relevant details in exception to help frontend developers:

```python
raise ValidationException(
    "Invalid agent configuration",
    details={
        "agent_id": agent_id,
        "invalid_field": "max_concurrent_tasks",
        "expected_range": "1-10"
    }
)
```

### 3. Use Appropriate HTTP Status Codes
Choose the correct HTTP status code based on the error type:
- 400: Bad Request (client error)
- 401: Unauthorized (authentication required)
- 403: Forbidden (authorization failed)
- 404: Not Found (resource doesn't exist)
- 409: Conflict (resource state conflict)
- 422: Unprocessable Entity (validation error)
- 429: Too Many Requests (rate limiting)
- 500: Internal Server Error (server-side error)
- 502: Bad Gateway (external service error)
- 503: Service Unavailable (temporarily down)

### 4. Include Correlation IDs
All error responses include correlation IDs for tracking:
- Request headers can include `X-Correlation-ID`
- Response headers will always include `X-Correlation-ID`
- Use correlation IDs when reporting issues to support

### 5. Log Errors Appropriately
- Use structured logging with correlation IDs
- Include relevant context in error logs
- Don't log sensitive information

### 6. Handle Exceptions Gracefully
Always catch exceptions and re-raise appropriate AutoAdmin exceptions:

```python
try:
    # External service call
    response = await external_service.call()
except ExternalServiceError as e:
    raise ExternalServiceException(
        service="ExternalAPI",
        message=f"Service call failed: {str(e)}",
        details={"original_error": str(e)}
    )
```

### 7. Frontend Error Handling
Frontend applications should:
- Check the `error.code` field for programmatic error handling
- Use `error.message` for user-facing error messages
- Include `correlation_id` when reporting issues
- Handle different HTTP status codes appropriately

### 8. Testing Error Scenarios
Test both happy path and error scenarios:
- Invalid input parameters
- Missing required fields
- Authentication/authorization failures
- Resource not found scenarios
- Rate limiting scenarios
- External service failures
- Database connection issues
"""