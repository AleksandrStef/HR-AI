"""
Recommendation engine for generating development suggestions based on IDP analysis.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
import logging

import openai
from openai import OpenAI
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func

from config.settings import settings
from ..models.database import Document, ExtractedInformation, MeetingAnalysis

logger = logging.getLogger(__name__)

class RecommendationEngine:
    """Generate recommendations for employee development and company improvements."""
    
    def __init__(self):
        self.engine = create_engine(settings.database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        if settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        else:
            self.client = None
    
    def generate_employee_recommendations(self, employee_name: str, months_back: int = 12) -> Dict[str, Any]:
        """
        Generate personalized development recommendations for an employee.
        
        Args:
            employee_name: Name of the employee
            months_back: How many months of data to analyze
            
        Returns:
            Personalized recommendations
        """
        try:
            # Get employee's historical data
            cutoff_date = datetime.now() - timedelta(days=months_back * 30)
            
            documents = self.session.query(Document, ExtractedInformation).outerjoin(
                ExtractedInformation, Document.id == ExtractedInformation.document_id
            ).filter(
                Document.employee_name.ilike(f"%{employee_name}%"),
                Document.parsed_at >= cutoff_date
            ).all()
            
            if not documents:
                return {
                    'employee_name': employee_name,
                    'recommendations': [],
                    'message': 'Недостаточно данных для анализа'
                }
            
            # Analyze patterns
            patterns = self._analyze_employee_patterns(documents)
            
            # Generate recommendations
            recommendations = self._generate_individual_recommendations(patterns, employee_name)
            
            return {
                'employee_name': employee_name,
                'analysis_period_months': months_back,
                'data_points': len(documents),
                'patterns': patterns,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating employee recommendations: {str(e)}")
            return {
                'employee_name': employee_name,
                'error': str(e),
                'recommendations': []
            }
    
    def generate_company_insights(self, months_back: int = 6) -> Dict[str, Any]:
        """
        Generate company-wide insights and improvement recommendations.
        
        Args:
            months_back: How many months of data to analyze
            
        Returns:
            Company-wide insights and recommendations
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=months_back * 30)
            
            # Get all recent data
            documents = self.session.query(Document, ExtractedInformation, MeetingAnalysis).outerjoin(
                ExtractedInformation, Document.id == ExtractedInformation.document_id
            ).outerjoin(
                MeetingAnalysis, Document.id == MeetingAnalysis.document_id
            ).filter(Document.parsed_at >= cutoff_date).all()
            
            if not documents:
                return {
                    'insights': [],
                    'recommendations': [],
                    'message': 'Недостаточно данных для анализа'
                }
            
            # Analyze company-wide patterns
            insights = self._analyze_company_patterns(documents)
            
            # Generate system recommendations
            recommendations = self._generate_system_recommendations(insights)
            
            return {
                'analysis_period_months': months_back,
                'total_employees': len(set(doc.employee_name for doc, _, _ in documents)),
                'total_documents': len(documents),
                'insights': insights,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating company insights: {str(e)}")
            return {
                'error': str(e),
                'insights': [],
                'recommendations': []
            }
    
    def _analyze_employee_patterns(self, documents: List[Tuple]) -> Dict[str, Any]:
        """Analyze patterns for a specific employee."""
        patterns = {
            'training_interests': [],
            'consistent_themes': [],
            'progress_indicators': [],
            'risk_factors': [],
            'meeting_consistency': 0,
            'growth_areas': []
        }
        
        training_items = []
        feedback_items = []
        meeting_consistency = []
        
        for doc, extracted_info in documents:
            if extracted_info:
                # Collect training interests
                if extracted_info.training_development:
                    training_items.extend(extracted_info.training_development)
                
                # Collect feedback patterns
                if extracted_info.feedback_motivation:
                    feedback_items.extend(extracted_info.feedback_motivation)
                
                # Check for risk indicators
                if extracted_info.risks_concerns:
                    patterns['risk_factors'].extend([
                        item.get('content', '') for item in extracted_info.risks_concerns
                    ])
            
            # Meeting consistency (you'd need to add this analysis)
            # This is a simplified version
            meeting_consistency.append(1 if 'meeting occurred' in str(doc.sections) else 0)
        
        # Analyze training patterns
        if training_items:
            categories = [item.get('category', '') for item in training_items]
            category_counts = Counter(categories)
            patterns['training_interests'] = [
                {'category': cat, 'frequency': count} 
                for cat, count in category_counts.most_common(5)
            ]
        
        # Analyze feedback themes
        if feedback_items:
            # Simple keyword analysis for themes
            all_feedback = ' '.join([item.get('content', '') for item in feedback_items])
            patterns['consistent_themes'] = self._extract_themes(all_feedback)
        
        # Meeting consistency score
        if meeting_consistency:
            patterns['meeting_consistency'] = sum(meeting_consistency) / len(meeting_consistency)
        
        return patterns
    
    def _analyze_company_patterns(self, documents: List[Tuple]) -> Dict[str, Any]:
        """Analyze company-wide patterns."""
        insights = {
            'common_training_requests': [],
            'recurring_feedback_themes': [],
            'meeting_compliance': 0,
            'risk_patterns': [],
            'relocation_trends': [],
            'hr_process_improvements': []
        }
        
        all_training = []
        all_feedback = []
        all_risks = []
        all_relocations = []
        all_hr_processes = []
        meeting_data = []
        
        for doc, extracted_info, meeting_analysis in documents:
            if extracted_info:
                if extracted_info.training_development:
                    all_training.extend(extracted_info.training_development)
                if extracted_info.feedback_motivation:
                    all_feedback.extend(extracted_info.feedback_motivation)
                if extracted_info.risks_concerns:
                    all_risks.extend(extracted_info.risks_concerns)
                if extracted_info.location_relocation:
                    all_relocations.extend(extracted_info.location_relocation)
                if extracted_info.hr_processes:
                    all_hr_processes.extend(extracted_info.hr_processes)
            
            if meeting_analysis:
                meeting_data.append(meeting_analysis.meeting_occurred)
        
        # Analyze training requests
        if all_training:
            training_categories = [item.get('category', 'unknown') for item in all_training]
            category_counts = Counter(training_categories)
            insights['common_training_requests'] = [
                {'category': cat, 'requests': count}
                for cat, count in category_counts.most_common(10)
            ]
        
        # Analyze feedback themes
        if all_feedback:
            negative_feedback = [
                item for item in all_feedback 
                if item.get('sentiment') == 'negative'
            ]
            if negative_feedback:
                insights['recurring_feedback_themes'] = self._extract_themes(
                    ' '.join([item.get('content', '') for item in negative_feedback])
                )
        
        # Meeting compliance
        if meeting_data:
            insights['meeting_compliance'] = sum(meeting_data) / len(meeting_data)
        
        # Risk patterns
        if all_risks:
            risk_keywords = []
            for risk in all_risks:
                risk_keywords.extend(risk.get('content', '').lower().split())
            risk_counter = Counter(risk_keywords)
            insights['risk_patterns'] = [
                {'keyword': word, 'frequency': count}
                for word, count in risk_counter.most_common(10)
                if len(word) > 3  # Filter short words
            ]
        
        # Relocation trends
        if all_relocations:
            locations = []
            for reloc in all_relocations:
                content = reloc.get('content', '').lower()
                # Extract location names (simplified)
                if 'алматы' in content:
                    locations.append('Алматы')
                elif 'ташкент' in content:
                    locations.append('Ташкент')
                elif 'москва' in content:
                    locations.append('Москва')
            
            location_counts = Counter(locations)
            insights['relocation_trends'] = [
                {'location': loc, 'mentions': count}
                for loc, count in location_counts.items()
            ]
        
        return insights
    
    def _generate_individual_recommendations(self, patterns: Dict[str, Any], employee_name: str) -> List[Dict[str, Any]]:
        """Generate personalized recommendations for an employee."""
        recommendations = []
        
        # Training recommendations
        training_interests = patterns.get('training_interests', [])
        if training_interests:
            top_interest = training_interests[0]
            recommendations.append({
                'type': 'training',
                'priority': 'high',
                'title': f"Развитие в области {top_interest['category']}",
                'description': f"Сотрудник проявил устойчивый интерес к {top_interest['category']}. Рекомендуется предложить дополнительные возможности обучения в этой области.",
                'action_items': [
                    f"Найти курсы или сертификацию по {top_interest['category']}",
                    "Рассмотреть участие в профильных конференциях",
                    "Предложить менторство или внутренние проекты"
                ]
            })
        
        # Meeting consistency recommendations
        meeting_consistency = patterns.get('meeting_consistency', 0)
        if meeting_consistency < 0.7:
            recommendations.append({
                'type': 'process',
                'priority': 'medium',
                'title': 'Улучшение регулярности встреч',
                'description': f"Регулярность встреч составляет {meeting_consistency:.1%}. Необходимо улучшить процесс планирования.",
                'action_items': [
                    "Обсудить с менеджером оптимальную частоту встреч",
                    "Установить регулярные напоминания",
                    "Рассмотреть изменение формата встреч"
                ]
            })
        
        # Risk factor recommendations
        risk_factors = patterns.get('risk_factors', [])
        if risk_factors:
            recommendations.append({
                'type': 'wellbeing',
                'priority': 'high',
                'title': 'Внимание к рискам выгорания',
                'description': "Обнаружены индикаторы возможных проблем с мотивацией или нагрузкой.",
                'action_items': [
                    "Провести детальную беседу о текущей нагрузке",
                    "Рассмотреть перераспределение задач",
                    "Предложить поддержку или отдых"
                ]
            })
        
        # Growth area recommendations
        consistent_themes = patterns.get('consistent_themes', [])
        if consistent_themes:
            recommendations.append({
                'type': 'development',
                'priority': 'medium',
                'title': 'Развитие выявленных интересов',
                'description': f"Выявлены устойчивые темы интереса: {', '.join(consistent_themes[:3])}",
                'action_items': [
                    "Создать план развития по выявленным направлениям",
                    "Найти внутренние возможности для применения навыков",
                    "Рассмотреть роль ментора для других сотрудников"
                ]
            })
        
        return recommendations
    
    def _generate_system_recommendations(self, insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate system-wide recommendations."""
        recommendations = []
        
        # Training program recommendations
        common_training = insights.get('common_training_requests', [])
        if common_training:
            top_requests = common_training[:3]
            recommendations.append({
                'type': 'training_program',
                'priority': 'high',
                'title': 'Запуск востребованных программ обучения',
                'description': f"Наиболее запрашиваемые направления: {', '.join([r['category'] for r in top_requests])}",
                'action_items': [
                    "Организовать внутренние воркшопы по популярным темам",
                    "Найти внешние курсы для групповой записи",
                    "Создать библиотеку обучающих материалов"
                ],
                'affected_employees': sum([r['requests'] for r in top_requests])
            })
        
        # Meeting process improvements
        meeting_compliance = insights.get('meeting_compliance', 0)
        if meeting_compliance < 0.8:
            recommendations.append({
                'type': 'process_improvement',
                'priority': 'medium',
                'title': 'Улучшение процесса проведения встреч',
                'description': f"Общая посещаемость встреч составляет {meeting_compliance:.1%}",
                'action_items': [
                    "Пересмотреть шаблоны и процедуры встреч",
                    "Обучить менеджеров эффективному планированию",
                    "Внедрить напоминания и трекинг встреч"
                ]
            })
        
        # Risk management recommendations
        risk_patterns = insights.get('risk_patterns', [])
        if risk_patterns:
            high_risk_words = [p['keyword'] for p in risk_patterns if p['frequency'] > 2]
            if high_risk_words:
                recommendations.append({
                    'type': 'risk_management',
                    'priority': 'high',
                    'title': 'Внимание к рискам выгорания сотрудников',
                    'description': f"Часто упоминаемые проблемы: {', '.join(high_risk_words[:5])}",
                    'action_items': [
                        "Провести опрос по нагрузке и удовлетворенности",
                        "Организовать сессии по управлению стрессом",
                        "Пересмотреть распределение задач в командах"
                    ]
                })
        
        # Relocation support recommendations
        relocation_trends = insights.get('relocation_trends', [])
        if relocation_trends:
            recommendations.append({
                'type': 'employee_support',
                'priority': 'medium',
                'title': 'Поддержка процессов релокации',
                'description': f"Планы релокации: {', '.join([f'{r[\"location\"]} ({r[\"mentions\"]} упоминаний)' for r in relocation_trends])}",
                'action_items': [
                    "Создать гид по релокации для популярных направлений",
                    "Установить контакты с HR в других офисах",
                    "Подготовить пакеты поддержки релокации"
                ]
            })
        
        return recommendations
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract common themes from text using simple keyword analysis."""
        # This is a simplified implementation
        # In a real system, you might use more sophisticated NLP
        
        keywords = {
            'обучение': ['обучение', 'курс', 'сертификат', 'тренинг'],
            'коммуникация': ['общение', 'коммуникация', 'обратная связь'],
            'процессы': ['процесс', 'workflow', 'автоматизация'],
            'нагрузка': ['нагрузка', 'перегрузка', 'усталость', 'время'],
            'команда': ['команда', 'коллектив', 'сотрудничество'],
            'развитие': ['развитие', 'рост', 'карьера', 'навыки']
        }
        
        text_lower = text.lower()
        found_themes = []
        
        for theme, theme_keywords in keywords.items():
            if any(keyword in text_lower for keyword in theme_keywords):
                found_themes.append(theme)
        
        return found_themes
    
    def get_recommendation_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """Get summary of recent recommendations and patterns."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Get recent documents
            documents = self.session.query(Document, ExtractedInformation).outerjoin(
                ExtractedInformation, Document.id == ExtractedInformation.document_id
            ).filter(Document.parsed_at >= cutoff_date).all()
            
            # Quick analysis
            employees_analyzed = set(doc.employee_name for doc, _ in documents)
            
            # Count different types of insights
            training_mentions = 0
            risk_mentions = 0
            relocation_mentions = 0
            
            for doc, extracted_info in documents:
                if extracted_info:
                    if extracted_info.training_development:
                        training_mentions += len(extracted_info.training_development)
                    if extracted_info.risks_concerns:
                        risk_mentions += len(extracted_info.risks_concerns)
                    if extracted_info.location_relocation:
                        relocation_mentions += len(extracted_info.location_relocation)
            
            return {
                'period_days': days_back,
                'employees_with_data': len(employees_analyzed),
                'total_documents': len(documents),
                'insights': {
                    'training_mentions': training_mentions,
                    'risk_indicators': risk_mentions,
                    'relocation_discussions': relocation_mentions
                },
                'top_employees_for_attention': list(employees_analyzed)[:10],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendation summary: {str(e)}")
            return {'error': str(e)}
    
    def close(self):
        """Close database session."""
        self.session.close()