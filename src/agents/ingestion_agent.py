from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
from datetime import datetime
import json

from ..tools.generic_scraper import GenericWebScraper
from ..tools.generic_faculty_finder import GenericFacultyFinder, SearchParameters
from ..core.a2a_protocols import (
    A2AMessage, MessageType, AgentType, 
    IngestionRequest, IngestionResponse,
    create_a2a_response, create_discovery_message,
    DiscoveryRequestType
)
from .database_discovery_agent import DatabaseDiscoveryAgent

logger = logging.getLogger(__name__)

class IngestionAgent:
    """
    Agent responsible for ingesting funding opportunities and faculty data from various sources.
    Supports A2A (Agent-to-Agent) communication protocol and can dynamically add new databases.
    """
    
    def __init__(self, 
                 funding_config_file: str = "config/scraping_urls.yaml",
                 faculty_config_file: str = "config/faculty_search_sources.yaml"):
        self.funding_scraper = GenericWebScraper(funding_config_file)
        self.faculty_finder = GenericFacultyFinder(faculty_config_file)
        self.discovery_agent = DatabaseDiscoveryAgent()
        self.last_run = None
        
        logger.info("Ingestion Agent initialized with A2A support")
        
    def collect_funding_opportunities(self) -> List[Dict[str, Any]]:
        """Collect funding opportunities from all configured sources"""
        logger.info("Starting funding opportunity collection...")
        
        results = self.funding_scraper.scrape_all()
        
        # Process and normalize the data
        opportunities = []
        for result in results:
            if result['success']:
                for item in result['data']:
                    opportunity = {
                        'source': result['source'],
                        'source_url': result['url'],
                        'scraped_at': result['scraped_at'],
                        'title': item.get('title', ''),
                        'description': item.get('description', ''),
                        'deadline': item.get('deadline', ''),
                        'url': item.get('title_link', ''),
                        'funding_amount': item.get('funding_amount', ''),
                        'funding_type': item.get('funding_type', ''),
                        'program': item.get('program', ''),
                        'office': item.get('office', ''),
                        'focus_area': item.get('focus_area', ''),
                        'raw_data': item
                    }
                    opportunities.append(opportunity)
            else:
                logger.warning(f"Failed to scrape {result['source']}: {result.get('error', 'Unknown error')}")
        
        self.last_run = datetime.now()
        logger.info(f"Collected {len(opportunities)} funding opportunities")
        
        return opportunities
    
    def collect_faculty_data(self, faculty_list: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Collect faculty data from academic databases"""
        logger.info("Starting faculty data collection...")
        
        if faculty_list is None:
            # Default faculty list for testing
            faculty_list = [
                {"name": "John Smith", "institution": "Stanford University"},
                {"name": "Jane Doe", "institution": "MIT"},
                {"name": "Robert Johnson", "institution": "Harvard University"}
            ]
        
        faculty_profiles = []
        for faculty_info in faculty_list:
            try:
                params = SearchParameters(
                    full_name=faculty_info.get("name"),
                    institution=faculty_info.get("institution"),
                    email=faculty_info.get("email"),
                    orcid_id=faculty_info.get("orcid_id"),
                    research_keywords=faculty_info.get("keywords", [])
                )
                
                profile = self.faculty_finder.find_faculty(params)
                
                # Convert to dictionary for storage
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
                
                faculty_profiles.append(profile_dict)
                
            except Exception as e:
                logger.error(f"Error collecting data for {faculty_info.get('name', 'Unknown')}: {e}")
        
        logger.info(f"Collected data for {len(faculty_profiles)} faculty members")
        return faculty_profiles
    
    def add_new_database(self, database_url: str, database_name: str = None, database_type: str = "funding") -> Dict[str, Any]:
        """Add a new database by discovering its structure via Database Discovery Agent"""
        logger.info(f"Adding new {database_type} database: {database_url}")
        
        try:
            # Create discovery request
            from .database_discovery_agent import DiscoveryRequest, RequestType
            
            request = DiscoveryRequest(
                request_type=RequestType.GENERATE_BOTH,
                database_url=database_url,
                database_name=database_name
            )
            
            # Process request
            response = self.discovery_agent.process_request(request)
            
            if response.success:
                logger.info(f"Successfully added {database_name}: {response.generated_files}")
                
                # Reload configurations to include new database
                if database_type == "funding":
                    self.funding_scraper = GenericWebScraper(self.funding_scraper.config_file)
                elif database_type == "faculty":
                    self.faculty_finder = GenericFacultyFinder(self.faculty_finder.config_file)
                
                return {
                    'success': True,
                    'database_name': response.database_name,
                    'files_generated': response.generated_files,
                    'config_path': response.config_file_path,
                    'test_path': response.test_file_path
                }
            else:
                return {
                    'success': False,
                    'error': response.error_message
                }
                
        except Exception as e:
            logger.error(f"Failed to add database {database_url}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_opportunities(self, opportunities: List[Dict[str, Any]], output_file: str = None):
        """Save processed opportunities to file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/funding_opportunities_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(opportunities, f, indent=2)
        
        logger.info(f"Saved {len(opportunities)} opportunities to {output_path}")
        return output_path
    
    def save_faculty_data(self, faculty_data: List[Dict[str, Any]], output_file: str = None) -> Path:
        """Save faculty data to file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/faculty_profiles_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(faculty_data, f, indent=2)
        
        logger.info(f"Saved {len(faculty_data)} faculty profiles to {output_path}")
        return output_path
    
    def process_a2a_message(self, message: A2AMessage) -> A2AMessage:
        """Process A2A messages from other agents"""
        logger.info(f"Processing A2A message from {message.source_agent}")
        
        try:
            # Parse request payload
            request_data = message.payload
            request = IngestionRequest(**request_data)
            
            # Process the ingestion request
            result = self.run_ingestion_a2a(request)
            
            # Create response
            response = create_a2a_response(
                message,
                result.__dict__,
                success=result.success
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing A2A message: {e}")
            error_response = create_a2a_response(
                message,
                {"error": str(e)},
                success=False
            )
            return error_response
    
    def run_ingestion_a2a(self, request: IngestionRequest) -> IngestionResponse:
        """Run ingestion based on A2A request"""
        start_time = datetime.now()
        errors = []
        data_files = []
        
        try:
            funding_count = 0
            faculty_count = 0
            
            # Collect funding data if requested
            if request.include_funding_data:
                try:
                    funding_opportunities = self.collect_funding_opportunities()
                    funding_file = self.save_opportunities(funding_opportunities)
                    funding_count = len(funding_opportunities)
                    data_files.append(str(funding_file))
                except Exception as e:
                    errors.append(f"Funding data collection failed: {e}")
            
            # Collect faculty data if requested
            if request.include_faculty_data:
                try:
                    faculty_data = self.collect_faculty_data()
                    faculty_file = self.save_faculty_data(faculty_data)
                    faculty_count = len(faculty_data)
                    data_files.append(str(faculty_file))
                except Exception as e:
                    errors.append(f"Faculty data collection failed: {e}")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return IngestionResponse(
                success=len(errors) == 0,
                funding_opportunities_count=funding_count,
                faculty_profiles_count=faculty_count,
                data_files=data_files,
                errors=errors,
                processing_time_seconds=processing_time
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            return IngestionResponse(
                success=False,
                errors=[str(e)],
                processing_time_seconds=processing_time
            )
    
    def run_ingestion(self) -> Dict[str, Any]:
        """Run the complete ingestion process"""
        try:
            opportunities = self.collect_funding_opportunities()
            output_file = self.save_opportunities(opportunities)
            
            return {
                'success': True,
                'opportunities_count': len(opportunities),
                'output_file': str(output_file),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

def main():
    """Main function for running the ingestion agent"""
    agent = IngestionAgent()
    result = agent.run_ingestion()
    
    if result['success']:
        print(f"Ingestion complete: {result['opportunities_count']} opportunities saved to {result['output_file']}")
    else:
        print(f"Ingestion failed: {result['error']}")

if __name__ == "__main__":
    main()