"""Google Photos source adapter (stub for future implementation)."""

from __future__ import annotations

from typing import Any

from album_printer.sources.adapter import SourceAdapter
from album_printer.sources.models import SourceLoadResult


class GooglePhotosSource(SourceAdapter):
    """Source adapter for loading images from Google Photos.

    This is a stub implementation. Full Google Photos integration will include:
    - OAuth2 authentication
    - Album listing and selection
    - Photo download to local cache
    - Metadata extraction (datetime, location)
    - Stable asset ID based on Google Photo ID
    """

    def get_source_id(self) -> str:
        """Return 'google_photos' as the source identifier."""
        return "google_photos"

    def get_display_name(self) -> str:
        """Return 'Google Photos' as the display name."""
        return "Google Photos"

    def can_load(self, params: dict[str, Any]) -> bool:
        """Check if Google Photos can be loaded.

        Args:
            params: Should contain authentication and album selection info

        Returns:
            False for now (not yet implemented)
        """
        # TODO: Implement when Google Photos integration is ready
        return False

    def load(self, params: dict[str, Any]) -> SourceLoadResult:
        """Load images from Google Photos.

        Args:
            params: Google Photos specific parameters

        Returns:
            SourceLoadResult with assets from Google Photos

        Raises:
            NotImplementedError: This feature is not yet implemented
        """
        raise NotImplementedError("Google Photos source is not yet implemented")
