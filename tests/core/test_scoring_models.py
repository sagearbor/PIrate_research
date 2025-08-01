"""
Tests for the scoring models module.

This module contains comprehensive tests for all scoring components including
research alignment, methodology matching, career stage compatibility,
deadline urgency, and budget alignment calculations.
"""

import pytest
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from src.core.scoring_models import (
    MatchingEngine, ScoringConfiguration, ResearchAlignmentScorer,
    MethodologyMatcher, CareerStageMatcher, DeadlineUrgencyCalculator,
    BudgetAlignmentCalculator
)
from src.core.models import (
    FacultyProfile, FundingOpportunity, CareerStage, ResearchMethodology,
    Publication, MatchScore
)


class TestScoringConfiguration:
    """Test scoring configuration setup."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = ScoringConfiguration()
        
        assert config.weights['research_alignment'] == 0.35
        assert config.weights['methodology_match'] == 0.25
        assert config.weights['career_stage_fit'] == 0.20
        assert config.weights['deadline_urgency'] == 0.15
        assert config.weights['budget_alignment'] == 0.05
        assert sum(config.weights.values()) == pytest.approx(1.0)
        
        assert config.min_deadline_days == 30
        assert config.methodology_boost_factor == 1.2
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        custom_weights = {
            'research_alignment': 0.4,
            'methodology_match': 0.3,
            'career_stage_fit': 0.2,
            'deadline_urgency': 0.1,
            'budget_alignment': 0.0
        }
        
        config = ScoringConfiguration(weights=custom_weights, min_deadline_days=60)
        
        assert config.weights == custom_weights
        assert config.min_deadline_days == 60


class TestResearchAlignmentScorer:
    """Test research alignment scoring functionality."""
    
    def test_normalize_text(self):
        """Test text normalization."""
        scorer = ResearchAlignmentScorer()
        
        assert scorer.normalize_text("Machine Learning!") == "machine learning"
        assert scorer.normalize_text("AI & ML") == "ai  ml"
        assert scorer.normalize_text("  Deep-Learning  ") == "deeplearning"
    
    def test_extract_keywords(self):
        """Test keyword extraction."""
        scorer = ResearchAlignmentScorer()
        
        keywords = scorer.extract_keywords("Machine learning for healthcare applications")
        assert "machine" in keywords
        assert "learning" in keywords
        assert "healthcare" in keywords
        assert "applications" in keywords
        assert "for" not in keywords  # Should filter out stop words
    
    def test_keyword_overlap_calculation(self):
        """Test keyword overlap calculation."""
        faculty_interests = ["machine learning", "artificial intelligence", "healthcare"]
        funding_areas = ["machine learning", "medical AI", "healthcare informatics"]
        
        overlap = ResearchAlignmentScorer.calculate_keyword_overlap(
            faculty_interests, funding_areas
        )
        
        # Should have overlap on "machine", "learning", "healthcare"
        assert overlap > 0.0
        assert overlap <= 1.0
    
    def test_keyword_overlap_no_match(self):
        """Test keyword overlap with no matches."""
        faculty_interests = ["theoretical physics", "quantum mechanics"]
        funding_areas = ["biology", "genetics", "medical research"]
        
        overlap = ResearchAlignmentScorer.calculate_keyword_overlap(
            faculty_interests, funding_areas
        )
        
        assert overlap == 0.0
    
    def test_keyword_overlap_empty_lists(self):
        """Test keyword overlap with empty lists."""
        assert ResearchAlignmentScorer.calculate_keyword_overlap([], ["ai", "ml"]) == 0.0
        assert ResearchAlignmentScorer.calculate_keyword_overlap(["ai"], []) == 0.0
        assert ResearchAlignmentScorer.calculate_keyword_overlap([], []) == 0.0
    
    def test_publication_relevance(self):
        """Test publication relevance scoring."""
        publications = [
            Publication(
                title="Machine Learning for Medical Diagnosis",
                authors=["Smith, J."],
                year=2023,
                citation_count=50,
                keywords=["machine learning", "medical diagnosis", "AI"]
            ),
            Publication(
                title="Quantum Computing Applications",
                authors=["Doe, J."],
                year=2020,
                citation_count=10,
                keywords=["quantum computing", "algorithms"]
            )
        ]
        
        funding_areas = ["machine learning", "artificial intelligence", "healthcare"]
        
        relevance = ResearchAlignmentScorer.calculate_publication_relevance(
            publications, funding_areas
        )
        
        assert relevance > 0.0
        assert relevance <= 1.0
    
    def test_alignment_score_calculation(self):
        """Test overall alignment score calculation."""
        faculty = FacultyProfile(
            name="Dr. Test",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["machine learning", "healthcare informatics"],
            methodologies=[ResearchMethodology.COMPUTATIONAL],
            publications=[
                Publication(
                    title="AI for Healthcare",
                    authors=["Test, Dr."],
                    year=2023,
                    keywords=["AI", "healthcare", "machine learning"]
                )
            ]
        )
        
        funding = FundingOpportunity(
            title="AI Healthcare Grant",
            agency="NIH",
            opportunity_id="TEST-001",
            deadline=date.today() + timedelta(days=90),
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
            research_areas=["artificial intelligence", "machine learning", "healthcare"],
            description="AI research for healthcare applications",
            url="https://example.com"
        )
        
        scorer = ResearchAlignmentScorer()
        alignment_score = scorer.calculate_alignment_score(faculty, funding)
        
        assert 0.0 <= alignment_score <= 1.0
        assert alignment_score > 0.5  # Should be good match


class TestMethodologyMatcher:
    """Test methodology matching functionality."""
    
    def test_exact_methodology_match(self):
        """Test exact methodology matching."""
        faculty_methods = [ResearchMethodology.EXPERIMENTAL]
        funding_methods = [ResearchMethodology.EXPERIMENTAL]
        
        score = MethodologyMatcher.calculate_methodology_score(
            faculty_methods, funding_methods
        )
        
        assert score == 1.0
    
    def test_compatible_methodology_match(self):
        """Test compatible methodology matching."""
        faculty_methods = [ResearchMethodology.EXPERIMENTAL]
        funding_methods = [ResearchMethodology.CLINICAL]
        
        score = MethodologyMatcher.calculate_methodology_score(
            faculty_methods, funding_methods
        )
        
        assert score == 0.8  # Based on compatibility matrix
    
    def test_incompatible_methodology_match(self):
        """Test incompatible methodology matching."""
        faculty_methods = [ResearchMethodology.THEORETICAL]
        funding_methods = [ResearchMethodology.CLINICAL]
        
        score = MethodologyMatcher.calculate_methodology_score(
            faculty_methods, funding_methods
        )
        
        assert score == 0.2  # Low compatibility
    
    def test_multiple_methodologies(self):
        """Test matching with multiple methodologies."""
        faculty_methods = [ResearchMethodology.EXPERIMENTAL, ResearchMethodology.COMPUTATIONAL]
        funding_methods = [ResearchMethodology.COMPUTATIONAL, ResearchMethodology.THEORETICAL]
        
        score = MethodologyMatcher.calculate_methodology_score(
            faculty_methods, funding_methods
        )
        
        assert score == 1.0  # Best match should be COMPUTATIONAL-COMPUTATIONAL
    
    def test_empty_methodology_lists(self):
        """Test handling of empty methodology lists."""
        score = MethodologyMatcher.calculate_methodology_score([], [ResearchMethodology.EXPERIMENTAL])
        assert score == 0.5  # Neutral score
        
        score = MethodologyMatcher.calculate_methodology_score([ResearchMethodology.EXPERIMENTAL], [])
        assert score == 0.5  # Neutral score
        
        score = MethodologyMatcher.calculate_methodology_score([], [])
        assert score == 0.5  # Neutral score


class TestCareerStageMatcher:
    """Test career stage matching functionality."""
    
    def test_exact_career_stage_match(self):
        """Test exact career stage matching."""
        config = ScoringConfiguration()
        
        score = CareerStageMatcher.calculate_career_stage_score(
            CareerStage.ASSISTANT_PROFESSOR,
            [CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR],
            config
        )
        
        assert score == 1.0
    
    def test_compatible_career_stage_match(self):
        """Test compatible career stage matching."""
        config = ScoringConfiguration()
        
        # Postdoc applying for assistant professor position
        score = CareerStageMatcher.calculate_career_stage_score(
            CareerStage.POSTDOC,
            [CareerStage.ASSISTANT_PROFESSOR],
            config
        )
        
        assert score == 0.7  # Compatible but not exact
    
    def test_incompatible_career_stage_match(self):
        """Test incompatible career stage matching."""
        config = ScoringConfiguration()
        
        # Graduate student applying for full professor position
        score = CareerStageMatcher.calculate_career_stage_score(
            CareerStage.GRADUATE_STUDENT,
            [CareerStage.FULL_PROFESSOR],
            config
        )
        
        assert score == 0.0  # Incompatible
    
    def test_no_career_stage_restrictions(self):
        """Test when no career stage restrictions exist."""
        config = ScoringConfiguration()
        
        score = CareerStageMatcher.calculate_career_stage_score(
            CareerStage.ASSISTANT_PROFESSOR,
            [],
            config
        )
        
        assert score == 1.0  # No restrictions


class TestDeadlineUrgencyCalculator:
    """Test deadline urgency calculation."""
    
    def test_optimal_deadline_range(self):
        """Test scoring for optimal deadline range."""
        config = ScoringConfiguration()
        
        # 60 days out - should be high urgency
        deadline = date.today() + timedelta(days=60)
        score = DeadlineUrgencyCalculator.calculate_urgency_score(deadline, config)
        
        assert score >= 0.8
    
    def test_too_urgent_deadline(self):
        """Test scoring for too urgent deadlines."""
        config = ScoringConfiguration()
        
        # 15 days out - too urgent
        deadline = date.today() + timedelta(days=15)
        score = DeadlineUrgencyCalculator.calculate_urgency_score(deadline, config)
        
        assert score == 0.2
    
    def test_past_deadline(self):
        """Test scoring for past deadlines."""
        config = ScoringConfiguration()
        
        # Past deadline
        deadline = date.today() - timedelta(days=5)
        score = DeadlineUrgencyCalculator.calculate_urgency_score(deadline, config)
        
        assert score == 0.0
    
    def test_far_future_deadline(self):
        """Test scoring for far future deadlines."""
        config = ScoringConfiguration()
        
        # 400 days out - low urgency
        deadline = date.today() + timedelta(days=400)
        score = DeadlineUrgencyCalculator.calculate_urgency_score(deadline, config)
        
        assert score >= 0.3
        assert score < 0.8


class TestBudgetAlignmentCalculator:
    """Test budget alignment calculation."""
    
    def test_faculty_budget_estimation(self):
        """Test faculty budget range estimation."""
        # Assistant professor
        faculty = FacultyProfile(
            name="Dr. Test",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["AI"],
            methodologies=[ResearchMethodology.COMPUTATIONAL]
        )
        
        min_budget, max_budget = BudgetAlignmentCalculator.estimate_faculty_budget_range(faculty)
        
        assert min_budget >= Decimal('25000')
        assert max_budget <= Decimal('200000')
        assert min_budget < max_budget
    
    def test_budget_score_perfect_match(self):
        """Test budget scoring for perfect match."""
        faculty = FacultyProfile(
            name="Dr. Test",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["AI"],
            methodologies=[ResearchMethodology.COMPUTATIONAL]
        )
        
        funding = FundingOpportunity(
            title="Test Grant",
            agency="NIH",
            opportunity_id="TEST-001",
            deadline=date.today() + timedelta(days=90),
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
            research_areas=["AI"],
            description="Test grant",
            url="https://example.com",
            max_award_amount=Decimal('100000')  # Within expected range
        )
        
        score = BudgetAlignmentCalculator.calculate_budget_score(faculty, funding)
        
        assert score == 1.0
    
    def test_budget_score_too_small(self):
        """Test budget scoring when funding is too small."""
        faculty = FacultyProfile(
            name="Dr. Test",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.FULL_PROFESSOR,
            research_interests=["AI"],
            methodologies=[ResearchMethodology.COMPUTATIONAL],
            total_citations=1000,
            h_index=25
        )
        
        funding = FundingOpportunity(
            title="Small Grant",
            agency="NSF",
            opportunity_id="TEST-002",
            deadline=date.today() + timedelta(days=90),
            eligible_career_stages=[CareerStage.FULL_PROFESSOR],
            research_areas=["AI"],
            description="Small test grant",
            url="https://example.com",
            max_award_amount=Decimal('5000')  # Too small for full professor
        )
        
        score = BudgetAlignmentCalculator.calculate_budget_score(faculty, funding)
        
        assert score < 1.0
        assert score >= 0.0
    
    def test_budget_score_no_amount(self):
        """Test budget scoring when no amount specified."""
        faculty = FacultyProfile(
            name="Dr. Test",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["AI"],
            methodologies=[ResearchMethodology.COMPUTATIONAL]
        )
        
        funding = FundingOpportunity(
            title="Test Grant",
            agency="NIH",
            opportunity_id="TEST-001",
            deadline=date.today() + timedelta(days=90),
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
            research_areas=["AI"],
            description="Test grant",
            url="https://example.com"
            # No max_award_amount specified
        )
        
        score = BudgetAlignmentCalculator.calculate_budget_score(faculty, funding)
        
        assert score == 0.5  # Neutral score


class TestMatchingEngine:
    """Test the main matching engine."""
    
    @pytest.fixture
    def sample_faculty(self):
        """Create sample faculty profile."""
        return FacultyProfile(
            name="Dr. Test Faculty",
            institution="Test University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["machine learning", "healthcare informatics"],
            methodologies=[ResearchMethodology.COMPUTATIONAL, ResearchMethodology.EXPERIMENTAL],
            publications=[
                Publication(
                    title="AI for Healthcare",
                    authors=["Faculty, T."],
                    year=2023,
                    citation_count=25,
                    keywords=["AI", "healthcare", "machine learning"]
                )
            ],
            h_index=10,
            total_citations=200,
            profile_id="test_faculty_001"
        )
    
    @pytest.fixture
    def sample_funding(self):
        """Create sample funding opportunity."""
        return FundingOpportunity(
            title="AI Healthcare Innovation Grant",
            agency="NIH",
            opportunity_id="TEST-AI-001",
            deadline=date.today() + timedelta(days=90),
            eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR],
            research_areas=["artificial intelligence", "machine learning", "healthcare informatics"],
            preferred_methodologies=[ResearchMethodology.COMPUTATIONAL, ResearchMethodology.EXPERIMENTAL],
            description="Grant for AI healthcare research",
            url="https://example.com/grant",
            max_award_amount=Decimal('200000'),
            min_award_amount=Decimal('50000')
        )
    
    def test_matching_engine_initialization(self):
        """Test matching engine initialization."""
        engine = MatchingEngine()
        
        assert engine.config is not None
        assert engine.research_scorer is not None
        assert engine.methodology_matcher is not None
        assert engine.career_matcher is not None
        assert engine.deadline_calculator is not None
        assert engine.budget_calculator is not None
    
    def test_calculate_match_score(self, sample_faculty, sample_funding):
        """Test match score calculation."""
        engine = MatchingEngine()
        
        match_score = engine.calculate_match_score(sample_faculty, sample_funding)
        
        assert isinstance(match_score, MatchScore)
        assert 0.0 <= match_score.total_score <= 1.0
        assert 0.0 <= match_score.research_alignment <= 1.0
        assert 0.0 <= match_score.methodology_match <= 1.0
        assert 0.0 <= match_score.career_stage_fit <= 1.0
        assert 0.0 <= match_score.deadline_urgency <= 1.0
        assert 0.0 <= match_score.budget_alignment <= 1.0
        
        # Should be a good match
        assert match_score.total_score > 0.6
    
    def test_batch_score_matches(self, sample_faculty, sample_funding):
        """Test batch scoring of matches."""
        engine = MatchingEngine()
        
        faculty_list = [sample_faculty]
        funding_list = [sample_funding]
        
        matches = engine.batch_score_matches(faculty_list, funding_list, min_score_threshold=0.0)
        
        assert len(matches) == 1
        faculty, funding, score = matches[0]
        
        assert faculty == sample_faculty
        assert funding == sample_funding
        assert isinstance(score, MatchScore)
    
    def test_batch_score_matches_with_threshold(self, sample_faculty, sample_funding):
        """Test batch scoring with threshold filtering."""
        engine = MatchingEngine()
        
        faculty_list = [sample_faculty]
        funding_list = [sample_funding]
        
        # High threshold that should filter out the match
        matches = engine.batch_score_matches(faculty_list, funding_list, min_score_threshold=0.99)
        
        assert len(matches) == 0
    
    def test_batch_score_multiple_combinations(self):
        """Test batch scoring with multiple faculty and funding."""
        engine = MatchingEngine()
        
        faculty_list = [
            FacultyProfile(
                name="Dr. AI Researcher",
                institution="AI University",
                department="Computer Science",
                career_stage=CareerStage.ASSISTANT_PROFESSOR,
                research_interests=["artificial intelligence", "machine learning"],
                methodologies=[ResearchMethodology.COMPUTATIONAL],
                profile_id="ai_faculty"
            ),
            FacultyProfile(
                name="Dr. Bio Researcher",
                institution="Bio University",
                department="Biology",
                career_stage=CareerStage.ASSOCIATE_PROFESSOR,
                research_interests=["biology", "genetics"],
                methodologies=[ResearchMethodology.EXPERIMENTAL],
                profile_id="bio_faculty"
            )
        ]
        
        funding_list = [
            FundingOpportunity(
                title="AI Research Grant",
                agency="NSF",
                opportunity_id="AI-GRANT-001",
                deadline=date.today() + timedelta(days=60),
                eligible_career_stages=[CareerStage.ASSISTANT_PROFESSOR],
                research_areas=["artificial intelligence", "computer science"],
                preferred_methodologies=[ResearchMethodology.COMPUTATIONAL],
                description="AI research funding",
                url="https://example.com/ai-grant"
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
                url="https://example.com/bio-grant"
            )
        ]
        
        matches = engine.batch_score_matches(faculty_list, funding_list, min_score_threshold=0.3)
        
        # Should have multiple matches
        assert len(matches) >= 2
        
        # Should be sorted by score (descending)
        scores = [match[2].total_score for match in matches]
        assert scores == sorted(scores, reverse=True)


class TestWithRealData:
    """Test scoring with real mock data."""
    
    @pytest.fixture
    def test_data_path(self):
        """Get path to test data directory."""
        return Path(__file__).parent.parent / "mock_data"
    
    @pytest.fixture
    def scoring_test_cases(self, test_data_path):
        """Load scoring test cases."""
        with open(test_data_path / "scoring_test_cases.json", 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def faculty_data(self, test_data_path):
        """Load faculty test data."""
        with open(test_data_path / "processed_faculty.json", 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def funding_data(self, test_data_path):
        """Load funding test data."""
        with open(test_data_path / "processed_funding.json", 'r') as f:
            return json.load(f)
    
    def create_faculty_from_data(self, faculty_data):
        """Create FacultyProfile from test data."""
        # Convert enums
        faculty_data['career_stage'] = CareerStage(faculty_data['career_stage'])
        faculty_data['methodologies'] = [ResearchMethodology(m) for m in faculty_data['methodologies']]
        
        # Convert publications
        if 'publications' in faculty_data:
            publications = []
            for pub_data in faculty_data['publications']:
                publications.append(Publication(**pub_data))
            faculty_data['publications'] = publications
        
        return FacultyProfile(**faculty_data)
    
    def create_funding_from_data(self, funding_data):
        """Create FundingOpportunity from test data."""
        # Convert enums
        funding_data['eligible_career_stages'] = [CareerStage(stage) for stage in funding_data['eligible_career_stages']]
        if 'preferred_methodologies' in funding_data:
            funding_data['preferred_methodologies'] = [ResearchMethodology(m) for m in funding_data['preferred_methodologies']]
        
        # Convert dates
        funding_data['deadline'] = date.fromisoformat(funding_data['deadline'])
        if 'award_start_date' in funding_data and funding_data['award_start_date']:
            funding_data['award_start_date'] = date.fromisoformat(funding_data['award_start_date'])
        
        # Convert decimals
        for field in ['total_budget', 'max_award_amount', 'min_award_amount']:
            if field in funding_data and funding_data[field] is not None:
                funding_data[field] = Decimal(str(funding_data[field]))
        
        return FundingOpportunity(**funding_data)
    
    def test_methodology_compatibility_cases(self, scoring_test_cases):
        """Test methodology compatibility with defined test cases."""
        for test_case in scoring_test_cases['methodology_compatibility_tests']:
            faculty_methods = [ResearchMethodology(m) for m in test_case['faculty_methodologies']]
            funding_methods = [ResearchMethodology(m) for m in test_case['funding_methodologies']]
            
            score = MethodologyMatcher.calculate_methodology_score(faculty_methods, funding_methods)
            
            assert score == pytest.approx(test_case['expected_score'], abs=0.1)
    
    def test_career_stage_compatibility_cases(self, scoring_test_cases):
        """Test career stage compatibility with defined test cases."""
        config = ScoringConfiguration()
        
        for test_case in scoring_test_cases['career_stage_compatibility_tests']:
            faculty_stage = CareerStage(test_case['faculty_stage'])
            eligible_stages = [CareerStage(stage) for stage in test_case['eligible_stages']]
            
            score = CareerStageMatcher.calculate_career_stage_score(faculty_stage, eligible_stages, config)
            
            assert score == pytest.approx(test_case['expected_score'], abs=0.1)
    
    def test_deadline_urgency_cases(self, scoring_test_cases):
        """Test deadline urgency with defined test cases."""
        config = ScoringConfiguration()
        
        for test_case in scoring_test_cases['deadline_urgency_tests']:
            deadline = date.today() + timedelta(days=test_case['days_remaining'])
            
            score = DeadlineUrgencyCalculator.calculate_urgency_score(deadline, config)
            
            if 'expected_score' in test_case:
                assert score == pytest.approx(test_case['expected_score'], abs=0.1)
            else:
                min_score, max_score = test_case['expected_score_range']
                assert min_score <= score <= max_score
    
    def test_research_alignment_cases(self, scoring_test_cases):
        """Test research alignment with defined test cases."""
        for test_case in scoring_test_cases['research_alignment_tests']:
            faculty_interests = test_case['faculty_interests']
            funding_areas = test_case['funding_areas']
            
            score = ResearchAlignmentScorer.calculate_keyword_overlap(faculty_interests, funding_areas)
            
            min_score, max_score = test_case['expected_score_range']
            assert min_score <= score <= max_score, f"Failed for case: {test_case['description']}"
    
    def test_full_matching_with_test_cases(self, scoring_test_cases, faculty_data, funding_data):
        """Test full matching pipeline with defined test cases."""
        engine = MatchingEngine()
        
        # Create lookup dictionaries
        faculty_lookup = {f['profile_id']: self.create_faculty_from_data(f.copy()) for f in faculty_data}
        funding_lookup = {f['opportunity_id']: self.create_funding_from_data(f.copy()) for f in funding_data}
        
        for test_case in scoring_test_cases['test_cases']:
            faculty = faculty_lookup[test_case['faculty_id']]
            funding = funding_lookup[test_case['funding_id']]
            
            match_score = engine.calculate_match_score(faculty, funding)
            
            expected = test_case['expected_scores']
            
            # Test individual component scores
            assert match_score.research_alignment == pytest.approx(expected['research_alignment'], abs=0.15)
            assert match_score.methodology_match == pytest.approx(expected['methodology_match'], abs=0.15)
            assert match_score.career_stage_fit == pytest.approx(expected['career_stage_fit'], abs=0.1)
            # Note: deadline_urgency and budget_alignment may vary based on current date and estimation
            
            # Test total score range
            min_total, max_total = expected['total_score_range']
            assert min_total <= match_score.total_score <= max_total, \
                f"Total score {match_score.total_score} not in range [{min_total}, {max_total}] for {test_case['description']}"


if __name__ == "__main__":
    pytest.main([__file__])