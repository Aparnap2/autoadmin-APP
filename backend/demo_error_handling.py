#!/usr/bin/env python3
"""
Demo script to showcase AutoAdmin API error handling
Demonstrates various error scenarios and response formats
"""

import asyncio
import json
import uuid
import random
from datetime import datetime
from typing import Dict, Any, List

# Import our error handling components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'fastapi', 'app', 'middleware'))

from error_handler import (
    AutoAdminException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    ConflictException,
    RateLimitException,
    ExternalServiceException,
    DatabaseException,
    ErrorCodes,
    create_error_response,
    get_correlation_id
)


class ErrorDemo:
    """Demonstration of error handling scenarios"""

    def __init__(self):
        self.demonstrations = [
            self.demo_validation_error,
            self.demo_authentication_error,
            self.demo_authorization_error,
            self.demo_resource_not_found,
            self.demo_conflict_error,
            self.demo_rate_limit_error,
            self.demo_external_service_error,
            self.demo_database_error,
            self.demo_internal_server_error,
            self.demo_correlation_id_handling
        ]

    async def run_all_demos(self):
        """Run all error handling demonstrations"""
        print("🚀 AutoAdmin API Error Handling Demonstrations")
        print("=" * 60)

        for demo in self.demonstrations:
            try:
                print(f"\n📋 {demo.__name__.replace('demo_', '').title()}:")
                print("-" * 40)
                await demo()
                print("✅ Demo completed successfully")
            except Exception as e:
                print(f"❌ Demo failed: {e}")

        print("\n" + "=" * 60)
        print("🎉 All error handling demonstrations completed!")

    async def demo_validation_error(self):
        """Demonstrate validation error handling"""
        print("Showing validation error for invalid agent configuration...")

        correlation_id = str(uuid.uuid4())

        # Create a validation exception
        exception = ValidationException(
            "Invalid agent configuration",
            field_errors=[
                {
                    "field": "max_concurrent_tasks",
                    "message": "must be greater than 0",
                    "type": "value_error.number.not_gt",
                    "input": -1
                },
                {
                    "field": "agent_type",
                    "message": "must be a valid agent type",
                    "type": "value_error.invalid_choice",
                    "input": "invalid_type",
                    "allowed_choices": ["marketing", "finance", "devops", "strategy"]
                }
            ],
            details={
                "agent_id": "test-agent-123",
                "configuration_version": "1.0"
            }
        )

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details=exception.details
        )

        print(json.dumps(error_response, indent=2))

    async def demo_authentication_error(self):
        """Demonstrate authentication error handling"""
        print("Showing authentication error for missing or invalid token...")

        correlation_id = str(uuid.uuid4())

        exception = AuthenticationException("Invalid or expired authentication token")

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id
        )

        print(json.dumps(error_response, indent=2))
        print(f"\nResponse Headers: WWW-Authenticate: {exception.headers.get('WWW-Authenticate')}")

    async def demo_authorization_error(self):
        """Demonstrate authorization error handling"""
        print("Showing authorization error for insufficient permissions...")

        correlation_id = str(uuid.uuid4())

        exception = AuthorizationException(
            "Insufficient permissions to access admin endpoints",
            resource="admin_panel"
        )

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details=exception.details
        )

        print(json.dumps(error_response, indent=2))

    async def demo_resource_not_found(self):
        """Demonstrate resource not found error handling"""
        print("Showing resource not found error for missing agent...")

        correlation_id = str(uuid.uuid4())

        exception = ResourceNotFoundException("Agent", "nonexistent-agent-999")

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details=exception.details
        )

        print(json.dumps(error_response, indent=2))

    async def demo_conflict_error(self):
        """Demonstrate conflict error handling"""
        print("Showing conflict error for duplicate agent creation...")

        correlation_id = str(uuid.uuid4())

        exception = ConflictException(
            "Agent with this email already exists",
            details={
                "conflicting_field": "email",
                "existing_value": "agent@autoadmin.com",
                "existing_agent_id": "marketing-001"
            }
        )

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details=exception.details
        )

        print(json.dumps(error_response, indent=2))

    async def demo_rate_limit_error(self):
        """Demonstrate rate limit error handling"""
        print("Showing rate limit error for exceeding API quotas...")

        correlation_id = str(uuid.uuid4())

        exception = RateLimitException(
            "API rate limit exceeded. Too many requests in the last minute.",
            retry_after=60
        )

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details={"retry_after": 60}
        )

        print(json.dumps(error_response, indent=2))
        print(f"\nResponse Headers: Retry-After: {exception.headers.get('Retry-After')} seconds")

    async def demo_external_service_error(self):
        """Demonstrate external service error handling"""
        print("Showing external service error for OpenAI API failure...")

        correlation_id = str(uuid.uuid4())

        exception = ExternalServiceException(
            service="OpenAI",
            message="Service temporarily unavailable due to high demand",
            details={
                "service_status": "503 Service Unavailable",
                "retry_after": 30,
                "api_endpoint": "https://api.openai.com/v1/chat/completions",
                "original_error_code": "service_unavailable"
            }
        )

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details=exception.details
        )

        print(json.dumps(error_response, indent=2))

    async def demo_database_error(self):
        """Demonstrate database error handling"""
        print("Showing database error for connection timeout...")

        correlation_id = str(uuid.uuid4())

        exception = DatabaseException(
            "Database connection timeout",
            details={
                "database": "postgresql",
                "error_code": "connection_timeout",
                "query_duration_ms": 30000,
                "connection_pool": "primary",
                "retry_attempts": 3
            }
        )

        error_response = create_error_response(
            error_code=exception.error_code,
            message=exception.message,
            status_code=exception.status_code,
            correlation_id=correlation_id,
            details=exception.details
        )

        print(json.dumps(error_response, indent=2))

    async def demo_internal_server_error(self):
        """Demonstrate internal server error handling"""
        print("Showing internal server error for unexpected failure...")

        correlation_id = str(uuid.uuid4())

        # Simulate production mode (hides sensitive details)
        from error_handler import settings
        original_env = getattr(settings, 'ENVIRONMENT', 'development')

        # First show development mode with details
        print("\n📊 Development Mode (with details):")
        development_response = create_error_response(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Failed to process agent task: Division by zero",
            status_code=500,
            correlation_id=correlation_id,
            details={
                "exception_type": "ZeroDivisionError",
                "traceback": "Traceback (most recent call last):..."
            }
        )
        print(json.dumps(development_response, indent=2))

        # Then show production mode (without details)
        print("\n🏭 Production Mode (sanitized):")
        production_response = create_error_response(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="An internal error occurred",
            status_code=500,
            correlation_id=correlation_id,
            details={}  # No sensitive details in production
        )
        print(json.dumps(production_response, indent=2))

    async def demo_correlation_id_handling(self):
        """Demonstrate correlation ID handling"""
        print("Showing correlation ID propagation through requests...")

        # Simulate client-provided correlation ID
        client_correlation_id = f"client-{int(datetime.now().timestamp())}"
        print(f"\n📤 Client provides correlation ID: {client_correlation_id}")

        # Simulate server-generated correlation ID
        server_correlation_id = str(uuid.uuid4())
        print(f"🔄 Server generates correlation ID: {server_correlation_id}")

        error_examples = [
            {
                "name": "Client-provided correlation ID",
                "correlation_id": client_correlation_id,
                "error": ValidationException("Invalid input", details={"field": "name"})
            },
            {
                "name": "Server-generated correlation ID",
                "correlation_id": server_correlation_id,
                "error": ResourceNotFoundException("Task", "task-123")
            }
        ]

        for example in error_examples:
            print(f"\n📋 {example['name']}:")
            error_response = create_error_response(
                error_code=example["error"].error_code,
                message=example["error"].message,
                status_code=example["error"].status_code,
                correlation_id=example["correlation_id"],
                details=example["error"].details
            )
            print(json.dumps(error_response, indent=2))

    def show_error_code_reference(self):
        """Display reference of all available error codes"""
        print("\n📚 Error Code Reference:")
        print("=" * 40)

        error_categories = {
            "Validation Errors (400)": [
                ErrorCodes.VALIDATION_ERROR,
                ErrorCodes.INVALID_REQUEST_FORMAT,
                ErrorCodes.MISSING_REQUIRED_FIELD,
                ErrorCodes.INVALID_FIELD_VALUE
            ],
            "Authentication Errors (401)": [
                ErrorCodes.AUTHENTICATION_REQUIRED,
                ErrorCodes.INVALID_TOKEN,
                ErrorCodes.TOKEN_EXPIRED
            ],
            "Authorization Errors (403)": [
                ErrorCodes.ACCESS_DENIED,
                ErrorCodes.INSUFFICIENT_PERMISSIONS
            ],
            "Not Found Errors (404)": [
                ErrorCodes.RESOURCE_NOT_FOUND,
                ErrorCodes.AGENT_NOT_FOUND,
                ErrorCodes.TASK_NOT_FOUND
            ],
            "Conflict Errors (409)": [
                ErrorCodes.RESOURCE_CONFLICT,
                ErrorCodes.DUPLICATE_RESOURCE
            ],
            "Rate Limiting (429)": [
                ErrorCodes.RATE_LIMIT_EXCEEDED
            ],
            "Server Errors (500)": [
                ErrorCodes.INTERNAL_SERVER_ERROR,
                ErrorCodes.DATABASE_ERROR,
                ErrorCodes.AGENT_EXECUTION_ERROR
            ],
            "External Service Errors (502)": [
                ErrorCodes.EXTERNAL_SERVICE_ERROR,
                ErrorCodes.BAD_GATEWAY
            ]
        }

        for category, codes in error_categories.items():
            print(f"\n{category}:")
            for code in codes:
                print(f"  • {code}")

    def show_best_practices(self):
        """Display error handling best practices"""
        print("\n💡 Error Handling Best Practices:")
        print("=" * 40)

        practices = [
            "✅ Always use custom exception classes instead of generic HTTPException",
            "✅ Include relevant details in exceptions for debugging",
            "✅ Use appropriate HTTP status codes for different error types",
            "✅ Include correlation IDs in all error responses",
            "✅ Log errors with structured logging and context",
            "✅ Handle external service failures gracefully",
            "✅ Sanitize error messages in production environments",
            "✅ Test error scenarios in unit and integration tests",
            "✅ Provide clear error codes for frontend error handling",
            "✅ Include retry information when applicable"
        ]

        for practice in practices:
            print(f"  {practice}")

        print("\n🔍 For Developers:")
        developer_tips = [
            "📖 Read the ERROR_HANDLING_GUIDE.md for comprehensive documentation",
            "🧪 Run test_error_handling.py to validate error responses",
            "📝 Use error codes, not error messages, for programmatic handling",
            "🔗 Always include correlation IDs when reporting issues",
            "🚫 Never expose sensitive information in production error messages"
        ]

        for tip in developer_tips:
            print(f"  {tip}")


async def main():
    """Main demo function"""
    demo = ErrorDemo()

    print("🎯 AutoAdmin API Error Handling Demo")
    print("This script demonstrates the comprehensive error handling system")
    print("implemented in the AutoAdmin backend API.\n")

    # Ask user what they want to see
    print("Select demo options (separate multiple choices with spaces):")
    print("1. Run all demonstrations")
    print("2. Validation errors")
    print("3. Authentication/Authorization errors")
    print("4. Resource and conflict errors")
    print("5. Rate limiting and external service errors")
    print("6. Server and database errors")
    print("7. Correlation ID handling")
    print("8. Error code reference")
    print("9. Best practices guide")
    print("10. All demonstrations (1)")

    try:
        choice = input("\nEnter your choice: ").strip()
        choices = choice.split()

        if not choices or '1' in choices or '10' in choices:
            await demo.run_all_demos()
        else:
            for choice in choices:
                if choice == '2':
                    await demo.demo_validation_error()
                elif choice == '3':
                    await demo.demo_authentication_error()
                    await demo.demo_authorization_error()
                elif choice == '4':
                    await demo.demo_resource_not_found()
                    await demo.demo_conflict_error()
                elif choice == '5':
                    await demo.demo_rate_limit_error()
                    await demo.demo_external_service_error()
                elif choice == '6':
                    await demo.demo_internal_server_error()
                    await demo.demo_database_error()
                elif choice == '7':
                    await demo.demo_correlation_id_handling()
                elif choice == '8':
                    demo.show_error_code_reference()
                elif choice == '9':
                    demo.show_best_practices()

        # Always show best practices at the end
        if '9' not in choices:
            demo.show_best_practices()

    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")


if __name__ == "__main__":
    asyncio.run(main())