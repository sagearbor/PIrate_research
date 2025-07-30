import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import requests

from src.tools.generic_scraper import GenericWebScraper, ScrapingConfig

class TestGenericWebScraper:
    
    @pytest.fixture
    def mock_config(self):
        return {
            'urls': [
                {
                    'name': 'Test Source',
                    'url': 'https://example.com/test',
                    'selectors': {
                        'container': '.grant-item',
                        'title': 'h3',
                        'description': '.desc'
                    },
                    'delay': 0.5,
                    'max_retries': 2
                }
            ]
        }
    
    @pytest.fixture
    def mock_html_response(self):
        return """
        <html>
            <body>
                <div class="grant-item">
                    <h3>Test Grant 1</h3>
                    <div class="desc">This is a test grant description</div>
                </div>
                <div class="grant-item">
                    <h3>Test Grant 2</h3>
                    <div class="desc">Another test grant</div>
                </div>
            </body>
        </html>
        """
    
    @pytest.fixture
    def scraper(self, tmp_path):
        config_file = tmp_path / "test_config.yaml"
        return GenericWebScraper(str(config_file))
    
    def test_scraping_config_creation(self):
        config = ScrapingConfig(
            url="https://example.com",
            name="Test",
            selectors={"title": "h1"}
        )
        assert config.url == "https://example.com"
        assert config.name == "Test"
        assert config.delay == 1.0  # default value
        assert config.max_retries == 3  # default value
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_load_config(self, mock_yaml_load, mock_file, scraper, mock_config):
        mock_yaml_load.return_value = mock_config
        
        configs = scraper.load_config()
        
        assert len(configs) == 1
        assert configs[0].name == "Test Source"
        assert configs[0].url == "https://example.com/test"
        assert configs[0].delay == 0.5
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_config_file_not_found(self, mock_file, scraper):
        configs = scraper.load_config()
        assert configs == []
    
    @patch('requests.Session.get')
    def test_scrape_url_success(self, mock_get, scraper, mock_html_response):
        mock_response = Mock()
        mock_response.content = mock_html_response.encode()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        config = ScrapingConfig(
            url="https://example.com/test",
            name="Test Source",
            selectors={
                'container': '.grant-item',
                'title': 'h3',
                'description': '.desc'
            }
        )
        
        result = scraper.scrape_url(config)
        
        assert result['success'] is True
        assert result['source'] == "Test Source"
        assert len(result['data']) == 2
        assert result['data'][0]['title'] == "Test Grant 1"
        assert result['data'][0]['description'] == "This is a test grant description"
    
    @patch('requests.Session.get')
    def test_scrape_url_request_failure(self, mock_get, scraper):
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        config = ScrapingConfig(
            url="https://example.com/test",
            name="Test Source",
            selectors={'container': '.grant-item'},
            max_retries=1
        )
        
        result = scraper.scrape_url(config)
        
        assert result['success'] is False
        assert "Connection failed" in result['error']
    
    @patch('requests.Session.get')
    def test_scrape_url_with_links(self, mock_get, scraper):
        html_with_links = """
        <html>
            <body>
                <div class="grant-item">
                    <h3><a href="/grant1">Test Grant 1</a></h3>
                    <div class="desc">Description 1</div>
                </div>
            </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.content = html_with_links.encode()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        config = ScrapingConfig(
            url="https://example.com/test",
            name="Test Source",
            selectors={
                'container': '.grant-item',
                'title': 'h3 a',
                'title_link': 'h3 a',
                'description': '.desc'
            }
        )
        
        result = scraper.scrape_url(config)
        
        assert result['success'] is True
        assert result['data'][0]['title'] == "Test Grant 1"
        assert result['data'][0]['title_link'] == "/grant1"
    
    @patch.object(GenericWebScraper, 'load_config')
    @patch.object(GenericWebScraper, 'scrape_url')
    def test_scrape_all(self, mock_scrape_url, mock_load_config, scraper):
        mock_config = ScrapingConfig(
            url="https://example.com",
            name="Test",
            selectors={'container': '.item'}
        )
        mock_load_config.return_value = [mock_config]
        
        mock_result = {
            'success': True,
            'data': [{'title': 'Test'}],
            'source': 'Test'
        }
        mock_scrape_url.return_value = mock_result
        
        results = scraper.scrape_all()
        
        assert len(results) == 1
        assert results[0] == mock_result
        mock_scrape_url.assert_called_once_with(mock_config)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_results(self, mock_json_dump, mock_file, scraper, tmp_path):
        results = [{'test': 'data'}]
        
        with patch('pathlib.Path.mkdir'):
            output_path = scraper.save_results(results, str(tmp_path / "test.json"))
        
        mock_json_dump.assert_called_once_with(results, mock_file.return_value.__enter__.return_value, indent=2)
        assert str(tmp_path / "test.json") in str(output_path)
    
    def test_main_function_runs(self, scraper):
        with patch.object(GenericWebScraper, 'scrape_all') as mock_scrape_all, \
             patch.object(GenericWebScraper, 'save_results') as mock_save_results:
            
            mock_scrape_all.return_value = [
                {'success': True, 'data': [{'title': 'Test'}]},
                {'success': False, 'data': []}
            ]
            mock_save_results.return_value = Path("test.json")
            
            from src.tools.generic_scraper import main
            
            # Should run without error
            with patch('builtins.print'):  # Suppress print output
                main()