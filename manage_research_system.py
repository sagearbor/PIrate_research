#!/usr/bin/env python3
"""
Research System Manager - Interactive CLI for System Updates

This is the primary interface for developers to extend and manage 
the Faculty Research Opportunity Notifier system.

Usage: python manage_research_system.py
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional 
import json
import yaml
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.agents.database_discovery_agent import (
    DatabaseDiscoveryAgent, 
    DiscoveryRequest, 
    RequestType, 
    ArtifactType,
    DatabaseType
)
from src.agents.ingestion_agent import IngestionAgent
from src.core.a2a_protocols import create_artifact_generation_message, AgentType

class ResearchSystemManager:
    """Interactive CLI for managing the research system"""
    
    def __init__(self):
        self.discovery_agent = DatabaseDiscoveryAgent()
        self.ingestion_agent = IngestionAgent()
        
    def main_menu(self):
        """Display main menu and handle user selection"""
        while True:
            self.print_header()
            print("🔬 Research System Manager - What would you like to do?\n")
            
            options = [
                "Add new funding source",
                "Add new faculty/academic database", 
                "Generate documentation for existing database",
                "Run system health check",
                "View system status",
                "Test database connection",
                "Show configuration files",
                "Exit"
            ]
            
            for i, option in enumerate(options, 1):
                print(f"{i}. {option}")
            
            try:
                choice = input(f"\nChoose an option (1-{len(options)}): ").strip()
                choice_num = int(choice)
                
                if choice_num == 1:
                    self.add_funding_source()
                elif choice_num == 2:
                    self.add_faculty_database()
                elif choice_num == 3:
                    self.generate_documentation()
                elif choice_num == 4:
                    self.run_health_check()
                elif choice_num == 5:
                    self.show_system_status()
                elif choice_num == 6:
                    self.test_database_connection()
                elif choice_num == 7:
                    self.show_configuration_files()
                elif choice_num == 8:
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid option. Please try again.")
                    
            except (ValueError, KeyboardInterrupt):
                if input("\n🤔 Exit? (y/N): ").lower().startswith('y'):
                    print("👋 Goodbye!")
                    break
            
            input("\n📋 Press Enter to continue...")
    
    def add_funding_source(self):
        """Interactive funding source addition"""
        self.print_section("Adding New Funding Source")
        
        # Get basic info
        url = input("📡 Enter the database URL: ").strip()
        if not url:
            print("❌ URL is required")
            return
            
        name = input("🏷️  Enter the database name: ").strip()
        if not name:
            name = self.extract_name_from_url(url)
            print(f"🤖 Auto-detected name: {name}")
        
        # Determine if API or website
        print("\n🔍 Is this an API endpoint or a website to scrape?")
        source_type = self.get_choice(["API endpoint", "Website to scrape"], default=1)
        
        api_key = None
        if source_type == 1:  # API
            needs_key = self.get_yes_no("🔐 Does this API require an API key?", default=False)
            if needs_key:
                api_key = input("🔑 Enter API key (or leave blank to configure later): ").strip() or None
        
        # Choose artifacts to generate
        print(f"\n📦 What should be generated for {name}?")
        artifact_options = [
            "Basic integration (config + tests + mock data)",
            "Full integration (+ documentation + integration guide)", 
            "Documentation only",
            "Custom selection"
        ]
        
        artifact_choice = self.get_choice(artifact_options, default=2)
        
        if artifact_choice == 1:  # Basic
            artifacts = [ArtifactType.CONFIG_FILE, ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]
        elif artifact_choice == 2:  # Full
            artifacts = [
                ArtifactType.CONFIG_FILE,
                ArtifactType.TEST_FILE, 
                ArtifactType.MOCK_DATA,
                ArtifactType.DOCUMENTATION,
                ArtifactType.INTEGRATION_GUIDE
            ]
        elif artifact_choice == 3:  # Docs only
            artifacts = [ArtifactType.DOCUMENTATION, ArtifactType.INTEGRATION_GUIDE]
        else:  # Custom
            artifacts = self.select_custom_artifacts()
        
        # Execute the addition
        self.execute_database_addition(
            url=url,
            name=name,
            database_type=DatabaseType.FUNDING,
            api_key=api_key,
            artifacts=artifacts,
            is_api=(source_type == 1)
        )
    
    def add_faculty_database(self):
        """Interactive faculty database addition"""
        self.print_section("Adding New Faculty/Academic Database")
        
        # Get basic info
        url = input("📡 Enter the API URL: ").strip()
        if not url:
            print("❌ URL is required")
            return
            
        name = input("🏷️  Enter the database name: ").strip()
        if not name:
            name = self.extract_name_from_url(url)
            print(f"🤖 Auto-detected name: {name}")
        
        # API key check
        needs_key = self.get_yes_no("🔐 Does this API require an API key?", default=False)
        api_key = None
        if needs_key:
            api_key = input("🔑 Enter API key (or leave blank to configure later): ").strip() or None
        
        # Choose artifacts
        print(f"\n📦 What should be generated for {name}?")
        artifact_options = [
            "Standard integration (config + tests + mock data)",
            "Full integration (+ documentation + plugin template)",
            "Documentation only",
            "Custom selection"
        ]
        
        artifact_choice = self.get_choice(artifact_options, default=1)
        
        if artifact_choice == 1:  # Standard
            artifacts = [ArtifactType.CONFIG_FILE, ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]
        elif artifact_choice == 2:  # Full
            artifacts = [
                ArtifactType.CONFIG_FILE,
                ArtifactType.TEST_FILE,
                ArtifactType.MOCK_DATA,
                ArtifactType.DOCUMENTATION,
                ArtifactType.INTEGRATION_GUIDE,
                ArtifactType.PLUGIN_CODE
            ]
        elif artifact_choice == 3:  # Docs only
            artifacts = [ArtifactType.DOCUMENTATION, ArtifactType.INTEGRATION_GUIDE]
        else:  # Custom
            artifacts = self.select_custom_artifacts()
        
        # Execute the addition
        self.execute_database_addition(
            url=url,
            name=name,
            database_type=DatabaseType.FACULTY,
            api_key=api_key,
            artifacts=artifacts,
            is_api=True
        )
    
    def generate_documentation(self):
        """Generate documentation for existing database"""
        self.print_section("Generate Documentation")
        
        url = input("📡 Enter the database URL: ").strip()
        if not url:
            print("❌ URL is required")
            return
            
        name = input("🏷️  Enter the database name: ").strip()
        if not name:
            name = self.extract_name_from_url(url)
            print(f"🤖 Auto-detected name: {name}")
        
        print(f"\n📚 What documentation should be generated for {name}?")
        doc_options = [
            "API documentation only",
            "Integration guide only", 
            "Both documentation and integration guide",
            "Full package (docs + guide + plugin template)"
        ]
        
        doc_choice = self.get_choice(doc_options, default=3)
        
        if doc_choice == 1:
            artifacts = [ArtifactType.DOCUMENTATION]
        elif doc_choice == 2:
            artifacts = [ArtifactType.INTEGRATION_GUIDE]
        elif doc_choice == 3:
            artifacts = [ArtifactType.DOCUMENTATION, ArtifactType.INTEGRATION_GUIDE]
        else:
            artifacts = [
                ArtifactType.DOCUMENTATION, 
                ArtifactType.INTEGRATION_GUIDE,
                ArtifactType.PLUGIN_CODE
            ]
        
        # Determine database type
        db_type = DatabaseType.FACULTY
        if self.get_yes_no("🎯 Is this a funding source (vs faculty/academic database)?", default=False):
            db_type = DatabaseType.FUNDING
        
        self.execute_database_addition(
            url=url,
            name=name,
            database_type=db_type,
            artifacts=artifacts,
            is_api=True
        )
    
    def run_health_check(self):
        """Run system health diagnostics"""
        self.print_section("System Health Check")
        
        print("🔍 Running system diagnostics...\n")
        
        # Check if required directories exist
        dirs_to_check = [
            "src/agents", "src/tools", "src/core",
            "config", "tests", "tests/mock_data",
            "data/raw", "data/processed"
        ]
        
        print("📁 Checking directory structure:")
        for dir_path in dirs_to_check:
            path = Path(dir_path)
            status = "✅" if path.exists() else "❌"
            print(f"   {status} {dir_path}")
        
        # Check configuration files
        print("\n📄 Checking configuration files:")
        config_files = [
            "config/scraping_urls.yaml",
            "config/faculty_search_sources.yaml",
            "requirements.txt"
        ]
        
        for config_file in config_files:
            path = Path(config_file)
            if path.exists():
                try:
                    if config_file.endswith('.yaml'):
                        with open(path, 'r') as f:
                            yaml.safe_load(f)
                    print(f"   ✅ {config_file}")
                except Exception as e:
                    print(f"   ❌ {config_file} - Error: {e}")
            else:
                print(f"   ❌ {config_file} - Missing")
        
        # Check agents
        print("\n🤖 Checking agents:")
        try:
            discovery_agent = DatabaseDiscoveryAgent()
            print("   ✅ Database Discovery Agent")
        except Exception as e:
            print(f"   ❌ Database Discovery Agent - Error: {e}")
        
        try:
            ingestion_agent = IngestionAgent()
            print("   ✅ Ingestion Agent")
        except Exception as e:
            print(f"   ❌ Ingestion Agent - Error: {e}")
        
        print("\n🎉 Health check complete!")
    
    def show_system_status(self):
        """Show current system status and statistics"""
        self.print_section("System Status")
        
        # Count funding sources
        funding_config = Path("config/scraping_urls.yaml")
        funding_count = 0
        if funding_config.exists():
            try:
                with open(funding_config, 'r') as f:
                    data = yaml.safe_load(f)
                    funding_count = len(data.get('urls', []))
            except:
                pass
        
        # Count faculty sources  
        faculty_config = Path("config/faculty_search_sources.yaml")
        faculty_count = 0
        if faculty_config.exists():
            try:
                with open(faculty_config, 'r') as f:
                    data = yaml.safe_load(f)
                    faculty_count = len(data.get('databases', []))
            except:
                pass
        
        # Count test files
        test_files = list(Path("tests").glob("test_*.py")) if Path("tests").exists() else []
        
        # Count mock data files
        mock_files = list(Path("tests/mock_data").glob("*.json")) if Path("tests/mock_data").exists() else []
        
        print("📊 Current System Statistics:")
        print(f"   🎯 Funding sources configured: {funding_count}")
        print(f"   👨‍🔬 Faculty databases configured: {faculty_count}")
        print(f"   🧪 Test files: {len(test_files)}")
        print(f"   📝 Mock data files: {len(mock_files)}")
        
        # Show recent data files
        raw_data = Path("data/raw")
        processed_data = Path("data/processed")
        
        if raw_data.exists():
            recent_raw = sorted(raw_data.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
            print(f"\n📁 Recent raw data files:")
            for file in recent_raw:
                mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                print(f"   📄 {file.name} ({mtime})")
        
        if processed_data.exists():
            recent_processed = sorted(processed_data.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
            print(f"\n📊 Recent processed data files:")
            for file in recent_processed:
                mtime = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                print(f"   📄 {file.name} ({mtime})")
    
    def test_database_connection(self):
        """Test connection to a database"""
        self.print_section("Test Database Connection")
        
        url = input("📡 Enter the database URL to test: ").strip()
        if not url:
            print("❌ URL is required")
            return
        
        name = input("🏷️  Enter the database name: ").strip() or "Test Database"
        
        print(f"\n🔍 Testing connection to {name}...")
        
        request = DiscoveryRequest(
            request_type=RequestType.VALIDATE_API,
            database_url=url,
            database_name=name
        )
        
        try:
            response = self.discovery_agent.process_request(request)
            
            if response.success:
                results = response.validation_results
                print("✅ Connection successful!")
                print(f"   📊 Status Code: {results.get('status_code', 'Unknown')}")
                print(f"   ⚡ Response Time: {results.get('response_time', 'Unknown')}s")
                print(f"   📄 Content Type: {results.get('content_type', 'Unknown')}")
                print(f"   🔗 API Accessible: {results.get('api_accessible', False)}")
                print(f"   📝 JSON Response: {results.get('json_response', False)}")
                
                if results.get('estimated_results', 0) > 0:
                    print(f"   📈 Estimated Results: {results['estimated_results']}")
            else:
                print(f"❌ Connection failed: {response.error_message}")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    def show_configuration_files(self):
        """Show current configuration files and their contents"""
        self.print_section("Configuration Files")
        
        config_files = {
            "Funding Sources": "config/scraping_urls.yaml",
            "Faculty Databases": "config/faculty_search_sources.yaml", 
            "Easy Database Config": "config/easy_database_config.yaml"
        }
        
        for title, file_path in config_files.items():
            path = Path(file_path)
            print(f"\n📄 {title} ({file_path}):")
            
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        data = yaml.safe_load(f)
                    
                    if file_path == "config/scraping_urls.yaml":
                        urls = data.get('urls', [])
                        print(f"   Found {len(urls)} funding sources:")
                        for url_config in urls[:5]:  # Show first 5
                            print(f"   • {url_config.get('name', 'Unknown')}")
                        if len(urls) > 5:
                            print(f"   ... and {len(urls) - 5} more")
                    
                    elif file_path == "config/faculty_search_sources.yaml":
                        dbs = data.get('databases', [])
                        print(f"   Found {len(dbs)} faculty databases:")
                        for db_config in dbs[:5]:
                            print(f"   • {db_config.get('name', 'Unknown')}")
                        if len(dbs) > 5:
                            print(f"   ... and {len(dbs) - 5} more")
                    
                    else:
                        print(f"   ✅ Valid YAML file")
                        
                except Exception as e:
                    print(f"   ❌ Error reading file: {e}")
            else:
                print(f"   ❌ File not found")
        
        print(f"\n💡 To edit these files manually, use any text editor.")
        print(f"💡 Or use this CLI to add new sources automatically!")
    
    def execute_database_addition(self, url: str, name: str, database_type: DatabaseType, 
                                 artifacts: List[ArtifactType], api_key: str = None, is_api: bool = True):
        """Execute the database addition with progress feedback"""
        print(f"\n🚀 Adding {name}...")
        print(f"   📡 URL: {url}")
        print(f"   🎯 Type: {database_type.value}")
        print(f"   📦 Artifacts: {', '.join([a.value for a in artifacts])}")
        
        try:
            request = DiscoveryRequest(
                request_type=RequestType.GENERATE_ARTIFACTS,
                database_url=url,
                database_name=name,
                database_type=database_type,
                api_key=api_key,
                artifacts_requested=artifacts
            )
            
            print("\n⏳ Processing...")
            response = self.discovery_agent.process_request(request)
            
            if response.success:
                print("✅ Success! Generated artifacts:")
                
                for artifact_type, file_path in response.generated_artifacts.items():
                    metadata = response.artifact_metadata.get(artifact_type, {})
                    file_type = metadata.get('type', 'file')
                    print(f"   📄 {artifact_type.value}: {file_path} ({file_type})")
                
                # Show next steps
                print(f"\n🎉 {name} has been added to the system!")
                print("📋 Next steps:")
                
                if ArtifactType.TEST_FILE in response.generated_artifacts:
                    test_file = Path(response.generated_artifacts[ArtifactType.TEST_FILE]).name
                    print(f"   1. Run tests: pytest tests/{test_file} -v")
                
                if ArtifactType.CONFIG_FILE in response.generated_artifacts:
                    print(f"   2. Review and customize the generated configuration if needed")
                
                if database_type == DatabaseType.FUNDING:
                    print(f"   3. Run ingestion: python -m src.agents.ingestion_agent")
                else:
                    print(f"   3. Test faculty search with the new database")
                
                if ArtifactType.DOCUMENTATION in response.generated_artifacts:
                    doc_file = response.generated_artifacts[ArtifactType.DOCUMENTATION]
                    print(f"   4. Check documentation: {doc_file}")
                
            else:
                print(f"❌ Failed to add {name}: {response.error_message}")
                
        except Exception as e:
            print(f"❌ Error adding {name}: {e}")
    
    def select_custom_artifacts(self) -> List[ArtifactType]:
        """Let user select custom artifacts"""
        print("\n📦 Select artifacts to generate (multiple choice):")
        
        all_artifacts = [
            (ArtifactType.CONFIG_FILE, "Configuration file (YAML)"),
            (ArtifactType.TEST_FILE, "Test file (Python/pytest)"),
            (ArtifactType.MOCK_DATA, "Mock data (JSON)"),
            (ArtifactType.DOCUMENTATION, "API documentation (Markdown)"),
            (ArtifactType.INTEGRATION_GUIDE, "Integration guide (Markdown)"),
            (ArtifactType.PLUGIN_CODE, "Custom plugin template (Python)")
        ]
        
        selected = []
        for i, (artifact_type, description) in enumerate(all_artifacts, 1):
            choice = self.get_yes_no(f"   {i}. {description}", default=True)
            if choice:
                selected.append(artifact_type)
        
        if not selected:
            print("⚠️  No artifacts selected, using defaults")
            return [ArtifactType.CONFIG_FILE, ArtifactType.TEST_FILE, ArtifactType.MOCK_DATA]
        
        return selected
    
    def get_choice(self, options: List[str], default: int = 1) -> int:
        """Get user choice from a list of options"""
        for i, option in enumerate(options, 1):
            marker = " (default)" if i == default else ""
            print(f"   {i}. {option}{marker}")
        
        while True:
            try:
                choice = input(f"Choose (1-{len(options)}) [default: {default}]: ").strip()
                if not choice:
                    return default
                choice_num = int(choice)
                if 1 <= choice_num <= len(options):
                    return choice_num
                print(f"❌ Please choose a number between 1 and {len(options)}")
            except ValueError:
                print("❌ Please enter a valid number")
    
    def get_yes_no(self, question: str, default: bool = True) -> bool:
        """Get yes/no answer from user"""
        default_str = "Y/n" if default else "y/N"
        while True:
            answer = input(f"{question} [{default_str}]: ").strip().lower()
            if not answer:
                return default
            if answer in ['y', 'yes']:
                return True
            if answer in ['n', 'no']:
                return False
            print("❌ Please answer 'y' or 'n'")
    
    def extract_name_from_url(self, url: str) -> str:
        """Extract a reasonable name from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '').replace('api.', '')
        parts = domain.split('.')
        if len(parts) >= 2:
            name = parts[0]
        else:
            name = domain
        return name.replace('-', ' ').replace('_', ' ').title()
    
    def print_header(self):
        """Print program header"""
        print("\n" + "="*60)
        print("🔬 FACULTY RESEARCH OPPORTUNITY NOTIFIER")
        print("   System Management Interface")
        print("="*60)
    
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{'─'*50}")
        print(f"📋 {title}")
        print(f"{'─'*50}")

def main():
    """Main entry point"""
    try:
        manager = ResearchSystemManager()
        manager.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("📧 Please report this issue to the development team.")

if __name__ == "__main__":
    main()