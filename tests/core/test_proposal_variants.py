"""
Test suite for the Proposal Variants module.

This module tests the ProposalVariantGenerator, BudgetEstimator, and TimelineEstimator
classes for generating different types of research proposals with appropriate
estimates and characteristics.
"""

import pytest
from decimal import Decimal

from src.core.proposal_variants import (
    ProposalVariantGenerator, BudgetEstimator, TimelineEstimator
)
from src.core.models import ProposalVariant, CareerStage, ResearchMethodology


class TestProposalVariantGenerator:
    """Test cases for ProposalVariantGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create a ProposalVariantGenerator instance for testing."""
        return ProposalVariantGenerator()
    
    @pytest.fixture
    def sample_interests(self):
        """Sample faculty research interests."""
        return ["machine learning", "healthcare informatics", "natural language processing"]
    
    @pytest.fixture
    def sample_funding_areas(self):
        """Sample funding areas."""
        return ["artificial intelligence", "healthcare AI", "clinical decision support"]
    
    def test_variant_templates_structure(self, generator):
        """Test that variant templates have correct structure."""
        templates = generator.VARIANT_TEMPLATES
        
        assert ProposalVariant.CONSERVATIVE in templates
        assert ProposalVariant.INNOVATIVE in templates
        assert ProposalVariant.STRETCH in templates
        
        for variant, template in templates.items():
            assert 'risk_level' in template
            assert 'novelty_factor' in template
            assert 'methodology_complexity' in template
            assert 'approach' in template
            
            # Check novelty factor ordering
            if variant == ProposalVariant.CONSERVATIVE:
                assert template['novelty_factor'] < 0.5
                assert template['risk_level'] == 'low'
            elif variant == ProposalVariant.INNOVATIVE:
                assert 0.4 < template['novelty_factor'] < 0.8
                assert template['risk_level'] == 'moderate'
            elif variant == ProposalVariant.STRETCH:
                assert template['novelty_factor'] > 0.8
                assert template['risk_level'] == 'high'
    
    def test_generate_idea_content_conservative(self, generator, sample_interests, sample_funding_areas):
        """Test generation of conservative proposal content."""
        content = generator.generate_idea_content(
            sample_interests, sample_funding_areas, ProposalVariant.CONSERVATIVE, use_llm=False
        )
        
        assert 'title' in content
        assert 'research_question' in content
        assert 'objectives' in content
        assert 'key_references' in content
        assert 'literature_gap' in content
        
        # Conservative characteristics
        assert content['title'].startswith(('Investigating', 'Examining', 'Analyzing'))
        assert content['hypothesis'] is None  # Conservative typically doesn't have hypothesis
        assert len(content['objectives']) == 3
        assert 'established' in content['research_question'] or 'proven' in content['research_question']
    
    def test_generate_idea_content_innovative(self, generator, sample_interests, sample_funding_areas):
        """Test generation of innovative proposal content."""
        content = generator.generate_idea_content(
            sample_interests, sample_funding_areas, ProposalVariant.INNOVATIVE, use_llm=False
        )
        
        assert content['title'].startswith(('Advancing', 'Developing', 'Enhancing'))
        assert content['hypothesis'] is not None  # Innovative should have hypothesis
        assert 'novel' in content['research_question'] or 'advance' in content['research_question']
        assert 'novel approaches' in content['hypothesis']
    
    def test_generate_idea_content_stretch(self, generator, sample_interests, sample_funding_areas):
        """Test generation of stretch proposal content."""
        content = generator.generate_idea_content(
            sample_interests, sample_funding_areas, ProposalVariant.STRETCH, use_llm=False
        )
        
        assert content['title'].startswith(('Revolutionizing', 'Pioneering', 'Transforming'))
        assert content['hypothesis'] is not None  # Stretch should have hypothesis
        assert 'breakthrough' in content['research_question'] or 'revolutionize' in content['research_question']
        assert 'breakthrough methodologies' in content['hypothesis']
    
    def test_generate_idea_content_with_llm_flag(self, generator, sample_interests, sample_funding_areas):
        """Test generation with LLM flag (should return template-based for now)."""
        content = generator.generate_idea_content(
            sample_interests, sample_funding_areas, ProposalVariant.INNOVATIVE, use_llm=True
        )
        
        # Should still work but indicate LLM not implemented
        assert 'title' in content
        assert content.get('llm_generated') is False
        assert 'not implemented' in content.get('note', '')
    
    def test_generate_idea_empty_inputs(self, generator):
        """Test generation with empty inputs."""
        content = generator.generate_idea_content(
            [], [], ProposalVariant.CONSERVATIVE, use_llm=False
        )
        
        # Should still generate content with fallback values
        assert 'title' in content
        assert 'research_question' in content
        assert content['title']  # Not empty
        assert content['research_question']  # Not empty
    
    def test_calculate_innovation_metrics_conservative(self, generator):
        """Test innovation metrics calculation for conservative variant."""
        metrics = generator.calculate_innovation_metrics(
            ProposalVariant.CONSERVATIVE, 0.8, "assistant_professor"
        )
        
        assert 0 <= metrics['innovation_level'] <= 1
        assert 0 <= metrics['feasibility_score'] <= 1
        assert 0 <= metrics['impact_potential'] <= 1
        
        # Conservative should have low innovation, high feasibility
        assert metrics['innovation_level'] < 0.5
        assert metrics['feasibility_score'] > 0.7
    
    def test_calculate_innovation_metrics_stretch(self, generator):
        """Test innovation metrics calculation for stretch variant."""
        metrics = generator.calculate_innovation_metrics(
            ProposalVariant.STRETCH, 0.6, "full_professor"
        )
        
        # Stretch should have high innovation, lower feasibility
        assert metrics['innovation_level'] > 0.7
        assert metrics['feasibility_score'] < 0.7
        assert metrics['impact_potential'] > 0.8
    
    def test_calculate_innovation_metrics_career_stage_adjustment(self, generator):
        """Test that career stage affects innovation metrics."""
        # Graduate student
        grad_metrics = generator.calculate_innovation_metrics(
            ProposalVariant.INNOVATIVE, 0.7, "graduate_student"
        )
        
        # Full professor
        prof_metrics = generator.calculate_innovation_metrics(
            ProposalVariant.INNOVATIVE, 0.7, "full_professor"
        )
        
        # Full professor should have higher feasibility due to experience
        assert prof_metrics['feasibility_score'] >= grad_metrics['feasibility_score']
    
    def test_calculate_innovation_metrics_match_score_adjustment(self, generator):
        """Test that match score affects metrics."""
        low_match_metrics = generator.calculate_innovation_metrics(
            ProposalVariant.INNOVATIVE, 0.3, "assistant_professor"
        )
        
        high_match_metrics = generator.calculate_innovation_metrics(
            ProposalVariant.INNOVATIVE, 0.9, "assistant_professor"
        )
        
        # Higher match score should lead to higher feasibility
        assert high_match_metrics['feasibility_score'] >= low_match_metrics['feasibility_score']


class TestBudgetEstimator:
    """Test cases for BudgetEstimator."""
    
    @pytest.fixture
    def estimator(self):
        """Create a BudgetEstimator instance for testing."""
        return BudgetEstimator()
    
    def test_career_stage_budgets_structure(self, estimator):
        """Test that career stage budgets are properly structured."""
        budgets = estimator.CAREER_STAGE_BUDGETS
        
        # Should have all career stages
        expected_stages = {
            CareerStage.GRADUATE_STUDENT, CareerStage.POSTDOC,
            CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR,
            CareerStage.FULL_PROFESSOR, CareerStage.RESEARCH_SCIENTIST,
            CareerStage.OTHER
        }
        
        assert set(budgets.keys()) >= expected_stages
        
        # Check budget ranges increase with career level
        assert budgets[CareerStage.GRADUATE_STUDENT]['max'] < budgets[CareerStage.FULL_PROFESSOR]['max']
        assert budgets[CareerStage.POSTDOC]['max'] < budgets[CareerStage.ASSOCIATE_PROFESSOR]['max']
        
        # All ranges should have min < max
        for stage, budget_range in budgets.items():
            assert budget_range['min'] < budget_range['max']
            assert budget_range['min'] > 0
    
    def test_variant_multipliers(self, estimator):
        """Test that variant multipliers are properly ordered."""
        multipliers = estimator.VARIANT_MULTIPLIERS
        
        assert multipliers[ProposalVariant.CONSERVATIVE] < multipliers[ProposalVariant.INNOVATIVE]
        assert multipliers[ProposalVariant.INNOVATIVE] < multipliers[ProposalVariant.STRETCH]
        
        # All multipliers should be positive
        assert all(m > 0 for m in multipliers.values())
    
    def test_methodology_multipliers(self, estimator):
        """Test that methodology multipliers make sense."""
        multipliers = estimator.METHODOLOGY_MULTIPLIERS
        
        # Clinical and experimental should be more expensive than theoretical
        assert multipliers[ResearchMethodology.CLINICAL] > multipliers[ResearchMethodology.THEORETICAL]
        assert multipliers[ResearchMethodology.EXPERIMENTAL] > multipliers[ResearchMethodology.THEORETICAL]
        
        # Meta-analysis should be relatively inexpensive
        assert multipliers[ResearchMethodology.META_ANALYSIS] < 1.0
        
        # All multipliers should be positive
        assert all(m > 0 for m in multipliers.values())
    
    def test_estimate_budget_basic(self, estimator):
        """Test basic budget estimation functionality."""
        budget = estimator.estimate_budget(
            variant_type=ProposalVariant.INNOVATIVE,
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            methodologies=[ResearchMethodology.EXPERIMENTAL],
            max_funding=Decimal('500000'),
            base_score=0.7
        )
        
        assert isinstance(budget, Decimal)
        assert budget > 0
        assert budget <= Decimal('500000')  # Should not exceed max funding
    
    def test_estimate_budget_career_stage_effect(self, estimator):
        """Test that career stage affects budget estimation."""
        common_params = {
            'variant_type': ProposalVariant.INNOVATIVE,
            'methodologies': [ResearchMethodology.EXPERIMENTAL],
            'max_funding': Decimal('1000000'),
            'base_score': 0.7
        }
        
        grad_budget = estimator.estimate_budget(
            career_stage=CareerStage.GRADUATE_STUDENT, **common_params
        )
        
        prof_budget = estimator.estimate_budget(
            career_stage=CareerStage.FULL_PROFESSOR, **common_params
        )
        
        # Full professor should get higher budget than graduate student
        assert prof_budget > grad_budget
    
    def test_estimate_budget_variant_effect(self, estimator):
        """Test that variant type affects budget estimation."""
        common_params = {
            'career_stage': CareerStage.ASSOCIATE_PROFESSOR,
            'methodologies': [ResearchMethodology.EXPERIMENTAL],
            'max_funding': Decimal('500000'),
            'base_score': 0.7
        }
        
        conservative_budget = estimator.estimate_budget(
            variant_type=ProposalVariant.CONSERVATIVE, **common_params
        )
        
        stretch_budget = estimator.estimate_budget(
            variant_type=ProposalVariant.STRETCH, **common_params
        )
        
        # Stretch should get higher budget than conservative
        assert stretch_budget > conservative_budget
    
    def test_estimate_budget_methodology_effect(self, estimator):
        """Test that methodology affects budget estimation."""
        common_params = {
            'variant_type': ProposalVariant.INNOVATIVE,
            'career_stage': CareerStage.ASSISTANT_PROFESSOR,
            'max_funding': Decimal('300000'),
            'base_score': 0.7
        }
        
        theoretical_budget = estimator.estimate_budget(
            methodologies=[ResearchMethodology.THEORETICAL], **common_params
        )
        
        clinical_budget = estimator.estimate_budget(
            methodologies=[ResearchMethodology.CLINICAL], **common_params
        )
        
        # Clinical should be more expensive than theoretical
        assert clinical_budget > theoretical_budget
    
    def test_estimate_budget_max_funding_constraint(self, estimator):
        """Test that budget respects max funding constraint."""
        budget = estimator.estimate_budget(
            variant_type=ProposalVariant.STRETCH,
            career_stage=CareerStage.FULL_PROFESSOR,
            methodologies=[ResearchMethodology.CLINICAL],
            max_funding=Decimal('50000'),  # Very low max
            base_score=0.9
        )
        
        assert budget <= Decimal('50000')
        assert budget > 0  # Should still be positive
    
    def test_generate_budget_breakdown_structure(self, estimator):
        """Test that budget breakdown has correct structure."""
        breakdown = estimator.generate_budget_breakdown(
            total_budget=Decimal('100000'),
            variant_type=ProposalVariant.INNOVATIVE,
            methodologies=['experimental']
        )
        
        expected_categories = {'personnel', 'equipment', 'supplies', 'travel', 'indirect'}
        assert set(breakdown.keys()) == expected_categories
        
        # All amounts should be positive
        assert all(amount >= 0 for amount in breakdown.values())
        
        # Total should approximately equal input budget
        total_allocated = sum(breakdown.values())
        assert abs(total_allocated - Decimal('100000')) < Decimal('0.01')
    
    def test_generate_budget_breakdown_variant_differences(self, estimator):
        """Test that budget breakdown varies by variant type."""
        total_budget = Decimal('200000')
        methodologies = ['experimental']
        
        conservative_breakdown = estimator.generate_budget_breakdown(
            total_budget, ProposalVariant.CONSERVATIVE, methodologies
        )
        
        stretch_breakdown = estimator.generate_budget_breakdown(
            total_budget, ProposalVariant.STRETCH, methodologies
        )
        
        # Stretch should allocate more to equipment and supplies, less to personnel
        assert stretch_breakdown['equipment'] >= conservative_breakdown['equipment']
        assert stretch_breakdown['personnel'] <= conservative_breakdown['personnel']
    
    def test_generate_budget_breakdown_methodology_effect(self, estimator):
        """Test that budget breakdown varies by methodology."""
        total_budget = Decimal('150000')
        
        computational_breakdown = estimator.generate_budget_breakdown(
            total_budget, ProposalVariant.INNOVATIVE, ['computational']
        )
        
        clinical_breakdown = estimator.generate_budget_breakdown(
            total_budget, ProposalVariant.INNOVATIVE, ['clinical']
        )
        
        # Different methodologies should have different allocations
        # (exact differences depend on implementation, so just check they're different)
        assert computational_breakdown != clinical_breakdown


class TestTimelineEstimator:
    """Test cases for TimelineEstimator."""
    
    @pytest.fixture
    def estimator(self):
        """Create a TimelineEstimator instance for testing."""
        return TimelineEstimator()
    
    def test_variant_timelines_structure(self, estimator):
        """Test that variant timelines are properly structured."""
        timelines = estimator.VARIANT_TIMELINES
        
        assert ProposalVariant.CONSERVATIVE in timelines
        assert ProposalVariant.INNOVATIVE in timelines
        assert ProposalVariant.STRETCH in timelines
        
        # Check that timelines increase with complexity
        conservative_max = timelines[ProposalVariant.CONSERVATIVE]['max']
        innovative_max = timelines[ProposalVariant.INNOVATIVE]['max']
        stretch_max = timelines[ProposalVariant.STRETCH]['max']
        
        assert conservative_max <= innovative_max <= stretch_max
        
        # All ranges should have min < max
        for variant, timeline_range in timelines.items():
            assert timeline_range['min'] < timeline_range['max']
            assert timeline_range['min'] > 0
    
    def test_methodology_adjustments_structure(self, estimator):
        """Test that methodology adjustments are reasonable."""
        adjustments = estimator.METHODOLOGY_ADJUSTMENTS
        
        # Clinical should add more time than theoretical
        assert adjustments[ResearchMethodology.CLINICAL] > adjustments[ResearchMethodology.THEORETICAL]
        
        # Experimental should add more time than computational
        assert adjustments[ResearchMethodology.EXPERIMENTAL] > adjustments[ResearchMethodology.COMPUTATIONAL]
        
        # Meta-analysis should reduce time
        assert adjustments[ResearchMethodology.META_ANALYSIS] < 0
    
    def test_estimate_timeline_basic(self, estimator):
        """Test basic timeline estimation functionality."""
        timeline = estimator.estimate_timeline(
            variant_type=ProposalVariant.INNOVATIVE,
            methodologies=[ResearchMethodology.EXPERIMENTAL],
            max_duration=48,
            budget=Decimal('150000')
        )
        
        assert isinstance(timeline, int)
        assert timeline >= 6  # Minimum reasonable timeline
        assert timeline <= 48  # Should not exceed max duration
    
    def test_estimate_timeline_variant_effect(self, estimator):
        """Test that variant type affects timeline estimation."""
        common_params = {
            'methodologies': [ResearchMethodology.EXPERIMENTAL],
            'max_duration': 60,
            'budget': Decimal('200000')
        }
        
        conservative_timeline = estimator.estimate_timeline(
            variant_type=ProposalVariant.CONSERVATIVE, **common_params
        )
        
        stretch_timeline = estimator.estimate_timeline(
            variant_type=ProposalVariant.STRETCH, **common_params
        )
        
        # Stretch should take longer than conservative
        assert stretch_timeline >= conservative_timeline
    
    def test_estimate_timeline_methodology_effect(self, estimator):
        """Test that methodology affects timeline estimation."""
        common_params = {
            'variant_type': ProposalVariant.INNOVATIVE,
            'max_duration': 48,
            'budget': Decimal('150000')
        }
        
        theoretical_timeline = estimator.estimate_timeline(
            methodologies=[ResearchMethodology.THEORETICAL], **common_params
        )
        
        clinical_timeline = estimator.estimate_timeline(
            methodologies=[ResearchMethodology.CLINICAL], **common_params
        )
        
        # Clinical should take longer than theoretical
        assert clinical_timeline >= theoretical_timeline
    
    def test_estimate_timeline_budget_effect(self, estimator):
        """Test that budget affects timeline estimation."""
        common_params = {
            'variant_type': ProposalVariant.INNOVATIVE,
            'methodologies': [ResearchMethodology.EXPERIMENTAL],
            'max_duration': 60
        }
        
        low_budget_timeline = estimator.estimate_timeline(
            budget=Decimal('25000'), **common_params
        )
        
        high_budget_timeline = estimator.estimate_timeline(
            budget=Decimal('750000'), **common_params
        )
        
        # Higher budget should generally lead to longer timeline
        assert high_budget_timeline >= low_budget_timeline
    
    def test_estimate_timeline_max_duration_constraint(self, estimator):
        """Test that timeline respects max duration constraint."""
        timeline = estimator.estimate_timeline(
            variant_type=ProposalVariant.STRETCH,
            methodologies=[ResearchMethodology.CLINICAL],
            max_duration=12,  # Very short max
            budget=Decimal('500000')
        )
        
        assert timeline <= 12
        assert timeline >= 6  # Should still be reasonable minimum
    
    def test_generate_milestones_basic(self, estimator):
        """Test basic milestone generation."""
        milestones = estimator.generate_milestones(24, ProposalVariant.INNOVATIVE)
        
        assert len(milestones) >= 2  # Should have at least 2 milestones
        assert all(isinstance(milestone, str) for milestone in milestones)
        assert all("Month" in milestone for milestone in milestones)
        assert all(milestone.strip() for milestone in milestones)  # No empty milestones
    
    def test_generate_milestones_variant_differences(self, estimator):
        """Test that milestones vary by variant type."""
        conservative_milestones = estimator.generate_milestones(18, ProposalVariant.CONSERVATIVE)
        stretch_milestones = estimator.generate_milestones(36, ProposalVariant.STRETCH)
        
        # Content should be different
        assert conservative_milestones != stretch_milestones
        
        # Stretch should have more complex milestones
        assert len(stretch_milestones) >= len(conservative_milestones)
    
    def test_generate_milestones_timeline_scaling(self, estimator):
        """Test that milestone count scales with timeline."""
        short_milestones = estimator.generate_milestones(12, ProposalVariant.INNOVATIVE)
        long_milestones = estimator.generate_milestones(48, ProposalVariant.INNOVATIVE)
        
        # Longer timelines should have more milestones (or at least not fewer)
        assert len(long_milestones) >= len(short_milestones)
    
    def test_generate_deliverables_basic(self, estimator):
        """Test basic deliverable generation."""
        deliverables = estimator.generate_deliverables(
            ProposalVariant.INNOVATIVE, ['experimental']
        )
        
        assert len(deliverables) > 0
        assert all(isinstance(deliverable, str) for deliverable in deliverables)
        assert all(deliverable.strip() for deliverable in deliverables)  # No empty deliverables
        
        # Should include standard deliverables
        deliverable_text = ' '.join(deliverables).lower()
        assert 'report' in deliverable_text
        assert 'publication' in deliverable_text
    
    def test_generate_deliverables_variant_differences(self, estimator):
        """Test that deliverables vary by variant type."""
        conservative_deliverables = estimator.generate_deliverables(
            ProposalVariant.CONSERVATIVE, ['experimental']
        )
        
        stretch_deliverables = estimator.generate_deliverables(
            ProposalVariant.STRETCH, ['experimental']
        )
        
        # Stretch should have more ambitious deliverables
        assert len(stretch_deliverables) >= len(conservative_deliverables)
        
        # Stretch should include things like patents, prototypes
        stretch_text = ' '.join(stretch_deliverables).lower()
        assert any(word in stretch_text for word in ['prototype', 'patent', 'commercialization'])
    
    def test_generate_deliverables_methodology_specific(self, estimator):
        """Test that deliverables include methodology-specific items."""
        computational_deliverables = estimator.generate_deliverables(
            ProposalVariant.INNOVATIVE, ['computational']
        )
        
        clinical_deliverables = estimator.generate_deliverables(
            ProposalVariant.INNOVATIVE, ['clinical']
        )
        
        # Computational should include software
        comp_text = ' '.join(computational_deliverables).lower()
        assert 'software' in comp_text
        
        # Clinical should include protocol
        clinical_text = ' '.join(clinical_deliverables).lower()
        assert 'protocol' in clinical_text or 'trial' in clinical_text


class TestIntegration:
    """Integration tests for the proposal variants module."""
    
    def test_full_proposal_generation_workflow(self):
        """Test complete workflow of proposal generation."""
        generator = ProposalVariantGenerator()
        budget_estimator = BudgetEstimator()
        timeline_estimator = TimelineEstimator()
        
        # Generate idea content
        content = generator.generate_idea_content(
            faculty_interests=["machine learning", "healthcare"],
            funding_areas=["AI in medicine", "clinical decision support"],
            variant_type=ProposalVariant.INNOVATIVE,
            use_llm=False
        )
        
        # Estimate budget
        budget = budget_estimator.estimate_budget(
            variant_type=ProposalVariant.INNOVATIVE,
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            methodologies=[ResearchMethodology.EXPERIMENTAL, ResearchMethodology.COMPUTATIONAL],
            max_funding=Decimal('300000'),
            base_score=0.8
        )
        
        # Generate budget breakdown
        budget_breakdown = budget_estimator.generate_budget_breakdown(
            budget, ProposalVariant.INNOVATIVE, ['experimental', 'computational']
        )
        
        # Estimate timeline
        timeline = timeline_estimator.estimate_timeline(
            variant_type=ProposalVariant.INNOVATIVE,
            methodologies=[ResearchMethodology.EXPERIMENTAL, ResearchMethodology.COMPUTATIONAL],
            max_duration=36,
            budget=budget
        )
        
        # Generate milestones and deliverables
        milestones = timeline_estimator.generate_milestones(timeline, ProposalVariant.INNOVATIVE)
        deliverables = timeline_estimator.generate_deliverables(
            ProposalVariant.INNOVATIVE, ['experimental', 'computational']
        )
        
        # Innovation metrics
        metrics = generator.calculate_innovation_metrics(
            ProposalVariant.INNOVATIVE, 0.8, "assistant_professor"
        )
        
        # Verify all components work together
        assert content['title']
        assert content['research_question']
        assert budget > 0
        assert len(budget_breakdown) == 5  # All budget categories
        assert timeline > 0
        assert len(milestones) >= 2
        assert len(deliverables) >= 3
        assert all(0 <= v <= 1 for v in metrics.values())
        
        # Verify consistency
        assert timeline <= 36  # Respects max duration
        assert budget <= Decimal('300000')  # Respects max funding
        
        # Budget breakdown should sum to total budget
        total_allocated = sum(budget_breakdown.values())
        assert abs(total_allocated - budget) < Decimal('0.01')
    
    @pytest.mark.parametrize("variant", [
        ProposalVariant.CONSERVATIVE,
        ProposalVariant.INNOVATIVE,
        ProposalVariant.STRETCH
    ])
    def test_variant_consistency(self, variant):
        """Test that all components produce consistent results for each variant."""
        generator = ProposalVariantGenerator()
        budget_estimator = BudgetEstimator()
        timeline_estimator = TimelineEstimator()
        
        # Generate content for variant
        content = generator.generate_idea_content(
            ["data science"], ["healthcare analytics"], variant, use_llm=False
        )
        
        # Estimate budget and timeline
        budget = budget_estimator.estimate_budget(
            variant, CareerStage.ASSOCIATE_PROFESSOR,
            [ResearchMethodology.COMPUTATIONAL], Decimal('200000'), 0.7
        )
        
        timeline = timeline_estimator.estimate_timeline(
            variant, [ResearchMethodology.COMPUTATIONAL], 48, budget
        )
        
        metrics = generator.calculate_innovation_metrics(variant, 0.7, "associate_professor")
        
        # Verify variant-specific characteristics
        if variant == ProposalVariant.CONSERVATIVE:
            assert metrics['innovation_level'] < 0.5
            assert metrics['feasibility_score'] > 0.7
            assert content['hypothesis'] is None
        elif variant == ProposalVariant.STRETCH:
            assert metrics['innovation_level'] > 0.7
            assert metrics['impact_potential'] > 0.8
            assert content['hypothesis'] is not None
            
        # All variants should produce valid results
        assert content['title']
        assert budget > 0
        assert timeline > 0