"""
Query processing engine for answering HR questions about IDP data.
"""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

import openai
from openai import OpenAI
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, and_, or_

from config.settings import settings
from ..models.database import Document, ExtractedInformation, MeetingAnalysis, QueryLog

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Process natural language queries about HR data."""
    
    def __init__(self):
        self.engine = create_engine(settings.database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None
    
    async def process_query(self, query_text: str) -> Dict[str, Any]:
        """
        Process a natural language query and return structured results.
        
        Args:
            query_text: The HR specialist's question
            
        Returns:
            Structured response with data and summary
        """
        start_time = datetime.now()
        
        try:
            # Analyze query to understand intent and parameters
            query_analysis = await self._analyze_query(query_text)
            
            # Execute database search based on query analysis
            search_results = await self._execute_search(query_analysis)
            
            # Format results for display
            formatted_response = await self._format_response(query_analysis, search_results)
            
            # Log the query
            processing_time = (datetime.now() - start_time).total_seconds()
            self._log_query(query_text, query_analysis, formatted_response, processing_time)
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query': query_text,
                'results': [],
                'summary': f"Произошла ошибка при обработке запроса: {str(e)}"
            }
    
    async def _analyze_query(self, query_text: str) -> Dict[str, Any]:
        """Analyze query to extract intent and parameters."""
        
        # Default analysis structure
        analysis = {
            'intent': 'general',
            'categories': [],
            'time_period': None,
            'employee_names': [],
            'keywords': [],
            'confidence': 0.5
        }
        
        # Keyword-based intent detection
        query_lower = query_text.lower()
        logger.info(f"Analyzing query: '{query_text}' -> '{query_lower}'")
        
        # Training/development related
        if any(keyword in query_lower for keyword in ['обучение', 'training', 'сертификат', 'курс', 'митап', 'workshop']):
            analysis['intent'] = 'training'
            analysis['categories'].append('training_development')
        
        # Feedback/satisfaction related
        discomfort_keywords = ['удовлетворен', 'satisfaction', 'мотивация', 'выгорание', 'перегрузка', 
                               'дискомфорт', 'проблем', 'недовольств', 'стресс', 'комфорт', 'отношение', 
                               'нравится', 'не нравится', 'устраивает', 'не устраивает', 'вызывает',
                               'беспокоит', 'волнует', 'тревожит', 'расстраивает', 'огорчает']
        if any(keyword in query_lower for keyword in discomfort_keywords):
            analysis['intent'] = 'feedback'
            analysis['categories'].append('feedback_motivation')
            analysis['categories'].append('risks_concerns')
            logger.info(f"Detected feedback/discomfort query intent based on keywords: {[k for k in discomfort_keywords if k in query_lower]}")
        
        # Meeting related
        if any(keyword in query_lower for keyword in ['встреча', 'meeting', 'пропуск', 'missed', 'checkpoint']):
            analysis['intent'] = 'meetings'
            analysis['categories'].append('meetings')
        
        # Relocation related
        if any(keyword in query_lower for keyword in ['релокация', 'relocation', 'переезд', 'локация']):
            analysis['intent'] = 'relocation'
            analysis['categories'].append('location_relocation')
        
        # HR processes related
        if any(keyword in query_lower for keyword in ['собеседование', 'interview', 'процесс', 'предложение']):
            analysis['intent'] = 'hr_processes'
            analysis['categories'].append('hr_processes')
        
        # Extract time period
        analysis['time_period'] = self._extract_time_period(query_text)
        
        # Extract employee names (simple pattern matching)
        analysis['employee_names'] = self._extract_employee_names(query_text)
        
        # Extract key search terms
        analysis['keywords'] = self._extract_keywords(query_text)
        
        # If using AI, enhance analysis but preserve reliable keyword-based intent
        # TEMPORARILY DISABLED TO TEST KEYWORD-BASED ANALYSIS
        if False and settings.openai_api_key:
            try:
                # Store the reliable keyword-based intent
                reliable_intent = analysis['intent']
                reliable_categories = analysis['categories'].copy()
                
                enhanced_analysis = await self._ai_analyze_query(query_text, analysis)
                
                # Only use AI intent if keyword-based analysis was 'general'
                # This preserves reliable keyword matching for specific domains
                if reliable_intent != 'general':
                    enhanced_analysis['intent'] = reliable_intent
                    enhanced_analysis['categories'] = reliable_categories
                    logger.info(f"Preserving keyword-based intent '{reliable_intent}' over AI suggestion '{enhanced_analysis.get('intent', 'unknown')}'")
                
                analysis.update(enhanced_analysis)
            except Exception as e:
                logger.warning(f"AI query analysis failed: {str(e)}")
        
        return analysis
    
    async def _ai_analyze_query(self, query_text: str, base_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to enhance query analysis."""
        
        prompt = f"""
Analyze this HR query and extract structured information:

Query: "{query_text}"

Current analysis: {json.dumps(base_analysis, ensure_ascii=False)}

Please enhance the analysis by:
1. Confirming or correcting the intent classification
2. Identifying specific information being requested
3. Extracting any time constraints
4. Identifying key search terms

Respond in JSON format with:
{{
    "intent": "training/feedback/meetings/relocation/hr_processes/general",
    "categories": ["list of relevant categories"],
    "time_period_days": number or null,
    "specific_request": "what exactly is being asked",
    "search_strategy": "how to search the data",
    "confidence": float (0-1)
}}
"""
        
        if not self.client:
            return {}
            
        try:
            response = self.client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": "You are an HR AI assistant that analyzes queries about employee development plans."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            response_content = response.choices[0].message.content
            if not response_content or not response_content.strip():
                logger.warning("Empty response from OpenAI for query analysis")
                return {}
            
            # Handle markdown code blocks
            if response_content.strip().startswith('```json'):
                json_start = response_content.find('```json') + 7
                json_end = response_content.rfind('```')
                if json_end > json_start:
                    response_content = response_content[json_start:json_end].strip()
            elif response_content.strip().startswith('```'):
                lines = response_content.strip().split('\n')
                if len(lines) > 2:
                    response_content = '\n'.join(lines[1:-1])
            
            result = json.loads(response_content)
            return result
            
        except Exception as e:
            logger.error(f"AI query analysis error: {str(e)}")
            return {}
    
    def _extract_time_period(self, query_text: str) -> Optional[int]:
        """Extract time period in days from query text."""
        
        time_patterns = {
            r'за\s+последни[ехй]\s+(\d+)\s+месяц[аеов]*': lambda x: int(x) * 30,
            r'за\s+последни[ехй]\s+(\d+)\s+недел[иьяю]*': lambda x: int(x) * 7,
            r'за\s+последни[ехй]\s+(\d+)\s+дн[ейяь]*': lambda x: int(x),
            r'последни[ехй]\s+(\d+)\s+месяц[аеов]*': lambda x: int(x) * 30,
            r'последни[ехй]\s+(\d+)\s+недел[иьяю]*': lambda x: int(x) * 7,
            r'(\d+)\s+месяц[аеов]*': lambda x: int(x) * 30,
            r'(\d+)\s+недел[иьяю]*': lambda x: int(x) * 7,
            r'полгода': lambda x: 180,
            r'год': lambda x: 365
        }
        
        for pattern, converter in time_patterns.items():
            match = re.search(pattern, query_text.lower())
            if match:
                try:
                    if pattern in [r'полгода', r'год']:
                        return converter(None)
                    else:
                        return converter(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_employee_names(self, query_text: str) -> List[str]:
        """Extract potential employee names from query text."""
        # Simple pattern for Cyrillic names
        name_patterns = [
            r'[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+',  # Имя Фамилия
            r'[A-Z][a-z]+\s+[A-Z][a-z]+'        # Name Surname
        ]
        
        names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, query_text)
            names.extend(matches)
        
        return list(set(names))  # Remove duplicates
    
    def _extract_keywords(self, query_text: str) -> List[str]:
        """Extract key search terms from query text."""
        # Remove common words and extract meaningful terms
        stop_words = {
            'кто', 'что', 'где', 'когда', 'как', 'какие', 'который', 'которая', 'которые',
            'за', 'последние', 'месяца', 'недели', 'дней', 'года', 'сотрудники', 'сотрудник',
            'who', 'what', 'where', 'when', 'how', 'which', 'last', 'months', 'weeks', 'days',
            'years', 'employees', 'employee'
        }
        
        # Split query into words and filter
        words = re.findall(r'\w+', query_text.lower())
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        return keywords
    
    async def _execute_search(self, query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute database search based on query analysis."""
        
        results = []
        intent = query_analysis.get('intent', 'general')
        time_period = query_analysis.get('time_period')
        employee_names = query_analysis.get('employee_names', [])
        keywords = query_analysis.get('keywords', [])
        
        logger.info(f"Executing search - Intent: {intent}, Keywords: {keywords}, Categories: {query_analysis.get('categories', [])}")
        
        # Calculate date filter if time period specified
        date_filter = None
        if time_period:
            cutoff_date = datetime.now() - timedelta(days=time_period)
            date_filter = cutoff_date
        
        # Base query for documents
        query = self.session.query(Document, ExtractedInformation, MeetingAnalysis).outerjoin(
            ExtractedInformation, Document.id == ExtractedInformation.document_id
        ).outerjoin(
            MeetingAnalysis, Document.id == MeetingAnalysis.document_id
        )
        
        # Apply date filter
        if date_filter:
            query = query.filter(Document.parsed_at >= date_filter)
        
        # Apply employee name filter
        if employee_names:
            name_conditions = []
            for name in employee_names:
                name_conditions.append(Document.employee_name.ilike(f"%{name}%"))
            query = query.filter(or_(*name_conditions))
        
        # Execute query
        db_results = query.all()
        logger.info(f"Database query returned {len(db_results)} documents")
        
        # Process results based on intent
        if intent == 'training':
            results = self._process_training_results(db_results, keywords)
        elif intent == 'feedback':
            results = self._process_feedback_results(db_results, keywords)
        elif intent == 'meetings':
            results = self._process_meeting_results(db_results, keywords)
        elif intent == 'relocation':
            results = self._process_relocation_results(db_results, keywords)
        elif intent == 'hr_processes':
            results = self._process_hr_process_results(db_results, keywords)
        else:
            results = self._process_general_results(db_results, keywords)
        
        logger.info(f"Search execution completed - Found {len(results)} results")
        return results
    
    def _process_training_results(self, db_results: List[Tuple], keywords: List[str]) -> List[Dict[str, Any]]:
        """Process results for training-related queries."""
        results = []
        
        for doc, extracted_info, meeting_analysis in db_results:
            if extracted_info and extracted_info.training_development:
                for item in extracted_info.training_development:
                    # Filter by keywords if provided
                    if not keywords or any(keyword in item.get('content', '').lower() for keyword in keywords):
                        results.append({
                            'employee_name': doc.employee_name,
                            'date': doc.parsed_at.strftime('%d.%m.%Y'),
                            'type': 'Обучение и развитие',
                            'content': item.get('content', ''),
                            'category': item.get('category', ''),
                            'status': item.get('status', ''),
                            'context': item.get('context', ''),
                            'document_link': doc.file_path
                        })
        
        return results
    
    def _process_feedback_results(self, db_results: List[Tuple], keywords: List[str]) -> List[Dict[str, Any]]:
        """Process results for feedback-related queries."""
        results = []
        
        logger.info(f"Processing feedback results: {len(db_results)} documents, keywords: {keywords}")
        
        # Expanded search terms for better matching
        discomfort_terms = ['дискомфорт', 'проблем', 'недовольств', 'стресс', 'вызывает', 'беспокоит', 
                           'волнует', 'тревожит', 'расстраивает', 'огорчает', 'не нравится', 'не устраивает']
        
        for doc, extracted_info, meeting_analysis in db_results:
            # Check feedback_motivation data
            if extracted_info and extracted_info.feedback_motivation:
                logger.info(f"Found feedback data for {doc.employee_name}: {len(extracted_info.feedback_motivation)} items")
                for item in extracted_info.feedback_motivation:
                    # More flexible keyword matching
                    content_lower = item.get('content', '').lower()
                    context_lower = item.get('context', '').lower()
                    combined_text = f"{content_lower} {context_lower}"
                    
                    # Check for keyword matches or discomfort-related terms
                    keyword_match = not keywords or any(keyword.lower() in combined_text for keyword in keywords)
                    discomfort_match = any(term in combined_text for term in discomfort_terms)
                    
                    if keyword_match or discomfort_match:
                        results.append({
                            'employee_name': doc.employee_name,
                            'date': doc.parsed_at.strftime('%d.%m.%Y'),
                            'type': 'Обратная связь',
                            'content': item.get('content', ''),
                            'sentiment': item.get('sentiment', 'neutral'),
                            'context': item.get('context', ''),
                            'document_link': doc.file_path
                        })
            
            # Also check for risks/concerns
            if extracted_info and extracted_info.risks_concerns:
                logger.info(f"Found risks data for {doc.employee_name}: {len(extracted_info.risks_concerns)} items")
                for item in extracted_info.risks_concerns:
                    # More flexible keyword matching for risks
                    content_lower = item.get('content', '').lower()
                    context_lower = item.get('context', '').lower()
                    combined_text = f"{content_lower} {context_lower}"
                    
                    # Check for keyword matches or discomfort-related terms
                    keyword_match = not keywords or any(keyword.lower() in combined_text for keyword in keywords)
                    discomfort_match = any(term in combined_text for term in discomfort_terms)
                    
                    if keyword_match or discomfort_match:
                        results.append({
                            'employee_name': doc.employee_name,
                            'date': doc.parsed_at.strftime('%d.%m.%Y'),
                            'type': 'Риски и проблемы',
                            'content': item.get('content', ''),
                            'severity': item.get('severity', 'medium'),
                            'context': item.get('context', ''),
                            'document_link': doc.file_path
                        })
        
        logger.info(f"Feedback processing result: {len(results)} items found")
        return results
    
    def _process_meeting_results(self, db_results: List[Tuple], keywords: List[str]) -> List[Dict[str, Any]]:
        """Process results for meeting-related queries."""
        results = []
        
        for doc, extracted_info, meeting_analysis in db_results:
            if meeting_analysis:
                results.append({
                    'employee_name': doc.employee_name,
                    'date': doc.parsed_at.strftime('%d.%m.%Y'),
                    'type': f"Встреча - {meeting_analysis.meeting_type or 'не определен'}",
                    'content': 'Встреча состоялась' if meeting_analysis.meeting_occurred else 'Встреча не состоялась',
                    'confidence': f"{meeting_analysis.confidence_score:.1%}" if meeting_analysis.confidence_score else "N/A",
                    'requires_attention': 'Да' if meeting_analysis.requires_hr_attention else 'Нет',
                    'evidence': ', '.join(meeting_analysis.evidence or []),
                    'document_link': doc.file_path
                })
        
        return results
    
    def _process_relocation_results(self, db_results: List[Tuple], keywords: List[str]) -> List[Dict[str, Any]]:
        """Process results for relocation-related queries."""
        results = []
        
        for doc, extracted_info, meeting_analysis in db_results:
            if extracted_info and extracted_info.location_relocation:
                for item in extracted_info.location_relocation:
                    if not keywords or any(keyword in item.get('content', '').lower() for keyword in keywords):
                        results.append({
                            'employee_name': doc.employee_name,
                            'date': doc.parsed_at.strftime('%d.%m.%Y'),
                            'type': 'Локация/Релокация',
                            'content': item.get('content', ''),
                            'category': item.get('category', ''),
                            'context': item.get('context', ''),
                            'document_link': doc.file_path
                        })
        
        return results
    
    def _process_hr_process_results(self, db_results: List[Tuple], keywords: List[str]) -> List[Dict[str, Any]]:
        """Process results for HR process-related queries."""
        results = []
        
        for doc, extracted_info, meeting_analysis in db_results:
            if extracted_info and extracted_info.hr_processes:
                for item in extracted_info.hr_processes:
                    if not keywords or any(keyword in item.get('content', '').lower() for keyword in keywords):
                        results.append({
                            'employee_name': doc.employee_name,
                            'date': doc.parsed_at.strftime('%d.%m.%Y'),
                            'type': 'HR процессы',
                            'content': item.get('content', ''),
                            'category': item.get('category', ''),
                            'context': item.get('context', ''),
                            'document_link': doc.file_path
                        })
        
        return results
    
    def _process_general_results(self, db_results: List[Tuple], keywords: List[str]) -> List[Dict[str, Any]]:
        """Process results for general queries."""
        results = []
        
        logger.info(f"Processing general results: {len(db_results)} documents, keywords: {keywords}")
        
        for doc, extracted_info, meeting_analysis in db_results:
            # Search in extracted information first (more structured)
            found_in_extracted = False
            
            # Check all extracted categories for relevant content
            if extracted_info:
                categories_to_check = [
                    ('feedback_motivation', 'Обратная связь'),
                    ('risks_concerns', 'Риски и проблемы'),
                    ('training_development', 'Обучение и развитие'),
                    ('hr_processes', 'HR процессы'),
                    ('community_engagement', 'Участие в сообществе'),
                    ('location_relocation', 'Локация/Релокация')
                ]
                
                for category_name, category_label in categories_to_check:
                    category_data = getattr(extracted_info, category_name, [])
                    if category_data:
                        for item in category_data:
                            content = item.get('content', '').lower()
                            # Check if content matches keywords or discomfort-related terms
                            if (not keywords or any(keyword.lower() in content for keyword in keywords) or 
                                any(term in content for term in ['дискомфорт', 'проблем', 'недовольств', 'стресс', 'вызывает', 'не нравится'])):
                                
                                results.append({
                                    'employee_name': doc.employee_name,
                                    'date': doc.parsed_at.strftime('%d.%m.%Y'),
                                    'type': category_label,
                                    'content': item.get('content', ''),
                                    'context': item.get('context', ''),
                                    'category': item.get('category', ''),
                                    'document_link': doc.file_path
                                })
                                found_in_extracted = True
            
            # If nothing found in extracted data, search full document text
            if not found_in_extracted and doc.full_text:
                full_text = doc.full_text.lower()
                search_terms = keywords + ['дискомфорт', 'проблем', 'недовольств', 'стресс', 'вызывает']
                
                if any(term.lower() in full_text for term in search_terms):
                    # Find relevant sentences
                    sentences = doc.full_text.split('.')
                    relevant_sentences = []
                    
                    for sentence in sentences:
                        if any(term.lower() in sentence.lower() for term in search_terms):
                            relevant_sentences.append(sentence.strip())
                        if len(relevant_sentences) >= 3:  # Limit to first 3 matches
                            break
                    
                    if relevant_sentences:
                        results.append({
                            'employee_name': doc.employee_name,
                            'date': doc.parsed_at.strftime('%d.%m.%Y'),
                            'type': 'Общий поиск',
                            'content': ' '.join(relevant_sentences),
                            'document_link': doc.file_path
                        })
        
        logger.info(f"General processing result: {len(results)} items found")
        return results
    
    async def _format_response(self, query_analysis: Dict[str, Any], search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format search results into structured response."""
        
        # Create summary
        summary = self._create_result_summary(query_analysis, search_results)
        
        # Sort results by relevance (date, employee name)
        sorted_results = sorted(search_results, key=lambda x: (x.get('date', ''), x.get('employee_name', '')), reverse=True)
        
        response = {
            'success': True,
            'query_analysis': query_analysis,
            'total_results': len(sorted_results),
            'results': sorted_results,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }
        
        return response
    
    def _create_result_summary(self, query_analysis: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Create human-readable summary of results."""
        
        if not results:
            return "По вашему запросу не найдено результатов."
        
        intent = query_analysis.get('intent', 'general')
        total = len(results)
        
        # Count unique employees
        employees = set(r.get('employee_name', '') for r in results)
        employee_count = len(employees)
        
        summary_parts = [f"Найдено {total} результат(ов) по {employee_count} сотрудник(ам)."]
        
        if intent == 'training':
            categories = set(r.get('category', 'неизвестно') for r in results)
            summary_parts.append(f"Категории обучения: {', '.join(categories)}")
        
        elif intent == 'feedback':
            positive = len([r for r in results if r.get('sentiment') == 'positive'])
            negative = len([r for r in results if r.get('sentiment') == 'negative'])
            if negative > 0:
                summary_parts.append(f"Обнаружено {negative} негативных отзыва из {total}.")
        
        elif intent == 'meetings':
            missed = len([r for r in results if 'не состоялась' in r.get('content', '')])
            if missed > 0:
                summary_parts.append(f"Пропущенных встреч: {missed} из {total}.")
        
        # Add employee list if reasonable number
        if employee_count <= 10:
            employee_list = ', '.join(sorted(employees))
            summary_parts.append(f"Сотрудники: {employee_list}")
        
        return ' '.join(summary_parts)
    
    def _log_query(self, query_text: str, query_analysis: Dict[str, Any], response: Dict[str, Any], processing_time: float):
        """Log query for analytics and improvement."""
        try:
            log_entry = QueryLog(
                query_text=query_text,
                query_type=query_analysis.get('intent', 'general'),
                response_data=response,
                response_summary=response.get('summary', ''),
                documents_matched=response.get('total_results', 0),
                processing_time=processing_time
            )
            
            self.session.add(log_entry)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging query: {str(e)}")
            self.session.rollback()
    
    def get_popular_queries(self, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular queries from the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        logs = self.session.query(QueryLog).filter(
            QueryLog.queried_at >= cutoff_date
        ).order_by(QueryLog.queried_at.desc()).limit(limit * 2).all()
        
        # Group by similar queries (basic similarity)
        query_groups = {}
        for log in logs:
            # Simple grouping by first few words
            key_words = ' '.join(log.query_text.lower().split()[:3])
            if key_words not in query_groups:
                query_groups[key_words] = []
            query_groups[key_words].append(log)
        
        # Return most frequent groups
        popular = []
        for group_queries in sorted(query_groups.values(), key=len, reverse=True)[:limit]:
            popular.append({
                'query_example': group_queries[0].query_text,
                'count': len(group_queries),
                'query_type': group_queries[0].query_type,
                'avg_results': sum(q.documents_matched for q in group_queries) / len(group_queries)
            })
        
        return popular
    
    def close(self):
        """Close database session."""
        self.session.close()