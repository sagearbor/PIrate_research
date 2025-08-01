"""
API documentation configuration and extensions for FastAPI.

This module provides comprehensive API documentation setup including:
- OpenAPI schema customization
- Response models and examples
- Authentication documentation
- Error response models
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# ============================================================================
# Response Models for Documentation
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Health status", example="healthy")
    timestamp: str = Field(..., description="ISO timestamp", example="2025-01-01T12:00:00")
    service: str = Field(..., description="Service name", example="Faculty Research Opportunity Notifier")
    version: str = Field(..., description="Service version", example="1.0.0")

class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str = Field(..., description="Overall health status", example="healthy")
    timestamp: str = Field(..., description="ISO timestamp", example="2025-01-01T12:00:00")
    service: str = Field(..., description="Service name", example="Faculty Research Opportunity Notifier")
    version: str = Field(..., description="Service version", example="1.0.0")
    
    class ComponentStatus(BaseModel):
        api: str = Field(..., description="API component status", example="healthy")
        metrics: str = Field(..., description="Metrics system status", example="healthy")
        logging: str = Field(..., description="Logging system status", example="healthy")
    
    class SystemMetrics(BaseModel):
        class MemoryInfo(BaseModel):
            total: int = Field(..., description="Total memory in bytes")
            available: int = Field(..., description="Available memory in bytes")
            percent: float = Field(..., description="Memory usage percentage")
        
        class CPUInfo(BaseModel):
            percent: float = Field(..., description="CPU usage percentage")
            count: int = Field(..., description="Number of CPU cores")
        
        class DiskInfo(BaseModel):
            usage: float = Field(..., description="Disk usage percentage")
        
        memory: MemoryInfo
        cpu: CPUInfo
        disk: DiskInfo
    
    components: ComponentStatus
    system: SystemMetrics

class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool = Field(..., description="Whether the service is ready", example=True)
    timestamp: str = Field(..., description="ISO timestamp", example="2025-01-01T12:00:00")
    
    class Checks(BaseModel):
        api: bool = Field(..., description="API readiness", example=True)
        metrics: bool = Field(..., description="Metrics system readiness", example=True)
    
    checks: Checks

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type", example="ValidationError")
    message: str = Field(..., description="Error message", example="Invalid input provided")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")
    timestamp: str = Field(..., description="Error timestamp", example="2025-01-01T12:00:00")

class RootResponse(BaseModel):
    """Root endpoint response model."""
    message: str = Field(..., description="Welcome message", example="Faculty Research Opportunity Notifier API")
    version: str = Field(..., description="API version", example="1.0.0")
    status: str = Field(..., description="Service status", example="active")
    timestamp: str = Field(..., description="Response timestamp", example="2025-01-01T12:00:00")

# ============================================================================
# API Documentation Examples
# ============================================================================

RESPONSE_EXAMPLES = {
    "health_healthy": {
        "summary": "Healthy service response",
        "value": {
            "status": "healthy",
            "timestamp": "2025-01-01T12:00:00.000Z",
            "service": "Faculty Research Opportunity Notifier",
            "version": "1.0.0"
        }
    },
    "health_detailed": {
        "summary": "Detailed health with system metrics",
        "value": {
            "status": "healthy",
            "timestamp": "2025-01-01T12:00:00.000Z",
            "service": "Faculty Research Opportunity Notifier",
            "version": "1.0.0",
            "components": {
                "api": "healthy",
                "metrics": "healthy",
                "logging": "healthy"
            },
            "system": {
                "memory": {
                    "total": 8589934592,
                    "available": 4294967296,
                    "percent": 50.0
                },
                "cpu": {
                    "percent": 25.5,
                    "count": 4
                },
                "disk": {
                    "usage": 45.2
                }
            }
        }
    },
    "health_degraded": {
        "summary": "Service with degraded health",
        "value": {
            "status": "degraded",
            "timestamp": "2025-01-01T12:00:00.000Z",
            "service": "Faculty Research Opportunity Notifier",
            "version": "1.0.0",
            "components": {
                "api": "healthy",
                "metrics": "unhealthy",
                "logging": "healthy"
            },
            "system": {
                "error": "Failed to collect system metrics"
            }
        }
    },
    "readiness_ready": {
        "summary": "Service ready",
        "value": {
            "ready": True,
            "timestamp": "2025-01-01T12:00:00.000Z",
            "checks": {
                "api": True,
                "metrics": True
            }
        }
    },
    "readiness_not_ready": {
        "summary": "Service not ready",
        "value": {
            "ready": False,
            "timestamp": "2025-01-01T12:00:00.000Z",
            "checks": {
                "api": True,
                "metrics": False
            }
        }
    },
    "error_validation": {
        "summary": "Validation error",
        "value": {
            "error": "ValidationError",
            "message": "Invalid input provided",
            "details": {
                "field": "email",
                "constraint": "must be a valid email address"
            },
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-01-01T12:00:00.000Z"
        }
    },
    "error_server": {
        "summary": "Internal server error",
        "value": {
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-01-01T12:00:00.000Z"
        }
    }
}

# ============================================================================
# OpenAPI Configuration
# ============================================================================

def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with comprehensive documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Faculty Research Opportunity Notifier API",
        version="1.0.0",
        description="""
# Faculty Research Opportunity Notifier API

## Overview

The Faculty Research Opportunity Notifier is an AI-driven multi-agent system that connects university faculty with relevant research funding opportunities. This API provides access to the core functionality including:

- **Multi-Agent Processing Pipeline**: Automated data ingestion, matching, and notification generation
- **Real-time Monitoring**: Comprehensive health checks and metrics collection
- **Structured Logging**: Full request tracing with correlation IDs
- **External Integration**: NIH, PCORI, Google Scholar, and other academic databases

## Architecture

The system follows a multi-agent pipeline architecture with the following components:

1. **Ingestion Agent** - Scrapes funding opportunities and faculty data
2. **Matcher Agent** - Multi-dimensional scoring system for opportunity matching
3. **Idea Generation Agent** - Generates proposal variants with budget estimates
4. **Collaborator Suggestion Agent** - Identifies potential collaborators
5. **Notification Agent** - Formats and prepares email notifications
6. **Admin Dashboard** - System monitoring and analytics
7. **Export Tools** - Formatted proposals and collaboration introductions

## Multi-Agent Communication (Phase 5)

In Phase 5, the system will implement Agent-to-Agent (A2A) communication using:
- Google Agent Development Kit (ADK)
- Model Context Protocol (MCP)
- Standardized message passing between agents

## Monitoring and Observability

The API includes comprehensive monitoring:
- **Prometheus Metrics**: Available at `/metrics`
- **Health Checks**: Basic (`/health`), Detailed (`/health/detailed`), Readiness (`/health/ready`)
- **Structured Logging**: JSON-formatted logs with correlation tracking
- **Security Auditing**: API access logging and anomaly detection

## Data Sources

The system integrates with multiple external data sources:
- **NIH Reporter**: Federal research funding opportunities
- **PCORI**: Patient-Centered Outcomes Research Institute
- **Google Scholar**: Faculty publication and citation data
- **arXiv**: Preprint research publications
- **PubMed**: Biomedical literature database
- **ORCID**: Researcher identification and profile data

## Getting Started

1. **Authentication**: Currently no authentication required (development phase)
2. **Rate Limiting**: No rate limits enforced (will be implemented in production)
3. **CORS**: Configured for development environment

## Support and Development

- **Repository**: [GitHub Repository URL]
- **Issues**: [GitHub Issues URL]
- **Documentation**: [Full Documentation URL]
- **Monitoring Dashboard**: Available at http://localhost:3000 (Grafana)

## Version History

- **v1.0.0**: Initial release with core multi-agent functionality
""",
        routes=app.routes,
    )
    
    # Add custom server information
    openapi_schema["servers"] = [
        {
            "url": "http://127.0.0.1:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.research-system.local",
            "description": "Production server"
        }
    ]
    
    # Add custom tags for organization
    openapi_schema["tags"] = [
        {
            "name": "Health & Monitoring",
            "description": "Health checks, metrics, and system status endpoints"
        },
        {
            "name": "Multi-Agent Pipeline",
            "description": "Core multi-agent research opportunity processing endpoints"
        },
        {
            "name": "Data Ingestion",
            "description": "Endpoints for data collection from external sources"
        },
        {
            "name": "Matching & Analysis",
            "description": "Research opportunity matching and scoring endpoints"
        },
        {
            "name": "Notifications",
            "description": "Notification generation and delivery endpoints"
        },
        {
            "name": "Analytics & Reporting",
            "description": "System analytics and reporting endpoints"
        }
    ]
    
    # Add custom components
    openapi_schema["components"]["schemas"]["CorrelationHeader"] = {
        "type": "string",
        "description": "Optional correlation ID for request tracking",
        "example": "550e8400-e29b-41d4-a716-446655440000"
    }
    
    # Add security schemes (for future authentication)
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Bearer token authentication (Phase 4+)"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key authentication (Phase 4+)"
        }
    }
    
    # Add custom response examples
    for path_data in openapi_schema["paths"].values():
        for method_data in path_data.values():
            if isinstance(method_data, dict) and "responses" in method_data:
                responses = method_data["responses"]
                
                # Add correlation ID header to all responses
                for response_code, response_data in responses.items():
                    if "headers" not in response_data:
                        response_data["headers"] = {}
                    response_data["headers"]["X-Correlation-ID"] = {
                        "description": "Request correlation ID for tracing",
                        "schema": {"type": "string"}
                    }
                    response_data["headers"]["X-Process-Time"] = {
                        "description": "Request processing time in seconds",
                        "schema": {"type": "string"}
                    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# ============================================================================
# Documentation Enhancement Functions
# ============================================================================

def add_response_examples(app: FastAPI):
    """Add response examples to existing endpoints."""
    # This would be called after all routes are defined
    # to enhance them with examples
    pass

def setup_api_documentation(app: FastAPI):
    """Set up comprehensive API documentation."""
    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)
    
    # Add response examples
    add_response_examples(app)
    
    return app