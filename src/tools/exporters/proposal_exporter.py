"""
Proposal Exporter for the Faculty Research Opportunity Notifier.

This module provides functionality to export research proposals and ideas
in multiple formats including PDF, Word documents, LaTeX templates, and more.
"""

import logging
import json
import csv
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from io import StringIO, BytesIO
from decimal import Decimal

from pydantic import BaseModel, Field

from ...core.models import ResearchIdea, FacultyFundingMatch, FacultyProfile, FundingOpportunity

logger = logging.getLogger(__name__)


class ProposalExportFormat(str, Enum):
    """Supported export formats for proposals."""
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"
    LATEX = "latex"
    PLAIN_TEXT = "plain_text"


class ProposalExportConfig(BaseModel):
    """Configuration for proposal export."""
    format: ProposalExportFormat
    include_metadata: bool = Field(default=True, description="Include system metadata")
    include_budget_breakdown: bool = Field(default=True, description="Include detailed budget breakdown")
    include_timeline: bool = Field(default=True, description="Include project timeline")
    include_references: bool = Field(default=True, description="Include literature references")
    template_path: Optional[str] = Field(None, description="Path to custom template file")
    output_filename: Optional[str] = Field(None, description="Custom output filename")


class ProposalExporter:
    """
    Exporter for research proposals and ideas in multiple formats.
    """
    
    def __init__(self, output_dir: str = "exports/proposals"):
        """
        Initialize the proposal exporter.
        
        Args:
            output_dir: Directory to save exported files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_proposal(
        self,
        research_idea: ResearchIdea,
        faculty_match: FacultyFundingMatch,
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """
        Export a single research proposal.
        
        Args:
            research_idea: Research idea to export
            faculty_match: Associated faculty-funding match
            config: Export configuration
            
        Returns:
            Dict containing export result information
        """
        try:
            # Generate filename if not provided
            if not config.output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_title = "".join(c for c in research_idea.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_')[:50]
                config.output_filename = f"proposal_{safe_title}_{timestamp}.{config.format.value}"
            
            # Export based on format
            if config.format == ProposalExportFormat.JSON:
                return self._export_json(research_idea, faculty_match, config)
            elif config.format == ProposalExportFormat.CSV:
                return self._export_csv([research_idea], [faculty_match], config)
            elif config.format == ProposalExportFormat.MARKDOWN:
                return self._export_markdown(research_idea, faculty_match, config)
            elif config.format == ProposalExportFormat.HTML:
                return self._export_html(research_idea, faculty_match, config)
            elif config.format == ProposalExportFormat.LATEX:
                return self._export_latex(research_idea, faculty_match, config)
            elif config.format == ProposalExportFormat.PLAIN_TEXT:
                return self._export_plain_text(research_idea, faculty_match, config)
            else:
                raise ValueError(f"Unsupported export format: {config.format}")
                
        except Exception as e:
            logger.error(f"Failed to export proposal: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def export_multiple_proposals(
        self,
        proposals_data: List[Dict[str, Any]],
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """
        Export multiple research proposals.
        
        Args:
            proposals_data: List of proposal data containing research_idea and faculty_match
            config: Export configuration
            
        Returns:
            Dict containing export result information
        """
        try:
            research_ideas = []
            faculty_matches = []
            
            for proposal in proposals_data:
                research_ideas.append(proposal["research_idea"])  
                faculty_matches.append(proposal["faculty_match"])
            
            # Generate filename if not provided
            if not config.output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                config.output_filename = f"proposals_batch_{timestamp}.{config.format.value}"
            
            # Export based on format
            if config.format == ProposalExportFormat.CSV:
                return self._export_csv(research_ideas, faculty_matches, config)
            elif config.format == ProposalExportFormat.JSON:
                return self._export_multiple_json(research_ideas, faculty_matches, config)
            else:
                # For other formats, create individual files
                return self._export_multiple_individual(proposals_data, config)
                
        except Exception as e:
            logger.error(f"Failed to export multiple proposals: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _export_json(
        self,
        research_idea: ResearchIdea,
        faculty_match: FacultyFundingMatch,
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export proposal as JSON."""
        
        # Build export data
        export_data = {
            "research_proposal": research_idea.model_dump(),
            "match_information": {
                "match_id": faculty_match.match_id,
                "match_score": faculty_match.match_score.model_dump(),
                "faculty_profile_id": faculty_match.faculty_profile_id,
                "funding_opportunity_id": faculty_match.funding_opportunity_id
            }
        }
        
        if config.include_metadata:
            export_data["export_metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "export_format": config.format.value,
                "exporter_version": "1.0.0"
            }
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_csv(
        self,
        research_ideas: List[ResearchIdea],
        faculty_matches: List[FacultyFundingMatch],
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export proposals as CSV."""
        
        output_path = self.output_dir / config.output_filename
        
        # Define CSV fields
        fieldnames = [
            'proposal_title', 'variant_type', 'research_question', 'methodology',
            'timeline_months', 'estimated_budget', 'innovation_level', 'feasibility_score',
            'impact_potential', 'match_id', 'match_score', 'faculty_profile_id',
            'funding_opportunity_id'
        ]
        
        if config.include_budget_breakdown:
            fieldnames.extend(['budget_personnel', 'budget_equipment', 'budget_supplies', 'budget_travel'])
        
        if config.include_metadata:
            fieldnames.extend(['generated_date', 'llm_model', 'created_date'])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for idea, match in zip(research_ideas, faculty_matches):
                row = {
                    'proposal_title': idea.title,
                    'variant_type': idea.variant_type.value,
                    'research_question': idea.research_question,
                    'methodology': ', '.join([m.value for m in idea.methodology]),
                    'timeline_months': idea.timeline_months,
                    'estimated_budget': float(idea.estimated_budget),
                    'innovation_level': idea.innovation_level,
                    'feasibility_score': idea.feasibility_score,
                    'impact_potential': idea.impact_potential,
                    'match_id': match.match_id,
                    'match_score': match.match_score.total_score,
                    'faculty_profile_id': match.faculty_profile_id,
                    'funding_opportunity_id': match.funding_opportunity_id
                }
                
                if config.include_budget_breakdown and idea.budget_breakdown:
                    row.update({
                        'budget_personnel': idea.budget_breakdown.get('personnel', 0),
                        'budget_equipment': idea.budget_breakdown.get('equipment', 0),
                        'budget_supplies': idea.budget_breakdown.get('supplies', 0),
                        'budget_travel': idea.budget_breakdown.get('travel', 0)
                    })
                
                if config.include_metadata:
                    row.update({
                        'generated_date': idea.generated_date.isoformat(),
                        'llm_model': idea.llm_model or 'unknown',
                        'created_date': match.created_date.isoformat()
                    })
                
                writer.writerow(row)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "rows_exported": len(research_ideas),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_markdown(
        self,
        research_idea: ResearchIdea,
        faculty_match: FacultyFundingMatch,
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export proposal as Markdown."""
        
        # Build markdown content
        md_content = []
        
        # Title and metadata
        md_content.append(f"# {research_idea.title}")
        md_content.append(f"**Proposal Type:** {research_idea.variant_type.value.title()}")
        md_content.append(f"**Match Score:** {faculty_match.match_score.total_score:.3f}")
        md_content.append("")
        
        # Research question and hypothesis
        md_content.append("## Research Question")
        md_content.append(research_idea.research_question)
        md_content.append("")
        
        if research_idea.hypothesis:
            md_content.append("## Hypothesis")
            md_content.append(research_idea.hypothesis)
            md_content.append("")
        
        # Methodology
        md_content.append("## Methodology")
        for method in research_idea.methodology:
            md_content.append(f"- {method.value.replace('_', ' ').title()}")
        md_content.append("")
        
        # Objectives
        md_content.append("## Research Objectives")
        for i, objective in enumerate(research_idea.objectives, 1):
            md_content.append(f"{i}. {objective}")
        md_content.append("")
        
        # Timeline and milestones
        if config.include_timeline:
            md_content.append("## Project Timeline")
            md_content.append(f"**Duration:** {research_idea.timeline_months} months")
            md_content.append("")
            
            if research_idea.milestones:
                md_content.append("### Key Milestones")
                for milestone in research_idea.milestones:
                    md_content.append(f"- {milestone}")
                md_content.append("")
        
        # Budget
        if config.include_budget_breakdown:
            md_content.append("## Budget")
            md_content.append(f"**Total Estimated Budget:** ${research_idea.estimated_budget:,.2f}")
            md_content.append("")
            
            if research_idea.budget_breakdown:
                md_content.append("### Budget Breakdown")
                for category, amount in research_idea.budget_breakdown.items():
                    md_content.append(f"- **{category.title()}:** ${float(amount):,.2f}")
                md_content.append("")
        
        # Innovation and impact metrics
        md_content.append("## Project Metrics")
        md_content.append(f"- **Innovation Level:** {research_idea.innovation_level:.2f}/1.0")
        md_content.append(f"- **Feasibility Score:** {research_idea.feasibility_score:.2f}/1.0")
        md_content.append(f"- **Impact Potential:** {research_idea.impact_potential:.2f}/1.0")
        md_content.append("")
        
        # Deliverables
        if research_idea.deliverables:
            md_content.append("## Expected Deliverables")
            for deliverable in research_idea.deliverables:
                md_content.append(f"- {deliverable}")
            md_content.append("")
        
        # References
        if config.include_references and research_idea.key_references:
            md_content.append("## Key References")
            for ref in research_idea.key_references:
                md_content.append(f"- {ref}")
            md_content.append("")
        
        # Literature gap
        if research_idea.literature_gap:
            md_content.append("## Literature Gap")
            md_content.append(research_idea.literature_gap)
            md_content.append("")
        
        # Export metadata
        if config.include_metadata:
            md_content.append("---")
            md_content.append("## Export Information")
            md_content.append(f"- **Generated:** {research_idea.generated_date.strftime('%Y-%m-%d %H:%M:%S')}")
            md_content.append(f"- **Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            md_content.append(f"- **Match ID:** {faculty_match.match_id}")
            md_content.append(f"- **LLM Model:** {research_idea.llm_model or 'Unknown'}")
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_content))
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_html(
        self,
        research_idea: ResearchIdea,
        faculty_match: FacultyFundingMatch,
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export proposal as HTML."""
        
        # HTML template
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{research_idea.title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .header {{
            border-bottom: 2px solid #0066cc;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #0066cc;
            margin-bottom: 10px;
        }}
        .metadata {{
            background: #f0f8ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .budget-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        .budget-table th, .budget-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        .budget-table th {{
            background-color: #f2f2f2;
        }}
        .metrics {{
            display: flex;
            justify-content: space-around;
            background: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
        }}
        .metric {{
            text-align: center;
        }}
        .metric-value {{
            font-size: 1.2em;
            font-weight: bold;
            color: #0066cc;
        }}
        ul li {{
            margin-bottom: 5px;
        }}
        .footer {{
            border-top: 1px solid #ccc;
            padding-top: 15px;
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{research_idea.title}</h1>
        <div class="metadata">
            <strong>Proposal Type:</strong> {research_idea.variant_type.value.title()} |
            <strong>Match Score:</strong> {faculty_match.match_score.total_score:.3f} |
            <strong>Duration:</strong> {research_idea.timeline_months} months
        </div>
    </div>
    
    <div class="section">
        <h2>Research Question</h2>
        <p>{research_idea.research_question}</p>
    </div>
    
    {f'<div class="section"><h2>Hypothesis</h2><p>{research_idea.hypothesis}</p></div>' if research_idea.hypothesis else ''}
    
    <div class="section">
        <h2>Methodology</h2>
        <ul>
            {''.join([f"<li>{method.value.replace('_', ' ').title()}</li>" for method in research_idea.methodology])}
        </ul>
    </div>
    
    <div class="section">
        <h2>Research Objectives</h2>
        <ol>
            {''.join([f"<li>{obj}</li>" for obj in research_idea.objectives])}
        </ol>
    </div>
    
    <div class="section">
        <h2>Project Metrics</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{research_idea.innovation_level:.2f}</div>
                <div>Innovation Level</div>
            </div>
            <div class="metric">
                <div class="metric-value">{research_idea.feasibility_score:.2f}</div>
                <div>Feasibility Score</div>
            </div>
            <div class="metric">
                <div class="metric-value">{research_idea.impact_potential:.2f}</div>
                <div>Impact Potential</div>
            </div>
        </div>
    </div>
"""
        
        # Add budget section if requested
        if config.include_budget_breakdown:
            html_content += f"""
    <div class="section">
        <h2>Budget</h2>
        <p><strong>Total Estimated Budget:</strong> ${research_idea.estimated_budget:,.2f}</p>
"""
            if research_idea.budget_breakdown:
                html_content += """
        <table class="budget-table">
            <thead>
                <tr><th>Category</th><th>Amount</th></tr>
            </thead>
            <tbody>
"""
                for category, amount in research_idea.budget_breakdown.items():
                    html_content += f"                <tr><td>{category.title()}</td><td>${float(amount):,.2f}</td></tr>\n"
                html_content += "            </tbody>\n        </table>"
            html_content += "    </div>\n"
        
        # Add deliverables if available
        if research_idea.deliverables:
            html_content += """
    <div class="section">
        <h2>Expected Deliverables</h2>
        <ul>
"""
            for deliverable in research_idea.deliverables:
                html_content += f"            <li>{deliverable}</li>\n"
            html_content += "        </ul>\n    </div>\n"
        
        # Add references if requested
        if config.include_references and research_idea.key_references:
            html_content += """
    <div class="section">
        <h2>Key References</h2>
        <ul>
"""
            for ref in research_idea.key_references:
                html_content += f"            <li>{ref}</li>\n"
            html_content += "        </ul>\n    </div>\n"
        
        # Add footer with metadata
        if config.include_metadata:
            html_content += f"""
    <div class="footer">
        <p><strong>Generated:</strong> {research_idea.generated_date.strftime('%Y-%m-%d %H:%M:%S')} | 
        <strong>Exported:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
        <strong>Match ID:</strong> {faculty_match.match_id}</p>
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_latex(
        self,
        research_idea: ResearchIdea,
        faculty_match: FacultyFundingMatch,
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export proposal as LaTeX."""
        
        # LaTeX content
        latex_content = f"""\\documentclass[12pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{hyperref}}
\\usepackage{{booktabs}}
\\usepackage{{array}}

\\title{{{research_idea.title}}}
\\author{{Faculty Research Opportunity Notifier}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

\\section{{Proposal Overview}}
\\textbf{{Proposal Type:}} {research_idea.variant_type.value.title()} \\\\
\\textbf{{Match Score:}} {faculty_match.match_score.total_score:.3f} \\\\
\\textbf{{Duration:}} {research_idea.timeline_months} months \\\\
\\textbf{{Estimated Budget:}} \\${research_idea.estimated_budget:,.2f}

\\section{{Research Question}}
{research_idea.research_question}

"""
        
        if research_idea.hypothesis:
            latex_content += f"""\\section{{Hypothesis}}
{research_idea.hypothesis}

"""
        
        # Methodology
        latex_content += """\\section{Methodology}
\\begin{itemize}
"""
        for method in research_idea.methodology:
            latex_content += f"    \\item {method.value.replace('_', ' ').title()}\n"
        latex_content += "\\end{itemize}\n\n"
        
        # Objectives
        latex_content += """\\section{Research Objectives}
\\begin{enumerate}
"""
        for objective in research_idea.objectives:
            latex_content += f"    \\item {objective}\n"
        latex_content += "\\end{enumerate}\n\n"
        
        # Budget breakdown
        if config.include_budget_breakdown and research_idea.budget_breakdown:
            latex_content += """\\section{Budget Breakdown}
\\begin{table}[h]
\\centering
\\begin{tabular}{lr}
\\toprule
Category & Amount \\\\
\\midrule
"""
            for category, amount in research_idea.budget_breakdown.items():
                latex_content += f"{category.title()} & \\${float(amount):,.2f} \\\\\n"
            latex_content += f"""\\midrule
\\textbf{{Total}} & \\textbf{{\\${research_idea.estimated_budget:,.2f}}} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}

"""
        
        # Metrics
        latex_content += f"""\\section{{Project Metrics}}
\\begin{{itemize}}
    \\item \\textbf{{Innovation Level:}} {research_idea.innovation_level:.2f}/1.0
    \\item \\textbf{{Feasibility Score:}} {research_idea.feasibility_score:.2f}/1.0
    \\item \\textbf{{Impact Potential:}} {research_idea.impact_potential:.2f}/1.0
\\end{{itemize}}

"""
        
        # Deliverables
        if research_idea.deliverables:
            latex_content += """\\section{Expected Deliverables}
\\begin{itemize}
"""
            for deliverable in research_idea.deliverables:
                latex_content += f"    \\item {deliverable}\n"
            latex_content += "\\end{itemize}\n\n"
        
        # References
        if config.include_references and research_idea.key_references:
            latex_content += """\\section{Key References}
\\begin{itemize}
"""
            for ref in research_idea.key_references:
                latex_content += f"    \\item {ref}\n"
            latex_content += "\\end{itemize}\n\n"
        
        latex_content += "\\end{document}"
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_plain_text(
        self,
        research_idea: ResearchIdea,
        faculty_match: FacultyFundingMatch,
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export proposal as plain text."""
        
        lines = []
        
        # Header
        lines.append("="*80)
        lines.append(f"RESEARCH PROPOSAL: {research_idea.title.upper()}")
        lines.append("="*80)
        lines.append("")
        
        # Metadata
        lines.append(f"Proposal Type: {research_idea.variant_type.value.title()}")
        lines.append(f"Match Score: {faculty_match.match_score.total_score:.3f}")
        lines.append(f"Duration: {research_idea.timeline_months} months")
        lines.append(f"Estimated Budget: ${research_idea.estimated_budget:,.2f}")
        lines.append("")
        
        # Research question
        lines.append("RESEARCH QUESTION")
        lines.append("-"*40)
        lines.append(research_idea.research_question)
        lines.append("")
        
        # Hypothesis
        if research_idea.hypothesis:
            lines.append("HYPOTHESIS")
            lines.append("-"*40)
            lines.append(research_idea.hypothesis)
            lines.append("")
        
        # Methodology
        lines.append("METHODOLOGY")
        lines.append("-"*40)
        for method in research_idea.methodology:
            lines.append(f"• {method.value.replace('_', ' ').title()}")
        lines.append("")
        
        # Objectives
        lines.append("RESEARCH OBJECTIVES")
        lines.append("-"*40)
        for i, objective in enumerate(research_idea.objectives, 1):
            lines.append(f"{i}. {objective}")
        lines.append("")
        
        # Budget breakdown
        if config.include_budget_breakdown and research_idea.budget_breakdown:
            lines.append("BUDGET BREAKDOWN")
            lines.append("-"*40)
            for category, amount in research_idea.budget_breakdown.items():
                lines.append(f"{category.title():<20} ${float(amount):>10,.2f}")
            lines.append("-"*40)
            lines.append(f"{'TOTAL':<20} ${research_idea.estimated_budget:>10,.2f}")
            lines.append("")
        
        # Metrics
        lines.append("PROJECT METRICS")
        lines.append("-"*40)
        lines.append(f"Innovation Level:    {research_idea.innovation_level:.2f}/1.0")
        lines.append(f"Feasibility Score:   {research_idea.feasibility_score:.2f}/1.0")
        lines.append(f"Impact Potential:    {research_idea.impact_potential:.2f}/1.0")
        lines.append("")
        
        # Deliverables
        if research_idea.deliverables:
            lines.append("EXPECTED DELIVERABLES")
            lines.append("-"*40)
            for deliverable in research_idea.deliverables:
                lines.append(f"• {deliverable}")
            lines.append("")
        
        # References
        if config.include_references and research_idea.key_references:
            lines.append("KEY REFERENCES")
            lines.append("-"*40)
            for ref in research_idea.key_references:
                lines.append(f"• {ref}")
            lines.append("")
        
        # Footer
        if config.include_metadata:
            lines.append("="*80)
            lines.append("EXPORT INFORMATION")
            lines.append("="*80)
            lines.append(f"Generated: {research_idea.generated_date.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Exported:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Match ID:  {faculty_match.match_id}")
            lines.append(f"LLM Model: {research_idea.llm_model or 'Unknown'}")
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_multiple_json(
        self,
        research_ideas: List[ResearchIdea],
        faculty_matches: List[FacultyFundingMatch],
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export multiple proposals as a single JSON file."""
        
        export_data = {
            "proposals": [],
            "summary": {
                "total_proposals": len(research_ideas),
                "export_date": datetime.now().isoformat(),
                "export_format": config.format.value
            }
        }
        
        for idea, match in zip(research_ideas, faculty_matches):
            proposal_data = {
                "research_proposal": idea.model_dump(),
                "match_information": {
                    "match_id": match.match_id,
                    "match_score": match.match_score.model_dump(),
                    "faculty_profile_id": match.faculty_profile_id,
                    "funding_opportunity_id": match.funding_opportunity_id
                }
            }
            export_data["proposals"].append(proposal_data)
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "proposals_exported": len(research_ideas),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_multiple_individual(
        self,
        proposals_data: List[Dict[str, Any]],
        config: ProposalExportConfig
    ) -> Dict[str, Any]:
        """Export multiple proposals as individual files."""
        
        results = []
        base_filename = config.output_filename.rsplit('.', 1)[0]
        file_extension = config.output_filename.rsplit('.', 1)[1]
        
        for i, proposal in enumerate(proposals_data):
            # Create individual config
            individual_config = config.model_copy()
            individual_config.output_filename = f"{base_filename}_{i+1:03d}.{file_extension}"
            
            # Export individual proposal
            result = self.export_proposal(
                proposal["research_idea"],
                proposal["faculty_match"], 
                individual_config
            )
            results.append(result)
        
        # Return summary
        successful_exports = [r for r in results if r.get("success", False)]
        
        return {
            "success": len(successful_exports) > 0,
            "total_proposals": len(proposals_data),
            "successful_exports": len(successful_exports),
            "failed_exports": len(proposals_data) - len(successful_exports),
            "individual_results": results,
            "timestamp": datetime.now().isoformat()
        }