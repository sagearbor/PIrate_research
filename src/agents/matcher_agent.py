"""
Matcher Agent for the Faculty Research Opportunity Notifier.

This agent is responsible for matching faculty profiles with funding opportunities
using multi-dimensional scoring algorithms. It processes ingested data and generates
ranked matches based on research alignment, methodology compatibility, career stage
fit, deadline urgency, and budget alignment.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from pathlib import Path
from datetime import datetime
import json
from dataclasses import asdict

from ..core.models import (
    FacultyProfile, FundingOpportunity, FacultyFundingMatch, 
    MatchScore, MatchStatus, CareerStage, ResearchMethodology
)
from ..core.scoring_models import MatchingEngine, ScoringConfiguration
from ..core.a2a_protocols import (
    A2AMessage, MessageType, AgentType,
    create_a2a_response
)

logger = logging.getLogger(__name__)


class MatcherAgent:
    """
    Agent responsible for matching faculty profiles with funding opportunities
    using multi-dimensional scoring algorithms.
    """
    
    def __init__(self, 
                 scoring_config: ScoringConfiguration = None,
                 min_score_threshold: float = 0.3,
                 max_matches_per_faculty: int = 10):
        """
        Initialize the Matcher Agent.
        
        Args:
            scoring_config: Configuration for scoring algorithms
            min_score_threshold: Minimum score for considering a match
            max_matches_per_faculty: Maximum number of matches per faculty member
        """
        self.scoring_config = scoring_config or ScoringConfiguration()
        self.matching_engine = MatchingEngine(self.scoring_config)
        self.min_score_threshold = min_score_threshold
        self.max_matches_per_faculty = max_matches_per_faculty
        self.last_run = None
        
        logger.info(f"Matcher Agent initialized with threshold {min_score_threshold}")
    
    def load_faculty_data(self, data_file: str) -> List[FacultyProfile]:
        """Load faculty profiles from processed data file."""
        try:
            with open(data_file, 'r') as f:
                faculty_data = json.load(f)
            
            profiles = []
            for data in faculty_data:
                try:
                    # Convert string enums back to enum objects
                    if 'career_stage' in data:
                        data['career_stage'] = CareerStage(data['career_stage'])
                    
                    if 'methodologies' in data:
                        data['methodologies'] = [ResearchMethodology(m) for m in data['methodologies']]
                    
                    # Handle publications if present
                    if 'publications' in data and isinstance(data['publications'], list):
                        from ..core.models import Publication
                        publications = []
                        for pub_data in data['publications']:
                            if isinstance(pub_data, dict):
                                publications.append(Publication(**pub_data))
                        data['publications'] = publications
                    
                    profile = FacultyProfile(**data)
                    profiles.append(profile)
                    
                except Exception as e:
                    logger.warning(f"Error parsing faculty profile: {e}")
                    continue
            
            logger.info(f"Loaded {len(profiles)} faculty profiles from {data_file}")
            return profiles
            
        except Exception as e:
            logger.error(f"Error loading faculty data from {data_file}: {e}")
            return []
    
    def load_funding_data(self, data_file: str) -> List[FundingOpportunity]:
        """Load funding opportunities from processed data file."""
        try:
            with open(data_file, 'r') as f:
                funding_data = json.load(f)
            
            opportunities = []
            for data in funding_data:
                try:
                    # Convert string enums back to enum objects
                    if 'eligible_career_stages' in data:
                        data['eligible_career_stages'] = [CareerStage(stage) for stage in data['eligible_career_stages']]
                    
                    if 'preferred_methodologies' in data:
                        data['preferred_methodologies'] = [ResearchMethodology(m) for m in data['preferred_methodologies']]
                    
                    # Convert date strings to date objects
                    if 'deadline' in data and isinstance(data['deadline'], str):
                        from datetime import date
                        data['deadline'] = date.fromisoformat(data['deadline'])
                    
                    if 'award_start_date' in data and isinstance(data['award_start_date'], str):
                        from datetime import date
                        data['award_start_date'] = date.fromisoformat(data['award_start_date'])
                    
                    # Convert decimal strings to Decimal objects
                    from decimal import Decimal
                    for field in ['total_budget', 'max_award_amount', 'min_award_amount']:
                        if field in data and data[field] is not None:
                            data[field] = Decimal(str(data[field]))
                    
                    opportunity = FundingOpportunity(**data)
                    opportunities.append(opportunity)
                    
                except Exception as e:
                    logger.warning(f"Error parsing funding opportunity: {e}")
                    continue
            
            logger.info(f"Loaded {len(opportunities)} funding opportunities from {data_file}")
            return opportunities
            
        except Exception as e:
            logger.error(f"Error loading funding data from {data_file}: {e}")
            return []
    
    def generate_matches(self, 
                        faculty_profiles: List[FacultyProfile],
                        funding_opportunities: List[FundingOpportunity]) -> List[FacultyFundingMatch]:
        """
        Generate matches between faculty and funding opportunities.
        
        Args:
            faculty_profiles: List of faculty profiles
            funding_opportunities: List of funding opportunities
            
        Returns:
            List of FacultyFundingMatch objects
        """
        logger.info(f"Generating matches for {len(faculty_profiles)} faculty and {len(funding_opportunities)} opportunities")
        
        # Get all potential matches above threshold
        raw_matches = self.matching_engine.batch_score_matches(
            faculty_profiles, 
            funding_opportunities,
            self.min_score_threshold
        )
        
        # Organize matches by faculty
        faculty_matches = {}
        for faculty, funding, score in raw_matches:
            faculty_id = faculty.profile_id or faculty.name
            
            if faculty_id not in faculty_matches:
                faculty_matches[faculty_id] = []
            
            faculty_matches[faculty_id].append((faculty, funding, score))
        
        # Limit matches per faculty and create FacultyFundingMatch objects
        matches = []
        for faculty_id, faculty_match_list in faculty_matches.items():
            # Sort by score and limit
            faculty_match_list.sort(key=lambda x: x[2].total_score, reverse=True)
            top_matches = faculty_match_list[:self.max_matches_per_faculty]
            
            for faculty, funding, score in top_matches:
                match_id = f"match_{faculty_id}_{funding.opportunity_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                match = FacultyFundingMatch(
                    match_id=match_id,
                    faculty_profile_id=faculty.profile_id or faculty.name,
                    funding_opportunity_id=funding.opportunity_id,
                    match_score=score,
                    status=MatchStatus.PENDING
                )
                
                matches.append(match)
        
        self.last_run = datetime.now()
        logger.info(f"Generated {len(matches)} matches above threshold {self.min_score_threshold}")
        
        return matches
    
    def filter_matches_by_criteria(self, 
                                 matches: List[FacultyFundingMatch],
                                 min_research_alignment: float = None,
                                 min_career_stage_fit: float = None,
                                 max_deadline_days: int = None) -> List[FacultyFundingMatch]:
        """
        Filter matches based on additional criteria.
        
        Args:
            matches: List of matches to filter
            min_research_alignment: Minimum research alignment score
            min_career_stage_fit: Minimum career stage fit score
            max_deadline_days: Maximum days until deadline
            
        Returns:
            Filtered list of matches
        """
        filtered_matches = []
        
        for match in matches:
            # Check research alignment
            if min_research_alignment and match.match_score.research_alignment < min_research_alignment:
                continue
            
            # Check career stage fit
            if min_career_stage_fit and match.match_score.career_stage_fit < min_career_stage_fit:
                continue
            
            # Check deadline (would need access to funding data for this)
            # This is a simplified version - in practice, you'd want to load the funding data
            if max_deadline_days is not None:
                # Skip deadline filtering for now - would require loading funding data
                pass
            
            filtered_matches.append(match)
        
        logger.info(f"Filtered {len(matches)} matches down to {len(filtered_matches)}")
        return filtered_matches
    
    def save_matches(self, matches: List[FacultyFundingMatch], output_file: str = None) -> Path:
        """Save generated matches to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/faculty_funding_matches_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert matches to serializable format
        matches_data = []
        for match in matches:
            match_dict = {
                'match_id': match.match_id,
                'faculty_profile_id': match.faculty_profile_id,
                'funding_opportunity_id': match.funding_opportunity_id,
                'match_score': {
                    'total_score': match.match_score.total_score,
                    'research_alignment': match.match_score.research_alignment,
                    'methodology_match': match.match_score.methodology_match,
                    'career_stage_fit': match.match_score.career_stage_fit,
                    'deadline_urgency': match.match_score.deadline_urgency,
                    'budget_alignment': match.match_score.budget_alignment,
                    'scoring_algorithm': match.match_score.scoring_algorithm,
                    'calculated_date': match.match_score.calculated_date.isoformat()
                },
                'status': match.status.value,
                'notification_sent': match.notification_sent,
                'faculty_response': match.faculty_response,
                'created_date': match.created_date.isoformat(),
                'last_updated': match.last_updated.isoformat()
            }
            matches_data.append(match_dict)
        
        with open(output_path, 'w') as f:
            json.dump(matches_data, f, indent=2)
        
        logger.info(f"Saved {len(matches)} matches to {output_path}")
        return output_path
    
    def get_match_statistics(self, matches: List[FacultyFundingMatch]) -> Dict[str, Any]:
        """Generate statistics about the generated matches."""
        if not matches:
            return {
                'total_matches': 0,
                'average_score': 0.0,
                'score_distribution': {},
                'top_matches': []
            }
        
        scores = [match.match_score.total_score for match in matches]
        
        # Score distribution
        score_ranges = {
            '0.9-1.0': sum(1 for s in scores if 0.9 <= s <= 1.0),
            '0.8-0.9': sum(1 for s in scores if 0.8 <= s < 0.9),
            '0.7-0.8': sum(1 for s in scores if 0.7 <= s < 0.8),
            '0.6-0.7': sum(1 for s in scores if 0.6 <= s < 0.7),
            '0.5-0.6': sum(1 for s in scores if 0.5 <= s < 0.6),
            'below-0.5': sum(1 for s in scores if s < 0.5)
        }
        
        # Top matches
        sorted_matches = sorted(matches, key=lambda m: m.match_score.total_score, reverse=True)
        top_matches = [
            {
                'match_id': match.match_id,
                'faculty_id': match.faculty_profile_id,
                'funding_id': match.funding_opportunity_id,
                'total_score': match.match_score.total_score,
                'research_alignment': match.match_score.research_alignment,
                'methodology_match': match.match_score.methodology_match,
                'career_stage_fit': match.match_score.career_stage_fit
            }
            for match in sorted_matches[:10]
        ]
        
        return {
            'total_matches': len(matches),
            'average_score': sum(scores) / len(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'score_distribution': score_ranges,
            'top_matches': top_matches,
            'unique_faculty': len(set(match.faculty_profile_id for match in matches)),
            'unique_opportunities': len(set(match.funding_opportunity_id for match in matches))
        }
    
    def process_a2a_message(self, message: A2AMessage) -> A2AMessage:
        """Process A2A messages from other agents."""
        logger.info(f"Processing A2A message from {message.source_agent}")
        
        try:
            request_data = message.payload
            
            # Extract parameters from request
            faculty_data_file = request_data.get('faculty_data_file')
            funding_data_file = request_data.get('funding_data_file')
            min_score_threshold = request_data.get('min_score_threshold', self.min_score_threshold)
            
            if not faculty_data_file or not funding_data_file:
                raise ValueError("Both faculty_data_file and funding_data_file are required")
            
            # Process matching request
            result = self.run_matching_a2a(faculty_data_file, funding_data_file, min_score_threshold)
            
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
    
    def run_matching_a2a(self, faculty_data_file: str, funding_data_file: str, 
                         min_score_threshold: float = None) -> Dict[str, Any]:
        """Run matching process for A2A communication."""
        start_time = datetime.now()
        
        try:
            # Load data
            faculty_profiles = self.load_faculty_data(faculty_data_file)
            funding_opportunities = self.load_funding_data(funding_data_file)
            
            if not faculty_profiles:
                return {
                    'success': False,
                    'error': 'No valid faculty profiles loaded',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            if not funding_opportunities:
                return {
                    'success': False,
                    'error': 'No valid funding opportunities loaded',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            # Update threshold if provided
            if min_score_threshold is not None:
                self.min_score_threshold = min_score_threshold
            
            # Generate matches
            matches = self.generate_matches(faculty_profiles, funding_opportunities)
            
            # Save matches
            matches_file = self.save_matches(matches)
            
            # Generate statistics
            stats = self.get_match_statistics(matches)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'matches_count': len(matches),
                'matches_file': str(matches_file),
                'statistics': stats,
                'faculty_count': len(faculty_profiles),
                'funding_count': len(funding_opportunities),
                'processing_time_seconds': processing_time,
                'min_score_threshold': self.min_score_threshold
            }
            
        except Exception as e:
            logger.error(f"Error in matching process: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def run_matching(self, faculty_data_file: str, funding_data_file: str) -> Dict[str, Any]:
        """Run the complete matching process."""
        return self.run_matching_a2a(faculty_data_file, funding_data_file)


def main():
    """Main function for running the matcher agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Faculty-Funding Matching Agent')
    parser.add_argument('--faculty-data', required=True, help='Faculty data file path')
    parser.add_argument('--funding-data', required=True, help='Funding data file path')
    parser.add_argument('--min-score', type=float, default=0.3, help='Minimum match score threshold')
    parser.add_argument('--max-matches', type=int, default=10, help='Maximum matches per faculty')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = MatcherAgent(
        min_score_threshold=args.min_score,
        max_matches_per_faculty=args.max_matches
    )
    
    # Run matching
    result = agent.run_matching(args.faculty_data, args.funding_data)
    
    if result['success']:
        print(f"Matching complete!")
        print(f"Generated {result['matches_count']} matches")
        print(f"Processed {result['faculty_count']} faculty and {result['funding_count']} opportunities")
        print(f"Results saved to: {result['matches_file']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f} seconds")
        
        # Print top matches
        if 'statistics' in result and 'top_matches' in result['statistics']:
            print("\nTop 5 matches:")
            for i, match in enumerate(result['statistics']['top_matches'][:5], 1):
                print(f"{i}. Faculty: {match['faculty_id']} | Funding: {match['funding_id']} | Score: {match['total_score']:.3f}")
    else:
        print(f"Matching failed: {result['error']}")


if __name__ == "__main__":
    main()