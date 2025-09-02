# Google Drive Integration

This document describes how to set up and use Google Drive integration with the HR AI system.

## Overview

The HR AI system supports automatic integration with Google Drive for document storage and processing. When enabled, the system will:

1. **Prioritize Google Drive**: If Google Drive access is available, the system works exclusively with Google Drive
2. **Fallback to Local**: If Google Drive is not accessible, the system automatically falls back to local document storage
3. **Automatic Sync**: Periodically synchronizes documents from Google Drive to local cache for processing

## Benefits

- **Centralized Storage**: All HR documents stored in Google Drive are automatically processed
- **Real-time Updates**: Documents are synchronized based on modification times
- **Access Control**: Leverage Google Drive's existing permission system
- **Backup**: Local cache provides redundancy
- **Seamless Fallback**: Automatic fallback to local storage if Google Drive is unavailable

## Setup Instructions

### 1. Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing project
3. Enable the Google Drive API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

### 2. Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application" as the application type
4. Give it a name (e.g., "HR AI System")
5. Download the credentials JSON file

### 3. Configure the Application

1. Place the downloaded credentials file in your project directory
2. Update your `.env` file:

```env
# Google Drive Integration
ENABLE_GOOGLE_DRIVE=true
GOOGLE_CREDENTIALS_FILE=path/to/your/credentials.json
GOOGLE_TOKEN_FILE=token.json
GOOGLE_DRIVE_FOLDER_ID=optional_specific_folder_id
GOOGLE_DRIVE_SYNC_INTERVAL=300
```

### 4. Run Setup Script

```bash
python setup_google_drive.py
```

This script will:
- Check your configuration
- Test the Google Drive connection
- Guide you through the OAuth flow
- Verify file access

### 5. First Authentication

When you first run the application or setup script:
1. A browser window will open
2. Sign in with your Google account
3. Grant permission to access Google Drive
4. The system will save authentication tokens for future use

## Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `ENABLE_GOOGLE_DRIVE` | Enable/disable Google Drive integration | `false` |
| `GOOGLE_CREDENTIALS_FILE` | Path to OAuth2 credentials JSON file | `credentials.json` |
| `GOOGLE_TOKEN_FILE` | Path to store authentication tokens | `token.json` |
| `GOOGLE_DRIVE_FOLDER_ID` | Specific folder ID to monitor (optional) | None (root) |
| `GOOGLE_DRIVE_SYNC_INTERVAL` | Sync interval in seconds | `300` (5 minutes) |

### Getting Folder ID

To restrict access to a specific Google Drive folder:
1. Open the folder in Google Drive
2. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`
3. Set `GOOGLE_DRIVE_FOLDER_ID` in your `.env` file

## Usage

### Web Interface

The web interface includes Google Drive controls:

1. **Storage Status**: View current storage backend and connection status
2. **Synchronization**: Manually trigger sync or force full sync
3. **Refresh Connection**: Refresh Google Drive authentication

### API Endpoints

- `GET /api/storage-status` - Get storage backend status
- `POST /api/sync-google-drive` - Trigger Google Drive sync
- `POST /api/refresh-storage` - Refresh storage connection

### Automatic Operation

When Google Drive is enabled and connected:
- The system automatically scans Google Drive for supported documents
- Documents are processed directly from Google Drive or cached locally
- Sync occurs automatically based on the configured interval
- If Google Drive becomes unavailable, the system falls back to local storage

## Supported File Types

The integration supports the same file types as the local parser:
- `.docx` - Microsoft Word documents
- `.doc` - Legacy Microsoft Word documents  
- `.pdf` - PDF documents

## File Processing

### From Google Drive
1. System lists files in the configured folder
2. Downloads files to temporary location for processing
3. Processes documents using standard analyzers
4. Results include Google Drive metadata

### Caching Strategy
- Modified files are downloaded to local cache
- Cache is updated based on file modification times
- Local cache provides backup if Google Drive is unavailable

## Security Considerations

1. **OAuth2 Flow**: Uses secure OAuth2 for authentication
2. **Read-Only Access**: System only requests read access to Google Drive
3. **Token Storage**: Authentication tokens are stored locally
4. **Folder Restrictions**: Can be restricted to specific folders

## Troubleshooting

### Common Issues

**"Authentication failed"**
- Verify credentials file exists and is valid
- Check that Google Drive API is enabled
- Ensure OAuth2 client is configured correctly

**"Connection test failed"**
- Check internet connectivity
- Verify Google Drive permissions
- Try refreshing the connection

**"No files found"**
- Check folder ID is correct
- Verify folder contains supported file types
- Ensure Google account has access to the folder

### Debug Mode

Enable debug logging to troubleshoot issues:

```env
DEBUG=true
```

### Reset Authentication

To reset Google Drive authentication:
1. Delete the token file (default: `token.json`)
2. Restart the application
3. Complete the OAuth flow again

## Migration from Local Storage

To migrate from local document storage to Google Drive:

1. Upload your existing documents to Google Drive
2. Configure Google Drive integration
3. Run initial sync
4. Verify all documents are accessible
5. Optionally move local documents to backup folder

## Performance Considerations

- **Initial Sync**: First sync may take time depending on document count
- **Incremental Updates**: Subsequent syncs only process changed files
- **Cache Size**: Local cache grows with document count
- **Network Usage**: Consider bandwidth for document downloads

## Monitoring

Monitor Google Drive integration through:
- Web interface storage status
- Application logs
- Sync statistics
- File processing metrics

## Backup Strategy

- Google Drive serves as primary storage
- Local cache provides immediate backup
- Consider additional backup of critical documents
- Monitor sync status regularly