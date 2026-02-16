"""Base adapter interface for image sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from album_printer.sources.models import SourceLoadResult


class SourceAdapter(ABC):
    """Base interface for source adapters.

    Each adapter loads assets from a specific source type and returns
    normalized SourceAsset objects with local file paths.
    """

    @abstractmethod
    def get_source_id(self) -> str:
        """Return unique identifier for this source type.

        Examples: 'folder', 'google_photos'
        """
        pass

    @abstractmethod
    def get_display_name(self) -> str:
        """Return human-readable name for this source.

        Examples: 'Folder', 'Google Photos'
        """
        pass

    @abstractmethod
    def can_load(self, params: dict[str, Any]) -> bool:
        """Check if this adapter can load from the given parameters.

        Args:
            params: Source-specific parameters (e.g., {'path': '/photos'} for folder)

        Returns:
            True if this adapter can handle the load request
        """
        pass

    @abstractmethod
    def load(self, params: dict[str, Any]) -> SourceLoadResult:
        """Load assets from the source.

        Args:
            params: Source-specific parameters

        Returns:
            SourceLoadResult with loaded assets and metadata

        Raises:
            ValueError: If parameters are invalid or source cannot be loaded
        """
        pass
