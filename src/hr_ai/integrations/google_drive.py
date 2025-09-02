"""
Google Drive integration for HR AI system.
Handles authentication, file listing, downloading, and synchronization.
"""

import io
import os
import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from config.settings import settings

logger = logging.getLogger(__name__)

class GoogleDriveError(Exception):
    """Custom exception for Google Drive operations."""
    pass

class GoogleDriveClient:
    """Client for interacting with Google Drive API."""
    
    # Scopes needed for reading files
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self.folder_id = settings.google_drive_folder_id
        self.credentials_file = settings.google_credentials_file
        self.token_file = settings.google_token_file
        self._last_sync = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            creds = None
            
            # Load existing token
            if self.token_file and os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.warning(f"Failed to refresh credentials: {e}")
                        creds = None
                
                if not creds:
                    if not self.credentials_file or not os.path.exists(self.credentials_file):
                        logger.error(f"Google credentials file not found: {self.credentials_file}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for future use
                if self.token_file:
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
            
            self.credentials = creds
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive")
            return True
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the connection to Google Drive.
        
        Returns:
            True if connection is successful, False otherwise
        """
        if not self.service:
            return self.authenticate()
        
        try:
            # Try to access the specified folder or root
            if self.folder_id:
                folder = self.service.files().get(fileId=self.folder_id).execute()
                logger.info(f"Connected to Google Drive folder: {folder.get('name')}")
            else:
                # Test with a simple query
                results = self.service.files().list(pageSize=1).execute()
                logger.info("Connected to Google Drive (root)")
            
            return True
            
        except HttpError as e:
            logger.error(f"Google Drive connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing Google Drive connection: {e}")
            return False
    
    def list_files(self, folder_id: Optional[str] = None) -> List[Dict[str, any]]:
        """
        List files in Google Drive folder.
        
        Args:
            folder_id: Specific folder ID to list, uses configured folder if None
            
        Returns:
            List of file information dictionaries
        """
        if not self.service:
            if not self.authenticate():
                raise GoogleDriveError("Failed to authenticate with Google Drive")
        
        try:
            folder_id = folder_id or self.folder_id
            
            # Build query for supported file types
            supported_mimes = [
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
                'application/msword',  # .doc
                'application/pdf'  # .pdf
            ]
            
            mime_query = ' or '.join([f"mimeType='{mime}'" for mime in supported_mimes])
            
            query = f"({mime_query}) and trashed=false"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            logger.info(f"Querying Google Drive with: {query}")
            
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields=\"nextPageToken, files(id, name, size, modifiedTime, mimeType, parents)\"
            ).execute()
            
            files = results.get('files', [])
            
            # Convert to our standard format
            files_info = []
            for file in files:
                try:
                    files_info.append({
                        'id': file['id'],
                        'name': file['name'],
                        'size': int(file.get('size', 0)),
                        'modified_time': file['modifiedTime'],
                        'mime_type': file['mimeType'],
                        'extension': self._get_extension_from_mime(file['mimeType']),
                        'source': 'google_drive'
                    })
                except Exception as e:
                    logger.warning(f"Error processing file {file.get('name', 'unknown')}: {e}")
            
            logger.info(f"Found {len(files_info)} files in Google Drive")
            return files_info
            
        except HttpError as e:
            logger.error(f"Failed to list Google Drive files: {e}")
            raise GoogleDriveError(f"Failed to list files: {e}")
        except Exception as e:
            logger.error(f"Unexpected error listing Google Drive files: {e}")
            raise GoogleDriveError(f"Unexpected error: {e}")
    
    def download_file(self, file_id: str, file_name: str) -> bytes:
        \"\"\"
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file (for logging)
            
        Returns:
            File content as bytes
        \"\"\"
        if not self.service:
            if not self.authenticate():
                raise GoogleDriveError("Failed to authenticate with Google Drive")
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            file_content = file_buffer.getvalue()
            logger.info(f"Downloaded file {file_name} ({len(file_content)} bytes)")
            return file_content
            
        except HttpError as e:
            logger.error(f"Failed to download file {file_name}: {e}")
            raise GoogleDriveError(f"Failed to download {file_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error downloading {file_name}: {e}")
            raise GoogleDriveError(f"Unexpected error downloading {file_name}: {e}")
    
    def download_file_to_path(self, file_id: str, file_name: str, local_path: str) -> str:
        \"\"\"
        Download a file from Google Drive to local path.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name of the file
            local_path: Local directory to save the file
            
        Returns:
            Path to the downloaded file
        \"\"\"
        file_content = self.download_file(file_id, file_name)
        
        # Ensure local directory exists
        os.makedirs(local_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(local_path, file_name)
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"Saved file to {file_path}")
        return file_path
    
    def sync_files(self, local_directory: str, force_download: bool = False) -> Dict[str, any]:
        \"\"\"
        Synchronize Google Drive files to local directory.
        
        Args:
            local_directory: Local directory to sync files to
            force_download: Force download even if file exists locally
            
        Returns:
            Sync statistics
        \"\"\"
        if not self.service:
            if not self.authenticate():
                raise GoogleDriveError("Failed to authenticate with Google Drive")
        
        logger.info(f"Starting Google Drive sync to {local_directory}")
        
        stats = {
            'total_files': 0,
            'downloaded': 0,
            'skipped': 0,
            'errors': 0,
            'sync_time': datetime.now().isoformat()
        }
        
        try:
            # Get list of files from Google Drive
            drive_files = self.list_files()
            stats['total_files'] = len(drive_files)
            
            # Ensure local directory exists
            os.makedirs(local_directory, exist_ok=True)
            
            for file_info in drive_files:
                try:
                    local_path = os.path.join(local_directory, file_info['name'])
                    
                    # Check if file needs to be downloaded
                    should_download = force_download
                    
                    if not should_download and os.path.exists(local_path):
                        # Compare modification times
                        local_mtime = datetime.fromtimestamp(os.path.getmtime(local_path))
                        drive_mtime = datetime.fromisoformat(file_info['modified_time'].replace('Z', '+00:00'))
                        
                        # Convert to same timezone for comparison
                        if drive_mtime.replace(tzinfo=None) > local_mtime:
                            should_download = True
                    else:
                        should_download = True
                    
                    if should_download:
                        self.download_file_to_path(
                            file_info['id'], 
                            file_info['name'], 
                            local_directory
                        )
                        stats['downloaded'] += 1
                    else:
                        stats['skipped'] += 1
                        logger.debug(f"Skipped {file_info['name']} (up to date)")
                        
                except Exception as e:
                    logger.error(f"Error syncing file {file_info.get('name', 'unknown')}: {e}")
                    stats['errors'] += 1
            
            self._last_sync = datetime.now()
            logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync Google Drive files: {e}")
            raise GoogleDriveError(f"Sync failed: {e}")
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        \"\"\"Get file extension from MIME type.\"\"\"
        mime_to_ext = {
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/msword': '.doc',
            'application/pdf': '.pdf'
        }
        return mime_to_ext.get(mime_type, '')
    
    def get_last_sync_time(self) -> Optional[datetime]:
        \"\"\"Get the last sync timestamp.\"\"\"
        return self._last_sync
    
    def is_sync_needed(self) -> bool:
        \"\"\"Check if sync is needed based on configured interval.\"\"\"
        if not self._last_sync:
            return True
        
        time_since_sync = datetime.now() - self._last_sync
        return time_since_sync.total_seconds() > settings.google_drive_sync_interval