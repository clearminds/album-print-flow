#!/usr/bin/env python3
"""Example script demonstrating Google Photos integration.

This script shows how to:
1. Authenticate with Google Photos
2. List available albums
3. Load photos from an album
4. Access photo metadata

Before running:
1. Follow setup instructions in GOOGLE_PHOTOS_SETUP.md
2. Place your credentials file at ~/.config/album_printer/google_photos_credentials.json
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from album_printer.sources import get_source_registry  # noqa: E402
from album_printer.sources.google_photos_auth import GooglePhotosAuth  # noqa: E402
from album_printer.sources.google_photos_client import GooglePhotosClient  # noqa: E402


def main():
    """Main example function."""
    print("=" * 70)
    print("Google Photos Integration Example")
    print("=" * 70)
    print()

    # Setup paths
    config_dir = Path.home() / ".config" / "album_printer"
    credentials_path = config_dir / "google_photos_credentials.json"
    token_path = config_dir / ".google_photos_token.pickle"

    # Check if credentials exist
    if not credentials_path.exists():
        print(f"❌ Credentials not found at: {credentials_path}")
        print()
        print("Please follow the setup instructions in GOOGLE_PHOTOS_SETUP.md")
        print(
            "to create OAuth credentials and place them at the path shown above."
        )
        return 1

    print(f"✓ Found credentials at: {credentials_path}")
    print()

    # Step 1: Authentication
    print("Step 1: Authenticating with Google Photos...")
    print("-" * 70)

    auth = GooglePhotosAuth(
        credentials_path=credentials_path, token_path=token_path
    )

    if not auth.is_authenticated():
        print("No valid token found. Starting authentication flow...")
        print("A browser window will open. Please sign in and grant permissions.")
        print()
        try:
            auth.authenticate()
            print("✓ Authentication successful!")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return 1
    else:
        print("✓ Already authenticated (using cached token)")

    print()

    # Step 2: List albums
    print("Step 2: Listing your Google Photos albums...")
    print("-" * 70)

    client = GooglePhotosClient(auth)

    try:
        albums = client.list_albums()
        print(f"✓ Found {len(albums)} albums:")
        print()

        for i, album in enumerate(albums[:10], 1):  # Show first 10
            title = album.get("title", "Untitled")
            album_id = album.get("id", "unknown")
            count = album.get("mediaItemsCount", "?")
            print(f"  {i}. {title}")
            print(f"     ID: {album_id}")
            print(f"     Photos: {count}")
            print()

        if len(albums) > 10:
            print(f"  ... and {len(albums) - 10} more albums")
            print()

    except Exception as e:
        print(f"❌ Failed to list albums: {e}")
        return 1

    # Step 3: Load photos from first album (if available)
    if albums:
        print("Step 3: Loading photos from first album...")
        print("-" * 70)

        album = albums[0]
        album_id = album.get("id")
        album_title = album.get("title", "Untitled")

        print(f"Loading from: {album_title}")
        print()

        # Get source from registry
        registry = get_source_registry()
        google_source = registry.get_adapter("google_photos")

        # Set authentication
        google_source.auth = auth
        google_source.client = client

        try:
            # Load photos
            result = google_source.load({"album_id": album_id})

            print(f"✓ Loaded {len(result.assets)} photos")
            print(f"  Source: {result.source_id}")
            print(f"  Token: {result.source_token}")
            print(f"  Metadata path: {result.metadata_path}")
            print()

            # Show first 5 photos
            print("First 5 photos:")
            for i, asset in enumerate(result.assets[:5], 1):
                print(f"\n  {i}. {asset.display_name}")
                print(f"     Asset ID: {asset.asset_id}")
                print(f"     Local path: {asset.local_path}")
                print(f"     Datetime: {asset.datetime_hint or 'N/A'}")
                print(f"     Location: {asset.location or 'N/A'}")

            if len(result.assets) > 5:
                print(f"\n  ... and {len(result.assets) - 5} more photos")

            print()
            print("✓ All photos cached locally for future use")

        except Exception as e:
            print(f"❌ Failed to load photos: {e}")
            return 1

    print()
    print("=" * 70)
    print("Example completed successfully!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  - Photos are cached in:", google_source.cache_dir)
    print("  - Use these photos in Album Print Flow for printing")
    print("  - Check GOOGLE_PHOTOS_SETUP.md for more usage examples")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
