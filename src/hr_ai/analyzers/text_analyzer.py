"""
AI-powered text analysis engine for extracting structured information from IDPs.
Uses OpenAI GPT models for intelligent content extraction and analysis.
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

import openai
from openai import OpenAI
from pydantic import BaseModel, Field

from config.settings import settings

logger = logging.getLogger(__name__)

class MeetingAnalysis(BaseModel):
    """Structure for meeting analysis results."""
    meeting_occurred: bool = Field(description="Whether a meeting actually took place")
    confidence_score: float = Field(description="Confidence in the analysis (0-1)")
    evidence: List[str] = Field(description="Text evidence supporting the conclusion")
    planned_date: Optional[str] = Field(default=None, description="Planned meeting date if found")
    actual_date: Optional[str] = Field(default=None, description="Actual meeting date if found")
    meeting_type: Optional[str] = Field(default=None, description="Type of meeting (checkpoint, review, etc.)")
    requires_hr_attention: bool = Field(default=False, description="Whether this needs HR follow-up")

class ExtractedInformation(BaseModel):
    """Structure for extracted key information."""
    training_development: List[Dict[str, str]] = Field(description="Training and development items")
    feedback_motivation: List[Dict[str, str]] = Field(description="Feedback and motivation insights")
    hr_processes: List[Dict[str, str]] = Field(description="HR-related processes and proposals")
    community_engagement: List[Dict[str, str]] = Field(description="Community and communication items")
    location_relocation: List[Dict[str, str]] = Field(description="Location and relocation mentions")
    risks_concerns: List[Dict[str, str]] = Field(description="Identified risks or concerns")

class TextAnalyzer:
    """AI-powered text analyzer for IDP documents."""
    
    def __init__(self):
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured. AI analysis will be limited.")
            self.client = None
        else:
            self.client = OpenAI(api_key=settings.openai_api_key)
    
    def analyze_meeting_occurrence(self, document_data: Dict[str, Any]) -> MeetingAnalysis:
        """
        Analyze whether a meeting occurred based on document content.
        
        Args:
            document_data: Parsed document data from DocumentParser
            
        Returns:
            MeetingAnalysis object with meeting status and evidence
        """
        if not self.client:
            return self._fallback_meeting_analysis(document_data)
        
        try:
            # Prepare context for AI analysis
            relevant_sections = self._extract_meeting_sections(document_data)
            context = self._build_meeting_context(document_data, relevant_sections)
            
            prompt = self._create_meeting_analysis_prompt(context)
            
            response = self.client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": self._get_meeting_analysis_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=settings.max_tokens,
                temperature=settings.temperature
            )
            
            result = self._parse_meeting_analysis_response(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error in AI meeting analysis: {str(e)}")
            return self._fallback_meeting_analysis(document_data)
    
    def extract_structured_information(self, document_data: Dict[str, Any]) -> ExtractedInformation:
        """
        Extract structured information from document using AI analysis.
        
        Args:
            document_data: Parsed document data
            
        Returns:
            ExtractedInformation object with categorized insights
        """
        if not self.client:
            return self._fallback_information_extraction(document_data)
        
        try:
            full_text = document_data.get('full_text', '')
            sections = document_data.get('sections', {})
            
            # Analyze each category separately for better accuracy
            categories = {
                'training_development': self._analyze_training_development(full_text, sections),
                'feedback_motivation': self._analyze_feedback_motivation(full_text, sections),
                'hr_processes': self._analyze_hr_processes(full_text, sections),
                'community_engagement': self._analyze_community_engagement(full_text, sections),
                'location_relocation': self._analyze_location_relocation(full_text, sections),
                'risks_concerns': self._analyze_risks_concerns(full_text, sections)
            }
            
            return ExtractedInformation(**categories)
            
        except Exception as e:
            logger.error(f"Error in AI information extraction: {str(e)}")
            return self._fallback_information_extraction(document_data)
    
    def _extract_meeting_sections(self, document_data: Dict[str, Any]) -> List[str]:
        """Extract sections that likely contain meeting information."""
        sections = document_data.get('sections', {})
        meeting_sections = document_data.get('meeting_sections', [])
        
        relevant_content = []
        
        # Focus on sections identified as meeting-related
        for section_name in meeting_sections:
            if section_name in sections:
                relevant_content.extend(sections[section_name])
        
        # Also check for recent date sections
        for section_name, content in sections.items():
            section_text = ' '.join(content).lower()
            if any(keyword in section_text for keyword in ['checkpoint', 'review', '2025', '2024']):
                relevant_content.extend(content)
        
        return relevant_content
    
    def _build_meeting_context(self, document_data: Dict[str, Any], relevant_sections: List[str]) -> str:
        """Build context string for meeting analysis."""
        employee_name = document_data.get('employee_name', 'Unknown')
        dates_found = document_data.get('dates_found', [])
        
        context = f"Employee: {employee_name}\n\n"
        
        if dates_found:
            context += "Dates mentioned in document:\n"
            for date_info in dates_found[:5]:  # Limit to first 5 dates
                context += f"- {date_info['date_string']}: {date_info['context'][:100]}...\n"
            context += "\n"
        
        context += "Relevant meeting sections:\n"
        for section in relevant_sections[:10]:  # Limit content
            context += f"- {section[:200]}...\n"
        
        return context
    
    def _create_meeting_analysis_prompt(self, context: str) -> str:
        """Create prompt for meeting analysis."""
        return f"""
Analyze the following Individual Development Plan (IDP) content to determine if scheduled meetings actually occurred.

{context}

Please analyze:
1. Were there planned meetings that should have happened?
2. Is there evidence that meetings actually occurred (comments, feedback, discussions)?
3. Are there empty sections where meeting content should be?
4. What is your confidence level in this assessment?

Consider that meetings are indicated by:
- Filled sections with substantial comments
- Discussion points and feedback
- Action items or follow-ups
- References to conversations or calls

Respond in JSON format with the structure:
{{
    "meeting_occurred": boolean,
    "confidence_score": float (0-1),
    "evidence": [list of text evidence],
    "planned_date": "date string or null",
    "actual_date": "date string or null", 
    "meeting_type": "checkpoint/review/other or null",
    "requires_hr_attention": boolean
}}
"""
    
    def _get_meeting_analysis_system_prompt(self) -> str:
        """Get system prompt for meeting analysis."""
        return """You are an HR AI assistant specialized in analyzing Individual Development Plans (IDPs). 
Your task is to determine whether scheduled meetings between employees and managers actually took place.

Key indicators of successful meetings:
- Substantive comments and feedback
- Discussion of goals and progress
- Action items or next steps
- References to conversations or calls

Red flags for missed meetings:
- Empty sections for scheduled meeting dates
- Placeholder text without substance
- Missing feedback where expected
- Dates in the past with no content

Be objective and provide clear reasoning for your conclusions."""
    
    def _analyze_training_development(self, full_text: str, sections: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Extract training and development information."""
        if not self.client:
            return self._keyword_extract_training(full_text)
        
        try:
            prompt = f"""
Extract training and development information from this IDP content:

{full_text[:3000]}  # Limit text length

Find information about:
- Certifications obtained or planned
- Courses completed or desired
- Workshop participation or interest
- Speaking opportunities (forums, meetups)
- Knowledge sharing activities
- Skill development goals

Return as JSON array of objects with:
- "category": type of activity
- "content": the specific information
- "status": planned/completed/interested
- "context": surrounding text for verification
"""
            
            response = self.client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": "Extract training and development information from HR documents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            response_content = response.choices[0].message.content
            if not response_content or not response_content.strip():
                logger.warning("Empty response from OpenAI for training analysis")
                return self._keyword_extract_training(full_text)
            
            try:
                # Handle markdown code blocks
                if response_content.strip().startswith('```json'):
                    # Extract JSON from markdown code block
                    json_start = response_content.find('```json') + 7
                    json_end = response_content.rfind('```')
                    if json_end > json_start:
                        response_content = response_content[json_start:json_end].strip()
                elif response_content.strip().startswith('```'):
                    # Handle generic code blocks
                    lines = response_content.strip().split('\n')
                    if len(lines) > 2:
                        response_content = '\n'.join(lines[1:-1])
                
                result = json.loads(response_content)
                return result if isinstance(result, list) else []
            except json.JSONDecodeError as json_err:
                logger.warning(f"Invalid JSON response from OpenAI: {response_content[:100]}...")
                return self._keyword_extract_training(full_text)
            
        except Exception as e:
            logger.error(f"Error in training analysis: {str(e)}")
            return self._keyword_extract_training(full_text)
    
    def _analyze_feedback_motivation(self, full_text: str, sections: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Extract feedback and motivation insights."""
        if not self.client:
            return self._keyword_extract_feedback(full_text)
        
        try:
            prompt = f"""
Extract feedback and motivation insights from this IDP content:

{full_text[:3000]}

Find information about:
- Job satisfaction levels and changes
- Attitude towards the company
- Stress, burnout, or overload mentions
- Motivation factors
- Comfort/discomfort issues
- Work-life balance concerns

Return as JSON array of objects with:
- "category": satisfaction/motivation/concern/etc
- "content": the specific insight
- "sentiment": positive/negative/neutral
- "context": surrounding text
"""
            
            response = self.client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": "Extract feedback and motivation insights from HR documents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            response_content = response.choices[0].message.content
            if not response_content or not response_content.strip():
                logger.warning("Empty response from OpenAI for feedback analysis")
                return self._keyword_extract_feedback(full_text)
            
            try:
                # Handle markdown code blocks
                if response_content.strip().startswith('```json'):
                    # Extract JSON from markdown code block
                    json_start = response_content.find('```json') + 7
                    json_end = response_content.rfind('```')
                    if json_end > json_start:
                        response_content = response_content[json_start:json_end].strip()
                elif response_content.strip().startswith('```'):
                    # Handle generic code blocks
                    lines = response_content.strip().split('\n')
                    if len(lines) > 2:
                        response_content = '\n'.join(lines[1:-1])
                
                result = json.loads(response_content)
                return result if isinstance(result, list) else []
            except json.JSONDecodeError as json_err:
                logger.warning(f"Invalid JSON response from OpenAI: {response_content[:100]}...")
                return self._keyword_extract_feedback(full_text)
            
        except Exception as e:
            logger.error(f"Error in feedback analysis: {str(e)}")
            return self._keyword_extract_feedback(full_text)
    
    def _analyze_hr_processes(self, full_text: str, sections: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Extract HR processes and proposals."""
        try:
            # Look for interview, assessment, and process improvement mentions
            hr_items = []
            
            patterns = {
                'interview_participation': [
                    r'собеседован\w*', r'interview\w*', r'участ\w* в собеседовани\w*',
                    r'проводить\s+собеседовани\w*', r'conduct\s+interview\w*'
                ],
                'assessment_participation': [
                    r'ассессмент\w*', r'assessment\w*', r'техническ\w*\s+оценк\w*',
                    r'technical\s+assessment\w*'
                ],
                'process_improvement': [
                    r'предложени\w*\s+по\s+улучшени\w*', r'improvement\s+suggest\w*',
                    r'процесс\w*\s+улучшени\w*', r'process\s+improvement\w*'
                ],
                'hr_mentions': [
                    r'HR\s+\w*', r'отдел\s+кадр\w*', r'обсудить\s+с\s+\w*\s*(Марией|Тимофеем)',
                    r'связаться\s+с\s+HR'
                ]
            }
            
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.finditer(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        start = max(0, match.start() - 50)
                        end = min(len(full_text), match.end() + 50)
                        context = full_text[start:end].strip()
                        
                        hr_items.append({
                            'category': category,
                            'content': match.group(),
                            'status': 'mentioned',
                            'context': context
                        })
            
            return hr_items
            
        except Exception as e:
            logger.error(f"Error in HR processes analysis: {str(e)}")
            return []
    
    def _analyze_community_engagement(self, full_text: str, sections: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Extract community engagement information."""
        try:
            community_items = []
            
            patterns = {
                'forum_participation': [
                    r'VVT\s+Forum', r'форум\w*', r'выступ\w*\s+на\s+форум\w*',
                    r'участ\w*\s+в\s+форум\w*'
                ],
                'meetup_participation': [
                    r'митап\w*', r'meetup\w*', r'мастер-класс\w*', r'workshop\w*'
                ],
                'community_proposals': [
                    r'предложени\w*\s+по\s+комьюнити', r'community\s+suggest\w*',
                    r'улучшени\w*\s+сообществ\w*'
                ],
                'viva_engage': [
                    r'Viva\s+Engage', r'публикаци\w*\s+в\s+сообществ\w*',
                    r'posting\s+in\s+communities'
                ]
            }
            
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.finditer(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        start = max(0, match.start() - 50)
                        end = min(len(full_text), match.end() + 50)
                        context = full_text[start:end].strip()
                        
                        community_items.append({
                            'category': category,
                            'content': match.group(),
                            'status': 'mentioned',
                            'context': context
                        })
            
            return community_items
            
        except Exception as e:
            logger.error(f"Error in community analysis: {str(e)}")
            return []
    
    def _analyze_location_relocation(self, full_text: str, sections: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Extract location and relocation information."""
        try:
            location_items = []
            
            patterns = {
                'current_location': [
                    r'текущ\w*\s+местоположени\w*', r'current\s+location',
                    r'город\s+\w+', r'city\s+\w+', r'страна\s+\w+'
                ],
                'relocation_plans': [
                    r'релокаци\w*', r'relocation', r'план\w*\s+на\s+переезд',
                    r'планиру\w*\s+релокаци\w*', r'planning\s+to\s+relocate'
                ],
                'location_mentions': [
                    r'Алматы', r'Ташкент', r'Москва', r'Казахстан', r'Узбекистан',
                    r'Kazakhstan', r'Uzbekistan'
                ]
            }
            
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    matches = re.finditer(pattern, full_text, re.IGNORECASE)
                    for match in matches:
                        start = max(0, match.start() - 30)
                        end = min(len(full_text), match.end() + 30)
                        context = full_text[start:end].strip()
                        
                        location_items.append({
                            'category': category,
                            'content': match.group(),
                            'status': 'mentioned',
                            'context': context
                        })
            
            return location_items
            
        except Exception as e:
            logger.error(f"Error in location analysis: {str(e)}")
            return []
    
    def _analyze_risks_concerns(self, full_text: str, sections: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """Extract risks and concerns."""
        try:
            risk_items = []
            
            risk_indicators = [
                r'усталость', r'выгорани\w*', r'перегрузк\w*', r'стресс',
                r'дискомфорт', r'проблем\w*', r'недовольств\w*',
                r'burnout', r'stress', r'overwhelm\w*', r'concern\w*',
                r'uncomfortable', r'dissatisf\w*'
            ]
            
            for pattern in risk_indicators:
                matches = re.finditer(pattern, full_text, re.IGNORECASE)
                for match in matches:
                    start = max(0, match.start() - 100)
                    end = min(len(full_text), match.end() + 100)
                    context = full_text[start:end].strip()
                    
                    risk_items.append({
                        'category': 'risk_concern',
                        'content': match.group(),
                        'severity': 'medium',  # Could be enhanced with sentiment analysis
                        'context': context
                    })
            
            return risk_items
            
        except Exception as e:
            logger.error(f"Error in risk analysis: {str(e)}")
            return []
    
    def _parse_meeting_analysis_response(self, response_text: str) -> MeetingAnalysis:
        """Parse AI response into MeetingAnalysis object."""
        try:
            # Handle markdown code blocks first
            clean_text = response_text
            if response_text.strip().startswith('```json'):
                # Extract JSON from markdown code block
                json_start = response_text.find('```json') + 7
                json_end = response_text.rfind('```')
                if json_end > json_start:
                    clean_text = response_text[json_start:json_end].strip()
            elif response_text.strip().startswith('```'):
                # Handle generic code blocks
                lines = response_text.strip().split('\n')
                if len(lines) > 2:
                    clean_text = '\n'.join(lines[1:-1])
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', clean_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return MeetingAnalysis(**data)
            else:
                # Fallback parsing
                return MeetingAnalysis(
                    meeting_occurred=False,
                    confidence_score=0.5,
                    evidence=["Could not parse AI response"],
                    requires_hr_attention=True
                )
        except Exception as e:
            logger.error(f"Error parsing meeting analysis response: {str(e)}")
            return MeetingAnalysis(
                meeting_occurred=False,
                confidence_score=0.3,
                evidence=[f"Parse error: {str(e)}"],
                requires_hr_attention=True
            )
    
    def _fallback_meeting_analysis(self, document_data: Dict[str, Any]) -> MeetingAnalysis:
        """Fallback meeting analysis when AI is not available."""
        sections = document_data.get('sections', {})
        meeting_sections = document_data.get('meeting_sections', [])
        
        # Simple heuristic: if meeting sections have substantial content
        meeting_content_found = False
        evidence = []
        
        for section_name in meeting_sections:
            if section_name in sections:
                section_content = ' '.join(sections[section_name])
                if len(section_content.strip()) > 50:  # Arbitrary threshold
                    meeting_content_found = True
                    evidence.append(f"Content found in {section_name}")
        
        return MeetingAnalysis(
            meeting_occurred=meeting_content_found,
            confidence_score=0.6 if meeting_content_found else 0.7,
            evidence=evidence,
            requires_hr_attention=not meeting_content_found
        )
    
    def _fallback_information_extraction(self, document_data: Dict[str, Any]) -> ExtractedInformation:
        """Fallback information extraction using keyword matching."""
        full_text = document_data.get('full_text', '')
        
        return ExtractedInformation(
            training_development=self._keyword_extract_training(full_text),
            feedback_motivation=self._keyword_extract_feedback(full_text),
            hr_processes=self._analyze_hr_processes(full_text, {}),
            community_engagement=self._analyze_community_engagement(full_text, {}),
            location_relocation=self._analyze_location_relocation(full_text, {}),
            risks_concerns=self._analyze_risks_concerns(full_text, {})
        )
    
    def _keyword_extract_training(self, text: str) -> List[Dict[str, str]]:
        """Extract training information using keyword matching."""
        training_items = []
        training_keywords = settings.training_keywords
        
        for keyword in training_keywords:
            matches = re.finditer(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                training_items.append({
                    'category': 'training',
                    'content': keyword,
                    'status': 'mentioned',
                    'context': context
                })
        
        return training_items
    
    def _keyword_extract_feedback(self, text: str) -> List[Dict[str, str]]:
        """Extract feedback information using keyword matching."""
        feedback_items = []
        feedback_keywords = settings.feedback_keywords
        
        for keyword in feedback_keywords:
            matches = re.finditer(rf'\b{re.escape(keyword)}\b', text, re.IGNORECASE)
            for match in matches:
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                feedback_items.append({
                    'category': 'feedback',
                    'content': keyword,
                    'sentiment': 'neutral',
                    'context': context
                })
        
        return feedback_items