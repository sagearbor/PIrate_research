"""
Notification Agent for the Faculty Research Opportunity Notifier.

This agent is responsible for formatting and preparing email notifications
based on faculty-funding matches, research ideas, and collaborator suggestions.
It generates professional, personalized email content with both HTML and
plain text formats.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime, date
from pathlib import Path
import json
from decimal import Decimal
import re

from ..core.models import (
    FacultyFundingMatch, ResearchIdea, CollaboratorSuggestion,
    NotificationContent, FacultyProfile, FundingOpportunity,
    ProposalVariant, CareerStage
)
from ..core.a2a_protocols import (
    A2AMessage, MessageType, AgentType,
    create_a2a_response, NotificationChannel
)

logger = logging.getLogger(__name__)


class EmailTemplateEngine:
    """Template engine for generating email content."""
    
    @staticmethod
    def format_currency(amount: Decimal) -> str:
        """Format currency amount for display."""
        try:
            return f"${amount:,.0f}"
        except (ValueError, TypeError):
            return f"${amount}"
    
    @staticmethod
    def format_deadline(deadline: date) -> str:
        """Format deadline for display with urgency indicator."""
        today = date.today()
        days_until = (deadline - today).days
        
        if days_until < 0:
            return f"{deadline.strftime('%B %d, %Y')} (PAST DUE)"
        elif days_until <= 7:
            return f"{deadline.strftime('%B %d, %Y')} (⚠️ {days_until} days remaining)"
        elif days_until <= 30:
            return f"{deadline.strftime('%B %d, %Y')} ({days_until} days remaining)"
        else:
            return f"{deadline.strftime('%B %d, %Y')}"
    
    @staticmethod
    def format_timeline(months: int) -> str:
        """Format timeline for display."""
        if months == 1:
            return "1 month"
        elif months < 12:
            return f"{months} months"
        elif months == 12:
            return "1 year"
        else:
            years = months // 12
            remaining_months = months % 12
            if remaining_months == 0:
                return f"{years} year{'s' if years > 1 else ''}"
            else:
                return f"{years} year{'s' if years > 1 else ''}, {remaining_months} month{'s' if remaining_months > 1 else ''}"
    
    @staticmethod
    def get_variant_emoji(variant: ProposalVariant) -> str:
        """Get emoji for proposal variant."""
        emoji_map = {
            ProposalVariant.CONSERVATIVE: "🛡️",
            ProposalVariant.INNOVATIVE: "💡",
            ProposalVariant.STRETCH: "🚀"
        }
        return emoji_map.get(variant, "📋")
    
    @staticmethod
    def get_variant_description(variant: ProposalVariant) -> str:
        """Get description for proposal variant."""
        descriptions = {
            ProposalVariant.CONSERVATIVE: "Low-risk approach with proven methodologies",
            ProposalVariant.INNOVATIVE: "Novel approach balancing innovation with feasibility",
            ProposalVariant.STRETCH: "High-impact, cutting-edge research with ambitious goals"
        }
        return descriptions.get(variant, "Research proposal variant")


class NotificationAgent:
    """
    Agent responsible for formatting and preparing email notifications
    based on complete data packages from Phase 3 agents.
    """
    
    def __init__(self, 
                 template_dir: str = None,
                 default_sender: str = "Research Opportunities <no-reply@research-notifier.org>",
                 include_unsubscribe: bool = True):
        """
        Initialize the Notification Agent.
        
        Args:
            template_dir: Directory containing email templates
            default_sender: Default sender email address
            include_unsubscribe: Whether to include unsubscribe links
        """
        self.template_dir = Path(template_dir) if template_dir else None
        self.default_sender = default_sender
        self.include_unsubscribe = include_unsubscribe
        self.template_engine = EmailTemplateEngine()
        
        logger.info("Notification Agent initialized")
    
    def load_data_package(self, data_package_file: str) -> Dict[str, Any]:
        """Load complete data package from file."""
        try:
            with open(data_package_file, 'r') as f:
                package_data = json.load(f)
            
            logger.info(f"Loaded data package from {data_package_file}")
            return package_data
            
        except Exception as e:
            logger.error(f"Error loading data package from {data_package_file}: {e}")
            return {}
    
    def load_reference_data(self, faculty_file: str, funding_file: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Load faculty and funding reference data."""
        try:
            with open(faculty_file, 'r') as f:
                faculty_data = json.load(f)
            
            with open(funding_file, 'r') as f:
                funding_data = json.load(f)
            
            # Create lookup dictionaries
            faculty_lookup = {profile.get('profile_id', profile.get('name')): profile for profile in faculty_data}
            funding_lookup = {opp.get('opportunity_id'): opp for opp in funding_data}
            
            logger.info(f"Loaded {len(faculty_lookup)} faculty profiles and {len(funding_lookup)} funding opportunities")
            return faculty_lookup, funding_lookup
            
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
            return {}, {}
    
    def generate_subject_line(self, 
                            faculty_name: str,
                            funding_title: str, 
                            deadline: date,
                            match_score: float) -> str:
        """Generate personalized email subject line."""
        
        # Calculate urgency
        today = date.today()
        days_until = (deadline - today).days
        
        if days_until <= 7:
            urgency = "⚠️ URGENT: "
        elif days_until <= 30:
            urgency = "🕐 Reminder: "
        else:
            urgency = ""
        
        # Score-based language
        if match_score >= 0.8:
            match_quality = "Excellent"
        elif match_score >= 0.6:
            match_quality = "Strong"
        else:
            match_quality = "Potential"
        
        # Truncate funding title if too long
        max_title_length = 50
        if len(funding_title) > max_title_length:
            funding_title = funding_title[:max_title_length].rsplit(' ', 1)[0] + "..."
        
        subject = f"{urgency}{match_quality} Research Opportunity: {funding_title}"
        
        return subject
    
    def generate_html_email(self,
                          faculty_data: Dict[str, Any],
                          funding_data: Dict[str, Any],
                          match_data: Dict[str, Any],
                          research_ideas: List[Dict[str, Any]],
                          collaborators: List[Dict[str, Any]],
                          match_score: float) -> str:
        """Generate HTML email content."""
        
        faculty_name = faculty_data.get('name', 'Dear Colleague')
        funding_title = funding_data.get('title', 'Research Opportunity')
        agency = funding_data.get('agency', 'Funding Agency')
        deadline = funding_data.get('deadline')
        max_award = funding_data.get('max_award_amount')
        funding_url = funding_data.get('url', '#')
        
        # Parse deadline
        if isinstance(deadline, str):
            try:
                deadline = date.fromisoformat(deadline)
            except ValueError:
                deadline = date.today()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Opportunity Notification</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .opportunity-card {{ background: #f8f9ff; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 4px; }}
        .match-score {{ display: inline-block; background: #28a745; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 14px; }}
        .deadline {{ color: #dc3545; font-weight: bold; }}
        .idea-card {{ background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .variant-header {{ display: flex; align-items: center; margin-bottom: 10px; }}
        .variant-emoji {{ font-size: 24px; margin-right: 10px; }}
        .variant-title {{ font-size: 18px; font-weight: bold; color: #495057; }}
        .budget {{ color: #28a745; font-weight: bold; }}
        .timeline {{ color: #6c757d; }}
        .collaborator-card {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 15px; margin: 10px 0; }}
        .score-badge {{ background: #17a2b8; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 10px; }}
        .cta-section {{ background: #e9ecef; padding: 25px; border-radius: 8px; text-align: center; margin: 30px 0; }}
        .cta-button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 10px; }}
        .footer {{ color: #6c757d; font-size: 12px; text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 5px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 New Research Opportunity Match</h1>
        <p>Personalized recommendation for {faculty_name}</p>
    </div>
    
    <div class="opportunity-card">
        <h2>{funding_title}</h2>
        <p><strong>Agency:</strong> {agency}</p>
        <p><strong>Deadline:</strong> <span class="deadline">{self.template_engine.format_deadline(deadline)}</span></p>
        {f'<p><strong>Maximum Award:</strong> {self.template_engine.format_currency(max_award)}</p>' if max_award else ''}
        <p><strong>Match Score:</strong> <span class="match-score">{match_score:.1%}</span></p>
        <p><a href="{funding_url}" target="_blank">📋 View Full Opportunity Details</a></p>
    </div>
    
    <h2>🚀 Research Proposal Ideas</h2>
    <p>Based on your research profile and this funding opportunity, here are three proposal approaches:</p>
"""
        
        # Add research ideas
        for idea in research_ideas:
            variant = idea.get('variant_type', 'conservative')
            variant_enum = ProposalVariant(variant)
            emoji = self.template_engine.get_variant_emoji(variant_enum)
            description = self.template_engine.get_variant_description(variant_enum)
            
            budget = idea.get('estimated_budget', '0')
            timeline = idea.get('timeline_months', 24)
            objectives = idea.get('objectives', [])
            
            html_content += f"""
    <div class="idea-card">
        <div class="variant-header">
            <span class="variant-emoji">{emoji}</span>
            <span class="variant-title">{idea.get('title', 'Research Proposal')}</span>
        </div>
        <p><em>{description}</em></p>
        <p><strong>Research Question:</strong> {idea.get('research_question', 'Not specified')}</p>
        <p><strong>Budget:</strong> <span class="budget">{self.template_engine.format_currency(Decimal(str(budget)))}</span> | 
           <strong>Timeline:</strong> <span class="timeline">{self.template_engine.format_timeline(timeline)}</span></p>
        {f'<p><strong>Key Objectives:</strong></p><ul>{"".join(f"<li>{obj}</li>" for obj in objectives[:3])}</ul>' if objectives else ''}
    </div>
"""
        
        # Add collaborator suggestions
        if collaborators:
            html_content += """
    <h2>🤝 Suggested Collaborators</h2>
    <p>These researchers have complementary expertise that could strengthen your proposal:</p>
"""
            
            for collaborator in collaborators[:5]:  # Limit to top 5
                name = collaborator.get('name', 'Unknown')
                institution = collaborator.get('institution', 'Unknown Institution')
                score = collaborator.get('relevance_score', 0.0)
                shared_interests = collaborator.get('shared_interests', [])
                complementary = collaborator.get('complementary_expertise', [])
                
                html_content += f"""
    <div class="collaborator-card">
        <h4>{name} <span class="score-badge">{score:.0%} match</span></h4>
        <p><strong>Institution:</strong> {institution}</p>
        {f'<p><strong>Shared Interests:</strong> {", ".join(shared_interests[:3])}</p>' if shared_interests else ''}
        {f'<p><strong>Complementary Expertise:</strong> {", ".join(complementary[:3])}</p>' if complementary else ''}
    </div>
"""
        
        # Add call-to-action section
        html_content += f"""
    <div class="cta-section">
        <h3>Ready to Apply?</h3>
        <p>Don't miss this opportunity! The deadline is {self.template_engine.format_deadline(deadline)}.</p>
        <a href="{funding_url}" class="cta-button">📝 Access Application</a>
        <a href="mailto:research-support@institution.edu" class="cta-button">💬 Get Support</a>
    </div>
    
    <div class="footer">
        <p>This recommendation was generated by the Research Opportunity Notifier system.<br>
        Questions? Contact your research office or reply to this email.</p>
        {f'<p><a href="#">Unsubscribe</a> | <a href="#">Update Preferences</a></p>' if self.include_unsubscribe else ''}
        <p>Generated on {datetime.now().strftime('%B %d, %Y')}</p>
    </div>
</body>
</html>
"""
        
        return html_content
    
    def generate_plain_text_email(self,
                                faculty_data: Dict[str, Any],
                                funding_data: Dict[str, Any],
                                match_data: Dict[str, Any],
                                research_ideas: List[Dict[str, Any]],
                                collaborators: List[Dict[str, Any]],
                                match_score: float) -> str:
        """Generate plain text email content."""
        
        faculty_name = faculty_data.get('name', 'Dear Colleague')
        funding_title = funding_data.get('title', 'Research Opportunity')
        agency = funding_data.get('agency', 'Funding Agency')
        deadline = funding_data.get('deadline')
        max_award = funding_data.get('max_award_amount')
        funding_url = funding_data.get('url', '#')
        
        # Parse deadline
        if isinstance(deadline, str):
            try:
                deadline = date.fromisoformat(deadline)
            except ValueError:
                deadline = date.today()
        
        text_content = f"""
NEW RESEARCH OPPORTUNITY MATCH
{'=' * 50}

Dear {faculty_name},

We've identified a research funding opportunity that matches your profile with a {match_score:.0%} compatibility score.

FUNDING OPPORTUNITY DETAILS
{'-' * 30}
Title: {funding_title}
Agency: {agency}
Deadline: {self.template_engine.format_deadline(deadline)}
"""
        
        if max_award:
            text_content += f"Maximum Award: {self.template_engine.format_currency(max_award)}\n"
        
        text_content += f"""
Full Details: {funding_url}

RESEARCH PROPOSAL IDEAS
{'-' * 25}
Based on your research profile, here are three proposal approaches:

"""
        
        # Add research ideas
        for i, idea in enumerate(research_ideas, 1):
            variant = idea.get('variant_type', 'conservative')
            variant_enum = ProposalVariant(variant)
            description = self.template_engine.get_variant_description(variant_enum)
            
            budget = idea.get('estimated_budget', '0')
            timeline = idea.get('timeline_months', 24)
            objectives = idea.get('objectives', [])
            
            text_content += f"""
{i}. {idea.get('title', 'Research Proposal')} ({variant.upper()})
   {description}
   
   Research Question: {idea.get('research_question', 'Not specified')}
   Budget: {self.template_engine.format_currency(Decimal(str(budget)))}
   Timeline: {self.template_engine.format_timeline(timeline)}
"""
            
            if objectives:
                text_content += "   Key Objectives:\n"
                for obj in objectives[:3]:
                    text_content += f"   - {obj}\n"
            
            text_content += "\n"
        
        # Add collaborator suggestions
        if collaborators:
            text_content += f"""
SUGGESTED COLLABORATORS
{'-' * 23}
These researchers have complementary expertise:

"""
            
            for i, collaborator in enumerate(collaborators[:5], 1):
                name = collaborator.get('name', 'Unknown')
                institution = collaborator.get('institution', 'Unknown Institution')
                score = collaborator.get('relevance_score', 0.0)
                shared_interests = collaborator.get('shared_interests', [])
                complementary = collaborator.get('complementary_expertise', [])
                
                text_content += f"""
{i}. {name} ({score:.0%} match)
   Institution: {institution}
"""
                
                if shared_interests:
                    text_content += f"   Shared Interests: {', '.join(shared_interests[:3])}\n"
                
                if complementary:
                    text_content += f"   Complementary Expertise: {', '.join(complementary[:3])}\n"
                
                text_content += "\n"
        
        # Add call-to-action
        text_content += f"""
NEXT STEPS
{'-' * 10}
Don't miss this opportunity! The deadline is {self.template_engine.format_deadline(deadline)}.

1. Review the full opportunity: {funding_url}
2. Contact research support: research-support@institution.edu
3. Begin preparing your application

{'UNSUBSCRIBE' if self.include_unsubscribe else ''}
{'-' * 12 if self.include_unsubscribe else ''}
{'To unsubscribe or update preferences, reply to this email.' if self.include_unsubscribe else ''}

This recommendation was generated by the Research Opportunity Notifier system.
Generated on {datetime.now().strftime('%B %d, %Y')}

Questions? Contact your research office or reply to this email.
"""
        
        return text_content.strip()
    
    def create_notification_content(self,
                                  match_id: str,
                                  faculty_data: Dict[str, Any],
                                  funding_data: Dict[str, Any],
                                  match_data: Dict[str, Any],
                                  research_ideas: List[Dict[str, Any]],
                                  collaborators: List[Dict[str, Any]]) -> NotificationContent:
        """Create a complete notification content object."""
        
        # Extract key information
        faculty_name = faculty_data.get('name', 'Dear Colleague')
        faculty_email = faculty_data.get('email', 'unknown@example.com')
        funding_title = funding_data.get('title', 'Research Opportunity')
        deadline = funding_data.get('deadline')
        match_score = match_data.get('match_score', {}).get('total_score', 0.0)
        
        # Parse deadline
        if isinstance(deadline, str):
            try:
                deadline_date = date.fromisoformat(deadline)
            except ValueError:
                deadline_date = date.today()
        else:
            deadline_date = deadline or date.today()
        
        # Generate email content
        subject = self.generate_subject_line(faculty_name, funding_title, deadline_date, match_score)
        html_body = self.generate_html_email(faculty_data, funding_data, match_data, research_ideas, collaborators, match_score)
        text_body = self.generate_plain_text_email(faculty_data, funding_data, match_data, research_ideas, collaborators, match_score)
        
        # Create notification content object
        notification = NotificationContent(
            recipient_email=faculty_email,
            recipient_name=faculty_name,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            match_id=match_id,
            funding_title=funding_title,
            deadline=deadline_date
        )
        
        return notification
    
    def process_complete_data_package(self,
                                    matches_file: str,
                                    ideas_file: str,
                                    collaborators_file: str,
                                    faculty_file: str,
                                    funding_file: str) -> List[NotificationContent]:
        """
        Process complete data package and generate notifications.
        
        Args:
            matches_file: Faculty-funding matches file
            ideas_file: Research ideas file
            collaborators_file: Collaborator suggestions file
            faculty_file: Faculty reference data
            funding_file: Funding reference data
            
        Returns:
            List of NotificationContent objects
        """
        
        try:
            # Load all data
            with open(matches_file, 'r') as f:
                matches_data = json.load(f)
            
            with open(ideas_file, 'r') as f:
                ideas_data = json.load(f)
            
            with open(collaborators_file, 'r') as f:
                collaborators_data = json.load(f)
            
            faculty_lookup, funding_lookup = self.load_reference_data(faculty_file, funding_file)
            
            notifications = []
            
            # Process each match
            for match in matches_data:
                match_id = match.get('match_id')
                faculty_id = match.get('faculty_profile_id')
                funding_id = match.get('funding_opportunity_id')
                
                if not all([match_id, faculty_id, funding_id]):
                    logger.warning(f"Incomplete match data: {match}")
                    continue
                
                # Get reference data
                faculty_data = faculty_lookup.get(faculty_id)
                funding_data = funding_lookup.get(funding_id)
                
                if not faculty_data or not funding_data:
                    logger.warning(f"Missing reference data for match {match_id}")
                    continue
                
                # Get ideas and collaborators for this match
                research_ideas = ideas_data.get(match_id, [])
                collaborators = collaborators_data.get(faculty_id, [])
                
                # Create notification
                try:
                    notification = self.create_notification_content(
                        match_id, faculty_data, funding_data, match,
                        research_ideas, collaborators
                    )
                    notifications.append(notification)
                    
                    logger.info(f"Created notification for match {match_id}")
                    
                except Exception as e:
                    logger.error(f"Error creating notification for match {match_id}: {e}")
                    continue
            
            logger.info(f"Generated {len(notifications)} notifications from {len(matches_data)} matches")
            return notifications
            
        except Exception as e:
            logger.error(f"Error processing data package: {e}")
            return []
    
    def save_notifications(self, notifications: List[NotificationContent], output_file: str = None) -> Path:
        """Save generated notifications to file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/processed/notifications_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert notifications to serializable format
        notifications_data = []
        for notification in notifications:
            notification_dict = {
                'recipient_email': notification.recipient_email,
                'recipient_name': notification.recipient_name,
                'subject': notification.subject,
                'body_html': notification.body_html,
                'body_text': notification.body_text,
                'match_id': notification.match_id,
                'funding_title': notification.funding_title,
                'deadline': notification.deadline.isoformat(),
                'sent': notification.sent,
                'sent_date': notification.sent_date.isoformat() if notification.sent_date else None,
                'created_date': notification.created_date.isoformat()
            }
            notifications_data.append(notification_dict)
        
        with open(output_path, 'w') as f:
            json.dump(notifications_data, f, indent=2)
        
        logger.info(f"Saved {len(notifications)} notifications to {output_path}")
        return output_path
    
    def get_notification_statistics(self, notifications: List[NotificationContent]) -> Dict[str, Any]:
        """Generate statistics about the notification generation process."""
        if not notifications:
            return {
                'total_notifications': 0,
                'recipient_count': 0,
                'average_subject_length': 0,
                'deadline_distribution': {}
            }
        
        # Calculate statistics
        recipient_emails = set(n.recipient_email for n in notifications)
        subject_lengths = [len(n.subject) for n in notifications]
        
        # Deadline distribution
        today = date.today()
        deadline_buckets = {
            'overdue': 0,
            'this_week': 0,
            'this_month': 0,
            'next_3_months': 0,
            'later': 0
        }
        
        for notification in notifications:
            days_until = (notification.deadline - today).days
            if days_until < 0:
                deadline_buckets['overdue'] += 1
            elif days_until <= 7:
                deadline_buckets['this_week'] += 1
            elif days_until <= 30:
                deadline_buckets['this_month'] += 1
            elif days_until <= 90:
                deadline_buckets['next_3_months'] += 1
            else:
                deadline_buckets['later'] += 1
        
        return {
            'total_notifications': len(notifications),
            'recipient_count': len(recipient_emails),
            'average_subject_length': sum(subject_lengths) / len(subject_lengths),
            'deadline_distribution': deadline_buckets,
            'unique_funding_opportunities': len(set(n.funding_title for n in notifications))
        }
    
    def process_a2a_message(self, message: A2AMessage) -> A2AMessage:
        """Process A2A messages from other agents."""
        logger.info(f"Processing A2A message from {message.source_agent}")
        
        try:
            request_data = message.payload
            
            # Extract parameters from request
            matches_file = request_data.get('matches_file')
            ideas_file = request_data.get('ideas_file')
            collaborators_file = request_data.get('collaborators_file')
            faculty_file = request_data.get('faculty_file')
            funding_file = request_data.get('funding_file')
            
            required_files = [matches_file, ideas_file, collaborators_file, faculty_file, funding_file]
            if not all(required_files):
                raise ValueError("All data files are required: matches_file, ideas_file, collaborators_file, faculty_file, funding_file")
            
            # Process notification generation request
            result = self.run_notification_generation_a2a(
                matches_file, ideas_file, collaborators_file, faculty_file, funding_file
            )
            
            # Create response
            response = create_a2a_response(
                message,
                result,
                success=result.get('success', False)
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
    
    def run_notification_generation_a2a(self,
                                      matches_file: str,
                                      ideas_file: str,
                                      collaborators_file: str,
                                      faculty_file: str,
                                      funding_file: str) -> Dict[str, Any]:
        """Run notification generation process for A2A communication."""
        start_time = datetime.now()
        
        try:
            # Process complete data package
            notifications = self.process_complete_data_package(
                matches_file, ideas_file, collaborators_file, faculty_file, funding_file
            )
            
            if not notifications:
                return {
                    'success': False,
                    'error': 'No notifications generated',
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            # Save notifications
            notifications_file = self.save_notifications(notifications)
            
            # Generate statistics
            stats = self.get_notification_statistics(notifications)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'notifications_count': len(notifications),
                'notifications_file': str(notifications_file),
                'statistics': stats,
                'processing_time_seconds': processing_time
            }
            
        except Exception as e:
            logger.error(f"Error in notification generation process: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def run_notification_generation(self,
                                  matches_file: str,
                                  ideas_file: str,
                                  collaborators_file: str,
                                  faculty_file: str,
                                  funding_file: str) -> Dict[str, Any]:
        """Run the complete notification generation process."""
        return self.run_notification_generation_a2a(
            matches_file, ideas_file, collaborators_file, faculty_file, funding_file
        )


def main():
    """Main function for running the notification agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Notification Agent')
    parser.add_argument('--matches-file', required=True, help='Faculty-funding matches file path')
    parser.add_argument('--ideas-file', required=True, help='Research ideas file path')
    parser.add_argument('--collaborators-file', required=True, help='Collaborator suggestions file path')
    parser.add_argument('--faculty-file', required=True, help='Faculty data file path')
    parser.add_argument('--funding-file', required=True, help='Funding data file path')
    parser.add_argument('--template-dir', help='Email templates directory')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = NotificationAgent(template_dir=args.template_dir)
    
    # Run notification generation
    result = agent.run_notification_generation(
        args.matches_file, args.ideas_file, args.collaborators_file,
        args.faculty_file, args.funding_file
    )
    
    if result['success']:
        print(f"Notification generation complete!")
        print(f"Generated {result['notifications_count']} notifications")
        print(f"Results saved to: {result['notifications_file']}")
        print(f"Processing time: {result['processing_time_seconds']:.2f} seconds")
        
        # Print statistics
        if 'statistics' in result:
            stats = result['statistics']
            print(f"\nStatistics:")
            print(f"Recipients: {stats['recipient_count']}")
            print(f"Average subject length: {stats['average_subject_length']:.0f} characters")
            print(f"Deadline distribution: {stats['deadline_distribution']}")
    else:
        print(f"Notification generation failed: {result['error']}")


if __name__ == "__main__":
    main()