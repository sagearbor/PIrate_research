"""
FastAPI application entry point for the Faculty Research Opportunity Notifier.

This application provides endpoints for the multi-agent research opportunity matching system.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator
import logging
from datetime import datetime
import asyncio
import time
import uuid

# Import metrics, logging, and documentation modules
from src.core.metrics import (
    http_requests_total, 
    http_request_duration_seconds,
    update_system_metrics
)
# Temporarily simplified for testing
import logging
from src.core.api_documentation import (
    setup_api_documentation,
    HealthResponse,
    DetailedHealthResponse,
    ReadinessResponse,
    RootResponse,
    ErrorResponse,
    RESPONSE_EXAMPLES
)
from src.core.circuit_breaker import (
    get_external_services_health,
    get_external_services_status
)
from src.core.security_monitoring import (
    log_request_security,
    check_rate_limit,
    get_security_status,
    security_cleanup_task
)
from src.dashboard import setup_dashboard_routes

# Configure structured logging
# setup_structured_logging(log_level="INFO", enable_json=True)
logger = logging.getLogger(__name__)


async def update_metrics_task():
    """Background task to update system metrics periodically."""
    while True:
        try:
            update_system_metrics()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")
            await asyncio.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Faculty Research Opportunity Notifier API starting up...")
    logger.info("Health check endpoint available at /health")
    logger.info("Metrics endpoint available at /metrics")
    
    # Start background tasks
    metrics_task = asyncio.create_task(update_metrics_task())
    security_task = asyncio.create_task(security_cleanup_task())
    
    yield
    
    # Shutdown
    logger.info("Faculty Research Opportunity Notifier API shutting down...")
    metrics_task.cancel()
    security_task.cancel()
    try:
        await metrics_task
    except asyncio.CancelledError:
        pass
    try:
        await security_task
    except asyncio.CancelledError:
        pass


# Create FastAPI application instance
app = FastAPI(
    title="Faculty Research Opportunity Notifier",
    description="AI-driven multi-agent system connecting university faculty with relevant research funding opportunities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Initialize Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Setup comprehensive API documentation
setup_api_documentation(app)

# Setup admin dashboard routes
setup_dashboard_routes(app)

# Custom metrics, logging, and security middleware
@app.middleware("http")
async def comprehensive_middleware(request: Request, call_next):
    """Custom middleware for metrics, logging, and security monitoring."""
    start_time = time.time()
    
    # Set correlation ID for request tracking
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    # set_correlation_id(correlation_id)
    
    # Get client information
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Rate limiting check
    if not await check_rate_limit(client_ip, request.url.path):
        logger.warning(
            f"Rate limit exceeded for IP {client_ip} on endpoint {request.url.path} "
            f"(correlation_id: {correlation_id})"
        )
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please try again later.",
                "correlation_id": correlation_id,
                "timestamp": datetime.now().isoformat()
            },
            headers={"X-Correlation-ID": correlation_id}
        )
    
    # Log API access for security monitoring
    # security_logger.log_api_access(
    #     endpoint=request.url.path,
    #     method=request.method,
    #     user_agent=user_agent,
    #     ip_address=client_ip,
    #     correlation_id=correlation_id
    # )
    
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Security monitoring - log request details
    await log_request_security(
        ip_address=client_ip,
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        user_agent=user_agent,
        response_time=process_time,
        correlation_id=correlation_id
    )
    
    # Record metrics
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    # Add timing and correlation headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Correlation-ID"] = correlation_id
    
    # Log response
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"status={response.status_code} duration={process_time:.3f}s "
        f"correlation_id={correlation_id}"
    )
    
    return response


@app.get(
    "/",
    response_model=RootResponse,
    tags=["Health & Monitoring"],
    summary="API Information",
    description="Get basic information about the Faculty Research Opportunity Notifier API",
    responses={
        200: {
            "description": "API information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Faculty Research Opportunity Notifier API",
                        "version": "1.0.0",
                        "status": "active",
                        "timestamp": "2025-01-01T12:00:00.000Z"
                    }
                }
            }
        }
    }
)
async def root():
    """Root endpoint providing basic API information."""
    return {
        "message": "Faculty Research Opportunity Notifier API",
        "version": "1.0.0",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health & Monitoring"],
    summary="Basic Health Check",
    description="Performs a basic health check to verify the API is running and responsive",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": RESPONSE_EXAMPLES["health_healthy"]
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    Basic health check endpoint for monitoring application status.
    
    Returns:
        HealthResponse: Basic health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Faculty Research Opportunity Notifier",
        "version": "1.0.0"
    }

@app.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    tags=["Health & Monitoring"],
    summary="Detailed Health Check",
    description="Comprehensive health check including system metrics, component status, and detailed diagnostics",
    responses={
        200: {
            "description": "Detailed health information retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": RESPONSE_EXAMPLES["health_detailed"],
                        "degraded": RESPONSE_EXAMPLES["health_degraded"]
                    }
                }
            }
        }
    }
)
async def detailed_health_check():
    """
    Detailed health check endpoint with system metrics and component status.
    
    Returns:
        DetailedHealthResponse: Comprehensive health status including system metrics
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Faculty Research Opportunity Notifier",
        "version": "1.0.0",
        "components": {
            "api": "healthy",
            "metrics": "healthy",
            "logging": "healthy"
        },
        "system": {}
    }
    
    try:
        import psutil
        # System metrics
        health_status["system"] = {
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            },
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count()
            },
            "disk": {
                "usage": psutil.disk_usage('/').percent
            }
        }
    except ImportError:
        health_status["system"]["note"] = "psutil not available, system metrics unavailable"
    except Exception as e:
        health_status["components"]["system_metrics"] = "unhealthy"
        health_status["system"]["error"] = str(e)
        
    # Check if any components are unhealthy
    if any(status == "unhealthy" for status in health_status["components"].values()):
        health_status["status"] = "degraded"
        
    return health_status

@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["Health & Monitoring"],
    summary="Readiness Check",
    description="Kubernetes/container orchestration readiness check to verify service dependencies are available",
    responses={
        200: {
            "description": "Service readiness status",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": RESPONSE_EXAMPLES["readiness_ready"],
                        "not_ready": RESPONSE_EXAMPLES["readiness_not_ready"]
                    }
                }
            }
        }
    }
)
async def readiness_check():
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns:
        ReadinessResponse: Readiness status for the application
    """
    # Add checks for dependencies here (databases, external APIs, etc.)
    ready_status = {
        "ready": True,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "api": True,
            "metrics": True
        }
    }
    
    # If any checks fail, set ready to False
    if not all(ready_status["checks"].values()):
        ready_status["ready"] = False
        
    return ready_status

@app.get(
    "/health/external-services",
    tags=["Health & Monitoring"],
    summary="External Services Health",
    description="Check the health status of all external services with circuit breaker information",
    responses={
        200: {
            "description": "External services health status",
            "content": {
                "application/json": {
                    "example": {
                        "nih_reporter": {
                            "service": "nih_reporter",
                            "status": "healthy",
                            "circuit_breaker": {
                                "state": "closed",
                                "total_calls": 150,
                                "successful_calls": 145,
                                "failed_calls": 5,
                                "success_rate": 0.967
                            },
                            "last_check": 1640995200.0
                        },
                        "google_scholar": {
                            "service": "google_scholar", 
                            "status": "degraded",
                            "circuit_breaker": {
                                "state": "half_open",
                                "total_calls": 75,
                                "successful_calls": 60,
                                "failed_calls": 15,
                                "success_rate": 0.8
                            }
                        }
                    }
                }
            }
        }
    }
)
async def external_services_health():
    """
    Check the health status of all external services.
    
    Returns comprehensive health information including:
    - Circuit breaker status and statistics
    - HTTP health check results (where available)
    - Service availability and performance metrics
    
    Returns:
        dict: External services health status
    """
    try:
        health_results = await get_external_services_health()
        status_results = get_external_services_status()
        
        # Combine health and status information
        combined_results = {}
        for service_name in status_results.keys():
            combined_results[service_name] = {
                **status_results[service_name],
                **health_results.get(service_name, {})
            }
        
        return combined_results
        
    except Exception as e:
        logger.error(f"Failed to get external services health: {e}")
        return {
            "error": "Failed to retrieve external services health",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get(
    "/security/status",
    tags=["Health & Monitoring"],
    summary="Security Monitoring Status",
    description="Get comprehensive security monitoring status including threat detection, rate limiting, and suspicious activity",
    responses={
        200: {
            "description": "Security monitoring status",
            "content": {
                "application/json": {
                    "example": {
                        "summary": {
                            "total_events_24h": 25,
                            "high_risk_events": 2,
                            "suspicious_ips": 3,
                            "blocked_ips": 1,
                            "active_patterns": 15
                        },
                        "event_types": {
                            "suspicious_activity": 10,
                            "rate_limit_exceeded": 8,
                            "auth_failure": 5,
                            "potential_attack": 2
                        },
                        "security_levels": {
                            "low": 15,
                            "medium": 8,
                            "high": 2
                        },
                        "top_suspicious_ips": [
                            {"ip": "192.168.1.100", "risk_score": 45.5},
                            {"ip": "10.0.0.50", "risk_score": 32.1}
                        ],
                        "rate_limiter": {
                            "max_requests": 100,
                            "window_seconds": 60,
                            "active_ips": 25,
                            "blocked_ips": 1,
                            "warning_ips": 3
                        }
                    }
                }
            }
        }
    }
)
async def security_status():
    """
    Get comprehensive security monitoring status.
    
    Returns detailed security information including:
    - Security event summary for the last 24 hours
    - Top suspicious IP addresses and their risk scores  
    - Rate limiting statistics and blocked IPs
    - Security event distribution by type and severity level
    
    Returns:
        dict: Security monitoring status and statistics
    """
    try:
        return await get_security_status()
    except Exception as e:
        logger.error(f"Failed to get security status: {e}")
        return {
            "error": "Failed to retrieve security status",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)