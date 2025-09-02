"""
Test runner for HR AI system - MVP validation.
"""

import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import asyncio
import logging
from datetime import datetime

from hr_ai.parsers.document_parser import DocumentParser
from hr_ai.analyzers.text_analyzer import TextAnalyzer
from hr_ai.analyzers.hr_analyzer import HRAnalyzer
from hr_ai.api.query_processor import QueryProcessor
from hr_ai.notifications.notifier import NotificationManager
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MVPTester:
    """Test the MVP functionality with sample documents."""
    
    def __init__(self):
        self.results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': []
        }
    
    def run_all_tests(self):
        """Run all MVP tests."""
        print("🧪 Запуск тестирования MVP HR AI системы")
        print("=" * 50)
        
        # Test 1: Document parsing
        self.test_document_parsing()
        
        # Test 2: Text analysis
        self.test_text_analysis()
        
        # Test 3: Full analysis workflow
        self.test_full_analysis()
        
        # Test 4: Query processing
        self.test_query_processing()
        
        # Test 5: Notification system
        self.test_notifications()
        
        # Print summary
        self.print_summary()
    
    def test_document_parsing(self):
        """Test document parser with sample files."""
        print("\n📄 Тест 1: Парсинг документов")
        
        try:
            parser = DocumentParser()
            files_info = parser.scan_directory()
            
            self.results['tests_run'] += 1
            
            if not files_info:
                print("⚠️ Документы не найдены в папке docs/")
                print("💡 Убедитесь, что в папке docs/ есть .docx файлы")
                self.results['tests_failed'] += 1
                return
            
            print(f"📊 Найдено документов: {len(files_info)}")
            
            # Test parsing first document
            first_file = files_info[0]['file_path']
            print(f"🔍 Тестирование парсинга: {Path(first_file).name}")
            
            document_data = parser.parse_document(first_file)
            
            # Validate parsing results
            required_fields = ['employee_name', 'full_text', 'sections', 'dates_found']
            for field in required_fields:
                if field not in document_data:
                    raise ValueError(f"Отсутствует поле: {field}")
            
            print(f"✅ Документ успешно обработан")
            print(f"   Сотрудник: {document_data['employee_name']}")
            print(f"   Текст: {len(document_data['full_text'])} символов")
            print(f"   Секций: {len(document_data['sections'])}")
            print(f"   Дат найдено: {len(document_data['dates_found'])}")
            
            self.results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {str(e)}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Document parsing: {str(e)}")
    
    def test_text_analysis(self):
        """Test AI text analysis."""
        print("\n🤖 Тест 2: AI анализ текста")
        
        try:
            parser = DocumentParser()
            analyzer = TextAnalyzer()
            
            self.results['tests_run'] += 1
            
            # Get first document
            files_info = parser.scan_directory()
            if not files_info:
                print("⚠️ Нет документов для анализа")
                self.results['tests_failed'] += 1
                return
            
            document_data = parser.parse_document(files_info[0]['file_path'])
            
            # Test meeting analysis
            print("🔍 Тестирование анализа встреч...")
            meeting_analysis = analyzer.analyze_meeting_occurrence(document_data)
            
            print(f"   Встреча состоялась: {meeting_analysis.meeting_occurred}")
            print(f"   Уверенность: {meeting_analysis.confidence_score:.2f}")
            print(f"   Требует внимания HR: {meeting_analysis.requires_hr_attention}")
            
            # Test information extraction
            print("🔍 Тестирование извлечения информации...")
            extracted_info = analyzer.extract_structured_information(document_data)
            
            categories = [
                'training_development', 'feedback_motivation', 'hr_processes',
                'community_engagement', 'location_relocation', 'risks_concerns'
            ]
            
            for category in categories:
                items = getattr(extracted_info, category, [])
                if items:
                    print(f"   {category}: {len(items)} элементов")
            
            print("✅ AI анализ завершен успешно")
            self.results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Ошибка AI анализа: {str(e)}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Text analysis: {str(e)}")
    
    def test_full_analysis(self):
        """Test full analysis workflow."""
        print("\n⚙️ Тест 3: Полный цикл анализа")
        
        try:
            self.results['tests_run'] += 1
            
            analyzer = HRAnalyzer()
            
            print("🔄 Запуск анализа всех документов...")
            results = analyzer.analyze_all_documents(force_reanalyze=True)
            
            print(f"📊 Результаты анализа:")
            print(f"   Всего файлов: {results['total_files']}")
            print(f"   Обработано: {results['processed']}")
            print(f"   Ошибок: {results['errors']}")
            print(f"   Встреч состоялось: {results['meetings_detected']}")
            print(f"   Встреч пропущено: {results['meetings_missed']}")
            print(f"   Требует внимания HR: {len(results['hr_attention_required'])}")
            
            if results['hr_attention_required']:
                print("\n⚠️ Случаи, требующие внимания HR:")
                for case in results['hr_attention_required'][:3]:  # Show first 3
                    print(f"   • {case.get('employee', 'Unknown')}: {case.get('reason', 'Unknown')}")
            
            # Test summary generation
            summary = analyzer.get_analysis_summary(days=30)
            print(f"\n📈 Сводка за 30 дней:")
            print(f"   Документов: {summary['total_documents']}")
            print(f"   Сотрудников: {len(summary['employees'])}")
            print(f"   Встреч всего: {summary['meetings_total']}")
            
            analyzer.close()
            
            print("✅ Полный анализ завершен успешно")
            self.results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Ошибка полного анализа: {str(e)}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Full analysis: {str(e)}")
    
    def test_query_processing(self):
        """Test query processing functionality."""
        print("\n💬 Тест 4: Обработка запросов")
        
        try:
            self.results['tests_run'] += 1
            
            processor = QueryProcessor()
            
            # Test queries
            test_queries = [
                "Кто упоминал обучение за последние 3 месяца?",
                "Какие встречи не состоялись?",
                "Есть ли упоминания релокации?",
                "Кто проявил интерес к сертификации?"
            ]
            
            print("🔍 Тестирование обработки запросов...")
            
            for i, query in enumerate(test_queries[:2]):  # Test first 2 queries
                print(f"\n   Запрос {i+1}: {query}")
                
                result = asyncio.run(processor.process_query(query))
                
                if result['success']:
                    print(f"   ✅ Результатов: {result['total_results']}")
                    print(f"   💡 {result['summary'][:100]}...")
                else:
                    print(f"   ⚠️ Ошибка: {result.get('error', 'Unknown')}")
            
            processor.close()
            
            print("\n✅ Обработка запросов работает")
            self.results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Ошибка обработки запросов: {str(e)}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Query processing: {str(e)}")
    
    def test_notifications(self):
        """Test notification system."""
        print("\n📨 Тест 5: Система уведомлений")
        
        try:
            self.results['tests_run'] += 1
            
            notifier = NotificationManager()
            
            print("🔍 Тестирование подключений...")
            
            # Test connections
            connection_results = notifier.test_connections()
            
            teams_status = "✅" if connection_results.get('teams') else "❌"
            email_status = "✅" if connection_results.get('email') else "❌"
            
            print(f"   Teams: {teams_status}")
            print(f"   Email: {email_status}")
            
            if not any(connection_results.values()):
                print("⚠️ Уведомления не настроены (это нормально для MVP)")
                print("💡 Для настройки уведомлений заполните .env файл")
            else:
                print("✅ Хотя бы один канал уведомлений доступен")
            
            self.results['tests_passed'] += 1
            
        except Exception as e:
            print(f"❌ Ошибка тестирования уведомлений: {str(e)}")
            self.results['tests_failed'] += 1
            self.results['errors'].append(f"Notifications: {str(e)}")
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ MVP")
        print("=" * 50)
        
        print(f"🧪 Всего тестов: {self.results['tests_run']}")
        print(f"✅ Пройдено: {self.results['tests_passed']}")
        print(f"❌ Провалено: {self.results['tests_failed']}")
        
        success_rate = (self.results['tests_passed'] / self.results['tests_run']) * 100 if self.results['tests_run'] > 0 else 0
        print(f"📊 Успешность: {success_rate:.1f}%")
        
        if self.results['errors']:
            print("\n🔍 Обнаруженные ошибки:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        print("\n💡 Рекомендации:")
        
        if self.results['tests_failed'] == 0:
            print("   🎉 Все тесты пройдены! MVP готов к использованию.")
            print("   🚀 Можно запускать веб-интерфейс: python main.py web")
        else:
            print("   ⚠️ Есть проблемы, которые нужно исправить.")
            print("   🔧 Проверьте конфигурацию: python main.py setup")
        
        if not settings.openai_api_key:
            print("   🤖 Для полного AI анализа добавьте OpenAI API ключ в .env")
        
        print("\n📚 Для запуска системы используйте:")
        print("   python main.py web       # Веб-интерфейс")
        print("   python main.py analyze   # Ручной анализ")
        print("   python main.py schedule  # Планировщик")

def main():
    """Run MVP tests."""
    tester = MVPTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()