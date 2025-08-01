"""
Tests for the FastAPI main application.

This module tests the core FastAPI endpoints including health checks.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from src.main import app

# Create test client
client = TestClient(app)


class TestMainApp:
    """Test cases for the main FastAPI application."""

    def test_root_endpoint(self):
        """Test the root endpoint returns correct information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Faculty Research Opportunity Notifier API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "active"
        assert "timestamp" in data
        
        # Verify timestamp format
        timestamp = data["timestamp"]
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_health_endpoint(self):
        """Test the health check endpoint returns 200 OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Faculty Research Opportunity Notifier"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data
        
        # Verify timestamp format
        timestamp = data["timestamp"]
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    def test_health_endpoint_response_format(self):
        """Test that health endpoint returns correct JSON structure."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        required_keys = ["status", "timestamp", "service", "version"]
        for key in required_keys:
            assert key in data

    def test_health_endpoint_multiple_calls(self):
        """Test that health endpoint works consistently across multiple calls."""
        for _ in range(3):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_openapi_docs_available(self):
        """Test that OpenAPI documentation endpoints are accessible."""
        # Test docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test redoc endpoint  
        response = client.get("/redoc")
        assert response.status_code == 200
        
        # Test OpenAPI JSON schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert openapi_data["info"]["title"] == "Faculty Research Opportunity Notifier"
        assert openapi_data["info"]["version"] == "1.0.0"

    def test_invalid_endpoint(self):
        """Test that invalid endpoints return 404."""
        response = client.get("/invalid-endpoint")
        assert response.status_code == 404