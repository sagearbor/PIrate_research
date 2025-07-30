import requests
from typing import List, Dict, Optional, Any, Union
import json
import yaml
from pathlib import Path
import logging
from dataclasses import dataclass, field
from datetime import datetime
import urllib.parse
import time

logger = logging.getLogger(__name__)

@dataclass
class SearchParameters:
    """Parameters for searching academic databases"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    institution: Optional[str] = None
    email: Optional[str] = None
    orcid_id: Optional[str] = None
    google_scholar_id: Optional[str] = None
    researcher_id: Optional[str] = None
    scopus_id: Optional[str] = None
    department: Optional[str] = None
    research_keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, list) and len(value) > 0:
                    result[key] = value
                elif not isinstance(value, list):
                    result[key] = value
        return result

@dataclass
class DatabaseConfig:
    """Configuration for a specific academic database"""
    name: str
    base_url: str
    api_key_required: bool = False
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    search_params_mapping: Dict[str, str] = field(default_factory=dict)
    result_parsers: Dict[str, str] = field(default_factory=dict)
    headers: Optional[Dict[str, str]] = None

@dataclass
class Publication:
    """Represents a single publication"""
    title: str
    authors: List[str]
    year: Optional[int] = None
    journal: Optional[str] = None
    citations: Optional[int] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    source_db: Optional[str] = None

@dataclass
class FacultyProfile:
    """Comprehensive faculty profile aggregated from multiple sources"""
    name: str
    institution: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    orcid_id: Optional[str] = None
    google_scholar_id: Optional[str] = None
    h_index: Optional[int] = None
    total_citations: Optional[int] = None
    publications: List[Publication] = field(default_factory=list)
    research_interests: List[str] = field(default_factory=list)
    coauthors: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    source_databases: List[str] = field(default_factory=list)

class GenericFacultyFinder:
    """Generic academic database searcher that aggregates faculty information from multiple sources"""
    
    def __init__(self, config_file: str = "config/faculty_search_sources.yaml"):
        self.config_file = Path(config_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Academic Research Tool/1.0 (Contact: research@university.edu)'
        })
        
    def load_config(self) -> List[DatabaseConfig]:
        """Load database configurations from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            configs = []
            for item in config_data.get('databases', []):
                configs.append(DatabaseConfig(**item))
            
            return configs
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_file}")
            return []
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return []
    
    def search_google_scholar(self, params: SearchParameters, config: DatabaseConfig) -> Dict[str, Any]:
        """Search Google Scholar for faculty publications"""
        results = {
            'source': 'Google Scholar',
            'success': False,
            'publications': [],
            'profile_data': {},
            'error': None
        }
        
        try:
            # Build search query
            query_parts = []
            if params.full_name:
                query_parts.append(f'author:"{params.full_name}"')
            elif params.first_name and params.last_name:
                query_parts.append(f'author:"{params.first_name} {params.last_name}"')
            
            if params.institution:
                query_parts.append(f'"{params.institution}"')
            
            query = " ".join(query_parts)
            
            # Note: This is a simplified example. In practice, you'd use scholarly library or similar
            # For now, we'll create mock data structure
            results['profile_data'] = {
                'h_index': None,
                'total_citations': None,
                'verified_email': params.email
            }
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Error searching Google Scholar: {e}")
            results['error'] = str(e)
            
        return results
    
    def search_arxiv(self, params: SearchParameters, config: DatabaseConfig) -> Dict[str, Any]:
        """Search arXiv for faculty publications"""
        results = {
            'source': 'arXiv',
            'success': False,
            'publications': [],
            'profile_data': {},
            'error': None
        }
        
        try:
            base_url = "http://export.arxiv.org/api/query"
            
            # Build search query
            search_terms = []
            if params.full_name:
                search_terms.append(f'au:"{params.full_name}"')
            elif params.first_name and params.last_name:
                search_terms.append(f'au:"{params.first_name} {params.last_name}"')
            
            if params.research_keywords:
                for keyword in params.research_keywords[:3]:  # Limit to avoid too complex queries
                    search_terms.append(f'all:{keyword}')
            
            if not search_terms:
                results['error'] = "No search terms provided"
                return results
            
            query = " AND ".join(search_terms)
            params_dict = {
                'search_query': query,
                'start': 0,
                'max_results': 20,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            response = self.session.get(base_url, params=params_dict, timeout=30)
            response.raise_for_status()
            
            # Parse XML response (simplified - in practice use xml.etree.ElementTree)
            results['success'] = True
            results['raw_response'] = response.text[:1000]  # Store sample for debugging
            
        except Exception as e:
            logger.error(f"Error searching arXiv: {e}")
            results['error'] = str(e)
            
        return results
    
    def search_pubmed(self, params: SearchParameters, config: DatabaseConfig) -> Dict[str, Any]:
        """Search PubMed for faculty publications"""
        results = {
            'source': 'PubMed',
            'success': False,
            'publications': [],
            'profile_data': {},
            'error': None
        }
        
        try:
            base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            
            # Build search query
            search_terms = []
            if params.full_name:
                search_terms.append(f'"{params.full_name}"[Author]')
            elif params.first_name and params.last_name:
                search_terms.append(f'"{params.last_name} {params.first_name}"[Author]')
            
            if params.institution:
                search_terms.append(f'"{params.institution}"[Affiliation]')
            
            if not search_terms:
                results['error'] = "No search terms provided"
                return results
            
            query = " AND ".join(search_terms)
            params_dict = {
                'db': 'pubmed',
                'term': query,
                'retmax': 20,
                'retmode': 'json',
                'sort': 'pub_date'
            }
            
            response = self.session.get(base_url, params=params_dict, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results['success'] = True
            results['id_list'] = data.get('esearchresult', {}).get('idlist', [])
            
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            results['error'] = str(e)
            
        return results
    
    def search_orcid(self, params: SearchParameters, config: DatabaseConfig) -> Dict[str, Any]:
        """Search ORCID for faculty profile"""
        results = {
            'source': 'ORCID',
            'success': False,
            'publications': [],
            'profile_data': {},
            'error': None
        }
        
        try:
            if params.orcid_id:
                # Direct ORCID lookup
                url = f"https://pub.orcid.org/v3.0/{params.orcid_id}/record"
                headers = {'Accept': 'application/json'}
                response = self.session.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                results['profile_data'] = {
                    'orcid_id': params.orcid_id,
                    'verified': True
                }
                results['success'] = True
            else:
                # Search ORCID by name
                base_url = "https://pub.orcid.org/v3.0/search"
                query_parts = []
                
                if params.full_name:
                    query_parts.append(f'family-name:"{params.full_name.split()[-1]}"')
                    if len(params.full_name.split()) > 1:
                        query_parts.append(f'given-names:"{params.full_name.split()[0]}"')
                elif params.first_name and params.last_name:
                    query_parts.append(f'family-name:"{params.last_name}"')
                    query_parts.append(f'given-names:"{params.first_name}"')
                
                if params.institution:
                    query_parts.append(f'affiliation-org-name:"{params.institution}"')
                
                query = " AND ".join(query_parts)
                params_dict = {'q': query}
                headers = {'Accept': 'application/json'}
                
                response = self.session.get(base_url, params=params_dict, headers=headers, timeout=30)
                response.raise_for_status()
                
                results['success'] = True
                results['search_results'] = response.json()
                
        except Exception as e:
            logger.error(f"Error searching ORCID: {e}")
            results['error'] = str(e)
            
        return results
    
    def search_database(self, db_config: DatabaseConfig, params: SearchParameters) -> Dict[str, Any]:
        """Search a specific database based on its configuration"""
        logger.info(f"Searching {db_config.name}...")
        
        if db_config.name.lower() == 'google scholar':
            return self.search_google_scholar(params, db_config)
        elif db_config.name.lower() == 'arxiv':
            return self.search_arxiv(params, db_config)
        elif db_config.name.lower() == 'pubmed':
            return self.search_pubmed(params, db_config)
        elif db_config.name.lower() == 'orcid':
            return self.search_orcid(params, db_config)
        else:
            return {
                'source': db_config.name,
                'success': False,
                'error': f"Database {db_config.name} not implemented yet"
            }
    
    def search_all_databases(self, params: SearchParameters) -> List[Dict[str, Any]]:
        """Search all configured databases"""
        db_configs = self.load_config()
        results = []
        
        for db_config in db_configs:
            try:
                result = self.search_database(db_config, params)
                results.append(result)
                
                # Respect rate limits
                if db_config.rate_limit_delay > 0:
                    time.sleep(db_config.rate_limit_delay)
                    
            except Exception as e:
                logger.error(f"Error searching {db_config.name}: {e}")
                results.append({
                    'source': db_config.name,
                    'success': False,
                    'error': str(e)
                })
                
        return results
    
    def aggregate_faculty_profile(self, search_results: List[Dict[str, Any]], params: SearchParameters) -> FacultyProfile:
        """Aggregate results from multiple databases into a single faculty profile"""
        profile = FacultyProfile(
            name=params.full_name or f"{params.first_name} {params.last_name}",
            institution=params.institution,
            email=params.email,
            department=params.department,
            orcid_id=params.orcid_id,
            google_scholar_id=params.google_scholar_id,
            last_updated=datetime.now().isoformat()
        )
        
        publications = []
        research_interests = set(params.research_keywords if params.research_keywords else [])
        coauthors = set()
        successful_sources = []
        
        for result in search_results:
            if result['success']:
                successful_sources.append(result['source'])
                
                # Aggregate profile data
                profile_data = result.get('profile_data', {})
                if 'h_index' in profile_data and profile_data['h_index']:
                    profile.h_index = profile_data['h_index']
                if 'total_citations' in profile_data and profile_data['total_citations']:
                    profile.total_citations = profile_data['total_citations']
                
                # Add publications
                for pub_data in result.get('publications', []):
                    pub = Publication(
                        title=pub_data.get('title', ''),
                        authors=pub_data.get('authors', []),
                        year=pub_data.get('year'),
                        journal=pub_data.get('journal'),
                        citations=pub_data.get('citations'),
                        doi=pub_data.get('doi'),
                        url=pub_data.get('url'),
                        abstract=pub_data.get('abstract'),
                        keywords=pub_data.get('keywords', []),
                        source_db=result['source']
                    )
                    publications.append(pub)
                    
                    # Aggregate coauthors and research interests
                    coauthors.update(pub.authors)
                    research_interests.update(pub.keywords)
        
        profile.publications = publications
        profile.research_interests = list(research_interests)
        profile.coauthors = list(coauthors)
        profile.source_databases = successful_sources
        
        return profile
    
    def find_faculty(self, search_params: SearchParameters) -> FacultyProfile:
        """Main method to find and aggregate faculty information"""
        logger.info(f"Searching for faculty: {search_params.full_name or f'{search_params.first_name} {search_params.last_name}'}")
        
        results = self.search_all_databases(search_params)
        profile = self.aggregate_faculty_profile(results, search_params)
        
        logger.info(f"Found {len(profile.publications)} publications from {len(profile.source_databases)} sources")
        
        return profile
    
    def save_profile(self, profile: FacultyProfile, output_file: str = None) -> Path:
        """Save faculty profile to JSON file"""
        if output_file is None:
            safe_name = profile.name.replace(" ", "_").replace(".", "")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/faculty_profile_{safe_name}_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclass to dict for JSON serialization
        profile_dict = {
            'name': profile.name,
            'institution': profile.institution,
            'email': profile.email,
            'department': profile.department,
            'orcid_id': profile.orcid_id,
            'google_scholar_id': profile.google_scholar_id,
            'h_index': profile.h_index,
            'total_citations': profile.total_citations,
            'publications': [pub.__dict__ for pub in profile.publications],
            'research_interests': profile.research_interests,
            'coauthors': profile.coauthors,
            'last_updated': profile.last_updated,
            'source_databases': profile.source_databases
        }
        
        with open(output_path, 'w') as f:
            json.dump(profile_dict, f, indent=2)
        
        logger.info(f"Faculty profile saved to {output_path}")
        return output_path

def main():
    """Main function for testing the faculty finder"""
    finder = GenericFacultyFinder()
    
    # Example search
    params = SearchParameters(
        full_name="John Smith",
        institution="Stanford University",
        research_keywords=["machine learning", "artificial intelligence"]
    )
    
    profile = finder.find_faculty(params)
    finder.save_profile(profile)
    
    print(f"Faculty profile created for {profile.name}")
    print(f"Found {len(profile.publications)} publications")
    print(f"Sources: {', '.join(profile.source_databases)}")

if __name__ == "__main__":
    main()