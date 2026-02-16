"""Google Photos source adapter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from album_printer.sources.adapter import SourceAdapter
from album_printer.sources.google_photos_auth import GooglePhotosAuth
from album_printer.sources.google_photos_client import GooglePhotosClient
from album_printer.sources.models import SourceAsset, SourceLoadResult


class GooglePhotosSource(SourceAdapter):
    """Source adapter for loading images from Google Photos.

    This implementation provides:
    - OAuth2 authentication
    - Album listing and selection
    - Photo download to local cache
    - Metadata extraction (datetime, location)
    - Stable asset ID based on Google Photo ID
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        credentials_path: Path | None = None,
        token_path: Path | None = None,
    ) -> None:
        """Initialize Google Photos source.

        Args:
            cache_dir: Directory for caching downloaded photos
            credentials_path: Path to OAuth2 credentials JSON
            token_path: Path to store authentication tokens
        """
        self.cache_dir = (
            cache_dir or Path.home() / ".cache" / "album_printer" / "google_photos"
        )
        self.auth = GooglePhotosAuth(credentials_path, token_path)
        self.client: GooglePhotosClient | None = None

    def get_source_id(self) -> str:
        """Return 'google_photos' as the source identifier."""
        return "google_photos"

    def get_display_name(self) -> str:
        """Return 'Google Photos' as the display name."""
        return "Google Photos"

    def can_load(self, params: dict[str, Any]) -> bool:
        """Check if Google Photos can be loaded.

        Args:
            params: Should contain 'album_id' for the album to load

        Returns:
            True if authenticated and album_id is provided
        """
        if not params.get("album_id"):
            return False

        # Check if authenticated
        return self.auth.is_authenticated()

    def authenticate(self) -> bool:
        """Perform authentication flow.

        Returns:
            True if authentication succeeded
        """
        try:
            self.auth.authenticate()
            return True
        except Exception:
            return False

    def load(self, params: dict[str, Any]) -> SourceLoadResult:
        """Load images from Google Photos.

        Args:
            params: Must contain 'album_id' for the album to load

        Returns:
            SourceLoadResult with assets from Google Photos

        Raises:
            ValueError: If album_id is missing or authentication failed
            RuntimeError: If photo loading fails
        """
        album_id = params.get("album_id")
        if not album_id:
            raise ValueError("Missing required parameter: album_id")

        # Ensure authenticated
        if not self.auth.is_authenticated():
            raise ValueError("Not authenticated. Please authenticate first.")

        # Create client if needed
        if self.client is None:
            self.client = GooglePhotosClient(self.auth)

        try:
            # Fetch photos from album
            photos = self.client.get_album_photos(album_id)

            # Download and create assets
            assets = []
            for photo in photos:
                asset = self._create_asset_from_photo(photo)
                if asset:
                    assets.append(asset)

            # Create metadata path for this album
            metadata_path = self.cache_dir / album_id

            return SourceLoadResult(
                assets=assets,
                source_id=self.get_source_id(),
                source_token=f"google_photos:{album_id}",
                metadata_path=metadata_path,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load Google Photos album: {e}") from e

    def _create_asset_from_photo(self, photo: dict[str, Any]) -> SourceAsset | None:
        """Create a SourceAsset from a Google Photos media item.

        Args:
            photo: Media item from Google Photos API

        Returns:
            SourceAsset or None if download failed
        """
        try:
            # Extract metadata
            metadata = self.client.get_photo_metadata(photo)
            photo_id = metadata["id"]
            filename = metadata.get("filename", f"{photo_id}.jpg")

            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Download photo to cache
            local_path = self.cache_dir / f"{photo_id}_{filename}"

            # Skip if already cached
            if not local_path.exists():
                download_url = self.client.get_photo_url(photo)
                if not download_url:
                    return None

                # Download the photo
                response = requests.get(download_url, timeout=30)
                response.raise_for_status()

                with open(local_path, "wb") as f:
                    f.write(response.content)

            # Parse datetime
            datetime_hint = None
            if metadata.get("creation_time"):
                try:
                    # Google Photos returns ISO 8601 format
                    datetime_hint = datetime.fromisoformat(
                        metadata["creation_time"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            # Create asset
            return SourceAsset(
                asset_id=photo_id,  # Use Google Photos ID as stable identifier
                display_name=filename,
                local_path=local_path,
                datetime_hint=datetime_hint,
                location=metadata.get("location"),
            )
        except Exception:
            return None  # Skip photos that fail to download
