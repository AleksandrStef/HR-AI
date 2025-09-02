#!/usr/bin/env python3
"""
Install Google Drive dependencies for HR AI system.
"""

import subprocess
import sys

def install_google_drive_deps():
    """Install Google Drive integration dependencies."""
    
    dependencies = [
        'google-api-python-client==2.110.0',
        'google-auth==2.24.0', 
        'google-auth-oauthlib==1.1.0',
        'google-auth-httplib2==0.1.1'
    ]
    
    print("🚀 Installing Google Drive Integration Dependencies")
    print("=" * 55)
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', dep
            ])
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            return False
    
    print("\n✅ All Google Drive dependencies installed successfully!")
    print("\nNext steps:")
    print("1. Configure Google Drive API credentials")
    print("2. Update your .env file with Google Drive settings")
    print("3. Run: python setup_google_drive.py")
    
    return True

if __name__ == "__main__":
    install_google_drive_deps()