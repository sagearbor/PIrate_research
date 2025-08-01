"""
Test suite for the Idea Generation Agent.

This module tests the IdeaGenerationAgent class functionality including
proposal variant generation, budget estimation, timeline estimation,
and integration with mock LLM responses.
"""

import pytest
import json
import tempfile
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.agents.idea_agent import IdeaGenerationAgent
from src.core.proposal_variants import ProposalVariantGenerator, BudgetEstimator, TimelineEstimator
from src.core.models import ProposalVariant, CareerStage, ResearchMethodology, ResearchIdea
from src.core.a2a_protocols import A2AMessage, MessageType, AgentType


class TestIdeaGenerationAgent:
    """Test cases for IdeaGenerationAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create an IdeaGenerationAgent instance for testing."""
        return IdeaGenerationAgent(
            llm_model="test-gpt-4",
            max_ideas_per_match=3,
            enable_llm_integration=False
        )
    
    @pytest.fixture
    def mock_matches_data(self):
        """Mock matches data for testing."""
        return [
            {
                "match_id": "test_match_001",
                "faculty_profile_id": "faculty_001",
                "funding_opportunity_id": "NIH-2024-AI-HEALTHCARE-001",
                "match_score": {
                    "total_score": 0.85,
                    "research_alignment": 0.90,
                    "methodology_match": 0.80,
                    "career_stage_fit": 1.0,
                    "deadline_urgency": 0.75,
                    "budget_alignment": 0.80
                }
            }
        ]
    
    @pytest.fixture
    def mock_faculty_data(self):
        """Mock faculty data for testing."""
        return {
            "faculty_001": {
                "name": "Dr. Test Faculty",
                "career_stage": "assistant_professor",
                "research_interests": ["machine learning", "healthcare informatics"],
                "methodologies": ["experimental", "computational"],
                "publications": [
                    {
                        "title": "Test Publication",
                        "keywords": ["AI", "healthcare"]
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_funding_data(self):
        """Mock funding data for testing."""
        return {
            "NIH-2024-AI-HEALTHCARE-001": {
                "title": "AI for Healthcare Innovation Grant",
                "research_areas": ["artificial intelligence", "healthcare informatics"],
                "keywords": ["AI", "healthcare", "clinical trials"],
                "max_award_amount": "500000.00",
                "project_duration_months": 36
            }
        }
    
    @pytest.fixture
    def temp_files(self, mock_matches_data, mock_faculty_data, mock_funding_data):
        """Create temporary files with mock data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create matches file
            matches_file = Path(temp_dir) / "matches.json"
            with open(matches_file, 'w') as f:
                json.dump(mock_matches_data, f)
            
            # Create faculty file
            faculty_file = Path(temp_dir) / "faculty.json"
            with open(faculty_file, 'w') as f:
                json.dump(list(mock_faculty_data.values()), f)
            
            # Create funding file
            funding_file = Path(temp_dir) / "funding.json"
            with open(funding_file, 'w') as f:
                json.dump(list(mock_funding_data.values()), f)
            
            yield {
                'matches_file': str(matches_file),
                'faculty_file': str(faculty_file),
                'funding_file': str(funding_file)
            }
    
    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.llm_model == "test-gpt-4"
        assert agent.max_ideas_per_match == 3
        assert agent.enable_llm_integration is False
        assert isinstance(agent.variant_generator, ProposalVariantGenerator)
        assert isinstance(agent.budget_estimator, BudgetEstimator)
        assert isinstance(agent.timeline_estimator, TimelineEstimator)
    
    def test_load_matches(self, agent, temp_files):
        """Test loading matches from file."""
        matches = agent.load_matches(temp_files['matches_file'])
        
        assert len(matches) == 1
        assert matches[0]['match_id'] == "test_match_001"
        assert matches[0]['faculty_profile_id'] == "faculty_001"
    
    def test_load_faculty_and_funding_data(self, agent, temp_files):
        """Test loading faculty and funding reference data."""
        faculty_lookup, funding_lookup = agent.load_faculty_and_funding_data(
            temp_files['faculty_file'], temp_files['funding_file']
        )
        
        assert len(faculty_lookup) == 1
        assert len(funding_lookup) == 1
        assert "Dr. Test Faculty" in faculty_lookup
        assert "NIH-2024-AI-HEALTHCARE-001" in funding_lookup
    
    def test_generate_ideas_for_match(self, agent, mock_faculty_data, mock_funding_data):
        """Test generating research ideas for a faculty-funding match."""
        faculty_data = mock_faculty_data["faculty_001"]
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        match_score = 0.85
        
        ideas = agent.generate_ideas_for_match(faculty_data, funding_data, match_score)
        
        # Should generate 3 ideas (one for each variant)
        assert len(ideas) == 3
        
        # Check that all variant types are represented
        variant_types = {idea.variant_type for idea in ideas}
        expected_variants = {ProposalVariant.CONSERVATIVE, ProposalVariant.INNOVATIVE, ProposalVariant.STRETCH}
        assert variant_types == expected_variants
        
        # Verify each idea has required fields
        for idea in ideas:
            assert isinstance(idea, ResearchIdea)
            assert idea.title
            assert idea.research_question
            assert idea.objectives
            assert idea.timeline_months > 0
            assert idea.estimated_budget > 0
            assert 0 <= idea.innovation_level <= 1
            assert 0 <= idea.feasibility_score <= 1
            assert 0 <= idea.impact_potential <= 1
    
    def test_generate_single_idea_conservative(self, agent, mock_faculty_data, mock_funding_data):
        """Test generating a conservative research idea."""
        faculty_data = mock_faculty_data["faculty_001"]
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.CONSERVATIVE, 0.85
        )
        
        assert idea is not None
        assert idea.variant_type == ProposalVariant.CONSERVATIVE
        assert idea.innovation_level < 0.5  # Conservative should have lower innovation
        assert idea.feasibility_score > 0.7  # Conservative should have higher feasibility
        assert "Investigating" in idea.title or "Examining" in idea.title or "Analyzing" in idea.title
    
    def test_generate_single_idea_innovative(self, agent, mock_faculty_data, mock_funding_data):
        """Test generating an innovative research idea."""
        faculty_data = mock_faculty_data["faculty_001"]
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.INNOVATIVE, 0.85
        )
        
        assert idea is not None
        assert idea.variant_type == ProposalVariant.INNOVATIVE
        assert 0.4 < idea.innovation_level < 0.8  # Moderate innovation
        assert idea.hypothesis is not None  # Innovative should have hypothesis
    
    def test_generate_single_idea_stretch(self, agent, mock_faculty_data, mock_funding_data):
        """Test generating a stretch research idea."""
        faculty_data = mock_faculty_data["faculty_001"]
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.STRETCH, 0.85
        )
        
        assert idea is not None
        assert idea.variant_type == ProposalVariant.STRETCH
        assert idea.innovation_level > 0.7  # High innovation
        assert idea.hypothesis is not None  # Stretch should have hypothesis
        assert "Revolutionizing" in idea.title or "Pioneering" in idea.title or "Transforming" in idea.title
    
    def test_budget_estimation_varies_by_variant(self, agent, mock_faculty_data, mock_funding_data):
        """Test that budget estimation varies appropriately by variant type."""
        faculty_data = mock_faculty_data["faculty_001"]
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        conservative_idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.CONSERVATIVE, 0.85
        )
        innovative_idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.INNOVATIVE, 0.85
        )
        stretch_idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.STRETCH, 0.85
        )
        
        # Budget should generally increase: conservative < innovative < stretch
        assert conservative_idea.estimated_budget <= innovative_idea.estimated_budget <= stretch_idea.estimated_budget
    
    def test_timeline_estimation_varies_by_variant(self, agent, mock_faculty_data, mock_funding_data):
        """Test that timeline estimation varies appropriately by variant type."""
        faculty_data = mock_faculty_data["faculty_001"]
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        conservative_idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.CONSERVATIVE, 0.85
        )
        stretch_idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.STRETCH, 0.85
        )
        
        # Stretch projects should generally take longer than conservative
        assert conservative_idea.timeline_months <= stretch_idea.timeline_months
    
    def test_process_matches_batch(self, agent, temp_files):
        """Test batch processing of multiple matches."""
        matches_data = agent.load_matches(temp_files['matches_file'])
        faculty_lookup, funding_lookup = agent.load_faculty_and_funding_data(
            temp_files['faculty_file'], temp_files['funding_file']
        )
        
        match_ideas = agent.process_matches_batch(matches_data, faculty_lookup, funding_lookup)
        
        assert len(match_ideas) == 1
        assert "test_match_001" in match_ideas
        assert len(match_ideas["test_match_001"]) == 3  # 3 variants
    
    def test_save_and_load_ideas(self, agent, temp_files):
        """Test saving and loading generated ideas."""
        matches_data = agent.load_matches(temp_files['matches_file'])
        faculty_lookup, funding_lookup = agent.load_faculty_and_funding_data(
            temp_files['faculty_file'], temp_files['funding_file']
        )
        
        match_ideas = agent.process_matches_batch(matches_data, faculty_lookup, funding_lookup)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_ideas.json"
            saved_path = agent.save_ideas(match_ideas, str(output_file))
            
            assert saved_path.exists()
            
            # Load and verify saved data
            with open(saved_path, 'r') as f:
                saved_data = json.load(f)
            
            assert "test_match_001" in saved_data
            assert len(saved_data["test_match_001"]) == 3
            
            # Verify structure of saved ideas
            for idea_data in saved_data["test_match_001"]:
                assert "title" in idea_data
                assert "variant_type" in idea_data
                assert "research_question" in idea_data
                assert "estimated_budget" in idea_data
                assert "timeline_months" in idea_data
    
    def test_generation_statistics(self, agent, temp_files):
        """Test generation of statistics about the idea generation process."""
        matches_data = agent.load_matches(temp_files['matches_file'])
        faculty_lookup, funding_lookup = agent.load_faculty_and_funding_data(
            temp_files['faculty_file'], temp_files['funding_file']
        )
        
        match_ideas = agent.process_matches_batch(matches_data, faculty_lookup, funding_lookup)
        stats = agent.get_generation_statistics(match_ideas)
        
        assert stats['total_matches'] == 1
        assert stats['total_ideas'] == 3
        assert 'ideas_per_variant' in stats
        assert 'average_budget' in stats
        assert 'average_timeline' in stats
        assert 'budget_range' in stats
        assert 'timeline_range' in stats
        
        # Verify variant counts
        variant_counts = stats['ideas_per_variant']
        assert variant_counts['conservative'] == 1
        assert variant_counts['innovative'] == 1
        assert variant_counts['stretch'] == 1
    
    def test_run_idea_generation_a2a_success(self, agent, temp_files):
        """Test successful A2A idea generation process."""
        result = agent.run_idea_generation_a2a(
            temp_files['matches_file'],
            temp_files['faculty_file'],
            temp_files['funding_file']
        )
        
        assert result['success'] is True
        assert result['matches_processed'] == 1
        assert result['ideas_generated'] == 3
        assert 'ideas_file' in result
        assert 'statistics' in result
        assert 'processing_time_seconds' in result
    
    def test_run_idea_generation_a2a_no_matches(self, agent, temp_files):
        """Test A2A process with no matches."""
        # Create empty matches file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            empty_matches_file = f.name
        
        try:
            result = agent.run_idea_generation_a2a(
                empty_matches_file,
                temp_files['faculty_file'],
                temp_files['funding_file']
            )
            
            assert result['success'] is False
            assert 'No valid matches loaded' in result['error']
        finally:
            Path(empty_matches_file).unlink()
    
    def test_run_idea_generation_a2a_invalid_file(self, agent, temp_files):
        """Test A2A process with invalid file."""
        result = agent.run_idea_generation_a2a(
            "nonexistent_file.json",
            temp_files['faculty_file'],
            temp_files['funding_file']
        )
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_process_a2a_message_success(self, agent, temp_files):
        """Test processing A2A messages successfully."""
        message = A2AMessage(
            message_id="test_msg_001",
            source_agent=AgentType.MATCHER_AGENT,
            target_agent=AgentType.IDEA_AGENT,
            message_type=MessageType.REQUEST,
            payload={
                'matches_file': temp_files['matches_file'],
                'faculty_file': temp_files['faculty_file'],
                'funding_file': temp_files['funding_file']
            },
            timestamp=datetime.now()
        )
        
        response = agent.process_a2a_message(message)
        
        assert response.message_type == MessageType.RESPONSE
        assert response.source_agent == AgentType.IDEA_AGENT
        assert response.target_agent == AgentType.MATCHER_AGENT
        assert response.payload.get('success') is True
    
    def test_process_a2a_message_missing_parameters(self, agent):
        """Test processing A2A messages with missing parameters."""
        message = A2AMessage(
            message_id="test_msg_002",
            source_agent=AgentType.MATCHER_AGENT,
            target_agent=AgentType.IDEA_AGENT,
            message_type=MessageType.REQUEST,
            payload={
                'matches_file': 'test.json'
                # Missing faculty_file and funding_file
            },
            timestamp=datetime.now()
        )
        
        response = agent.process_a2a_message(message)
        
        assert response.message_type == MessageType.RESPONSE
        assert response.payload.get('success') is False
        assert 'are required' in response.payload.get('error', '')
    
    def test_empty_statistics(self, agent):
        """Test statistics generation with empty data."""
        stats = agent.get_generation_statistics({})
        
        assert stats['total_matches'] == 0
        assert stats['total_ideas'] == 0
        assert stats['average_budget'] == 0
        assert stats['average_timeline'] == 0
    
    @pytest.mark.parametrize("career_stage", [
        "graduate_student", "postdoc", "assistant_professor", 
        "associate_professor", "full_professor"
    ])
    def test_budget_varies_by_career_stage(self, agent, mock_faculty_data, mock_funding_data, career_stage):
        """Test that budget estimation varies appropriately by career stage."""
        faculty_data = mock_faculty_data["faculty_001"].copy()
        faculty_data['career_stage'] = career_stage
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.INNOVATIVE, 0.85
        )
        
        assert idea is not None
        assert idea.estimated_budget > 0
        
        # Budget should be reasonable for career stage
        if career_stage in ["graduate_student", "postdoc"]:
            assert idea.estimated_budget < Decimal('100000')
        elif career_stage == "full_professor":
            # Full professors can have higher budgets
            assert idea.estimated_budget >= Decimal('50000')
    
    @pytest.mark.parametrize("methodology", [
        ["experimental"], ["computational"], ["clinical"], ["theoretical"]
    ])
    def test_methodology_affects_estimates(self, agent, mock_faculty_data, mock_funding_data, methodology):
        """Test that different methodologies affect budget and timeline estimates."""
        faculty_data = mock_faculty_data["faculty_001"].copy()
        faculty_data['methodologies'] = methodology
        funding_data = mock_funding_data["NIH-2024-AI-HEALTHCARE-001"]
        
        idea = agent._generate_single_idea(
            faculty_data, funding_data, ProposalVariant.INNOVATIVE, 0.85
        )
        
        assert idea is not None
        assert idea.methodology == [ResearchMethodology(m) for m in methodology]
        
        # Clinical and experimental methodologies should generally have higher budgets
        if methodology[0] in ["clinical", "experimental"]:
            assert idea.estimated_budget > Decimal('75000')
        # Theoretical methodologies should generally have lower budgets
        elif methodology[0] == "theoretical":
            assert idea.estimated_budget < Decimal('200000')


class TestProposalVariantGenerator:
    """Test cases for ProposalVariantGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a ProposalVariantGenerator instance for testing."""
        return ProposalVariantGenerator()
    
    def test_generate_template_based_conservative(self, generator):
        """Test template-based generation for conservative variant."""
        content = generator._generate_template_based(
            ["machine learning"], ["healthcare AI"], ProposalVariant.CONSERVATIVE
        )
        
        assert content['title'].startswith(('Investigating', 'Examining', 'Analyzing'))
        assert content['research_question']
        assert content['objectives']
        assert len(content['objectives']) > 0
        assert content['literature_gap']
        assert content['variant_characteristics']['risk_level'] == 'low'
    
    def test_generate_template_based_stretch(self, generator):
        """Test template-based generation for stretch variant."""
        content = generator._generate_template_based(
            ["machine learning"], ["healthcare AI"], ProposalVariant.STRETCH
        )
        
        assert content['title'].startswith(('Revolutionizing', 'Pioneering', 'Transforming'))
        assert content['hypothesis'] is not None
        assert content['variant_characteristics']['risk_level'] == 'high'
        assert content['variant_characteristics']['novelty_factor'] == 0.9
    
    def test_calculate_innovation_metrics(self, generator):
        """Test calculation of innovation metrics."""
        metrics = generator.calculate_innovation_metrics(
            ProposalVariant.INNOVATIVE, 0.8, "assistant_professor"
        )
        
        assert 0 <= metrics['innovation_level'] <= 1
        assert 0 <= metrics['feasibility_score'] <= 1
        assert 0 <= metrics['impact_potential'] <= 1
        
        # Innovative should have moderate innovation level
        assert 0.4 < metrics['innovation_level'] < 0.8


class TestBudgetEstimator:
    """Test cases for BudgetEstimator."""
    
    @pytest.fixture
    def estimator(self):
        """Create a BudgetEstimator instance for testing."""
        return BudgetEstimator()
    
    def test_estimate_budget_by_career_stage(self, estimator):
        """Test budget estimation varies by career stage."""
        methodologies = [ResearchMethodology.EXPERIMENTAL]
        max_funding = Decimal('500000')
        
        # Test different career stages
        postdoc_budget = estimator.estimate_budget(
            ProposalVariant.INNOVATIVE, CareerStage.POSTDOC, methodologies, max_funding
        )
        
        full_prof_budget = estimator.estimate_budget(
            ProposalVariant.INNOVATIVE, CareerStage.FULL_PROFESSOR, methodologies, max_funding
        )
        
        # Full professor should generally get higher budget than postdoc
        assert full_prof_budget >= postdoc_budget
    
    def test_estimate_budget_by_variant(self, estimator):
        """Test budget estimation varies by variant type."""
        career_stage = CareerStage.ASSISTANT_PROFESSOR
        methodologies = [ResearchMethodology.EXPERIMENTAL]
        max_funding = Decimal('500000')
        
        conservative_budget = estimator.estimate_budget(
            ProposalVariant.CONSERVATIVE, career_stage, methodologies, max_funding
        )
        
        stretch_budget = estimator.estimate_budget(
            ProposalVariant.STRETCH, career_stage, methodologies, max_funding
        )
        
        # Stretch should have higher budget than conservative
        assert stretch_budget >= conservative_budget
    
    def test_generate_budget_breakdown(self, estimator):
        """Test generation of detailed budget breakdown."""
        total_budget = Decimal('100000')
        methodologies = ['experimental']
        
        breakdown = estimator.generate_budget_breakdown(
            total_budget, ProposalVariant.INNOVATIVE, methodologies
        )
        
        # Should have standard categories
        expected_categories = {'personnel', 'equipment', 'supplies', 'travel', 'indirect'}
        assert set(breakdown.keys()) == expected_categories
        
        # Total should approximately equal input budget
        total_allocated = sum(breakdown.values())
        assert abs(total_allocated - total_budget) < Decimal('1.00')  # Allow small rounding differences
        
        # All amounts should be positive
        assert all(amount >= 0 for amount in breakdown.values())


class TestTimelineEstimator:
    """Test cases for TimelineEstimator."""
    
    @pytest.fixture
    def estimator(self):
        """Create a TimelineEstimator instance for testing."""
        return TimelineEstimator()
    
    def test_estimate_timeline_by_variant(self, estimator):
        """Test timeline estimation varies by variant type."""
        methodologies = [ResearchMethodology.EXPERIMENTAL]
        max_duration = 60
        budget = Decimal('100000')
        
        conservative_timeline = estimator.estimate_timeline(
            ProposalVariant.CONSERVATIVE, methodologies, max_duration, budget
        )
        
        stretch_timeline = estimator.estimate_timeline(
            ProposalVariant.STRETCH, methodologies, max_duration, budget
        )
        
        # Stretch should take longer than conservative
        assert stretch_timeline >= conservative_timeline
        assert conservative_timeline >= 6  # Minimum reasonable timeline
        assert stretch_timeline <= max_duration  # Should not exceed maximum
    
    def test_generate_milestones(self, estimator):
        """Test generation of project milestones."""
        timeline_months = 24
        
        milestones = estimator.generate_milestones(timeline_months, ProposalVariant.INNOVATIVE)
        
        assert len(milestones) >= 2  # Should have at least 2 milestones
        assert all("Month" in milestone for milestone in milestones)
        assert all(milestone for milestone in milestones)  # No empty milestones
    
    def test_generate_deliverables(self, estimator):
        """Test generation of project deliverables."""
        methodologies = ['computational', 'experimental']
        
        deliverables = estimator.generate_deliverables(ProposalVariant.STRETCH, methodologies)
        
        assert len(deliverables) > 0
        assert "Comprehensive final report" in deliverables
        assert "Peer-reviewed publication(s)" in deliverables
        
        # Should include methodology-specific deliverables
        assert any("software" in d.lower() for d in deliverables)  # For computational
    
    def test_methodology_affects_timeline(self, estimator):
        """Test that different methodologies affect timeline estimates."""
        max_duration = 48
        budget = Decimal('150000')
        
        # Clinical should take longer than theoretical
        clinical_timeline = estimator.estimate_timeline(
            ProposalVariant.INNOVATIVE, [ResearchMethodology.CLINICAL], max_duration, budget
        )
        
        theoretical_timeline = estimator.estimate_timeline(
            ProposalVariant.INNOVATIVE, [ResearchMethodology.THEORETICAL], max_duration, budget
        )
        
        assert clinical_timeline >= theoretical_timeline