import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import requests

from src.tools.generic_faculty_finder import (
    GenericFacultyFinder, 
    SearchParameters, 
    DatabaseConfig, 
    Publication, 
    FacultyProfile
)

class TestSearchParameters:
    
    def test_search_parameters_creation(self):
        params = SearchParameters(
            first_name="John",
            last_name="Smith",
            institution="Stanford University",
            orcid_id="0000-0000-0000-0000"
        )
        assert params.first_name == "John"
        assert params.last_name == "Smith"
        assert params.institution == "Stanford University"
        assert params.orcid_id == "0000-0000-0000-0000"
    
    def test_to_dict_excludes_none_values(self):
        params = SearchParameters(
            first_name="John",
            last_name="Smith",
            institution=None,
            research_keywords=["AI", "ML"]
        )
        result = params.to_dict()
        assert "first_name" in result
        assert "last_name" in result
        assert "institution" not in result
        assert "research_keywords" in result
        assert result["research_keywords"] == ["AI", "ML"]

class TestDatabaseConfig:
    
    def test_database_config_creation(self):
        config = DatabaseConfig(
            name="Test DB",
            base_url="https://example.com",
            api_key_required=True,
            rate_limit_delay=2.0
        )
        assert config.name == "Test DB"
        assert config.base_url == "https://example.com"
        assert config.api_key_required is True
        assert config.rate_limit_delay == 2.0

class TestPublication:
    
    def test_publication_creation(self):
        pub = Publication(
            title="Test Paper",
            authors=["John Smith", "Jane Doe"],
            year=2023,
            journal="Test Journal",
            citations=10
        )
        assert pub.title == "Test Paper"
        assert len(pub.authors) == 2
        assert pub.year == 2023
        assert pub.citations == 10

class TestFacultyProfile:
    
    def test_faculty_profile_creation(self):
        profile = FacultyProfile(
            name="John Smith",
            institution="Stanford University",
            h_index=25,
            total_citations=1500
        )
        assert profile.name == "John Smith"
        assert profile.institution == "Stanford University"
        assert profile.h_index == 25
        assert profile.total_citations == 1500
        assert len(profile.publications) == 0  # default empty list

class TestGenericFacultyFinder:
    
    @pytest.fixture
    def mock_config(self):
        return {
            'databases': [
                {
                    'name': 'Test Database',
                    'base_url': 'https://example.com',
                    'api_key_required': False,
                    'rate_limit_delay': 0.5,
                    'max_retries': 2,
                    'search_params_mapping': {
                        'author': 'au',
                        'keywords': 'q'
                    },
                    'result_parsers': {
                        'title': 'title',
                        'authors': 'authors'
                    }
                }
            ]
        }
    
    @pytest.fixture
    def finder(self, tmp_path):
        config_file = tmp_path / "test_config.yaml"
        return GenericFacultyFinder(str(config_file))
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_load_config(self, mock_yaml_load, mock_file, finder, mock_config):
        mock_yaml_load.return_value = mock_config
        
        configs = finder.load_config()
        
        assert len(configs) == 1
        assert configs[0].name == "Test Database"
        assert configs[0].base_url == "https://example.com"
        assert configs[0].rate_limit_delay == 0.5
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_file, finder):
        configs = finder.load_config()
        assert configs == []
    
    @patch('requests.Session.get')
    def test_search_arxiv_success(self, mock_get, finder):
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper on Machine Learning</title>
                <author><name>John Smith</name></author>
                <published>2023-01-01T00:00:00Z</published>
            </entry>
        </feed>"""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        config = DatabaseConfig(name="arXiv", base_url="http://export.arxiv.org")
        params = SearchParameters(full_name="John Smith")
        
        result = finder.search_arxiv(params, config)
        
        assert result['success'] is True
        assert result['source'] == 'arXiv'
        assert 'raw_response' in result
    
    @patch('requests.Session.get')
    def test_search_arxiv_failure(self, mock_get, finder):
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        config = DatabaseConfig(name="arXiv", base_url="http://export.arxiv.org")
        params = SearchParameters(full_name="John Smith")
        
        result = finder.search_arxiv(params, config)
        
        assert result['success'] is False
        assert "Connection failed" in result['error']
    
    @patch('requests.Session.get')
    def test_search_pubmed_success(self, mock_get, finder):
        mock_response = Mock()
        mock_response.json.return_value = {
            'esearchresult': {
                'idlist': ['12345', '67890'],
                'count': '2'
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        config = DatabaseConfig(name="PubMed", base_url="https://eutils.ncbi.nlm.nih.gov")
        params = SearchParameters(full_name="John Smith", institution="Harvard")
        
        result = finder.search_pubmed(params, config)
        
        assert result['success'] is True
        assert result['source'] == 'PubMed'
        assert len(result['id_list']) == 2
    
    @patch('requests.Session.get')
    def test_search_orcid_with_id(self, mock_get, finder):
        mock_response = Mock()
        mock_response.json.return_value = {
            'orcid-identifier': {
                'path': '0000-0000-0000-0000'
            },
            'person': {
                'name': {
                    'family-name': {'value': 'Smith'},
                    'given-names': {'value': 'John'}
                }
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        config = DatabaseConfig(name="ORCID", base_url="https://pub.orcid.org/v3.0")
        params = SearchParameters(orcid_id="0000-0000-0000-0000")
        
        result = finder.search_orcid(params, config)
        
        assert result['success'] is True
        assert result['source'] == 'ORCID'
        assert result['profile_data']['orcid_id'] == "0000-0000-0000-0000"
    
    def test_search_database_unknown_database(self, finder):
        config = DatabaseConfig(name="Unknown DB", base_url="https://example.com")
        params = SearchParameters(full_name="John Smith")
        
        result = finder.search_database(config, params)
        
        assert result['success'] is False
        assert "not implemented yet" in result['error']
    
    @patch.object(GenericFacultyFinder, 'load_config')
    @patch.object(GenericFacultyFinder, 'search_database')
    def test_search_all_databases(self, mock_search_db, mock_load_config, finder):
        mock_config = DatabaseConfig(
            name="Test DB",
            base_url="https://example.com",
            rate_limit_delay=0  # No delay for testing
        )
        mock_load_config.return_value = [mock_config]
        
        mock_result = {
            'source': 'Test DB',
            'success': True,
            'publications': [],
            'profile_data': {}
        }
        mock_search_db.return_value = mock_result
        
        params = SearchParameters(full_name="John Smith")
        results = finder.search_all_databases(params)
        
        assert len(results) == 1
        assert results[0] == mock_result
        mock_search_db.assert_called_once_with(mock_config, params)
    
    def test_aggregate_faculty_profile(self, finder):
        search_results = [
            {
                'source': 'Google Scholar',
                'success': True,
                'publications': [
                    {
                        'title': 'Test Paper 1',
                        'authors': ['John Smith', 'Jane Doe'],
                        'year': 2023,
                        'citations': 10
                    }
                ],
                'profile_data': {
                    'h_index': 15,
                    'total_citations': 500
                }
            },
            {
                'source': 'arXiv',
                'success': True,
                'publications': [
                    {
                        'title': 'Test Paper 2',
                        'authors': ['John Smith', 'Bob Johnson'],
                        'year': 2022,
                        'keywords': ['machine learning', 'AI']
                    }
                ],
                'profile_data': {}
            },
            {
                'source': 'PubMed',
                'success': False,
                'error': 'Connection failed'
            }
        ]
        
        params = SearchParameters(
            full_name="John Smith",
            institution="Stanford University",
            research_keywords=["AI"]
        )
        
        profile = finder.aggregate_faculty_profile(search_results, params)
        
        assert profile.name == "John Smith"
        assert profile.institution == "Stanford University"
        assert profile.h_index == 15
        assert profile.total_citations == 500
        assert len(profile.publications) == 2
        assert len(profile.source_databases) == 2
        assert 'Google Scholar' in profile.source_databases
        assert 'arXiv' in profile.source_databases
        assert 'PubMed' not in profile.source_databases
        
        # Check if research interests were aggregated
        assert 'machine learning' in profile.research_interests
        assert 'AI' in profile.research_interests
        
        # Check if coauthors were aggregated
        assert 'Jane Doe' in profile.coauthors
        assert 'Bob Johnson' in profile.coauthors
        assert 'John Smith' in profile.coauthors
    
    @patch.object(GenericFacultyFinder, 'search_all_databases')
    @patch.object(GenericFacultyFinder, 'aggregate_faculty_profile')
    def test_find_faculty(self, mock_aggregate, mock_search_all, finder):
        mock_search_results = [{'source': 'Test', 'success': True}]
        mock_search_all.return_value = mock_search_results
        
        mock_profile = FacultyProfile(name="John Smith")
        mock_aggregate.return_value = mock_profile
        
        params = SearchParameters(full_name="John Smith")
        result = finder.find_faculty(params)
        
        assert result == mock_profile
        mock_search_all.assert_called_once_with(params)
        mock_aggregate.assert_called_once_with(mock_search_results, params)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_profile(self, mock_json_dump, mock_file, finder, tmp_path):
        profile = FacultyProfile(
            name="John Smith",
            institution="Stanford",
            publications=[
                Publication(title="Test Paper", authors=["John Smith"], year=2023)
            ]
        )
        
        with patch('pathlib.Path.mkdir'):
            output_path = finder.save_profile(profile, str(tmp_path / "test.json"))
        
        # Verify JSON dump was called
        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        profile_dict = args[0]
        
        assert profile_dict['name'] == "John Smith"
        assert profile_dict['institution'] == "Stanford"
        assert len(profile_dict['publications']) == 1
        assert profile_dict['publications'][0]['title'] == "Test Paper"
    
    def test_main_function_runs(self):
        with patch.object(GenericFacultyFinder, 'find_faculty') as mock_find_faculty, \
             patch.object(GenericFacultyFinder, 'save_profile') as mock_save_profile:
            
            mock_profile = FacultyProfile(name="John Smith", publications=[])
            mock_find_faculty.return_value = mock_profile
            mock_save_profile.return_value = Path("test.json")
            
            from src.tools.generic_faculty_finder import main
            
            # Should run without error
            with patch('builtins.print'):  # Suppress print output
                main()
                
            mock_find_faculty.assert_called_once()
            mock_save_profile.assert_called_once_with(mock_profile)