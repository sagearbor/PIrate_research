"""
Dashboard module for the Faculty Research Opportunity Notifier.

This module provides web-based administrative interfaces for system monitoring,
analytics, and configuration management.
"""

from .admin_dashboard import dashboard_router, setup_dashboard_routes

__all__ = [
    "dashboard_router",
    "setup_dashboard_routes"
]