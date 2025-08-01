"""
Tests for core Pydantic models.

This module tests model creation, validation (positive and negative cases),
and serialization for all core data structures.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from pydantic import ValidationError

from src.core.models import (
    Publication, FacultyProfile, FundingOpportunity, ResearchIdea,
    CollaboratorSuggestion, MatchScore, FacultyFundingMatch,
    SystemMetrics, NotificationContent,
    CareerStage, ResearchMethodology, ProposalVariant, MatchStatus
)


class TestPublication:
    """Test cases for Publication model."""

    def test_valid_publication_creation(self):
        """Test creating a valid publication."""
        pub = Publication(
            title="AI in Healthcare Research",
            authors=["Smith, J.", "Johnson, A."],
            journal="Nature Medicine",
            year=2023,
            doi="10.1038/s41591-023-01234-5",
            citation_count=15,
            keywords=["artificial intelligence", "healthcare", "machine learning"]
        )
        
        assert pub.title == "AI in Healthcare Research"
        assert len(pub.authors) == 2
        assert pub.year == 2023
        assert pub.citation_count == 15

    def test_publication_year_validation(self):
        """Test year validation for publications."""
        # Test invalid year (too old)
        with pytest.raises(ValidationError) as exc_info:
            Publication(
                title="Old Paper",
                authors=["Author, A."],
                year=1800  # Too old
            )
        assert "Year must be between 1900" in str(exc_info.value)
        
        # Test invalid year (future)
        current_year = datetime.now().year
        with pytest.raises(ValidationError) as exc_info:
            Publication(
                title="Future Paper", 
                authors=["Author, A."],
                year=current_year + 5  # Too far in future
            )
        assert "Year must be between 1900" in str(exc_info.value)

    def test_publication_minimal_data(self):
        """Test publication with minimal required data."""
        pub = Publication(
            title="Minimal Paper",
            authors=["Solo, A."],
            year=2023
        )
        
        assert pub.title == "Minimal Paper"
        assert pub.journal is None
        assert pub.citation_count == 0
        assert pub.keywords == []


class TestFacultyProfile:
    """Test cases for FacultyProfile model."""

    def test_valid_faculty_profile_creation(self):
        """Test creating a valid faculty profile."""
        profile = FacultyProfile(
            name="Dr. Jane Smith",
            email="jane.smith@university.edu",
            institution="Research University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["Machine Learning", "AI Ethics", "Healthcare AI"],
            methodologies=[ResearchMethodology.EXPERIMENTAL, ResearchMethodology.COMPUTATIONAL],
            h_index=15,
            total_citations=450
        )
        
        assert profile.name == "Dr. Jane Smith"
        assert profile.career_stage == CareerStage.ASSISTANT_PROFESSOR
        assert len(profile.research_interests) == 3
        assert len(profile.methodologies) == 2
        assert profile.h_index == 15

    def test_research_interests_normalization(self):
        """Test that research interests are normalized to lowercase."""
        profile = FacultyProfile(
            name="Dr. Test",
            institution="Test Uni",
            department="CS",
            career_stage=CareerStage.POSTDOC,
            research_interests=["Machine Learning", "AI ETHICS", "  Healthcare AI  "],
            methodologies=[ResearchMethodology.COMPUTATIONAL]
        )
        
        expected_interests = ["machine learning", "ai ethics", "healthcare ai"]
        assert profile.research_interests == expected_interests

    def test_email_validation(self):
        """Test email validation for faculty profiles."""
        # Valid email should work
        profile = FacultyProfile(
            name="Dr. Test",
            email="test@university.edu",
            institution="Test Uni",
            department="CS", 
            career_stage=CareerStage.POSTDOC,
            research_interests=["AI"],
            methodologies=[ResearchMethodology.COMPUTATIONAL]
        )
        assert profile.email == "test@university.edu"
        
        # Invalid email should fail
        with pytest.raises(ValidationError) as exc_info:
            FacultyProfile(
                name="Dr. Test",
                email="invalid-email",  # No @ symbol
                institution="Test Uni",
                department="CS",
                career_stage=CareerStage.POSTDOC,
                research_interests=["AI"],
                methodologies=[ResearchMethodology.COMPUTATIONAL]
            )
        assert "Invalid email format" in str(exc_info.value)

    def test_research_interests_required(self):
        """Test that at least one research interest is required."""
        with pytest.raises(ValidationError) as exc_info:
            FacultyProfile(
                name="Dr. Test",
                institution="Test Uni",
                department="CS",
                career_stage=CareerStage.POSTDOC,
                research_interests=[],  # Empty list
                methodologies=[ResearchMethodology.COMPUTATIONAL]
            )
        assert "At least one research interest is required" in str(exc_info.value)


class TestFundingOpportunity:
    """Test cases for FundingOpportunity model."""

    def test_valid_funding_opportunity_creation(self):
        """Test creating a valid funding opportunity."""
        tomorrow = date.today() + timedelta(days=1)
        
        opportunity = FundingOpportunity(
            title="AI Research Grant",
            agency="National Science Foundation",
            opportunity_id="NSF-2024-AI-001",
            total_budget=Decimal("1000000.00"),
            max_award_amount=Decimal("200000.00"),
            deadline=tomorrow,
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR],
            research_areas=["Artificial Intelligence", "Machine Learning"],
            description="Funding for AI research projects",
            url="https://nsf.gov/funding/ai-2024",
            source="NSF"
        )
        
        assert opportunity.title == "AI Research Grant" 
        assert opportunity.agency == "National Science Foundation"
        assert opportunity.total_budget == Decimal("1000000.00")
        assert len(opportunity.eligible_career_stages) == 2
        assert len(opportunity.research_areas) == 2

    def test_deadline_validation(self):
        """Test deadline validation for funding opportunities."""
        yesterday = date.today() - timedelta(days=1)
        
        with pytest.raises(ValidationError) as exc_info:
            FundingOpportunity(
                title="Past Deadline Grant",
                agency="Test Agency",
                opportunity_id="TEST-001",
                deadline=yesterday,  # Past deadline
                eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
                research_areas=["Test Area"],
                description="Test description",
                url="https://test.gov",
                source="TEST"
            )
        assert "Deadline cannot be in the past" in str(exc_info.value)

    def test_research_areas_required(self):
        """Test that at least one research area is required."""
        tomorrow = date.today() + timedelta(days=1)
        
        with pytest.raises(ValidationError) as exc_info:
            FundingOpportunity(
                title="No Areas Grant",
                agency="Test Agency", 
                opportunity_id="TEST-001",
                deadline=tomorrow,
                eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
                research_areas=[],  # Empty list
                description="Test description",
                url="https://test.gov",
                source="TEST"
            )
        assert "At least one research area is required" in str(exc_info.value)

    def test_research_areas_normalization(self):
        """Test that research areas are normalized to lowercase."""
        tomorrow = date.today() + timedelta(days=1)
        
        opportunity = FundingOpportunity(
            title="Test Grant",
            agency="Test Agency",
            opportunity_id="TEST-001", 
            deadline=tomorrow,
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
            research_areas=["Machine Learning", "AI ETHICS", "  Data Science  "],
            description="Test description",
            url="https://test.gov",
            source="TEST"
        )
        
        expected_areas = ["machine learning", "ai ethics", "data science"]
        assert opportunity.research_areas == expected_areas


class TestResearchIdea:
    """Test cases for ResearchIdea model."""

    def test_valid_research_idea_creation(self):
        """Test creating a valid research idea."""
        idea = ResearchIdea(
            title="AI-Powered Medical Diagnosis",
            variant_type=ProposalVariant.INNOVATIVE,
            research_question="Can deep learning improve diagnostic accuracy?",
            methodology=[ResearchMethodology.EXPERIMENTAL, ResearchMethodology.COMPUTATIONAL],
            objectives=["Develop AI model", "Validate on clinical data", "Compare to human experts"],
            timeline_months=24,
            estimated_budget=Decimal("150000.00"),
            innovation_level=0.8,
            feasibility_score=0.7,
            impact_potential=0.9
        )
        
        assert idea.title == "AI-Powered Medical Diagnosis"
        assert idea.variant_type == ProposalVariant.INNOVATIVE
        assert idea.timeline_months == 24
        assert len(idea.objectives) == 3
        assert idea.innovation_level == 0.8

    def test_timeline_validation(self):
        """Test timeline validation for research ideas."""
        # Test invalid timeline (too short)
        with pytest.raises(ValidationError) as exc_info:
            ResearchIdea(
                title="Test Idea",
                variant_type=ProposalVariant.CONSERVATIVE,
                research_question="Test question?",
                methodology=[ResearchMethodology.THEORETICAL],
                objectives=["Test objective"],
                timeline_months=0,  # Invalid
                estimated_budget=Decimal("10000.00"),
                innovation_level=0.5,
                feasibility_score=0.8,
                impact_potential=0.6
            )
        assert "Timeline must be between 1 and 120 months" in str(exc_info.value)
        
        # Test invalid timeline (too long)
        with pytest.raises(ValidationError) as exc_info:
            ResearchIdea(
                title="Test Idea",
                variant_type=ProposalVariant.STRETCH,
                research_question="Test question?",
                methodology=[ResearchMethodology.THEORETICAL],
                objectives=["Test objective"],
                timeline_months=150,  # Too long
                estimated_budget=Decimal("10000.00"),
                innovation_level=0.5,
                feasibility_score=0.8,
                impact_potential=0.6
            )
        assert "Timeline must be between 1 and 120 months" in str(exc_info.value)

    def test_score_ranges(self):
        """Test that all score fields are properly constrained to 0-1 range."""
        # Valid scores should work
        idea = ResearchIdea(
            title="Test Idea",
            variant_type=ProposalVariant.CONSERVATIVE,
            research_question="Test question?",
            methodology=[ResearchMethodology.THEORETICAL],
            objectives=["Test objective"],
            timeline_months=12,
            estimated_budget=Decimal("10000.00"),
            innovation_level=0.0,  # Minimum
            feasibility_score=1.0,  # Maximum
            impact_potential=0.5   # Middle
        )
        assert idea.innovation_level == 0.0
        assert idea.feasibility_score == 1.0
        assert idea.impact_potential == 0.5


class TestCollaboratorSuggestion:
    """Test cases for CollaboratorSuggestion model."""

    def test_valid_collaborator_suggestion_creation(self):
        """Test creating a valid collaborator suggestion."""
        suggestion = CollaboratorSuggestion(
            faculty_profile_id="profile_123",
            name="Dr. Alice Johnson",
            institution="Partner University",
            relevance_score=0.85,
            complementary_expertise=["Data Mining", "Statistics"],
            shared_interests=["Machine Learning", "Healthcare"]
        )
        
        assert suggestion.faculty_profile_id == "profile_123"
        assert suggestion.name == "Dr. Alice Johnson"
        assert suggestion.relevance_score == 0.85
        assert len(suggestion.complementary_expertise) == 2
        assert len(suggestion.shared_interests) == 2


class TestMatchScore:
    """Test cases for MatchScore model."""

    def test_valid_match_score_creation(self):
        """Test creating a valid match score."""
        score = MatchScore(
            total_score=0.82,
            research_alignment=0.9,
            methodology_match=0.8,
            career_stage_fit=0.75,
            deadline_urgency=0.6,
            budget_alignment=0.85,
            scoring_algorithm="multi_dimensional_v1"
        )
        
        assert score.total_score == 0.82
        assert score.research_alignment == 0.9
        assert score.scoring_algorithm == "multi_dimensional_v1"


class TestFacultyFundingMatch:
    """Test cases for FacultyFundingMatch model."""

    def test_valid_match_creation(self):
        """Test creating a valid faculty-funding match."""
        match_score = MatchScore(
            total_score=0.82,
            research_alignment=0.9,
            methodology_match=0.8,
            career_stage_fit=0.75,
            deadline_urgency=0.6,
            budget_alignment=0.85,
            scoring_algorithm="multi_dimensional_v1"
        )
        
        match = FacultyFundingMatch(
            match_id="match_001",
            faculty_profile_id="profile_123",
            funding_opportunity_id="funding_456",
            match_score=match_score,
            status=MatchStatus.PENDING
        )
        
        assert match.match_id == "match_001"
        assert match.faculty_profile_id == "profile_123"
        assert match.funding_opportunity_id == "funding_456"
        assert match.status == MatchStatus.PENDING
        assert match.match_score.total_score == 0.82


class TestSystemMetrics:
    """Test cases for SystemMetrics model."""

    def test_valid_system_metrics_creation(self):
        """Test creating valid system metrics."""
        metrics = SystemMetrics(
            total_funding_opportunities=150,
            total_faculty_profiles=500,
            active_opportunities=75,
            total_matches_generated=1200,
            high_quality_matches=300,
            matches_with_faculty_response=45,
            successful_applications=12,
            application_rate=0.15,
            system_uptime_hours=720.5
        )
        
        assert metrics.total_funding_opportunities == 150
        assert metrics.total_faculty_profiles == 500
        assert metrics.active_opportunities == 75
        assert metrics.application_rate == 0.15


class TestNotificationContent:
    """Test cases for NotificationContent model."""

    def test_valid_notification_creation(self):
        """Test creating a valid notification."""
        tomorrow = date.today() + timedelta(days=1)
        
        notification = NotificationContent(
            recipient_email="faculty@university.edu",
            recipient_name="Dr. Smith",
            subject="New Funding Opportunity Match",
            body_html="<p>You have a new match!</p>",
            body_text="You have a new match!",
            match_id="match_123",
            funding_title="AI Research Grant",
            deadline=tomorrow
        )
        
        assert notification.recipient_email == "faculty@university.edu"
        assert notification.recipient_name == "Dr. Smith"
        assert notification.match_id == "match_123"
        assert notification.sent is False
        assert notification.sent_date is None


class TestModelSerialization:
    """Test JSON serialization and deserialization of models."""

    def test_faculty_profile_serialization(self):
        """Test that faculty profile can be serialized and deserialized."""
        original_profile = FacultyProfile(
            name="Dr. Test",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["AI", "ML"],
            methodologies=[ResearchMethodology.COMPUTATIONAL]
        )
        
        # Serialize to dict
        profile_dict = original_profile.model_dump()
        assert isinstance(profile_dict, dict)
        assert profile_dict["name"] == "Dr. Test"
        assert profile_dict["career_stage"] == "assistant_professor"
        
        # Deserialize from dict
        reconstructed_profile = FacultyProfile(**profile_dict)
        assert reconstructed_profile.name == original_profile.name
        assert reconstructed_profile.career_stage == original_profile.career_stage
        assert reconstructed_profile.research_interests == original_profile.research_interests

    def test_funding_opportunity_serialization(self):
        """Test that funding opportunity can be serialized and deserialized."""
        tomorrow = date.today() + timedelta(days=1)
        
        original_opportunity = FundingOpportunity(
            title="Test Grant",
            agency="Test Agency",
            opportunity_id="TEST-001",
            deadline=tomorrow,
            eligible_career_stages=[CareerStage.POSTDOC],
            research_areas=["test area"],
            description="Test description",
            url="https://test.gov",
            source="TEST"
        )
        
        # Serialize to JSON string
        json_str = original_opportunity.model_dump_json()
        assert isinstance(json_str, str)
        
        # Deserialize from JSON string
        reconstructed_opportunity = FundingOpportunity.model_validate_json(json_str)
        assert reconstructed_opportunity.title == original_opportunity.title
        assert reconstructed_opportunity.deadline == original_opportunity.deadline
        assert reconstructed_opportunity.eligible_career_stages == original_opportunity.eligible_career_stages