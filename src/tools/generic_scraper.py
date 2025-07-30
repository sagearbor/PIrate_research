import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
import json
import yaml
from pathlib import Path
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ScrapingConfig:
    """Configuration for a specific URL scraping"""
    url: str
    name: str
    selectors: Dict[str, str]  # CSS selectors for different data elements
    headers: Optional[Dict[str, str]] = None
    delay: float = 1.0
    max_retries: int = 3

class GenericWebScraper:
    """A flexible web scraper that can handle multiple URLs with different configurations"""
    
    def __init__(self, config_file: str = "config/scraping_urls.yaml"):
        self.config_file = Path(config_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def load_config(self) -> List[ScrapingConfig]:
        """Load scraping configurations from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            configs = []
            for item in config_data.get('urls', []):
                configs.append(ScrapingConfig(**item))
            
            return configs
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_file}")
            return []
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return []
    
    def scrape_url(self, config: ScrapingConfig) -> Dict[str, Any]:
        """Scrape a single URL using the provided configuration"""
        result = {
            'source': config.name,
            'url': config.url,
            'scraped_at': datetime.now().isoformat(),
            'data': [],
            'success': False,
            'error': None
        }
        
        headers = config.headers or {}
        
        for attempt in range(config.max_retries):
            try:
                response = self.session.get(config.url, headers=headers, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract data based on selectors
                scraped_items = []
                
                # Find all containers that match the main selector
                main_selector = config.selectors.get('container', 'div')
                containers = soup.select(main_selector)
                
                for container in containers:
                    item = {}
                    
                    # Extract each field based on its selector
                    for field, selector in config.selectors.items():
                        if field == 'container':
                            continue
                            
                        element = container.select_one(selector)
                        if element:
                            if field.endswith('_link'):
                                item[field] = element.get('href', '')
                            else:
                                item[field] = element.get_text(strip=True)
                        else:
                            item[field] = None
                    
                    if any(item.values()):  # Only add if we found some data
                        scraped_items.append(item)
                
                result['data'] = scraped_items
                result['success'] = True
                logger.info(f"Successfully scraped {len(scraped_items)} items from {config.name}")
                break
                
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {config.name}: {e}")
                if attempt == config.max_retries - 1:
                    result['error'] = str(e)
            except Exception as e:
                logger.error(f"Unexpected error scraping {config.name}: {e}")
                result['error'] = str(e)
                break
        
        return result
    
    def scrape_all(self) -> List[Dict[str, Any]]:
        """Scrape all URLs from the configuration file"""
        configs = self.load_config()
        results = []
        
        for config in configs:
            logger.info(f"Scraping {config.name}...")
            result = self.scrape_url(config)
            results.append(result)
            
            # Respect delay between requests
            if config.delay > 0:
                import time
                time.sleep(config.delay)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_file: str = None):
        """Save scraping results to JSON file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/raw/scraped_data_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
        return output_path

def main():
    """Main function for running the scraper"""
    scraper = GenericWebScraper()
    results = scraper.scrape_all()
    scraper.save_results(results)
    
    # Print summary
    total_items = sum(len(r['data']) for r in results if r['success'])
    successful_sources = sum(1 for r in results if r['success'])
    total_sources = len(results)
    
    print(f"Scraping complete: {total_items} items from {successful_sources}/{total_sources} sources")

if __name__ == "__main__":
    main()