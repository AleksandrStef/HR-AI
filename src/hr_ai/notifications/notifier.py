"""
Notification manager for sending alerts to HR team via Teams and email.
"""

import json
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
import logging
import asyncio
import aiohttp

import pymsteams

from config.settings import settings

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manager for sending notifications to HR team."""
    
    def __init__(self):
        self.teams_webhook_url = settings.teams_webhook_url
        self.email_config = {
            'smtp_server': settings.smtp_server,
            'smtp_port': settings.smtp_port,
            'username': settings.smtp_username,
            'password': settings.smtp_password
        }
    
    async def send_teams_notification(self, title: str, summary: str, report_data: Dict[str, Any] = None) -> bool:
        """
        Send notification to Microsoft Teams.
        
        Args:
            title: Notification title
            summary: Summary text
            report_data: Additional report data for formatting
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.teams_webhook_url:
            logger.warning("Teams webhook URL not configured")
            return False
        
        try:
            # Create Teams message
            teams_message = pymsteams.connectorcard(self.teams_webhook_url)
            teams_message.title(title)
            teams_message.summary(summary)
            
            # Format the main message
            formatted_summary = self._format_teams_message(summary, report_data)
            teams_message.text(formatted_summary)
            
            # Add color based on content
            if report_data and report_data.get('error'):
                teams_message.color("#FF0000")  # Red for errors
            elif report_data and any(n.get('priority') == 'high' for n in report_data.get('notifications', [])):
                teams_message.color("#FFA500")  # Orange for high priority
            else:
                teams_message.color("#00AA00")  # Green for normal
            
            # Add sections for different types of notifications
            if report_data and 'notifications' in report_data:
                self._add_teams_sections(teams_message, report_data)
            
            # Send the message
            teams_message.send()
            logger.info("Teams notification sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Teams notification: {str(e)}")
            return False
    
    def _format_teams_message(self, summary: str, report_data: Dict[str, Any] = None) -> str:
        """Format message text for Teams."""
        formatted_text = summary
        
        if report_data and 'period' in report_data:
            period_desc = report_data['period'].get('description', '')
            formatted_text = f"**{period_desc}**\n\n{formatted_text}"
        
        return formatted_text
    
    def _add_teams_sections(self, teams_message, report_data: Dict[str, Any]):
        """Add sections to Teams message based on report data."""
        notifications = report_data.get('notifications', [])
        
        # High priority notifications section
        high_priority = [n for n in notifications if n.get('priority') == 'high']
        if high_priority:
            section = pymsteams.cardsection()
            section.title("🚨 Требует немедленного внимания")
            facts = []
            for notif in high_priority[:5]:  # Limit to 5
                facts.append({
                    "name": notif.get('employee', 'Unknown'),
                    "value": notif.get('message', '')
                })
            for fact in facts:
                section.addFact(fact['name'], fact['value'])
            teams_message.addSection(section)
        
        # Training interests
        training_notifications = [n for n in notifications if n.get('type') == 'training_interest']
        if training_notifications:
            section = pymsteams.cardsection()
            section.title("📚 Инициативы по обучению")
            for notif in training_notifications[:3]:
                section.addFact(notif.get('employee', 'Unknown'), notif.get('message', ''))
            teams_message.addSection(section)
        
        # Relocation mentions
        relocation_notifications = [n for n in notifications if n.get('type') == 'relocation']
        if relocation_notifications:
            section = pymsteams.cardsection()
            section.title("🌍 Планы релокации")
            for notif in relocation_notifications:
                section.addFact(notif.get('employee', 'Unknown'), notif.get('message', ''))
            teams_message.addSection(section)
    
    async def send_email_notification(self, subject: str, body: str, recipients: List[str], report_data: Dict[str, Any] = None) -> bool:
        """
        Send email notification.
        
        Args:
            subject: Email subject
            body: Email body text
            recipients: List of recipient email addresses
            report_data: Additional report data for formatting
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not all([self.email_config['smtp_server'], self.email_config['username'], self.email_config['password']]):
            logger.warning("Email configuration incomplete")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.email_config['username']
            message["To"] = ", ".join(recipients)
            
            # Create HTML and text versions
            text_part = MIMEText(body, "plain", "utf-8")
            html_part = MIMEText(self._create_html_email(body, report_data), "html", "utf-8")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls(context=context)
                server.login(self.email_config['username'], self.email_config['password'])
                server.sendmail(self.email_config['username'], recipients, message.as_string())
            
            logger.info(f"Email notification sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    def _create_html_email(self, body: str, report_data: Dict[str, Any] = None) -> str:
        """Create HTML version of email."""
        html_body = body.replace('\n', '<br>')
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>HR AI Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 20px; }}
                .high-priority {{ background-color: #ffe6e6; padding: 10px; border-left: 4px solid #ff0000; }}
                .medium-priority {{ background-color: #fff3e0; padding: 10px; border-left: 4px solid #ff9800; }}
                .stats-table {{ border-collapse: collapse; width: 100%; }}
                .stats-table th, .stats-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .stats-table th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🤖 HR AI Система - Анализ ПИР</h2>
                <p><strong>Дата создания:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            </div>
            
            <div class="section">
                <pre>{html_body}</pre>
            </div>
        """
        
        if report_data:
            # Add statistics table
            stats = report_data.get('statistics', {})
            html_template += """
            <div class="section">
                <h3>📊 Статистика</h3>
                <table class="stats-table">
                    <tr><th>Показатель</th><th>Значение</th></tr>
            """
            
            stats_items = [
                ('Документов проанализировано', stats.get('documents_processed', 0)),
                ('Сотрудников', stats.get('employees_analyzed', 0)),
                ('Встреч состоялось', stats.get('meetings_detected', 0)),
                ('Встреч пропущено', stats.get('meetings_missed', 0)),
                ('Требует внимания HR', stats.get('hr_attention_cases', 0))
            ]
            
            for label, value in stats_items:
                html_template += f"<tr><td>{label}</td><td>{value}</td></tr>"
            
            html_template += "</table></div>"
            
            # Add high priority notifications
            notifications = report_data.get('notifications', [])
            high_priority = [n for n in notifications if n.get('priority') == 'high']
            
            if high_priority:
                html_template += """
                <div class="section">
                    <h3>🚨 Требует немедленного внимания</h3>
                """
                for notif in high_priority:
                    html_template += f"""
                    <div class="high-priority">
                        <strong>{notif.get('employee', 'Unknown')}:</strong> {notif.get('message', '')}
                    </div>
                    """
                html_template += "</div>"
        
        html_template += """
        </body>
        </html>
        """
        
        return html_template
    
    async def send_instant_alert(self, employee_name: str, alert_type: str, message: str, priority: str = "medium") -> bool:
        """
        Send instant alert for critical situations.
        
        Args:
            employee_name: Name of employee
            alert_type: Type of alert (missed_meeting, burnout_risk, etc.)
            message: Alert message
            priority: Priority level (high, medium, low)
            
        Returns:
            True if sent successfully
        """
        title = f"🚨 HR Alert: {employee_name}"
        
        # Determine urgency based on alert type and priority
        urgent_types = ['burnout_risk', 'negative_feedback', 'resignation_risk']
        is_urgent = alert_type in urgent_types or priority == 'high'
        
        if is_urgent:
            title = f"🚨 URGENT - " + title
        
        # Prepare alert data
        alert_data = {
            'notifications': [{
                'type': alert_type,
                'message': message,
                'priority': priority,
                'employee': employee_name,
                'timestamp': datetime.now().isoformat()
            }],
            'error': False
        }
        
        # Send to both Teams and email if urgent
        teams_sent = False
        email_sent = False
        
        if settings.enable_teams_notifications:
            teams_sent = await self.send_teams_notification(title, message, alert_data)
        
        if is_urgent and settings.enable_email_notifications:
            email_sent = await self.send_email_notification(
                subject=title,
                body=f"Сотрудник: {employee_name}\nТип: {alert_type}\nСообщение: {message}\n\nВремя: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                recipients=settings.hr_email_recipients,
                report_data=alert_data
            )
        
        return teams_sent or email_sent
    
    def test_connections(self) -> Dict[str, bool]:
        """
        Test notification connections.
        
        Returns:
            Dict with connection test results
        """
        results = {}
        
        # Test Teams webhook
        try:
            if self.teams_webhook_url:
                test_card = pymsteams.connectorcard(self.teams_webhook_url)
                test_card.title("HR AI Test")
                test_card.text("Это тестовое сообщение от HR AI системы")
                test_card.send()
                results['teams'] = True
            else:
                results['teams'] = False
                
        except Exception as e:
            logger.error(f"Teams connection test failed: {str(e)}")
            results['teams'] = False
        
        # Test email configuration
        try:
            if all([self.email_config['smtp_server'], self.email_config['username'], self.email_config['password']]):
                context = ssl.create_default_context()
                with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                    server.starttls(context=context)
                    server.login(self.email_config['username'], self.email_config['password'])
                    results['email'] = True
            else:
                results['email'] = False
                
        except Exception as e:
            logger.error(f"Email connection test failed: {str(e)}")
            results['email'] = False
        
        return results