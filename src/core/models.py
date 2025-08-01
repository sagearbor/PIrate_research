"""
Core Pydantic models for the Faculty Research Opportunity Notifier system.

This module defines the data structures used throughout the multi-agent system
for representing funding opportunities, faculty profiles, research ideas, and
related entities.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator, HttpUrl
from decimal import Decimal


class CareerStage(str, Enum):
    """Career stage classification for faculty members."""
    GRADUATE_STUDENT = "graduate_student"
    POSTDOC = "postdoc" 
    ASSISTANT_PROFESSOR = "assistant_professor"
    ASSOCIATE_PROFESSOR = "associate_professor"
    FULL_PROFESSOR = "full_professor"
    EMERITUS = "emeritus"
    RESEARCH_SCIENTIST = "research_scientist"
    OTHER = "other"


class ResearchMethodology(str, Enum):
    """Research methodology classifications."""
    EXPERIMENTAL = "experimental"
    COMPUTATIONAL = "computational"
    THEORETICAL = "theoretical"
    OBSERVATIONAL = "observational"
    CLINICAL = "clinical"
    SURVEY = "survey"
    QUALITATIVE = "qualitative"
    META_ANALYSIS = "meta_analysis"
    MIXED_METHODS = "mixed_methods"


class ProposalVariant(str, Enum):
    """Types of research proposal variants."""
    CONSERVATIVE = "conservative"
    INNOVATIVE = "innovative"
    STRETCH = "stretch"


class MatchStatus(str, Enum):
    """Status of faculty-funding matches."""
    PENDING = "pending"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"


class Publication(BaseModel):
    """Model for academic publications."""
    title: str = Field(..., description="Publication title")
    authors: List[str] = Field(..., description="List of author names")
    journal: Optional[str] = Field(None, description="Journal or venue name")
    year: int = Field(..., description="Publication year")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    url: Optional[HttpUrl] = Field(None, description="URL to publication")
    citation_count: Optional[int] = Field(0, description="Number of citations")
    keywords: List[str] = Field(default_factory=list, description="Publication keywords")

    @field_validator('year')
    @classmethod
    def validate_year(cls, v):
        current_year = datetime.now().year
        if v < 1900 or v > current_year + 1:
            raise ValueError(f'Year must be between 1900 and {current_year + 1}')
        return v


class FacultyProfile(BaseModel):
    """Model representing a faculty member's academic profile."""
    
    # Basic Information
    name: str = Field(..., description="Full name of the faculty member")
    email: Optional[str] = Field(None, description="Email address")
    institution: str = Field(..., description="Institution affiliation")
    department: str = Field(..., description="Department name")
    career_stage: CareerStage = Field(..., description="Current career stage")
    
    # Academic Information
    research_interests: List[str] = Field(..., description="List of research interest keywords")
    methodologies: List[ResearchMethodology] = Field(..., description="Preferred research methodologies")
    publications: List[Publication] = Field(default_factory=list, description="Recent publications")
    
    # Profile URLs and IDs
    orcid_id: Optional[str] = Field(None, description="ORCID identifier")
    google_scholar_id: Optional[str] = Field(None, description="Google Scholar profile ID")
    institutional_profile_url: Optional[HttpUrl] = Field(None, description="Institution profile URL")
    
    # Metrics
    h_index: Optional[int] = Field(None, description="H-index score")
    total_citations: Optional[int] = Field(0, description="Total citation count")
    years_active: Optional[int] = Field(None, description="Years of research activity")
    
    # System metadata
    profile_id: Optional[str] = Field(None, description="Unique profile identifier")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last profile update")
    data_sources: List[str] = Field(default_factory=list, description="Sources used to build profile")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @field_validator('research_interests')
    @classmethod
    def validate_research_interests(cls, v):
        if not v:
            raise ValueError('At least one research interest is required')
        return [interest.strip().lower() for interest in v]


class FundingOpportunity(BaseModel):
    """Model representing a funding opportunity."""
    
    # Basic Information
    title: str = Field(..., description="Funding opportunity title")
    agency: str = Field(..., description="Funding agency name")
    opportunity_id: str = Field(..., description="Unique opportunity identifier")
    
    # Financial Details  
    total_budget: Optional[Decimal] = Field(None, description="Total available funding")
    max_award_amount: Optional[Decimal] = Field(None, description="Maximum individual award")
    min_award_amount: Optional[Decimal] = Field(None, description="Minimum individual award")
    currency: str = Field(default="USD", description="Currency code")
    
    # Timeline
    deadline: date = Field(..., description="Application deadline")
    award_start_date: Optional[date] = Field(None, description="Expected award start date")
    project_duration_months: Optional[int] = Field(None, description="Project duration in months")
    
    # Eligibility and Requirements
    eligible_career_stages: List[CareerStage] = Field(..., description="Eligible career stages")
    eligible_institutions: List[str] = Field(default_factory=list, description="Eligible institution types")
    citizenship_requirements: List[str] = Field(default_factory=list, description="Citizenship requirements")
    
    # Research Focus
    research_areas: List[str] = Field(..., description="Targeted research areas")
    preferred_methodologies: List[ResearchMethodology] = Field(default_factory=list, description="Preferred methodologies")
    keywords: List[str] = Field(default_factory=list, description="Opportunity keywords")
    
    # Details
    description: str = Field(..., description="Full opportunity description")
    url: HttpUrl = Field(..., description="URL to opportunity details")
    
    # System metadata
    scraped_date: datetime = Field(default_factory=datetime.now, description="Date when opportunity was scraped")
    source: str = Field(..., description="Data source (e.g., 'NIH', 'PCORI')")
    is_active: bool = Field(default=True, description="Whether opportunity is still active")

    @field_validator('deadline')
    @classmethod
    def validate_deadline(cls, v):
        if v < date.today():
            raise ValueError('Deadline cannot be in the past')
        return v

    @field_validator('research_areas')
    @classmethod
    def validate_research_areas(cls, v):
        if not v:
            raise ValueError('At least one research area is required')
        return [area.strip().lower() for area in v]


class ResearchIdea(BaseModel):
    """Model representing a generated research idea/proposal."""
    
    # Basic Information
    title: str = Field(..., description="Research proposal title")
    variant_type: ProposalVariant = Field(..., description="Type of proposal variant")
    
    # Research Details
    research_question: str = Field(..., description="Primary research question")
    hypothesis: Optional[str] = Field(None, description="Research hypothesis")
    methodology: List[ResearchMethodology] = Field(..., description="Proposed methodologies")
    objectives: List[str] = Field(..., description="Research objectives")
    
    # Project Planning
    timeline_months: int = Field(..., description="Proposed project duration in months")
    milestones: List[str] = Field(default_factory=list, description="Key project milestones")
    deliverables: List[str] = Field(default_factory=list, description="Expected deliverables")
    
    # Budget Estimation
    estimated_budget: Decimal = Field(..., description="Estimated total budget")
    budget_breakdown: Dict[str, Decimal] = Field(default_factory=dict, description="Budget category breakdown")
    
    # Innovation and Impact
    innovation_level: float = Field(..., ge=0.0, le=1.0, description="Innovation score (0-1)")
    feasibility_score: float = Field(..., ge=0.0, le=1.0, description="Feasibility score (0-1)")
    impact_potential: float = Field(..., ge=0.0, le=1.0, description="Impact potential (0-1)")
    
    # Literature and Background
    key_references: List[str] = Field(default_factory=list, description="Key literature references")
    literature_gap: Optional[str] = Field(None, description="Identified literature gap")
    
    # System metadata
    generated_date: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    llm_model: Optional[str] = Field(None, description="LLM model used for generation")

    @field_validator('timeline_months')
    @classmethod
    def validate_timeline(cls, v):
        if v <= 0 or v > 120:  # Max 10 years
            raise ValueError('Timeline must be between 1 and 120 months')
        return v


class CollaboratorSuggestion(BaseModel):
    """Model for suggested research collaborators."""
    
    faculty_profile_id: str = Field(..., description="ID of suggested collaborator")
    name: str = Field(..., description="Collaborator name")
    institution: str = Field(..., description="Collaborator institution")
    
    # Matching Details
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    complementary_expertise: List[str] = Field(..., description="Complementary research areas")
    shared_interests: List[str] = Field(..., description="Shared research interests")
    
    # Collaboration History
    previous_collaborations: int = Field(default=0, description="Number of previous collaborations")
    common_publications: List[str] = Field(default_factory=list, description="Common publication titles")
    
    # Contact Information
    email: Optional[str] = Field(None, description="Collaborator email")
    profile_url: Optional[HttpUrl] = Field(None, description="Profile URL")


class MatchScore(BaseModel):
    """Model representing a faculty-funding match score."""
    
    # Overall Score
    total_score: float = Field(..., ge=0.0, le=1.0, description="Overall match score (0-1)")
    
    # Component Scores
    research_alignment: float = Field(..., ge=0.0, le=1.0, description="Research area alignment score")
    methodology_match: float = Field(..., ge=0.0, le=1.0, description="Methodology alignment score") 
    career_stage_fit: float = Field(..., ge=0.0, le=1.0, description="Career stage appropriateness")
    deadline_urgency: float = Field(..., ge=0.0, le=1.0, description="Deadline urgency factor")
    budget_alignment: float = Field(..., ge=0.0, le=1.0, description="Budget expectation alignment")
    
    # Metadata
    scoring_algorithm: str = Field(..., description="Algorithm used for scoring")
    calculated_date: datetime = Field(default_factory=datetime.now, description="Score calculation timestamp")


class FacultyFundingMatch(BaseModel):
    """Model representing a match between faculty and funding opportunity."""
    
    # IDs
    match_id: str = Field(..., description="Unique match identifier")
    faculty_profile_id: str = Field(..., description="Faculty profile ID")
    funding_opportunity_id: str = Field(..., description="Funding opportunity ID")
    
    # Scores and Analysis
    match_score: MatchScore = Field(..., description="Detailed match scoring")
    
    # Generated Content
    research_ideas: List[ResearchIdea] = Field(default_factory=list, description="Generated research ideas")
    collaborator_suggestions: List[CollaboratorSuggestion] = Field(default_factory=list, description="Suggested collaborators")
    
    # Status and Workflow
    status: MatchStatus = Field(default=MatchStatus.PENDING, description="Match status")
    notification_sent: bool = Field(default=False, description="Whether notification was sent")
    faculty_response: Optional[str] = Field(None, description="Faculty response to match")
    
    # System metadata
    created_date: datetime = Field(default_factory=datetime.now, description="Match creation timestamp")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class SystemMetrics(BaseModel):
    """Model for system performance and analytics metrics."""
    
    # Data Ingestion Metrics
    total_funding_opportunities: int = Field(default=0, description="Total opportunities in system")
    total_faculty_profiles: int = Field(default=0, description="Total faculty profiles")
    active_opportunities: int = Field(default=0, description="Currently active opportunities")
    
    # Matching Metrics
    total_matches_generated: int = Field(default=0, description="Total matches generated")
    high_quality_matches: int = Field(default=0, description="Matches with score > 0.7")
    matches_with_faculty_response: int = Field(default=0, description="Matches with faculty feedback")
    
    # Success Metrics
    successful_applications: int = Field(default=0, description="Known successful applications")
    application_rate: float = Field(default=0.0, description="Percentage of matches leading to applications")
    
    # System Health
    last_ingestion_run: Optional[datetime] = Field(None, description="Last data ingestion timestamp")
    system_uptime_hours: float = Field(default=0.0, description="System uptime in hours")
    
    # Timestamp
    metrics_date: datetime = Field(default_factory=datetime.now, description="Metrics collection timestamp")


class NotificationContent(BaseModel):
    """Model for email notification content."""
    
    # Recipients
    recipient_email: str = Field(..., description="Recipient email address")
    recipient_name: str = Field(..., description="Recipient name")
    
    # Content
    subject: str = Field(..., description="Email subject line")
    body_html: str = Field(..., description="HTML email body")
    body_text: str = Field(..., description="Plain text email body")
    
    # Match Information
    match_id: str = Field(..., description="Associated match ID")
    funding_title: str = Field(..., description="Funding opportunity title")
    deadline: date = Field(..., description="Funding deadline")
    
    # Status
    sent: bool = Field(default=False, description="Whether email was sent")
    sent_date: Optional[datetime] = Field(None, description="Email send timestamp")
    
    # System metadata
    created_date: datetime = Field(default_factory=datetime.now, description="Notification creation timestamp")