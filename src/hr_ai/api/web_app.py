"""
FastAPI web application for HR AI system.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from config.settings import settings
from .query_processor import QueryProcessor
from ..analyzers.hr_analyzer import HRAnalyzer
from ..schedulers.weekly_scheduler import WeeklyScheduler
from ..notifications.notifier import NotificationManager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="HR AI Development Plan Analyzer",
    description="AI-powered analysis of Individual Development Plans",
    version="1.0.0"
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global instances
query_processor = QueryProcessor()
hr_analyzer = HRAnalyzer()
scheduler = WeeklyScheduler()
notifier = NotificationManager()

# Pydantic models for API
class QueryRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    success: bool
    total_results: int
    results: List[Dict[str, Any]]
    summary: str
    query_analysis: Dict[str, Any]
    timestamp: str

class AnalysisRequest(BaseModel):
    force_reanalyze: bool = False
    days_back: Optional[int] = None

class AnalysisResponse(BaseModel):
    success: bool
    message: str
    statistics: Dict[str, Any]
    hr_attention_required: List[Dict[str, Any]]

class NotificationTest(BaseModel):
    message: str
    priority: str = "medium"

# Routes

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main interface."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>HR AI - Individual Development Plan Analyzer</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .section { margin-bottom: 30px; padding: 20px; border-radius: 8px; background-color: #f9f9f9; }
            .query-box { width: 100%; padding: 15px; font-size: 16px; border: 1px solid #ddd; border-radius: 4px; }
            .btn { padding: 12px 24px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .btn:hover { background-color: #0056b3; }
            .btn-secondary { background-color: #6c757d; }
            .btn-secondary:hover { background-color: #545b62; }
            .results { margin-top: 20px; }
            .result-item { padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; background-color: white; }
            .employee-name { font-weight: bold; color: #007bff; }
            .result-type { color: #6c757d; font-size: 14px; }
            .result-content { margin: 10px 0; }
            .loading { display: none; text-align: center; padding: 20px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 HR AI - Анализ ПИР</h1>
                <p>Система автоматического анализа планов индивидуального развития</p>
            </div>
            
            <div class="section">
                <h2>💬 Задать вопрос системе</h2>
                <textarea id="queryInput" class="query-box" rows="3" placeholder="Введите ваш вопрос, например: 'Кто за последние 3 месяца выразил желание выступить на внешнем форуме?'"></textarea>
                <br>
                <button class="btn" onclick="submitQuery()">Отправить запрос</button>
                <button class="btn btn-secondary" onclick="clearResults()">Очистить</button>
                
                <div class="loading" id="loading">
                    <p>🔄 Обрабатываем запрос...</p>
                </div>
                
                <div id="results" class="results"></div>
            </div>
            
            <div class="section">
                <h2>📊 Управление анализом</h2>
                <button class="btn" onclick="runAnalysis(false)">Анализ новых документов</button>
                <button class="btn" onclick="runAnalysis(true)">Полный переанализ</button>
                <button class="btn btn-secondary" onclick="getSystemStatus()">Статус системы</button>
                <button class="btn btn-secondary" onclick="testNotifications()">Тест уведомлений</button>
                
                <div id="analysisResults"></div>
            </div>
            
            <div class="section">
                <h2>☁️ Google Drive</h2>
                <button class="btn" onclick="getStorageStatus()">Статус хранилища</button>
                <button class="btn" onclick="syncGoogleDrive(false)">Синхронизация</button>
                <button class="btn" onclick="syncGoogleDrive(true)">Принудительная синхронизация</button>
                <button class="btn btn-secondary" onclick="refreshStorageConnection()">Обновить подключение</button>
                
                <div id="storageResults"></div>
            </div>
            
            <div class="section">
                <h2>📋 Примеры запросов</h2>
                <ul>
                    <li><a href="#" onclick="setQuery('Кто за последние 3 месяца выразил желание выступить на внешнем форуме?')">Кто хочет выступать на форумах?</a></li>
                    <li><a href="#" onclick="setQuery('Какие сотрудники сообщили о перегрузке или выгорании?')">Признаки выгорания</a></li>
                    <li><a href="#" onclick="setQuery('Кто прошёл обучение с сертификацией за последние 6 месяцев?')">Завершенные сертификации</a></li>
                    <li><a href="#" onclick="setQuery('Есть ли упоминания релокации?')">Планы релокации</a></li>
                    <li><a href="#" onclick="setQuery('Какие встречи не состоялись на прошлой неделе?')">Пропущенные встречи</a></li>
                </ul>
            </div>
        </div>
        
        <script>
            async function submitQuery() {
                const query = document.getElementById('queryInput').value.trim();
                if (!query) {
                    alert('Пожалуйста, введите запрос');
                    return;
                }
                
                const loading = document.getElementById('loading');
                const results = document.getElementById('results');
                
                loading.style.display = 'block';
                results.innerHTML = '';
                
                try {
                    const response = await fetch('/api/query', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query: query })
                    });
                    
                    const data = await response.json();
                    displayResults(data);
                } catch (error) {
                    results.innerHTML = '<div class="result-item">Ошибка: ' + error.message + '</div>';
                } finally {
                    loading.style.display = 'none';
                }
            }
            
            function displayResults(data) {
                const results = document.getElementById('results');
                
                if (!data.success) {
                    results.innerHTML = '<div class="result-item">Ошибка: ' + (data.error || 'Неизвестная ошибка') + '</div>';
                    return;
                }
                
                let html = '<h3>Результаты поиска</h3>';
                html += '<p><strong>Краткое описание:</strong> ' + data.summary + '</p>';
                html += '<p><strong>Найдено результатов:</strong> ' + data.total_results + '</p>';
                
                if (data.results && data.results.length > 0) {
                    html += '<div class="stats"><div class="stat-card"><div class="stat-number">' + data.total_results + '</div><div>Результатов</div></div></div>';
                    
                    data.results.forEach(result => {
                        html += '<div class="result-item">';
                        html += '<div class="employee-name">' + (result.employee_name || 'Неизвестно') + '</div>';
                        html += '<div class="result-type">' + (result.type || 'Общий') + ' • ' + (result.date || 'Дата неизвестна') + '</div>';
                        html += '<div class="result-content">' + (result.content || result.context || 'Нет содержимого') + '</div>';
                        if (result.confidence) html += '<div><small>Уверенность: ' + result.confidence + '</small></div>';
                        html += '</div>';
                    });
                } else {
                    html += '<p>По вашему запросу ничего не найдено.</p>';
                }
                
                results.innerHTML = html;
            }
            
            async function runAnalysis(forceReanalyze = false) {
                const analysisResults = document.getElementById('analysisResults');
                const buttonText = forceReanalyze ? '🔄 Выполняем полный переанализ...' : '🔄 Анализируем новые документы...';
                analysisResults.innerHTML = '<p>' + buttonText + '</p>';
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ force_reanalyze: forceReanalyze })
                    });
                    
                    const data = await response.json();
                    
                    let html = '<h3>Результаты анализа</h3>';
                    
                    if (data.statistics?.processed === 0 && !forceReanalyze) {
                        html += '<div class="result-item" style="border-left-color: #FFA500;">';
                        html += '<div class="employee-name">ℹ️ Новые документы не обнаружены</div>';
                        html += '<div class="result-content">Все документы уже проанализированы. Нажмите "Полный переанализ" для повторного анализа.</div>';
                        html += '</div>';
                    }
                    
                    html += '<div class="stats">';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.statistics?.total_files || 0) + '</div><div>Всего файлов</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.statistics?.processed || 0) + '</div><div>Обработано</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.statistics?.skipped || 0) + '</div><div>Пропущено</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.statistics?.meetings_detected || 0) + '</div><div>Встреч состоялось</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.statistics?.meetings_missed || 0) + '</div><div>Встреч пропущено</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.hr_attention_required?.length || 0) + '</div><div>Требует внимания HR</div></div>';
                    html += '</div>';
                    
                    if (data.hr_attention_required && data.hr_attention_required.length > 0) {
                        html += '<h4>Требует внимания HR:</h4>';
                        data.hr_attention_required.forEach(item => {
                            html += '<div class="result-item">';
                            html += '<div class="employee-name">' + (item.employee || 'Неизвестно') + '</div>';
                            html += '<div class="result-content">' + (item.reason || 'Неизвестная причина') + '</div>';
                            html += '</div>';
                        });
                    }
                    
                    analysisResults.innerHTML = html;
                } catch (error) {
                    analysisResults.innerHTML = '<div class="result-item">Ошибка: ' + error.message + '</div>';
                }
            }
            
            async function getSystemStatus() {
                const analysisResults = document.getElementById('analysisResults');
                
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    
                    let html = '<h3>Статус системы</h3>';
                    html += '<div class="stats">';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.total_documents || 0) + '</div><div>Документов в системе</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.analyzed_documents || 0) + '</div><div>Проанализировано</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.ai_enabled ? '✅' : '❌') + '</div><div>AI анализ</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.notifications_enabled ? '✅' : '❌') + '</div><div>Уведомления</div></div>';
                    html += '</div>';
                    
                    analysisResults.innerHTML = html;
                } catch (error) {
                    analysisResults.innerHTML = '<div class="result-item">Ошибка: ' + error.message + '</div>';
                }
            }
            
            async function testNotifications() {
                try {
                    const response = await fetch('/api/test-notifications', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: 'Тестовое уведомление от HR AI системы' })
                    });
                    
                    const data = await response.json();
                    alert('Результат теста уведомлений: ' + JSON.stringify(data));
                } catch (error) {
                    alert('Ошибка тестирования: ' + error.message);
                }
            }
            
            function setQuery(query) {
                document.getElementById('queryInput').value = query;
            }
            
            function clearResults() {
                document.getElementById('results').innerHTML = '';
                document.getElementById('analysisResults').innerHTML = '';
                document.getElementById('queryInput').value = '';
            }
            
            // Allow Enter key to submit query
            document.getElementById('queryInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && e.ctrlKey) {
                    submitQuery();
                }
            });
            
            // Google Drive functions
            async function getStorageStatus() {
                const storageResults = document.getElementById('storageResults');
                storageResults.innerHTML = '<p>🔄 Получаем статус хранилища...</p>';
                
                try {
                    const response = await fetch('/api/storage-status');
                    const data = await response.json();
                    
                    let html = '<h3>Статус системы хранения</h3>';
                    html += '<div class="stats">';
                    html += '<div class="stat-card"><div class="stat-number">' + data.storage_backend.toUpperCase() + '</div><div>Текущее хранилище</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.google_drive_enabled ? '✅' : '❌') + '</div><div>Google Drive включен</div></div>';
                    html += '<div class="stat-card"><div class="stat-number">' + (data.google_drive_connected ? '✅' : '❌') + '</div><div>Google Drive подключен</div></div>';
                    html += '</div>';
                    
                    if (data.last_sync) {
                        html += '<p><strong>Последняя синхронизация:</strong> ' + new Date(data.last_sync).toLocaleString() + '</p>';
                    }
                    
                    html += '<p><strong>Локальная папка:</strong> ' + data.local_directory + '</p>';
                    
                    storageResults.innerHTML = html;
                } catch (error) {
                    storageResults.innerHTML = '<div class="result-item">Ошибка: ' + error.message + '</div>';
                }
            }
            
            async function syncGoogleDrive(force = false) {
                const storageResults = document.getElementById('storageResults');
                const buttonText = force ? '🔄 Выполняем принудительную синхронизацию...' : '🔄 Синхронизируем Google Drive...';
                storageResults.innerHTML = '<p>' + buttonText + '</p>';
                
                try {
                    const response = await fetch('/api/sync-google-drive', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ force: force })
                    });
                    
                    const data = await response.json();
                    
                    let html = '<h3>Результаты синхронизации</h3>';
                    
                    if (data.success && data.statistics) {
                        html += '<div class="stats">';
                        html += '<div class="stat-card"><div class="stat-number">' + (data.statistics.total_files || 0) + '</div><div>Всего файлов</div></div>';
                        html += '<div class="stat-card"><div class="stat-number">' + (data.statistics.downloaded || 0) + '</div><div>Загружено</div></div>';
                        html += '<div class="stat-card"><div class="stat-number">' + (data.statistics.skipped || 0) + '</div><div>Пропущено</div></div>';
                        html += '<div class="stat-card"><div class="stat-number">' + (data.statistics.errors || 0) + '</div><div>Ошибок</div></div>';
                        html += '</div>';
                        html += '<p><strong>Сообщение:</strong> ' + data.message + '</p>';
                    } else {
                        html += '<p>' + data.message + '</p>';
                    }
                    
                    storageResults.innerHTML = html;
                } catch (error) {
                    storageResults.innerHTML = '<div class="result-item">Ошибка: ' + error.message + '</div>';
                }
            }
            
            async function refreshStorageConnection() {
                const storageResults = document.getElementById('storageResults');
                storageResults.innerHTML = '<p>🔄 Обновляем подключение...</p>';
                
                try {
                    const response = await fetch('/api/refresh-storage', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const data = await response.json();
                    
                    let html = '<h3>Обновление подключения</h3>';
                    html += '<p>' + data.message + '</p>';
                    
                    if (data.success) {
                        html += '<p style="color: green;">✅ Подключение успешно обновлено</p>';
                    } else {
                        html += '<p style="color: red;">❌ Не удалось обновить подключение</p>';
                    }
                    
                    storageResults.innerHTML = html;
                } catch (error) {
                    storageResults.innerHTML = '<div class="result-item">Ошибка: ' + error.message + '</div>';
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a natural language query."""
    try:
        result = await query_processor.process_query(request.query)
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Query processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze", response_model=AnalysisResponse)
async def run_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Run document analysis."""
    try:
        if request.days_back:
            result = hr_analyzer.analyze_recent_documents(request.days_back)
        else:
            result = hr_analyzer.analyze_all_documents(request.force_reanalyze)
        
        return AnalysisResponse(
            success=True,
            message="Analysis completed successfully",
            statistics=result,
            hr_attention_required=result.get('hr_attention_required', [])
        )
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_system_status():
    """Get system status and statistics."""
    try:
        # Get document statistics
        from sqlalchemy import func
        from ..models.database import Document, MeetingAnalysis
        
        session = hr_analyzer.session
        
        total_docs = session.query(func.count(Document.id)).scalar() or 0
        analyzed_docs = session.query(func.count(MeetingAnalysis.id)).scalar() or 0
        
        # Test connections
        notification_status = notifier.test_connections()
        
        return {
            "status": "running",
            "total_documents": total_docs,
            "analyzed_documents": analyzed_docs,
            "ai_enabled": bool(settings.openai_api_key),
            "notifications_enabled": any(notification_status.values()),
            "notification_status": notification_status,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test-notifications")
async def test_notifications(request: NotificationTest):
    """Test notification systems."""
    try:
        results = notifier.test_connections()
        
        # Send actual test message if connections work
        if any(results.values()):
            await notifier.send_instant_alert(
                employee_name="Тестовый сотрудник",
                alert_type="system_test",
                message=request.message,
                priority=request.priority
            )
        
        return {
            "success": True,
            "connection_tests": results,
            "message": "Test notifications sent where possible"
        }
    except Exception as e:
        logger.error(f"Notification test error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/popular-queries")
async def get_popular_queries(days: int = 30):
    """Get popular queries from recent history."""
    try:
        popular = query_processor.get_popular_queries(days)
        return {"popular_queries": popular}
    except Exception as e:
        logger.error(f"Popular queries error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting HR AI system...")
    
    # Start the scheduler
    try:
        scheduler.start()
        logger.info("Weekly scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down HR AI system...")
    
    try:
        scheduler.stop()
        query_processor.close()
        hr_analyzer.close()
        scheduler.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Google Drive integration endpoints
@app.get("/api/storage-status")
async def get_storage_status():
    """Get current storage backend status."""
    try:
        status = hr_analyzer.get_storage_status()
        return status
    except Exception as e:
        logger.error(f"Storage status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync-google-drive")
async def sync_google_drive(force: bool = False):
    """Sync Google Drive files."""
    try:
        sync_result = hr_analyzer.sync_google_drive(force=force)
        if sync_result:
            return {
                "success": True,
                "message": "Google Drive sync completed",
                "statistics": sync_result
            }
        else:
            return {
                "success": False,
                "message": "Google Drive not available or sync not needed"
            }
    except Exception as e:
        logger.error(f"Google Drive sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh-storage")
async def refresh_storage_connection():
    """Refresh storage connection."""
    try:
        success = hr_analyzer.force_refresh_storage_connection()
        return {
            "success": success,
            "message": "Storage connection refreshed" if success else "Failed to refresh storage connection"
        }
    except Exception as e:
        logger.error(f"Storage refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Main function for running the server
def main():
    """Run the FastAPI server."""
    uvicorn.run(
        "hr_ai.api.web_app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )

if __name__ == "__main__":
    main()