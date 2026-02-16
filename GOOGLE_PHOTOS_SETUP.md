# Google Photos Integration Setup Guide

This guide explains how to set up and use Google Photos integration with Album Print Flow.

## Prerequisites

1. **Google Cloud Project**: You need a Google Cloud project with Photos Library API enabled
2. **OAuth2 Credentials**: Desktop application credentials from Google Cloud Console

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Photos Library API**:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Photos Library API"
   - Click "Enable"

## Step 2: Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop app" as the application type
4. Give it a name (e.g., "Album Print Flow")
5. Click "Create"
6. Download the credentials JSON file
7. Save it as `google_photos_credentials.json` in your home directory or a secure location

## Step 3: Configure Album Print Flow

### Option 1: Default Location
Place your credentials file at:
```
~/.config/album_printer/google_photos_credentials.json
```

### Option 2: Custom Location
You can specify a custom location when using the GooglePhotosSource:

```python
from pathlib import Path
from album_printer.sources import get_source_registry

# Get the Google Photos source
registry = get_source_registry()
google_source = registry.get_adapter("google_photos")

# Set custom credentials path
google_source.auth.credentials_path = Path("/path/to/your/credentials.json")
```

## Step 4: First-Time Authentication

1. When you first load photos from Google Photos, a browser window will open
2. Sign in with your Google account
3. Grant the requested permissions (read-only access to your photos)
4. The authentication token will be saved for future use

## Using Google Photos in Album Print Flow

### Basic Usage

```python
from album_printer.sources import get_source_registry

# Get registry and Google Photos adapter
registry = get_source_registry()
google_source = registry.get_adapter("google_photos")

# Authenticate (only needed once)
google_source.authenticate()

# Load photos from an album
result = google_source.load({"album_id": "your-album-id-here"})

# Access the photos
for asset in result.assets:
    print(f"Photo: {asset.display_name}")
    print(f"  Location: {asset.location or 'No location'}")
    print(f"  Local path: {asset.local_path}")
```

### Finding Album IDs

To get album IDs, you can use the Google Photos client:

```python
from album_printer.sources.google_photos_auth import GooglePhotosAuth
from album_printer.sources.google_photos_client import GooglePhotosClient
from pathlib import Path

# Setup authentication
auth = GooglePhotosAuth(
    credentials_path=Path("~/.config/album_printer/google_photos_credentials.json").expanduser()
)
auth.authenticate()

# Create client
client = GooglePhotosClient(auth)

# List all albums
albums = client.list_albums()
for album in albums:
    print(f"Album: {album['title']}")
    print(f"  ID: {album['id']}")
    print(f"  Photos: {album.get('mediaItemsCount', 'Unknown')}")
```

## Cached Photos

Downloaded photos are cached in:
```
~/.cache/album_printer/google_photos/
```

This avoids re-downloading photos each time you open an album.

## Troubleshooting

### "Credentials file not found"
- Ensure the credentials JSON file exists at the specified location
- Check file permissions

### "Authentication failed"
- Make sure the Photos Library API is enabled in your Google Cloud project
- Verify your credentials file is valid and for a "Desktop app" type
- Try clearing cached tokens: `rm ~/.cache/album_printer/.google_photos_token.pickle`

### "Failed to list albums" or "Failed to get album photos"
- Check your internet connection
- Verify you granted the necessary permissions during authentication
- Try re-authenticating by clearing the token file

### Rate Limiting
Google Photos API has usage quotas. If you hit rate limits:
- Wait before making more requests
- Consider implementing request batching for large operations

## Security Considerations

### Credentials File
- **Never commit** your `google_photos_credentials.json` to version control
- Store it securely with appropriate file permissions (e.g., `chmod 600`)
- Do not share this file with others

### Token Storage
- Authentication tokens are stored locally in pickle format
- Tokens are encrypted by Google's authentication library
- Clear tokens if you suspect unauthorized access

### Scopes
The application requests **read-only** access to your photos:
- Scope: `https://www.googleapis.com/auth/photoslibrary.readonly`
- This cannot modify or delete your photos
- Only allows reading photo data and downloading

## Advanced Configuration

### Custom Cache Directory

```python
from pathlib import Path

google_source = registry.get_adapter("google_photos")
google_source.cache_dir = Path("/custom/cache/location")
```

### Custom Token Storage

```python
from pathlib import Path

google_source = registry.get_adapter("google_photos")
google_source.auth.token_path = Path("/custom/token/location/.token.pickle")
```

## API Limits and Quotas

Google Photos API has the following limits (as of 2024):
- **10,000 requests per day** per project
- **10 queries per second** per user

For typical usage (loading albums for printing), these limits should be sufficient.

## Privacy

Album Print Flow:
- Only requests read-only access to your photos
- Downloads photos temporarily for printing purposes
- Does not upload, modify, or share your photos
- Stores authentication tokens locally on your machine
- Does not send data to third parties

## Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Review Google Photos API documentation: https://developers.google.com/photos
3. Open an issue on the Album Print Flow repository with:
   - Error messages (excluding any credentials)
   - Steps to reproduce
   - Your environment (OS, Python version)
