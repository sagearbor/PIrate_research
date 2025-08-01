"""
Tests for the Matcher Agent.

This module contains comprehensive tests for the MatcherAgent including
data loading, match generation, filtering, saving, and A2A communication.
"""

import pytest
import json
import tempfile
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.agents.matcher_agent import MatcherAgent
from src.core.models import (
    FacultyProfile, FundingOpportunity, FacultyFundingMatch, 
    MatchScore, MatchStatus, CareerStage, ResearchMethodology, Publication
)
from src.core.scoring_models import ScoringConfiguration, MatchingEngine
from src.core.a2a_protocols import A2AMessage, MessageType, AgentType


class TestMatcherAgentInitialization:
    """Test MatcherAgent initialization."""
    
    def test_default_initialization(self):
        """Test default initialization parameters."""
        agent = MatcherAgent()
        
        assert agent.min_score_threshold == 0.3
        assert agent.max_matches_per_faculty == 10
        assert isinstance(agent.scoring_config, ScoringConfiguration)
        assert isinstance(agent.matching_engine, MatchingEngine)
        assert agent.last_run is None
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        custom_config = ScoringConfiguration(min_deadline_days=60)
        
        agent = MatcherAgent(
            scoring_config=custom_config,
            min_score_threshold=0.5,
            max_matches_per_faculty=5
        )
        
        assert agent.min_score_threshold == 0.5
        assert agent.max_matches_per_faculty == 5
        assert agent.scoring_config.min_deadline_days == 60


class TestDataLoading:
    """Test data loading functionality."""
    
    @pytest.fixture
    def temp_faculty_file(self):
        """Create temporary faculty data file."""
        faculty_data = [
            {
                "name": "Dr. Test Faculty",
                "institution": "Test University",
                "department": "Computer Science",
                "career_stage": "assistant_professor",
                "research_interests": ["machine learning", "AI"],
                "methodologies": ["computational"],
                "publications": [
                    {
                        "title": "Test Publication",
                        "authors": ["Faculty, T."],
                        "year": 2023,
                        "keywords": ["AI", "ML"]
                    }
                ],
                "profile_id": "test_faculty_001",
                "h_index": 10,
                "total_citations": 200
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(faculty_data, f)
            temp_file = f.name
        
        yield temp_file
        os.unlink(temp_file)
    
    @pytest.fixture
    def temp_funding_file(self):
        """Create temporary funding data file."""
        funding_data = [
            {
                "title": "Test Grant",
                "agency": "Test Agency",
                "opportunity_id": "TEST-001",
                "deadline": (date.today() + timedelta(days=90)).isoformat(),
                "eligible_career_stages": ["assistant_professor"],
                "research_areas": ["artificial intelligence", "machine learning"],
                "preferred_methodologies": ["computational"],
                "description": "Test grant description",
                "url": "https://example.com/grant",
                "max_award_amount": "100000.00",
                "source": "TEST"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(funding_data, f)
            temp_file = f.name
        
        yield temp_file
        os.unlink(temp_file)
    
    def test_load_faculty_data_success(self, temp_faculty_file):
        """Test successful faculty data loading."""
        agent = MatcherAgent()
        
        profiles = agent.load_faculty_data(temp_faculty_file)
        
        assert len(profiles) == 1
        assert isinstance(profiles[0], FacultyProfile)
        assert profiles[0].name == "Dr. Test Faculty"
        assert profiles[0].career_stage == CareerStage.ASSISTANT_PROFESSOR
        assert ResearchMethodology.COMPUTATIONAL in profiles[0].methodologies
    
    def test_load_funding_data_success(self, temp_funding_file):
        """Test successful funding data loading."""
        agent = MatcherAgent()
        
        opportunities = agent.load_funding_data(temp_funding_file)
        
        assert len(opportunities) == 1
        assert isinstance(opportunities[0], FundingOpportunity)
        assert opportunities[0].title == "Test Grant"
        assert CareerStage.ASSISTANT_PROFESSOR in opportunities[0].eligible_career_stages
        assert ResearchMethodology.COMPUTATIONAL in opportunities[0].preferred_methodologies
    
    def test_load_faculty_data_file_not_found(self):
        """Test faculty data loading with non-existent file."""
        agent = MatcherAgent()
        
        profiles = agent.load_faculty_data("nonexistent_file.json")
        
        assert profiles == []
    
    def test_load_funding_data_file_not_found(self):
        """Test funding data loading with non-existent file."""
        agent = MatcherAgent()
        
        opportunities = agent.load_funding_data("nonexistent_file.json")
        
        assert opportunities == []
    
    def test_load_faculty_data_malformed_json(self):
        """Test faculty data loading with malformed JSON."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("{ invalid json }")
            temp_file = f.name
        
        try:
            agent = MatcherAgent()
            profiles = agent.load_faculty_data(temp_file)
            assert profiles == []
        finally:
            os.unlink(temp_file)
    
    def test_load_faculty_data_invalid_model(self):
        """Test faculty data loading with invalid model data."""
        invalid_data = [
            {
                "name": "Dr. Test",
                "career_stage": "invalid_stage",  # Invalid enum value
                "research_interests": [],  # Invalid - empty list
                "methodologies": ["invalid_method"]  # Invalid enum value
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(invalid_data, f)
            temp_file = f.name
        
        try:
            agent = MatcherAgent()
            profiles = agent.load_faculty_data(temp_file)
            assert profiles == []  # Should skip invalid entries
        finally:
            os.unlink(temp_file)


class TestMatchGeneration:
    """Test match generation functionality."""
    
    @pytest.fixture
    def sample_faculty(self):
        """Create sample faculty profiles."""
        return [
            FacultyProfile(
                name="Dr. AI Researcher",
                institution="AI University",
                department="Computer Science",
                career_stage=CareerStage.ASSISTANT_PROFESSOR,
                research_interests=["artificial intelligence", "machine learning"],
                methodologies=[ResearchMethodology.COMPUTATIONAL],
                profile_id="ai_faculty_001"
            ),
            FacultyProfile(
                name="Dr. Bio Researcher",
                institution="Bio University",
                department="Biology",
                career_stage=CareerStage.ASSOCIATE_PROFESSOR,
                research_interests=["biology", "genetics"],
                methodologies=[ResearchMethodology.EXPERIMENTAL],
                profile_id="bio_faculty_001"
            )
        ]
    
    @pytest.fixture
    def sample_funding(self):
        """Create sample funding opportunities."""
        return [
            FundingOpportunity(
                title="AI Research Grant",
                agency="NSF",
                opportunity_id="AI-GRANT-001",
                deadline=date.today() + timedelta(days=60),
                eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
                research_areas=["artificial intelligence", "computer science"],
                preferred_methodologies=[ResearchMethodology.COMPUTATIONAL],
                description="AI research funding",
                url="https://example.com/ai-grant",
                max_award_amount=Decimal('200000')
            ),
            FundingOpportunity(
                title="Biology Research Grant",
                agency="NIH",
                opportunity_id="BIO-GRANT-001",
                deadline=date.today() + timedelta(days=90),
                eligible_career_stages=[CareerStage.ASSOCIATE_PROFESSOR],
                research_areas=["biology", "life sciences"],
                preferred_methodologies=[ResearchMethodology.EXPERIMENTAL],
                description="Biology research funding",
                url="https://example.com/bio-grant",
                max_award_amount=Decimal('300000')
            )
        ]
    
    def test_generate_matches_success(self, sample_faculty, sample_funding):
        """Test successful match generation."""
        agent = MatcherAgent(min_score_threshold=0.1)  # Low threshold for testing
        
        matches = agent.generate_matches(sample_faculty, sample_funding)
        
        assert len(matches) > 0
        assert all(isinstance(match, FacultyFundingMatch) for match in matches)
        assert all(match.status == MatchStatus.PENDING for match in matches)
        assert all(match.match_score.total_score >= agent.min_score_threshold for match in matches)
        assert agent.last_run is not None
    
    def test_generate_matches_with_high_threshold(self, sample_faculty, sample_funding):
        """Test match generation with high threshold filters out matches."""
        agent = MatcherAgent(min_score_threshold=0.95)  # Very high threshold
        
        matches = agent.generate_matches(sample_faculty, sample_funding)
        
        # Should have few or no matches due to high threshold
        assert len(matches) <= 2  # At most one per faculty
    
    def test_generate_matches_empty_lists(self):
        """Test match generation with empty input lists."""
        agent = MatcherAgent()
        
        matches = agent.generate_matches([], [])
        assert matches == []
        
        faculty = [FacultyProfile(
            name="Dr. Test", institution="Test", department="Test",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["test"], methodologies=[ResearchMethodology.COMPUTATIONAL]
        )]
        matches = agent.generate_matches(faculty, [])
        assert matches == []
        
        funding = [FundingOpportunity(
            title="Test", agency="Test", opportunity_id="TEST-001",
            deadline=date.today() + timedelta(days=60),
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
            research_areas=["test"], description="test", url="https://example.com"
        )]
        matches = agent.generate_matches([], funding)
        assert matches == []
    
    def test_generate_matches_max_matches_per_faculty(self, sample_funding):
        """Test max matches per faculty limit."""
        # Create one faculty member
        faculty = [FacultyProfile(
            name="Dr. Popular Researcher",
            institution="Popular University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["artificial intelligence", "biology", "everything"],
            methodologies=[ResearchMethodology.COMPUTATIONAL, ResearchMethodology.EXPERIMENTAL],
            profile_id="popular_faculty"
        )]
        
        # Create many funding opportunities
        many_funding = []
        for i in range(20):
            funding = FundingOpportunity(
                title=f"Grant {i}",
                agency="Test Agency",
                opportunity_id=f"GRANT-{i:03d}",
                deadline=date.today() + timedelta(days=60),
                eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
                research_areas=["artificial intelligence"],
                preferred_methodologies=[ResearchMethodology.COMPUTATIONAL],
                description=f"Grant {i} description",
                url=f"https://example.com/grant-{i}",
                max_award_amount=Decimal('100000')
            )
            many_funding.append(funding)
        
        agent = MatcherAgent(min_score_threshold=0.1, max_matches_per_faculty=5)
        
        matches = agent.generate_matches(faculty, many_funding)
        
        # Should be limited to max_matches_per_faculty
        assert len(matches) <= 5
        
        # All matches should be for the same faculty
        faculty_ids = set(match.faculty_profile_id for match in matches)
        assert len(faculty_ids) == 1
        assert "popular_faculty" in faculty_ids


class TestMatchFiltering:
    """Test match filtering functionality."""
    
    @pytest.fixture
    def sample_matches(self):
        """Create sample matches for filtering tests."""
        return [
            FacultyFundingMatch(
                match_id="match_001",
                faculty_profile_id="faculty_001",
                funding_opportunity_id="funding_001",
                match_score=MatchScore(
                    total_score=0.8,
                    research_alignment=0.9,
                    methodology_match=0.7,
                    career_stage_fit=1.0,
                    deadline_urgency=0.6,
                    budget_alignment=0.8,
                    scoring_algorithm="test"
                )
            ),
            FacultyFundingMatch(
                match_id="match_002",
                faculty_profile_id="faculty_002",
                funding_opportunity_id="funding_002",
                match_score=MatchScore(
                    total_score=0.6,
                    research_alignment=0.5,
                    methodology_match=0.8,
                    career_stage_fit=0.3,
                    deadline_urgency=0.9,
                    budget_alignment=0.7,
                    scoring_algorithm="test"
                )
            ),
            FacultyFundingMatch(
                match_id="match_003",
                faculty_profile_id="faculty_003",
                funding_opportunity_id="funding_003",
                match_score=MatchScore(
                    total_score=0.9,
                    research_alignment=0.95,
                    methodology_match=0.9,
                    career_stage_fit=0.8,
                    deadline_urgency=0.8,
                    budget_alignment=0.9,
                    scoring_algorithm="test"
                )
            )
        ]
    
    def test_filter_by_research_alignment(self, sample_matches):
        """Test filtering by research alignment threshold."""
        agent = MatcherAgent()
        
        filtered = agent.filter_matches_by_criteria(
            sample_matches,
            min_research_alignment=0.8
        )
        
        assert len(filtered) == 2  # matches 001 and 003
        assert all(match.match_score.research_alignment >= 0.8 for match in filtered)
    
    def test_filter_by_career_stage_fit(self, sample_matches):
        """Test filtering by career stage fit threshold."""
        agent = MatcherAgent()
        
        filtered = agent.filter_matches_by_criteria(
            sample_matches,
            min_career_stage_fit=0.5
        )
        
        assert len(filtered) == 2  # matches 001 and 003
        assert all(match.match_score.career_stage_fit >= 0.5 for match in filtered)
    
    def test_filter_multiple_criteria(self, sample_matches):
        """Test filtering with multiple criteria."""
        agent = MatcherAgent()
        
        filtered = agent.filter_matches_by_criteria(
            sample_matches,
            min_research_alignment=0.8,
            min_career_stage_fit=0.5
        )
        
        assert len(filtered) == 2  # matches 001 and 003
        assert all(
            match.match_score.research_alignment >= 0.8 and 
            match.match_score.career_stage_fit >= 0.5 
            for match in filtered
        )
    
    def test_filter_no_matches(self, sample_matches):
        """Test filtering with criteria that exclude all matches."""
        agent = MatcherAgent()
        
        filtered = agent.filter_matches_by_criteria(
            sample_matches,
            min_research_alignment=0.99  # Too high
        )
        
        assert len(filtered) == 0


class TestMatchSaving:
    """Test match saving functionality."""
    
    @pytest.fixture
    def sample_match(self):
        """Create a sample match for saving tests."""
        return FacultyFundingMatch(
            match_id="test_match_001",
            faculty_profile_id="test_faculty_001",
            funding_opportunity_id="test_funding_001",
            match_score=MatchScore(
                total_score=0.85,
                research_alignment=0.9,
                methodology_match=0.8,
                career_stage_fit=1.0,
                deadline_urgency=0.7,
                budget_alignment=0.8,
                scoring_algorithm="test-algorithm-v1"
            ),
            status=MatchStatus.PENDING,
            notification_sent=False
        )
    
    def test_save_matches_success(self, sample_match):
        """Test successful match saving."""
        agent = MatcherAgent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "test_matches.json")
            
            result_path = agent.save_matches([sample_match], output_file)
            
            assert result_path.exists()
            assert str(result_path) == output_file
            
            # Verify file contents
            with open(result_path, 'r') as f:
                saved_data = json.load(f)
            
            assert len(saved_data) == 1
            assert saved_data[0]['match_id'] == "test_match_001"
            assert saved_data[0]['match_score']['total_score'] == 0.85
    
    def test_save_matches_auto_filename(self, sample_match):
        """Test match saving with auto-generated filename."""
        agent = MatcherAgent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                result_path = agent.save_matches([sample_match])
                
                assert result_path.exists()
                assert "faculty_funding_matches_" in str(result_path)
                assert str(result_path).endswith(".json")
            finally:
                os.chdir(original_cwd)
    
    def test_save_empty_matches(self):
        """Test saving empty match list."""
        agent = MatcherAgent()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, "empty_matches.json")
            
            result_path = agent.save_matches([], output_file)
            
            assert result_path.exists()
            
            with open(result_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data == []


class TestMatchStatistics:
    """Test match statistics functionality."""
    
    @pytest.fixture
    def varied_matches(self):
        """Create matches with varied scores for statistics testing."""
        matches = []
        scores = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25]
        
        for i, score in enumerate(scores):
            match = FacultyFundingMatch(
                match_id=f"match_{i:03d}",
                faculty_profile_id=f"faculty_{i:03d}",
                funding_opportunity_id=f"funding_{i:03d}",
                match_score=MatchScore(
                    total_score=score,
                    research_alignment=score,
                    methodology_match=score,
                    career_stage_fit=score,
                    deadline_urgency=score,
                    budget_alignment=score,
                    scoring_algorithm="test"
                )
            )
            matches.append(match)
        
        return matches
    
    def test_statistics_calculation(self, varied_matches):
        """Test statistics calculation."""
        agent = MatcherAgent()
        
        stats = agent.get_match_statistics(varied_matches)
        
        assert stats['total_matches'] == 8
        assert stats['average_score'] == pytest.approx(0.6, abs=0.01)
        assert stats['max_score'] == 0.95
        assert stats['min_score'] == 0.25
        assert stats['unique_faculty'] == 8
        assert stats['unique_opportunities'] == 8
        
        # Check score distribution
        assert stats['score_distribution']['0.9-1.0'] == 1
        assert stats['score_distribution']['0.8-0.9'] == 1
        assert stats['score_distribution']['below-0.5'] == 3
        
        # Check top matches
        assert len(stats['top_matches']) == 8  # All matches since we have <= 10
        assert stats['top_matches'][0]['total_score'] == 0.95  # Highest first
        assert stats['top_matches'][-1]['total_score'] == 0.25  # Lowest last
    
    def test_statistics_empty_matches(self):
        """Test statistics with empty match list."""
        agent = MatcherAgent()
        
        stats = agent.get_match_statistics([])
        
        assert stats['total_matches'] == 0
        assert stats['average_score'] == 0.0
        assert stats['score_distribution'] == {}
        assert stats['top_matches'] == []


class TestA2ACommunication:
    """Test A2A communication functionality."""
    
    def test_process_a2a_message_success(self):
        """Test successful A2A message processing."""
        agent = MatcherAgent()
        
        # Mock the run_matching_a2a method
        with patch.object(agent, 'run_matching_a2a') as mock_run:
            mock_run.return_value = {
                'success': True,
                'matches_count': 5,
                'matches_file': '/tmp/matches.json'
            }
            
            # Create test message
            message = A2AMessage(
                message_id="test_001",
                message_type=MessageType.REQUEST,
                source_agent=AgentType.INGESTION,
                target_agent=AgentType.MATCHER,
                payload={
                    'faculty_data_file': '/tmp/faculty.json',
                    'funding_data_file': '/tmp/funding.json',
                    'min_score_threshold': 0.4
                },
                timestamp=datetime.now()
            )
            
            response = agent.process_a2a_message(message)
            
            assert response.message_type == MessageType.RESPONSE
            assert response.source_agent == AgentType.MATCHER
            assert response.target_agent == AgentType.INGESTION
            assert response.payload['success'] == True
            assert response.payload['matches_count'] == 5
    
    def test_process_a2a_message_missing_parameters(self):
        """Test A2A message processing with missing parameters."""
        agent = MatcherAgent()
        
        # Create message with missing required parameters
        message = A2AMessage(
            message_id="test_002",
            message_type=MessageType.REQUEST,
            source_agent=AgentType.INGESTION,
            target_agent=AgentType.MATCHER,
            payload={
                'faculty_data_file': '/tmp/faculty.json'
                # Missing funding_data_file
            },
            timestamp=datetime.now()
        )
        
        response = agent.process_a2a_message(message)
        
        assert response.message_type == MessageType.RESPONSE
        assert response.payload.get('success') == False
        assert 'error' in response.payload
    
    def test_process_a2a_message_processing_error(self):
        """Test A2A message processing with processing error."""
        agent = MatcherAgent()
        
        # Mock run_matching_a2a to raise an exception
        with patch.object(agent, 'run_matching_a2a') as mock_run:
            mock_run.side_effect = Exception("Processing failed")
            
            message = A2AMessage(
                message_id="test_003",
                message_type=MessageType.REQUEST,
                source_agent=AgentType.INGESTION,
                target_agent=AgentType.MATCHER,
                payload={
                    'faculty_data_file': '/tmp/faculty.json',
                    'funding_data_file': '/tmp/funding.json'
                },
                timestamp=datetime.now()
            )
            
            response = agent.process_a2a_message(message)
            
            assert response.message_type == MessageType.RESPONSE
            assert response.payload.get('success') == False
            assert 'Processing failed' in response.payload.get('error', '')


class TestIntegrationWithRealData:
    """Integration tests with real mock data."""
    
    @pytest.fixture
    def test_data_path(self):
        """Get path to test data directory."""
        return Path(__file__).parent.parent / "mock_data"
    
    def test_full_matching_pipeline(self, test_data_path):
        """Test full matching pipeline with real mock data."""
        agent = MatcherAgent(min_score_threshold=0.2)  # Lower threshold for testing
        
        faculty_file = test_data_path / "processed_faculty.json"
        funding_file = test_data_path / "processed_funding.json"
        
        # Skip if test files don't exist
        if not faculty_file.exists() or not funding_file.exists():
            pytest.skip("Test data files not found")
        
        result = agent.run_matching(str(faculty_file), str(funding_file))
        
        assert result['success'] == True
        assert result['faculty_count'] > 0
        assert result['funding_count'] > 0
        assert result['matches_count'] >= 0
        assert 'matches_file' in result
        assert 'statistics' in result
        assert result['processing_time_seconds'] > 0
    
    def test_run_matching_a2a_with_real_data(self, test_data_path):
        """Test A2A matching process with real mock data."""
        agent = MatcherAgent(min_score_threshold=0.2)
        
        faculty_file = test_data_path / "processed_faculty.json"
        funding_file = test_data_path / "processed_funding.json"
        
        # Skip if test files don't exist
        if not faculty_file.exists() or not funding_file.exists():
            pytest.skip("Test data files not found")
        
        result = agent.run_matching_a2a(str(faculty_file), str(funding_file), 0.3)
        
        assert result['success'] == True
        assert result['min_score_threshold'] == 0.3
        assert isinstance(result['statistics'], dict)
        
        # Verify matches file was created
        matches_file = Path(result['matches_file'])
        assert matches_file.exists()
        
        # Clean up
        matches_file.unlink()
    
    def test_data_loading_error_handling(self):
        """Test error handling for data loading issues."""
        agent = MatcherAgent()
        
        result = agent.run_matching_a2a("nonexistent_faculty.json", "nonexistent_funding.json")
        
        assert result['success'] == False
        assert 'error' in result
        assert 'No valid faculty profiles loaded' in result['error']


if __name__ == "__main__":
    pytest.main([__file__])