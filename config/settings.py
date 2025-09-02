# HR AI Configuration
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
from dotenv import load_dotenv

# Get the project root directory (parent of config directory)
PROJECT_ROOT = Path(__file__).parent.parent

# Load environment variables from .env file
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)

class Settings(BaseSettings):
    # Application settings
    app_name: str = "HR AI Development Plan Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Document settings
    docs_directory: str = "docs"
    supported_formats: List[str] = [".docx", ".doc", ".pdf"]
    
    # Google Drive settings
    enable_google_drive: bool = False
    google_drive_folder_id: Optional[str] = None
    google_credentials_file: Optional[str] = None
    google_token_file: Optional[str] = "token.json"
    google_drive_sync_interval: int = 300  # seconds
    
    # AI/LLM settings
    openai_api_key: Optional[str] = None
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.3
    
    # Database settings
    database_url: str = "sqlite:///hr_ai.db"
    
    # Analysis settings
    analysis_schedule_cron: str = "0 9 * * 1"  # Every Monday at 9 AM
    confidence_threshold: float = 0.7
    
    # Notification settings
    enable_teams_notifications: bool = False
    teams_webhook_url: Optional[str] = None
    enable_email_notifications: bool = False
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    hr_email_recipients: List[str] = []
    
    @field_validator('hr_email_recipients', mode='before')
    @classmethod
    def parse_email_recipients(cls, v):
        if isinstance(v, str):
            if v.strip():
                return [email.strip() for email in v.split(',') if email.strip()]
            else:
                return []
        return v
    
    # Language settings
    default_language: str = "en"
    supported_languages: List[str] = ["en", "ru"]
    
    # Meeting detection settings
    meeting_keywords_en: List[str] = [
        "meeting", "checkpoint", "review", "discussion", 
        "conversation", "call", "session", "talked", "discussed"
    ]
    meeting_keywords_ru: List[str] = [
        "встреча", "обсуждение", "разговор", "созвон", 
        "беседа", "чекпоинт", "ревью", "обговорили"
    ]
    
    # Extraction keywords for different categories
    training_keywords: List[str] = [
        "обучение", "сертификат", "курс", "workshop", "training", 
        "certification", "course", "masterclass", "митап", "meetup"
    ]
    
    feedback_keywords: List[str] = [
        "satisfaction", "удовлетворен", "мотивация", "усталость", 
        "выгорание", "дискомфорт", "отношение к компании"
    ]
    
    hr_process_keywords: List[str] = [
        "собеседование", "interview", "assessment", "ассессмент", 
        "HR", "процесс", "предложение"
    ]
    
    community_keywords: List[str] = [
        "комьюнити", "community", "инициатива", "мероприятие", 
        "форум", "forum", "viva engage"
    ]
    
    location_keywords: List[str] = [
        "локация", "location", "релокация", "relocation", 
        "местоположение", "переезд"
    ]
    
    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env

# Global settings instance
settings = Settings()