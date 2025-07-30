import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import requests

from src.agents.database_discovery_agent import (
    DatabaseDiscoveryAgent,
    DiscoveryRequest,
    DiscoveryResponse,
    RequestType
)
from src.core.a2a_protocols import (
    A2AMessage,
    MessageType,
    AgentType,
    create_discovery_message,
    DiscoveryRequestType
)

class TestDatabaseDiscoveryAgent:
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent instance with temporary directories"""
        config_dir = tmp_path / "config"
        test_dir = tmp_path / "tests"
        mock_data_dir = tmp_path / "tests" / "mock_data"
        
        return DatabaseDiscoveryAgent(
            config_dir=str(config_dir),
            test_dir=str(test_dir),
            mock_data_dir=str(mock_data_dir)
        )
    
    @pytest.fixture
    def sample_request(self):
        """Sample discovery request"""
        return DiscoveryRequest(
            request_type=RequestType.DISCOVER_API,
            database_url="https://api.example.com/search",
            database_name="Example Database"
        )
    
    @pytest.fixture
    def mock_api_response(self):
        """Mock API response data"""
        return {
            "results": [
                {
                    "title": "Sample Paper 1",
                    "authors": ["John Smith", "Jane Doe"],
                    "year": 2023,
                    "venue": "Sample Journal",
                    "citations": 15
                },
                {
                    "title": "Sample Paper 2",
                    "authors": ["Alice Brown"],
                    "year": 2022,
                    "venue": "Another Journal",
                    "citations": 8
                }
            ],
            "total": 2,
            "status": "success"
        }
    
    def test_agent_initialization(self, agent):
        """Test agent initializes correctly"""
        assert agent.config_dir.exists()
        assert agent.test_dir.exists()
        assert agent.mock_data_dir.exists()
        assert agent.mock_generator is not None
    
    def test_process_request_discover_api(self, agent, sample_request, mock_api_response):
        """Test API discovery request processing"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_get.return_value = mock_response
            
            response = agent.process_request(sample_request)
            
            assert response.success is True
            assert response.database_name == "Example Database"
            assert response.validation_results is not None
            assert 'working_params' in response.validation_results
            assert 'api_format' in response.validation_results
    
    def test_process_request_generate_artifacts_config_only(self, agent, tmp_path):
        """Test configuration generation using GENERATE_ARTIFACTS"""
        from src.agents.database_discovery_agent import ArtifactType
        
        request = DiscoveryRequest(
            request_type=RequestType.GENERATE_ARTIFACTS,
            database_url="https://api.example.com/search",
            database_name="Test Database",
            artifacts_requested=[ArtifactType.CONFIG_FILE]
        )
        
        with patch.object(agent, '_discover_api') as mock_discover:
            mock_discover.return_value = DiscoveryResponse(
                success=True,
                validation_results={'api_format': 'json', 'working_params': [{'q': 'test'}]}
            )
            
            response = agent.process_request(request)
            
            assert response.success is True
            assert ArtifactType.CONFIG_FILE in response.generated_artifacts
            config_path = response.generated_artifacts[ArtifactType.CONFIG_FILE]
            assert Path(config_path).exists()
            assert "test_database_config.yaml" in config_path
    
    def test_process_request_generate_artifacts_tests_only(self, agent):
        """Test test file generation using GENERATE_ARTIFACTS"""
        from src.agents.database_discovery_agent import ArtifactType
        
        request = DiscoveryRequest(
            request_type=RequestType.GENERATE_ARTIFACTS,
            database_url="https://api.example.com/search",
            database_name="Test Database",
            artifacts_requested=[ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]
        )
        
        response = agent.process_request(request)
        
        assert response.success is True
        assert ArtifactType.TEST_FILE in response.generated_artifacts
        assert ArtifactType.MOCK_DATA in response.generated_artifacts
        test_path = response.generated_artifacts[ArtifactType.TEST_FILE]
        mock_path = response.generated_artifacts[ArtifactType.MOCK_DATA]
        assert Path(test_path).exists()
        assert Path(mock_path).exists()
        assert len(response.generated_artifacts) == 2
    
    def test_process_request_generate_artifacts_default(self, agent):
        """Test generating default artifacts (config, tests, mock data)"""
        from src.agents.database_discovery_agent import ArtifactType
        
        request = DiscoveryRequest(
            request_type=RequestType.GENERATE_ARTIFACTS,
            database_url="https://api.example.com/search",
            database_name="Complete Database"
            # artifacts_requested defaults to [CONFIG_FILE, TEST_FILE, MOCK_DATA]
        )
        
        with patch.object(agent, '_discover_api') as mock_discover:
            mock_discover.return_value = DiscoveryResponse(
                success=True,
                validation_results={'api_format': 'json', 'working_params': [{}]}
            )
            
            response = agent.process_request(request)
            
            assert response.success is True
            assert ArtifactType.CONFIG_FILE in response.generated_artifacts
            assert ArtifactType.TEST_FILE in response.generated_artifacts
            assert ArtifactType.MOCK_DATA in response.generated_artifacts
            assert len(response.generated_artifacts) == 3
    
    def test_process_request_generate_artifacts_custom(self, agent):
        """Test generating custom artifact selection"""
        from src.agents.database_discovery_agent import ArtifactType
        
        request = DiscoveryRequest(
            request_type=RequestType.GENERATE_ARTIFACTS,
            database_url="https://api.example.com/search",
            database_name="Custom Database",
            artifacts_requested=[
                ArtifactType.CONFIG_FILE,
                ArtifactType.DOCUMENTATION,
                ArtifactType.INTEGRATION_GUIDE
            ]
        )
        
        with patch.object(agent, '_discover_api') as mock_discover:
            mock_discover.return_value = DiscoveryResponse(
                success=True,
                validation_results={'api_format': 'json', 'working_params': [{}]}
            )
            
            response = agent.process_request(request)
            
            assert response.success is True
            assert ArtifactType.CONFIG_FILE in response.generated_artifacts
            assert ArtifactType.DOCUMENTATION in response.generated_artifacts
            assert ArtifactType.INTEGRATION_GUIDE in response.generated_artifacts
            assert ArtifactType.TEST_FILE not in response.generated_artifacts  # Not requested
    
    @patch('requests.get')
    def test_validate_api_success(self, mock_get, agent):
        """Test API validation with successful response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {"results": [], "total": 0}
        mock_get.return_value = mock_response
        
        request = DiscoveryRequest(
            request_type=RequestType.VALIDATE_API,
            database_url="https://api.example.com/search",
            sample_search_params={'q': 'test'}
        )
        
        response = agent.process_request(request)
        
        assert response.success is True
        assert response.validation_results['status_code'] == 200
        assert response.validation_results['api_accessible'] is True
        assert response.validation_results['json_response'] is True
    
    @patch('requests.get')
    def test_validate_api_failure(self, mock_get, agent):
        """Test API validation with failed response"""
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        request = DiscoveryRequest(
            request_type=RequestType.VALIDATE_API,
            database_url="https://api.broken.com/search"
        )
        
        response = agent.process_request(request)
        
        assert response.success is False
        assert "Connection failed" in response.error_message
    
    def test_analyze_json_structure(self, agent):
        """Test JSON structure analysis"""
        test_data = {
            "results": [
                {
                    "title": "Test Paper",
                    "authors": [{"name": "John Doe"}],
                    "metadata": {
                        "year": 2023,
                        "citations": 10
                    }
                }
            ],
            "total": 1
        }
        
        structure = agent._analyze_json_structure(test_data)
        
        assert 'results' in structure
        assert 'total' in structure
        assert isinstance(structure['results'], list)
        assert len(structure['results']) == 1
    
    def test_detect_academic_fields(self, agent):
        """Test academic field detection"""
        from src.agents.database_discovery_agent import DatabaseType
        
        test_data = {
            "papers": [
                {
                    "title": "Research Paper",
                    "authors": ["John Smith"],
                    "publication_year": 2023,
                    "journal": "Science Journal",
                    "citation_count": 15,
                    "abstract": "This is a test abstract",
                    "doi": "10.1234/test"
                }
            ]
        }
        
        detected_fields = agent._detect_academic_fields(test_data, DatabaseType.FACULTY)
        
        expected_fields = ['title', 'authors', 'year', 'venue', 'citations', 'abstract', 'doi']
        for field in expected_fields:
            assert field in detected_fields
    
    def test_extract_name_from_url(self, agent):
        """Test database name extraction from URL"""
        test_cases = [
            ("https://api.semanticscholar.org/graph/v1/paper/search", "Semanticscholar"),
            ("https://www.arxiv.org/api/query", "Arxiv"),
            ("https://api.crossref.org/works", "Crossref"),
            ("https://example-database.com/search", "Example Database")
        ]
        
        for url, expected_name in test_cases:
            name = agent._extract_name_from_url(url)
            assert expected_name.lower() in name.lower()
    
    def test_create_database_config(self, agent):
        """Test database configuration creation"""
        from src.agents.database_discovery_agent import DatabaseType
        
        request = DiscoveryRequest(
            request_type=RequestType.GENERATE_ARTIFACTS,
            database_url="https://api.test.com/search",
            database_name="Test API",
            database_type=DatabaseType.FACULTY
        )
        
        discovery_results = {
            'working_params': [{'query': 'test'}],
            'api_format': 'json'
        }
        
        config = agent._create_database_config(request, discovery_results)
        
        assert config['name'] == "Test API"
        assert config['base_url'] == "https://api.test.com/search"
        assert 'param_mapping' in config
        assert 'result_mapping' in config
        assert config['param_mapping']['keywords'] == 'query'  # Should adapt based on working_params
    
    def test_generate_test_template(self, agent):
        """Test test template generation"""
        template = agent._generate_test_template("Example Database", "example_response.json")
        
        assert "TestExampleDatabasePlugin" in template
        assert "example_response.json" in template
        assert "def test_search_success" in template
        assert "def test_search_failure" in template
        assert "import pytest" in template
    
    def test_estimate_result_count(self, agent):
        """Test result count estimation"""
        test_cases = [
            ({"results": [1, 2, 3]}, 3),
            ({"data": [1, 2]}, 2),
            ({"items": [1]}, 1),
            ({"papers": []}, 0),
            ({"some_field": "value"}, 1),
            ([1, 2, 3, 4], 4)
        ]
        
        for test_data, expected_count in test_cases:
            count = agent._estimate_result_count(test_data)
            assert count == expected_count
    
    def test_unknown_request_type(self, agent):
        """Test handling of unknown request types"""
        request = DiscoveryRequest(
            request_type="invalid_type",
            database_url="https://api.example.com"
        )
        
        # This should be caught by the enum validation, but let's test error handling
        with pytest.raises(ValueError):
            RequestType("invalid_type")
    
    def test_error_handling(self, agent):
        """Test error handling in request processing"""
        from src.agents.database_discovery_agent import ArtifactType
        
        # Test error handling when discovery fails for discovery-dependent artifacts
        request = DiscoveryRequest(
            request_type=RequestType.GENERATE_ARTIFACTS,
            database_url="https://api.example.com/search",
            database_name="Test",
            artifacts_requested=[ArtifactType.DOCUMENTATION]  # This requires discovery
        )
        
        # Mock _discover_api to raise an exception
        with patch.object(agent, '_discover_api', side_effect=Exception("Mock discovery error")):
            response = agent.process_request(request)
            
            # Should handle error gracefully and report failure
            assert response.success is False
            assert "Mock discovery error" in response.error_message

class TestA2AIntegration:
    """Test A2A protocol integration"""
    
    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent instance"""
        return DatabaseDiscoveryAgent(
            config_dir=str(tmp_path / "config"),
            test_dir=str(tmp_path / "tests"),
            mock_data_dir=str(tmp_path / "mock_data")
        )
    
    def test_a2a_message_creation(self):
        """Test A2A message creation helper"""
        message = create_discovery_message(
            source_agent=AgentType.ADMIN_DASHBOARD,
            request_type=DiscoveryRequestType.GENERATE_ARTIFACTS,
            database_url="https://api.example.com",
            database_name="Test API"
        )
        
        assert message.source_agent == AgentType.ADMIN_DASHBOARD
        assert message.target_agent == AgentType.DATABASE_DISCOVERY
        assert message.message_type == MessageType.REQUEST
        assert message.payload['request_type'] == DiscoveryRequestType.GENERATE_ARTIFACTS
        assert message.payload['database_url'] == "https://api.example.com"
    
    def test_a2a_message_processing(self, agent):
        """Test processing A2A messages"""
        # Create an A2A message
        message = create_discovery_message(
            source_agent=AgentType.INGESTION,
            request_type=DiscoveryRequestType.VALIDATE_API,
            database_url="https://api.example.com",
            database_name="Test Database"
        )
        
        # Add process_a2a_message method to agent for testing
        def process_a2a_message(self, message: A2AMessage) -> A2AMessage:
            from src.core.a2a_protocols import create_a2a_response
            from dataclasses import asdict
            
            request = DiscoveryRequest(**message.payload)
            response = self.process_request(request)
            
            return create_a2a_response(
                message,
                asdict(response),
                success=response.success
            )
        
        # Monkey patch the method
        DatabaseDiscoveryAgent.process_a2a_message = process_a2a_message
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_response.headers = {'content-type': 'application/json'}
            mock_response.json.return_value = {"test": "data"}
            mock_get.return_value = mock_response
            
            response_message = agent.process_a2a_message(message)
            
            assert response_message.message_type == MessageType.RESPONSE
            assert response_message.source_agent == AgentType.DATABASE_DISCOVERY
            assert response_message.target_agent == AgentType.INGESTION
            assert response_message.reply_to == message.message_id

def main():
    """Run tests manually"""
    pytest.main([__file__, "-v"])

if __name__ == "__main__":
    main()