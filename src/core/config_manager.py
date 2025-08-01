"""
Configuration Manager for the Faculty Research Opportunity Notifier.

This module provides comprehensive configuration management capabilities
for different institutions, allowing customization of:
- Institution-specific settings
- Funding source preferences
- Notification templates
- Research area mappings
- Faculty data sources
- System behaviors
"""

import logging
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ConfigurationFormat(str, Enum):
    """Supported configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"


class NotificationPreference(str, Enum):
    """Notification delivery preferences."""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    DISABLED = "disabled"


@dataclass
class FundingSourceConfig:
    """Configuration for a funding source."""
    name: str
    base_url: str
    enabled: bool = True
    scraping_frequency_hours: int = 24
    priority: int = 1  # 1 = highest priority
    custom_parameters: Dict[str, Any] = field(default_factory=dict)
    eligibility_keywords: List[str] = field(default_factory=list)
    exclude_keywords: List[str] = field(default_factory=list)


@dataclass
class FacultyDataSourceConfig:
    """Configuration for faculty data sources."""
    name: str
    source_type: str  # google_scholar, orcid, institutional, etc.
    base_url: Optional[str] = None
    enabled: bool = True
    update_frequency_hours: int = 168  # Weekly by default
    api_key_required: bool = False
    rate_limit_per_hour: int = 100
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


class InstitutionConfiguration(BaseModel):
    """
    Comprehensive configuration model for an institution.
    """
    
    # Basic Institution Information
    institution_name: str = Field(..., description="Full institution name")
    institution_code: str = Field(..., description="Short institution code")
    country: str = Field(default="United States", description="Country name")
    timezone: str = Field(default="UTC", description="Institution timezone")
    
    # Contact and Administrative Information
    admin_contact: str = Field(..., description="Administrative contact email")
    system_admin: Optional[str] = Field(None, description="System administrator contact")
    support_email: Optional[str] = Field(None, description="Support contact email")
    
    # Research Areas and Priorities
    primary_research_areas: List[str] = Field(default_factory=list, description="Primary research focus areas")
    excluded_research_areas: List[str] = Field(default_factory=list, description="Areas to exclude from matching")
    research_keywords: List[str] = Field(default_factory=list, description="Institution-specific research keywords")
    
    # Funding Source Configuration
    funding_sources: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Configuration for funding sources"
    )
    funding_preferences: Dict[str, int] = Field(
        default_factory=dict, 
        description="Funding source priorities (1=highest)"
    )
    
    # Faculty Data Sources
    faculty_data_sources: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Configuration for faculty data sources"
    )
    
    # Notification Settings
    notification_preferences: List[NotificationPreference] = Field(
        default=[NotificationPreference.EMAIL],
        description="Preferred notification methods"
    )
    notification_frequency: str = Field(
        default="daily",
        description="Notification frequency: immediate, daily, weekly"
    )
    notification_template_override: Optional[str] = Field(
        None,
        description="Path to custom notification templates"
    )
    
    # Matching and Scoring Configuration
    matching_algorithm: str = Field(
        default="multi_dimensional_v1",
        description="Algorithm to use for faculty-funding matching"
    )
    minimum_match_score: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum score for match to be considered"
    )
    career_stage_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "graduate_student": 0.8,
            "postdoc": 0.9,
            "assistant_professor": 1.0,
            "associate_professor": 0.8,
            "full_professor": 0.6,
            "emeritus": 0.3
        },
        description="Weights for different career stages"
    )
    
    # System Behavior Configuration
    auto_notification_enabled: bool = Field(default=True, description="Enable automatic notifications")
    batch_processing_enabled: bool = Field(default=True, description="Enable batch processing")
    analytics_enabled: bool = Field(default=True, description="Enable analytics collection")
    external_integrations_enabled: bool = Field(default=True, description="Enable external integrations")
    
    # Data Retention and Privacy
    data_retention_days: int = Field(default=365, description="Days to retain data")
    anonymize_data: bool = Field(default=False, description="Anonymize personal data")
    gdpr_compliance: bool = Field(default=False, description="Enable GDPR compliance mode")
    
    # API and Integration Settings
    api_rate_limits: Dict[str, int] = Field(
        default_factory=lambda: {
            "per_minute": 60,
            "per_hour": 1000,
            "per_day": 10000
        },
        description="API rate limits"
    )
    webhook_endpoints: Dict[str, str] = Field(
        default_factory=dict,
        description="Webhook endpoints for integrations"
    )
    
    # Custom Fields and Extensions
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Institution-specific custom configuration"
    )
    
    # Configuration Metadata
    config_version: str = Field(default="1.0.0", description="Configuration version")
    created_date: datetime = Field(default_factory=datetime.now, description="Configuration creation date")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    
    @field_validator('institution_code')
    @classmethod
    def validate_institution_code(cls, v):
        if not v.isalnum() or len(v) > 10:
            raise ValueError('Institution code must be alphanumeric and max 10 characters')
        return v.upper()
    
    @field_validator('primary_research_areas')
    @classmethod
    def validate_research_areas(cls, v):
        return [area.lower().strip() for area in v]
    
    def update_timestamp(self):
        """Update the last_updated timestamp."""
        self.last_updated = datetime.now()


class ConfigurationManager:
    """
    Manager for institutional configuration handling.
    """
    
    def __init__(self, config_dir: str = "config/institution_templates"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing institutional configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded configurations
        self._config_cache: Dict[str, InstitutionConfiguration] = {}
        self._default_config: Optional[InstitutionConfiguration] = None
        
        # Load default configuration if available
        self._load_default_config()
    
    def _load_default_config(self):
        """Load the default configuration template."""
        default_path = self.config_dir / "default.yaml"
        if default_path.exists():
            try:
                self._default_config = self.load_configuration("default")
                logger.info("Default configuration loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load default configuration: {e}")
    
    def create_configuration_template(
        self,
        institution_name: str,
        institution_code: str,
        admin_contact: str,
        format: ConfigurationFormat = ConfigurationFormat.YAML
    ) -> InstitutionConfiguration:
        """
        Create a new configuration template for an institution.
        
        Args:
            institution_name: Full institution name
            institution_code: Short institution code
            admin_contact: Administrative contact email
            format: Configuration file format
            
        Returns:
            InstitutionConfiguration: New configuration instance
        """
        # Start with default config if available
        if self._default_config:
            config_data = self._default_config.model_dump()
            config_data.update({
                "institution_name": institution_name,
                "institution_code": institution_code,
                "admin_contact": admin_contact,
                "created_date": datetime.now(),
                "last_updated": datetime.now()
            })
            config = InstitutionConfiguration(**config_data)
        else:
            # Create minimal configuration
            config = InstitutionConfiguration(
                institution_name=institution_name,
                institution_code=institution_code,
                admin_contact=admin_contact
            )
        
        # Add some sensible defaults
        config.funding_sources = {
            "nih": {
                "name": "National Institutes of Health",
                "base_url": "https://reporter.nih.gov/",
                "enabled": True,
                "priority": 1,
                "scraping_frequency_hours": 24
            },
            "nsf": {
                "name": "National Science Foundation",
                "base_url": "https://www.nsf.gov/funding/",
                "enabled": True,
                "priority": 2,
                "scraping_frequency_hours": 24
            }
        }
        
        config.faculty_data_sources = {
            "google_scholar": {
                "name": "Google Scholar",
                "source_type": "google_scholar",
                "enabled": True,
                "update_frequency_hours": 168,
                "rate_limit_per_hour": 100
            },
            "institutional": {
                "name": "Institutional Directory",
                "source_type": "institutional",
                "enabled": True,
                "update_frequency_hours": 24,
                "rate_limit_per_hour": 1000
            }
        }
        
        # Save the configuration
        self.save_configuration(config, format)
        
        return config
    
    def load_configuration(
        self,
        institution_code: str,
        use_cache: bool = True
    ) -> InstitutionConfiguration:
        """
        Load configuration for an institution.
        
        Args:
            institution_code: Institution code
            use_cache: Whether to use cached configuration
            
        Returns:
            InstitutionConfiguration: Loaded configuration
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is invalid
        """
        if use_cache and institution_code in self._config_cache:
            return self._config_cache[institution_code]
        
        # Try different file extensions
        for ext in ['yaml', 'yml', 'json']:
            config_path = self.config_dir / f"{institution_code}.{ext}"
            if config_path.exists():
                config = self._load_config_file(config_path)
                
                if use_cache:
                    self._config_cache[institution_code] = config
                
                return config
        
        raise FileNotFoundError(
            f"Configuration file for institution '{institution_code}' not found in {self.config_dir}"
        )
    
    def _load_config_file(self, file_path: Path) -> InstitutionConfiguration:
        """Load configuration from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            # Convert datetime strings if present
            if isinstance(data.get('created_date'), str):
                data['created_date'] = datetime.fromisoformat(data['created_date'])
            if isinstance(data.get('last_updated'), str):
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
            
            return InstitutionConfiguration(**data)
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
            raise ValueError(f"Invalid configuration file {file_path}: {e}")
    
    def save_configuration(
        self,
        config: InstitutionConfiguration,
        format: ConfigurationFormat = ConfigurationFormat.YAML
    ) -> Path:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            format: File format to use
            
        Returns:
            Path: Path to saved configuration file
        """
        # Update timestamp
        config.update_timestamp()
        
        # Determine file path
        if format == ConfigurationFormat.YAML:
            file_path = self.config_dir / f"{config.institution_code}.yaml"
        elif format == ConfigurationFormat.JSON:
            file_path = self.config_dir / f"{config.institution_code}.json"
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Convert to dictionary
        config_data = config.model_dump()
        
        # Convert datetime objects to strings
        config_data['created_date'] = config.created_date.isoformat()
        config_data['last_updated'] = config.last_updated.isoformat()
        
        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == ConfigurationFormat.YAML:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                elif format == ConfigurationFormat.JSON:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._config_cache[config.institution_code] = config
            
            logger.info(f"Configuration saved for {config.institution_name} ({config.institution_code})")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def update_configuration(
        self,
        institution_code: str,
        updates: Dict[str, Any],
        save: bool = True
    ) -> InstitutionConfiguration:
        """
        Update an existing configuration.
        
        Args:
            institution_code: Institution code
            updates: Dictionary of updates to apply
            save: Whether to save after updating
            
        Returns:
            InstitutionConfiguration: Updated configuration
        """
        config = self.load_configuration(institution_code)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                # Add to custom_fields if not a standard field
                config.custom_fields[key] = value
        
        config.update_timestamp()
        
        if save:
            self.save_configuration(config)
        
        return config
    
    def list_configurations(self) -> List[Dict[str, str]]:
        """
        List all available configurations.
        
        Returns:
            List of configuration summaries
        """
        configs = []
        
        for config_file in self.config_dir.glob("*.{yaml,yml,json}"):
            if config_file.stem == "default":
                continue
            
            try:
                config = self._load_config_file(config_file)
                configs.append({
                    "institution_code": config.institution_code,
                    "institution_name": config.institution_name,
                    "admin_contact": config.admin_contact,
                    "last_updated": config.last_updated.isoformat(),
                    "file_path": str(config_file)
                })
            except Exception as e:
                logger.warning(f"Failed to load config summary from {config_file}: {e}")
        
        return sorted(configs, key=lambda x: x["institution_name"])
    
    def validate_configuration(self, config: InstitutionConfiguration) -> Dict[str, List[str]]:
        """
        Validate a configuration and return any issues.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Dict with validation results
        """
        issues = {
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check required fields
        if not config.admin_contact or "@" not in config.admin_contact:
            issues["errors"].append("Valid admin_contact email is required")
        
        if not config.primary_research_areas:
            issues["warnings"].append("No primary research areas specified")
        
        if not config.funding_sources:
            issues["errors"].append("At least one funding source must be configured")
        
        # Check funding source configurations
        for source_name, source_config in config.funding_sources.items():
            if not source_config.get("base_url"):
                issues["warnings"].append(f"No base_url specified for funding source '{source_name}'")
        
        # Check notification settings
        if NotificationPreference.EMAIL in config.notification_preferences:
            if not config.admin_contact:
                issues["errors"].append("Email notifications enabled but no admin contact specified")
        
        # Check scoring configuration
        if config.minimum_match_score < 0.3:
            issues["warnings"].append("Very low minimum match score may result in poor quality matches")
        elif config.minimum_match_score > 0.9:
            issues["warnings"].append("Very high minimum match score may result in too few matches")
        
        # Suggestions for improvement
        if len(config.funding_sources) < 3:
            issues["suggestions"].append("Consider adding more funding sources for better coverage")
        
        if not config.research_keywords:
            issues["suggestions"].append("Adding research keywords can improve matching accuracy")
        
        return issues
    
    def export_configuration_summary(self, institution_code: str) -> Dict[str, Any]:
        """
        Export a summary of configuration for reporting.
        
        Args:
            institution_code: Institution code
            
        Returns:
            Configuration summary
        """
        config = self.load_configuration(institution_code)
        
        return {
            "institution": {
                "name": config.institution_name,
                "code": config.institution_code,
                "country": config.country,
                "admin_contact": config.admin_contact
            },
            "research_focus": {
                "primary_areas": config.primary_research_areas,
                "keywords": config.research_keywords,
                "excluded_areas": config.excluded_research_areas
            },
            "funding_sources": {
                "total": len(config.funding_sources),
                "enabled": len([s for s in config.funding_sources.values() if s.get("enabled", True)]),
                "sources": list(config.funding_sources.keys())
            },
            "faculty_data_sources": {
                "total": len(config.faculty_data_sources),
                "enabled": len([s for s in config.faculty_data_sources.values() if s.get("enabled", True)]),
                "sources": list(config.faculty_data_sources.keys())
            },
            "notifications": {
                "methods": config.notification_preferences,
                "frequency": config.notification_frequency,
                "auto_enabled": config.auto_notification_enabled
            },
            "matching": {
                "algorithm": config.matching_algorithm,
                "minimum_score": config.minimum_match_score,
                "career_stage_weights": config.career_stage_weights
            },
            "system": {
                "analytics_enabled": config.analytics_enabled,
                "batch_processing": config.batch_processing_enabled,
                "data_retention_days": config.data_retention_days,
                "gdpr_compliance": config.gdpr_compliance
            },
            "metadata": {
                "config_version": config.config_version,
                "created": config.created_date.isoformat(),
                "last_updated": config.last_updated.isoformat()
            }
        }
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._config_cache.clear()
        logger.info("Configuration cache cleared")
    
    def get_active_configuration(self) -> Optional[InstitutionConfiguration]:
        """
        Get the currently active configuration.
        This would typically be determined by environment variables or system settings.
        """
        # For now, return the first available configuration
        configs = self.list_configurations()
        if configs:
            return self.load_configuration(configs[0]["institution_code"])
        return None


# Global configuration manager instance
config_manager = ConfigurationManager()


# Convenience functions
def get_institution_config(institution_code: str) -> InstitutionConfiguration:
    """Get configuration for an institution."""
    return config_manager.load_configuration(institution_code)


def create_institution_config(
    institution_name: str,
    institution_code: str,
    admin_contact: str
) -> InstitutionConfiguration:
    """Create a new institutional configuration."""
    return config_manager.create_configuration_template(
        institution_name, institution_code, admin_contact
    )


def update_institution_config(
    institution_code: str,
    updates: Dict[str, Any]
) -> InstitutionConfiguration:
    """Update an institutional configuration."""
    return config_manager.update_configuration(institution_code, updates)