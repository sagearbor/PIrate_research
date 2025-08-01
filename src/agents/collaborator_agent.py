"""
Collaborator Suggestion Agent for the Faculty Research Opportunity Notifier.

This agent identifies potential research collaborators based on faculty profiles,
research interests, and expertise overlap. It suggests collaborators who could
enhance research proposals and provide complementary skills.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from datetime import datetime
from pathlib import Path
import json
import re
from collections import defaultdict

from ..core.models import (
    FacultyProfile, CollaboratorSuggestion, ResearchMethodology, 
    CareerStage, Publication
)
from ..core.a2a_protocols import (
    A2AMessage, MessageType, AgentType,
    create_a2a_response
)

logger = logging.getLogger(__name__)


class CollaboratorSuggestionAgent:
    """
    Agent responsible for identifying potential research collaborators
    based on expertise overlap and complementary skills.
    """
    
    def __init__(self, 
                 max_suggestions_per_faculty: int = 5,
                 min_relevance_threshold: float = 0.3,
                 diversity_weight: float = 0.2):
        """
        Initialize the Collaborator Suggestion Agent.
        
        Args:
            max_suggestions_per_faculty: Maximum collaborator suggestions per faculty
            min_relevance_threshold: Minimum relevance score for suggestions
            diversity_weight: Weight for institutional/geographic diversity
        """
        self.max_suggestions_per_faculty = max_suggestions_per_faculty
        self.min_relevance_threshold = min_relevance_threshold
        self.diversity_weight = diversity_weight
        
        logger.info(f"Collaborator Suggestion Agent initialized with threshold {min_relevance_threshold}")
    
    def load_faculty_data(self, faculty_file: str) -> List[Dict[str, Any]]:
        """Load faculty profiles from file."""
        try:
            with open(faculty_file, 'r') as f:
                faculty_data = json.load(f)
            
            logger.info(f"Loaded {len(faculty_data)} faculty profiles from {faculty_file}")
            return faculty_data
            
        except Exception as e:
            logger.error(f"Error loading faculty data from {faculty_file}: {e}")
            return []
    
    def load_matches(self, matches_file: str) -> List[Dict[str, Any]]:
        """Load faculty-funding matches to get target faculty for collaboration suggestions."""
        try:
            with open(matches_file, 'r') as f:
                matches_data = json.load(f)
            
            logger.info(f"Loaded {len(matches_data)} matches from {matches_file}")
            return matches_data
            
        except Exception as e:
            logger.error(f"Error loading matches from {matches_file}: {e}")
            return []
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r'[^\w\s]', '', text.lower().strip())
    
    def extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text."""
        normalized = self.normalize_text(text)
        words = normalized.split()
        # Filter out common words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'must', 'can', 'a', 'an', 'this', 'that', 'these', 'those'
        }
        return {word for word in words if len(word) > 2 and word not in stop_words}
    
    def calculate_research_overlap(self, 
                                 faculty1_interests: List[str], 
                                 faculty2_interests: List[str]) -> float:
        """Calculate research interest overlap between two faculty members."""
        if not faculty1_interests or not faculty2_interests:
            return 0.0
        
        # Extract keywords from all interests
        keywords1 = set()
        for interest in faculty1_interests:
            keywords1.update(self.extract_keywords(interest))
        
        keywords2 = set()
        for interest in faculty2_interests:
            keywords2.update(self.extract_keywords(interest))
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(keywords1.intersection(keywords2))
        union = len(keywords1.union(keywords2))
        
        return intersection / union if union > 0 else 0.0
    
    def calculate_methodology_complementarity(self,
                                            faculty1_methods: List[str],
                                            faculty2_methods: List[str]) -> float:
        """Calculate how well methodologies complement each other."""
        if not faculty1_methods or not faculty2_methods:
            return 0.0
        
        methods1 = set(faculty1_methods)
        methods2 = set(faculty2_methods)
        
        # Check for complementary methodologies
        complementary_pairs = {
            ('experimental', 'theoretical'),
            ('computational', 'experimental'),
            ('qualitative', 'survey'),
            ('clinical', 'observational'),
            ('mixed_methods', 'experimental'),
            ('mixed_methods', 'qualitative')
        }
        
        complementarity_score = 0.0
        total_combinations = len(methods1) * len(methods2)
        
        for m1 in methods1:
            for m2 in methods2:
                if m1 == m2:
                    complementarity_score += 0.3  # Same methodology = some overlap
                elif (m1, m2) in complementary_pairs or (m2, m1) in complementary_pairs:
                    complementarity_score += 1.0  # Complementary methodologies
                else:
                    complementarity_score += 0.1  # Different but potentially useful
        
        return complementarity_score / total_combinations if total_combinations > 0 else 0.0
    
    def calculate_career_stage_compatibility(self, stage1: str, stage2: str) -> float:
        """Calculate compatibility between career stages for collaboration."""
        
        # Career stage hierarchy (roughly)
        stage_hierarchy = {
            'graduate_student': 1,
            'postdoc': 2,
            'assistant_professor': 3,
            'associate_professor': 4,
            'full_professor': 5,
            'emeritus': 5,
            'research_scientist': 3.5,
            'other': 3
        }
        
        level1 = stage_hierarchy.get(stage1, 3)
        level2 = stage_hierarchy.get(stage2, 3)
        
        # Calculate compatibility based on level difference
        level_diff = abs(level1 - level2)
        
        if level_diff == 0:
            return 0.8  # Same level - good collaboration potential
        elif level_diff == 1:
            return 1.0  # Adjacent levels - excellent mentoring/collaboration potential
        elif level_diff == 2:
            return 0.9  # Two levels apart - still very good
        elif level_diff >= 3:
            return 0.6  # Large gap but still possible
        
        return 0.7  # Default
    
    def calculate_publication_overlap(self,
                                    faculty1_pubs: List[Dict[str, Any]],
                                    faculty2_pubs: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
        """Calculate publication topic overlap and find common publications."""
        
        if not faculty1_pubs or not faculty2_pubs:
            return 0.0, []
        
        # Extract keywords from publications
        keywords1 = set()
        titles1 = set()
        for pub in faculty1_pubs:
            if 'keywords' in pub:
                keywords1.update(self.extract_keywords(' '.join(pub['keywords'])))
            if 'title' in pub:
                keywords1.update(self.extract_keywords(pub['title']))
                titles1.add(self.normalize_text(pub['title']))
        
        keywords2 = set()
        titles2 = set()
        for pub in faculty2_pubs:
            if 'keywords' in pub:
                keywords2.update(self.extract_keywords(' '.join(pub['keywords'])))
            if 'title' in pub:
                keywords2.update(self.extract_keywords(pub['title']))
                titles2.add(self.normalize_text(pub['title']))
        
        # Check for common publications
        common_publications = []
        for pub1 in faculty1_pubs:
            title1 = self.normalize_text(pub1.get('title', ''))
            if title1 in titles2:
                common_publications.append(pub1.get('title', 'Unknown'))
        
        # Calculate keyword overlap
        if keywords1 and keywords2:
            intersection = len(keywords1.intersection(keywords2))
            union = len(keywords1.union(keywords2))
            overlap_score = intersection / union
        else:
            overlap_score = 0.0
        
        return overlap_score, common_publications
    
    def calculate_institutional_diversity_score(self, 
                                              faculty1_institution: str,
                                              faculty2_institution: str) -> float:
        """Calculate diversity score based on institutional affiliation."""
        if faculty1_institution.lower() == faculty2_institution.lower():
            return 0.3  # Same institution - lower diversity but easier collaboration
        else:
            return 1.0  # Different institutions - higher diversity
    
    def calculate_collaboration_score(self,
                                    target_faculty: Dict[str, Any],
                                    candidate_faculty: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate overall collaboration score between two faculty members.
        
        Returns:
            Tuple of (score, details_dict)
        """
        
        # Extract relevant information
        target_interests = target_faculty.get('research_interests', [])
        candidate_interests = candidate_faculty.get('research_interests', [])
        
        target_methods = target_faculty.get('methodologies', [])
        candidate_methods = candidate_faculty.get('methodologies', [])
        
        target_career = target_faculty.get('career_stage', 'other')
        candidate_career = candidate_faculty.get('career_stage', 'other')
        
        target_institution = target_faculty.get('institution', '')
        candidate_institution = candidate_faculty.get('institution', '')
        
        target_pubs = target_faculty.get('publications', [])
        candidate_pubs = candidate_faculty.get('publications', [])
        
        # Calculate component scores
        research_overlap = self.calculate_research_overlap(target_interests, candidate_interests)
        methodology_complementarity = self.calculate_methodology_complementarity(target_methods, candidate_methods)
        career_compatibility = self.calculate_career_stage_compatibility(target_career, candidate_career)
        institutional_diversity = self.calculate_institutional_diversity_score(target_institution, candidate_institution)
        publication_overlap, common_pubs = self.calculate_publication_overlap(target_pubs, candidate_pubs)
        
        # Calculate weighted overall score
        overall_score = (
            research_overlap * 0.35 +
            methodology_complementarity * 0.25 +
            career_compatibility * 0.20 +
            publication_overlap * 0.10 +
            institutional_diversity * self.diversity_weight
        )
        
        # Find shared and complementary interests
        target_keywords = set()
        for interest in target_interests:
            target_keywords.update(self.extract_keywords(interest))
        
        candidate_keywords = set()
        for interest in candidate_interests:
            candidate_keywords.update(self.extract_keywords(interest))
        
        shared_interests = list(target_keywords.intersection(candidate_keywords))
        complementary_expertise = list(candidate_keywords - target_keywords)[:5]  # Top 5
        
        details = {
            'research_overlap': research_overlap,
            'methodology_complementarity': methodology_complementarity,
            'career_compatibility': career_compatibility,
            'institutional_diversity': institutional_diversity,
            'publication_overlap': publication_overlap,
            'shared_interests': shared_interests,
            'complementary_expertise': complementary_expertise,
            'common_publications': common_pubs,
            'previous_collaborations': len(common_pubs)  # Simplified metric
        }
        
        return overall_score, details
    
    def find_collaborators_for_faculty(self,
                                     target_faculty: Dict[str, Any],
                                     all_faculty: List[Dict[str, Any]]) -> List[CollaboratorSuggestion]:
        """Find potential collaborators for a specific faculty member."""
        
        target_id = target_faculty.get('profile_id', target_faculty.get('name'))
        collaborator_suggestions = []
        
        for candidate_faculty in all_faculty:
            candidate_id = candidate_faculty.get('profile_id', candidate_faculty.get('name'))
            
            # Skip self-collaboration
            if target_id == candidate_id:
                continue
            
            # Calculate collaboration score
            score, details = self.calculate_collaboration_score(target_faculty, candidate_faculty)
            
            # Only include suggestions above threshold
            if score >= self.min_relevance_threshold:
                suggestion = CollaboratorSuggestion(
                    faculty_profile_id=candidate_id,
                    name=candidate_faculty.get('name', 'Unknown'),
                    institution=candidate_faculty.get('institution', 'Unknown'),
                    relevance_score=score,
                    complementary_expertise=details['complementary_expertise'],
                    shared_interests=details['shared_interests'],
                    previous_collaborations=details['previous_collaborations'],
                    common_publications=details['common_publications'],
                    email=candidate_faculty.get('email'),
                    profile_url=candidate_faculty.get('institutional_profile_url')
                )
                
                collaborator_suggestions.append(suggestion)
        
        # Sort by relevance score and limit results
        collaborator_suggestions.sort(key=lambda x: x.relevance_score, reverse=True)
        return collaborator_suggestions[:self.max_suggestions_per_faculty]
    
    def process_collaboration_requests(self,
                                     matches_data: List[Dict[str, Any]],
                                     all_faculty: List[Dict[str, Any]]) -> Dict[str, List[CollaboratorSuggestion]]:
        """
        Process collaboration requests for matched faculty members.
        
        Returns:
            Dictionary mapping faculty_profile_id to list of collaborator suggestions
        """
        
        # Create faculty lookup
        faculty_lookup = {}
        for faculty in all_faculty:
            faculty_id = faculty.get('profile_id', faculty.get('name'))
            faculty_lookup[faculty_id] = faculty
        
        collaboration_suggestions = {}
        
        # Get unique faculty from matches
        target_faculty_ids = set()
        for match in matches_data:
            faculty_id = match.get('faculty_profile_id')
            if faculty_id:
                target_faculty_ids.add(faculty_id)
        
        logger.info(f"Finding collaborators for {len(target_faculty_ids)} faculty members")
        
        # Find collaborators for each target faculty
        for faculty_id in target_faculty_ids:
            if faculty_id not in faculty_lookup:
                logger.warning(f"Faculty {faculty_id} not found in faculty data")
                continue
            
            target_faculty = faculty_lookup[faculty_id]
            
            try:
                suggestions = self.find_collaborators_for_faculty(target_faculty, all_faculty)
                collaboration_suggestions[faculty_id] = suggestions
                
                logger.info(f"Found {len(suggestions)} collaborators for faculty {faculty_id}")
                
            except Exception as e:
                logger.error(f"Error finding collaborators for faculty {faculty_id}: {e}")
                continue
        
        return collaboration_suggestions
    
    def save_collaborator_suggestions(self, 
                                    suggestions: Dict[str, List[CollaboratorSuggestion]], 
                                    output_file: str = None) -> Path:
        """Save collaborator suggestions to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/collaborator_suggestions_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert suggestions to serializable format
        suggestions_data = {}
        for faculty_id, faculty_suggestions in suggestions.items():
            suggestions_data[faculty_id] = []
            for suggestion in faculty_suggestions:
                suggestion_dict = {
                    'faculty_profile_id': suggestion.faculty_profile_id,
                    'name': suggestion.name,
                    'institution': suggestion.institution,
                    'relevance_score': suggestion.relevance_score,
                    'complementary_expertise': suggestion.complementary_expertise,
                    'shared_interests': suggestion.shared_interests,
                    'previous_collaborations': suggestion.previous_collaborations,
                    'common_publications': suggestion.common_publications,
                    'email': suggestion.email,
                    'profile_url': str(suggestion.profile_url) if suggestion.profile_url else None
                }
                suggestions_data[faculty_id].append(suggestion_dict)
        
        with open(output_path, 'w') as f:
            json.dump(suggestions_data, f, indent=2)
        
        logger.info(f"Saved collaborator suggestions for {len(suggestions)} faculty to {output_path}")
        return output_path
    
    def get_collaboration_statistics(self, 
                                   suggestions: Dict[str, List[CollaboratorSuggestion]]) -> Dict[str, Any]:
        """Generate statistics about the collaboration suggestion process."""
        if not suggestions:
            return {
                'total_faculty': 0,
                'total_suggestions': 0,
                'average_suggestions_per_faculty': 0,
                'score_distribution': {},
                'top_collaborators': []
            }
        
        total_suggestions = sum(len(faculty_suggestions) for faculty_suggestions in suggestions.values())
        all_scores = []
        institution_counts = defaultdict(int)
        
        # Collect all suggestions for analysis
        all_suggestions = []
        for faculty_id, faculty_suggestions in suggestions.items():
            for suggestion in faculty_suggestions:
                all_suggestions.append(suggestion)
                all_scores.append(suggestion.relevance_score)
                institution_counts[suggestion.institution] += 1
        
        # Score distribution
        score_ranges = {
            '0.9-1.0': sum(1 for s in all_scores if 0.9 <= s <= 1.0),
            '0.8-0.9': sum(1 for s in all_scores if 0.8 <= s < 0.9),
            '0.7-0.8': sum(1 for s in all_scores if 0.7 <= s < 0.8),
            '0.6-0.7': sum(1 for s in all_scores if 0.6 <= s < 0.7),
            '0.5-0.6': sum(1 for s in all_scores if 0.5 <= s < 0.6),
            'below-0.5': sum(1 for s in all_scores if s < 0.5)
        }
        
        # Top collaborators (by frequency of appearance)
        collaborator_frequency = defaultdict(int)
        for suggestion in all_suggestions:
            collaborator_frequency[suggestion.name] += 1
        
        top_collaborators = sorted(
            collaborator_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'total_faculty': len(suggestions),
            'total_suggestions': total_suggestions,
            'average_suggestions_per_faculty': total_suggestions / len(suggestions),
            'average_score': sum(all_scores) / len(all_scores) if all_scores else 0,
            'score_distribution': score_ranges,
            'top_collaborators': [{'name': name, 'frequency': freq} for name, freq in top_collaborators],
            'institution_diversity': len(institution_counts),
            'most_represented_institutions': sorted(
                institution_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def process_a2a_message(self, message: A2AMessage) -> A2AMessage:
        """Process A2A messages from other agents."""
        logger.info(f"Processing A2A message from {message.source_agent}")
        
        try:
            request_data = message.payload
            
            # Extract parameters from request
            matches_file = request_data.get('matches_file')
            faculty_file = request_data.get('faculty_file')
            
            if not matches_file or not faculty_file:
                raise ValueError("Both matches_file and faculty_file are required")
            
            # Process collaboration request
            result = self.run_collaboration_suggestion_a2a(matches_file, faculty_file)
            
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
    
    def run_collaboration_suggestion_a2a(self, matches_file: str, faculty_file: str) -> Dict[str, Any]:
        """Run collaboration suggestion process for A2A communication."""
        start_time = datetime.now()
        
        try:
            # Load data
            matches_data = self.load_matches(matches_file)
            all_faculty = self.load_faculty_data(faculty_file)
            
            if not matches_data:
                return {
                    'success': False,
                    'error': 'No valid matches loaded',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            if not all_faculty:
                return {
                    'success': False,
                    'error': 'No valid faculty data loaded',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            # Generate collaboration suggestions
            suggestions = self.process_collaboration_requests(matches_data, all_faculty)
            
            # Save suggestions
            suggestions_file = self.save_collaborator_suggestions(suggestions)
            
            # Generate statistics
            stats = self.get_collaboration_statistics(suggestions)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'faculty_processed': len(suggestions),
                'total_suggestions': stats['total_suggestions'],
                'suggestions_file': str(suggestions_file),
                'statistics': stats,
                'processing_time_seconds': processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in collaboration suggestion process: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def run_collaboration_suggestion(self, matches_file: str, faculty_file: str) -> Dict[str, Any]:
        """Run the complete collaboration suggestion process."""
        return self.run_collaboration_suggestion_a2a(matches_file, faculty_file)


def main():
    """Main function for running the collaborator suggestion agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Collaborator Suggestion Agent')
    parser.add_argument('--matches-file', required=True, help='Faculty-funding matches file path')
    parser.add_argument('--faculty-file', required=True, help='Faculty data file path')
    parser.add_argument('--max-suggestions', type=int, default=5, help='Maximum suggestions per faculty')
    parser.add_argument('--min-threshold', type=float, default=0.3, help='Minimum relevance threshold')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = CollaboratorSuggestionAgent(
        max_suggestions_per_faculty=args.max_suggestions,
        min_relevance_threshold=args.min_threshold
    )
    
    # Run collaboration suggestion
    result = agent.run_collaboration_suggestion(args.matches_file, args.faculty_file)
    
    if result['success']:
        print(f"Collaboration suggestion complete!")
        print(f"Processed {result['faculty_processed']} faculty members")
        print(f"Generated {result['total_suggestions']} collaborator suggestions")
        print(f"Results saved to: {result['suggestions_file']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f} seconds")
        
        # Print statistics
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\nStatistics:")
            print(f"Average suggestions per faculty: {stats['average_suggestions_per_faculty']:.1f}")
            print(f"Average relevance score: {stats['average_score']:.3f}")
            print(f"Institution diversity: {stats['institution_diversity']} institutions")
    else:
        print(f"Collaboration suggestion failed: {result['error']}")


if __name__ == "__main__":
    main()