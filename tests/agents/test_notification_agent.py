"""
Test suite for the Notification Agent.

This module tests the NotificationAgent class functionality including
email template generation, data package processing, HTML/text formatting,
and A2A message handling with complete mock data packages.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from src.agents.notification_agent import NotificationAgent, EmailTemplateEngine
from src.core.models import NotificationContent, ProposalVariant, CareerStage
from src.core.a2a_protocols import A2AMessage, MessageType, AgentType


class TestEmailTemplateEngine:
    """Test cases for EmailTemplateEngine."""
    
    def test_format_currency(self):
        """Test currency formatting."""
        engine = EmailTemplateEngine()
        
        assert engine.format_currency(Decimal('100000')) == '$100,000'
        assert engine.format_currency(Decimal('1500.50')) == '$1,500'
        assert engine.format_currency(Decimal('0')) == '$0'
    
    def test_format_deadline(self):
        """Test deadline formatting with urgency indicators."""
        engine = EmailTemplateEngine()
        today = date.today()
        
        # Past deadline
        past_date = date(today.year, today.month, max(1, today.day - 5))
        result = engine.format_deadline(past_date)
        assert '(PAST DUE)' in result
        
        # Urgent deadline (within 7 days)
        from datetime import timedelta
        urgent_date = today + timedelta(days=3)
        result = engine.format_deadline(urgent_date)
        assert '⚠️' in result and 'days remaining' in result
        
        # Future deadline
        future_date = today + timedelta(days=60)
        result = engine.format_deadline(future_date)
        assert 'remaining' not in result or '60 days remaining' in result
    
    def test_format_timeline(self):
        """Test timeline formatting."""
        engine = EmailTemplateEngine()
        
        assert engine.format_timeline(1) == '1 month'
        assert engine.format_timeline(6) == '6 months'
        assert engine.format_timeline(12) == '1 year'
        assert engine.format_timeline(18) == '1 year, 6 months'
        assert engine.format_timeline(24) == '2 years'
    
    def test_get_variant_emoji(self):
        """Test variant emoji mapping."""
        engine = EmailTemplateEngine()
        
        assert engine.get_variant_emoji(ProposalVariant.CONSERVATIVE) == '🛡️'
        assert engine.get_variant_emoji(ProposalVariant.INNOVATIVE) == '💡'
        assert engine.get_variant_emoji(ProposalVariant.STRETCH) == '🚀'
    
    def test_get_variant_description(self):
        """Test variant description mapping."""
        engine = EmailTemplateEngine()
        
        desc = engine.get_variant_description(ProposalVariant.CONSERVATIVE)
        assert 'Low-risk' in desc
        
        desc = engine.get_variant_description(ProposalVariant.INNOVATIVE)
        assert 'Novel approach' in desc
        
        desc = engine.get_variant_description(ProposalVariant.STRETCH)
        assert 'High-impact' in desc


class TestNotificationAgent:
    """Test cases for NotificationAgent."""
    
    @pytest.fixture
    def agent(self):
        """Create a NotificationAgent instance for testing."""
        return NotificationAgent(
            default_sender="test@example.com",
            include_unsubscribe=True
        )
    
    @pytest.fixture
    def mock_faculty_data(self):
        """Mock faculty data for testing."""
        return {
            'profile_id': 'faculty_001',
            'name': 'Dr. Jane Smith',
            'email': 'jane.smith@university.edu',
            'institution': 'University of Research',
            'department': 'Computer Science',
            'career_stage': 'assistant_professor',
            'research_interests': ['machine learning', 'healthcare AI', 'data mining'],
            'methodologies': ['computational', 'experimental']
        }
    
    @pytest.fixture
    def mock_funding_data(self):
        """Mock funding data for testing."""
        return {
            'opportunity_id': 'NIH-2024-AI-HEALTHCARE-001',
            'title': 'AI in Healthcare Research Initiative',
            'agency': 'National Institutes of Health',
            'deadline': '2024-06-15',
            'max_award_amount': '250000',
            'research_areas': ['artificial intelligence', 'healthcare', 'clinical research'],
            'url': 'https://grants.nih.gov/test-opportunity'
        }
    
    @pytest.fixture
    def mock_match_data(self):
        """Mock match data for testing."""
        return {
            'match_id': 'match_001',
            'faculty_profile_id': 'faculty_001',
            'funding_opportunity_id': 'NIH-2024-AI-HEALTHCARE-001',
            'match_score': {
                'total_score': 0.85,
                'research_alignment': 0.90,
                'methodology_match': 0.80,
                'career_stage_fit': 1.0,
                'deadline_urgency': 0.75,
                'budget_alignment': 0.80
            }
        }
    
    @pytest.fixture
    def mock_research_ideas(self):
        """Mock research ideas for testing."""
        return [
            {
                'title': 'Conservative AI Healthcare Analysis',
                'variant_type': 'conservative',
                'research_question': 'How can existing ML techniques improve diagnostic accuracy?',
                'hypothesis': 'Standard ML models can enhance current diagnostic workflows',
                'estimated_budget': '150000',
                'timeline_months': 24,
                'objectives': [
                    'Implement proven ML algorithms',
                    'Validate on existing datasets',
                    'Integrate with current systems'
                ]
            },
            {
                'title': 'Innovative Multimodal Healthcare AI',
                'variant_type': 'innovative',
                'research_question': 'Can multimodal AI systems revolutionize personalized healthcare?',
                'hypothesis': 'Combining multiple data types will enable breakthrough insights',
                'estimated_budget': '200000',
                'timeline_months': 30,
                'objectives': [
                    'Develop multimodal fusion techniques',
                    'Create personalized health models',
                    'Conduct clinical validation studies'
                ]
            },
            {
                'title': 'Stretch Goal: AGI for Healthcare',
                'variant_type': 'stretch',
                'research_question': 'How can we develop general AI systems for comprehensive healthcare?',
                'hypothesis': 'Advanced AI architectures can achieve human-level medical reasoning',
                'estimated_budget': '250000',
                'timeline_months': 36,
                'objectives': [
                    'Research novel AI architectures',
                    'Develop comprehensive medical knowledge bases',
                    'Create autonomous diagnostic systems'
                ]
            }
        ]
    
    @pytest.fixture
    def mock_collaborators(self):
        """Mock collaborator suggestions for testing."""
        return [
            {
                'faculty_profile_id': 'faculty_002',
                'name': 'Dr. John Doe',
                'institution': 'Medical Center University',
                'relevance_score': 0.92,
                'complementary_expertise': ['clinical trials', 'medical imaging', 'biostatistics'],
                'shared_interests': ['healthcare AI', 'machine learning'],
                'previous_collaborations': 2,
                'common_publications': ['AI in Medical Diagnosis: A Survey']
            },
            {
                'faculty_profile_id': 'faculty_003',
                'name': 'Dr. Alice Johnson',
                'institution': 'Institute of Technology',
                'relevance_score': 0.78,
                'complementary_expertise': ['computer vision', 'deep learning', 'medical devices'],
                'shared_interests': ['AI', 'healthcare'],
                'previous_collaborations': 0,
                'common_publications': []
            }
        ]
    
    @pytest.fixture
    def complete_data_package(self, mock_faculty_data, mock_funding_data, 
                             mock_match_data, mock_research_ideas, mock_collaborators):
        """Complete data package for comprehensive testing."""
        return {
            'faculty_data': mock_faculty_data,
            'funding_data': mock_funding_data,
            'match_data': mock_match_data,
            'research_ideas': mock_research_ideas,
            'collaborators': mock_collaborators
        }
    
    def test_agent_initialization(self):
        """Test agent initialization with various parameters."""
        agent = NotificationAgent()
        assert agent.default_sender == "Research Opportunities <no-reply@research-notifier.org>"
        assert agent.include_unsubscribe is True
        
        custom_agent = NotificationAgent(
            default_sender="custom@test.com",
            include_unsubscribe=False
        )
        assert custom_agent.default_sender == "custom@test.com"
        assert custom_agent.include_unsubscribe is False
    
    def test_generate_subject_line(self, agent):
        """Test subject line generation with various scenarios."""
        today = date.today()
        from datetime import timedelta
        
        # Urgent deadline
        urgent_deadline = today + timedelta(days=3)
        subject = agent.generate_subject_line(
            "Dr. Smith", "AI Research Grant", urgent_deadline, 0.9
        )
        assert "⚠️ URGENT:" in subject
        assert "Excellent" in subject
        
        # Normal deadline with high score
        normal_deadline = today + timedelta(days=45)
        subject = agent.generate_subject_line(
            "Dr. Smith", "Very Long Research Grant Title That Should Be Truncated", 
            normal_deadline, 0.85
        )
        assert "Excellent" in subject
        assert len(subject) < 150  # Reasonable length
        
        # Low score
        subject = agent.generate_subject_line(
            "Dr. Smith", "Research Grant", normal_deadline, 0.45
        )
        assert "Potential" in subject
    
    def test_generate_html_email(self, agent, complete_data_package):
        """Test HTML email generation."""
        html_content = agent.generate_html_email(
            complete_data_package['faculty_data'],
            complete_data_package['funding_data'],
            complete_data_package['match_data'],
            complete_data_package['research_ideas'],
            complete_data_package['collaborators'],
            0.85
        )
        
        # Check basic HTML structure
        assert '<!DOCTYPE html>' in html_content
        assert '<html lang="en">' in html_content
        assert '</html>' in html_content
        
        # Check content elements
        assert 'Dr. Jane Smith' in html_content
        assert 'AI in Healthcare Research Initiative' in html_content
        assert 'National Institutes of Health' in html_content
        assert '$250,000' in html_content
        assert '85.0%' in html_content
        
        # Check research ideas
        assert 'Conservative AI Healthcare Analysis' in html_content
        assert 'Innovative Multimodal Healthcare AI' in html_content
        assert 'Stretch Goal: AGI for Healthcare' in html_content
        assert '🛡️' in html_content  # Conservative emoji
        assert '💡' in html_content  # Innovative emoji
        assert '🚀' in html_content  # Stretch emoji
        
        # Check collaborators
        assert 'Dr. John Doe' in html_content
        assert 'Medical Center University' in html_content
        assert '92%' in html_content
        
        # Check styling and structure
        assert '<style>' in html_content
        assert 'font-family: Arial' in html_content
        assert 'class="header"' in html_content
        assert 'class="idea-card"' in html_content
        assert 'class="collaborator-card"' in html_content
    
    def test_generate_plain_text_email(self, agent, complete_data_package):
        """Test plain text email generation."""
        text_content = agent.generate_plain_text_email(
            complete_data_package['faculty_data'],
            complete_data_package['funding_data'],
            complete_data_package['match_data'],
            complete_data_package['research_ideas'],
            complete_data_package['collaborators'],
            0.85
        )
        
        # Check basic structure
        assert 'NEW RESEARCH OPPORTUNITY MATCH' in text_content
        assert '=' * 50 in text_content
        assert 'FUNDING OPPORTUNITY DETAILS' in text_content
        assert 'RESEARCH PROPOSAL IDEAS' in text_content
        assert 'SUGGESTED COLLABORATORS' in text_content
        assert 'NEXT STEPS' in text_content
        
        # Check content
        assert 'Dear Dr. Jane Smith' in text_content
        assert 'AI in Healthcare Research Initiative' in text_content
        assert 'National Institutes of Health' in text_content
        assert '$250,000' in text_content
        assert '85%' in text_content or '85.0%' in text_content
        
        # Check research ideas formatting
        assert '1. Conservative AI Healthcare Analysis (CONSERVATIVE)' in text_content
        assert '2. Innovative Multimodal Healthcare AI (INNOVATIVE)' in text_content
        assert '3. Stretch Goal: AGI for Healthcare (STRETCH)' in text_content
        
        # Check collaborators formatting
        assert '1. Dr. John Doe (92% match)' in text_content
        assert '2. Dr. Alice Johnson (78% match)' in text_content
        
        # No HTML tags
        assert '<' not in text_content
        assert '>' not in text_content
    
    def test_create_notification_content(self, agent, complete_data_package):
        """Test notification content object creation."""
        notification = agent.create_notification_content(
            'match_001',
            complete_data_package['faculty_data'],
            complete_data_package['funding_data'],
            complete_data_package['match_data'],
            complete_data_package['research_ideas'],
            complete_data_package['collaborators']
        )
        
        # Check notification properties
        assert isinstance(notification, NotificationContent)
        assert notification.recipient_email == 'jane.smith@university.edu'
        assert notification.recipient_name == 'Dr. Jane Smith'
        assert notification.match_id == 'match_001'
        assert notification.funding_title == 'AI in Healthcare Research Initiative'
        assert notification.deadline == date(2024, 6, 15)
        
        # Check subject line
        assert 'AI in Healthcare Research Initiative' in notification.subject
        assert 'Excellent' in notification.subject  # High score
        
        # Check email bodies
        assert len(notification.body_html) > 1000  # Substantial HTML content
        assert len(notification.body_text) > 500   # Substantial text content
        assert '<!DOCTYPE html>' in notification.body_html
        assert 'NEW RESEARCH OPPORTUNITY MATCH' in notification.body_text
    
    def test_process_complete_data_package_with_files(self, agent, tmp_path):
        """Test processing complete data package from files."""
        
        # Create test files
        matches_data = [
            {
                'match_id': 'match_001',
                'faculty_profile_id': 'faculty_001',
                'funding_opportunity_id': 'funding_001',
                'match_score': {'total_score': 0.85}
            }
        ]
        
        ideas_data = {
            'match_001': [
                {
                    'title': 'Test Research Idea',
                    'variant_type': 'conservative',
                    'research_question': 'How to test?',
                    'estimated_budget': '100000',
                    'timeline_months': 24,
                    'objectives': ['Test objective 1', 'Test objective 2']
                }
            ]
        }
        
        collaborators_data = {
            'faculty_001': [
                {
                    'name': 'Dr. Test Collaborator',
                    'institution': 'Test University',
                    'relevance_score': 0.8,
                    'complementary_expertise': ['testing'],
                    'shared_interests': ['research']
                }
            ]
        }
        
        faculty_data = [
            {
                'profile_id': 'faculty_001',
                'name': 'Dr. Test Faculty',
                'email': 'test@university.edu',
                'institution': 'Test University',
                'research_interests': ['testing']
            }
        ]
        
        funding_data = [
            {
                'opportunity_id': 'funding_001',
                'title': 'Test Funding Opportunity',
                'agency': 'Test Agency',
                'deadline': '2024-12-31',
                'max_award_amount': '200000',
                'url': 'https://test.gov/funding'
            }
        ]
        
        # Write test files
        matches_file = tmp_path / 'matches.json'
        ideas_file = tmp_path / 'ideas.json'
        collaborators_file = tmp_path / 'collaborators.json'
        faculty_file = tmp_path / 'faculty.json'
        funding_file = tmp_path / 'funding.json'
        
        matches_file.write_text(json.dumps(matches_data))
        ideas_file.write_text(json.dumps(ideas_data))
        collaborators_file.write_text(json.dumps(collaborators_data))
        faculty_file.write_text(json.dumps(faculty_data))
        funding_file.write_text(json.dumps(funding_data))
        
        # Process data package
        notifications = agent.process_complete_data_package(
            str(matches_file), str(ideas_file), str(collaborators_file),
            str(faculty_file), str(funding_file)
        )
        
        # Verify results
        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.recipient_email == 'test@university.edu'
        assert notification.recipient_name == 'Dr. Test Faculty'
        assert notification.funding_title == 'Test Funding Opportunity'
        assert 'Test Research Idea' in notification.body_html
        assert 'Dr. Test Collaborator' in notification.body_html
    
    def test_save_notifications(self, agent, tmp_path):
        """Test saving notifications to file."""
        # Create mock notification
        notification = NotificationContent(
            recipient_email='test@university.edu',
            recipient_name='Dr. Test',
            subject='Test Subject',
            body_html='<p>Test HTML</p>',
            body_text='Test Text',
            match_id='match_001',
            funding_title='Test Funding',
            deadline=date(2024, 12, 31)
        )
        
        output_file = tmp_path / 'notifications.json'
        saved_path = agent.save_notifications([notification], str(output_file))
        
        # Verify file was saved
        assert saved_path == output_file
        assert output_file.exists()
        
        # Verify content
        with open(output_file, 'r') as f:
            saved_data = json.load(f)
        
        assert len(saved_data) == 1
        saved_notification = saved_data[0]
        assert saved_notification['recipient_email'] == 'test@university.edu'
        assert saved_notification['subject'] == 'Test Subject'
        assert saved_notification['funding_title'] == 'Test Funding'
        assert saved_notification['deadline'] == '2024-12-31'
    
    def test_get_notification_statistics(self, agent):
        """Test notification statistics generation."""
        # Create mock notifications
        notifications = [
            NotificationContent(
                recipient_email='user1@university.edu',
                recipient_name='Dr. User One',
                subject='Short Subject',
                body_html='<p>HTML</p>',
                body_text='Text',
                match_id='match_001',
                funding_title='Funding A',
                deadline=date.today()
            ),
            NotificationContent(
                recipient_email='user2@university.edu',
                recipient_name='Dr. User Two',
                subject='Very Long Subject Line That Goes On And On',
                body_html='<p>HTML</p>',
                body_text='Text',
                match_id='match_002',
                funding_title='Funding B',
                deadline=date(2024, 12, 31)
            ),
            NotificationContent(
                recipient_email='user1@university.edu',  # Same recipient
                recipient_name='Dr. User One',
                subject='Another Subject',
                body_html='<p>HTML</p>',
                body_text='Text',
                match_id='match_003',
                funding_title='Funding A',  # Same funding
                deadline=date(2025, 1, 15)
            )
        ]
        
        stats = agent.get_notification_statistics(notifications)
        
        assert stats['total_notifications'] == 3
        assert stats['recipient_count'] == 2  # Unique recipients
        assert stats['unique_funding_opportunities'] == 2  # Unique funding titles
        assert 'deadline_distribution' in stats
        assert 'average_subject_length' in stats
        
        # Check deadline distribution
        deadline_dist = stats['deadline_distribution']
        assert 'this_week' in deadline_dist
        assert 'later' in deadline_dist
    
    def test_empty_notification_statistics(self, agent):
        """Test statistics for empty notification list."""
        stats = agent.get_notification_statistics([])
        
        assert stats['total_notifications'] == 0
        assert stats['recipient_count'] == 0
        assert stats['average_subject_length'] == 0
        assert stats['deadline_distribution'] == {}
    
    def test_process_a2a_message(self, agent, tmp_path):
        """Test A2A message processing."""
        # Create minimal test files
        test_files = {
            'matches.json': [{'match_id': 'test', 'faculty_profile_id': 'f1', 'funding_opportunity_id': 'fund1'}],
            'ideas.json': {'test': []},
            'collaborators.json': {'f1': []},
            'faculty.json': [{'profile_id': 'f1', 'name': 'Dr. Test', 'email': 'test@edu'}],
            'funding.json': [{'opportunity_id': 'fund1', 'title': 'Test Fund', 'deadline': '2024-12-31'}]
        }
        
        file_paths = {}
        for filename, data in test_files.items():
            file_path = tmp_path / filename
            file_path.write_text(json.dumps(data))
            file_paths[filename.replace('.json', '_file')] = str(file_path)
        
        # Create A2A request message
        request_message = A2AMessage(
            message_type=MessageType.REQUEST,
            source_agent=AgentType.IDEA_GENERATION,
            target_agent=AgentType.NOTIFICATION,
            message_id='test_msg_001',
            timestamp=datetime.now().isoformat(),
            payload=file_paths
        )
        
        # Process message
        response = agent.process_a2a_message(request_message)
        
        # Verify response
        assert response.message_type == MessageType.RESPONSE
        assert response.source_agent == AgentType.NOTIFICATION
        assert response.target_agent == AgentType.IDEA_GENERATION
        assert response.reply_to == 'test_msg_001'
        
        # Check response payload
        payload = response.payload
        assert payload.get('success') is True or payload.get('success') is False  # Should have success field
        if payload.get('success'):
            assert 'notifications_count' in payload
            assert 'notifications_file' in payload
    
    def test_process_a2a_message_missing_files(self, agent):
        """Test A2A message processing with missing required files."""
        # Create incomplete request
        request_message = A2AMessage(
            message_type=MessageType.REQUEST,
            source_agent=AgentType.IDEA_GENERATION,
            target_agent=AgentType.NOTIFICATION,
            message_id='test_msg_002',
            timestamp=datetime.now().isoformat(),
            payload={'matches_file': 'test.json'}  # Missing other required files
        )
        
        # Process message
        response = agent.process_a2a_message(request_message)
        
        # Verify error response
        assert response.message_type == MessageType.RESPONSE
        assert 'error' in response.payload
        assert 'required' in response.payload['error'].lower()
    
    def test_run_notification_generation_a2a(self, agent, tmp_path):
        """Test the complete A2A notification generation process."""
        # Create comprehensive test data
        matches_data = [
            {
                'match_id': 'match_comprehensive',
                'faculty_profile_id': 'faculty_comp',
                'funding_opportunity_id': 'funding_comp',
                'match_score': {'total_score': 0.75}
            }
        ]
        
        ideas_data = {
            'match_comprehensive': [
                {
                    'title': 'Comprehensive Research Project',
                    'variant_type': 'innovative',
                    'research_question': 'How can we comprehensively test this system?',
                    'estimated_budget': '175000',
                    'timeline_months': 30,
                    'objectives': ['Comprehensive testing', 'System validation', 'Performance analysis']
                }
            ]
        }
        
        collaborators_data = {
            'faculty_comp': [
                {
                    'name': 'Dr. Comprehensive Collaborator',
                    'institution': 'Comprehensive University',
                    'relevance_score': 0.9,
                    'complementary_expertise': ['comprehensive analysis', 'system testing'],
                    'shared_interests': ['comprehensive research', 'testing methodologies']
                }
            ]
        }
        
        faculty_data = [
            {
                'profile_id': 'faculty_comp',
                'name': 'Dr. Comprehensive Researcher',
                'email': 'comprehensive@university.edu',
                'institution': 'Comprehensive Research University',
                'department': 'Comprehensive Studies',
                'research_interests': ['comprehensive research', 'system analysis']
            }
        ]
        
        funding_data = [
            {
                'opportunity_id': 'funding_comp',
                'title': 'Comprehensive Research Funding Initiative',
                'agency': 'Comprehensive Research Foundation',
                'deadline': '2024-08-15',
                'max_award_amount': '300000',
                'url': 'https://comprehensive.research.gov/funding',
                'research_areas': ['comprehensive research', 'system analysis']
            }
        ]
        
        # Write test files
        file_paths = {}
        test_data = {
            'matches': matches_data,
            'ideas': ideas_data,
            'collaborators': collaborators_data,
            'faculty': faculty_data,
            'funding': funding_data
        }
        
        for name, data in test_data.items():
            file_path = tmp_path / f'{name}.json'
            file_path.write_text(json.dumps(data))
            file_paths[f'{name}_file'] = str(file_path)
        
        # Run A2A process
        result = agent.run_notification_generation_a2a(**file_paths)
        
        # Verify comprehensive results
        assert result['success'] is True
        assert result['notifications_count'] == 1
        assert 'notifications_file' in result
        assert 'statistics' in result
        assert 'processing_time_seconds' in result
        assert result['processing_time_seconds'] > 0
        
        # Verify statistics
        stats = result['statistics']
        assert stats['total_notifications'] == 1
        assert stats['recipient_count'] == 1
        assert stats['unique_funding_opportunities'] == 1
        
        # Verify notification file was created
        notifications_file = Path(result['notifications_file'])
        assert notifications_file.exists()
        
        # Verify notification content
        with open(notifications_file, 'r') as f:
            saved_notifications = json.load(f)
        
        assert len(saved_notifications) == 1
        notification = saved_notifications[0]
        assert notification['recipient_email'] == 'comprehensive@university.edu'
        assert notification['recipient_name'] == 'Dr. Comprehensive Researcher'
        assert notification['funding_title'] == 'Comprehensive Research Funding Initiative'
        assert 'Comprehensive Research Project' in notification['body_html']
        assert 'Dr. Comprehensive Collaborator' in notification['body_html']
    
    def test_error_handling(self, agent):
        """Test error handling for various failure scenarios."""
        # Test with non-existent files
        result = agent.run_notification_generation_a2a(
            'nonexistent_matches.json',
            'nonexistent_ideas.json', 
            'nonexistent_collaborators.json',
            'nonexistent_faculty.json',
            'nonexistent_funding.json'
        )
        
        assert result['success'] is False
        assert 'error' in result
        assert 'processing_time_seconds' in result


if __name__ == "__main__":
    pytest.main([__file__])