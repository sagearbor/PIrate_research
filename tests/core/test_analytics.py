"""
Tests for the analytics engine module.

This module contains comprehensive tests for the analytics engine,
including system metrics calculation, caching functionality,
and recommendation effectiveness tracking.
"""

import json
import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock

from src.core.analytics import AnalyticsEngine, get_system_metrics, get_system_health, clear_analytics_cache


class TestAnalyticsEngine:
    """Test cases for the AnalyticsEngine class."""
    
    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def analytics_engine(self, temp_data_dir):
        """Create an AnalyticsEngine instance with temporary data directory."""
        return AnalyticsEngine(data_path=temp_data_dir)
    
    @pytest.fixture
    def sample_matches_data(self, temp_data_dir):
        """Create sample matches data for testing."""
        matches_data = [
            {
                "match_id": "match_001",
                "faculty_profile_id": "prof_001",
                "funding_opportunity_id": "funding_001",
                "match_score": {
                    "total_score": 0.85,
                    "research_alignment": 0.90,
                    "methodology_match": 0.80,
                    "career_stage_fit": 0.85,
                    "deadline_urgency": 0.75,
                    "budget_alignment": 0.88
                },
                "status": "pending",
                "created_date": datetime.now().isoformat(),
                "faculty_response": "interested"
            },
            {
                "match_id": "match_002",
                "faculty_profile_id": "prof_002",
                "funding_opportunity_id": "funding_002",
                "match_score": {
                    "total_score": 0.62,
                    "research_alignment": 0.65,
                    "methodology_match": 0.60,
                    "career_stage_fit": 0.70,
                    "deadline_urgency": 0.55,
                    "budget_alignment": 0.58
                },
                "status": "reviewed",
                "created_date": (datetime.now() - timedelta(days=3)).isoformat(),
                "faculty_response": None
            },
            {
                "match_id": "match_003",
                "faculty_profile_id": "prof_003",
                "funding_opportunity_id": "funding_003",
                "match_score": {
                    "total_score": 0.92,
                    "research_alignment": 0.95,
                    "methodology_match": 0.90,
                    "career_stage_fit": 0.88,
                    "deadline_urgency": 0.95,
                    "budget_alignment": 0.92
                },
                "status": "accepted",
                "created_date": (datetime.now() - timedelta(days=1)).isoformat(),
                "faculty_response": "very_interested"
            }
        ]
        
        # Write data to file
        file_path = Path(temp_data_dir) / "faculty_funding_matches_20250131_120000.json"
        with open(file_path, 'w') as f:
            json.dump(matches_data, f)
        
        return matches_data
    
    @pytest.fixture
    def sample_ideas_data(self, temp_data_dir):
        """Create sample research ideas data for testing."""
        ideas_data = [
            {
                "title": "AI-Driven Healthcare Analytics",
                "variant_type": "innovative",
                "methodology": ["computational", "experimental"],
                "innovation_level": 0.78,
                "feasibility_score": 0.85,
                "impact_potential": 0.90,
                "estimated_budget": 150000,
                "timeline_months": 24
            },
            {
                "title": "Sustainable Energy Solutions",
                "variant_type": "conservative",
                "methodology": ["experimental", "observational"],
                "innovation_level": 0.65,
                "feasibility_score": 0.92,
                "impact_potential": 0.75,
                "estimated_budget": 200000,
                "timeline_months": 36
            },
            {
                "title": "Quantum Computing Applications",
                "variant_type": "stretch",
                "methodology": ["theoretical", "computational"],
                "innovation_level": 0.95,
                "feasibility_score": 0.60,
                "impact_potential": 0.98,
                "estimated_budget": 500000,
                "timeline_months": 48
            }
        ]
        
        # Write data to file
        file_path = Path(temp_data_dir) / "research_ideas_20250131_120000.json"
        with open(file_path, 'w') as f:
            json.dump(ideas_data, f)
        
        return ideas_data
    
    @pytest.fixture
    def sample_collaborators_data(self, temp_data_dir):
        """Create sample collaborator suggestions data for testing."""
        collaborators_data = [
            {
                "faculty_profile_id": "collab_001",
                "name": "Dr. Jane Smith",
                "institution": "University of Science",
                "relevance_score": 0.88,
                "complementary_expertise": ["machine learning", "data analysis"],
                "shared_interests": ["artificial intelligence"]
            },
            {
                "faculty_profile_id": "collab_002",
                "name": "Dr. John Doe",
                "institution": "Tech Institute",
                "relevance_score": 0.75,
                "complementary_expertise": ["software engineering", "systems design"],
                "shared_interests": ["computer science"]
            }
        ]
        
        # Write data to file
        file_path = Path(temp_data_dir) / "collaborator_suggestions_20250131_120000.json"
        with open(file_path, 'w') as f:
            json.dump(collaborators_data, f)
        
        return collaborators_data
    
    @pytest.fixture
    def sample_notifications_data(self, temp_data_dir):
        """Create sample notifications data for testing."""
        notifications_data = [
            {
                "match_id": "match_001",
                "recipient_email": "prof1@university.edu",
                "sent": True,
                "created_date": datetime.now().isoformat()
            },
            {
                "match_id": "match_002",
                "recipient_email": "prof2@university.edu",
                "sent": True,
                "created_date": (datetime.now() - timedelta(days=1)).isoformat()
            },
            {
                "match_id": "match_003",
                "recipient_email": "prof3@university.edu",
                "sent": False,
                "created_date": (datetime.now() - timedelta(hours=2)).isoformat()
            }
        ]
        
        # Write data to file
        file_path = Path(temp_data_dir) / "notifications_20250131_120000.json"
        with open(file_path, 'w') as f:
            json.dump(notifications_data, f)
        
        return notifications_data
    
    @pytest.mark.asyncio
    async def test_get_system_overview(self, analytics_engine, sample_matches_data, 
                                     sample_ideas_data, sample_collaborators_data, 
                                     sample_notifications_data):
        """Test system overview generation."""
        overview = await analytics_engine.get_system_overview()
        
        # Check structure
        assert "overview" in overview
        assert "match_quality" in overview
        assert "system_health" in overview
        assert "timestamp" in overview
        
        # Check overview metrics
        overview_data = overview["overview"]
        assert overview_data["total_matches"] == 3
        assert overview_data["total_ideas"] == 3
        assert overview_data["total_collaborator_suggestions"] == 2
        assert overview_data["total_notifications"] == 3
        assert overview_data["recent_matches_7d"] == 3
        
        # Check match quality distribution
        match_quality = overview["match_quality"]
        assert match_quality["high"] == 2  # scores >= 0.8
        assert match_quality["medium"] == 1  # scores >= 0.6 and < 0.8
        assert match_quality["low"] == 0  # scores < 0.6
        
        # Check system health
        system_health = overview["system_health"]
        assert system_health["status"] == "healthy"
        assert "last_data_update" in system_health
        assert "data_freshness_hours" in system_health
    
    @pytest.mark.asyncio
    async def test_get_agent_performance(self, analytics_engine, sample_matches_data,
                                       sample_ideas_data, sample_collaborators_data,
                                       sample_notifications_data):
        """Test agent performance metrics generation."""
        performance = await analytics_engine.get_agent_performance()
        
        # Check structure
        assert "matcher_agent" in performance
        assert "idea_agent" in performance
        assert "collaborator_agent" in performance
        assert "notification_agent" in performance
        assert "timestamp" in performance
        
        # Check matcher agent performance
        matcher = performance["matcher_agent"]
        assert matcher["total_matches"] == 3
        assert abs(matcher["avg_score"] - 0.797) < 0.01  # (0.85 + 0.62 + 0.92) / 3
        assert matcher["high_quality_matches"] == 2
        
        # Check ideas agent performance
        ideas = performance["idea_agent"]
        assert ideas["total_ideas"] == 3
        assert ideas["variant_distribution"]["conservative"] == 1
        assert ideas["variant_distribution"]["innovative"] == 1
        assert ideas["variant_distribution"]["stretch"] == 1
        assert abs(ideas["avg_innovation_score"] - 0.793) < 0.01  # (0.78 + 0.65 + 0.95) / 3
        
        # Check collaborator agent performance
        collaborator = performance["collaborator_agent"]
        assert collaborator["total_suggestions"] == 2
        assert abs(collaborator["avg_relevance_score"] - 0.815) < 0.01  # (0.88 + 0.75) / 2
        assert collaborator["high_relevance_suggestions"] == 1  # Only one >= 0.8
        
        # Check notification agent performance
        notification = performance["notification_agent"]
        assert notification["total_notifications"] == 3
        assert notification["sent_notifications"] == 2
        assert abs(notification["success_rate"] - 0.667) < 0.01  # 2/3
    
    @pytest.mark.asyncio
    async def test_get_recommendation_effectiveness(self, analytics_engine, sample_matches_data):
        """Test recommendation effectiveness tracking."""
        effectiveness = await analytics_engine.get_recommendation_effectiveness()
        
        # Check structure
        assert "effectiveness_by_period" in effectiveness
        assert "trends" in effectiveness
        assert "timestamp" in effectiveness
        
        # Check periods
        periods = effectiveness["effectiveness_by_period"]
        assert "last_7_days" in periods
        assert "last_30_days" in periods
        assert "last_90_days" in periods
        
        # Check 7-day metrics (all matches are within 7 days)
        last_7_days = periods["last_7_days"]
        assert last_7_days["total_matches"] == 3
        assert abs(last_7_days["avg_score"] - 0.797) < 0.01
        assert last_7_days["score_distribution"]["high"] == 2
        assert last_7_days["score_distribution"]["medium"] == 1
        assert last_7_days["score_distribution"]["low"] == 0
        assert abs(last_7_days["response_rate"] - 0.667) < 0.01  # 2 responses out of 3
        
        # Check trends
        trends = effectiveness["trends"]
        assert "match_volume_trend" in trends
        assert "quality_trend" in trends
        assert "response_trend" in trends
    
    @pytest.mark.asyncio
    async def test_get_research_insights(self, analytics_engine, sample_matches_data, sample_ideas_data):
        """Test research insights generation."""
        insights = await analytics_engine.get_research_insights()
        
        # Check structure
        assert "research_trends" in insights
        assert "idea_quality_metrics" in insights
        assert "insights" in insights
        assert "timestamp" in insights
        
        # Check idea quality metrics
        quality = insights["idea_quality_metrics"]
        assert quality["total_ideas"] == 3
        assert abs(quality["avg_innovation_level"] - 0.793) < 0.01
        assert abs(quality["avg_feasibility_score"] - 0.790) < 0.01
        assert abs(quality["avg_impact_potential"] - 0.877) < 0.01
        
        # Check research trends
        trends = insights["research_trends"]
        assert "top_research_areas" in trends
        assert "top_methodologies" in trends
        assert "career_stage_distribution" in trends
        
        # Check top methodologies (should include computational, experimental, etc.)
        top_methods = dict(trends["top_methodologies"])
        assert "computational" in top_methods
        assert "experimental" in top_methods
        assert "theoretical" in top_methods
        assert "observational" in top_methods
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, analytics_engine, sample_matches_data):
        """Test analytics caching functionality."""
        # First call should generate fresh data
        metrics1 = await analytics_engine.get_cached_metrics()
        assert analytics_engine._metrics_cache is not None
        assert analytics_engine._cache_timestamp is not None
        
        # Second call should return cached data
        metrics2 = await analytics_engine.get_cached_metrics()
        assert metrics1["generated_at"] == metrics2["generated_at"]
        
        # Clear cache and verify it's cleared
        analytics_engine.clear_cache()
        assert analytics_engine._metrics_cache is None
        assert analytics_engine._cache_timestamp is None
        
        # Next call should generate fresh data
        metrics3 = await analytics_engine.get_cached_metrics()
        assert metrics1["generated_at"] != metrics3["generated_at"]
    
    @pytest.mark.asyncio
    async def test_empty_data_handling(self, analytics_engine):
        """Test handling of empty data files."""
        overview = await analytics_engine.get_system_overview()
        
        # Should handle empty data gracefully
        assert overview["overview"]["total_matches"] == 0
        assert overview["overview"]["total_ideas"] == 0
        assert overview["overview"]["total_collaborator_suggestions"] == 0
        assert overview["overview"]["total_notifications"] == 0
        assert overview["match_quality"]["high"] == 0
        assert overview["match_quality"]["medium"] == 0
        assert overview["match_quality"]["low"] == 0
        
        # System health should indicate no data
        assert overview["system_health"]["status"] == "healthy"  # Default when no data
        assert overview["system_health"]["last_data_update"] is None
    
    @pytest.mark.asyncio
    async def test_invalid_data_handling(self, analytics_engine, temp_data_dir):
        """Test handling of invalid/corrupted data files."""
        # Create a file with invalid JSON
        invalid_file = Path(temp_data_dir) / "faculty_funding_matches_invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("invalid json content {")
        
        # Should handle invalid data gracefully
        overview = await analytics_engine.get_system_overview()
        assert "error" not in overview  # Should not crash
        assert overview["overview"]["total_matches"] == 0
    
    def test_cache_validity_check(self, analytics_engine):
        """Test cache validity checking."""
        # No cache initially
        assert not analytics_engine._is_cache_valid()
        
        # Set cache with current timestamp
        analytics_engine._metrics_cache = {"test": "data"}
        analytics_engine._cache_timestamp = datetime.now()
        assert analytics_engine._is_cache_valid()
        
        # Set cache with old timestamp
        analytics_engine._cache_timestamp = datetime.now() - timedelta(minutes=20)
        assert not analytics_engine._is_cache_valid()
    
    @pytest.mark.asyncio
    async def test_load_processed_data_edge_cases(self, analytics_engine, temp_data_dir):
        """Test edge cases in data loading."""
        # Test with single dict instead of list
        single_match = {
            "match_id": "single_match",
            "match_score": {"total_score": 0.8},
            "created_date": datetime.now().isoformat()
        }
        
        file_path = Path(temp_data_dir) / "faculty_funding_matches_single.json"
        with open(file_path, 'w') as f:
            json.dump(single_match, f)
        
        data = analytics_engine._load_processed_data("faculty_funding_matches_*.json")
        assert len(data) == 1
        assert data[0]["match_id"] == "single_match"


class TestAnalyticsGlobalFunctions:
    """Test cases for global analytics functions."""
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self):
        """Test the global get_system_metrics function."""
        with patch('src.core.analytics.analytics_engine') as mock_engine:
            mock_engine.get_cached_metrics.return_value = {"test": "metrics"}
            
            result = await get_system_metrics()
            
            mock_engine.get_cached_metrics.assert_called_once()
            assert result == {"test": "metrics"}
    
    @pytest.mark.asyncio
    async def test_get_system_health(self):
        """Test the global get_system_health function."""
        with patch('src.core.analytics.analytics_engine') as mock_engine:
            mock_engine.get_system_overview.return_value = {
                "system_health": {"status": "healthy", "data_freshness_hours": 1.5}
            }
            
            result = await get_system_health()
            
            mock_engine.get_system_overview.assert_called_once()
            assert result == {"status": "healthy", "data_freshness_hours": 1.5}
    
    @pytest.mark.asyncio
    async def test_get_system_health_error_handling(self):
        """Test error handling in get_system_health."""
        with patch('src.core.analytics.analytics_engine') as mock_engine:
            mock_engine.get_system_overview.return_value = {"error": "test error"}
            
            result = await get_system_health()
            
            assert result == {"status": "unknown"}
    
    def test_clear_analytics_cache(self):
        """Test the global cache clearing function."""
        with patch('src.core.analytics.analytics_engine') as mock_engine:
            clear_analytics_cache()
            mock_engine.clear_cache.assert_called_once()


class TestAnalyticsIntegration:
    """Integration tests for analytics functionality."""
    
    @pytest.fixture
    def mock_real_data(self, tmp_path):
        """Create realistic mock data for integration testing."""
        data_dir = tmp_path / "processed"
        data_dir.mkdir()
        
        # Load the actual mock data from test files
        test_data_dir = Path(__file__).parent.parent / "mock_data"
        
        # Copy system metrics if it exists
        system_metrics_file = test_data_dir / "system_metrics.json"
        if system_metrics_file.exists():
            with open(system_metrics_file) as f:
                system_data = json.load(f)
            
            # Extract data for individual files
            matches_data = []
            for i in range(system_data["system_overview"]["overview"]["total_matches"]):
                matches_data.append({
                    "match_id": f"match_{i:03d}",
                    "faculty_profile_id": f"prof_{i:03d}",
                    "funding_opportunity_id": f"funding_{i:03d}",
                    "match_score": {
                        "total_score": 0.7 + (i % 3) * 0.1,
                        "research_alignment": 0.8,
                        "methodology_match": 0.75,
                        "career_stage_fit": 0.85,
                        "deadline_urgency": 0.6,
                        "budget_alignment": 0.7
                    },
                    "status": "pending",
                    "created_date": (datetime.now() - timedelta(hours=i)).isoformat(),
                    "faculty_response": "interested" if i % 3 == 0 else None
                })
            
            # Write matches file
            matches_file = data_dir / "faculty_funding_matches_20250131_120000.json"
            with open(matches_file, 'w') as f:
                json.dump(matches_data, f)
        
        return str(data_dir)
    
    @pytest.mark.asyncio
    async def test_full_analytics_pipeline(self, mock_real_data):
        """Test complete analytics pipeline with realistic data."""
        engine = AnalyticsEngine(data_path=mock_real_data)
        
        # Test all major functions
        overview = await engine.get_system_overview()
        performance = await engine.get_agent_performance()
        effectiveness = await engine.get_recommendation_effectiveness()
        insights = await engine.get_research_insights()
        cached_metrics = await engine.get_cached_metrics()
        
        # Verify structure and data integrity
        assert "overview" in overview
        assert "matcher_agent" in performance
        assert "effectiveness_by_period" in effectiveness
        assert "research_trends" in insights
        
        # Verify cached metrics contain all components
        assert "system_overview" in cached_metrics
        assert "agent_performance" in cached_metrics
        assert "recommendation_effectiveness" in cached_metrics
        assert "research_insights" in cached_metrics
        assert "generated_at" in cached_metrics
    
    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(self, tmp_path):
        """Test analytics performance with a larger dataset."""
        data_dir = tmp_path / "processed"
        data_dir.mkdir()
        
        # Generate larger dataset
        large_matches = []
        for i in range(1000):
            large_matches.append({
                "match_id": f"match_{i:04d}",
                "faculty_profile_id": f"prof_{i:04d}",
                "funding_opportunity_id": f"funding_{i:04d}",
                "match_score": {
                    "total_score": 0.3 + (i % 100) / 100 * 0.7,  # Scores from 0.3 to 1.0
                    "research_alignment": 0.8,
                    "methodology_match": 0.75,
                    "career_stage_fit": 0.85,
                    "deadline_urgency": 0.6,
                    "budget_alignment": 0.7
                },
                "status": "pending",
                "created_date": (datetime.now() - timedelta(hours=i)).isoformat(),
                "faculty_response": "interested" if i % 5 == 0 else None
            })
        
        # Write data
        matches_file = data_dir / "faculty_funding_matches_large.json"
        with open(matches_file, 'w') as f:
            json.dump(large_matches, f)
        
        # Test performance
        engine = AnalyticsEngine(data_path=str(data_dir))
        
        import time
        start_time = time.time()
        cached_metrics = await engine.get_cached_metrics()
        end_time = time.time()
        
        # Should complete within reasonable time (< 5 seconds for 1000 records)
        assert end_time - start_time < 5.0
        
        # Verify correctness with large dataset
        assert cached_metrics["system_overview"]["overview"]["total_matches"] == 1000
        
        # Test caching improves performance
        start_time = time.time()
        cached_metrics2 = await engine.get_cached_metrics()
        end_time = time.time()
        
        # Cached call should be much faster (< 0.1 seconds)
        assert end_time - start_time < 0.1
        assert cached_metrics["generated_at"] == cached_metrics2["generated_at"]