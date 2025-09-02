"""
Main entry point for HR AI application.
"""

import sys
import os
import argparse
import asyncio
import logging
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hr_ai.api.web_app import main as run_web_app
from hr_ai.analyzers.hr_analyzer import HRAnalyzer
from hr_ai.schedulers.weekly_scheduler import WeeklyScheduler
from hr_ai.notifications.notifier import NotificationManager
from config.settings import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hr_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_analysis():
    """Run document analysis manually."""
    print("🔄 Запуск анализа документов...")
    
    analyzer = HRAnalyzer()
    try:
        results = analyzer.analyze_all_documents()
        
        print(f"✅ Анализ завершен!")
        print(f"📊 Обработано документов: {results['processed']}")
        print(f"👥 Встреч обнаружено: {results['meetings_detected']}")
        print(f"❌ Встреч пропущено: {results['meetings_missed']}")
        print(f"⚠️ Требует внимания HR: {len(results['hr_attention_required'])}")
        
        if results['hr_attention_required']:
            print("\n🚨 Случаи, требующие внимания HR:")
            for case in results['hr_attention_required']:
                print(f"  • {case['employee']}: {case['reason']}")
                
    except Exception as e:
        print(f"❌ Ошибка при анализе: {str(e)}")
    finally:
        analyzer.close()

def run_scheduler():
    """Run the scheduler in standalone mode."""
    print("⏰ Запуск планировщика...")
    
    scheduler = WeeklyScheduler()
    try:
        # Run manual analysis first
        results = scheduler.run_manual_analysis()
        print(f"📊 Результаты анализа: {results}")
        
        # Start scheduler
        scheduler.start()
        print("✅ Планировщик запущен. Нажмите Ctrl+C для остановки.")
        
        # Keep running
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            print("\n🛑 Остановка планировщика...")
            
    except Exception as e:
        print(f"❌ Ошибка планировщика: {str(e)}")
    finally:
        scheduler.stop()
        scheduler.close()

def test_notifications():
    """Test notification systems."""
    print("📨 Тестирование системы уведомлений...")
    
    notifier = NotificationManager()
    
    # Test connections
    results = notifier.test_connections()
    print(f"🔗 Результаты тестирования подключений:")
    print(f"  Teams: {'✅' if results.get('teams') else '❌'}")
    print(f"  Email: {'✅' if results.get('email') else '❌'}")
    
    # Send test notification
    if any(results.values()):
        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                notifier.send_instant_alert(
                    employee_name="Тестовый сотрудник",
                    alert_type="system_test",
                    message="Это тестовое уведомление от HR AI системы",
                    priority="medium"
                )
            )
            print(f"📤 Тестовое уведомление отправлено: {'✅' if success else '❌'}")
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления: {str(e)}")
    else:
        print("⚠️ Нет доступных каналов уведомлений")

def setup_environment():
    """Setup environment and check configuration."""
    print("🔧 Проверка конфигурации...")
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️ Файл .env не найден. Создаем из примера...")
        try:
            import shutil
            shutil.copy(".env.example", ".env")
            print("✅ Файл .env создан. Пожалуйста, заполните настройки.")
        except Exception as e:
            print(f"❌ Ошибка создания .env: {str(e)}")
            return False
    
    # Check docs directory
    docs_path = Path(settings.docs_directory)
    if not docs_path.exists():
        print(f"⚠️ Папка документов не найдена: {docs_path}")
        try:
            docs_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Создана папка документов: {docs_path}")
        except Exception as e:
            print(f"❌ Ошибка создания папки: {str(e)}")
            return False
    
    # Check for documents
    doc_files = list(docs_path.glob("*.docx")) + list(docs_path.glob("*.doc"))
    print(f"📄 Найдено документов: {len(doc_files)}")
    
    # Check AI configuration
    if settings.openai_api_key:
        print("🤖 OpenAI API ключ настроен ✅")
    else:
        print("⚠️ OpenAI API ключ не настроен - будет использоваться базовый анализ")
    
    # Check notification configuration
    notifications_configured = any([
        settings.enable_teams_notifications and settings.teams_webhook_url,
        settings.enable_email_notifications and settings.smtp_server
    ])
    
    if notifications_configured:
        print("📨 Уведомления настроены ✅")
    else:
        print("⚠️ Уведомления не настроены")
    
    print("✅ Проверка конфигурации завершена\n")
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="HR AI - Система анализа планов индивидуального развития")
    parser.add_argument("command", choices=["web", "analyze", "schedule", "test-notifications", "setup"], 
                       help="Команда для выполнения")
    parser.add_argument("--port", type=int, default=settings.port, help="Порт для веб-сервера")
    parser.add_argument("--host", default=settings.host, help="Хост для веб-сервера")
    
    args = parser.parse_args()
    
    print("🤖 HR AI - Система анализа планов индивидуального развития")
    print("=" * 60)
    
    if args.command == "setup":
        setup_environment()
        return
    
    if not setup_environment():
        print("❌ Ошибка конфигурации. Запустите: python main.py setup")
        return
    
    try:
        if args.command == "web":
            print(f"🌐 Запуск веб-сервера на http://{args.host}:{args.port}")
            # Update settings for command line args
            settings.host = args.host
            settings.port = args.port
            run_web_app()
            
        elif args.command == "analyze":
            run_analysis()
            
        elif args.command == "schedule":
            run_scheduler()
            
        elif args.command == "test-notifications":
            test_notifications()
            
    except KeyboardInterrupt:
        print("\n👋 Завершение работы...")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        print(f"❌ Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    main()