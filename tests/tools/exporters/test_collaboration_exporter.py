"""
Tests for the collaboration exporter module.

This module contains comprehensive tests for the collaboration exporter,
including export format validation, email template generation, and content verification.
"""

import json
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from src.tools.exporters.collaboration_exporter import (
    CollaborationExporter,
    CollaborationExportConfig,
    CollaborationExportFormat
)
from src.core.models import (
    CollaboratorSuggestion,
    FacultyProfile,
    ResearchIdea,
    CareerStage,
    ResearchMethodology,
    ProposalVariant
)
from decimal import Decimal


class TestCollaborationExporter:
    """Test cases for the CollaborationExporter class."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def exporter(self, temp_output_dir):
        """Create a CollaborationExporter instance with temporary output directory."""
        return CollaborationExporter(output_dir=temp_output_dir)
    
    @pytest.fixture
    def sample_primary_faculty(self):
        """Create a sample primary faculty profile for testing."""
        return FacultyProfile(
            name="Dr. Sarah Johnson",
            email="s.johnson@university.edu",
            institution="State University",
            department="Computer Science",
            career_stage=CareerStage.ASSISTANT_PROFESSOR,
            research_interests=["machine learning", "healthcare informatics", "data mining"],
            methodologies=[ResearchMethodology.COMPUTATIONAL, ResearchMethodology.EXPERIMENTAL],
            h_index=15,
            total_citations=450,
            years_active=5,
            profile_id="prof_primary_001",
            institutional_profile_url="https://cs.university.edu/faculty/johnson"
        )
    
    @pytest.fixture
    def sample_collaborator_suggestions(self):
        """Create sample collaborator suggestions for testing."""
        return [
            CollaboratorSuggestion(
                faculty_profile_id="collab_001",
                name="Dr. Michael Chen",
                institution="Tech Institute",
                relevance_score=0.92,
                complementary_expertise=["deep learning", "neural networks", "computer vision"],
                shared_interests=["machine learning", "healthcare informatics"],
                previous_collaborations=0,
                common_publications=[],
                email="m.chen@techinstitute.edu",
                profile_url="https://techinstitute.edu/faculty/chen"
            ),
            CollaboratorSuggestion(
                faculty_profile_id="collab_002",
                name="Dr. Emily Rodriguez",
                institution="Medical College",
                relevance_score=0.87,
                complementary_expertise=["clinical data analysis", "biostatistics", "epidemiology"],
                shared_interests=["healthcare informatics", "data mining"],
                previous_collaborations=1,
                common_publications=["Collaborative Study on Patient Outcomes (2022)"],
                email="e.rodriguez@medicalcollege.edu",
                profile_url="https://medicalcollege.edu/faculty/rodriguez"
            ),
            CollaboratorSuggestion(
                faculty_profile_id="collab_003",
                name="Dr. James Wilson",
                institution="Research University",
                relevance_score=0.75,
                complementary_expertise=["software engineering", "system design", "databases"],
                shared_interests=["data mining"],
                previous_collaborations=0,
                common_publications=[],
                email="j.wilson@researchuniv.edu"
            ),
            CollaboratorSuggestion(
                faculty_profile_id="collab_004",
                name="Dr. Lisa Park",
                institution="Innovation Institute",
                relevance_score=0.65,
                complementary_expertise=["user interface design", "human-computer interaction"],
                shared_interests=["machine learning"],
                previous_collaborations=2,
                common_publications=["HCI in ML Systems (2021)", "User-Centered AI Design (2023)"],
                email="l.park@innovation.edu"
            )
        ]
    
    @pytest.fixture
    def sample_research_context(self):
        """Create a sample research context for testing."""
        return ResearchIdea(
            title="AI-Powered Clinical Decision Support System",
            variant_type=ProposalVariant.INNOVATIVE,
            research_question="How can AI improve clinical decision-making in emergency departments?",
            methodology=[ResearchMethodology.COMPUTATIONAL, ResearchMethodology.CLINICAL],
            objectives=[
                "Develop AI algorithms for clinical decision support",
                "Validate algorithms in clinical settings",
                "Assess impact on patient outcomes"
            ],
            timeline_months=24,
            estimated_budget=Decimal("500000.00"),
            innovation_level=0.85,
            feasibility_score=0.78,
            impact_potential=0.90
        )
    
    def test_export_json_format(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test JSON export format."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.JSON,
            output_filename="test_collaboration.json"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        assert result["format"] == "json"
        assert result["collaborators_exported"] == 4
        
        # Verify file exists and content
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert "primary_faculty" in data
        assert "collaborator_suggestions" in data
        assert "summary" in data
        assert data["primary_faculty"]["name"] == sample_primary_faculty.name
        assert len(data["collaborator_suggestions"]) == 4
        assert data["summary"]["total_suggestions"] == 4
        assert data["summary"]["high_relevance_suggestions"] == 2  # >= 0.8
    
    def test_export_csv_format(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test CSV export format."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.CSV,
            output_filename="test_collaboration.csv"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        assert result["format"] == "csv"
        
        # Verify file exists and basic structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "primary_faculty_name" in content
            assert sample_primary_faculty.name in content
            assert "Dr. Michael Chen" in content
            assert "machine learning" in content
    
    def test_export_email_template(self, exporter, sample_primary_faculty, sample_collaborator_suggestions, sample_research_context):
        """Test email template export format."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.EMAIL_TEMPLATE,
            email_tone="professional",
            sender_name="Dr. Research Coordinator",
            sender_email="coordinator@university.edu",
            sender_institution="State University",
            output_filename="test_emails.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            sample_research_context,
            config
        )
        
        assert result["success"] is True
        assert result["format"] == "email_template"
        assert result["email_templates_generated"] == 4
        
        # Verify file exists and email structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "COLLABORATION EMAIL TEMPLATES" in content
            assert "Dear Dr. Chen," in content  # Professional greeting
            assert sample_primary_faculty.name in content
            assert sample_research_context.title in content
            assert "Best regards," in content  # Professional closing
            assert "Dr. Research Coordinator" in content
    
    def test_email_tone_variations(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test different email tone variations."""
        # Test casual tone
        config_casual = CollaborationExportConfig(
            format=CollaborationExportFormat.EMAIL_TEMPLATE,
            email_tone="casual",
            output_filename="test_casual_emails.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions[:1],  # Just one for speed
            config=config_casual
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            assert "Hi Chen," in content  # Casual greeting
            assert "Best," in content  # Casual closing
        
        # Test formal tone
        config_formal = CollaborationExportConfig(
            format=CollaborationExportFormat.EMAIL_TEMPLATE,
            email_tone="formal",
            output_filename="test_formal_emails.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions[:1],
            config=config_formal
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            assert "Dear Professor Chen," in content  # Formal greeting
            assert "Respectfully yours," in content  # Formal closing
    
    def test_export_contact_sheet(self, exporter, sample_primary_faculty, sample_collaborator_suggestions, sample_research_context):
        """Test contact sheet export format."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.CONTACT_SHEET,
            output_filename="test_contact_sheet.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            sample_research_context,
            config
        )
        
        assert result["success"] is True
        assert result["format"] == "contact_sheet"
        
        # Verify file exists and contact sheet structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "COLLABORATION CONTACT SHEET" in content
            assert sample_primary_faculty.name in content
            assert "RESEARCH CONTEXT" in content
            assert sample_research_context.title in content
            assert "SUGGESTED COLLABORATORS" in content
            assert "Dr. Michael Chen" in content
            assert "Tech Institute" in content
            assert "SUMMARY STATISTICS" in content
            assert "Total Suggestions: 4" in content
            assert "High Relevance" in content
    
    def test_export_networking_report(self, exporter, sample_primary_faculty, sample_collaborator_suggestions, sample_research_context):
        """Test networking report export format."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.NETWORKING_REPORT,
            output_filename="test_networking_report.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            sample_research_context,
            config
        )
        
        assert result["success"] is True
        assert result["format"] == "networking_report"
        
        # Verify file exists and report structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "RESEARCH NETWORKING REPORT" in content
            assert "EXECUTIVE SUMMARY" in content
            assert "RESEARCH PROFILE ANALYSIS" in content
            assert "TOP COLLABORATION RECOMMENDATIONS" in content
            assert "NETWORK ANALYSIS" in content
            assert "RECOMMENDED ACTIONS" in content
            assert "HIGHLY RECOMMENDED" in content or "RECOMMENDED" in content
            assert sample_primary_faculty.name in content
            assert str(sample_primary_faculty.h_index) in content
    
    def test_export_html_format(self, exporter, sample_primary_faculty, sample_collaborator_suggestions, sample_research_context):
        """Test HTML export format."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.HTML,
            output_filename="test_collaboration.html"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            sample_research_context,
            config
        )
        
        assert result["success"] is True
        assert result["format"] == "html"
        
        # Verify file exists and HTML structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert f"<title>Collaboration Report - {sample_primary_faculty.name}</title>" in content
            assert "stats-grid" in content
            assert "collaborator-card" in content
            assert "Dr. Michael Chen" in content
            assert "92%" in content  # High relevance score formatted as percentage
    
    def test_configuration_options(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test various configuration options."""
        # Test without contact info
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.JSON,
            include_contact_info=False,
            output_filename="test_no_contact.json"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            data = json.load(f)
            assert "export_metadata" not in data or data["export_metadata"]["sender_info"]["name"] is None
        
        # Test without match scores
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.CONTACT_SHEET,
            include_match_scores=False,
            output_filename="test_no_scores.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            # Relevance scores should not be displayed
            assert "Relevance Score:" not in content
    
    def test_export_multiple_collaborations(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test exporting multiple collaboration sets."""
        # Create a second faculty member
        faculty_2 = sample_primary_faculty.model_copy()
        faculty_2.name = "Dr. Robert Brown"
        faculty_2.email = "r.brown@university.edu"
        faculty_2.department = "Biology"
        
        collaboration_data = [
            {
                "primary_faculty": sample_primary_faculty,
                "collaborator_suggestions": sample_collaborator_suggestions[:2]
            },
            {
                "primary_faculty": faculty_2,
                "collaborator_suggestions": sample_collaborator_suggestions[2:]
            }
        ]
        
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.EMAIL_TEMPLATE,
            output_filename="test_multiple_collab.txt"
        )
        
        result = exporter.export_multiple_collaborations(collaboration_data, config)
        
        assert result["success"] is True
        assert result["total_collaboration_sets"] == 2
        assert result["successful_exports"] == 2
        assert len(result["individual_results"]) == 2
    
    def test_automatic_filename_generation(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test automatic filename generation when not provided."""
        config = CollaborationExportConfig(format=CollaborationExportFormat.JSON)
        # No output_filename specified
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        output_path = Path(result["output_path"])
        assert output_path.exists()
        assert output_path.name.startswith("collaboration_")
        assert output_path.name.endswith(".json")
        assert "Sarah_Johnson" in output_path.name  # Part of sanitized name
    
    def test_research_context_inclusion(self, exporter, sample_primary_faculty, sample_collaborator_suggestions, sample_research_context):
        """Test research context inclusion in exports."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.CSV,
            include_research_details=True,
            output_filename="test_with_research.csv"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            sample_research_context,
            config
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            assert "research_title" in content
            assert sample_research_context.title in content
            assert "research_methodology" in content
            assert str(sample_research_context.estimated_budget) in content
    
    def test_sorting_by_relevance_score(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test that collaborators are sorted by relevance score in appropriate formats."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.CONTACT_SHEET,
            output_filename="test_sorted.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            
            # Dr. Michael Chen (0.92) should appear before Dr. Emily Rodriguez (0.87)
            chen_pos = content.find("Dr. Michael Chen")
            rodriguez_pos = content.find("Dr. Emily Rodriguez")
            assert chen_pos < rodriguez_pos
    
    def test_institution_analysis(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test institution analysis in networking report."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.NETWORKING_REPORT,
            output_filename="test_institutions.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            assert "Network Diversity: 4 unique institutions" in content
            assert "Top Institutions for Collaboration:" in content
            assert "Tech Institute" in content
            assert "Medical College" in content
    
    def test_collaboration_history_handling(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test handling of collaboration history in exports."""
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.EMAIL_TEMPLATE,
            output_filename="test_collab_history.txt"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            # Should mention previous collaborations for Dr. Rodriguez (1) and Dr. Park (2)
            assert "1 previous collaboration" in content
            assert "2 previous collaboration" in content
    
    def test_error_handling(self, exporter, sample_primary_faculty, sample_collaborator_suggestions):
        """Test error handling for various scenarios."""
        # Test with empty collaborator list
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.JSON,
            output_filename="test_empty.json"
        )
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            [],  # Empty list
            config=config
        )
        
        assert result["success"] is True
        assert result["collaborators_exported"] == 0
        
        # Test with invalid output path
        original_output_dir = exporter.output_dir
        exporter.output_dir = Path("/invalid/path/that/does/not/exist")
        
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            sample_collaborator_suggestions,
            config=config
        )
        
        assert result["success"] is False
        assert "error" in result
        
        # Restore original output directory
        exporter.output_dir = original_output_dir
    
    def test_performance_with_many_collaborators(self, exporter, sample_primary_faculty):
        """Test performance with a large number of collaborators."""
        # Generate many collaborators
        many_collaborators = []
        for i in range(100):
            collab = CollaboratorSuggestion(
                faculty_profile_id=f"collab_{i:03d}",
                name=f"Dr. Collaborator {i+1}",
                institution=f"University {i % 10}",  # 10 different institutions
                relevance_score=0.5 + (i % 50) * 0.01,  # Scores from 0.5 to 0.99
                complementary_expertise=[f"expertise_{i % 5}", f"skill_{i % 3}"],
                shared_interests=[f"interest_{i % 4}"],
                email=f"collab{i}@university{i % 10}.edu"
            )
            many_collaborators.append(collab)
        
        config = CollaborationExportConfig(
            format=CollaborationExportFormat.CSV,
            output_filename="test_many_collaborators.csv"
        )
        
        import time
        start_time = time.time()
        result = exporter.export_collaboration_introductions(
            sample_primary_faculty,
            many_collaborators,
            config=config
        )
        end_time = time.time()
        
        assert result["success"] is True
        assert result["collaborators_exported"] == 100
        
        # Should complete within reasonable time (< 5 seconds for 100 collaborators)
        assert end_time - start_time < 5.0
        
        # Verify file content
        with open(result["output_path"], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 101  # Header + 100 data rows