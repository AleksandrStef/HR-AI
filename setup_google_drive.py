#!/usr/bin/env python3
"""
Google Drive setup script for HR AI system.
Helps configure Google Drive integration.
"""

import os
import json
from pathlib import Path
from config.settings import settings

def setup_google_drive():
    """Setup Google Drive integration."""
    print("🚀 HR AI - Google Drive Integration Setup")
    print("=" * 50)
    
    # Check if Google Drive is enabled
    print(f"Google Drive enabled in settings: {settings.enable_google_drive}")
    
    if not settings.enable_google_drive:
        enable = input("Enable Google Drive integration? (y/n): ").lower().strip()
        if enable == 'y':
            print("\n📝 To enable Google Drive:")
            print("1. Set ENABLE_GOOGLE_DRIVE=true in your .env file")
            print("2. Restart the application")
            print("3. Run this setup script again")
            return
        else:
            print("Google Drive integration will remain disabled.")
            return
    
    print("\n📋 Google Drive Configuration:")
    print(f"Credentials file: {settings.google_credentials_file or 'Not configured'}")
    print(f"Token file: {settings.google_token_file}")
    print(f"Folder ID: {settings.google_drive_folder_id or 'Root folder'}")
    
    # Check credentials file
    if not settings.google_credentials_file or not os.path.exists(settings.google_credentials_file):
        print("\n❌ Google credentials file not found!")
        print("\n📖 To set up Google Drive API credentials:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a new project or select existing project")
        print("3. Enable Google Drive API")
        print("4. Create credentials (OAuth 2.0 Client ID)")
        print("5. Download the credentials JSON file")
        print("6. Place it in your project directory")
        print("7. Update GOOGLE_CREDENTIALS_FILE in .env file")
        
        cred_file = input("\nEnter path to credentials file (or press Enter to skip): ").strip()
        if cred_file and os.path.exists(cred_file):
            print(f"✅ Credentials file found: {cred_file}")
            print(f"Add this to your .env file: GOOGLE_CREDENTIALS_FILE={cred_file}")
        return
    
    print("✅ Credentials file found")
    
    # Test connection
    print("\n🔧 Testing Google Drive connection...")
    
    try:
        from src.hr_ai.integrations.google_drive import GoogleDriveClient
        
        client = GoogleDriveClient()
        
        print("Authenticating with Google Drive...")
        if client.authenticate():
            print("✅ Authentication successful!")
            
            print("Testing connection...")
            if client.test_connection():
                print("✅ Google Drive connection successful!")
                
                print("Listing files...")
                files = client.list_files()
                print(f"✅ Found {len(files)} files in Google Drive")
                
                if files:
                    print("\nFirst few files:")
                    for i, file_info in enumerate(files[:3]):
                        print(f"  {i+1}. {file_info['name']} ({file_info['size']} bytes)")
                
            else:
                print("❌ Connection test failed")
        else:
            print("❌ Authentication failed")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you've installed Google Drive dependencies:")
        print("pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n📝 Configuration Summary:")
    print("To complete setup, ensure your .env file contains:")
    print(f"ENABLE_GOOGLE_DRIVE=true")
    print(f"GOOGLE_CREDENTIALS_FILE=path/to/credentials.json")
    print(f"GOOGLE_DRIVE_FOLDER_ID=<optional_folder_id>")
    print("\nFor specific folder access, get folder ID from Google Drive URL:")
    print("https://drive.google.com/drive/folders/[FOLDER_ID]")

def check_environment():
    """Check current environment setup."""
    print("\n🔍 Environment Check:")
    
    env_vars = [
        'ENABLE_GOOGLE_DRIVE',
        'GOOGLE_CREDENTIALS_FILE', 
        'GOOGLE_DRIVE_FOLDER_ID',
        'GOOGLE_TOKEN_FILE'
    ]
    
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")
    
    # Check if .env file exists
    env_path = Path('.env')
    if env_path.exists():
        print(f"\n✅ .env file found: {env_path.absolute()}")
    else:
        print(f"\n❌ .env file not found. Create it from .env.example")

if __name__ == "__main__":
    check_environment()
    setup_google_drive()