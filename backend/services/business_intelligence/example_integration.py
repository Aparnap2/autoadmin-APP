"""
Business Intelligence Integration Example
Complete example showing how to integrate the business intelligence module
with an existing FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .integration_config import (
    configure_business_intelligence_integration,
    setup_background_tasks,
    validate_integration,
    get_integration_config
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for business intelligence integration.
    Handles startup and shutdown events.
    """
    logger.info("Starting up business intelligence integration...")

    # Validate integration
    validation_results = validate_integration()
    if validation_results["status"] == "fail":
        logger.error(
            "Business intelligence integration validation failed",
            extra={"validation_results": validation_results}
        )
        # You might want to raise an exception here in production
        # raise RuntimeError("Business intelligence integration validation failed")

    logger.info("Business intelligence integration startup complete")

    yield

    logger.info("Shutting down business intelligence integration...")


def create_app_with_business_intelligence() -> FastAPI:
    """
    Create a FastAPI application with full business intelligence integration.

    Returns:
        Configured FastAPI application instance
    """

    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="AutoAdmin with Business Intelligence",
        description="Complete business intelligence and automation platform",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # Configure CORS for frontend integration
    # Adjust these origins based on your frontend deployment
    cors_origins = [
        "http://localhost:3000",    # React development
        "http://localhost:19006",  # Expo development
        "http://localhost:8081",    # Existing frontend
        "https://yourdomain.com",   # Production frontend
        "https://admin.yourdomain.com",  # Production admin panel
    ]

    # Configure business intelligence integration
    configure_business_intelligence_integration(
        app=app,
        cors_origins=cors_origins,
        enable_sse_middleware=True,
        enable_polling_middleware=True,
        enable_connection_tracking=True
    )

    # Setup background tasks
    setup_background_tasks(app)

    # Add custom error handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception: {exc}",
            extra={
                "url": str(request.url),
                "method": request.method,
                "error": str(exc)
            }
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "timestamp": "2024-01-01T00:00:00Z"  # Use actual timestamp
            }
        )

    # Add health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Overall application health check"""
        try:
            # Get BI integration status
            bi_config = get_integration_config()

            return {
                "status": "healthy",
                "timestamp": "2024-01-01T00:00:00Z",  # Use actual timestamp
                "version": "2.0.0",
                "business_intelligence": {
                    "status": "integrated",
                    "features_enabled": len([
                        f for f in bi_config["features"]
                        if bi_config["features"][f]["enabled"]
                    ]),
                    "streaming_enabled": True,
                    "api_version": bi_config["api_version"]
                },
                "endpoints": {
                    "api_docs": "/docs",
                    "business_intelligence": bi_config["base_path"],
                    "streaming": bi_config["streaming_path"]
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "error": str(e)
                }
            )

    # Add root redirect to API documentation
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information"""
        config = get_integration_config()

        return {
            "message": "AutoAdmin Business Intelligence API",
            "version": "2.0.0",
            "status": "operational",
            "endpoints": {
                "documentation": "/docs",
                "business_intelligence": config["base_path"],
                "streaming": config["streaming_path"],
                "health": "/health"
            },
            "features": {
                name: details["enabled"]
                for name, details in config["features"].items()
            }
        }

    # Add API info endpoint
    @app.get("/api/info", tags=["API"])
    async def api_info():
        """Get detailed API information"""
        config = get_integration_config()

        return {
            "api_name": "AutoAdmin Business Intelligence",
            "version": "2.0.0",
            "description": "Complete business intelligence and automation platform",
            "base_url": "/api/v2",
            "business_intelligence": {
                "base_path": config["base_path"],
                "features": config["features"],
                "middleware": config["middleware"],
                "endpoints": config["endpoints"]
            },
            "streaming": {
                "protocol": "Server-Sent Events",
                "fallback": "HTTP Polling",
                "endpoints": {
                    "executive_dashboard": "/api/v2/business-intelligence/stream/dashboard/{user_id}",
                    "morning_briefing": "/api/v2/business-intelligence/stream/morning-briefing/{user_id}",
                    "kpi_dashboard": "/api/v2/business-intelligence/stream/kpi-dashboard/{dashboard_id}/{user_id}",
                    "alerts": "/api/v2/business-intelligence/stream/alerts/{user_id}"
                }
            },
            "frontend_integration": {
                "react_components": True,
                "typescript_support": True,
                "sse_client": True,
                "automatic_reconnection": True
            }
        }

    return app


# Example: How to integrate with existing main.py
def integrate_with_existing_app(existing_app: FastAPI) -> FastAPI:
    """
    Example function showing how to integrate business intelligence
    with an existing FastAPI application.

    Args:
        existing_app: Existing FastAPI application instance

    Returns:
        Enhanced FastAPI application with business intelligence
    """

    logger.info("Integrating business intelligence with existing application...")

    # Configure business intelligence integration
    configure_business_intelligence_integration(
        app=existing_app,
        cors_origins=[
            "http://localhost:3000",
            "http://localhost:19006",
            "http://localhost:8081"
        ],
        enable_sse_middleware=True,
        enable_polling_middleware=True,
        enable_connection_tracking=True
    )

    # Setup background tasks
    setup_background_tasks(existing_app)

    # Add business intelligence health check to existing app
    @existing_app.get("/bi/health", tags=["Business Intelligence"])
    async def bi_health_check():
        """Business intelligence specific health check"""
        validation_results = validate_integration()
        config = get_integration_config()

        return {
            "business_intelligence": {
                "status": validation_results["status"],
                "validation": validation_results["checks"],
                "api_version": config["api_version"],
                "features_enabled": len([
                    f for f in config["features"]
                    if config["features"][f]["enabled"]
                ])
            }
        }

    logger.info("Business intelligence integration complete")

    return existing_app


# Example usage
if __name__ == "__main__":
    import uvicorn

    # Create and run the application
    app = create_app_with_business_intelligence()

    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )


# Development helper functions
def run_validation():
    """Run integration validation and print results"""
    print("Validating business intelligence integration...")

    results = validate_integration()

    print(f"Status: {results['status']}")
    print("\nChecks:")
    for check_name, check_result in results['checks'].items():
        status_symbol = "✓" if check_result['status'] == 'pass' else "✗"
        print(f"  {status_symbol} {check_name}: {check_result['status']}")

    if results['issues']:
        print("\nIssues:")
        for issue in results['issues']:
            print(f"  • {issue}")

    if results['recommendations']:
        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"  • {rec}")

    return results


def print_integration_info():
    """Print detailed integration information"""
    config = get_integration_config()

    print("Business Intelligence Integration Configuration")
    print("=" * 50)
    print(f"API Version: {config['api_version']}")
    print(f"Base Path: {config['base_path']}")
    print(f"Streaming Path: {config['streaming_path']}")

    print("\nEnabled Features:")
    for feature_name, feature_config in config['features'].items():
        status = "✓" if feature_config['enabled'] else "✗"
        print(f"  {status} {feature_name.replace('_', ' ').title()}")

    print("\nAvailable Endpoints:")
    for endpoint_type, endpoints in config['endpoints'].items():
        print(f"\n{endpoint_type.replace('_', ' ').title()}:")
        if isinstance(endpoints, dict):
            for name, path in endpoints.items():
                print(f"  {name}: {path}")
        else:
            print(f"  {endpoints}")

    print("\nMiddleware:")
    for middleware_name, middleware_config in config['middleware'].items():
        status = "✓" if middleware_config['enabled'] else "✗"
        print(f"  {status} {middleware_name.replace('_', ' ').title()}")
        print(f"    Purpose: {middleware_config['purpose']}")


# Export main functions
__all__ = [
    "create_app_with_business_intelligence",
    "integrate_with_existing_app",
    "run_validation",
    "print_integration_info"
]