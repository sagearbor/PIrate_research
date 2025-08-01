"""
Idea Generation Agent for the Faculty Research Opportunity Notifier.

This agent generates research proposal ideas based on faculty-funding matches.
It creates three variants (conservative, innovative, stretch) with budget and
timeline estimates for each proposal.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date
from decimal import Decimal
import json
from pathlib import Path

from ..core.models import (
    FacultyProfile, FundingOpportunity, ResearchIdea, ProposalVariant,
    FacultyFundingMatch, ResearchMethodology, CareerStage
)
from ..core.proposal_variants import (
    ProposalVariantGenerator, BudgetEstimator, TimelineEstimator
)
from ..core.a2a_protocols import (
    A2AMessage, MessageType, AgentType,
    create_a2a_response
)

logger = logging.getLogger(__name__)


class IdeaGenerationAgent:
    """
    Agent responsible for generating research proposal ideas with multiple variants
    based on faculty-funding matches.
    """
    
    def __init__(self, 
                 llm_model: str = "mock-gpt-4",
                 max_ideas_per_match: int = 3,
                 enable_llm_integration: bool = False):
        """
        Initialize the Idea Generation Agent.
        
        Args:
            llm_model: LLM model identifier for idea generation
            max_ideas_per_match: Maximum number of ideas per match
            enable_llm_integration: Whether to use actual LLM (False for testing)
        """
        self.llm_model = llm_model
        self.max_ideas_per_match = max_ideas_per_match
        self.enable_llm_integration = enable_llm_integration
        
        self.variant_generator = ProposalVariantGenerator()
        self.budget_estimator = BudgetEstimator()
        self.timeline_estimator = TimelineEstimator()
        
        logger.info(f"Idea Generation Agent initialized with model {llm_model}")
    
    def load_matches(self, matches_file: str) -> List[Dict[str, Any]]:
        """Load faculty-funding matches from file."""
        try:
            with open(matches_file, 'r') as f:
                matches_data = json.load(f)
            
            logger.info(f"Loaded {len(matches_data)} matches from {matches_file}")
            return matches_data
            
        except Exception as e:
            logger.error(f"Error loading matches from {matches_file}: {e}")
            return []
    
    def load_faculty_and_funding_data(self, faculty_file: str, funding_file: str) -> tuple:
        """Load faculty and funding data for reference."""
        try:
            with open(faculty_file, 'r') as f:
                faculty_data = json.load(f)
            
            with open(funding_file, 'r') as f:
                funding_data = json.load(f)
            
            # Create lookup dictionaries
            faculty_lookup = {profile.get('profile_id', profile.get('name')): profile for profile in faculty_data}
            funding_lookup = {opp.get('opportunity_id'): opp for opp in funding_data}
            
            logger.info(f"Loaded {len(faculty_lookup)} faculty profiles and {len(funding_lookup)} funding opportunities")
            return faculty_lookup, funding_lookup
            
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
            return {}, {}
    
    def generate_ideas_for_match(self,
                               faculty_data: Dict[str, Any],
                               funding_data: Dict[str, Any],
                               match_score: float) -> List[ResearchIdea]:
        """
        Generate research ideas for a faculty-funding match.
        
        Args:
            faculty_data: Faculty profile data
            funding_data: Funding opportunity data
            match_score: Overall match score
            
        Returns:
            List of ResearchIdea objects (one per variant)
        """
        ideas = []
        
        # Generate each variant type
        for variant_type in [ProposalVariant.CONSERVATIVE, ProposalVariant.INNOVATIVE, ProposalVariant.STRETCH]:
            try:
                idea = self._generate_single_idea(faculty_data, funding_data, variant_type, match_score)
                if idea:
                    ideas.append(idea)
            except Exception as e:
                logger.warning(f"Error generating {variant_type.value} idea: {e}")
                continue
        
        return ideas
    
    def _generate_single_idea(self,
                            faculty_data: Dict[str, Any],
                            funding_data: Dict[str, Any],
                            variant_type: ProposalVariant,
                            match_score: float) -> Optional[ResearchIdea]:
        """Generate a single research idea for a specific variant type."""
        
        # Extract key information
        faculty_interests = faculty_data.get('research_interests', [])
        faculty_methodologies = faculty_data.get('methodologies', [])
        faculty_career_stage = faculty_data.get('career_stage', 'other')
        
        funding_areas = funding_data.get('research_areas', [])
        funding_keywords = funding_data.get('keywords', [])
        funding_max_budget = Decimal(str(funding_data.get('max_award_amount', '100000')))
        funding_duration = funding_data.get('project_duration_months', 24)
        
        # Generate idea content using variant generator
        idea_content = self.variant_generator.generate_idea_content(
            faculty_interests, funding_areas, variant_type, self.enable_llm_integration
        )
        
        # Estimate budget based on variant type and constraints
        estimated_budget = self.budget_estimator.estimate_budget(
            variant_type=variant_type,
            career_stage=CareerStage(faculty_career_stage),
            methodologies=[ResearchMethodology(m) for m in faculty_methodologies],
            max_funding=funding_max_budget,
            base_score=match_score
        )
        
        # Generate budget breakdown
        budget_breakdown = self.budget_estimator.generate_budget_breakdown(
            estimated_budget, variant_type, faculty_methodologies
        )
        
        # Estimate timeline
        timeline_months = self.timeline_estimator.estimate_timeline(
            variant_type=variant_type,
            methodologies=[ResearchMethodology(m) for m in faculty_methodologies],
            max_duration=funding_duration,
            budget=estimated_budget
        )
        
        # Generate milestones and deliverables
        milestones = self.timeline_estimator.generate_milestones(timeline_months, variant_type)
        deliverables = self.timeline_estimator.generate_deliverables(variant_type, faculty_methodologies)
        
        # Calculate innovation metrics
        innovation_metrics = self.variant_generator.calculate_innovation_metrics(
            variant_type, match_score, faculty_career_stage
        )
        
        # Create ResearchIdea object
        research_idea = ResearchIdea(
            title=idea_content['title'],
            variant_type=variant_type,
            research_question=idea_content['research_question'],
            hypothesis=idea_content.get('hypothesis'),
            methodology=[ResearchMethodology(m) for m in faculty_methodologies],
            objectives=idea_content['objectives'],
            timeline_months=timeline_months,
            milestones=milestones,
            deliverables=deliverables,
            estimated_budget=estimated_budget,
            budget_breakdown=budget_breakdown,
            innovation_level=innovation_metrics['innovation_level'],
            feasibility_score=innovation_metrics['feasibility_score'],
            impact_potential=innovation_metrics['impact_potential'],
            key_references=idea_content.get('key_references', []),
            literature_gap=idea_content.get('literature_gap'),
            llm_model=self.llm_model if self.enable_llm_integration else None
        )
        
        return research_idea
    
    def process_matches_batch(self,
                            matches_data: List[Dict[str, Any]],
                            faculty_lookup: Dict[str, Any],
                            funding_lookup: Dict[str, Any]) -> Dict[str, List[ResearchIdea]]:
        """
        Process multiple matches and generate ideas for each.
        
        Returns:
            Dictionary mapping match_id to list of research ideas
        """
        match_ideas = {}
        
        for match_data in matches_data:
            match_id = match_data.get('match_id')
            faculty_id = match_data.get('faculty_profile_id')
            funding_id = match_data.get('funding_opportunity_id')
            match_score = match_data.get('match_score', {}).get('total_score', 0.5)
            
            if not all([match_id, faculty_id, funding_id]):
                logger.warning(f"Incomplete match data: {match_data}")
                continue
            
            faculty_data = faculty_lookup.get(faculty_id)
            funding_data = funding_lookup.get(funding_id)
            
            if not faculty_data or not funding_data:
                logger.warning(f"Missing reference data for match {match_id}")
                continue
            
            try:
                ideas = self.generate_ideas_for_match(faculty_data, funding_data, match_score)
                match_ideas[match_id] = ideas
                
                logger.info(f"Generated {len(ideas)} ideas for match {match_id}")
                
            except Exception as e:
                logger.error(f"Error processing match {match_id}: {e}")
                continue
        
        return match_ideas
    
    def save_ideas(self, match_ideas: Dict[str, List[ResearchIdea]], output_file: str = None) -> Path:
        """Save generated ideas to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/research_ideas_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert ideas to serializable format
        ideas_data = {}
        for match_id, ideas in match_ideas.items():
            ideas_data[match_id] = []
            for idea in ideas:
                idea_dict = {
                    'title': idea.title,
                    'variant_type': idea.variant_type.value,
                    'research_question': idea.research_question,
                    'hypothesis': idea.hypothesis,
                    'methodology': [m.value for m in idea.methodology],
                    'objectives': idea.objectives,
                    'timeline_months': idea.timeline_months,
                    'milestones': idea.milestones,
                    'deliverables': idea.deliverables,
                    'estimated_budget': str(idea.estimated_budget),
                    'budget_breakdown': {k: str(v) for k, v in idea.budget_breakdown.items()},
                    'innovation_level': idea.innovation_level,
                    'feasibility_score': idea.feasibility_score,
                    'impact_potential': idea.impact_potential,
                    'key_references': idea.key_references,
                    'literature_gap': idea.literature_gap,
                    'generated_date': idea.generated_date.isoformat(),
                    'llm_model': idea.llm_model
                }
                ideas_data[match_id].append(idea_dict)
        
        with open(output_path, 'w') as f:
            json.dump(ideas_data, f, indent=2)
        
        logger.info(f"Saved ideas for {len(match_ideas)} matches to {output_path}")
        return output_path
    
    def get_generation_statistics(self, match_ideas: Dict[str, List[ResearchIdea]]) -> Dict[str, Any]:
        """Generate statistics about the idea generation process."""
        if not match_ideas:
            return {
                'total_matches': 0,
                'total_ideas': 0,
                'ideas_per_variant': {},
                'average_budget': 0,
                'average_timeline': 0
            }
        
        total_ideas = sum(len(ideas) for ideas in match_ideas.values())
        
        # Count ideas by variant
        variant_counts = {variant.value: 0 for variant in ProposalVariant}
        budgets = []
        timelines = []
        
        for ideas in match_ideas.values():
            for idea in ideas:
                variant_counts[idea.variant_type.value] += 1
                budgets.append(float(idea.estimated_budget))
                timelines.append(idea.timeline_months)
        
        return {
            'total_matches': len(match_ideas),
            'total_ideas': total_ideas,
            'ideas_per_variant': variant_counts,
            'average_budget': sum(budgets) / len(budgets) if budgets else 0,
            'average_timeline': sum(timelines) / len(timelines) if timelines else 0,
            'budget_range': {
                'min': min(budgets) if budgets else 0,
                'max': max(budgets) if budgets else 0
            },
            'timeline_range': {
                'min': min(timelines) if timelines else 0,
                'max': max(timelines) if timelines else 0
            }
        }
    
    def process_a2a_message(self, message: A2AMessage) -> A2AMessage:
        """Process A2A messages from other agents."""
        logger.info(f"Processing A2A message from {message.source_agent}")
        
        try:
            request_data = message.payload
            
            # Extract parameters from request
            matches_file = request_data.get('matches_file')
            faculty_file = request_data.get('faculty_file')
            funding_file = request_data.get('funding_file')
            
            if not all([matches_file, faculty_file, funding_file]):
                raise ValueError("matches_file, faculty_file, and funding_file are required")
            
            # Process idea generation request
            result = self.run_idea_generation_a2a(matches_file, faculty_file, funding_file)
            
            # Create response
            response = create_a2a_response(
                message,
                result,
                success=result.get('success', False)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing A2A message: {e}")
            error_response = create_a2a_response(
                message,
                {"error": str(e)},
                success=False
            )
            return error_response
    
    def run_idea_generation_a2a(self, matches_file: str, faculty_file: str, funding_file: str) -> Dict[str, Any]:
        """Run idea generation process for A2A communication."""
        start_time = datetime.now()
        
        try:
            # Load data
            matches_data = self.load_matches(matches_file)
            faculty_lookup, funding_lookup = self.load_faculty_and_funding_data(faculty_file, funding_file)
            
            if not matches_data:
                return {
                    'success': False,
                    'error': 'No valid matches loaded',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            if not faculty_lookup or not funding_lookup:
                return {
                    'success': False,
                    'error': 'Failed to load reference data',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            # Generate ideas
            match_ideas = self.process_matches_batch(matches_data, faculty_lookup, funding_lookup)
            
            # Save ideas
            ideas_file = self.save_ideas(match_ideas)
            
            # Generate statistics
            stats = self.get_generation_statistics(match_ideas)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'matches_processed': len(matches_data),
                'ideas_generated': stats['total_ideas'],
                'ideas_file': str(ideas_file),
                'statistics': stats,
                'processing_time_seconds': processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in idea generation process: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def run_idea_generation(self, matches_file: str, faculty_file: str, funding_file: str) -> Dict[str, Any]:
        """Run the complete idea generation process."""
        return self.run_idea_generation_a2a(matches_file, faculty_file, funding_file)


def main():
    """Main function for running the idea generation agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Idea Generation Agent')
    parser.add_argument('--matches-file', required=True, help='Faculty-funding matches file path')
    parser.add_argument('--faculty-file', required=True, help='Faculty data file path')
    parser.add_argument('--funding-file', required=True, help='Funding data file path')
    parser.add_argument('--llm-model', default='mock-gpt-4', help='LLM model to use')
    parser.add_argument('--enable-llm', action='store_true', help='Enable actual LLM integration')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = IdeaGenerationAgent(
        llm_model=args.llm_model,
        enable_llm_integration=args.enable_llm
    )
    
    # Run idea generation
    result = agent.run_idea_generation(args.matches_file, args.faculty_file, args.funding_file)
    
    if result['success']:
        print(f"Idea generation complete!")
        print(f"Processed {result['matches_processed']} matches")
        print(f"Generated {result['ideas_generated']} ideas")
        print(f"Results saved to: {result['ideas_file']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f} seconds")
        
        # Print statistics
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\nStatistics:")
            print(f"Ideas per variant: {stats['ideas_per_variant']}")
            print(f"Average budget: ${stats['average_budget']:,.2f}")
            print(f"Average timeline: {stats['average_timeline']:.1f} months")
    else:
        print(f"Idea generation failed: {result['error']}")


if __name__ == "__main__":
    main()