from typing import Dict, Any, List, Optional, Literal
import json
import yaml
import requests
from pathlib import Path
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from enum import Enum

from ..tools.mock_data_generator import MockDataGenerator
from ..tools.database_plugins import GenericAPIPlugin

logger = logging.getLogger(__name__)

class RequestType(str, Enum):
    """Types of requests the Database Discovery Agent can handle"""
    DISCOVER_API = "discover_api"
    VALIDATE_API = "validate_api"
    GENERATE_ARTIFACTS = "generate_artifacts"

class ArtifactType(str, Enum):
    """Types of artifacts the agent can generate"""
    CONFIG_FILE = "config_file"
    TEST_FILE = "test_file"
    MOCK_DATA = "mock_data"
    DOCUMENTATION = "documentation"
    INTEGRATION_GUIDE = "integration_guide"
    PLUGIN_CODE = "plugin_code"

class DatabaseType(str, Enum):
    """Types of databases the agent can discover"""
    FACULTY = "faculty"          # Academic publication databases (APIs)
    FUNDING = "funding"          # Funding opportunity sources (APIs or websites)
    HYBRID = "hybrid"           # Sources with both faculty and funding data

@dataclass
class DiscoveryRequest:
    """Request message for Database Discovery Agent"""
    request_type: RequestType
    database_url: str
    database_type: DatabaseType = DatabaseType.FACULTY
    database_name: Optional[str] = None
    api_key: Optional[str] = None
    sample_search_params: Optional[Dict[str, Any]] = None
    output_directory: Optional[str] = None
    request_id: Optional[str] = None
    # NEW: Flexible artifact specification
    artifacts_requested: List[ArtifactType] = None  # If None, defaults to [CONFIG_FILE, TEST_FILE, MOCK_DATA]
    custom_options: Optional[Dict[str, Any]] = None  # For future extensibility
    
    def __post_init__(self):
        if self.artifacts_requested is None:
            # Default artifacts for backward compatibility
            self.artifacts_requested = [ArtifactType.CONFIG_FILE, ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]

@dataclass
class DiscoveryResponse:
    """Response message from Database Discovery Agent"""
    success: bool
    request_id: Optional[str] = None
    database_name: Optional[str] = None
    validation_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
    # NEW: Flexible artifact results
    generated_artifacts: Dict[ArtifactType, str] = None  # Maps artifact type to file path
    artifact_metadata: Dict[ArtifactType, Dict[str, Any]] = None  # Additional info per artifact
    
    def __post_init__(self):
        if self.generated_artifacts is None:
            self.generated_artifacts = {}
        if self.artifact_metadata is None:
            self.artifact_metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def get_artifact_path(self, artifact_type: ArtifactType) -> Optional[str]:
        """Get the file path for a specific artifact type"""
        return self.generated_artifacts.get(artifact_type)
    
    def get_all_generated_files(self) -> List[str]:
        """Get list of all generated file paths"""
        return list(self.generated_artifacts.values())

class DatabaseDiscoveryAgent:
    """
    Agent responsible for discovering new academic databases and generating
    configuration files, tests, and mock data automatically.
    
    Supports A2A (Agent-to-Agent) communication protocol.
    """
    
    def __init__(self, config_dir: str = "config", test_dir: str = "tests", mock_data_dir: str = "tests/mock_data"):
        self.config_dir = Path(config_dir)
        self.test_dir = Path(test_dir)
        self.mock_data_dir = Path(mock_data_dir)
        self.mock_generator = MockDataGenerator()
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.mock_data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Database Discovery Agent initialized")
    
    def process_request(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """
        Main entry point for processing A2A requests
        """
        logger.info(f"Processing {request.request_type} request for {request.database_url}")
        
        try:
            if request.request_type == RequestType.DISCOVER_API:
                return self._discover_api(request)
            elif request.request_type == RequestType.VALIDATE_API:
                return self._validate_api(request)
            elif request.request_type == RequestType.GENERATE_ARTIFACTS:
                return self._generate_artifacts(request)
            else:
                return DiscoveryResponse(
                    success=False,
                    request_id=request.request_id,
                    error_message=f"Unknown request type: {request.request_type}"
                )
                
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return DiscoveryResponse(
                success=False,
                request_id=request.request_id,
                error_message=str(e)
            )
    
    def _discover_api(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Analyze an API URL and attempt to discover its structure"""
        
        try:
            # Try to call the API with minimal parameters
            headers = {'Accept': 'application/json', 'User-Agent': 'Academic Research Tool/1.0'}
            
            # Try common parameter patterns
            test_params = [
                {'q': 'test'},
                {'query': 'test'},
                {'search': 'test'},
                {'author': 'smith'},
                {}  # No parameters
            ]
            
            discovery_results = {
                'url': request.database_url,
                'working_params': [],
                'response_structure': None,
                'detected_fields': [],
                'api_format': 'unknown'
            }
            
            for params in test_params:
                try:
                    response = requests.get(request.database_url, params=params, headers=headers, timeout=10)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            discovery_results['working_params'].append(params)
                            discovery_results['response_structure'] = self._analyze_json_structure(data)
                            discovery_results['api_format'] = 'json'
                            discovery_results['detected_fields'] = self._detect_academic_fields(data, request.database_type)
                            break
                        except json.JSONDecodeError:
                            discovery_results['api_format'] = 'non-json'
                            
                except requests.RequestException:
                    continue
            
            return DiscoveryResponse(
                success=True,
                request_id=request.request_id,
                database_name=request.database_name,
                validation_results=discovery_results
            )
            
        except Exception as e:
            return DiscoveryResponse(
                success=False,
                request_id=request.request_id,
                error_message=f"API discovery failed: {e}"
            )
    
    def _generate_artifacts(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Generate requested artifacts for a database"""
        logger.info(f"Generating artifacts: {[a.value for a in request.artifacts_requested]}")
        
        try:
            if not request.database_name:
                request.database_name = self._extract_name_from_url(request.database_url)
            
            response = DiscoveryResponse(
                success=True,
                request_id=request.request_id,
                database_name=request.database_name
            )
            
            # Run discovery if we need it for any artifact
            discovery_results = None
            if any(artifact in [ArtifactType.CONFIG_FILE, ArtifactType.DOCUMENTATION, ArtifactType.INTEGRATION_GUIDE] 
                   for artifact in request.artifacts_requested):
                discovery_response = self._discover_api(request)
                if discovery_response.success:
                    discovery_results = discovery_response.validation_results
            
            # Generate each requested artifact
            for artifact_type in request.artifacts_requested:
                try:
                    if artifact_type == ArtifactType.CONFIG_FILE:
                        file_path = self._generate_config_file(request, discovery_results)
                        response.generated_artifacts[artifact_type] = file_path
                        response.artifact_metadata[artifact_type] = {"type": "yaml", "format": "database_config"}
                        
                    elif artifact_type == ArtifactType.TEST_FILE:
                        file_path = self._generate_test_file(request)
                        response.generated_artifacts[artifact_type] = file_path
                        response.artifact_metadata[artifact_type] = {"type": "python", "framework": "pytest"}
                        
                    elif artifact_type == ArtifactType.MOCK_DATA:
                        file_path = self._generate_mock_data_file(request)
                        response.generated_artifacts[artifact_type] = file_path
                        response.artifact_metadata[artifact_type] = {"type": "json", "format": "api_response"}
                        
                    elif artifact_type == ArtifactType.DOCUMENTATION:
                        file_path = self._generate_documentation(request, discovery_results)
                        response.generated_artifacts[artifact_type] = file_path
                        response.artifact_metadata[artifact_type] = {"type": "markdown", "sections": ["usage", "api", "examples"]}
                        
                    elif artifact_type == ArtifactType.INTEGRATION_GUIDE:
                        file_path = self._generate_integration_guide(request, discovery_results)
                        response.generated_artifacts[artifact_type] = file_path
                        response.artifact_metadata[artifact_type] = {"type": "markdown", "sections": ["setup", "integration", "troubleshooting"]}
                        
                    elif artifact_type == ArtifactType.PLUGIN_CODE:
                        file_path = self._generate_plugin_code(request, discovery_results)
                        response.generated_artifacts[artifact_type] = file_path
                        response.artifact_metadata[artifact_type] = {"type": "python", "class": "DatabasePlugin"}
                        
                    else:
                        logger.warning(f"Unknown artifact type: {artifact_type}")
                        
                except Exception as e:
                    logger.error(f"Failed to generate {artifact_type}: {e}")
                    # Continue with other artifacts instead of failing completely
            
            if not response.generated_artifacts:
                response.success = False
                response.error_message = "No artifacts were successfully generated"
            
            return response
            
        except Exception as e:
            return DiscoveryResponse(
                success=False,
                request_id=request.request_id,
                error_message=f"Artifact generation failed: {e}"
            )
    
    def _generate_config_file(self, request: DiscoveryRequest, discovery_results: Optional[Dict[str, Any]]) -> str:
        """Generate configuration file for a database"""
        config = self._create_database_config(request, discovery_results)
        
        config_filename = f"{request.database_name.lower().replace(' ', '_')}_config.yaml"
        config_path = self.config_dir / config_filename
        
        with open(config_path, 'w') as f:
            yaml.dump({'databases': [config]}, f, indent=2)
        
        logger.info(f"Generated config file: {config_path}")
        return str(config_path)
    
    def _generate_test_file(self, request: DiscoveryRequest) -> str:
        """Generate test file for a database"""
        test_filename = f"test_{request.database_name.lower().replace(' ', '_')}_plugin.py"
        test_path = self.test_dir / test_filename
        
        mock_filename = f"{request.database_name.lower().replace(' ', '_')}_api_response.json"
        test_content = self._generate_test_template(request.database_name, mock_filename)
        
        with open(test_path, 'w') as f:
            f.write(test_content)
        
        logger.info(f"Generated test file: {test_path}")
        return str(test_path)
    
    def _generate_mock_data_file(self, request: DiscoveryRequest) -> str:
        """Generate mock data file for a database"""
        mock_filename = f"{request.database_name.lower().replace(' ', '_')}_api_response.json"
        mock_path = self.mock_data_dir / mock_filename
        
        mock_data = self.mock_generator.generate_mock_response({
            'name': request.database_name,
            'base_url': request.database_url,
            'result_mapping': self._get_result_mapping_for_type(request.database_type),
            'data_path': ['results']
        })
        
        with open(mock_path, 'w') as f:
            json.dump(mock_data, f, indent=2)
        
        logger.info(f"Generated mock data: {mock_path}")
        return str(mock_path)
    
    def _generate_documentation(self, request: DiscoveryRequest, discovery_results: Optional[Dict[str, Any]]) -> str:
        """Generate documentation for a database integration"""
        doc_filename = f"{request.database_name.lower().replace(' ', '_')}_documentation.md"
        doc_path = self.config_dir.parent / "docs" / doc_filename
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        
        doc_content = f"""# {request.database_name} Integration Documentation

## Overview
This document describes the integration with {request.database_name} API.

## Configuration
- **Base URL**: `{request.database_url}`
- **Database Type**: {request.database_type.value}
- **API Key Required**: {'Yes' if request.api_key else 'No'}

## Usage
```python
from src.tools.database_plugins import GenericAPIPlugin

config = {{
    'name': '{request.database_name}',
    'base_url': '{request.database_url}',
    'database_type': '{request.database_type.value}'
}}

plugin = GenericAPIPlugin(config)
results = plugin.search({{'author': 'John Smith'}})
```

## API Structure
{json.dumps(discovery_results.get('response_structure', {}), indent=2) if discovery_results else 'Structure analysis not available'}

## Generated Files
- Configuration: Auto-generated in config/
- Tests: Auto-generated in tests/
- Mock Data: Auto-generated in tests/mock_data/

---
*Generated automatically by Database Discovery Agent*
"""
        
        with open(doc_path, 'w') as f:
            f.write(doc_content)
        
        logger.info(f"Generated documentation: {doc_path}")
        return str(doc_path)
    
    def _generate_integration_guide(self, request: DiscoveryRequest, discovery_results: Optional[Dict[str, Any]]) -> str:
        """Generate integration guide for a database"""
        guide_filename = f"{request.database_name.lower().replace(' ', '_')}_integration_guide.md"
        guide_path = self.config_dir.parent / "docs" / guide_filename
        guide_path.parent.mkdir(parents=True, exist_ok=True)
        
        guide_content = f"""# {request.database_name} Integration Guide

## Quick Setup

### 1. Add to Ingestion Agent
```python
result = ingestion_agent.add_new_database(
    database_url="{request.database_url}",
    database_name="{request.database_name}",
    database_type="{request.database_type.value}"
)
```

### 2. Manual Configuration (if needed)
Edit the generated config file and adjust:
- Parameter mappings
- Result field mappings  
- Rate limiting settings

### 3. Test the Integration
```bash
pytest tests/test_{request.database_name.lower().replace(' ', '_')}_plugin.py -v
```

## Troubleshooting

### Common Issues
- **Rate Limiting**: Adjust `rate_limit_delay` in config
- **Authentication**: Add API key if required
- **Field Mapping**: Update `result_mapping` for correct data extraction

### API Validation
```python
from src.agents.database_discovery_agent import DatabaseDiscoveryAgent

agent = DatabaseDiscoveryAgent()
request = DiscoveryRequest(
    request_type=RequestType.VALIDATE_API,
    database_url="{request.database_url}",
    database_name="{request.database_name}"
)
result = agent.process_request(request)
```

---
*Generated automatically by Database Discovery Agent*
"""
        
        with open(guide_path, 'w') as f:
            f.write(guide_content)
        
        logger.info(f"Generated integration guide: {guide_path}")
        return str(guide_path)
    
    def _generate_plugin_code(self, request: DiscoveryRequest, discovery_results: Optional[Dict[str, Any]]) -> str:
        """Generate custom plugin code for a database"""
        plugin_filename = f"{request.database_name.lower().replace(' ', '_')}_plugin.py"
        plugin_path = self.config_dir.parent / "src" / "plugins" / plugin_filename
        plugin_path.parent.mkdir(parents=True, exist_ok=True)
        
        class_name = ''.join(word.capitalize() for word in request.database_name.split())
        
        plugin_content = f'''"""
Custom plugin for {request.database_name}
Generated automatically by Database Discovery Agent
"""

from typing import List, Dict, Any
import requests
from ..tools.database_plugins import DatabasePlugin, SearchResult

class {class_name}Plugin(DatabasePlugin):
    """Custom plugin for {request.database_name}"""
    
    @property
    def name(self) -> str:
        return "{request.database_name}"
    
    @property
    def base_url(self) -> str:
        return "{request.database_url}"
    
    @property
    def requires_api_key(self) -> bool:
        return {"True" if request.api_key else "False"}
    
    def search(self, query_params: Dict[str, Any]) -> List[SearchResult]:
        """Custom search implementation for {request.database_name}"""
        results = []
        
        try:
            # TODO: Implement custom search logic here
            # This is a template - customize based on API requirements
            
            headers = self.get_headers()
            {"headers['Authorization'] = f'Bearer {request.api_key}'" if request.api_key else ""}
            
            response = requests.get(
                self.base_url,
                params=query_params,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # TODO: Parse response and create SearchResult objects
            # Example:
            # for item in data.get('results', []):
            #     result = SearchResult(
            #         title=item.get('title', ''),
            #         authors=item.get('authors', []),
            #         # ... other fields
            #     )
            #     results.append(result)
            
        except Exception as e:
            print(f"Error searching {request.database_name}: {{e}}")
            
        return results
'''
        
        with open(plugin_path, 'w') as f:
            f.write(plugin_content)
        
        logger.info(f"Generated plugin code: {plugin_path}")
        return str(plugin_path)
    
    def _get_result_mapping_for_type(self, database_type: DatabaseType) -> Dict[str, str]:
        """Get appropriate result mapping based on database type"""
        if database_type == DatabaseType.FACULTY:
            return self._get_faculty_result_mapping()
        elif database_type == DatabaseType.FUNDING:
            return self._get_funding_result_mapping()
        else:
            return self._get_hybrid_result_mapping()
    
    def _old_generate_tests(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Generate test files and mock data for a database"""
        
        try:
            if not request.database_name:
                request.database_name = self._extract_name_from_url(request.database_url)
            
            # Generate mock data
            mock_filename = f"{request.database_name.lower().replace(' ', '_')}_api_response.json"
            mock_path = self.mock_data_dir / mock_filename
            
            mock_data = self.mock_generator.generate_mock_response({
                'name': request.database_name,
                'base_url': request.database_url,
                'result_mapping': self._get_default_result_mapping(),
                'data_path': ['results']
            })
            
            with open(mock_path, 'w') as f:
                json.dump(mock_data, f, indent=2)
            
            # Generate test file
            test_filename = f"test_{request.database_name.lower().replace(' ', '_')}_plugin.py"
            test_path = self.test_dir / test_filename
            
            test_content = self._generate_test_template(request.database_name, mock_filename)
            
            with open(test_path, 'w') as f:
                f.write(test_content)
            
            return DiscoveryResponse(
                success=True,
                request_id=request.request_id,
                database_name=request.database_name,
                test_file_path=str(test_path),
                mock_data_path=str(mock_path),
                generated_files=[str(test_path), str(mock_path)]
            )
            
        except Exception as e:
            return DiscoveryResponse(
                success=False,
                request_id=request.request_id,
                error_message=f"Test generation failed: {e}"
            )
    
    def _generate_both(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Generate both configuration and test files"""
        
        try:
            # Generate config
            config_response = self._generate_config(request)
            if not config_response.success:
                return config_response
            
            # Generate tests
            test_response = self._generate_tests(request)
            if not test_response.success:
                return test_response
            
            # Combine responses
            return DiscoveryResponse(
                success=True,
                request_id=request.request_id,
                database_name=request.database_name,
                config_file_path=config_response.config_file_path,
                test_file_path=test_response.test_file_path,
                mock_data_path=test_response.mock_data_path,
                generated_files=config_response.generated_files + test_response.generated_files
            )
            
        except Exception as e:
            return DiscoveryResponse(
                success=False,
                request_id=request.request_id,
                error_message=f"Generation failed: {e}"
            )
    
    def _validate_api(self, request: DiscoveryRequest) -> DiscoveryResponse:
        """Validate that an API is working and accessible"""
        
        try:
            test_params = request.sample_search_params or {'q': 'test'}
            headers = {'Accept': 'application/json', 'User-Agent': 'Academic Research Tool/1.0'}
            
            if request.api_key:
                headers['Authorization'] = f"Bearer {request.api_key}"
            
            response = requests.get(request.database_url, params=test_params, headers=headers, timeout=10)
            
            validation_results = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'content_type': response.headers.get('content-type', ''),
                'api_accessible': response.status_code == 200,
                'json_response': False,
                'estimated_results': 0
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    validation_results['json_response'] = True
                    validation_results['response_structure'] = self._analyze_json_structure(data)
                    validation_results['estimated_results'] = self._estimate_result_count(data)
                except json.JSONDecodeError:
                    validation_results['json_response'] = False
            
            return DiscoveryResponse(
                success=True,
                request_id=request.request_id,
                database_name=request.database_name,
                validation_results=validation_results
            )
            
        except Exception as e:
            return DiscoveryResponse(
                success=False,
                request_id=request.request_id,
                error_message=f"API validation failed: {e}"
            )
    
    def _analyze_json_structure(self, data: Any, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze the structure of a JSON response"""
        
        def analyze_recursive(obj, depth=0):
            if depth > max_depth:
                return "max_depth_reached"
            
            if isinstance(obj, dict):
                return {key: analyze_recursive(value, depth + 1) for key, value in list(obj.items())[:10]}
            elif isinstance(obj, list):
                if obj:
                    return [analyze_recursive(obj[0], depth + 1)]
                return []
            else:
                return type(obj).__name__
        
        return analyze_recursive(data)
    
    def _detect_academic_fields(self, data: Any, database_type: DatabaseType) -> List[str]:
        """Detect common academic or funding fields in the response"""
        
        def search_keys(obj, found_keys=None):
            if found_keys is None:
                found_keys = set()
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    found_keys.add(key.lower())
                    search_keys(value, found_keys)
            elif isinstance(obj, list) and obj:
                search_keys(obj[0], found_keys)
            
            return found_keys
        
        all_keys = search_keys(data)
        
        if database_type == DatabaseType.FACULTY:
            # Academic/Faculty fields
            field_mappings = {
                'title': ['title', 'name', 'heading'],
                'authors': ['authors', 'author', 'creator', 'writers'],
                'year': ['year', 'date', 'published', 'publication_year'],
                'venue': ['venue', 'journal', 'conference', 'publication'],
                'citations': ['citations', 'cited_by', 'citedby', 'citation_count'],
                'abstract': ['abstract', 'summary', 'description'],
                'doi': ['doi', 'identifier', 'id'],
                'url': ['url', 'link', 'href']
            }
        elif database_type == DatabaseType.FUNDING:
            # Funding opportunity fields
            field_mappings = {
                'title': ['title', 'name', 'opportunity_title', 'grant_title'],
                'description': ['description', 'summary', 'abstract', 'overview'],
                'deadline': ['deadline', 'due_date', 'application_deadline', 'closing_date'],
                'funding_amount': ['amount', 'funding_amount', 'award_amount', 'budget'],
                'agency': ['agency', 'sponsor', 'funder', 'organization'],
                'program': ['program', 'initiative', 'scheme', 'call'],
                'eligibility': ['eligibility', 'requirements', 'criteria'],
                'url': ['url', 'link', 'href', 'application_url'],
                'status': ['status', 'state', 'active', 'open']
            }
        else:  # HYBRID
            # Combined fields
            field_mappings = {
                'title': ['title', 'name', 'heading', 'opportunity_title'],
                'description': ['description', 'summary', 'abstract', 'overview'],
                'authors': ['authors', 'author', 'creator'],
                'deadline': ['deadline', 'due_date', 'application_deadline'],
                'funding_amount': ['amount', 'funding_amount', 'award_amount'],
                'year': ['year', 'date', 'published'],
                'url': ['url', 'link', 'href']
            }
        
        detected = []
        for field, possible_keys in field_mappings.items():
            if any(key in all_keys for key in possible_keys):
                detected.append(field)
        
        return detected
    
    def _create_database_config(self, request: DiscoveryRequest, discovery_results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a database configuration based on discovery results"""
        
        config = {
            'name': request.database_name,
            'base_url': request.database_url,
            'requires_api_key': bool(request.api_key),
            'rate_limit_delay': 1.0,
            'database_type': request.database_type.value,
            'data_path': ['results'],
            'default_params': {
                'format': 'json',
                'limit': 20
            }
        }
        
        # Set appropriate mappings based on database type
        if request.database_type == DatabaseType.FACULTY:
            config['param_mapping'] = {
                'author': 'author',
                'keywords': 'q',
                'institution': 'affiliation'
            }
            config['result_mapping'] = self._get_faculty_result_mapping()
        elif request.database_type == DatabaseType.FUNDING:
            config['param_mapping'] = {
                'keywords': 'q',
                'agency': 'agency',
                'program': 'program',
                'deadline_from': 'from_date',
                'deadline_to': 'to_date'
            }
            config['result_mapping'] = self._get_funding_result_mapping()
            # Funding sources often use different endpoints
            config['selectors'] = self._get_funding_selectors()  # For web scraping fallback
        else:  # HYBRID
            config['param_mapping'] = {
                'keywords': 'q',
                'author': 'author',
                'agency': 'agency'
            }
            config['result_mapping'] = self._get_hybrid_result_mapping()
        
        # Customize based on discovery results
        if discovery_results and discovery_results.get('working_params'):
            working_params = discovery_results['working_params'][0]
            if 'query' in working_params:
                config['param_mapping']['keywords'] = 'query'
            elif 'search' in working_params:
                config['param_mapping']['keywords'] = 'search'
        
        return config
    
    def _get_faculty_result_mapping(self) -> Dict[str, str]:
        """Get field mappings for academic/faculty data"""
        return {
            'title': 'title',
            'authors': 'authors',
            'year': 'year',
            'venue': 'venue',
            'citations': 'citations',
            'url': 'url',
            'abstract': 'abstract',
            'doi': 'doi'
        }
    
    def _get_funding_result_mapping(self) -> Dict[str, str]:
        """Get field mappings for funding opportunity data"""
        return {
            'title': 'title',
            'description': 'description',
            'deadline': 'deadline',
            'funding_amount': 'funding_amount',
            'agency': 'agency',
            'program': 'program',
            'eligibility': 'eligibility',
            'url': 'url',
            'status': 'status'
        }
    
    def _get_hybrid_result_mapping(self) -> Dict[str, str]:
        """Get field mappings for hybrid data sources"""
        return {
            'title': 'title',
            'description': 'description',
            'authors': 'authors',
            'year': 'year',
            'deadline': 'deadline',
            'funding_amount': 'funding_amount',
            'url': 'url'
        }
    
    def _get_funding_selectors(self) -> Dict[str, str]:
        """Get CSS selectors for funding website scraping fallback"""
        return {
            'container': '.funding-opportunity, .grant-listing, .opportunity-item',
            'title': 'h1, h2, h3, .title, .opportunity-title',
            'title_link': 'h1 a, h2 a, h3 a, .title a',
            'description': '.description, .summary, .abstract, .overview',
            'deadline': '.deadline, .due-date, .closing-date, .application-deadline',
            'funding_amount': '.amount, .funding-amount, .award-amount, .budget',
            'agency': '.agency, .sponsor, .funder, .organization',
            'program': '.program, .initiative, .scheme'
        }
    
    def _generate_test_template(self, database_name: str, mock_filename: str) -> str:
        """Generate a test file template"""
        
        class_name = database_name.replace(' ', '').replace('-', '')
        
        return f'''import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

from src.tools.database_plugins import GenericAPIPlugin

class Test{class_name}Plugin:
    """Tests for {database_name} database plugin"""
    
    @pytest.fixture
    def mock_response_data(self):
        """Load mock response data"""
        mock_file = Path(__file__).parent / "mock_data" / "{mock_filename}"
        with open(mock_file, 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def plugin_config(self):
        """Plugin configuration"""
        return {{
            'name': '{database_name}',
            'base_url': 'https://api.example.com/search',
            'param_mapping': {{
                'author': 'author',
                'keywords': 'q'
            }},
            'result_mapping': {{
                'title': 'title',
                'authors': 'authors',
                'year': 'year'
            }},
            'data_path': ['results']
        }}
    
    @pytest.fixture
    def plugin(self, plugin_config):
        """Create plugin instance"""
        from src.tools.database_plugins import GenericAPIPlugin
        return GenericAPIPlugin(plugin_config)
    
    @patch('requests.get')
    def test_search_success(self, mock_get, plugin, mock_response_data):
        """Test successful search"""
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        query_params = {{'author': 'John Smith'}}
        results = plugin.search(query_params)
        
        assert len(results) > 0
        assert results[0].title is not None
        assert len(results[0].authors) > 0
    
    @patch('requests.get')
    def test_search_failure(self, mock_get, plugin):
        """Test search failure handling"""
        mock_get.side_effect = Exception("API Error")
        
        query_params = {{'author': 'John Smith'}}
        results = plugin.search(query_params)
        
        assert results == []  # Should return empty list on error
    
    def test_plugin_properties(self, plugin):
        """Test plugin basic properties"""
        assert plugin.name == '{database_name}'
        assert plugin.base_url is not None
        assert plugin.rate_limit_delay >= 0
'''
    
    def _extract_name_from_url(self, url: str) -> str:
        """Extract a reasonable database name from URL"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove common prefixes
        domain = domain.replace('www.', '').replace('api.', '')
        
        # Extract main part
        parts = domain.split('.')
        if len(parts) >= 2:
            name = parts[0]
        else:
            name = domain
        
        # Clean up and title case
        name = name.replace('-', ' ').replace('_', ' ').title()
        
        return name
    
    def _estimate_result_count(self, data: Any) -> int:
        """Estimate number of results in response"""
        
        def count_items(obj):
            if isinstance(obj, list):
                return len(obj)
            elif isinstance(obj, dict):
                # Look for common result array names
                result_keys = ['results', 'data', 'items', 'papers', 'articles', 'entries']
                for key in result_keys:
                    if key in obj and isinstance(obj[key], list):
                        return len(obj[key])
                # If no obvious result array, count dict items
                return len(obj)
            return 0
        
        return count_items(data)

# A2A Protocol Helper Functions
def create_discovery_request(request_type: str, database_url: str, **kwargs) -> Dict[str, Any]:
    """Helper function to create A2A request messages"""
    request = DiscoveryRequest(
        request_type=RequestType(request_type),
        database_url=database_url,
        **kwargs
    )
    return asdict(request)

def parse_discovery_response(response_data: Dict[str, Any]) -> DiscoveryResponse:
    """Helper function to parse A2A response messages"""
    return DiscoveryResponse(**response_data)

def main():
    """Example usage and testing"""
    agent = DatabaseDiscoveryAgent()
    
    # Example: Discover Semantic Scholar API
    request = DiscoveryRequest(
        request_type=RequestType.GENERATE_BOTH,
        database_url="https://api.semanticscholar.org/graph/v1/paper/search",
        database_name="Semantic Scholar",
        sample_search_params={"query": "machine learning", "limit": 5}
    )
    
    response = agent.process_request(request)
    
    if response.success:
        print(f"✅ Successfully processed {request.database_name}")
        print(f"Generated files: {response.generated_files}")
    else:
        print(f"❌ Failed: {response.error_message}")

if __name__ == "__main__":
    main()