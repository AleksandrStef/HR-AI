"""
Database models for storing HR AI analysis results.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Employee(Base):
    """Employee information extracted from documents."""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), index=True)  # For matching across documents
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to documents
    documents = relationship("Document", back_populates="employee")

class Document(Base):
    """Individual Development Plan documents."""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), index=True)
    file_path = Column(String(500), unique=True, nullable=False)
    employee_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), index=True)  # For detecting changes
    file_size = Column(Integer)
    file_modified = Column(DateTime)
    
    # Document content
    full_text = Column(Text)
    sections = Column(JSON)  # Structured sections
    tables = Column(JSON)    # Extracted table data
    dates_found = Column(JSON)  # Extracted dates
    meeting_sections = Column(JSON)  # Identified meeting sections
    
    # Processing metadata
    parsed_at = Column(DateTime, default=datetime.utcnow)
    last_analyzed = Column(DateTime)
    analysis_version = Column(String(50))  # Track analysis algorithm version
    
    # Relationships
    employee = relationship("Employee", back_populates="documents")
    meeting_analyses = relationship("MeetingAnalysis", back_populates="document")
    extracted_info = relationship("ExtractedInformation", back_populates="document")

class MeetingAnalysis(Base):
    """Results of meeting occurrence analysis."""
    __tablename__ = "meeting_analyses"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'), index=True)
    
    # Analysis results
    meeting_occurred = Column(Boolean, nullable=False)
    confidence_score = Column(Float)
    evidence = Column(JSON)  # List of evidence strings
    planned_date = Column(String(50))
    actual_date = Column(String(50))
    meeting_type = Column(String(100))
    requires_hr_attention = Column(Boolean, default=False)
    
    # Metadata
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_method = Column(String(50))  # AI, fallback, manual
    
    # Relationship
    document = relationship("Document", back_populates="meeting_analyses")

class ExtractedInformation(Base):
    """Structured information extracted from documents."""
    __tablename__ = "extracted_information"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'), index=True)
    
    # Extracted categories (stored as JSON arrays)
    training_development = Column(JSON)
    feedback_motivation = Column(JSON)
    hr_processes = Column(JSON)
    community_engagement = Column(JSON)
    location_relocation = Column(JSON)
    risks_concerns = Column(JSON)
    
    # Metadata
    extracted_at = Column(DateTime, default=datetime.utcnow)
    extraction_method = Column(String(50))
    
    # Relationship
    document = relationship("Document", back_populates="extracted_info")

class AnalysisReport(Base):
    """Weekly analysis reports sent to HR."""
    __tablename__ = "analysis_reports"
    
    id = Column(Integer, primary_key=True)
    report_date = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Report content
    summary = Column(Text)
    documents_analyzed = Column(Integer, default=0)
    meetings_detected = Column(Integer, default=0)
    meetings_missed = Column(Integer, default=0)
    hr_attention_required = Column(JSON)  # List of cases requiring attention
    key_insights = Column(JSON)  # Important findings
    
    # Notification status
    sent_to_teams = Column(Boolean, default=False)
    sent_to_email = Column(Boolean, default=False)
    teams_sent_at = Column(DateTime)
    email_sent_at = Column(DateTime)

class QueryLog(Base):
    """Log of HR specialist queries and responses."""
    __tablename__ = "query_logs"
    
    id = Column(Integer, primary_key=True)
    query_text = Column(Text, nullable=False)
    query_type = Column(String(100))  # training, feedback, general, etc.
    
    # Response data
    response_data = Column(JSON)  # Structured response
    response_summary = Column(Text)  # Human-readable summary
    documents_matched = Column(Integer, default=0)
    
    # Metadata
    queried_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float)  # seconds
    user_feedback = Column(String(20))  # helpful, not_helpful, etc.

class SystemLog(Base):
    """System activity and error logs."""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    component = Column(String(100))  # parser, analyzer, scheduler, etc.
    details = Column(JSON)  # Additional structured data
    
    # Metadata
    logged_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)