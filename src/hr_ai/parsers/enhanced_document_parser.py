"""
Enhanced document parser with Google Drive integration.
Automatically chooses between Google Drive and local storage based on availability.
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from ..parsers.document_parser import DocumentParser, DocumentParseError
from ..integrations.google_drive import GoogleDriveClient, GoogleDriveError
from config.settings import settings

logger = logging.getLogger(__name__)

class EnhancedDocumentParser(DocumentParser):
    """
    Enhanced document parser that integrates with Google Drive.
    Falls back to local storage if Google Drive is not available.
    """
    
    def __init__(self, docs_directory: str = None):
        super().__init__(docs_directory or settings.docs_directory)
        self.google_drive_client = None
        self.use_google_drive = False
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize storage backend (Google Drive or local)."""
        if settings.enable_google_drive:
            try:
                self.google_drive_client = GoogleDriveClient()
                if self.google_drive_client.test_connection():
                    self.use_google_drive = True
                    logger.info("Google Drive integration enabled and connected")
                else:
                    logger.warning("Google Drive connection failed, falling back to local storage")
            except Exception as e:
                logger.warning(f"Failed to initialize Google Drive: {e}, using local storage")
        else:
            logger.info("Google Drive integration disabled, using local storage")
    
    def get_storage_status(self) -> Dict[str, any]:
        """
        Get current storage backend status.
        
        Returns:
            Dictionary with storage status information
        """
        status = {
            'storage_backend': 'google_drive' if self.use_google_drive else 'local',
            'google_drive_enabled': settings.enable_google_drive,
            'google_drive_connected': False,
            'local_directory': str(self.docs_directory),
            'last_sync': None
        }
        
        if self.google_drive_client:
            status['google_drive_connected'] = self.google_drive_client.test_connection()
            status['last_sync'] = self.google_drive_client.get_last_sync_time()
        
        return status
    
    def scan_directory(self) -> List[Dict[str, any]]:
        """
        Scan documents from current storage backend.
        
        Returns:
            List of dictionaries containing file information
        """
        if self.use_google_drive:
            return self._scan_google_drive()
        else:
            return super().scan_directory()
    
    def _scan_google_drive(self) -> List[Dict[str, any]]:
        """Scan files from Google Drive."""
        try:
            drive_files = self.google_drive_client.list_files()
            
            # Convert Google Drive file info to our standard format
            files_info = []
            for file_info in drive_files:
                try:
                    files_info.append({
                        'file_path': f"gdrive://{file_info['id']}/{file_info['name']}",
                        'file_id': file_info['id'],
                        'employee_name': self._extract_employee_name(file_info['name']),
                        'file_size': file_info['size'],
                        'modified_time': file_info['modified_time'],
                        'extension': file_info['extension'],
                        'source': 'google_drive'
                    })
                except Exception as e:
                    logger.warning(f"Error processing Google Drive file {file_info.get('name', 'unknown')}: {e}")
            
            logger.info(f"Found {len(files_info)} files in Google Drive")
            return files_info
            
        except GoogleDriveError as e:
            logger.error(f"Failed to scan Google Drive: {e}")
            # Fall back to local storage on error
            self.use_google_drive = False
            logger.info("Falling back to local storage due to Google Drive error")
            return super().scan_directory()
        except Exception as e:
            logger.error(f"Unexpected error scanning Google Drive: {e}")
            self.use_google_drive = False
            return super().scan_directory()
    
    def parse_document(self, file_path: str) -> Dict[str, any]:
        """
        Parse a document from current storage backend.
        
        Args:
            file_path: Path to the document file (local path or Google Drive ID)
            
        Returns:
            Dict containing extracted text, metadata, and structure information
        """
        if file_path.startswith('gdrive://'):
            return self._parse_google_drive_document(file_path)
        else:
            return super().parse_document(file_path)
    
    def _parse_google_drive_document(self, gdrive_path: str) -> Dict[str, any]:
        """
        Parse a document from Google Drive.
        
        Args:
            gdrive_path: Google Drive path in format 'gdrive://file_id/filename'
            
        Returns:
            Parsed document data
        """
        try:
            # Extract file ID and name from gdrive path
            path_parts = gdrive_path.replace('gdrive://', '').split('/', 1)
            file_id = path_parts[0]
            file_name = path_parts[1] if len(path_parts) > 1 else f"file_{file_id}"
            
            logger.info(f"Parsing Google Drive document: {file_name} (ID: {file_id})")
            
            # Download file to temporary location
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = self.google_drive_client.download_file_to_path(
                    file_id, file_name, temp_dir
                )
                
                # Parse the downloaded file
                parsed_data = super().parse_document(temp_file_path)
                
                # Update file path to reflect Google Drive source
                parsed_data['file_path'] = gdrive_path
                parsed_data['source'] = 'google_drive'
                parsed_data['file_id'] = file_id
                
                return parsed_data
                
        except GoogleDriveError as e:
            logger.error(f"Failed to parse Google Drive document {gdrive_path}: {e}")
            raise DocumentParseError(f"Failed to parse Google Drive document: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing Google Drive document {gdrive_path}: {e}")
            raise DocumentParseError(f"Unexpected error: {e}")
    
    def sync_google_drive(self, force: bool = False) -> Optional[Dict[str, any]]:
        """
        Sync Google Drive files to local cache if needed.
        
        Args:
            force: Force sync even if not needed based on interval
            
        Returns:
            Sync statistics or None if not using Google Drive
        """
        if not self.use_google_drive or not self.google_drive_client:
            logger.info("Google Drive not available for sync")
            return None
        
        try:
            if force or self.google_drive_client.is_sync_needed():
                # Create cache directory
                cache_dir = self.docs_directory / "gdrive_cache"
                
                sync_stats = self.google_drive_client.sync_files(
                    str(cache_dir), 
                    force_download=force
                )
                
                logger.info(f"Google Drive sync completed: {sync_stats}")
                return sync_stats
            else:
                logger.debug("Google Drive sync not needed")
                return None
                
        except GoogleDriveError as e:
            logger.error(f"Failed to sync Google Drive: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during Google Drive sync: {e}")
            return None
    
    def get_recently_modified_files(self, days: int = 7) -> List[str]:
        """
        Get list of files modified within the specified number of days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of file paths
        """
        if self.use_google_drive:
            return self._get_recent_google_drive_files(days)
        else:
            return super().get_recently_modified_files(days)
    
    def _get_recent_google_drive_files(self, days: int) -> List[str]:
        """Get recently modified files from Google Drive."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            drive_files = self.google_drive_client.list_files()
            
            recent_files = []
            for file_info in drive_files:
                try:
                    # Parse Google Drive timestamp
                    modified_time = datetime.fromisoformat(
                        file_info['modified_time'].replace('Z', '+00:00')
                    ).replace(tzinfo=None)
                    
                    if modified_time >= cutoff_time:
                        gdrive_path = f"gdrive://{file_info['id']}/{file_info['name']}"
                        recent_files.append(gdrive_path)
                        
                except Exception as e:
                    logger.warning(f"Error processing file timestamp for {file_info.get('name', 'unknown')}: {e}")
            
            logger.info(f"Found {len(recent_files)} recently modified files in Google Drive")
            return recent_files
            
        except GoogleDriveError as e:
            logger.error(f"Failed to get recent Google Drive files: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting recent Google Drive files: {e}")
            return []
    
    def force_refresh_connection(self) -> bool:
        """
        Force refresh the storage connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        if settings.enable_google_drive:
            try:
                self.google_drive_client = GoogleDriveClient()
                if self.google_drive_client.authenticate():
                    self.use_google_drive = True
                    logger.info("Google Drive connection refreshed successfully")
                    return True
                else:
                    self.use_google_drive = False
                    logger.warning("Failed to refresh Google Drive connection")
                    return False
            except Exception as e:
                logger.error(f"Error refreshing Google Drive connection: {e}")
                self.use_google_drive = False
                return False
        else:
            logger.info("Google Drive integration is disabled")
            return True
    
    def switch_to_local_storage(self):
        """Manually switch to local storage backend."""
        self.use_google_drive = False
        logger.info("Switched to local storage backend")
    
    def switch_to_google_drive(self) -> bool:
        """
        Manually switch to Google Drive backend.
        
        Returns:
            True if switch successful, False otherwise
        """
        if not settings.enable_google_drive:
            logger.warning("Cannot switch to Google Drive: integration disabled in settings")
            return False
        
        return self.force_refresh_connection()