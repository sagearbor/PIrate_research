"""
Analytics engine for the Faculty Research Opportunity Notifier.

This module provides comprehensive analytics and effectiveness tracking for the
research opportunity matching system, including:
- System performance metrics
- Match effectiveness analytics
- Agent performance monitoring
- Recommendation success tracking
"""

import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

from ..core.models import (
    FacultyFundingMatch, 
    SystemMetrics, 
    MatchStatus, 
    ProposalVariant,
    CareerStage,
    ResearchMethodology
)

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Central analytics engine for tracking system performance and effectiveness.
    """
    
    def __init__(self, data_path: str = "data/processed"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Cache for analytics data
        self._metrics_cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_minutes = 15  # Cache for 15 minutes
        
    def _is_cache_valid(self) -> bool:
        """Check if the current cache is still valid."""
        if not self._metrics_cache or not self._cache_timestamp:
            return False
        
        cache_age = datetime.now() - self._cache_timestamp
        return cache_age.total_seconds() < (self._cache_ttl_minutes * 60)
    
    def _load_processed_data(self, pattern: str) -> List[Dict[str, Any]]:
        """Load processed data files matching a pattern."""
        data_files = list(self.data_path.glob(pattern))
        all_data = []
        
        for file_path in data_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_data.extend(data)
                    elif isinstance(data, dict):
                        all_data.append(data)
            except Exception as e:
                logger.warning(f"Failed to load data from {file_path}: {e}")
        
        return all_data
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """
        Get comprehensive system overview metrics.
        
        Returns:
            Dict containing system overview data
        """
        try:
            # Load all processed data
            matches_data = self._load_processed_data("faculty_funding_matches_*.json")
            ideas_data = self._load_processed_data("research_ideas_*.json") 
            collaborators_data = self._load_processed_data("collaborator_suggestions_*.json")
            notifications_data = self._load_processed_data("notifications_*.json")
            
            # Calculate basic counts
            total_matches = len(matches_data)
            total_ideas = len(ideas_data)
            total_collaborator_suggestions = len(collaborators_data)
            total_notifications = len(notifications_data)
            
            # Calculate match quality distribution
            match_quality = {"high": 0, "medium": 0, "low": 0}
            for match in matches_data:
                score = match.get("match_score", {}).get("total_score", 0)
                if score >= 0.8:
                    match_quality["high"] += 1
                elif score >= 0.6:
                    match_quality["medium"] += 1
                else:
                    match_quality["low"] += 1
            
            # Calculate recent activity (last 7 days)
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_matches = [
                m for m in matches_data 
                if datetime.fromisoformat(m.get("created_date", "1970-01-01T00:00:00")) > seven_days_ago
            ]
            
            # System health metrics
            system_health = {
                "status": "healthy",
                "last_data_update": None,
                "data_freshness_hours": 0
            }
            
            if matches_data:
                # Find most recent match
                latest_match = max(
                    matches_data,
                    key=lambda x: datetime.fromisoformat(x.get("created_date", "1970-01-01T00:00:00"))
                )
                last_update = datetime.fromisoformat(latest_match["created_date"])
                system_health["last_data_update"] = last_update.isoformat()
                system_health["data_freshness_hours"] = (datetime.now() - last_update).total_seconds() / 3600
                
                # Mark as stale if no updates in 24 hours
                if system_health["data_freshness_hours"] > 24:
                    system_health["status"] = "stale"
            
            return {
                "overview": {
                    "total_matches": total_matches,
                    "total_ideas": total_ideas,
                    "total_collaborator_suggestions": total_collaborator_suggestions,
                    "total_notifications": total_notifications,
                    "recent_matches_7d": len(recent_matches)
                },
                "match_quality": match_quality,
                "system_health": system_health,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate system overview: {e}")
            return {
                "error": "Failed to generate system overview",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_agent_performance(self) -> Dict[str, Any]:
        """
        Get performance metrics for all agents.
        
        Returns:
            Dict containing agent performance data
        """
        try:
            # Load processed data
            matches_data = self._load_processed_data("faculty_funding_matches_*.json")
            ideas_data = self._load_processed_data("research_ideas_*.json")
            collaborators_data = self._load_processed_data("collaborator_suggestions_*.json")
            notifications_data = self._load_processed_data("notifications_*.json")
            
            # Calculate agent performance metrics
            matcher_performance = {
                "total_matches": len(matches_data),
                "avg_score": 0.0,
                "high_quality_matches": 0
            }
            
            if matches_data:
                scores = [m.get("match_score", {}).get("total_score", 0) for m in matches_data]
                matcher_performance["avg_score"] = sum(scores) / len(scores)
                matcher_performance["high_quality_matches"] = sum(1 for s in scores if s >= 0.8)
            
            # Ideas agent performance
            ideas_performance = {
                "total_ideas": len(ideas_data),
                "variant_distribution": {"conservative": 0, "innovative": 0, "stretch": 0},
                "avg_innovation_score": 0.0
            }
            
            innovation_scores = []
            for idea in ideas_data:
                variant = idea.get("variant_type", "conservative")
                ideas_performance["variant_distribution"][variant] += 1
                
                innovation_score = idea.get("innovation_level", 0)
                if innovation_score:
                    innovation_scores.append(innovation_score)
            
            if innovation_scores:
                ideas_performance["avg_innovation_score"] = sum(innovation_scores) / len(innovation_scores)
            
            # Collaborator agent performance
            collaborator_performance = {
                "total_suggestions": len(collaborators_data),
                "avg_relevance_score": 0.0,
                "high_relevance_suggestions": 0
            }
            
            if collaborators_data:
                relevance_scores = [c.get("relevance_score", 0) for c in collaborators_data]
                collaborator_performance["avg_relevance_score"] = sum(relevance_scores) / len(relevance_scores)
                collaborator_performance["high_relevance_suggestions"] = sum(1 for s in relevance_scores if s >= 0.8)
            
            # Notification agent performance
            notification_performance = {
                "total_notifications": len(notifications_data),
                "sent_notifications": sum(1 for n in notifications_data if n.get("sent", False)),
                "success_rate": 0.0
            }
            
            if notifications_data:
                notification_performance["success_rate"] = (
                    notification_performance["sent_notifications"] / len(notifications_data)
                )
            
            return {
                "matcher_agent": matcher_performance,
                "idea_agent": ideas_performance,
                "collaborator_agent": collaborator_performance,
                "notification_agent": notification_performance,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate agent performance metrics: {e}")
            return {
                "error": "Failed to generate agent performance metrics",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_recommendation_effectiveness(self) -> Dict[str, Any]:
        """
        Track recommendation effectiveness and success rates.
        
        Returns:
            Dict containing recommendation effectiveness metrics
        """
        try:
            matches_data = self._load_processed_data("faculty_funding_matches_*.json")
            
            # Group matches by time periods
            now = datetime.now()
            periods = {
                "last_7_days": now - timedelta(days=7),
                "last_30_days": now - timedelta(days=30),
                "last_90_days": now - timedelta(days=90)
            }
            
            effectiveness_metrics = {}
            
            for period_name, cutoff_date in periods.items():
                period_matches = [
                    m for m in matches_data
                    if datetime.fromisoformat(m.get("created_date", "1970-01-01T00:00:00")) > cutoff_date
                ]
                
                if not period_matches:
                    effectiveness_metrics[period_name] = {
                        "total_matches": 0,
                        "avg_score": 0.0,
                        "score_distribution": {"high": 0, "medium": 0, "low": 0},
                        "response_rate": 0.0
                    }
                    continue
                
                # Calculate metrics for this period
                scores = [m.get("match_score", {}).get("total_score", 0) for m in period_matches]
                avg_score = sum(scores) / len(scores) if scores else 0.0
                
                score_distribution = {"high": 0, "medium": 0, "low": 0}
                for score in scores:
                    if score >= 0.8:
                        score_distribution["high"] += 1
                    elif score >= 0.6:
                        score_distribution["medium"] += 1
                    else:
                        score_distribution["low"] += 1
                
                # Calculate response rate (matches with faculty_response)
                responses = sum(1 for m in period_matches if m.get("faculty_response"))
                response_rate = responses / len(period_matches) if period_matches else 0.0
                
                effectiveness_metrics[period_name] = {
                    "total_matches": len(period_matches),
                    "avg_score": avg_score,
                    "score_distribution": score_distribution,
                    "response_rate": response_rate
                }
            
            # Calculate trend analysis
            trends = {
                "match_volume_trend": "stable",
                "quality_trend": "stable",
                "response_trend": "stable"
            }
            
            # Simple trend analysis comparing last 30 days to previous 30 days
            if len(matches_data) > 0:
                last_30 = effectiveness_metrics["last_30_days"]["total_matches"]
                previous_30_start = now - timedelta(days=60)
                previous_30_end = now - timedelta(days=30)
                
                previous_30_matches = [
                    m for m in matches_data
                    if previous_30_start < datetime.fromisoformat(m.get("created_date", "1970-01-01T00:00:00")) <= previous_30_end
                ]
                
                if len(previous_30_matches) > 0:
                    previous_30_count = len(previous_30_matches)
                    
                    # Volume trend
                    if last_30 > previous_30_count * 1.1:
                        trends["match_volume_trend"] = "increasing"
                    elif last_30 < previous_30_count * 0.9:
                        trends["match_volume_trend"] = "decreasing"
            
            return {
                "effectiveness_by_period": effectiveness_metrics,
                "trends": trends,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate recommendation effectiveness: {e}")
            return {
                "error": "Failed to calculate recommendation effectiveness",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_research_insights(self) -> Dict[str, Any]:
        """
        Generate insights about research patterns and trends.
        
        Returns:
            Dict containing research insights
        """
        try:
            matches_data = self._load_processed_data("faculty_funding_matches_*.json")
            ideas_data = self._load_processed_data("research_ideas_*.json")
            
            # Analyze research area trends
            research_areas = defaultdict(int)
            methodologies = defaultdict(int)
            career_stages = defaultdict(int)
            
            for match in matches_data:
                # Extract research areas from match
                match_areas = match.get("research_areas", [])
                for area in match_areas:
                    research_areas[area.lower()] += 1
                
                # Extract career stage
                career_stage = match.get("career_stage", "unknown")
                career_stages[career_stage] += 1
            
            for idea in ideas_data: 
                # Extract methodologies
                idea_methods = idea.get("methodology", [])
                for method in idea_methods:
                    methodologies[method] += 1
            
            # Get top trends
            top_research_areas = sorted(research_areas.items(), key=lambda x: x[1], reverse=True)[:10]
            top_methodologies = sorted(methodologies.items(), key=lambda x: x[1], reverse=True)[:10]
            career_stage_distribution = dict(career_stages)
            
            # Calculate idea quality metrics
            idea_quality = {
                "avg_innovation_level": 0.0,
                "avg_feasibility_score": 0.0,
                "avg_impact_potential": 0.0,
                "total_ideas": len(ideas_data)
            }
            
            if ideas_data:
                innovation_scores = [i.get("innovation_level", 0) for i in ideas_data if i.get("innovation_level")]
                feasibility_scores = [i.get("feasibility_score", 0) for i in ideas_data if i.get("feasibility_score")]
                impact_scores = [i.get("impact_potential", 0) for i in ideas_data if i.get("impact_potential")]
                
                if innovation_scores:
                    idea_quality["avg_innovation_level"] = sum(innovation_scores) / len(innovation_scores)
                if feasibility_scores:
                    idea_quality["avg_feasibility_score"] = sum(feasibility_scores) / len(feasibility_scores)
                if impact_scores:
                    idea_quality["avg_impact_potential"] = sum(impact_scores) / len(impact_scores)
            
            return {
                "research_trends": {
                    "top_research_areas": top_research_areas,
                    "top_methodologies": top_methodologies,
                    "career_stage_distribution": career_stage_distribution
                },
                "idea_quality_metrics": idea_quality,
                "insights": {
                    "most_active_research_area": top_research_areas[0][0] if top_research_areas else "unknown",
                    "most_common_methodology": top_methodologies[0][0] if top_methodologies else "unknown",
                    "dominant_career_stage": max(career_stages.items(), key=lambda x: x[1])[0] if career_stages else "unknown"
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate research insights: {e}")
            return {
                "error": "Failed to generate research insights",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_cached_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive system metrics with caching for performance.
        
        Returns:
            Dict containing all analytics metrics
        """
        if self._is_cache_valid():
            logger.debug("Returning cached analytics metrics")
            return self._metrics_cache
        
        logger.info("Generating fresh analytics metrics")
        
        # Generate all metrics in parallel
        tasks = [
            self.get_system_overview(),
            self.get_agent_performance(),
            self.get_recommendation_effectiveness(),
            self.get_research_insights()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        combined_metrics = {
            "system_overview": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "agent_performance": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "recommendation_effectiveness": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "research_insights": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
            "generated_at": datetime.now().isoformat(),
            "cache_ttl_minutes": self._cache_ttl_minutes
        }
        
        # Update cache
        self._metrics_cache = combined_metrics
        self._cache_timestamp = datetime.now()
        
        return combined_metrics
    
    def clear_cache(self):
        """Clear the analytics metrics cache."""
        self._metrics_cache = None
        self._cache_timestamp = None
        logger.info("Analytics cache cleared")


# Global analytics engine instance
analytics_engine = AnalyticsEngine()


# Convenience functions
async def get_system_metrics() -> Dict[str, Any]:
    """Get comprehensive system metrics."""
    return await analytics_engine.get_cached_metrics()


async def get_system_health() -> Dict[str, Any]:
    """Get system health overview."""
    metrics = await analytics_engine.get_system_overview()
    return metrics.get("system_health", {"status": "unknown"})


def clear_analytics_cache():
    """Clear the analytics cache to force fresh data generation."""
    analytics_engine.clear_cache()