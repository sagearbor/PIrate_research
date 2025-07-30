from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import requests
import json
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Standardized search result from any database"""
    title: str
    authors: List[str]
    year: Optional[int] = None
    venue: Optional[str] = None  # journal/conference
    url: Optional[str] = None
    abstract: Optional[str] = None
    citations: Optional[int] = None
    doi: Optional[str] = None
    keywords: List[str] = None
    raw_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.raw_data is None:
            self.raw_data = {}

class DatabasePlugin(ABC):
    """Abstract base class for database plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Database name"""
        pass
    
    @property
    @abstractmethod  
    def base_url(self) -> str:
        """Base URL for the database API"""
        pass
    
    @property
    def rate_limit_delay(self) -> float:
        """Seconds to wait between requests"""
        return 1.0
    
    @property
    def requires_api_key(self) -> bool:
        """Whether this database requires an API key"""
        return False
    
    @abstractmethod
    def search(self, query_params: Dict[str, Any]) -> List[SearchResult]:
        """Search the database and return standardized results"""
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for HTTP requests"""
        return {
            'User-Agent': 'Academic Research Tool/1.0',
            'Accept': 'application/json'
        }

class ArxivPlugin(DatabasePlugin):
    """Plugin for arXiv preprint server"""
    
    @property
    def name(self) -> str:
        return "arXiv"
    
    @property
    def base_url(self) -> str:
        return "http://export.arxiv.org/api/query"
    
    @property
    def rate_limit_delay(self) -> float:
        return 3.0  # arXiv has strict rate limits
    
    def search(self, query_params: Dict[str, Any]) -> List[SearchResult]:
        """Search arXiv using their API"""
        results = []
        
        try:
            # Build search query
            search_terms = []
            
            if 'author' in query_params:
                search_terms.append(f'au:"{query_params["author"]}"')
            
            if 'keywords' in query_params:
                for keyword in query_params['keywords'][:3]:  # Limit keywords
                    search_terms.append(f'all:{keyword}')
            
            if not search_terms:
                return results
            
            query = " AND ".join(search_terms)
            params = {
                'search_query': query,
                'start': 0,
                'max_results': 20,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response (simplified)
            # In a real implementation, you'd use xml.etree.ElementTree
            # For now, we'll return mock data to demonstrate the concept
            results = [
                SearchResult(
                    title="Example arXiv Paper",
                    authors=["Author 1", "Author 2"],
                    year=2023,
                    venue="arXiv preprint",
                    url="https://arxiv.org/abs/2301.12345",
                    abstract="This is an example abstract from arXiv.",
                    raw_data={'source': 'arxiv', 'query': query}
                )
            ]
            
        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            
        return results

class PubMedPlugin(DatabasePlugin):
    """Plugin for PubMed medical literature database"""
    
    @property
    def name(self) -> str:
        return "PubMed"
    
    @property
    def base_url(self) -> str:
        return "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    
    def search(self, query_params: Dict[str, Any]) -> List[SearchResult]:
        """Search PubMed using NCBI E-utilities"""
        results = []
        
        try:
            # Build search query
            search_terms = []
            
            if 'author' in query_params:
                search_terms.append(f'"{query_params["author"]}"[Author]')
            
            if 'institution' in query_params:
                search_terms.append(f'"{query_params["institution"]}"[Affiliation]')
            
            if not search_terms:
                return results
            
            query = " AND ".join(search_terms)
            params = {
                'db': 'pubmed',
                'term': query,
                'retmax': 20,
                'retmode': 'json',
                'sort': 'pub_date'
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            id_list = data.get('esearchresult', {}).get('idlist', [])
            
            # For each ID, we would normally fetch detailed info
            # For now, return mock data
            for pmid in id_list[:5]:  # Limit to first 5
                results.append(SearchResult(
                    title=f"PubMed Paper {pmid}",
                    authors=["Medical Author"],
                    year=2023,
                    venue="Medical Journal",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    raw_data={'pmid': pmid, 'source': 'pubmed'}
                ))
                
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            
        return results

class GenericAPIPlugin(DatabasePlugin):
    """Generic plugin that can be configured for any REST API"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @property
    def name(self) -> str:
        return self.config.get('name', 'Generic API')
    
    @property
    def base_url(self) -> str:
        return self.config.get('base_url', '')
    
    @property
    def rate_limit_delay(self) -> float:
        return self.config.get('rate_limit_delay', 1.0)
    
    @property
    def requires_api_key(self) -> bool:
        return self.config.get('requires_api_key', False)
    
    def search(self, query_params: Dict[str, Any]) -> List[SearchResult]:
        """Generic search using configuration mapping"""
        results = []
        
        try:
            # Map our standard params to API-specific params
            api_params = {}
            param_mapping = self.config.get('param_mapping', {})
            
            for our_param, their_param in param_mapping.items():
                if our_param in query_params:
                    api_params[their_param] = query_params[our_param]
            
            # Add any default parameters
            api_params.update(self.config.get('default_params', {}))
            
            # Make the request
            headers = self.get_headers()
            if self.requires_api_key and 'api_key' in self.config:
                headers['Authorization'] = f"Bearer {self.config['api_key']}"
            
            response = requests.get(self.base_url, params=api_params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response using configuration
            result_mapping = self.config.get('result_mapping', {})
            data_path = self.config.get('data_path', [])
            
            # Navigate to the data array
            items = data
            for path_part in data_path:
                items = items.get(path_part, [])
            
            if not isinstance(items, list):
                items = [items]
            
            for item in items[:20]:  # Limit results
                result = SearchResult(
                    title=self._extract_field(item, result_mapping.get('title', 'title')),
                    authors=self._extract_authors(item, result_mapping.get('authors', 'authors')),
                    year=self._extract_year(item, result_mapping.get('year', 'year')),
                    venue=self._extract_field(item, result_mapping.get('venue', 'venue')),
                    url=self._extract_field(item, result_mapping.get('url', 'url')),
                    abstract=self._extract_field(item, result_mapping.get('abstract', 'abstract')),
                    citations=self._extract_int(item, result_mapping.get('citations', 'citations')),
                    doi=self._extract_field(item, result_mapping.get('doi', 'doi')),
                    raw_data=item
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error searching {self.name}: {e}")
            
        return results
    
    def _extract_field(self, item: Dict, field_path: str) -> Optional[str]:
        """Extract a string field from nested dict"""
        try:
            parts = field_path.split('.')
            value = item
            for part in parts:
                value = value.get(part, '')
            return str(value) if value else None
        except:
            return None
    
    def _extract_authors(self, item: Dict, field_path: str) -> List[str]:
        """Extract authors list"""
        try:
            authors_data = self._extract_field(item, field_path)
            if isinstance(authors_data, list):
                return [str(author) for author in authors_data]
            elif isinstance(authors_data, str):
                return [authors_data]
            return []
        except:
            return []
    
    def _extract_year(self, item: Dict, field_path: str) -> Optional[int]:
        """Extract year as integer"""
        try:
            year_str = self._extract_field(item, field_path)
            if year_str:
                # Extract 4-digit year from string
                import re
                match = re.search(r'\b(19|20)\d{2}\b', str(year_str))
                if match:
                    return int(match.group())
            return None
        except:
            return None
    
    def _extract_int(self, item: Dict, field_path: str) -> Optional[int]:
        """Extract integer field"""
        try:
            value = self._extract_field(item, field_path)
            return int(value) if value and str(value).isdigit() else None
        except:
            return None

class PluginManager:
    """Manages all database plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, DatabasePlugin] = {}
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """Register built-in plugins"""
        self.register_plugin(ArxivPlugin())
        self.register_plugin(PubMedPlugin())
    
    def register_plugin(self, plugin: DatabasePlugin):
        """Register a new plugin"""
        self.plugins[plugin.name.lower()] = plugin
        logger.info(f"Registered plugin: {plugin.name}")
    
    def create_generic_plugin(self, config: Dict[str, Any]) -> DatabasePlugin:
        """Create a generic plugin from configuration"""
        plugin = GenericAPIPlugin(config)
        self.register_plugin(plugin)
        return plugin
    
    def get_plugin(self, name: str) -> Optional[DatabasePlugin]:
        """Get a plugin by name"""
        return self.plugins.get(name.lower())
    
    def list_plugins(self) -> List[str]:
        """List all registered plugins"""
        return list(self.plugins.keys())
    
    def search_all(self, query_params: Dict[str, Any]) -> Dict[str, List[SearchResult]]:
        """Search all plugins and return results"""
        all_results = {}
        
        for name, plugin in self.plugins.items():
            try:
                results = plugin.search(query_params)
                all_results[name] = results
                logger.info(f"Found {len(results)} results from {plugin.name}")
                
                # Respect rate limits
                import time
                time.sleep(plugin.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error searching {plugin.name}: {e}")
                all_results[name] = []
        
        return all_results

def main():
    """Example usage"""
    manager = PluginManager()
    
    # Example: Add a new database easily
    ieee_config = {
        'name': 'IEEE Xplore',
        'base_url': 'https://ieeexploreapi.ieee.org/api/v1/search/articles',
        'requires_api_key': True,
        'rate_limit_delay': 1.0,
        'param_mapping': {
            'author': 'author',
            'keywords': 'querytext'
        },
        'result_mapping': {
            'title': 'title',
            'authors': 'authors.authors.full_name',
            'year': 'publication_year',
            'venue': 'publication_title',
            'doi': 'doi'
        },
        'data_path': ['articles'],
        'default_params': {
            'format': 'json',
            'max_records': 20
        }
    }
    
    # Add the new plugin
    ieee_plugin = manager.create_generic_plugin(ieee_config)
    
    # Search all databases
    query = {
        'author': 'John Smith',
        'keywords': ['machine learning', 'AI']
    }
    
    results = manager.search_all(query)
    
    for db_name, papers in results.items():
        print(f"{db_name}: {len(papers)} papers found")

if __name__ == "__main__":
    main()