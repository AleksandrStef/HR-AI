"""
Main HR analysis engine that coordinates document parsing, AI analysis, and result storage.
"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from ..parsers.enhanced_document_parser import EnhancedDocumentParser
from ..parsers.document_parser import DocumentParseError
from ..analyzers.text_analyzer import TextAnalyzer, MeetingAnalysis, ExtractedInformation
from ..models.database import Base, Document, Employee, MeetingAnalysis as MeetingAnalysisDB, ExtractedInformation as ExtractedInformationDB

logger = logging.getLogger(__name__)

class HRAnalyzer:
    """Main coordinator for HR document analysis."""
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.document_parser = EnhancedDocumentParser(settings.docs_directory)
        self.text_analyzer = TextAnalyzer()
    
    def analyze_all_documents(self, force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Analyze all documents in the docs directory.
        
        Args:
            force_reanalyze: If True, reanalyze even if documents haven't changed
            
        Returns:
            Summary of analysis results
        """
        logger.info("Starting analysis of all documents")
        
        # Get all files in docs directory
        files_info = self.document_parser.scan_directory()
        
        results = {
            'total_files': len(files_info),
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'new_analyses': 0,
            'updated_analyses': 0,
            'meetings_detected': 0,
            'meetings_missed': 0,
            'hr_attention_required': []
        }
        
        for file_info in files_info:
            try:
                logger.info(f"Processing file: {file_info['file_path']}")
                result = self.analyze_document(file_info['file_path'], force_reanalyze)
                if result:
                    logger.info(f"Successfully analyzed: {result['employee_name']}")
                    results['processed'] += 1
                    if result.get('new_analysis'):
                        results['new_analyses'] += 1
                    else:
                        results['updated_analyses'] += 1
                    
                    if result.get('meeting_occurred'):
                        results['meetings_detected'] += 1
                    else:
                        results['meetings_missed'] += 1
                    
                    if result.get('requires_hr_attention'):
                        results['hr_attention_required'].append({
                            'employee': result.get('employee_name'),
                            'file': file_info['file_path'],
                            'reason': result.get('attention_reason')
                        })
                else:
                    logger.info(f"Skipped (already processed): {file_info['file_path']}")
                        
            except Exception as e:
                logger.error(f"Error analyzing {file_info['file_path']}: {str(e)}")
                results['errors'] += 1
        
        logger.info(f"Analysis complete: {results}")
        return results
    
    def analyze_document(self, file_path: str, force_reanalyze: bool = False) -> Optional[Dict[str, Any]]:
        """
        Analyze a single document.
        
        Args:
            file_path: Path to the document
            force_reanalyze: Force reanalysis even if unchanged
            
        Returns:
            Analysis results or None if skipped
        """
        try:
            # Parse the document
            document_data = self.document_parser.parse_document(file_path)
            
            # Check if document has changed or needs reanalysis
            file_hash = self._calculate_file_hash(file_path)
            existing_doc = self.session.query(Document).filter_by(file_path=file_path).first()
            
            if existing_doc and existing_doc.file_hash == file_hash and not force_reanalyze:
                logger.info(f"Document unchanged, skipping: {file_path} (hash: {file_hash[:8]}...)")
                return None
            
            # Store or update document in database
            doc_record = self._store_document(document_data, file_hash, existing_doc)
            
            # Perform AI analysis
            meeting_analysis = self.text_analyzer.analyze_meeting_occurrence(document_data)
            extracted_info = self.text_analyzer.extract_structured_information(document_data)
            
            # Store analysis results
            self._store_meeting_analysis(doc_record.id, meeting_analysis)
            self._store_extracted_information(doc_record.id, extracted_info)
            
            self.session.commit()
            
            return {
                'document_id': doc_record.id,
                'employee_name': document_data['employee_name'],
                'meeting_occurred': meeting_analysis.meeting_occurred,
                'requires_hr_attention': meeting_analysis.requires_hr_attention,
                'attention_reason': self._get_attention_reason(meeting_analysis, extracted_info),
                'new_analysis': existing_doc is None,
                'confidence_score': meeting_analysis.confidence_score
            }
            
        except DocumentParseError as e:
            logger.error(f"Parse error for {file_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Analysis error for {file_path}: {str(e)}")
            self.session.rollback()
            raise
    
    def analyze_recent_documents(self, days: int = 7) -> Dict[str, Any]:
        """
        Analyze only documents modified in the last N days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Analysis results summary
        """
        recent_files = self.document_parser.get_recently_modified_files(days)
        
        if not recent_files:
            logger.info(f"No documents modified in the last {days} days")
            return {
                'total_files': 0,
                'processed': 0,
                'errors': 0,
                'period_start': (datetime.now() - timedelta(days=days)).isoformat(),
                'period_end': datetime.now().isoformat()
            }
        
        logger.info(f"Analyzing {len(recent_files)} recently modified documents")
        
        results = {
            'total_files': len(recent_files),
            'processed': 0,
            'errors': 0,
            'new_analyses': 0,
            'updated_analyses': 0,
            'meetings_detected': 0,
            'meetings_missed': 0,
            'hr_attention_required': [],
            'period_start': (datetime.now() - timedelta(days=days)).isoformat(),
            'period_end': datetime.now().isoformat()
        }
        
        for file_path in recent_files:
            try:
                result = self.analyze_document(file_path, force_reanalyze=False)
                if result:
                    results['processed'] += 1
                    if result.get('new_analysis'):
                        results['new_analyses'] += 1
                    else:
                        results['updated_analyses'] += 1
                    
                    if result.get('meeting_occurred'):
                        results['meetings_detected'] += 1
                    else:
                        results['meetings_missed'] += 1
                    
                    if result.get('requires_hr_attention'):
                        results['hr_attention_required'].append({
                            'employee': result.get('employee_name'),
                            'file': file_path,
                            'reason': result.get('attention_reason'),
                            'confidence': result.get('confidence_score')
                        })
                        
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {str(e)}")
                results['errors'] += 1
        
        return results
    
    def get_analysis_summary(self, employee_name: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Get analysis summary for specific employee or all employees.
        
        Args:
            employee_name: Filter by employee name (optional)
            days: Days to look back
            
        Returns:
            Analysis summary
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Query recent documents
        query = self.session.query(Document).filter(Document.parsed_at >= cutoff_date)
        if employee_name:
            query = query.filter(Document.employee_name.ilike(f"%{employee_name}%"))
        
        documents = query.all()
        
        summary = {
            'period_days': days,
            'total_documents': len(documents),
            'employees': set(),
            'meetings_total': 0,
            'meetings_occurred': 0,
            'meetings_missed': 0,
            'hr_attention_cases': [],
            'key_insights': {
                'training_requests': [],
                'feedback_concerns': [],
                'relocation_plans': []
            }
        }
        
        for doc in documents:
            summary['employees'].add(doc.employee_name)
            
            # Get meeting analysis
            meeting_analysis = self.session.query(MeetingAnalysisDB).filter_by(document_id=doc.id).first()
            if meeting_analysis:
                summary['meetings_total'] += 1
                if meeting_analysis.meeting_occurred:
                    summary['meetings_occurred'] += 1
                else:
                    summary['meetings_missed'] += 1
                
                if meeting_analysis.requires_hr_attention:
                    summary['hr_attention_cases'].append({
                        'employee': doc.employee_name,
                        'type': 'missed_meeting',
                        'confidence': meeting_analysis.confidence_score,
                        'evidence': meeting_analysis.evidence
                    })
            
            # Get extracted information for insights
            extracted_info = self.session.query(ExtractedInformationDB).filter_by(document_id=doc.id).first()
            if extracted_info:
                # Training insights
                if extracted_info.training_development:
                    for item in extracted_info.training_development:
                        if item.get('status') in ['planned', 'interested']:
                            summary['key_insights']['training_requests'].append({
                                'employee': doc.employee_name,
                                'content': item.get('content'),
                                'category': item.get('category')
                            })
                
                # Feedback concerns
                if extracted_info.feedback_motivation:
                    for item in extracted_info.feedback_motivation:
                        if item.get('sentiment') == 'negative':
                            summary['key_insights']['feedback_concerns'].append({
                                'employee': doc.employee_name,
                                'content': item.get('content'),
                                'context': item.get('context', '')[:100]
                            })
                
                # Relocation plans
                if extracted_info.location_relocation:
                    for item in extracted_info.location_relocation:
                        if 'relocation' in item.get('category', '').lower():
                            summary['key_insights']['relocation_plans'].append({
                                'employee': doc.employee_name,
                                'content': item.get('content'),
                                'context': item.get('context', '')[:100]
                            })
        
        summary['employees'] = list(summary['employees'])
        return summary
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _store_document(self, document_data: Dict[str, Any], file_hash: str, existing_doc: Document = None) -> Document:
        """Store or update document in database."""
        if existing_doc:
            # Update existing document
            existing_doc.full_text = document_data['full_text']
            existing_doc.sections = document_data['sections']
            existing_doc.tables = document_data['tables']
            existing_doc.dates_found = document_data['dates_found']
            existing_doc.meeting_sections = document_data['meeting_sections']
            existing_doc.file_hash = file_hash
            existing_doc.file_size = os.path.getsize(document_data['file_path'])
            existing_doc.file_modified = datetime.fromisoformat(document_data['file_modified'])
            existing_doc.parsed_at = datetime.now()
            return existing_doc
        else:
            # Create new document record
            doc = Document(
                file_path=document_data['file_path'],
                employee_name=document_data['employee_name'],
                full_text=document_data['full_text'],
                sections=document_data['sections'],
                tables=document_data['tables'],
                dates_found=document_data['dates_found'],
                meeting_sections=document_data['meeting_sections'],
                file_hash=file_hash,
                file_size=os.path.getsize(document_data['file_path']),
                file_modified=datetime.fromisoformat(document_data['file_modified']),
                parsed_at=datetime.now()
            )
            self.session.add(doc)
            self.session.flush()  # Get the ID
            return doc
    
    def _store_meeting_analysis(self, document_id: int, analysis: MeetingAnalysis) -> None:
        """Store meeting analysis results."""
        # Remove existing analysis for this document
        self.session.query(MeetingAnalysisDB).filter_by(document_id=document_id).delete()
        
        # Add new analysis
        db_analysis = MeetingAnalysisDB(
            document_id=document_id,
            meeting_occurred=analysis.meeting_occurred,
            confidence_score=analysis.confidence_score,
            evidence=analysis.evidence,
            planned_date=analysis.planned_date,
            actual_date=analysis.actual_date,
            meeting_type=analysis.meeting_type,
            requires_hr_attention=analysis.requires_hr_attention,
            analysis_method='ai' if settings.openai_api_key else 'fallback'
        )
        self.session.add(db_analysis)
    
    def _store_extracted_information(self, document_id: int, extracted_info: ExtractedInformation) -> None:
        """Store extracted information."""
        # Remove existing extracted info for this document
        self.session.query(ExtractedInformationDB).filter_by(document_id=document_id).delete()
        
        # Add new extracted information
        db_extracted = ExtractedInformationDB(
            document_id=document_id,
            training_development=extracted_info.training_development,
            feedback_motivation=extracted_info.feedback_motivation,
            hr_processes=extracted_info.hr_processes,
            community_engagement=extracted_info.community_engagement,
            location_relocation=extracted_info.location_relocation,
            risks_concerns=extracted_info.risks_concerns,
            extraction_method='ai' if settings.openai_api_key else 'keyword'
        )
        self.session.add(db_extracted)
    
    def _get_attention_reason(self, meeting_analysis: MeetingAnalysis, extracted_info: ExtractedInformation) -> str:
        """Determine why this case requires HR attention."""
        reasons = []
        
        if meeting_analysis.requires_hr_attention:
            if not meeting_analysis.meeting_occurred:
                reasons.append("Possible missed meeting")
            if meeting_analysis.confidence_score < settings.confidence_threshold:
                reasons.append("Low confidence analysis")
        
        # Check for risk indicators in extracted information
        if extracted_info.risks_concerns:
            risk_count = len(extracted_info.risks_concerns)
            if risk_count > 2:
                reasons.append(f"Multiple risk indicators ({risk_count})")
        
        # Check for negative feedback
        negative_feedback = [
            item for item in extracted_info.feedback_motivation 
            if item.get('sentiment') == 'negative'
        ]
        if negative_feedback:
            reasons.append("Negative feedback detected")
        
        return "; ".join(reasons) if reasons else "Requires review"
    
    def sync_google_drive(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Sync Google Drive files if enabled.
        
        Args:
            force: Force sync even if not needed based on interval
            
        Returns:
            Sync statistics or None if not using Google Drive
        """
        return self.document_parser.sync_google_drive(force)
    
    def get_storage_status(self) -> Dict[str, Any]:
        """
        Get current storage backend status.
        
        Returns:
            Dictionary with storage status information
        """
        return self.document_parser.get_storage_status()
    
    def force_refresh_storage_connection(self) -> bool:
        """
        Force refresh the storage connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        return self.document_parser.force_refresh_connection()
    
    def close(self):
        """Close database session."""
        self.session.close()