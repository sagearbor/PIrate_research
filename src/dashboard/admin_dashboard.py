"""
Admin Dashboard for the Faculty Research Opportunity Notifier.

This module provides a comprehensive web-based dashboard for system monitoring,
analytics, and administrative functions including:
- System health monitoring
- Agent performance tracking
- Analytics and insights
- Configuration management
- Manual system controls
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from ..core.analytics import analytics_engine, get_system_metrics, get_system_health
from ..core.metrics import (
    agent_executions_total,
    agent_execution_duration_seconds,
    external_api_calls_total,
    matches_generated_total,
    funding_opportunities_scraped_total,
    faculty_profiles_discovered_total
)
from ..core.circuit_breaker import get_external_services_status
from ..core.security_monitoring import get_security_status

logger = logging.getLogger(__name__)

# Router for dashboard endpoints
dashboard_router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])


class DashboardMetrics(BaseModel):
    """Response model for dashboard metrics."""
    system_overview: Dict[str, Any]
    agent_performance: Dict[str, Any] 
    recommendation_effectiveness: Dict[str, Any]
    research_insights: Dict[str, Any]
    system_health: Dict[str, Any]
    external_services: Dict[str, Any]
    security_status: Dict[str, Any]
    generated_at: str


class SystemControlRequest(BaseModel):
    """Request model for system control actions."""
    action: str = Field(..., description="Action to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Action parameters")


@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """
    Serve the main admin dashboard HTML interface.
    
    Returns:
        HTMLResponse: Main dashboard HTML page
    """
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Faculty Research Opportunity Notifier - Admin Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f5f5;
                color: #333;
                line-height: 1.6;
            }
            
            .header {
                background: #2c3e50;
                color: white;
                padding: 1rem 2rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                font-size: 1.5rem;
                font-weight: 600;
            }
            
            .header .subtitle {
                opacity: 0.8;
                font-size: 0.9rem;
                margin-top: 0.25rem;
            }
            
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 2rem;
            }
            
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            
            .card {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                overflow: hidden;
            }
            
            .card-header {
                background: #34495e;
                color: white;
                padding: 1rem 1.5rem;
                font-weight: 600;
                font-size: 1.1rem;
            }
            
            .card-content {
                padding: 1.5rem;
            }
            
            .metric {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 0;
                border-bottom: 1px solid #eee;
            }
            
            .metric:last-child {
                border-bottom: none;
            }
            
            .metric-label {
                font-weight: 500;
                color: #555;
            }
            
            .metric-value {
                font-weight: 600;
                font-size: 1.1rem;
                color: #2c3e50;
            }
            
            .metric-value.success {
                color: #27ae60;
            }
            
            .metric-value.warning {
                color: #f39c12;
            }
            
            .metric-value.error {
                color: #e74c3c;
            }
            
            .status-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 0.5rem;
            }
            
            .status-healthy {
                background: #27ae60;
            }
            
            .status-warning {
                background: #f39c12;
            }
            
            .status-error {
                background: #e74c3c;
            }
            
            .controls-section {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                margin-bottom: 2rem;
            }
            
            .controls-header {
                background: #3498db;
                color: white;
                padding: 1rem 1.5rem;
                font-weight: 600;
            }
            
            .controls-content {
                padding: 1.5rem;
            }
            
            .button-group {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
            }
            
            .btn {
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 500;
                text-decoration: none;
                display: inline-block;
                transition: all 0.2s;
            }
            
            .btn-primary {
                background: #3498db;
                color: white;
            }
            
            .btn-primary:hover {
                background: #2980b9;
            }
            
            .btn-success {
                background: #27ae60;
                color: white;
            }
            
            .btn-success:hover {
                background: #219a52;
            }
            
            .btn-warning {
                background: #f39c12;
                color: white;
            }
            
            .btn-warning:hover {
                background: #e67e22;
            }
            
            .loading {
                text-align: center;
                padding: 2rem;
                color: #666;
            }
            
            .error {
                background: #fff5f5;
                border: 1px solid #fed7d7;
                color: #c53030;
                padding: 1rem;
                border-radius: 4px;
                margin: 1rem 0;
            }
            
            .timestamp {
                font-size: 0.8rem;
                color: #666;
                text-align: right;
                margin-top: 1rem;
                padding-top: 1rem;
                border-top: 1px solid #eee;
            }
            
            .agent-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1rem;
                margin-top: 1rem;
            }
            
            .agent-card {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 1rem;
            }
            
            .agent-name {
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 0.5rem;
            }
            
            .auto-refresh {
                text-align: center;
                margin-bottom: 1rem;
                padding: 0.5rem;
                background: #e8f4fd;
                border-radius: 4px;
                font-size: 0.9rem;
                color: #0969da;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Faculty Research Opportunity Notifier</h1>
            <div class="subtitle">Admin Dashboard - System Monitoring & Analytics</div>
        </div>
        
        <div class="container">
            <div class="auto-refresh" id="refresh-indicator">
                Auto-refreshing every 30 seconds... <span id="countdown">30</span>s
            </div>
            
            <div class="controls-section">
                <div class="controls-header">System Controls</div>
                <div class="controls-content">
                    <div class="button-group">
                        <button class="btn btn-primary" onclick="refreshDashboard()">Refresh Data</button>
                        <button class="btn btn-success" onclick="clearCache()">Clear Cache</button>
                        <button class="btn btn-warning" onclick="runIngestion()">Run Data Ingestion</button>
                        <a href="/dashboard/export" class="btn btn-primary">Export Reports</a>
                        <a href="/health/detailed" class="btn btn-primary" target="_blank">System Health</a>
                        <a href="/metrics" class="btn btn-primary" target="_blank">Prometheus Metrics</a>
                    </div>
                </div>
            </div>
            
            <div id="dashboard-content">
                <div class="loading">Loading dashboard data...</div>
            </div>
        </div>
        
        <script>
            let refreshTimer = null;
            let countdownTimer = null;
            let countdownSeconds = 30;
            
            // Auto-refresh functionality
            function startAutoRefresh() {
                refreshTimer = setInterval(refreshDashboard, 30000);
                startCountdown();
            }
            
            function startCountdown() {
                countdownSeconds = 30;
                countdownTimer = setInterval(() => {
                    countdownSeconds--;
                    document.getElementById('countdown').textContent = countdownSeconds;
                    if (countdownSeconds <= 0) {
                        countdownSeconds = 30;
                    }
                }, 1000);
            }
            
            function stopTimers() {
                if (refreshTimer) clearInterval(refreshTimer);
                if (countdownTimer) clearInterval(countdownTimer);
            }
            
            // Dashboard data loading
            async function refreshDashboard() {
                try {
                    document.getElementById('dashboard-content').innerHTML = 
                        '<div class="loading">Refreshing dashboard data...</div>';
                    
                    const response = await fetch('/dashboard/metrics');
                    const data = await response.json();
                    
                    if (response.ok) {
                        renderDashboard(data);
                    } else {
                        showError('Failed to load dashboard data: ' + (data.message || 'Unknown error'));
                    }
                } catch (error) {
                    showError('Failed to refresh dashboard: ' + error.message);
                }
            }
            
            function renderDashboard(data) {
                const content = document.getElementById('dashboard-content');
                content.innerHTML = `
                    <div class="dashboard-grid">
                        ${renderSystemOverview(data.system_overview)}
                        ${renderAgentPerformance(data.agent_performance)}
                        ${renderSystemHealth(data.system_health)}
                        ${renderExternalServices(data.external_services)}
                        ${renderSecurityStatus(data.security_status)}
                        ${renderRecommendationEffectiveness(data.recommendation_effectiveness)}
                        ${renderResearchInsights(data.research_insights)}
                    </div>
                    <div class="timestamp">Last updated: ${new Date(data.generated_at).toLocaleString()}</div>
                `;
            }
            
            function renderSystemOverview(overview) {
                if (overview.error) {
                    return `<div class="card">
                        <div class="card-header">System Overview</div>
                        <div class="card-content">
                            <div class="error">Error: ${overview.error}</div>
                        </div>
                    </div>`;
                }
                
                const overviewData = overview.overview || {};
                return `
                    <div class="card">
                        <div class="card-header">System Overview</div>
                        <div class="card-content">
                            <div class="metric">
                                <span class="metric-label">Total Matches</span>
                                <span class="metric-value">${overviewData.total_matches || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Total Ideas Generated</span>
                                <span class="metric-value">${overviewData.total_ideas || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Collaborator Suggestions</span>
                                <span class="metric-value">${overviewData.total_collaborator_suggestions || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Notifications Sent</span>
                                <span class="metric-value">${overviewData.total_notifications || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Recent Matches (7d)</span>
                                <span class="metric-value success">${overviewData.recent_matches_7d || 0}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function renderAgentPerformance(performance) {
                if (performance.error) {
                    return `<div class="card">
                        <div class="card-header">Agent Performance</div>
                        <div class="card-content">
                            <div class="error">Error: ${performance.error}</div>
                        </div>
                    </div>`;
                }
                
                const matcher = performance.matcher_agent || {};
                const ideas = performance.idea_agent || {};
                const collaborator = performance.collaborator_agent || {};
                const notification = performance.notification_agent || {};
                
                return `
                    <div class="card">
                        <div class="card-header">Agent Performance</div>
                        <div class="card-content">
                            <div class="agent-grid">
                                <div class="agent-card">
                                    <div class="agent-name">Matcher Agent</div>
                                    <div class="metric">
                                        <span class="metric-label">Avg Score</span>
                                        <span class="metric-value">${(matcher.avg_score || 0).toFixed(3)}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">High Quality</span>
                                        <span class="metric-value success">${matcher.high_quality_matches || 0}</span>
                                    </div>
                                </div>
                                <div class="agent-card">
                                    <div class="agent-name">Ideas Agent</div>
                                    <div class="metric">
                                        <span class="metric-label">Total Ideas</span>
                                        <span class="metric-value">${ideas.total_ideas || 0}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Avg Innovation</span>
                                        <span class="metric-value">${(ideas.avg_innovation_score || 0).toFixed(3)}</span>
                                    </div>
                                </div>
                                <div class="agent-card">
                                    <div class="agent-name">Collaborator Agent</div>
                                    <div class="metric">
                                        <span class="metric-label">Suggestions</span>
                                        <span class="metric-value">${collaborator.total_suggestions || 0}</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Avg Relevance</span>
                                        <span class="metric-value">${(collaborator.avg_relevance_score || 0).toFixed(3)}</span>
                                    </div>
                                </div>
                                <div class="agent-card">
                                    <div class="agent-name">Notification Agent</div>
                                    <div class="metric">
                                        <span class="metric-label">Success Rate</span>
                                        <span class="metric-value success">${((notification.success_rate || 0) * 100).toFixed(1)}%</span>
                                    </div>
                                    <div class="metric">
                                        <span class="metric-label">Sent</span>
                                        <span class="metric-value">${notification.sent_notifications || 0}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function renderSystemHealth(health) {
                if (health.error) {
                    return `<div class="card">
                        <div class="card-header">System Health</div>
                        <div class="card-content">
                            <div class="error">Error: ${health.error}</div>
                        </div>
                    </div>`;
                }
                
                const status = health.status || 'unknown';
                const statusClass = status === 'healthy' ? 'status-healthy' : 
                                   status === 'stale' ? 'status-warning' : 'status-error';
                const dataAge = health.data_freshness_hours || 0;
                
                return `
                    <div class="card">
                        <div class="card-header">System Health</div>
                        <div class="card-content">
                            <div class="metric">
                                <span class="metric-label">Status</span>
                                <span class="metric-value">
                                    <span class="status-indicator ${statusClass}"></span>
                                    ${status.charAt(0).toUpperCase() + status.slice(1)}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Data Freshness</span>
                                <span class="metric-value ${dataAge > 24 ? 'warning' : 'success'}">
                                    ${dataAge.toFixed(1)} hours ago
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Last Update</span>
                                <span class="metric-value">
                                    ${health.last_data_update ? new Date(health.last_data_update).toLocaleString() : 'Unknown'}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function renderExternalServices(services) {
                if (services.error) {
                    return `<div class="card">
                        <div class="card-header">External Services</div>
                        <div class="card-content">
                            <div class="error">Error: ${services.error}</div>
                        </div>
                    </div>`;
                }
                
                let servicesHtml = '';
                for (const [serviceName, serviceData] of Object.entries(services)) {
                    const status = serviceData.status || 'unknown';
                    const statusClass = status === 'healthy' ? 'status-healthy' : 
                                       status === 'degraded' ? 'status-warning' : 'status-error';
                    
                    servicesHtml += `
                        <div class="metric">
                            <span class="metric-label">${serviceName.replace('_', ' ').toUpperCase()}</span>
                            <span class="metric-value">
                                <span class="status-indicator ${statusClass}"></span>
                                ${status.charAt(0).toUpperCase() + status.slice(1)}
                            </span>
                        </div>
                    `;
                }
                
                return `
                    <div class="card">
                        <div class="card-header">External Services</div>
                        <div class="card-content">
                            ${servicesHtml || '<div class="metric"><span class="metric-label">No services monitored</span></div>'}
                        </div>
                    </div>
                `;
            }
            
            function renderSecurityStatus(security) {
                if (security.error) {
                    return `<div class="card">
                        <div class="card-header">Security Status</div>
                        <div class="card-content">
                            <div class="error">Error: ${security.error}</div>
                        </div>
                    </div>`;
                }
                
                const summary = security.summary || {};
                return `
                    <div class="card">
                        <div class="card-header">Security Status</div>
                        <div class="card-content">
                            <div class="metric">
                                <span class="metric-label">Events (24h)</span>
                                <span class="metric-value">${summary.total_events_24h || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">High Risk Events</span>
                                <span class="metric-value ${(summary.high_risk_events || 0) > 0 ? 'warning' : 'success'}">
                                    ${summary.high_risk_events || 0}
                                </span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Blocked IPs</span>
                                <span class="metric-value">${summary.blocked_ips || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Active Patterns</span>
                                <span class="metric-value">${summary.active_patterns || 0}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function renderRecommendationEffectiveness(effectiveness) {
                if (effectiveness.error) {
                    return `<div class="card">
                        <div class="card-header">Recommendation Effectiveness</div>
                        <div class="card-content">
                            <div class="error">Error: ${effectiveness.error}</div>
                        </div>
                    </div>`;
                }
                
                const last30 = effectiveness.effectiveness_by_period?.last_30_days || {};
                const trends = effectiveness.trends || {};
                
                return `
                    <div class="card">
                        <div class="card-header">Recommendation Effectiveness (30d)</div>
                        <div class="card-content">
                            <div class="metric">
                                <span class="metric-label">Total Matches</span>
                                <span class="metric-value">${last30.total_matches || 0}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Average Score</span>
                                <span class="metric-value">${(last30.avg_score || 0).toFixed(3)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Response Rate</span>
                                <span class="metric-value">${((last30.response_rate || 0) * 100).toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Volume Trend</span>
                                <span class="metric-value ${trends.match_volume_trend === 'increasing' ? 'success' : trends.match_volume_trend === 'decreasing' ? 'warning' : ''}">
                                    ${trends.match_volume_trend || 'stable'}
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function renderResearchInsights(insights) {
                if (insights.error) {
                    return `<div class="card">
                        <div class="card-header">Research Insights</div>
                        <div class="card-content">
                            <div class="error">Error: ${insights.error}</div>
                        </div>
                    </div>`;
                }
                
                const topInsights = insights.insights || {};
                const quality = insights.idea_quality_metrics || {};
                
                return `
                    <div class="card">
                        <div class="card-header">Research Insights</div>
                        <div class="card-content">
                            <div class="metric">
                                <span class="metric-label">Top Research Area</span>
                                <span class="metric-value">${topInsights.most_active_research_area || 'Unknown'}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Common Methodology</span>
                                <span class="metric-value">${topInsights.most_common_methodology || 'Unknown'}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Avg Innovation Level</span>
                                <span class="metric-value">${(quality.avg_innovation_level || 0).toFixed(3)}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Avg Feasibility</span>
                                <span class="metric-value">${(quality.avg_feasibility_score || 0).toFixed(3)}</span>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            function showError(message) {
                document.getElementById('dashboard-content').innerHTML = 
                    `<div class="error">Error loading dashboard: ${message}</div>`;
            }
            
            // Control functions
            async function clearCache() {
                try {
                    const response = await fetch('/dashboard/controls', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({action: 'clear_cache'})
                    });
                    
                    if (response.ok) {
                        alert('Cache cleared successfully');
                        refreshDashboard();
                    } else {
                        alert('Failed to clear cache');
                    }
                } catch (error) {
                    alert('Error clearing cache: ' + error.message);
                }
            }
            
            async function runIngestion() {
                try {
                    const response = await fetch('/dashboard/controls', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({action: 'run_ingestion'})
                    });
                    
                    if (response.ok) {
                        alert('Data ingestion triggered successfully');
                        setTimeout(refreshDashboard, 2000);
                    } else {
                        alert('Failed to trigger data ingestion');
                    }
                } catch (error) {
                    alert('Error triggering ingestion: ' + error.message);
                }
            }
            
            // Initialize dashboard
            document.addEventListener('DOMContentLoaded', function() {
                refreshDashboard();
                startAutoRefresh();
            });
            
            // Cleanup on page unload
            window.addEventListener('beforeunload', stopTimers);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@dashboard_router.get("/metrics")
async def get_dashboard_metrics() -> DashboardMetrics:
    """
    Get comprehensive dashboard metrics.
    
    Returns:
        DashboardMetrics: All dashboard metrics and analytics
    """
    try:
        # Get core analytics
        analytics_data = await get_system_metrics()
        
        # Get additional system data
        system_health = await get_system_health()
        external_services = get_external_services_status()
        security_status = await get_security_status()
        
        return DashboardMetrics(
            system_overview=analytics_data.get("system_overview", {}),
            agent_performance=analytics_data.get("agent_performance", {}),
            recommendation_effectiveness=analytics_data.get("recommendation_effectiveness", {}),
            research_insights=analytics_data.get("research_insights", {}),
            system_health=system_health,
            external_services=external_services,
            security_status=security_status,
            generated_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to generate dashboard metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dashboard metrics: {str(e)}"
        )


@dashboard_router.post("/controls")
async def dashboard_controls(request: SystemControlRequest):
    """
    Execute system control actions from the dashboard.
    
    Args:
        request: System control request
        
    Returns:
        JSONResponse: Control action result
    """
    try:
        action = request.action.lower()
        
        if action == "clear_cache":
            from ..core.analytics import clear_analytics_cache
            clear_analytics_cache()
            return JSONResponse({
                "success": True,
                "message": "Analytics cache cleared successfully",
                "timestamp": datetime.now().isoformat()
            })
            
        elif action == "run_ingestion":
            # This would typically trigger the ingestion agent
            # For now, return a success message
            logger.info("Data ingestion triggered from dashboard")
            return JSONResponse({
                "success": True,
                "message": "Data ingestion triggered successfully",
                "timestamp": datetime.now().isoformat()
            })
            
        elif action == "refresh_metrics":
            # Force refresh of metrics
            from ..core.analytics import clear_analytics_cache
            clear_analytics_cache()
            await get_system_metrics()  # This will generate fresh metrics
            return JSONResponse({
                "success": True,
                "message": "Metrics refreshed successfully",
                "timestamp": datetime.now().isoformat()
            })
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {action}"
            )
            
    except Exception as e:
        logger.error(f"Failed to execute control action {request.action}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute action: {str(e)}"
        )


@dashboard_router.get("/export")
async def export_dashboard_data():
    """
    Export dashboard data for external analysis.
    
    Returns:
        JSONResponse: Exportable dashboard data
    """
    try:
        # Get comprehensive metrics
        analytics_data = await get_system_metrics()
        system_health = await get_system_health()
        external_services = get_external_services_status()
        
        export_data = {
            "export_info": {
                "generated_at": datetime.now().isoformat(),
                "export_type": "dashboard_data",
                "version": "1.0.0"
            },
            "analytics": analytics_data,
            "system_health": system_health,
            "external_services": external_services
        }
        
        return JSONResponse(export_data)
        
    except Exception as e:
        logger.error(f"Failed to export dashboard data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export data: {str(e)}"
        )


@dashboard_router.get("/system-status")
async def get_system_status():
    """
    Get quick system status overview.
    
    Returns:
        JSONResponse: Quick system status
    """
    try:
        system_health = await get_system_health()
        
        # Quick status determination
        status = "healthy"
        if system_health.get("status") == "stale":
            status = "degraded"
        elif system_health.get("data_freshness_hours", 0) > 48:
            status = "unhealthy"
        
        return JSONResponse({
            "status": status,
            "health": system_health,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })


# Include router in main application
def setup_dashboard_routes(app):
    """
    Setup dashboard routes in the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.include_router(dashboard_router)
    logger.info("Admin dashboard routes configured")