"""
Tests for the admin dashboard module.

This module contains comprehensive tests for the admin dashboard,
including endpoint testing, data aggregation, system health checks,
and dashboard functionality.
"""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.dashboard.admin_dashboard import (
    dashboard_router,
    get_dashboard_metrics,
    dashboard_controls,
    export_dashboard_data,
    get_system_status,
    DashboardMetrics,
    SystemControlRequest
)


class TestAdminDashboard:
    """Test cases for the admin dashboard functionality."""
    
    @pytest.fixture
    def app(self):
        """Create a FastAPI app for testing."""
        app = FastAPI()
        app.include_router(dashboard_router)
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_system_metrics(self):
        """Mock system metrics data."""
        return {
            "system_overview": {
                "overview": {
                    "total_matches": 45,
                    "total_ideas": 135,
                    "total_collaborator_suggestions": 89,
                    "total_notifications": 42,
                    "recent_matches_7d": 12
                },
                "match_quality": {
                    "high": 18,
                    "medium": 22,
                    "low": 5
                },
                "system_health": {
                    "status": "healthy",
                    "last_data_update": "2025-01-31T10:30:00.000Z",
                    "data_freshness_hours": 2.5
                }
            },
            "agent_performance": {
                "matcher_agent": {
                    "total_matches": 45,
                    "avg_score": 0.756,
                    "high_quality_matches": 18
                },
                "idea_agent": {
                    "total_ideas": 135,
                    "variant_distribution": {
                        "conservative": 52,
                        "innovative": 48,
                        "stretch": 35
                    },
                    "avg_innovation_score": 0.672
                },
                "collaborator_agent": {
                    "total_suggestions": 89,
                    "avg_relevance_score": 0.821,
                    "high_relevance_suggestions": 67
                },
                "notification_agent": {
                    "total_notifications": 42,
                    "sent_notifications": 40,
                    "success_rate": 0.952
                }
            },
            "recommendation_effectiveness": {
                "effectiveness_by_period": {
                    "last_30_days": {
                        "total_matches": 35,
                        "avg_score": 0.745,
                        "score_distribution": {
                            "high": 15,
                            "medium": 16,
                            "low": 4
                        },
                        "response_rate": 0.314
                    }
                },
                "trends": {
                    "match_volume_trend": "increasing",
                    "quality_trend": "stable",
                    "response_trend": "stable"
                }
            },
            "research_insights": {
                "research_trends": {
                    "top_research_areas": [
                        ["machine learning", 15],
                        ["computational biology", 12]
                    ],
                    "top_methodologies": [
                        ["computational", 28],
                        ["experimental", 22]
                    ]
                },
                "idea_quality_metrics": {
                    "avg_innovation_level": 0.672,
                    "avg_feasibility_score": 0.789,
                    "avg_impact_potential": 0.734,
                    "total_ideas": 135
                },
                "insights": {
                    "most_active_research_area": "machine learning",
                    "most_common_methodology": "computational",
                    "dominant_career_stage": "assistant_professor"
                }
            },
            "generated_at": "2025-01-31T13:00:00.000Z"
        }
    
    @pytest.fixture
    def mock_system_health(self):
        """Mock system health data."""
        return {
            "status": "healthy",
            "last_data_update": "2025-01-31T10:30:00.000Z",
            "data_freshness_hours": 2.5
        }
    
    @pytest.fixture
    def mock_external_services(self):
        """Mock external services data."""
        return {
            "nih_reporter": {
                "service": "nih_reporter",
                "status": "healthy",
                "circuit_breaker": {
                    "state": "closed",
                    "total_calls": 156,
                    "successful_calls": 152,
                    "failed_calls": 4,
                    "success_rate": 0.974
                }
            },
            "google_scholar": {
                "service": "google_scholar",
                "status": "degraded",
                "circuit_breaker": {
                    "state": "half_open",
                    "total_calls": 89,
                    "successful_calls": 80,
                    "failed_calls": 9,
                    "success_rate": 0.899
                }
            }
        }
    
    @pytest.fixture
    def mock_security_status(self):
        """Mock security status data."""
        return {
            "summary": {
                "total_events_24h": 18,
                "high_risk_events": 1,
                "suspicious_ips": 2,
                "blocked_ips": 0,
                "active_patterns": 12
            },
            "event_types": {
                "suspicious_activity": 8,
                "rate_limit_exceeded": 6,
                "auth_failure": 3,
                "potential_attack": 1
            }
        }
    
    def test_dashboard_home_endpoint(self, client):
        """Test the dashboard home page endpoint."""
        response = client.get("/dashboard/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        
        # Check that the HTML contains key elements
        content = response.text
        assert "Faculty Research Opportunity Notifier" in content
        assert "Admin Dashboard" in content
        assert "System Controls" in content
        assert "dashboard-content" in content
        assert "refreshDashboard" in content  # JavaScript function
    
    @pytest.mark.asyncio
    async def test_get_dashboard_metrics_success(self, mock_system_metrics, 
                                               mock_system_health, mock_external_services,
                                               mock_security_status):
        """Test successful dashboard metrics retrieval."""
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics, \
             patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health, \
             patch('src.dashboard.admin_dashboard.get_external_services_status') as mock_get_external, \
             patch('src.dashboard.admin_dashboard.get_security_status') as mock_get_security:
            
            mock_get_metrics.return_value = mock_system_metrics
            mock_get_health.return_value = mock_system_health
            mock_get_external.return_value = mock_external_services
            mock_get_security.return_value = mock_security_status
            
            result = await get_dashboard_metrics()
            
            assert isinstance(result, DashboardMetrics)
            assert result.system_overview == mock_system_metrics["system_overview"]
            assert result.agent_performance == mock_system_metrics["agent_performance"]
            assert result.system_health == mock_system_health
            assert result.external_services == mock_external_services
            assert result.security_status == mock_security_status
            
            # Verify all mock functions were called
            mock_get_metrics.assert_called_once()
            mock_get_health.assert_called_once()
            mock_get_external.assert_called_once()
            mock_get_security.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_dashboard_metrics_error_handling(self):
        """Test error handling in dashboard metrics retrieval."""
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics:
            mock_get_metrics.side_effect = Exception("Test error")
            
            with pytest.raises(Exception):  # Should be HTTPException in FastAPI context
                await get_dashboard_metrics()
    
    def test_dashboard_metrics_endpoint(self, client, mock_system_metrics,
                                      mock_system_health, mock_external_services,
                                      mock_security_status):
        """Test the dashboard metrics endpoint."""
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics, \
             patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health, \
             patch('src.dashboard.admin_dashboard.get_external_services_status') as mock_get_external, \
             patch('src.dashboard.admin_dashboard.get_security_status') as mock_get_security:
            
            mock_get_metrics.return_value = mock_system_metrics
            mock_get_health.return_value = mock_system_health
            mock_get_external.return_value = mock_external_services
            mock_get_security.return_value = mock_security_status
            
            response = client.get("/dashboard/metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "system_overview" in data
            assert "agent_performance" in data
            assert "recommendation_effectiveness" in data
            assert "research_insights" in data
            assert "system_health" in data
            assert "external_services" in data
            assert "security_status" in data
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_dashboard_controls_clear_cache(self):
        """Test dashboard cache clearing control."""
        with patch('src.dashboard.admin_dashboard.clear_analytics_cache') as mock_clear_cache:
            request = SystemControlRequest(action="clear_cache")
            result = await dashboard_controls(request)
            
            mock_clear_cache.assert_called_once()
            assert result.status_code == 200
            
            response_data = json.loads(result.body)
            assert response_data["success"] is True
            assert "cache cleared" in response_data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_dashboard_controls_run_ingestion(self):
        """Test dashboard ingestion trigger control."""
        request = SystemControlRequest(action="run_ingestion")
        result = await dashboard_controls(request)
        
        assert result.status_code == 200
        
        response_data = json.loads(result.body)
        assert response_data["success"] is True
        assert "ingestion triggered" in response_data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_dashboard_controls_refresh_metrics(self):
        """Test dashboard metrics refresh control."""
        with patch('src.dashboard.admin_dashboard.clear_analytics_cache') as mock_clear_cache, \
             patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics:
            
            mock_get_metrics.return_value = {"test": "data"}
            
            request = SystemControlRequest(action="refresh_metrics")
            result = await dashboard_controls(request)
            
            mock_clear_cache.assert_called_once()
            mock_get_metrics.assert_called_once()
            
            assert result.status_code == 200
            response_data = json.loads(result.body)
            assert response_data["success"] is True
    
    @pytest.mark.asyncio
    async def test_dashboard_controls_unknown_action(self):
        """Test dashboard controls with unknown action."""
        request = SystemControlRequest(action="unknown_action")
        
        with pytest.raises(Exception):  # Should be HTTPException in FastAPI context
            await dashboard_controls(request)
    
    def test_dashboard_controls_endpoint(self, client):
        """Test the dashboard controls endpoint."""
        with patch('src.dashboard.admin_dashboard.clear_analytics_cache'):
            response = client.post(
                "/dashboard/controls",
                json={"action": "clear_cache"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_export_dashboard_data(self, mock_system_metrics, mock_system_health,
                                       mock_external_services):
        """Test dashboard data export functionality."""
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics, \
             patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health, \
             patch('src.dashboard.admin_dashboard.get_external_services_status') as mock_get_external:
            
            mock_get_metrics.return_value = mock_system_metrics
            mock_get_health.return_value = mock_system_health
            mock_get_external.return_value = mock_external_services
            
            result = await export_dashboard_data()
            
            assert result.status_code == 200
            export_data = json.loads(result.body)
            
            assert "export_info" in export_data
            assert "analytics" in export_data
            assert "system_health" in export_data
            assert "external_services" in export_data
            
            # Check export metadata
            export_info = export_data["export_info"]
            assert export_info["export_type"] == "dashboard_data"
            assert export_info["version"] == "1.0.0"
            assert "generated_at" in export_info
    
    def test_export_endpoint(self, client, mock_system_metrics, mock_system_health,
                           mock_external_services):
        """Test the export endpoint."""
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics, \
             patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health, \
             patch('src.dashboard.admin_dashboard.get_external_services_status') as mock_get_external:
            
            mock_get_metrics.return_value = mock_system_metrics
            mock_get_health.return_value = mock_system_health
            mock_get_external.return_value = mock_external_services
            
            response = client.get("/dashboard/export")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "export_info" in data
            assert "analytics" in data
            assert "system_health" in data
    
    @pytest.mark.asyncio
    async def test_get_system_status_healthy(self, mock_system_health):
        """Test system status when healthy."""
        with patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health:
            mock_get_health.return_value = mock_system_health
            
            result = await get_system_status()
            
            assert result.status_code == 200
            status_data = json.loads(result.body)
            
            assert status_data["status"] == "healthy"
            assert status_data["health"] == mock_system_health
            assert "timestamp" in status_data
    
    @pytest.mark.asyncio
    async def test_get_system_status_degraded(self):
        """Test system status when degraded."""
        degraded_health = {
            "status": "stale",
            "data_freshness_hours": 25
        }
        
        with patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health:
            mock_get_health.return_value = degraded_health
            
            result = await get_system_status()
            
            assert result.status_code == 200
            status_data = json.loads(result.body)
            
            assert status_data["status"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_get_system_status_unhealthy(self):
        """Test system status when unhealthy."""
        unhealthy_health = {
            "status": "healthy",
            "data_freshness_hours": 50  # > 48 hours
        }
        
        with patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health:
            mock_get_health.return_value = unhealthy_health
            
            result = await get_system_status()
            
            assert result.status_code == 200
            status_data = json.loads(result.body)
            
            assert status_data["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_get_system_status_error(self):
        """Test system status error handling."""
        with patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health:
            mock_get_health.side_effect = Exception("Test error")
            
            result = await get_system_status()
            
            assert result.status_code == 200
            status_data = json.loads(result.body)
            
            assert status_data["status"] == "error"
            assert "error" in status_data
    
    def test_system_status_endpoint(self, client, mock_system_health):
        """Test the system status endpoint."""
        with patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health:
            mock_get_health.return_value = mock_system_health
            
            response = client.get("/dashboard/system-status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert "health" in data
            assert "timestamp" in data


class TestDashboardModels:
    """Test cases for dashboard Pydantic models."""
    
    def test_dashboard_metrics_model(self):
        """Test DashboardMetrics model validation."""
        metrics_data = {
            "system_overview": {"test": "data"},
            "agent_performance": {"test": "data"},
            "recommendation_effectiveness": {"test": "data"},
            "research_insights": {"test": "data"},
            "system_health": {"status": "healthy"},
            "external_services": {"service1": {"status": "healthy"}},
            "security_status": {"summary": {"total_events_24h": 10}},
            "generated_at": "2025-01-31T13:00:00.000Z"
        }
        
        metrics = DashboardMetrics(**metrics_data)
        
        assert metrics.system_overview == {"test": "data"}
        assert metrics.agent_performance == {"test": "data"}
        assert metrics.system_health == {"status": "healthy"}
        assert metrics.generated_at == "2025-01-31T13:00:00.000Z"
    
    def test_system_control_request_model(self):
        """Test SystemControlRequest model validation."""
        # Test with just action
        request1 = SystemControlRequest(action="clear_cache")
        assert request1.action == "clear_cache"
        assert request1.parameters is None
        
        # Test with action and parameters
        request2 = SystemControlRequest(
            action="run_ingestion",
            parameters={"force": True, "sources": ["nih", "nsf"]}
        )
        assert request2.action == "run_ingestion"
        assert request2.parameters == {"force": True, "sources": ["nih", "nsf"]}
    
    def test_system_control_request_validation(self):
        """Test SystemControlRequest validation."""
        # Test that action is required
        with pytest.raises(ValueError):
            SystemControlRequest()


class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""
    
    def test_full_dashboard_workflow(self, client):
        """Test complete dashboard workflow."""
        mock_metrics = {
            "system_overview": {"overview": {"total_matches": 10}},
            "agent_performance": {"matcher_agent": {"total_matches": 10}},
            "recommendation_effectiveness": {"effectiveness_by_period": {}},
            "research_insights": {"research_trends": {}},
            "generated_at": "2025-01-31T13:00:00.000Z"
        }
        
        mock_health = {"status": "healthy", "data_freshness_hours": 1.0}
        mock_external = {"service1": {"status": "healthy"}}
        mock_security = {"summary": {"total_events_24h": 5}}
        
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics, \
             patch('src.dashboard.admin_dashboard.get_system_health') as mock_get_health, \
             patch('src.dashboard.admin_dashboard.get_external_services_status') as mock_get_external, \
             patch('src.dashboard.admin_dashboard.get_security_status') as mock_get_security, \
             patch('src.dashboard.admin_dashboard.clear_analytics_cache') as mock_clear_cache:
            
            mock_get_metrics.return_value = mock_metrics
            mock_get_health.return_value = mock_health
            mock_get_external.return_value = mock_external
            mock_get_security.return_value = mock_security
            
            # Test dashboard home
            response = client.get("/dashboard/")
            assert response.status_code == 200
            
            # Test metrics endpoint
            response = client.get("/dashboard/metrics")
            assert response.status_code == 200
            data = response.json()
            assert data["system_overview"]["overview"]["total_matches"] == 10
            
            # Test system status
            response = client.get("/dashboard/system-status")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["status"] == "healthy"
            
            # Test controls
            response = client.post("/dashboard/controls", json={"action": "clear_cache"})
            assert response.status_code == 200
            mock_clear_cache.assert_called_once()
            
            # Test export
            response = client.get("/dashboard/export")
            assert response.status_code == 200
            export_data = response.json()
            assert "export_info" in export_data
    
    def test_dashboard_error_scenarios(self, client):
        """Test dashboard behavior under error conditions."""
        # Test metrics endpoint with errors
        with patch('src.dashboard.admin_dashboard.get_system_metrics') as mock_get_metrics:
            mock_get_metrics.side_effect = Exception("Metrics error")
            
            response = client.get("/dashboard/metrics")
            assert response.status_code == 500
        
        # Test controls with invalid action
        response = client.post("/dashboard/controls", json={"action": "invalid_action"})
        assert response.status_code == 400
        
        # Test controls with missing action
        response = client.post("/dashboard/controls", json={})
        assert response.status_code == 422  # Validation error
    
    def test_dashboard_html_content_validation(self, client):
        """Test that dashboard HTML contains required elements."""
        response = client.get("/dashboard/")
        assert response.status_code == 200
        
        content = response.text
        
        # Check for essential HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<title>" in content
        assert "Faculty Research Opportunity Notifier" in content
        
        # Check for required CSS classes and IDs
        assert "dashboard-grid" in content
        assert "dashboard-content" in content
        assert "refresh-indicator" in content
        
        # Check for JavaScript functions
        assert "refreshDashboard" in content
        assert "clearCache" in content
        assert "runIngestion" in content
        
        # Check for control buttons
        assert "Refresh Data" in content
        assert "Clear Cache" in content
        assert "Run Data Ingestion" in content
        
        # Check for responsive design elements
        assert "viewport" in content
        assert "grid-template-columns" in content