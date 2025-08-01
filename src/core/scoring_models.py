"""
Multi-dimensional scoring models for the Faculty Research Opportunity Notifier.

This module implements the scoring algorithms used by the Matcher Agent to calculate
compatibility scores between faculty profiles and funding opportunities across
multiple dimensions: research alignment, methodology match, career stage fit,
deadline urgency, and budget alignment.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum
import math
import re
from decimal import Decimal

from .models import (
    FacultyProfile, FundingOpportunity, MatchScore, CareerStage, 
    ResearchMethodology, Publication
)


class ScoringWeights(Enum):
    """Default weights for different scoring dimensions."""
    RESEARCH_ALIGNMENT = 0.35
    METHODOLOGY_MATCH = 0.25
    CAREER_STAGE_FIT = 0.20
    DEADLINE_URGENCY = 0.15
    BUDGET_ALIGNMENT = 0.05


@dataclass
class ScoringConfiguration:
    """Configuration for customizing scoring behavior."""
    weights: Dict[str, float] = None
    career_stage_compatibility: Dict[CareerStage, List[CareerStage]] = None
    methodology_boost_factor: float = 1.2
    citation_impact_weight: float = 0.1
    publication_recency_weight: float = 0.1
    min_deadline_days: int = 30
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'research_alignment': ScoringWeights.RESEARCH_ALIGNMENT.value,
                'methodology_match': ScoringWeights.METHODOLOGY_MATCH.value,
                'career_stage_fit': ScoringWeights.CAREER_STAGE_FIT.value,
                'deadline_urgency': ScoringWeights.DEADLINE_URGENCY.value,
                'budget_alignment': ScoringWeights.BUDGET_ALIGNMENT.value
            }
        
        if self.career_stage_compatibility is None:
            self.career_stage_compatibility = {
                CareerStage.GRADUATE_STUDENT: [CareerStage.GRADUATE_STUDENT, CareerStage.POSTDOC],
                CareerStage.POSTDOC: [CareerStage.POSTDOC, CareerStage.ASSISTANT_PROFESSOR],
                CareerStage.ASSISTANT_PROFESSOR: [CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR],
                CareerStage.ASSOCIATE_PROFESSOR: [CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR, CareerStage.FULL_PROFESSOR],
                CareerStage.FULL_PROFESSOR: [CareerStage.ASSOCIATE_PROFESSOR, CareerStage.FULL_PROFESSOR, CareerStage.EMERITUS],
                CareerStage.EMERITUS: [CareerStage.FULL_PROFESSOR, CareerStage.EMERITUS],
                CareerStage.RESEARCH_SCIENTIST: [CareerStage.RESEARCH_SCIENTIST, CareerStage.ASSISTANT_PROFESSOR, CareerStage.ASSOCIATE_PROFESSOR],
                CareerStage.OTHER: list(CareerStage)
            }


class ResearchAlignmentScorer:
    """Calculates research area alignment between faculty and funding opportunities."""
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r'[^\w\s]', '', text.lower().strip())
    
    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from text descriptions."""
        # Simple keyword extraction - can be enhanced with NLP
        normalized = ResearchAlignmentScorer.normalize_text(text)
        words = normalized.split()
        # Filter out common words and keep significant terms
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'a', 'an', 'this', 'that', 'these', 'those'}
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    @classmethod
    def calculate_keyword_overlap(cls, faculty_interests: List[str], funding_areas: List[str]) -> float:
        """Calculate keyword overlap between faculty interests and funding areas."""
        if not faculty_interests or not funding_areas:
            return 0.0
        
        # Normalize all terms
        faculty_terms = set()
        for interest in faculty_interests:
            faculty_terms.update(cls.extract_keywords(interest))
        
        funding_terms = set()
        for area in funding_areas:
            funding_terms.update(cls.extract_keywords(area))
        
        if not faculty_terms or not funding_terms:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(faculty_terms.intersection(funding_terms))
        union = len(faculty_terms.union(funding_terms))
        
        return intersection / union if union > 0 else 0.0
    
    @classmethod
    def calculate_publication_relevance(cls, publications: List[Publication], funding_areas: List[str]) -> float:
        """Calculate how relevant faculty publications are to funding areas."""
        if not publications or not funding_areas:
            return 0.0
        
        funding_terms = set()
        for area in funding_areas:
            funding_terms.update(cls.extract_keywords(area))
        
        relevance_scores = []
        current_year = datetime.now().year
        
        for pub in publications:
            # Extract keywords from publication
            pub_terms = set()
            pub_terms.update(cls.extract_keywords(pub.title))
            pub_terms.update(cls.extract_keywords(' '.join(pub.keywords)))
            
            if pub_terms:
                # Calculate overlap
                overlap = len(pub_terms.intersection(funding_terms)) / len(pub_terms.union(funding_terms))
                
                # Weight by recency and citations
                recency_weight = max(0.5, 1.0 - (current_year - pub.year) * 0.1)
                citation_weight = min(2.0, 1.0 + (pub.citation_count or 0) * 0.01)
                
                weighted_score = overlap * recency_weight * citation_weight
                relevance_scores.append(weighted_score)
        
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    @classmethod
    def calculate_alignment_score(cls, faculty: FacultyProfile, funding: FundingOpportunity) -> float:
        """Calculate overall research alignment score."""
        # Direct keyword overlap
        keyword_score = cls.calculate_keyword_overlap(
            faculty.research_interests, 
            funding.research_areas + funding.keywords
        )
        
        # Publication relevance
        publication_score = cls.calculate_publication_relevance(
            faculty.publications, 
            funding.research_areas + funding.keywords
        )
        
        # Combined score with weights
        alignment_score = (keyword_score * 0.7) + (publication_score * 0.3)
        
        return min(1.0, alignment_score)


class MethodologyMatcher:
    """Matches research methodologies between faculty and funding opportunities."""
    
    # Methodology compatibility matrix
    METHODOLOGY_COMPATIBILITY = {
        ResearchMethodology.EXPERIMENTAL: {
            ResearchMethodology.EXPERIMENTAL: 1.0,
            ResearchMethodology.CLINICAL: 0.8,
            ResearchMethodology.OBSERVATIONAL: 0.6,
            ResearchMethodology.MIXED_METHODS: 0.7,
            ResearchMethodology.COMPUTATIONAL: 0.4,
            ResearchMethodology.THEORETICAL: 0.3,
            ResearchMethodology.QUALITATIVE: 0.3,
            ResearchMethodology.SURVEY: 0.4,
            ResearchMethodology.META_ANALYSIS: 0.5
        },
        ResearchMethodology.COMPUTATIONAL: {
            ResearchMethodology.COMPUTATIONAL: 1.0,
            ResearchMethodology.THEORETICAL: 0.8,
            ResearchMethodology.EXPERIMENTAL: 0.4,
            ResearchMethodology.MIXED_METHODS: 0.7,
            ResearchMethodology.META_ANALYSIS: 0.6,
            ResearchMethodology.OBSERVATIONAL: 0.5,
            ResearchMethodology.CLINICAL: 0.3,
            ResearchMethodology.QUALITATIVE: 0.2,
            ResearchMethodology.SURVEY: 0.3
        },
        ResearchMethodology.THEORETICAL: {
            ResearchMethodology.THEORETICAL: 1.0,
            ResearchMethodology.COMPUTATIONAL: 0.8,
            ResearchMethodology.META_ANALYSIS: 0.6,
            ResearchMethodology.MIXED_METHODS: 0.5,
            ResearchMethodology.EXPERIMENTAL: 0.3,
            ResearchMethodology.OBSERVATIONAL: 0.4,
            ResearchMethodology.CLINICAL: 0.2,
            ResearchMethodology.QUALITATIVE: 0.3,
            ResearchMethodology.SURVEY: 0.2
        },
        ResearchMethodology.CLINICAL: {
            ResearchMethodology.CLINICAL: 1.0,
            ResearchMethodology.EXPERIMENTAL: 0.8,
            ResearchMethodology.OBSERVATIONAL: 0.7,
            ResearchMethodology.MIXED_METHODS: 0.8,
            ResearchMethodology.SURVEY: 0.6,
            ResearchMethodology.META_ANALYSIS: 0.6,
            ResearchMethodology.QUALITATIVE: 0.5,
            ResearchMethodology.COMPUTATIONAL: 0.3,
            ResearchMethodology.THEORETICAL: 0.2
        },
        ResearchMethodology.OBSERVATIONAL: {
            ResearchMethodology.OBSERVATIONAL: 1.0,
            ResearchMethodology.CLINICAL: 0.7,
            ResearchMethodology.SURVEY: 0.8,
            ResearchMethodology.MIXED_METHODS: 0.7,
            ResearchMethodology.META_ANALYSIS: 0.6,
            ResearchMethodology.EXPERIMENTAL: 0.6,
            ResearchMethodology.QUALITATIVE: 0.6,
            ResearchMethodology.COMPUTATIONAL: 0.5,
            ResearchMethodology.THEORETICAL: 0.4
        },
        ResearchMethodology.QUALITATIVE: {
            ResearchMethodology.QUALITATIVE: 1.0,
            ResearchMethodology.MIXED_METHODS: 0.9,
            ResearchMethodology.SURVEY: 0.7,
            ResearchMethodology.OBSERVATIONAL: 0.6,
            ResearchMethodology.CLINICAL: 0.5,
            ResearchMethodology.META_ANALYSIS: 0.4,
            ResearchMethodology.EXPERIMENTAL: 0.3,
            ResearchMethodology.COMPUTATIONAL: 0.2,
            ResearchMethodology.THEORETICAL: 0.3
        },
        ResearchMethodology.SURVEY: {
            ResearchMethodology.SURVEY: 1.0,
            ResearchMethodology.OBSERVATIONAL: 0.8,
            ResearchMethodology.QUALITATIVE: 0.7,
            ResearchMethodology.MIXED_METHODS: 0.8,
            ResearchMethodology.CLINICAL: 0.6,
            ResearchMethodology.META_ANALYSIS: 0.5,
            ResearchMethodology.EXPERIMENTAL: 0.4,
            ResearchMethodology.COMPUTATIONAL: 0.3,
            ResearchMethodology.THEORETICAL: 0.2
        },
        ResearchMethodology.META_ANALYSIS: {
            ResearchMethodology.META_ANALYSIS: 1.0,
            ResearchMethodology.OBSERVATIONAL: 0.6,
            ResearchMethodology.CLINICAL: 0.6,
            ResearchMethodology.COMPUTATIONAL: 0.6,
            ResearchMethodology.THEORETICAL: 0.6,
            ResearchMethodology.MIXED_METHODS: 0.7,
            ResearchMethodology.EXPERIMENTAL: 0.5,
            ResearchMethodology.SURVEY: 0.5,
            ResearchMethodology.QUALITATIVE: 0.4
        },
        ResearchMethodology.MIXED_METHODS: {
            ResearchMethodology.MIXED_METHODS: 1.0,
            ResearchMethodology.QUALITATIVE: 0.9,
            ResearchMethodology.SURVEY: 0.8,
            ResearchMethodology.CLINICAL: 0.8,
            ResearchMethodology.OBSERVATIONAL: 0.7,
            ResearchMethodology.EXPERIMENTAL: 0.7,
            ResearchMethodology.META_ANALYSIS: 0.7,
            ResearchMethodology.COMPUTATIONAL: 0.7,
            ResearchMethodology.THEORETICAL: 0.5
        }
    }
    
    @classmethod
    def calculate_methodology_score(cls, faculty_methods: List[ResearchMethodology], 
                                  funding_methods: List[ResearchMethodology]) -> float:
        """Calculate methodology compatibility score."""
        if not faculty_methods or not funding_methods:
            return 0.5  # Neutral score when no methodology info
        
        max_score = 0.0
        
        # Find best match across all combinations
        for faculty_method in faculty_methods:
            for funding_method in funding_methods:
                compatibility = cls.METHODOLOGY_COMPATIBILITY.get(faculty_method, {}).get(funding_method, 0.0)
                max_score = max(max_score, compatibility)
        
        return max_score


class CareerStageMatcher:
    """Evaluates career stage fit between faculty and funding opportunities."""
    
    @staticmethod
    def calculate_career_stage_score(faculty_stage: CareerStage, 
                                   eligible_stages: List[CareerStage],
                                   config: ScoringConfiguration) -> float:
        """Calculate career stage compatibility score."""
        if not eligible_stages:
            return 1.0  # No restrictions
        
        # Direct match
        if faculty_stage in eligible_stages:
            return 1.0
        
        # Check compatibility based on configuration
        compatible_stages = config.career_stage_compatibility.get(faculty_stage, [])
        for stage in eligible_stages:
            if stage in compatible_stages:
                return 0.7  # Partial match for compatible stages
        
        return 0.0  # No compatibility


class DeadlineUrgencyCalculator:
    """Calculates deadline urgency scores."""
    
    @staticmethod
    def calculate_urgency_score(deadline: date, config: ScoringConfiguration) -> float:
        """Calculate urgency score based on deadline proximity."""
        today = date.today()
        days_remaining = (deadline - today).days
        
        if days_remaining < 0:
            return 0.0  # Past deadline
        
        if days_remaining < config.min_deadline_days:
            return 0.2  # Too urgent, may not allow adequate preparation
        
        # Optimal range: 30-180 days
        if days_remaining <= 180:
            # Higher score for moderate urgency
            return 0.8 + (0.2 * (180 - days_remaining) / 150)
        
        # Longer deadlines get lower urgency scores
        return max(0.3, 1.0 - (days_remaining - 180) / 365)


class BudgetAlignmentCalculator:
    """Calculates budget alignment scores."""
    
    @staticmethod
    def estimate_faculty_budget_range(faculty: FacultyProfile) -> Tuple[Decimal, Decimal]:
        """Estimate appropriate budget range based on faculty profile."""
        # Base ranges by career stage
        base_ranges = {
            CareerStage.GRADUATE_STUDENT: (Decimal('5000'), Decimal('25000')),
            CareerStage.POSTDOC: (Decimal('10000'), Decimal('50000')),
            CareerStage.ASSISTANT_PROFESSOR: (Decimal('25000'), Decimal('200000')),
            CareerStage.ASSOCIATE_PROFESSOR: (Decimal('50000'), Decimal('500000')),
            CareerStage.FULL_PROFESSOR: (Decimal('100000'), Decimal('1000000')),
            CareerStage.EMERITUS: (Decimal('10000'), Decimal('100000')),
            CareerStage.RESEARCH_SCIENTIST: (Decimal('25000'), Decimal('300000')),
            CareerStage.OTHER: (Decimal('10000'), Decimal('200000'))
        }
        
        min_budget, max_budget = base_ranges.get(faculty.career_stage, base_ranges[CareerStage.OTHER])
        
        # Adjust based on publication record and citations
        if faculty.total_citations and faculty.total_citations > 500:
            multiplier = min(2.0, 1.0 + (faculty.total_citations - 500) / 1000)
            max_budget = Decimal(str(float(max_budget) * multiplier))
        
        if faculty.h_index and faculty.h_index > 15:
            multiplier = min(1.5, 1.0 + (faculty.h_index - 15) / 30)
            max_budget = Decimal(str(float(max_budget) * multiplier))
        
        return min_budget, max_budget
    
    @classmethod
    def calculate_budget_score(cls, faculty: FacultyProfile, funding: FundingOpportunity) -> float:
        """Calculate budget alignment score."""
        if not funding.max_award_amount:
            return 0.5  # Neutral when no budget info
        
        faculty_min, faculty_max = cls.estimate_faculty_budget_range(faculty)
        funding_amount = funding.max_award_amount
        
        # Perfect match if funding amount is within faculty range
        if faculty_min <= funding_amount <= faculty_max:
            return 1.0
        
        # Partial matches
        if funding_amount < faculty_min:
            # Funding too small
            ratio = float(funding_amount / faculty_min)
            return max(0.0, ratio)
        else:
            # Funding too large - might still be acceptable
            ratio = float(faculty_max / funding_amount)
            return max(0.2, ratio)


class MatchingEngine:
    """Main engine that combines all scoring components."""
    
    def __init__(self, config: ScoringConfiguration = None):
        self.config = config or ScoringConfiguration()
        self.research_scorer = ResearchAlignmentScorer()
        self.methodology_matcher = MethodologyMatcher()
        self.career_matcher = CareerStageMatcher()
        self.deadline_calculator = DeadlineUrgencyCalculator()
        self.budget_calculator = BudgetAlignmentCalculator()
    
    def calculate_match_score(self, faculty: FacultyProfile, funding: FundingOpportunity) -> MatchScore:
        """Calculate comprehensive match score between faculty and funding opportunity."""
        
        # Calculate individual component scores
        research_alignment = self.research_scorer.calculate_alignment_score(faculty, funding)
        methodology_match = self.methodology_matcher.calculate_methodology_score(
            faculty.methodologies, funding.preferred_methodologies
        )
        career_stage_fit = self.career_matcher.calculate_career_stage_score(
            faculty.career_stage, funding.eligible_career_stages, self.config
        )
        deadline_urgency = self.deadline_calculator.calculate_urgency_score(
            funding.deadline, self.config
        )
        budget_alignment = self.budget_calculator.calculate_budget_score(faculty, funding)
        
        # Calculate weighted total score
        total_score = (
            research_alignment * self.config.weights['research_alignment'] +
            methodology_match * self.config.weights['methodology_match'] +
            career_stage_fit * self.config.weights['career_stage_fit'] +
            deadline_urgency * self.config.weights['deadline_urgency'] +
            budget_alignment * self.config.weights['budget_alignment']
        )
        
        return MatchScore(
            total_score=min(1.0, max(0.0, total_score)),
            research_alignment=research_alignment,
            methodology_match=methodology_match,
            career_stage_fit=career_stage_fit,
            deadline_urgency=deadline_urgency,
            budget_alignment=budget_alignment,
            scoring_algorithm=f"MatchingEngine-v1.0-{datetime.now().strftime('%Y%m%d')}"
        )
    
    def batch_score_matches(self, faculty_list: List[FacultyProfile], 
                          funding_list: List[FundingOpportunity],
                          min_score_threshold: float = 0.0) -> List[Tuple[FacultyProfile, FundingOpportunity, MatchScore]]:
        """Calculate scores for all faculty-funding combinations above threshold."""
        matches = []
        
        for faculty in faculty_list:
            for funding in funding_list:
                score = self.calculate_match_score(faculty, funding)
                
                if score.total_score >= min_score_threshold:
                    matches.append((faculty, funding, score))
        
        # Sort by total score (descending)
        matches.sort(key=lambda x: x[2].total_score, reverse=True)
        
        return matches