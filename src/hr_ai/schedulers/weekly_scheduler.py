"""
Scheduler for automated weekly analysis of IDP documents.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from config.settings import settings
from ..analyzers.hr_analyzer import HRAnalyzer
from ..notifications.notifier import NotificationManager
from ..models.database import Base, AnalysisReport

logger = logging.getLogger(__name__)

class WeeklyScheduler:
    """Scheduler for automated weekly IDP analysis."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.hr_analyzer = HRAnalyzer()
        self.notification_manager = NotificationManager()
        
        # Database setup for storing reports
        self.engine = create_engine(settings.database_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self._setup_scheduled_jobs()
    
    def _setup_scheduled_jobs(self):
        """Set up scheduled jobs based on configuration."""
        # Weekly analysis job - default Monday at 9 AM
        cron_expression = settings.analysis_schedule_cron
        try:
            # Parse cron: "minute hour day month day_of_week"
            parts = cron_expression.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                
                self.scheduler.add_job(
                    self.run_weekly_analysis,
                    CronTrigger(
                        minute=int(minute),
                        hour=int(hour),
                        day=day if day != '*' else None,
                        month=month if month != '*' else None,
                        day_of_week=day_of_week if day_of_week != '*' else None
                    ),
                    id='weekly_analysis',
                    name='Weekly IDP Analysis',
                    max_instances=1,
                    coalesce=True
                )
                logger.info(f"Scheduled weekly analysis: {cron_expression}")
            else:
                logger.error(f"Invalid cron expression: {cron_expression}")
                
        except Exception as e:
            logger.error(f"Error setting up scheduled job: {str(e)}")
    
    async def run_weekly_analysis(self):
        """Run the weekly analysis process."""
        try:
            logger.info("Starting weekly IDP analysis")
            
            # Calculate analysis period (last 7 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # Run analysis on recent documents
            analysis_results = self.hr_analyzer.analyze_recent_documents(days=7)
            
            # Generate comprehensive report
            report_data = await self._generate_weekly_report(analysis_results, start_date, end_date)
            
            # Store report in database
            report_record = self._store_analysis_report(report_data, start_date, end_date)
            
            # Send notifications
            await self._send_notifications(report_data, report_record)
            
            logger.info(f"Weekly analysis completed. Report ID: {report_record.id}")
            
        except Exception as e:
            logger.error(f"Error in weekly analysis: {str(e)}")
            # Send error notification to admins
            await self._send_error_notification(str(e))
    
    async def _generate_weekly_report(self, analysis_results: Dict[str, Any], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive weekly report."""
        
        # Get additional analysis summaries
        summary = self.hr_analyzer.get_analysis_summary(days=7)
        
        # Prepare notification messages
        notifications = []
        
        # Missed meetings notifications
        for case in analysis_results.get('hr_attention_required', []):
            employee = case.get('employee', 'Unknown')
            reason = case.get('reason', 'Unknown reason')
            confidence = case.get('confidence', 0)
            
            if 'missed meeting' in reason.lower():
                notifications.append({
                    'type': 'missed_meeting',
                    'message': f"У сотрудника {employee} возможно не состоялась встреча. Уверенность: {confidence:.1%}",
                    'priority': 'high' if confidence > 0.8 else 'medium',
                    'employee': employee
                })
        
        # Training and development insights
        for training_item in summary['key_insights'].get('training_requests', []):
            employee = training_item.get('employee')
            content = training_item.get('content')
            category = training_item.get('category', 'обучение')
            
            if 'выступ' in content or 'митап' in content:
                notifications.append({
                    'type': 'training_interest',
                    'message': f"Сотрудник {employee} выразил желание участвовать в {category}: {content}",
                    'priority': 'medium',
                    'employee': employee
                })
        
        # Feedback concerns
        for concern in summary['key_insights'].get('feedback_concerns', []):
            employee = concern.get('employee')
            content = concern.get('content')
            
            if any(keyword in content.lower() for keyword in ['усталость', 'выгорание', 'перегрузка']):
                notifications.append({
                    'type': 'burnout_risk',
                    'message': f"В отзыве сотрудника {employee} отмечено: '{content}' — возможный сигнал выгорания",
                    'priority': 'high',
                    'employee': employee
                })
        
        # Relocation plans
        for relocation in summary['key_insights'].get('relocation_plans', []):
            employee = relocation.get('employee')
            content = relocation.get('content')
            
            notifications.append({
                'type': 'relocation',
                'message': f"Сотрудник {employee} упомянул о релокации: {content}",
                'priority': 'medium',
                'employee': employee
            })
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'description': f"Неделя {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
            },
            'statistics': {
                'documents_analyzed': analysis_results.get('total_files', 0),
                'documents_processed': analysis_results.get('processed', 0),
                'meetings_detected': analysis_results.get('meetings_detected', 0),
                'meetings_missed': analysis_results.get('meetings_missed', 0),
                'employees_analyzed': len(summary.get('employees', [])),
                'hr_attention_cases': len(analysis_results.get('hr_attention_required', []))
            },
            'notifications': notifications,
            'summary_text': self._generate_summary_text(analysis_results, summary, notifications),
            'detailed_insights': {
                'training_development': summary['key_insights'].get('training_requests', []),
                'feedback_concerns': summary['key_insights'].get('feedback_concerns', []),
                'relocation_plans': summary['key_insights'].get('relocation_plans', [])
            }
        }
        
        return report
    
    def _generate_summary_text(self, analysis_results: Dict[str, Any], summary: Dict[str, Any], notifications: list) -> str:
        """Generate human-readable summary text."""
        stats = analysis_results
        
        summary_parts = [
            f"📊 Еженедельный анализ ПИР ({datetime.now().strftime('%d.%m.%Y')})",
            "",
            f"📋 Обработано документов: {stats.get('processed', 0)} из {stats.get('total_files', 0)}",
            f"👥 Сотрудников проанализировано: {len(summary.get('employees', []))}",
            f"✅ Встреч состоялось: {stats.get('meetings_detected', 0)}",
            f"❌ Встреч пропущено: {stats.get('meetings_missed', 0)}",
            f"⚠️ Требует внимания HR: {len(stats.get('hr_attention_required', []))}"
        ]
        
        if notifications:
            summary_parts.extend([
                "",
                "🔍 Ключевые наблюдения:"
            ])
            
            # Group notifications by priority
            high_priority = [n for n in notifications if n.get('priority') == 'high']
            medium_priority = [n for n in notifications if n.get('priority') == 'medium']
            
            if high_priority:
                summary_parts.append("🚨 Высокий приоритет:")
                for notif in high_priority[:5]:  # Limit to 5
                    summary_parts.append(f"  • {notif['message']}")
            
            if medium_priority:
                summary_parts.append("📋 Средний приоритет:")
                for notif in medium_priority[:5]:  # Limit to 5
                    summary_parts.append(f"  • {notif['message']}")
        
        return "\n".join(summary_parts)
    
    def _store_analysis_report(self, report_data: Dict[str, Any], start_date: datetime, end_date: datetime) -> AnalysisReport:
        """Store analysis report in database."""
        try:
            report = AnalysisReport(
                period_start=start_date,
                period_end=end_date,
                summary=report_data['summary_text'],
                documents_analyzed=report_data['statistics']['documents_analyzed'],
                meetings_detected=report_data['statistics']['meetings_detected'],
                meetings_missed=report_data['statistics']['meetings_missed'],
                hr_attention_required=[n for n in report_data['notifications'] if n.get('priority') == 'high'],
                key_insights=report_data['detailed_insights']
            )
            
            self.session.add(report)
            self.session.commit()
            
            logger.info(f"Stored analysis report for period {start_date} - {end_date}")
            return report
            
        except Exception as e:
            logger.error(f"Error storing analysis report: {str(e)}")
            self.session.rollback()
            raise
    
    async def _send_notifications(self, report_data: Dict[str, Any], report_record: AnalysisReport):
        """Send notifications to HR team."""
        try:
            summary_text = report_data['summary_text']
            
            # Send to Teams if configured
            if settings.enable_teams_notifications and settings.teams_webhook_url:
                teams_sent = await self.notification_manager.send_teams_notification(
                    title="Еженедельный анализ ПИР",
                    summary=summary_text,
                    report_data=report_data
                )
                
                if teams_sent:
                    report_record.sent_to_teams = True
                    report_record.teams_sent_at = datetime.now()
            
            # Send email if configured
            if settings.enable_email_notifications and settings.hr_email_recipients:
                email_sent = await self.notification_manager.send_email_notification(
                    subject=f"HR AI: Еженедельный анализ ПИР - {datetime.now().strftime('%d.%m.%Y')}",
                    body=summary_text,
                    recipients=settings.hr_email_recipients,
                    report_data=report_data
                )
                
                if email_sent:
                    report_record.sent_to_email = True
                    report_record.email_sent_at = datetime.now()
            
            self.session.commit()
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
    
    async def _send_error_notification(self, error_message: str):
        """Send error notification to administrators."""
        try:
            error_summary = f"❌ Ошибка в еженедельном анализе ПИР\n\nВремя: {datetime.now().strftime('%d.%m.%Y %H:%M')}\nОшибка: {error_message}"
            
            if settings.enable_teams_notifications:
                await self.notification_manager.send_teams_notification(
                    title="Ошибка HR AI системы",
                    summary=error_summary,
                    report_data={'error': True, 'message': error_message}
                )
            
            if settings.enable_email_notifications:
                await self.notification_manager.send_email_notification(
                    subject="HR AI: Ошибка системы",
                    body=error_summary,
                    recipients=settings.hr_email_recipients
                )
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
    
    def start(self):
        """Start the scheduler."""
        try:
            self.scheduler.start()
            logger.info("Weekly scheduler started")
        except Exception as e:
            logger.error(f"Error starting scheduler: {str(e)}")
    
    def stop(self):
        """Stop the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("Weekly scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
    
    def run_manual_analysis(self) -> Dict[str, Any]:
        """Run analysis manually (for testing or immediate execution)."""
        try:
            logger.info("Running manual analysis")
            analysis_results = self.hr_analyzer.analyze_recent_documents(days=7)
            return analysis_results
        except Exception as e:
            logger.error(f"Error in manual analysis: {str(e)}")
            return {'error': str(e)}
    
    def close(self):
        """Clean up resources."""
        self.hr_analyzer.close()
        self.session.close()