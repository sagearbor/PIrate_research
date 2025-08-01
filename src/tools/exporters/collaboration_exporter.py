"""
Collaboration Exporter for the Faculty Research Opportunity Notifier.

This module provides functionality to export collaboration introductions
and contact information in multiple formats including email templates,
contact sheets, and networking reports.
"""

import logging
import json
import csv
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
from io import StringIO

from pydantic import BaseModel, Field

from ...core.models import CollaboratorSuggestion, FacultyProfile, FacultyFundingMatch, ResearchIdea

logger = logging.getLogger(__name__)


class CollaborationExportFormat(str, Enum):
    """Supported export formats for collaboration data."""
    JSON = "json"
    CSV = "csv"
    EMAIL_TEMPLATE = "email_template"
    CONTACT_SHEET = "contact_sheet"
    NETWORKING_REPORT = "networking_report"
    HTML = "html"


class CollaborationExportConfig(BaseModel):
    """Configuration for collaboration export."""
    format: CollaborationExportFormat
    include_contact_info: bool = Field(default=True, description="Include contact information")
    include_research_details: bool = Field(default=True, description="Include detailed research information")
    include_match_scores: bool = Field(default=True, description="Include relevance scores")
    email_tone: str = Field(default="professional", description="Email tone: professional, casual, formal")
    template_path: Optional[str] = Field(None, description="Path to custom template file")
    output_filename: Optional[str] = Field(None, description="Custom output filename")
    sender_name: Optional[str] = Field(None, description="Name of the person sending introductions")
    sender_email: Optional[str] = Field(None, description="Email of the person sending introductions")
    sender_institution: Optional[str] = Field(None, description="Institution of the sender")


class CollaborationExporter:
    """
    Exporter for collaboration introductions and networking information.
    """
    
    def __init__(self, output_dir: str = "exports/collaborations"):
        """
        Initialize the collaboration exporter.
        
        Args:
            output_dir: Directory to save exported files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def export_collaboration_introductions(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea] = None,
        config: CollaborationExportConfig = None
    ) -> Dict[str, Any]:
        """
        Export collaboration introductions for a faculty member.
        
        Args:
            primary_faculty: Primary faculty member seeking collaborations
            collaborator_suggestions: List of suggested collaborators
            research_context: Optional research context for the collaboration
            config: Export configuration
            
        Returns:
            Dict containing export result information
        """
        if config is None:
            config = CollaborationExportConfig(format=CollaborationExportFormat.EMAIL_TEMPLATE)
        
        try:
            # Generate filename if not provided
            if not config.output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in primary_faculty.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_')[:30]
                config.output_filename = f"collaboration_{safe_name}_{timestamp}.{config.format.value}"
            
            # Export based on format
            if config.format == CollaborationExportFormat.JSON:
                return self._export_json(primary_faculty, collaborator_suggestions, research_context, config)
            elif config.format == CollaborationExportFormat.CSV:
                return self._export_csv(primary_faculty, collaborator_suggestions, research_context, config)
            elif config.format == CollaborationExportFormat.EMAIL_TEMPLATE:
                return self._export_email_template(primary_faculty, collaborator_suggestions, research_context, config)
            elif config.format == CollaborationExportFormat.CONTACT_SHEET:
                return self._export_contact_sheet(primary_faculty, collaborator_suggestions, research_context, config)
            elif config.format == CollaborationExportFormat.NETWORKING_REPORT:
                return self._export_networking_report(primary_faculty, collaborator_suggestions, research_context, config)
            elif config.format == CollaborationExportFormat.HTML:
                return self._export_html(primary_faculty, collaborator_suggestions, research_context, config)
            else:
                raise ValueError(f"Unsupported export format: {config.format}")
                
        except Exception as e:
            logger.error(f"Failed to export collaboration introductions: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def export_multiple_collaborations(
        self,
        collaboration_data: List[Dict[str, Any]],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """
        Export multiple collaboration introduction sets.
        
        Args:
            collaboration_data: List of collaboration data
            config: Export configuration
            
        Returns:
            Dict containing export result information
        """
        try:
            results = []
            
            for i, collab_set in enumerate(collaboration_data):
                # Create individual config
                individual_config = config.model_copy()
                if config.output_filename:
                    base_name, ext = config.output_filename.rsplit('.', 1)
                    individual_config.output_filename = f"{base_name}_{i+1:03d}.{ext}"
                
                # Export individual collaboration set
                result = self.export_collaboration_introductions(
                    collab_set["primary_faculty"],
                    collab_set["collaborator_suggestions"],
                    collab_set.get("research_context"),
                    individual_config
                )
                results.append(result)
            
            # Return summary
            successful_exports = [r for r in results if r.get("success", False)]
            
            return {
                "success": len(successful_exports) > 0,
                "total_collaboration_sets": len(collaboration_data),
                "successful_exports": len(successful_exports),
                "failed_exports": len(collaboration_data) - len(successful_exports),
                "individual_results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export multiple collaboration sets: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _export_json(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """Export collaboration data as JSON."""
        
        export_data = {
            "primary_faculty": primary_faculty.model_dump(),
            "collaborator_suggestions": [collab.model_dump() for collab in collaborator_suggestions],
            "summary": {
                "total_suggestions": len(collaborator_suggestions),
                "high_relevance_suggestions": len([c for c in collaborator_suggestions if c.relevance_score >= 0.8]),
                "average_relevance_score": sum(c.relevance_score for c in collaborator_suggestions) / len(collaborator_suggestions) if collaborator_suggestions else 0
            }
        }
        
        if research_context:
            export_data["research_context"] = research_context.model_dump()
        
        if config.include_contact_info:
            export_data["export_metadata"] = {
                "exported_at": datetime.now().isoformat(),
                "export_format": config.format.value,
                "exporter_version": "1.0.0",
                "sender_info": {
                    "name": config.sender_name,
                    "email": config.sender_email,
                    "institution": config.sender_institution
                }
            }
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "collaborators_exported": len(collaborator_suggestions),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_csv(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """Export collaboration data as CSV."""
        
        output_path = self.output_dir / config.output_filename
        
        # Define CSV fields
        fieldnames = [
            'primary_faculty_name', 'primary_faculty_institution', 'primary_faculty_department',
            'collaborator_name', 'collaborator_institution', 'relevance_score', 
            'complementary_expertise', 'shared_interests'
        ]
        
        if config.include_contact_info:
            fieldnames.append('collaborator_email')
        
        if config.include_research_details and research_context:
            fieldnames.extend(['research_title', 'research_methodology', 'research_budget'])
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for collab in collaborator_suggestions:
                row = {
                    'primary_faculty_name': primary_faculty.name,
                    'primary_faculty_institution': primary_faculty.institution,
                    'primary_faculty_department': primary_faculty.department,
                    'collaborator_name': collab.name,
                    'collaborator_institution': collab.institution,
                    'relevance_score': collab.relevance_score,
                    'complementary_expertise': ', '.join(collab.complementary_expertise),
                    'shared_interests': ', '.join(collab.shared_interests)
                }
                
                if config.include_contact_info and collab.email:
                    row['collaborator_email'] = collab.email
                
                if config.include_research_details and research_context:
                    row.update({
                        'research_title': research_context.title,
                        'research_methodology': ', '.join([m.value for m in research_context.methodology]),
                        'research_budget': float(research_context.estimated_budget)
                    })
                
                writer.writerow(row)
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "collaborators_exported": len(collaborator_suggestions),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_email_template(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """Export email templates for collaboration introductions."""
        
        templates = []
        
        # Email tone templates
        tone_templates = {
            "professional": {
                "greeting": "Dear Dr. {name},",
                "intro": "I hope this email finds you well. I am writing to introduce you to a potential collaboration opportunity.",
                "closing": "I would be happy to facilitate an introduction if you are interested in exploring this collaboration. Please let me know if you would like to connect.",
                "signature": "Best regards,"
            },
            "casual": {
                "greeting": "Hi {name},",
                "intro": "I hope you're doing well! I wanted to reach out about an exciting collaboration opportunity that might interest you.",
                "closing": "Let me know if you'd like me to put you two in touch!",
                "signature": "Best,"
            },
            "formal": {
                "greeting": "Dear Professor {name},",
                "intro": "I am writing to bring to your attention a potential research collaboration opportunity that aligns with your expertise.",
                "closing": "Should you find this opportunity of interest, I would be pleased to facilitate an introduction at your convenience.",
                "signature": "Respectfully yours,"
            }
        }
        
        tone = tone_templates.get(config.email_tone, tone_templates["professional"])
        
        for collab in collaborator_suggestions:
            # Generate email template
            email_content = []
            
            # Subject line
            subject = f"Research Collaboration Opportunity - {research_context.title if research_context else 'Faculty Introduction'}"
            email_content.append(f"Subject: {subject}")
            email_content.append("")
            
            # Greeting
            email_content.append(tone["greeting"].format(name=collab.name.split()[-1]))  # Use last name
            email_content.append("")
            
            # Introduction
            email_content.append(tone["intro"])
            email_content.append("")
            
            # Faculty introduction
            email_content.append(f"I would like to introduce you to {primary_faculty.name}, "
                                f"{primary_faculty.career_stage.value.replace('_', ' ').title()} at "
                                f"{primary_faculty.institution} in the {primary_faculty.department}.")
            email_content.append("")
            
            # Research context
            if research_context and config.include_research_details:
                email_content.append(f"Dr. {primary_faculty.name.split()[-1]} is currently working on a project titled "
                                    f"'{research_context.title}' which involves {', '.join([m.value.replace('_', ' ') for m in research_context.methodology])} approaches.")
                email_content.append("")
            
            # Why they're a good match
            email_content.append("I believe you two would be excellent collaborators because:")
            email_content.append(f"• You share research interests in: {', '.join(collab.shared_interests)}")
            email_content.append(f"• Your expertise in {', '.join(collab.complementary_expertise)} would complement their work")
            
            if config.include_match_scores:
                email_content.append(f"• Our matching algorithm shows a {collab.relevance_score:.1%} compatibility score")
            
            email_content.append("")
            
            # Collaboration history
            if collab.previous_collaborations > 0:
                email_content.append(f"I note that you have {collab.previous_collaborations} previous collaboration(s) "
                                    "which suggests strong collaborative potential.")
                email_content.append("")
            
            # Primary faculty contact info
            if config.include_contact_info and primary_faculty.email:
                email_content.append(f"Dr. {primary_faculty.name.split()[-1]} can be reached at {primary_faculty.email}")
                if primary_faculty.institutional_profile_url:
                    email_content.append(f"Profile: {primary_faculty.institutional_profile_url}")
                email_content.append("")
            
            # Closing
            email_content.append(tone["closing"])
            email_content.append("")
            
            # Signature
            email_content.append(tone["signature"])
            if config.sender_name:
                email_content.append(config.sender_name)
                if config.sender_institution:
                    email_content.append(config.sender_institution)
                if config.sender_email:
                    email_content.append(config.sender_email)
            
            templates.append({
                "collaborator": collab.name,
                "email": collab.email,
                "subject": subject,
                "content": "\n".join(email_content)
            })
        
        # Write templates to file
        output_path = self.output_dir / config.output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write(f"COLLABORATION EMAIL TEMPLATES\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Primary Faculty: {primary_faculty.name}\n")
            f.write("="*80 + "\n\n")
            
            for i, template in enumerate(templates, 1):
                f.write(f"EMAIL {i}: {template['collaborator']}\n")
                f.write("-"*80 + "\n")
                f.write(f"To: {template['email'] or '[EMAIL NEEDED]'}\n")
                f.write(f"{template['content']}\n")
                f.write("\n" + "="*80 + "\n\n")
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "email_templates_generated": len(templates),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_contact_sheet(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """Export a contact sheet with collaborator information."""
        
        content = []
        
        # Header
        content.append("="*80)
        content.append("COLLABORATION CONTACT SHEET")
        content.append("="*80)
        content.append(f"Primary Faculty: {primary_faculty.name}")
        content.append(f"Institution: {primary_faculty.institution}")
        content.append(f"Department: {primary_faculty.department}")
        content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("")
        
        # Research context
        if research_context and config.include_research_details:
            content.append("RESEARCH CONTEXT")
            content.append("-"*40)
            content.append(f"Project: {research_context.title}")
            content.append(f"Methodology: {', '.join([m.value.replace('_', ' ').title() for m in research_context.methodology])}")
            content.append(f"Budget: ${research_context.estimated_budget:,.2f}")
            content.append(f"Duration: {research_context.timeline_months} months")
            content.append("")
        
        # Collaborator suggestions
        content.append(f"SUGGESTED COLLABORATORS ({len(collaborator_suggestions)})")
        content.append("="*80)
        
        # Sort by relevance score
        sorted_collaborators = sorted(collaborator_suggestions, key=lambda x: x.relevance_score, reverse=True)
        
        for i, collab in enumerate(sorted_collaborators, 1):
            content.append(f"\n{i}. {collab.name}")
            content.append("-"*40)
            content.append(f"Institution: {collab.institution}")
            
            if config.include_contact_info and collab.email:
                content.append(f"Email: {collab.email}")
            
            if collab.profile_url:
                content.append(f"Profile: {collab.profile_url}")
            
            if config.include_match_scores:
                content.append(f"Relevance Score: {collab.relevance_score:.1%}")
            
            content.append(f"Shared Interests: {', '.join(collab.shared_interests)}")
            content.append(f"Complementary Expertise: {', '.join(collab.complementary_expertise)}")
            
            if collab.previous_collaborations > 0:
                content.append(f"Previous Collaborations: {collab.previous_collaborations}")
            
            if collab.common_publications:
                content.append(f"Common Publications: {len(collab.common_publications)}")
        
        # Summary statistics
        content.append("\n" + "="*80)
        content.append("SUMMARY STATISTICS")
        content.append("="*80)
        
        high_relevance = len([c for c in collaborator_suggestions if c.relevance_score >= 0.8])
        avg_score = sum(c.relevance_score for c in collaborator_suggestions) / len(collaborator_suggestions)
        
        content.append(f"Total Suggestions: {len(collaborator_suggestions)}")
        content.append(f"High Relevance (≥80%): {high_relevance}")
        content.append(f"Average Relevance Score: {avg_score:.1%}")
        
        # Institution distribution
        institutions = {}
        for collab in collaborator_suggestions:
            institutions[collab.institution] = institutions.get(collab.institution, 0) + 1
        
        content.append(f"Unique Institutions: {len(institutions)}")
        content.append("Institution Distribution:")
        for inst, count in sorted(institutions.items(), key=lambda x: x[1], reverse=True)[:5]:
            content.append(f"  • {inst}: {count} collaborator(s)")
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "collaborators_listed": len(collaborator_suggestions),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_networking_report(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """Export a comprehensive networking report."""
        
        content = []
        
        # Header
        content.append("="*80)
        content.append("RESEARCH NETWORKING REPORT")
        content.append("="*80)
        content.append(f"Prepared for: {primary_faculty.name}")
        content.append(f"Institution: {primary_faculty.institution}, {primary_faculty.department}")
        content.append(f"Career Stage: {primary_faculty.career_stage.value.replace('_', ' ').title()}")
        content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("")
        
        # Executive summary
        content.append("EXECUTIVE SUMMARY")
        content.append("-"*40)
        
        high_relevance = len([c for c in collaborator_suggestions if c.relevance_score >= 0.8])
        avg_score = sum(c.relevance_score for c in collaborator_suggestions) / len(collaborator_suggestions)
        
        content.append(f"This report identifies {len(collaborator_suggestions)} potential research collaborators for "
                      f"{primary_faculty.name}. {high_relevance} suggestions show high relevance (≥80%), with an "
                      f"average compatibility score of {avg_score:.1%}.")
        content.append("")
        
        # Research profile analysis
        content.append("RESEARCH PROFILE ANALYSIS")
        content.append("-"*40)
        content.append(f"Research Interests: {', '.join(primary_faculty.research_interests)}")
        content.append(f"Methodologies: {', '.join([m.value.replace('_', ' ').title() for m in primary_faculty.methodologies])}")
        
        if primary_faculty.h_index:
            content.append(f"H-Index: {primary_faculty.h_index}")
        if primary_faculty.total_citations:
            content.append(f"Total Citations: {primary_faculty.total_citations}")
        if primary_faculty.years_active:
            content.append(f"Years Active: {primary_faculty.years_active}")
        
        content.append("")
        
        # Research context
        if research_context and config.include_research_details:
            content.append("CURRENT RESEARCH PROJECT")
            content.append("-"*40)
            content.append(f"Title: {research_context.title}")
            content.append(f"Type: {research_context.variant_type.value.title()}")
            content.append(f"Question: {research_context.research_question}")
            content.append(f"Innovation Level: {research_context.innovation_level:.2f}/1.0")
            content.append(f"Feasibility: {research_context.feasibility_score:.2f}/1.0")
            content.append(f"Impact Potential: {research_context.impact_potential:.2f}/1.0")
            content.append("")
        
        # Top collaborator recommendations
        content.append("TOP COLLABORATION RECOMMENDATIONS")
        content.append("="*80)
        
        # Sort by relevance score and take top 5
        top_collaborators = sorted(collaborator_suggestions, key=lambda x: x.relevance_score, reverse=True)[:5]
        
        for i, collab in enumerate(top_collaborators, 1):
            content.append(f"\n{i}. {collab.name} - {collab.institution}")
            content.append("-"*60)
            content.append(f"Relevance Score: {collab.relevance_score:.1%}")
            content.append(f"Shared Research Interests:")
            for interest in collab.shared_interests:
                content.append(f"  • {interest}")
            content.append(f"Complementary Expertise:")
            for expertise in collab.complementary_expertise:
                content.append(f"  • {expertise}")
            
            if collab.previous_collaborations > 0:
                content.append(f"Collaboration History: {collab.previous_collaborations} previous collaboration(s)")
            
            # Networking recommendation
            if collab.relevance_score >= 0.9:
                rec = "HIGHLY RECOMMENDED - Excellent fit with strong potential for impactful collaboration"
            elif collab.relevance_score >= 0.8:
                rec = "RECOMMENDED - Good compatibility with shared research interests"
            elif collab.relevance_score >= 0.7:
                rec = "CONSIDER - Moderate fit, may be worth exploring"
            else:
                rec = "OPTIONAL - Lower compatibility, consider for specific expertise needs"
            
            content.append(f"Recommendation: {rec}")
        
        # Network analysis
        content.append("\n" + "="*80)
        content.append("NETWORK ANALYSIS")
        content.append("="*80)
        
        # Institution analysis
        institutions = {}
        for collab in collaborator_suggestions:
            institutions[collab.institution] = institutions.get(collab.institution, 0) + 1
        
        content.append(f"Network Diversity: {len(institutions)} unique institutions")
        content.append("Top Institutions for Collaboration:")
        for inst, count in sorted(institutions.items(), key=lambda x: x[1], reverse=True)[:10]:
            content.append(f"  • {inst}: {count} potential collaborator(s)")
        
        # Expertise analysis
        all_expertise = []
        for collab in collaborator_suggestions:
            all_expertise.extend(collab.complementary_expertise)
        
        expertise_counts = {}
        for exp in all_expertise:
            expertise_counts[exp] = expertise_counts.get(exp, 0) + 1
        
        content.append("\nComplementary Expertise Available:")
        for exp, count in sorted(expertise_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            content.append(f"  • {exp}: {count} collaborator(s)")
        
        # Action recommendations
        content.append("\n" + "="*80)
        content.append("RECOMMENDED ACTIONS")
        content.append("="*80)
        
        content.append("1. IMMEDIATE OUTREACH")
        for collab in top_collaborators[:3]:
            content.append(f"   • Contact {collab.name} at {collab.institution} (Score: {collab.relevance_score:.1%})")
        
        content.append("\n2. NETWORKING STRATEGIES")
        if len(set(c.institution for c in top_collaborators[:10])) > 5:
            content.append("   • Consider attending conferences where multiple target collaborators are present")
        
        top_expertise = sorted(expertise_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        content.append(f"   • Focus on expertise areas: {', '.join([exp[0] for exp in top_expertise])}")
        
        content.append("\n3. LONG-TERM RELATIONSHIP BUILDING")
        content.append("   • Consider collaborative grant applications with top-rated matches")
        content.append("   • Explore visiting scholar opportunities at high-concentration institutions")
        content.append("   • Participate in relevant research networks and consortiums")
        
        # Write to file
        output_path = self.output_dir / config.output_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return {
            "success": True,
            "output_path": str(output_path),
            "format": config.format.value,
            "collaborators_analyzed": len(collaborator_suggestions),
            "timestamp": datetime.now().isoformat()
        }
    
    def _export_html(
        self,
        primary_faculty: FacultyProfile,
        collaborator_suggestions: List[CollaboratorSuggestion],
        research_context: Optional[ResearchIdea],
        config: CollaborationExportConfig
    ) -> Dict[str, Any]:
        """Export collaboration information as HTML."""
        
        # Sort collaborators by relevance score
        sorted_collaborators = sorted(collaborator_suggestions, key=lambda x: x.relevance_score, reverse=True)
        
        # Calculate statistics
        high_relevance = len([c for c in collaborator_suggestions if c.relevance_score >= 0.8])
        avg_score = sum(c.relevance_score for c in collaborator_suggestions) / len(collaborator_suggestions)
        
        # Generate HTML content
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Collaboration Report - {primary_faculty.name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.2em;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #e9ecef;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }}
        .collaborator-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .collaborator-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .collaborator-name {{
            font-size: 1.3em;
            font-weight: bold;
            color: #333;
        }}
        .relevance-score {{
            background: #28a745;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .relevance-score.medium {{
            background: #ffc107;
            color: #333;
        }}
        .relevance-score.low {{
            background: #6c757d;
        }}
        .institution {{
            color: #666;
            margin-bottom: 10px;
        }}
        .expertise-tags {{
            margin: 10px 0;
        }}
        .tag {{
            display: inline-block;
            background: #e7f3ff;
            color: #0066cc;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            margin: 2px;
            border: 1px solid #b3d9ff;
        }}
        .shared-tag {{
            background: #e8f5e8;
            color: #28a745;
            border-color: #b3e5b3;
        }}
        .contact-info {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }}
        .research-context {{
            background: #f0f8ff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }}
        .section-title {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ccc;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Collaboration Report</h1>
        <div class="subtitle">
            Research networking opportunities for {primary_faculty.name}<br>
            {primary_faculty.institution} • {primary_faculty.department}
        </div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <span class="stat-number">{len(collaborator_suggestions)}</span>
            Total Collaborators
        </div>
        <div class="stat-card">
            <span class="stat-number">{high_relevance}</span>
            High Relevance (≥80%)
        </div>
        <div class="stat-card">
            <span class="stat-number">{avg_score:.1%}</span>
            Average Score
        </div>
        <div class="stat-card">
            <span class="stat-number">{len(set(c.institution for c in collaborator_suggestions))}</span>
            Unique Institutions
        </div>
    </div>
"""
        
        # Add research context if available
        if research_context and config.include_research_details:
            html_content += f"""
    <div class="research-context">
        <h2 class="section-title">Research Context</h2>
        <h3>{research_context.title}</h3>
        <p><strong>Type:</strong> {research_context.variant_type.value.title()}</p>
        <p><strong>Research Question:</strong> {research_context.research_question}</p>
        <p><strong>Methodology:</strong> {', '.join([m.value.replace('_', ' ').title() for m in research_context.methodology])}</p>
        <p><strong>Budget:</strong> ${research_context.estimated_budget:,.2f} • <strong>Duration:</strong> {research_context.timeline_months} months</p>
    </div>
"""
        
        # Add collaborator cards
        html_content += """
    <h2 class="section-title">Collaboration Opportunities</h2>
"""
        
        for collab in sorted_collaborators:
            # Determine score class
            if collab.relevance_score >= 0.8:
                score_class = ""
            elif collab.relevance_score >= 0.6:
                score_class = "medium"
            else:
                score_class = "low"
            
            # Build expertise tags
            shared_tags = ''.join([f'<span class="tag shared-tag">{interest}</span>' for interest in collab.shared_interests])
            expertise_tags = ''.join([f'<span class="tag">{exp}</span>' for exp in collab.complementary_expertise])
            
            # Contact info
            contact_html = ""
            if config.include_contact_info:
                contact_parts = []
                if collab.email:
                    contact_parts.append(f"<strong>Email:</strong> {collab.email}")
                if collab.profile_url:
                    contact_parts.append(f'<strong>Profile:</strong> <a href="{collab.profile_url}" target="_blank">View Profile</a>')
                if collab.previous_collaborations > 0:
                    contact_parts.append(f"<strong>Previous Collaborations:</strong> {collab.previous_collaborations}")
                
                if contact_parts:
                    contact_html = f'<div class="contact-info">{" • ".join(contact_parts)}</div>'
            
            html_content += f"""
    <div class="collaborator-card">
        <div class="collaborator-header">
            <div class="collaborator-name">{collab.name}</div>
            <div class="relevance-score {score_class}">{collab.relevance_score:.1%}</div>
        </div>
        <div class="institution">{collab.institution}</div>
        <div class="expertise-tags">
            <strong>Shared Interests:</strong> {shared_tags}<br>
            <strong>Complementary Expertise:</strong> {expertise_tags}
        </div>
        {contact_html}
    </div>
"""
        
        # Footer
        html_content += f"""
    <div class="footer">
        <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p>Faculty Research Opportunity Notifier • Collaboration Export System</p>
    </div>
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
            "collaborators_exported": len(collaborator_suggestions),
            "timestamp": datetime.now().isoformat()
        }