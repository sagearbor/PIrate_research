"""
Agent-to-Agent (A2A) Communication Protocols

This module defines the message formats and protocols for inter-agent communication
following the Model Context Protocol (MCP) standard.
"""

from typing import Dict, Any, List, Optional, Union, Literal
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import json
import uuid

# Base A2A Message Types
class MessageType(str, Enum):
    """Standard A2A message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"

class AgentType(str, Enum):
    """Types of agents in the system"""
    INGESTION = "ingestion_agent"
    MATCHER = "matcher_agent"
    IDEA_GENERATION = "idea_generation_agent"
    COLLABORATOR = "collaborator_agent"
    NOTIFICATION = "notification_agent"
    DATABASE_DISCOVERY = "database_discovery_agent"
    ADMIN_DASHBOARD = "admin_dashboard_agent"

@dataclass
class A2AMessage:
    """Base class for all A2A messages"""
    message_type: MessageType
    source_agent: AgentType
    target_agent: AgentType
    message_id: str
    timestamp: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for transmission"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        """Create message from dictionary"""
        return cls(**data)

# Database Discovery Agent Protocols
class DiscoveryRequestType(str, Enum):
    """Specific request types for Database Discovery Agent"""
    DISCOVER_API = "discover_api"
    VALIDATE_API = "validate_api"
    GENERATE_ARTIFACTS = "generate_artifacts"

class ArtifactType(str, Enum):
    """Types of artifacts that can be generated"""
    CONFIG_FILE = "config_file"
    TEST_FILE = "test_file"
    MOCK_DATA = "mock_data"
    DOCUMENTATION = "documentation"
    INTEGRATION_GUIDE = "integration_guide"
    PLUGIN_CODE = "plugin_code"

@dataclass
class DatabaseDiscoveryRequest:
    """Request payload for Database Discovery Agent"""
    request_type: DiscoveryRequestType
    database_url: str
    database_name: Optional[str] = None
    api_key: Optional[str] = None
    sample_search_params: Optional[Dict[str, Any]] = None
    output_directory: Optional[str] = None
    # NEW: Flexible artifact specification
    artifacts_requested: List[ArtifactType] = None
    custom_options: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.artifacts_requested is None:
            # Default artifacts for backward compatibility
            self.artifacts_requested = [ArtifactType.CONFIG_FILE, ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]

@dataclass
class DatabaseDiscoveryResponse:
    """Response payload from Database Discovery Agent"""
    success: bool
    database_name: Optional[str] = None
    config_file_path: Optional[str] = None
    test_file_path: Optional[str] = None
    mock_data_path: Optional[str] = None
    validation_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    generated_files: List[str] = None
    
    def __post_init__(self):
        if self.generated_files is None:
            self.generated_files = []

# Ingestion Agent Protocols
@dataclass
class IngestionRequest:
    """Request payload for Ingestion Agent"""
    sources: List[str]  # List of sources to scrape
    force_refresh: bool = False
    include_faculty_data: bool = True
    include_funding_data: bool = True
    max_results_per_source: int = 100

@dataclass
class IngestionResponse:
    """Response payload from Ingestion Agent"""
    success: bool
    funding_opportunities_count: int = 0
    faculty_profiles_count: int = 0
    data_files: List[str] = None
    errors: List[str] = None
    processing_time_seconds: float = 0.0
    
    def __post_init__(self):
        if self.data_files is None:
            self.data_files = []
        if self.errors is None:
            self.errors = []

# Matcher Agent Protocols
@dataclass
class MatchingRequest:
    """Request payload for Matcher Agent"""
    faculty_data_file: str
    funding_data_file: str
    matching_criteria: Dict[str, Any]
    min_match_score: float = 0.5
    max_matches_per_faculty: int = 10

@dataclass
class Match:
    """Individual faculty-funding match"""
    faculty_id: str
    faculty_name: str
    opportunity_id: str
    opportunity_title: str
    match_score: float
    score_breakdown: Dict[str, float]
    reasoning: str

@dataclass
class MatchingResponse:
    """Response payload from Matcher Agent"""
    success: bool
    total_matches: int = 0
    matches: List[Match] = None
    matches_file: Optional[str] = None
    analytics: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.matches is None:
            self.matches = []

# Idea Generation Agent Protocols
class ProposalVariant(str, Enum):
    """Types of proposal variants"""
    CONSERVATIVE = "conservative"
    INNOVATIVE = "innovative"
    STRETCH = "stretch"

@dataclass
class IdeaGenerationRequest:
    """Request payload for Idea Generation Agent"""
    match: Match
    generate_variants: List[ProposalVariant]
    include_budget_estimates: bool = True
    include_timeline: bool = True
    include_methodology: bool = True

@dataclass
class ProposalIdea:
    """Generated proposal idea"""
    variant_type: ProposalVariant
    title: str
    abstract: str
    methodology: Optional[str] = None
    budget_estimate: Optional[Dict[str, float]] = None
    timeline_months: Optional[int] = None
    risk_level: str = "medium"
    innovation_score: float = 0.5

@dataclass
class IdeaGenerationResponse:
    """Response payload from Idea Generation Agent"""
    success: bool
    match_id: str
    proposal_ideas: List[ProposalIdea] = None
    llm_usage_stats: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.proposal_ideas is None:
            self.proposal_ideas = []

# Collaborator Agent Protocols
@dataclass
class CollaboratorRequest:
    """Request payload for Collaborator Agent"""
    target_faculty_id: str
    research_area: str
    institution_preference: Optional[str] = None
    max_collaborators: int = 5
    min_shared_publications: int = 0

@dataclass
class CollaboratorSuggestion:
    """Individual collaborator suggestion"""
    faculty_id: str
    name: str
    institution: str
    relevance_score: float
    shared_interests: List[str]
    recent_publications: List[str]
    collaboration_history: Optional[str] = None

@dataclass
class CollaboratorResponse:
    """Response payload from Collaborator Agent"""
    success: bool
    target_faculty_id: str
    suggestions: List[CollaboratorSuggestion] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []

# Notification Agent Protocols
class NotificationChannel(str, Enum):
    """Available notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    FILE = "file"

@dataclass
class NotificationRequest:
    """Request payload for Notification Agent"""
    recipient: str
    channel: NotificationChannel
    match: Match
    proposal_ideas: List[ProposalIdea]
    collaborator_suggestions: List[CollaboratorSuggestion]
    template: Optional[str] = None
    personalization_level: str = "high"

@dataclass
class NotificationResponse:
    """Response payload from Notification Agent"""
    success: bool
    notification_id: str
    channel_used: NotificationChannel
    delivery_status: str
    message_preview: Optional[str] = None

# Protocol Helper Functions
def create_a2a_request(
    source_agent: AgentType,
    target_agent: AgentType,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> A2AMessage:
    """Helper function to create A2A request messages"""
    return A2AMessage(
        message_type=MessageType.REQUEST,
        source_agent=source_agent,
        target_agent=target_agent,
        message_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        payload=payload,
        correlation_id=correlation_id
    )

def create_a2a_response(
    request_message: A2AMessage,
    payload: Dict[str, Any],
    success: bool = True
) -> A2AMessage:
    """Helper function to create A2A response messages"""
    return A2AMessage(
        message_type=MessageType.RESPONSE,
        source_agent=request_message.target_agent,
        target_agent=request_message.source_agent,
        message_id=str(uuid.uuid4()),
        timestamp=datetime.now().isoformat(),
        payload=payload,
        correlation_id=request_message.correlation_id,
        reply_to=request_message.message_id
    )

def create_discovery_message(
    source_agent: AgentType,
    request_type: DiscoveryRequestType,
    database_url: str,
    artifacts: List[ArtifactType] = None,
    **kwargs
) -> A2AMessage:
    """Helper to create Database Discovery Agent requests"""
    request_payload = DatabaseDiscoveryRequest(
        request_type=request_type,
        database_url=database_url,
        artifacts_requested=artifacts,
        **kwargs
    )
    
    return create_a2a_request(
        source_agent=source_agent,
        target_agent=AgentType.DATABASE_DISCOVERY,
        payload=asdict(request_payload)
    )

def create_artifact_generation_message(
    source_agent: AgentType,
    database_url: str,
    artifacts: List[ArtifactType],
    database_name: str = None,
    **kwargs
) -> A2AMessage:
    """Convenient helper for artifact generation requests"""
    return create_discovery_message(
        source_agent=source_agent,
        request_type=DiscoveryRequestType.GENERATE_ARTIFACTS,
        database_url=database_url,
        artifacts=artifacts,
        database_name=database_name,
        **kwargs
    )

def create_ingestion_message(
    source_agent: AgentType,
    sources: List[str],
    **kwargs
) -> A2AMessage:
    """Helper to create Ingestion Agent requests"""
    request_payload = IngestionRequest(
        sources=sources,
        **kwargs
    )
    
    return create_a2a_request(
        source_agent=source_agent,
        target_agent=AgentType.INGESTION,
        payload=asdict(request_payload)
    )

def create_matching_message(
    source_agent: AgentType,
    faculty_data_file: str,
    funding_data_file: str,
    **kwargs
) -> A2AMessage:
    """Helper to create Matcher Agent requests"""
    request_payload = MatchingRequest(
        faculty_data_file=faculty_data_file,
        funding_data_file=funding_data_file,
        matching_criteria=kwargs.get('matching_criteria', {}),
        **{k: v for k, v in kwargs.items() if k != 'matching_criteria'}
    )
    
    return create_a2a_request(
        source_agent=source_agent,
        target_agent=AgentType.MATCHER,
        payload=asdict(request_payload)
    )

# Message Validation
def validate_a2a_message(message_data: Dict[str, Any]) -> bool:
    """Validate A2A message format"""
    required_fields = ['message_type', 'source_agent', 'target_agent', 'message_id', 'timestamp', 'payload']
    
    for field in required_fields:
        if field not in message_data:
            return False
    
    # Validate enums
    try:
        MessageType(message_data['message_type'])
        AgentType(message_data['source_agent'])
        AgentType(message_data['target_agent'])
    except ValueError:
        return False
    
    return True

# Message Routing
class MessageRouter:
    """Routes A2A messages between agents"""
    
    def __init__(self):
        self.agents = {}
        self.message_log = []
    
    def register_agent(self, agent_type: AgentType, agent_instance):
        """Register an agent for message routing"""
        self.agents[agent_type] = agent_instance
    
    def route_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Route a message to the target agent"""
        if not validate_a2a_message(message.to_dict()):
            raise ValueError("Invalid A2A message format")
        
        self.message_log.append(message)
        
        target_agent = self.agents.get(message.target_agent)
        if not target_agent:
            error_response = create_a2a_response(
                message,
                {"error": f"Agent {message.target_agent} not found"},
                success=False
            )
            return error_response
        
        # Call the agent's process method
        try:
            if hasattr(target_agent, 'process_a2a_message'):
                response = target_agent.process_a2a_message(message)
                self.message_log.append(response)
                return response
            else:
                error_response = create_a2a_response(
                    message,
                    {"error": f"Agent {message.target_agent} does not support A2A protocol"},
                    success=False
                )
                return error_response
                
        except Exception as e:
            error_response = create_a2a_response(
                message,
                {"error": str(e)},
                success=False
            )
            return error_response

def main():
    """Example usage of A2A protocols"""
    
    # Example 1: Generate just config and tests (old approach)
    basic_msg = create_discovery_message(
        source_agent=AgentType.ADMIN_DASHBOARD,
        request_type=DiscoveryRequestType.GENERATE_ARTIFACTS,
        database_url="https://api.semanticscholar.org/graph/v1/paper/search",
        database_name="Semantic Scholar",
        artifacts=[ArtifactType.CONFIG_FILE, ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]
    )
    
    # Example 2: Generate everything including documentation (new flexibility)
    comprehensive_msg = create_artifact_generation_message(
        source_agent=AgentType.ADMIN_DASHBOARD,
        database_url="https://api.ieee.org/search",
        database_name="IEEE Xplore",
        artifacts=[
            ArtifactType.CONFIG_FILE,
            ArtifactType.TEST_FILE,
            ArtifactType.MOCK_DATA,
            ArtifactType.DOCUMENTATION,
            ArtifactType.INTEGRATION_GUIDE,
            ArtifactType.PLUGIN_CODE
        ]
    )
    
    # Example 3: Just documentation for existing database
    docs_only_msg = create_artifact_generation_message(
        source_agent=AgentType.ADMIN_DASHBOARD,
        database_url="https://api.crossref.org/works",
        database_name="Crossref",
        artifacts=[ArtifactType.DOCUMENTATION, ArtifactType.INTEGRATION_GUIDE]
    )
    
    print("Basic Discovery Request:")
    print(json.dumps(basic_msg.to_dict(), indent=2))
    
    print("\nComprehensive Discovery Request:")
    print(json.dumps(comprehensive_msg.to_dict(), indent=2))
    
    # Example: Request data ingestion
    ingestion_msg = create_ingestion_message(
        source_agent=AgentType.ADMIN_DASHBOARD,
        sources=["nih", "pcori", "nsf"],
        force_refresh=True
    )
    
    print("\nIngestion Request:")
    print(json.dumps(ingestion_msg.to_dict(), indent=2))

if __name__ == "__main__":
    main()