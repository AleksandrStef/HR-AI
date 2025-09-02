#!/usr/bin/env python3
"""
Test script for Google Drive integration.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hr_ai.analyzers.hr_analyzer import HRAnalyzer
from hr_ai.parsers.enhanced_document_parser import EnhancedDocumentParser
from config.settings import settings

async def test_google_drive_integration():
    """Test Google Drive integration functionality."""
    
    print("🧪 Testing Google Drive Integration")
    print("=" * 50)
    
    # Test 1: Check settings
    print("1. Checking settings...")
    print(f"   Google Drive enabled: {settings.enable_google_drive}")
    print(f"   Credentials file: {settings.google_credentials_file}")
    print(f"   Token file: {settings.google_token_file}")
    print(f"   Folder ID: {settings.google_drive_folder_id or 'Root folder'}")
    
    # Test 2: Initialize enhanced document parser
    print("\n2. Initializing enhanced document parser...")
    parser = EnhancedDocumentParser()
    
    # Test 3: Check storage status
    print("\n3. Getting storage status...")
    status = parser.get_storage_status()
    print(f"   Storage backend: {status['storage_backend']}")
    print(f"   Google Drive enabled: {status['google_drive_enabled']}")
    print(f"   Google Drive connected: {status['google_drive_connected']}")
    print(f"   Local directory: {status['local_directory']}")
    
    # Test 4: Scan directory
    print("\n4. Scanning documents...")
    try:
        files = parser.scan_directory()
        print(f"   Found {len(files)} files")
        
        if files:
            print("   First few files:")
            for i, file_info in enumerate(files[:3]):
                print(f"     {i+1}. {file_info.get('employee_name', 'Unknown')} - {file_info.get('file_path', 'Unknown path')}")
    except Exception as e:
        print(f"   Error scanning: {e}")
    
    # Test 5: HR Analyzer integration
    print("\n5. Testing HR Analyzer integration...")
    try:
        analyzer = HRAnalyzer()
        storage_status = analyzer.get_storage_status()
        print(f"   HR Analyzer storage backend: {storage_status['storage_backend']}")
        
        # Test sync if Google Drive is available
        if storage_status['storage_backend'] == 'google_drive':
            print("\n6. Testing Google Drive sync...")
            sync_result = analyzer.sync_google_drive(force=False)
            if sync_result:
                print(f"   Sync completed: {sync_result}")
            else:
                print("   Sync not needed or not available")
        
    except Exception as e:
        print(f"   Error with HR Analyzer: {e}")
    
    # Test 6: Test force refresh
    print("\n7. Testing connection refresh...")
    try:
        success = parser.force_refresh_connection()
        print(f"   Connection refresh: {'Success' if success else 'Failed'}")
    except Exception as e:
        print(f"   Error refreshing connection: {e}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_google_drive_integration())