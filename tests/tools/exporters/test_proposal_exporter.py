"""
Tests for the proposal exporter module.

This module contains comprehensive tests for the proposal exporter,
including export format validation, file generation, and content verification.
"""

import json
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from decimal import Decimal

from src.tools.exporters.proposal_exporter import (
    ProposalExporter,
    ProposalExportConfig,
    ProposalExportFormat
)
from src.core.models import (
    ResearchIdea,
    FacultyFundingMatch,
    MatchScore,
    ProposalVariant,
    ResearchMethodology,
    CareerStage,
    MatchStatus
)


class TestProposalExporter:
    """Test cases for the ProposalExporter class."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def exporter(self, temp_output_dir):
        """Create a ProposalExporter instance with temporary output directory."""
        return ProposalExporter(output_dir=temp_output_dir)
    
    @pytest.fixture
    def sample_research_idea(self):
        """Create a sample research idea for testing."""
        return ResearchIdea(
            title="AI-Driven Healthcare Analytics Platform",
            variant_type=ProposalVariant.INNOVATIVE,
            research_question="How can machine learning algorithms improve early disease detection in primary care settings?",
            hypothesis="ML-based pattern recognition can identify disease markers 30% earlier than traditional methods",
            methodology=[ResearchMethodology.COMPUTATIONAL, ResearchMethodology.EXPERIMENTAL],
            objectives=[
                "Develop ML algorithms for pattern recognition in medical data",
                "Validate algorithms using retrospective patient data",
                "Conduct prospective clinical trials",
                "Assess cost-effectiveness and clinical impact"
            ],
            timeline_months=36,
            milestones=[
                "Algorithm development and initial testing (Months 1-12)",
                "Retrospective validation study (Months 13-24)",
                "Prospective clinical trial (Months 25-36)"
            ],
            deliverables=[
                "ML algorithm software package",
                "Clinical validation report",
                "Peer-reviewed publications",
                "Clinical implementation guidelines"
            ],
            estimated_budget=Decimal("750000.00"),
            budget_breakdown={
                "personnel": Decimal("450000.00"),
                "equipment": Decimal("150000.00"),
                "supplies": Decimal("75000.00"),
                "travel": Decimal("25000.00"),
                "indirect": Decimal("50000.00")
            },
            innovation_level=0.85,
            feasibility_score=0.78,
            impact_potential=0.92,
            key_references=[
                "Smith et al. (2023). Advanced ML in Healthcare. Nature Medicine.",
                "Jones et al. (2022). Early Disease Detection Systems. JAMA.",
                "Brown et al. (2023). Clinical AI Implementation. NEJM."
            ],
            literature_gap="Limited research on integrating multiple ML approaches for early detection",
            generated_date=datetime.now(),
            llm_model="gpt-4-turbo"
        )
    
    @pytest.fixture
    def sample_faculty_match(self):
        """Create a sample faculty-funding match for testing."""
        match_score = MatchScore(
            total_score=0.89,
            research_alignment=0.92,
            methodology_match=0.85,
            career_stage_fit=0.88,
            deadline_urgency=0.75,
            budget_alignment=0.95,
            scoring_algorithm="multi_dimensional_v1"
        )
        
        return FacultyFundingMatch(
            match_id="match_test_001",
            faculty_profile_id="prof_001",
            funding_opportunity_id="nih_r01_001",
            match_score=match_score,
            status=MatchStatus.PENDING,
            created_date=datetime.now()
        )
    
    def test_export_json_format(self, exporter, sample_research_idea, sample_faculty_match):
        """Test JSON export format."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.JSON,
            output_filename="test_proposal.json"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        assert result["format"] == "json"
        assert "output_path" in result
        
        # Verify file exists and content
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert "research_proposal" in data
        assert "match_information" in data
        assert "export_metadata" in data
        assert data["research_proposal"]["title"] == sample_research_idea.title
        assert data["match_information"]["match_id"] == sample_faculty_match.match_id
    
    def test_export_csv_format(self, exporter, sample_research_idea, sample_faculty_match):
        """Test CSV export format."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.CSV,
            output_filename="test_proposal.csv"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        assert result["format"] == "csv"
        
        # Verify file exists and basic structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "proposal_title" in content
            assert sample_research_idea.title in content
            assert str(sample_research_idea.estimated_budget) in content
    
    def test_export_markdown_format(self, exporter, sample_research_idea, sample_faculty_match):
        """Test Markdown export format."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.MARKDOWN,
            output_filename="test_proposal.md"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        assert result["format"] == "markdown"
        
        # Verify file exists and markdown structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert f"# {sample_research_idea.title}" in content
            assert "## Research Question" in content
            assert "## Methodology" in content
            assert "## Budget" in content
            assert sample_research_idea.research_question in content
    
    def test_export_html_format(self, exporter, sample_research_idea, sample_faculty_match):
        """Test HTML export format."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.HTML,
            output_filename="test_proposal.html"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        assert result["format"] == "html"
        
        # Verify file exists and HTML structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert f"<title>{sample_research_idea.title}</title>" in content
            assert sample_research_idea.research_question in content
            assert "budget-table" in content or str(sample_research_idea.estimated_budget) in content
    
    def test_export_latex_format(self, exporter, sample_research_idea, sample_faculty_match):
        """Test LaTeX export format."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.LATEX,
            output_filename="test_proposal.tex"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        assert result["format"] == "latex"
        
        # Verify file exists and LaTeX structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "\\documentclass" in content
            assert "\\begin{document}" in content
            assert "\\end{document}" in content
            assert sample_research_idea.title in content
    
    def test_export_plain_text_format(self, exporter, sample_research_idea, sample_faculty_match):
        """Test plain text export format."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.PLAIN_TEXT,
            output_filename="test_proposal.txt"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        assert result["format"] == "plain_text"
        
        # Verify file exists and text structure
        output_path = Path(result["output_path"])
        assert output_path.exists()
        
        with open(output_path, 'r') as f:
            content = f.read()
            assert "RESEARCH PROPOSAL:" in content
            assert "RESEARCH QUESTION" in content
            assert "METHODOLOGY" in content
            assert sample_research_idea.title.upper() in content
    
    def test_export_configuration_options(self, exporter, sample_research_idea, sample_faculty_match):
        """Test various export configuration options."""
        # Test without metadata
        config = ProposalExportConfig(
            format=ProposalExportFormat.JSON,
            include_metadata=False,
            output_filename="test_no_metadata.json"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            data = json.load(f)
            assert "export_metadata" not in data
        
        # Test without budget breakdown
        config = ProposalExportConfig(
            format=ProposalExportFormat.MARKDOWN,
            include_budget_breakdown=False,
            output_filename="test_no_budget.md"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        assert result["success"] is True
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
            # Should still have total budget but not breakdown table
            assert str(sample_research_idea.estimated_budget) in content
    
    def test_export_multiple_proposals(self, exporter, sample_research_idea, sample_faculty_match):
        """Test exporting multiple proposals."""
        # Create additional test data
        research_idea_2 = sample_research_idea.model_copy()
        research_idea_2.title = "Blockchain-Based Supply Chain Management"
        research_idea_2.variant_type = ProposalVariant.CONSERVATIVE
        
        faculty_match_2 = sample_faculty_match.model_copy()
        faculty_match_2.match_id = "match_test_002"
        
        proposals_data = [
            {"research_idea": sample_research_idea, "faculty_match": sample_faculty_match},
            {"research_idea": research_idea_2, "faculty_match": faculty_match_2}
        ]
        
        config = ProposalExportConfig(
            format=ProposalExportFormat.CSV,
            output_filename="test_multiple.csv"
        )
        
        result = exporter.export_multiple_proposals(proposals_data, config)
        
        assert result["success"] is True
        assert result["proposals_exported"] == 2
        
        # Verify CSV content
        with open(result["output_path"], 'r') as f:
            content = f.read()
            assert sample_research_idea.title in content
            assert research_idea_2.title in content
    
    def test_export_multiple_json(self, exporter, sample_research_idea, sample_faculty_match):
        """Test exporting multiple proposals as JSON."""
        research_idea_2 = sample_research_idea.model_copy()
        research_idea_2.title = "Quantum Computing Applications"
        
        faculty_match_2 = sample_faculty_match.model_copy()
        faculty_match_2.match_id = "match_test_003"
        
        proposals_data = [
            {"research_idea": sample_research_idea, "faculty_match": sample_faculty_match},
            {"research_idea": research_idea_2, "faculty_match": faculty_match_2}
        ]
        
        config = ProposalExportConfig(
            format=ProposalExportFormat.JSON,
            output_filename="test_multiple.json"
        )
        
        result = exporter.export_multiple_proposals(proposals_data, config)
        
        assert result["success"] is True
        assert result["proposals_exported"] == 2
        
        # Verify JSON structure
        with open(result["output_path"], 'r') as f:
            data = json.load(f)
            assert "proposals" in data
            assert "summary" in data
            assert len(data["proposals"]) == 2
            assert data["summary"]["total_proposals"] == 2
    
    def test_automatic_filename_generation(self, exporter, sample_research_idea, sample_faculty_match):
        """Test automatic filename generation when not provided."""
        config = ProposalExportConfig(format=ProposalExportFormat.JSON)
        # No output_filename specified
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is True
        output_path = Path(result["output_path"])
        assert output_path.exists()
        assert output_path.name.startswith("proposal_")
        assert output_path.name.endswith(".json")
        assert "AI_Driven_Healthcare" in output_path.name  # Part of sanitized title
    
    def test_budget_breakdown_handling(self, exporter, sample_faculty_match):
        """Test handling of proposals with and without budget breakdown."""
        # Research idea without budget breakdown
        research_idea_no_budget = ResearchIdea(
            title="Simple Research Project",
            variant_type=ProposalVariant.CONSERVATIVE,
            research_question="What is the effect of X on Y?",
            methodology=[ResearchMethodology.EXPERIMENTAL],
            objectives=["Investigate X", "Measure Y"],
            timeline_months=12,
            estimated_budget=Decimal("100000.00"),
            innovation_level=0.6,
            feasibility_score=0.9,
            impact_potential=0.7
        )
        
        config = ProposalExportConfig(
            format=ProposalExportFormat.HTML,
            include_budget_breakdown=True,
            output_filename="test_no_breakdown.html"
        )
        
        result = exporter.export_proposal(research_idea_no_budget, sample_faculty_match, config)
        
        assert result["success"] is True
        
        # Should still work without budget breakdown
        with open(result["output_path"], 'r') as f:
            content = f.read()
            assert str(research_idea_no_budget.estimated_budget) in content
    
    def test_error_handling(self, exporter, sample_research_idea, sample_faculty_match):
        """Test error handling for invalid configurations."""
        # Test with invalid format (this should be caught by Pydantic validation)
        with pytest.raises(ValueError):
            ProposalExportConfig(format="invalid_format")
        
        # Test export with read-only directory (simulate permission error)
        config = ProposalExportConfig(
            format=ProposalExportFormat.JSON,
            output_filename="test.json"
        )
        
        # Mock a file write error by using an invalid path
        original_output_dir = exporter.output_dir
        exporter.output_dir = Path("/invalid/path/that/does/not/exist")
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        assert result["success"] is False
        assert "error" in result
        
        # Restore original output directory
        exporter.output_dir = original_output_dir
    
    def test_content_accuracy_markdown(self, exporter, sample_research_idea, sample_faculty_match):
        """Test content accuracy in markdown export."""
        config = ProposalExportConfig(
            format=ProposalExportFormat.MARKDOWN,
            output_filename="test_content.md"
        )
        
        result = exporter.export_proposal(sample_research_idea, sample_faculty_match, config)
        
        with open(result["output_path"], 'r') as f:
            content = f.read()
        
        # Verify all key elements are present
        assert sample_research_idea.title in content
        assert sample_research_idea.research_question in content
        assert sample_research_idea.hypothesis in content
        
        # Check methodology items
        for method in sample_research_idea.methodology:
            assert method.value.replace('_', ' ').title() in content
        
        # Check objectives
        for objective in sample_research_idea.objectives:
            assert objective in content
        
        # Check budget breakdown
        for category, amount in sample_research_idea.budget_breakdown.items():
            assert category.title() in content
            assert f"${float(amount):,.2f}" in content
        
        # Check references
        for ref in sample_research_idea.key_references:
            assert ref in content
        
        # Check metrics
        assert f"{sample_research_idea.innovation_level:.2f}" in content
        assert f"{sample_research_idea.feasibility_score:.2f}" in content
        assert f"{sample_research_idea.impact_potential:.2f}" in content
    
    def test_large_dataset_performance(self, exporter):
        """Test performance with a larger number of proposals."""
        # Create multiple research ideas and matches
        proposals_data = []
        
        for i in range(50):  # Test with 50 proposals
            research_idea = ResearchIdea(
                title=f"Research Project {i+1}",
                variant_type=ProposalVariant.INNOVATIVE,
                research_question=f"Research question for project {i+1}",
                methodology=[ResearchMethodology.COMPUTATIONAL],
                objectives=[f"Objective 1 for project {i+1}", f"Objective 2 for project {i+1}"],
                timeline_months=12 + (i % 24),
                estimated_budget=Decimal(str(100000 + i * 10000)),
                innovation_level=0.5 + (i % 5) * 0.1,
                feasibility_score=0.6 + (i % 4) * 0.1,
                impact_potential=0.7 + (i % 3) * 0.1
            )
            
            match_score = MatchScore(
                total_score=0.7 + (i % 3) * 0.1,
                research_alignment=0.8,
                methodology_match=0.7,
                career_stage_fit=0.8,
                deadline_urgency=0.6,
                budget_alignment=0.8,
                scoring_algorithm="test_algorithm"
            )
            
            faculty_match = FacultyFundingMatch(
                match_id=f"match_{i:03d}",
                faculty_profile_id=f"prof_{i:03d}",
                funding_opportunity_id=f"funding_{i:03d}",
                match_score=match_score,
                status=MatchStatus.PENDING
            )
            
            proposals_data.append({
                "research_idea": research_idea,
                "faculty_match": faculty_match
            })
        
        config = ProposalExportConfig(
            format=ProposalExportFormat.CSV,
            output_filename="test_large_dataset.csv"
        )
        
        import time
        start_time = time.time()
        result = exporter.export_multiple_proposals(proposals_data, config)
        end_time = time.time()
        
        assert result["success"] is True
        assert result["proposals_exported"] == 50
        
        # Should complete within reasonable time (< 10 seconds for 50 proposals)
        assert end_time - start_time < 10.0
        
        # Verify file content
        with open(result["output_path"], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 51  # Header + 50 data rows