"""
Proposal variant generation and estimation logic for the Faculty Research Opportunity Notifier.

This module provides utilities for generating different types of research proposals
(conservative, innovative, stretch) with appropriate budget and timeline estimates.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from enum import Enum
import random

from .models import ProposalVariant, CareerStage, ResearchMethodology


class ProposalVariantGenerator:
    """Generates content for different proposal variants."""
    
    # Base templates for different variant types
    VARIANT_TEMPLATES = {
        ProposalVariant.CONSERVATIVE: {
            'risk_level': 'low',
            'novelty_factor': 0.3,
            'methodology_complexity': 'standard',
            'approach': 'proven methods and established techniques'
        },
        ProposalVariant.INNOVATIVE: {
            'risk_level': 'moderate',
            'novelty_factor': 0.6,
            'methodology_complexity': 'advanced',
            'approach': 'novel approaches with some established foundations'
        },
        ProposalVariant.STRETCH: {
            'risk_level': 'high',
            'novelty_factor': 0.9,
            'methodology_complexity': 'cutting-edge',
            'approach': 'breakthrough methodologies and experimental techniques'
        }
    }
    
    def generate_idea_content(self,
                            faculty_interests: List[str],
                            funding_areas: List[str],
                            variant_type: ProposalVariant,
                            use_llm: bool = False) -> Dict[str, Any]:
        """
        Generate research idea content for a specific variant type.
        
        Args:
            faculty_interests: Faculty research interests
            funding_areas: Funding opportunity focus areas
            variant_type: Type of proposal variant
            use_llm: Whether to use LLM for generation (not implemented in MVP)
            
        Returns:
            Dictionary containing idea content
        """
        if use_llm:
            # Placeholder for future LLM integration
            return self._generate_with_llm(faculty_interests, funding_areas, variant_type)
        else:
            return self._generate_template_based(faculty_interests, funding_areas, variant_type)
    
    def _generate_template_based(self,
                               faculty_interests: List[str],
                               funding_areas: List[str],
                               variant_type: ProposalVariant) -> Dict[str, Any]:
        """Generate idea content using template-based approach."""
        
        # Find intersection of interests and funding areas
        common_areas = []
        for interest in faculty_interests:
            for area in funding_areas:
                if any(word in area.lower() for word in interest.lower().split()):
                    common_areas.append((interest, area))
        
        if not common_areas:
            # Fallback to using first items from each list
            primary_interest = faculty_interests[0] if faculty_interests else "research"
            primary_area = funding_areas[0] if funding_areas else "investigation"
        else:
            primary_interest, primary_area = common_areas[0]
        
        template = self.VARIANT_TEMPLATES[variant_type]
        
        # Generate title based on variant type
        title_prefixes = {
            ProposalVariant.CONSERVATIVE: ["Investigating", "Examining", "Analyzing"],
            ProposalVariant.INNOVATIVE: ["Advancing", "Developing", "Enhancing"],
            ProposalVariant.STRETCH: ["Revolutionizing", "Pioneering", "Transforming"]
        }
        
        title_prefix = random.choice(title_prefixes[variant_type])
        title = f"{title_prefix} {primary_area.title()} through {primary_interest.title()}"
        
        # Generate research question
        question_templates = {
            ProposalVariant.CONSERVATIVE: "How can established {interest} methods be applied to improve {area}?",
            ProposalVariant.INNOVATIVE: "What novel {interest} approaches can advance our understanding of {area}?",
            ProposalVariant.STRETCH: "How might breakthrough {interest} technologies revolutionize {area}?"
        }
        
        research_question = question_templates[variant_type].format(
            interest=primary_interest,
            area=primary_area
        )
        
        # Generate hypothesis (if applicable)
        hypothesis = None
        if variant_type in [ProposalVariant.INNOVATIVE, ProposalVariant.STRETCH]:
            hypothesis = f"We hypothesize that {template['approach']} in {primary_interest} will significantly impact {primary_area}."
        
        # Generate objectives based on variant type
        objective_templates = {
            ProposalVariant.CONSERVATIVE: [
                f"Apply standard {primary_interest} techniques to {primary_area}",
                f"Validate existing approaches in the context of {primary_area}",
                f"Establish baseline measurements for {primary_area} applications"
            ],
            ProposalVariant.INNOVATIVE: [
                f"Develop enhanced {primary_interest} methodologies for {primary_area}",
                f"Integrate multiple approaches to advance {primary_area} research",
                f"Create novel frameworks for {primary_area} investigation"
            ],
            ProposalVariant.STRETCH: [
                f"Pioneer breakthrough {primary_interest} technologies for {primary_area}",
                f"Establish new paradigms in {primary_area} research",
                f"Develop transformative solutions for {primary_area} challenges"
            ]
        }
        
        objectives = objective_templates[variant_type]
        
        # Generate key references (simplified for template-based approach)
        key_references = [
            f"Key Research in {primary_interest.title()} (2023)",
            f"Advances in {primary_area.title()} Studies (2022)",
            f"Methodological Approaches to {primary_interest.title()} (2023)"
        ]
        
        # Generate literature gap
        gap_templates = {
            ProposalVariant.CONSERVATIVE: f"Limited application of proven {primary_interest} methods to {primary_area}",
            ProposalVariant.INNOVATIVE: f"Insufficient integration of advanced {primary_interest} approaches in {primary_area} research",
            ProposalVariant.STRETCH: f"Lack of breakthrough {primary_interest} technologies for transforming {primary_area}"
        }
        
        literature_gap = gap_templates[variant_type]
        
        return {
            'title': title,
            'research_question': research_question,
            'hypothesis': hypothesis,
            'objectives': objectives,
            'key_references': key_references,
            'literature_gap': literature_gap,
            'variant_characteristics': template
        }
    
    def _generate_with_llm(self,
                         faculty_interests: List[str],
                         funding_areas: List[str],
                         variant_type: ProposalVariant) -> Dict[str, Any]:
        """Generate idea content using LLM (placeholder for future implementation)."""
        # This would integrate with an actual LLM service
        # For now, return template-based content with a note
        content = self._generate_template_based(faculty_interests, funding_areas, variant_type)
        content['llm_generated'] = False
        content['note'] = "LLM integration not implemented in MVP"
        return content
    
    def calculate_innovation_metrics(self,
                                  variant_type: ProposalVariant,
                                  match_score: float,
                                  career_stage: str) -> Dict[str, float]:
        """Calculate innovation-related metrics for a proposal variant."""
        
        # Base metrics by variant type
        base_metrics = {
            ProposalVariant.CONSERVATIVE: {
                'innovation_level': 0.3,
                'feasibility_score': 0.9,
                'impact_potential': 0.6
            },
            ProposalVariant.INNOVATIVE: {
                'innovation_level': 0.6,
                'feasibility_score': 0.7,
                'impact_potential': 0.8
            },
            ProposalVariant.STRETCH: {
                'innovation_level': 0.9,
                'feasibility_score': 0.5,
                'impact_potential': 0.9
            }
        }
        
        metrics = base_metrics[variant_type].copy()
        
        # Adjust based on match score (higher match = better feasibility)
        metrics['feasibility_score'] = min(1.0, metrics['feasibility_score'] + (match_score - 0.5) * 0.2)
        
        # Adjust based on career stage
        career_adjustments = {
            'graduate_student': {'innovation_level': -0.1, 'feasibility_score': 0.1},
            'postdoc': {'innovation_level': 0.0, 'feasibility_score': 0.05},
            'assistant_professor': {'innovation_level': 0.1, 'feasibility_score': 0.0},
            'associate_professor': {'innovation_level': 0.05, 'feasibility_score': 0.1},
            'full_professor': {'innovation_level': 0.0, 'feasibility_score': 0.15}
        }
        
        if career_stage in career_adjustments:
            adjustments = career_adjustments[career_stage]
            for key, adjustment in adjustments.items():
                metrics[key] = max(0.0, min(1.0, metrics[key] + adjustment))
        
        return metrics


class BudgetEstimator:
    """Estimates budgets for different proposal variants."""
    
    # Base budget ranges by career stage (in USD)
    CAREER_STAGE_BUDGETS = {
        CareerStage.GRADUATE_STUDENT: {'min': 5000, 'max': 25000},
        CareerStage.POSTDOC: {'min': 10000, 'max': 75000},
        CareerStage.ASSISTANT_PROFESSOR: {'min': 25000, 'max': 200000},
        CareerStage.ASSOCIATE_PROFESSOR: {'min': 50000, 'max': 500000},
        CareerStage.FULL_PROFESSOR: {'min': 100000, 'max': 1000000},
        CareerStage.RESEARCH_SCIENTIST: {'min': 25000, 'max': 300000},
        CareerStage.OTHER: {'min': 10000, 'max': 150000}
    }
    
    # Budget multipliers by variant type
    VARIANT_MULTIPLIERS = {
        ProposalVariant.CONSERVATIVE: 0.8,
        ProposalVariant.INNOVATIVE: 1.0,
        ProposalVariant.STRETCH: 1.3
    }
    
    # Budget multipliers by methodology complexity
    METHODOLOGY_MULTIPLIERS = {
        ResearchMethodology.THEORETICAL: 0.6,
        ResearchMethodology.COMPUTATIONAL: 0.8,
        ResearchMethodology.SURVEY: 0.7,
        ResearchMethodology.QUALITATIVE: 0.7,
        ResearchMethodology.OBSERVATIONAL: 0.9,
        ResearchMethodology.EXPERIMENTAL: 1.2,
        ResearchMethodology.CLINICAL: 1.5,
        ResearchMethodology.MIXED_METHODS: 1.1,
        ResearchMethodology.META_ANALYSIS: 0.5
    }
    
    def estimate_budget(self,
                       variant_type: ProposalVariant,
                       career_stage: CareerStage,
                       methodologies: List[ResearchMethodology],
                       max_funding: Decimal,
                       base_score: float = 0.5) -> Decimal:
        """
        Estimate budget for a proposal variant.
        
        Args:
            variant_type: Type of proposal variant
            career_stage: Faculty career stage
            methodologies: Research methodologies to be used
            max_funding: Maximum available funding
            base_score: Base match score for adjustment
            
        Returns:
            Estimated budget as Decimal
        """
        
        # Get base budget range for career stage
        budget_range = self.CAREER_STAGE_BUDGETS.get(career_stage, self.CAREER_STAGE_BUDGETS[CareerStage.OTHER])
        base_budget = (budget_range['min'] + budget_range['max']) / 2
        
        # Apply variant multiplier
        variant_multiplier = self.VARIANT_MULTIPLIERS[variant_type]
        adjusted_budget = base_budget * variant_multiplier
        
        # Apply methodology multipliers (use maximum for multiple methodologies)
        if methodologies:
            methodology_multiplier = max(
                self.METHODOLOGY_MULTIPLIERS.get(method, 1.0) for method in methodologies
            )
            adjusted_budget *= methodology_multiplier
        
        # Apply match score adjustment (better match = higher confidence in budget)
        score_adjustment = 0.8 + (base_score * 0.4)  # Range: 0.8 to 1.2
        adjusted_budget *= score_adjustment
        
        # Ensure budget doesn't exceed max funding
        final_budget = min(adjusted_budget, float(max_funding))
        
        # Ensure minimum reasonable budget
        min_budget = budget_range['min'] * 0.5
        final_budget = max(final_budget, min_budget)
        
        return Decimal(str(round(final_budget, 2)))
    
    def generate_budget_breakdown(self,
                                total_budget: Decimal,
                                variant_type: ProposalVariant,
                                methodologies: List[str]) -> Dict[str, Decimal]:
        """Generate detailed budget breakdown by category."""
        
        # Base percentages by category
        base_breakdown = {
            'personnel': 0.60,
            'equipment': 0.15,
            'supplies': 0.10,
            'travel': 0.05,
            'indirect': 0.10
        }
        
        # Adjust percentages based on variant type
        variant_adjustments = {
            ProposalVariant.CONSERVATIVE: {
                'personnel': 0.05,
                'equipment': -0.03,
                'supplies': -0.02
            },
            ProposalVariant.INNOVATIVE: {
                'equipment': 0.03,
                'supplies': 0.02,
                'personnel': -0.05
            },
            ProposalVariant.STRETCH: {
                'equipment': 0.08,
                'supplies': 0.05,
                'personnel': -0.10,
                'travel': -0.03
            }
        }
        
        # Apply variant adjustments
        if variant_type in variant_adjustments:
            for category, adjustment in variant_adjustments[variant_type].items():
                base_breakdown[category] += adjustment
        
        # Adjust based on methodologies
        if 'experimental' in methodologies or 'clinical' in methodologies:
            base_breakdown['equipment'] += 0.05
            base_breakdown['supplies'] += 0.03
            base_breakdown['personnel'] -= 0.08
        
        if 'computational' in methodologies:
            base_breakdown['equipment'] += 0.03
            base_breakdown['personnel'] += 0.02
            base_breakdown['supplies'] -= 0.05
        
        # Normalize to ensure total = 1.0
        total_percentage = sum(base_breakdown.values())
        normalized_breakdown = {k: v / total_percentage for k, v in base_breakdown.items()}
        
        # Calculate actual amounts
        budget_breakdown = {}
        for category, percentage in normalized_breakdown.items():
            amount = total_budget * Decimal(str(percentage))
            budget_breakdown[category] = amount.quantize(Decimal('0.01'))
        
        return budget_breakdown


class TimelineEstimator:
    """Estimates project timelines for different proposal variants."""
    
    # Base timeline ranges by variant type (in months)
    VARIANT_TIMELINES = {
        ProposalVariant.CONSERVATIVE: {'min': 12, 'max': 24},
        ProposalVariant.INNOVATIVE: {'min': 18, 'max': 36},
        ProposalVariant.STRETCH: {'min': 24, 'max': 60}
    }
    
    # Timeline adjustments by methodology
    METHODOLOGY_ADJUSTMENTS = {
        ResearchMethodology.THEORETICAL: -3,
        ResearchMethodology.COMPUTATIONAL: -2,
        ResearchMethodology.SURVEY: 0,
        ResearchMethodology.QUALITATIVE: 2,
        ResearchMethodology.OBSERVATIONAL: 3,
        ResearchMethodology.EXPERIMENTAL: 4,
        ResearchMethodology.CLINICAL: 8,
        ResearchMethodology.MIXED_METHODS: 3,
        ResearchMethodology.META_ANALYSIS: -1
    }
    
    def estimate_timeline(self,
                         variant_type: ProposalVariant,
                         methodologies: List[ResearchMethodology],
                         max_duration: int,
                         budget: Decimal) -> int:
        """
        Estimate project timeline in months.
        
        Args:
            variant_type: Type of proposal variant
            methodologies: Research methodologies to be used
            max_duration: Maximum allowed duration
            budget: Project budget
            
        Returns:
            Estimated timeline in months
        """
        
        # Get base timeline for variant type
        timeline_range = self.VARIANT_TIMELINES[variant_type]
        base_timeline = (timeline_range['min'] + timeline_range['max']) / 2
        
        # Apply methodology adjustments
        methodology_adjustment = 0
        if methodologies:
            methodology_adjustment = max(
                self.METHODOLOGY_ADJUSTMENTS.get(method, 0) for method in methodologies
            )
        
        adjusted_timeline = base_timeline + methodology_adjustment
        
        # Budget-based adjustment (higher budget = potentially longer timeline)
        budget_float = float(budget)
        if budget_float > 500000:
            adjusted_timeline += 6
        elif budget_float > 200000:
            adjusted_timeline += 3
        elif budget_float < 50000:
            adjusted_timeline -= 3
        
        # Ensure timeline is within reasonable bounds
        final_timeline = max(6, min(adjusted_timeline, max_duration))
        
        return int(final_timeline)
    
    def generate_milestones(self, timeline_months: int, variant_type: ProposalVariant) -> List[str]:
        """Generate project milestones based on timeline and variant type."""
        
        milestones = []
        
        # Calculate milestone timing
        quarters = max(2, timeline_months // 6)  # At least 2 milestones
        milestone_interval = timeline_months / quarters
        
        # Generate milestone templates based on variant type
        milestone_templates = {
            ProposalVariant.CONSERVATIVE: [
                "Literature review and methodology validation",
                "Pilot study implementation",
                "Data collection and initial analysis",
                "Results validation and documentation",
                "Final analysis and reporting"
            ],
            ProposalVariant.INNOVATIVE: [
                "Comprehensive background research and tool development",
                "Methodology refinement and pilot testing",
                "Phase 1 implementation and initial results",
                "Methodology optimization and Phase 2",
                "Advanced analysis and integration",
                "Results validation and dissemination"
            ],
            ProposalVariant.STRETCH: [
                "Foundational research and breakthrough methodology development",
                "Proof-of-concept development and testing",
                "Phase 1 experimental implementation",
                "Technology refinement and scaling",
                "Phase 2 validation and optimization",
                "Advanced testing and analysis",
                "Results integration and future planning"
            ]
        }
        
        templates = milestone_templates[variant_type]
        
        # Select appropriate number of milestones
        num_milestones = min(len(templates), max(2, quarters))
        selected_templates = templates[:num_milestones]
        
        # Add timing to milestones
        for i, template in enumerate(selected_templates):
            month = int((i + 1) * milestone_interval)
            milestones.append(f"Month {month}: {template}")
        
        return milestones
    
    def generate_deliverables(self, variant_type: ProposalVariant, methodologies: List[str]) -> List[str]:
        """Generate expected project deliverables."""
        
        base_deliverables = [
            "Comprehensive final report",
            "Peer-reviewed publication(s)",
            "Conference presentation materials"
        ]
        
        # Add variant-specific deliverables
        variant_deliverables = {
            ProposalVariant.CONSERVATIVE: [
                "Validated methodology documentation",
                "Replication guidelines"
            ],
            ProposalVariant.INNOVATIVE: [
                "Novel methodology framework",
                "Open-source tools/software",
                "Training materials"
            ],
            ProposalVariant.STRETCH: [
                "Breakthrough technology prototype",
                "Patent applications (if applicable)",
                "Commercialization roadmap",
                "Industry partnership opportunities"
            ]
        }
        
        all_deliverables = base_deliverables + variant_deliverables.get(variant_type, [])
        
        # Add methodology-specific deliverables
        if 'computational' in methodologies:
            all_deliverables.append("Software package and documentation")
        
        if 'clinical' in methodologies:
            all_deliverables.append("Clinical trial protocol and results")
        
        if 'experimental' in methodologies:
            all_deliverables.append("Experimental protocols and data sets")
        
        return all_deliverables