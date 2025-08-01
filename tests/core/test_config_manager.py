"""
Tests for the configuration manager module.

This module contains comprehensive tests for the configuration manager,
including loading, saving, validation, and management of institutional configurations.
"""

import json
import pytest
import tempfile
import shutil
import yaml
from datetime import datetime
from pathlib import Path

from src.core.config_manager import (
    ConfigurationManager,
    InstitutionConfiguration,
    ConfigurationFormat,
    NotificationPreference,
    get_institution_config,
    create_institution_config,
    update_institution_config
)


class TestInstitutionConfiguration:
    """Test cases for the InstitutionConfiguration model."""
    
    def test_basic_configuration_creation(self):
        """Test creating a basic configuration."""
        config = InstitutionConfiguration(
            institution_name="Test University",
            institution_code="TESTUNI",
            admin_contact="admin@testuni.edu"
        )
        
        assert config.institution_name == "Test University"
        assert config.institution_code == "TESTUNI"
        assert config.admin_contact == "admin@testuni.edu"
        assert config.country == "United States"  # Default value
        assert config.timezone == "UTC"  # Default value
    
    def test_institution_code_validation(self):
        """Test institution code validation."""
        # Valid codes
        config = InstitutionConfiguration(
            institution_name="Test",
            institution_code="test123",
            admin_contact="test@test.edu"
        )
        assert config.institution_code == "TEST123"  # Should be uppercase
        
        # Invalid codes
        with pytest.raises(ValueError):
            InstitutionConfiguration(
                institution_name="Test",
                institution_code="test@invalid",  # Contains special characters
                admin_contact="test@test.edu"
            )
        
        with pytest.raises(ValueError):
            InstitutionConfiguration(
                institution_name="Test",
                institution_code="toolongcode12345",  # Too long
                admin_contact="test@test.edu"
            )
    
    def test_research_areas_normalization(self):
        """Test research areas are normalized to lowercase."""
        config = InstitutionConfiguration(
            institution_name="Test University",
            institution_code="TEST",
            admin_contact="admin@test.edu",
            primary_research_areas=["Computer Science", "BIOLOGY", "Physics "]
        )
        
        expected_areas = ["computer science", "biology", "physics"]
        assert config.primary_research_areas == expected_areas
    
    def test_default_values(self):
        """Test default values are set correctly."""
        config = InstitutionConfiguration(
            institution_name="Test University",
            institution_code="TEST",
            admin_contact="admin@test.edu"
        )
        
        assert config.notification_preferences == [NotificationPreference.EMAIL]
        assert config.notification_frequency == "daily"
        assert config.minimum_match_score == 0.6
        assert config.auto_notification_enabled is True
        assert config.analytics_enabled is True
        assert len(config.career_stage_weights) > 0
    
    def test_update_timestamp(self):
        """Test timestamp update functionality."""
        config = InstitutionConfiguration(
            institution_name="Test University",
            institution_code="TEST",
            admin_contact="admin@test.edu"
        )
        
        original_timestamp = config.last_updated
        config.update_timestamp()
        
        assert config.last_updated > original_timestamp


class TestConfigurationManager:
    """Test cases for the ConfigurationManager class."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config_manager(self, temp_config_dir):
        """Create a ConfigurationManager with temporary directory."""
        return ConfigurationManager(config_dir=temp_config_dir)
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        return InstitutionConfiguration(
            institution_name="Sample University",
            institution_code="SAMPLE",
            admin_contact="admin@sample.edu",
            primary_research_areas=["computer science", "biology"],
            funding_sources={
                "nih": {
                    "name": "National Institutes of Health",
                    "base_url": "https://reporter.nih.gov/",
                    "enabled": True,
                    "priority": 1
                }
            }
        )
    
    def test_create_configuration_template(self, config_manager):
        """Test creating a new configuration template."""
        config = config_manager.create_configuration_template(
            institution_name="New University",
            institution_code="NEWUNI",
            admin_contact="admin@newuni.edu"
        )
        
        assert config.institution_name == "New University"
        assert config.institution_code == "NEWUNI"
        assert config.admin_contact == "admin@newuni.edu"
        
        # Should have default funding sources
        assert "nih" in config.funding_sources
        assert "nsf" in config.funding_sources
        
        # Should have default faculty data sources
        assert "google_scholar" in config.faculty_data_sources
        assert "institutional" in config.faculty_data_sources
    
    def test_save_and_load_yaml_configuration(self, config_manager, sample_config):
        """Test saving and loading YAML configuration."""
        # Save configuration
        file_path = config_manager.save_configuration(sample_config, ConfigurationFormat.YAML)
        
        assert file_path.exists()
        assert file_path.suffix == ".yaml"
        
        # Load configuration
        loaded_config = config_manager.load_configuration("SAMPLE")
        
        assert loaded_config.institution_name == sample_config.institution_name
        assert loaded_config.institution_code == sample_config.institution_code
        assert loaded_config.admin_contact == sample_config.admin_contact
        assert loaded_config.primary_research_areas == sample_config.primary_research_areas
    
    def test_save_and_load_json_configuration(self, config_manager, sample_config):
        """Test saving and loading JSON configuration."""
        # Save configuration
        file_path = config_manager.save_configuration(sample_config, ConfigurationFormat.JSON)
        
        assert file_path.exists()
        assert file_path.suffix == ".json"
        
        # Load configuration
        loaded_config = config_manager.load_configuration("SAMPLE")
        
        assert loaded_config.institution_name == sample_config.institution_name
        assert loaded_config.funding_sources == sample_config.funding_sources
    
    def test_configuration_caching(self, config_manager, sample_config):
        """Test configuration caching functionality."""
        # Save configuration
        config_manager.save_configuration(sample_config, ConfigurationFormat.YAML)
        
        # Load configuration twice
        config1 = config_manager.load_configuration("SAMPLE", use_cache=True)
        config2 = config_manager.load_configuration("SAMPLE", use_cache=True)
        
        # Should be the same object due to caching
        assert config1 is config2
        
        # Load without cache should create new object
        config3 = config_manager.load_configuration("SAMPLE", use_cache=False)
        assert config1 is not config3
        assert config1.institution_name == config3.institution_name
    
    def test_update_configuration(self, config_manager, sample_config):
        """Test updating an existing configuration."""
        # Save initial configuration
        config_manager.save_configuration(sample_config, ConfigurationFormat.YAML)
        
        # Update configuration
        updates = {
            "notification_frequency": "weekly",
            "minimum_match_score": 0.75,
            "custom_field": "custom_value"
        }
        
        updated_config = config_manager.update_configuration("SAMPLE", updates)
        
        assert updated_config.notification_frequency == "weekly"
        assert updated_config.minimum_match_score == 0.75
        assert updated_config.custom_fields["custom_field"] == "custom_value"
        
        # Verify changes were saved
        loaded_config = config_manager.load_configuration("SAMPLE", use_cache=False)
        assert loaded_config.notification_frequency == "weekly"
        assert loaded_config.minimum_match_score == 0.75
    
    def test_list_configurations(self, config_manager):
        """Test listing all available configurations."""
        # Create multiple configurations
        configs = [
            InstitutionConfiguration(
                institution_name="University A",
                institution_code="UNIA",
                admin_contact="admin@unia.edu"
            ),
            InstitutionConfiguration(
                institution_name="University B",
                institution_code="UNIB",
                admin_contact="admin@unib.edu"
            )
        ]
        
        for config in configs:
            config_manager.save_configuration(config)
        
        # List configurations
        config_list = config_manager.list_configurations()
        
        assert len(config_list) == 2
        
        # Check that they're sorted by institution name
        assert config_list[0]["institution_name"] == "University A"
        assert config_list[1]["institution_name"] == "University B"
        
        # Check required fields are present
        for config_info in config_list:
            assert "institution_code" in config_info
            assert "institution_name" in config_info
            assert "admin_contact" in config_info
            assert "last_updated" in config_info
            assert "file_path" in config_info
    
    def test_validate_configuration(self, config_manager):
        """Test configuration validation."""
        # Valid configuration
        valid_config = InstitutionConfiguration(
            institution_name="Valid University",
            institution_code="VALID",
            admin_contact="admin@valid.edu",
            primary_research_areas=["computer science"],
            funding_sources={
                "nih": {
                    "name": "NIH",
                    "base_url": "https://nih.gov",
                    "enabled": True
                }
            }
        )
        
        validation_result = config_manager.validate_configuration(valid_config)
        
        assert len(validation_result["errors"]) == 0
        
        # Invalid configuration
        invalid_config = InstitutionConfiguration(
            institution_name="Invalid University",
            institution_code="INVALID",
            admin_contact="invalid-email",  # Invalid email
            minimum_match_score=1.5  # Invalid score
        )
        
        validation_result = config_manager.validate_configuration(invalid_config)
        
        assert len(validation_result["errors"]) > 0
        assert any("admin_contact" in error for error in validation_result["errors"])
    
    def test_export_configuration_summary(self, config_manager, sample_config):
        """Test exporting configuration summary."""
        # Save configuration
        config_manager.save_configuration(sample_config)
        
        # Export summary
        summary = config_manager.export_configuration_summary("SAMPLE")
        
        # Check summary structure
        assert "institution" in summary
        assert "research_focus" in summary
        assert "funding_sources" in summary
        assert "faculty_data_sources" in summary
        assert "notifications" in summary
        assert "matching" in summary
        assert "system" in summary
        assert "metadata" in summary
        
        # Check specific values
        assert summary["institution"]["name"] == "Sample University"
        assert summary["institution"]["code"] == "SAMPLE"
        assert summary["funding_sources"]["total"] == 1
        assert summary["funding_sources"]["enabled"] == 1
    
    def test_error_handling(self, config_manager):
        """Test error handling for various scenarios."""
        # Test loading non-existent configuration
        with pytest.raises(FileNotFoundError):
            config_manager.load_configuration("NONEXISTENT")
        
        # Test updating non-existent configuration
        with pytest.raises(FileNotFoundError):
            config_manager.update_configuration("NONEXISTENT", {"key": "value"})
        
        # Test exporting summary for non-existent configuration
        with pytest.raises(FileNotFoundError):
            config_manager.export_configuration_summary("NONEXISTENT")
    
    def test_clear_cache(self, config_manager, sample_config):
        """Test cache clearing functionality."""
        # Save and load configuration to populate cache
        config_manager.save_configuration(sample_config)
        config_manager.load_configuration("SAMPLE")
        
        # Verify cache is populated
        assert "SAMPLE" in config_manager._config_cache
        
        # Clear cache
        config_manager.clear_cache()
        
        # Verify cache is empty
        assert len(config_manager._config_cache) == 0
    
    def test_invalid_file_format_handling(self, config_manager, temp_config_dir):
        """Test handling of invalid configuration files."""
        # Create invalid YAML file
        invalid_yaml_path = Path(temp_config_dir) / "INVALID.yaml"
        with open(invalid_yaml_path, 'w') as f:
            f.write("invalid: yaml: content: [unclosed")
        
        # Should raise ValueError for invalid YAML
        with pytest.raises(ValueError):
            config_manager.load_configuration("INVALID")
        
        # Create invalid JSON file
        invalid_json_path = Path(temp_config_dir) / "INVALID2.json"
        with open(invalid_json_path, 'w') as f:
            f.write('{"invalid": json content}')
        
        # Should raise ValueError for invalid JSON
        with pytest.raises(ValueError):
            config_manager.load_configuration("INVALID2")
    
    def test_default_configuration_loading(self, temp_config_dir):
        """Test loading default configuration template."""
        # Create default configuration
        default_config = InstitutionConfiguration(
            institution_name="Default Template",
            institution_code="DEFAULT",
            admin_contact="admin@default.edu"
        )
        
        # Save as default.yaml
        default_path = Path(temp_config_dir) / "default.yaml"
        with open(default_path, 'w') as f:
            yaml.dump(default_config.model_dump(), f)
        
        # Create new manager (should load default)
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        assert manager._default_config is not None
        assert manager._default_config.institution_name == "Default Template"
    
    def test_configuration_with_datetime_handling(self, config_manager, sample_config):
        """Test proper handling of datetime fields in configurations."""
        # Set specific datetime
        test_datetime = datetime(2025, 1, 31, 12, 0, 0)
        sample_config.created_date = test_datetime
        sample_config.last_updated = test_datetime
        
        # Save configuration
        config_manager.save_configuration(sample_config, ConfigurationFormat.JSON)
        
        # Load configuration
        loaded_config = config_manager.load_configuration("SAMPLE")
        
        # Datetimes should be preserved (within reasonable precision)
        assert loaded_config.created_date.date() == test_datetime.date()
        assert loaded_config.last_updated.date() == test_datetime.date()


class TestConfigurationIntegration:
    """Integration tests for configuration management."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_complete_configuration_workflow(self, temp_config_dir):
        """Test complete configuration management workflow."""
        # Initialize manager
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        # Create new configuration
        config = manager.create_configuration_template(
            institution_name="Workflow University",
            institution_code="WORKFLOW",
            admin_contact="admin@workflow.edu"
        )
        
        # Verify it was saved
        config_list = manager.list_configurations()
        assert len(config_list) == 1
        assert config_list[0]["institution_code"] == "WORKFLOW"
        
        # Update configuration
        updated_config = manager.update_configuration(
            "WORKFLOW",
            {
                "notification_frequency": "weekly",
                "primary_research_areas": ["engineering", "computer science"]
            }
        )
        
        assert updated_config.notification_frequency == "weekly"
        assert "engineering" in updated_config.primary_research_areas
        
        # Validate configuration
        validation_result = manager.validate_configuration(updated_config)
        assert len(validation_result["errors"]) == 0
        
        # Export summary
        summary = manager.export_configuration_summary("WORKFLOW")
        assert summary["institution"]["name"] == "Workflow University"
        assert summary["notifications"]["frequency"] == "weekly"
    
    def test_multiple_format_compatibility(self, temp_config_dir):
        """Test that configurations work across different formats."""
        manager = ConfigurationManager(config_dir=temp_config_dir)
        
        # Create configuration
        config = InstitutionConfiguration(
            institution_name="Format Test University",
            institution_code="FORMAT",
            admin_contact="admin@format.edu",
            primary_research_areas=["test area"],
            minimum_match_score=0.8
        )
        
        # Save as YAML
        yaml_path = manager.save_configuration(config, ConfigurationFormat.YAML)
        assert yaml_path.suffix == ".yaml"
        
        # Load and save as JSON
        loaded_config = manager.load_configuration("FORMAT")
        json_path = manager.save_configuration(loaded_config, ConfigurationFormat.JSON)
        assert json_path.suffix == ".json"
        
        # Load JSON version and verify equivalence
        json_config = manager.load_configuration("FORMAT", use_cache=False)
        
        assert json_config.institution_name == config.institution_name
        assert json_config.minimum_match_score == config.minimum_match_score
        assert json_config.primary_research_areas == config.primary_research_areas


class TestGlobalFunctions:
    """Test cases for global convenience functions."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary configuration directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_global_get_institution_config(self, temp_config_dir, monkeypatch):
        """Test global get_institution_config function."""
        # Mock the global config_manager
        from src.core.config_manager import config_manager as global_manager
        monkeypatch.setattr(global_manager, "config_dir", Path(temp_config_dir))
        
        # Create a configuration
        config = InstitutionConfiguration(
            institution_name="Global Test",
            institution_code="GLOBAL",
            admin_contact="admin@global.edu"
        )
        
        global_manager.save_configuration(config)
        
        # Test global function
        loaded_config = get_institution_config("GLOBAL")
        assert loaded_config.institution_name == "Global Test"
    
    def test_global_create_institution_config(self, temp_config_dir, monkeypatch):
        """Test global create_institution_config function."""
        from src.core.config_manager import config_manager as global_manager
        monkeypatch.setattr(global_manager, "config_dir", Path(temp_config_dir))
        
        # Test global creation function
        config = create_institution_config(
            institution_name="Global Create Test",
            institution_code="GCREATE",
            admin_contact="admin@gcreate.edu"
        )
        
        assert config.institution_name == "Global Create Test"
        assert config.institution_code == "GCREATE"
        
        # Verify it was saved
        configs = global_manager.list_configurations()
        assert len(configs) == 1
    
    def test_global_update_institution_config(self, temp_config_dir, monkeypatch):
        """Test global update_institution_config function."""
        from src.core.config_manager import config_manager as global_manager
        monkeypatch.setattr(global_manager, "config_dir", Path(temp_config_dir))
        
        # Create initial configuration
        global_manager.create_configuration_template(
            "Global Update Test",
            "GUPDATE", 
            "admin@gupdate.edu"
        )
        
        # Test global update function
        updated_config = update_institution_config(
            "GUPDATE",
            {"notification_frequency": "monthly"}
        )
        
        assert updated_config.notification_frequency == "monthly"