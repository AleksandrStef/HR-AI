"""
Unit tests for HR AI text analyzer.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

# Add src to path for testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hr_ai.analyzers.text_analyzer import TextAnalyzer, MeetingAnalysis, ExtractedInformation

class TestTextAnalyzer:
    """Test cases for TextAnalyzer."""
    
    def setup_method(self):
        """Setup test environment."""
        self.analyzer = TextAnalyzer()
        
        # Sample document data for testing
        self.sample_document = {
            'employee_name': 'Test Employee',
            'full_text': 'Сотрудник прошел курс по Python. Встреча состоялась 15.01.2025. Планирует сертификацию AWS.',
            'sections': {
                'training': ['Прошел курс по Python', 'Планирует AWS сертификацию'],
                'meeting': ['Встреча состоялась', 'Обсудили прогресс']
            },
            'meeting_sections': ['meeting'],
            'dates_found': [
                {'date_string': '15.01.2025', 'context': 'Встреча состоялась 15.01.2025'}
            ]
        }
    
    def test_fallback_meeting_analysis(self):
        """Test fallback meeting analysis when AI is not available."""
        # Test with substantial meeting content
        result = self.analyzer._fallback_meeting_analysis(self.sample_document)
        
        assert isinstance(result, MeetingAnalysis)
        assert result.meeting_occurred == True  # Should detect meeting occurred
        assert result.confidence_score > 0.5
        assert len(result.evidence) > 0
    
    def test_fallback_meeting_analysis_no_content(self):
        """Test fallback meeting analysis with empty meeting sections."""
        empty_doc = {
            'sections': {'meeting': ['']},
            'meeting_sections': ['meeting']
        }
        
        result = self.analyzer._fallback_meeting_analysis(empty_doc)
        
        assert isinstance(result, MeetingAnalysis)
        assert result.meeting_occurred == False
        assert result.requires_hr_attention == True
    
    def test_keyword_extract_training(self):
        """Test keyword-based training extraction."""
        text = "Сотрудник прошел курс по Python и планирует сертификацию AWS. Хочет участвовать в митапе."
        
        result = self.analyzer._keyword_extract_training(text)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Check that extracted items have required fields
        for item in result:
            assert 'category' in item
            assert 'content' in item
            assert 'context' in item
    
    def test_keyword_extract_feedback(self):
        """Test keyword-based feedback extraction."""
        text = "Сотрудник удовлетворен работой, но чувствует небольшую усталость от количества задач."
        
        result = self.analyzer._keyword_extract_feedback(text)
        
        assert isinstance(result, list)
        
        # Should find satisfaction and fatigue keywords
        contents = [item['content'] for item in result]
        assert any('удовлетворен' in content for content in contents)
    
    def test_analyze_hr_processes(self):
        """Test HR processes analysis."""
        text = "Сотрудник готов участвовать в собеседованиях и проводить технические ассессменты."
        sections = {}
        
        result = self.analyzer._analyze_hr_processes(text, sections)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should find interview and assessment mentions
        categories = [item['category'] for item in result]
        assert 'interview_participation' in categories
    
    def test_analyze_location_relocation(self):
        """Test location and relocation analysis."""
        text = "Сотрудник планирует релокацию в Ташкент. Текущее местоположение: Алматы."
        sections = {}
        
        result = self.analyzer._analyze_location_relocation(text, sections)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should find location mentions
        contents = [item['content'] for item in result]
        assert any('Ташкент' in content for content in contents)
        assert any('Алматы' in content for content in contents)
    
    def test_analyze_risks_concerns(self):
        """Test risk and concern analysis."""
        text = "Сотрудник чувствует усталость и перегрузку. Есть признаки выгорания."
        sections = {}
        
        result = self.analyzer._analyze_risks_concerns(text, sections)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should find risk indicators
        contents = [item['content'] for item in result]
        risk_keywords = ['усталость', 'перегрузка', 'выгорания']
        assert any(any(keyword in content for keyword in risk_keywords) for content in contents)
    
    def test_extract_structured_information_fallback(self):
        """Test structured information extraction with fallback methods."""
        result = self.analyzer._fallback_information_extraction(self.sample_document)
        
        assert isinstance(result, ExtractedInformation)
        assert isinstance(result.training_development, list)
        assert isinstance(result.feedback_motivation, list)
        assert isinstance(result.hr_processes, list)
        assert isinstance(result.community_engagement, list)
        assert isinstance(result.location_relocation, list)
        assert isinstance(result.risks_concerns, list)

if __name__ == "__main__":
    pytest.main([__file__])