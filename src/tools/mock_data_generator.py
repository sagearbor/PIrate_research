#!/usr/bin/env python3
"""
Automatic Mock Data Generator for New Databases

This script helps you quickly generate mock test data for new databases
without needing to understand their API structure.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
import requests
from datetime import datetime

class MockDataGenerator:
    """Generates mock test data for database APIs"""
    
    def __init__(self):
        self.mock_papers = [
            {
                "title": "Machine Learning Applications in Healthcare: A Comprehensive Review",
                "authors": ["Dr. John Smith", "Dr. Sarah Johnson", "Dr. Michael Brown"],
                "year": 2023,
                "venue": "Nature Medicine",
                "abstract": "This comprehensive review examines the current state and future prospects of machine learning applications in healthcare, covering diagnostic imaging, drug discovery, and personalized treatment.",
                "citations": 156,
                "doi": "10.1038/s41591-023-01234-x",
                "keywords": ["machine learning", "healthcare", "medical AI", "diagnosis"]
            },
            {
                "title": "Privacy-Preserving Federated Learning in Medical Research",
                "authors": ["Dr. John Smith", "Dr. Alice Wilson", "Dr. Robert Davis"],
                "year": 2022,
                "venue": "Journal of Medical Internet Research",
                "abstract": "We present novel approaches for federated learning that maintain patient privacy while enabling collaborative medical research across institutions.",
                "citations": 89,
                "doi": "10.2196/12345",
                "keywords": ["federated learning", "privacy", "medical research", "collaboration"]
            },
            {
                "title": "Explainable AI for Clinical Decision Support Systems",
                "authors": ["Dr. John Smith", "Dr. Emily Chen"],
                "year": 2021,
                "venue": "Artificial Intelligence in Medicine",
                "abstract": "This work addresses the critical need for interpretable AI systems in clinical settings through novel explainability techniques.",
                "citations": 203,
                "doi": "10.1016/j.artmed.2021.102339",
                "keywords": ["explainable AI", "clinical decision support", "interpretability"]
            }
        ]
    
    def generate_mock_response(self, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mock API response based on database configuration"""
        
        # Start with the basic structure
        mock_response = {}
        
        # Navigate to where the data should be placed
        data_path = db_config.get('data_path', [])
        result_mapping = db_config.get('result_mapping', {})
        
        # Generate mock papers in the expected format
        mock_papers_formatted = []
        
        for paper in self.mock_papers:
            formatted_paper = {}
            
            # Map each field to the expected JSON structure
            for our_field, their_field in result_mapping.items():
                if our_field in paper:
                    self._set_nested_field(formatted_paper, their_field, paper[our_field])
            
            # Add some extra realistic fields
            formatted_paper.update({
                'id': f"paper_{len(mock_papers_formatted) + 1}",
                'updated': datetime.now().isoformat(),
                'type': 'journal-article'
            })
            
            mock_papers_formatted.append(formatted_paper)
        
        # Place the papers in the correct location according to data_path
        current_level = mock_response
        for i, path_part in enumerate(data_path):
            if i == len(data_path) - 1:  # Last part - put the data here
                current_level[path_part] = mock_papers_formatted
            else:
                current_level[path_part] = {}
                current_level = current_level[path_part]
        
        # If no data_path specified, put results at root
        if not data_path:
            mock_response = mock_papers_formatted
        
        # Add some metadata
        if isinstance(mock_response, dict):
            mock_response.update({
                'total': len(mock_papers_formatted),
                'generated_at': datetime.now().isoformat(),
                'status': 'success'
            })
        
        return mock_response
    
    def _set_nested_field(self, obj: Dict, field_path: str, value: Any):
        """Set a nested field in a dictionary using dot notation"""
        parts = field_path.split('.')
        current = obj
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def test_api_call(self, db_config: Dict[str, Any], sample_query: Dict[str, Any] = None) -> bool:
        """Test if we can actually call the API (optional)"""
        if sample_query is None:
            sample_query = {'author': 'John Smith'}
        
        try:
            base_url = db_config['base_url']
            param_mapping = db_config.get('param_mapping', {})
            
            # Map parameters
            api_params = {}
            for our_param, their_param in param_mapping.items():
                if our_param in sample_query:
                    api_params[their_param] = sample_query[our_param]
            
            # Add default params
            api_params.update(db_config.get('default_params', {}))
            
            # Make the request with a short timeout
            response = requests.get(base_url, params=api_params, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ Successfully called {db_config['name']} API")
                return True
            else:
                print(f"⚠️  API call returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Could not call {db_config['name']} API: {e}")
            return False
    
    def generate_all_mock_data(self, config_file: str = "config/easy_database_config.yaml"):
        """Generate mock data for all databases in config"""
        
        config_path = Path(config_file)
        if not config_path.exists():
            print(f"Config file not found: {config_file}")
            return
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        databases = config.get('databases', [])
        mock_data_dir = Path('tests/mock_data')
        mock_data_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Generating mock data for {len(databases)} databases...")
        
        for db_config in databases:
            db_name = db_config['name'].lower().replace(' ', '_')
            
            # Test the API first (optional)
            print(f"\n🔍 Testing {db_config['name']}...")
            api_works = self.test_api_call(db_config)
            
            # Generate mock data
            mock_response = self.generate_mock_response(db_config)
            
            # Save to file  
            mock_file = mock_data_dir / f"{db_name}_api_response.json"
            with open(mock_file, 'w') as f:
                json.dump(mock_response, f, indent=2)
            
            print(f"📁 Generated mock data: {mock_file}")
            
            # Generate a simple test template
            self._generate_test_template(db_config, mock_file)
    
    def _generate_test_template(self, db_config: Dict[str, Any], mock_file: Path):
        """Generate a basic test template for the database"""
        
        db_name = db_config['name'].lower().replace(' ', '_')
        test_file = Path(f'tests/test_{db_name}_plugin.py')
        
        test_template = f'''import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path

from src.tools.database_plugins import GenericAPIPlugin

class Test{db_config['name'].replace(' ', '')}Plugin:
    
    @pytest.fixture
    def mock_response_data(self):
        """Load mock response data"""
        mock_file = Path(__file__).parent / "mock_data" / "{mock_file.name}"
        with open(mock_file, 'r') as f:
            return json.load(f)
    
    @pytest.fixture
    def plugin(self):
        """Create plugin instance"""
        config = {db_config}
        return GenericAPIPlugin(config)
    
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
'''
        
        with open(test_file, 'w') as f:
            f.write(test_template)
        
        print(f"📝 Generated test template: {test_file}")

def main():
    """Main function"""
    print("🚀 Mock Data Generator for Academic Databases")
    print("=" * 50)
    
    generator = MockDataGenerator()
    generator.generate_all_mock_data()
    
    print("\n✅ Mock data generation complete!")
    print("\nTo add a new database:")
    print("1. Add its configuration to config/easy_database_config.yaml")
    print("2. Run this script: python src/tools/mock_data_generator.py")
    print("3. The mock data and test template will be auto-generated!")

if __name__ == "__main__":
    main()