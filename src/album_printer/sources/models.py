"""Core data models for source abstraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class SourceAsset:
    """Normalized asset representation from any source.

    Attributes:
        asset_id: Stable unique identifier for this asset (metadata key)
        display_name: Human-readable name shown in UI
        local_path: Path to image file on local filesystem (for render)
        datetime_hint: Optional datetime associated with the asset
        location: Optional location (e.g., "37.7749,-122.4194")
    """

    asset_id: str
    display_name: str
    local_path: Path
    datetime_hint: datetime | None = None
    location: str | None = None


@dataclass
class SourceLoadResult:
    """Result of loading assets from a source.

    Attributes:
        assets: List of loaded assets
        source_id: Identifier for the source type (e.g., "folder", "google_photos")
        source_token: Token/identifier for this specific source instance
        metadata_path: Path where metadata should be stored for this source
    """

    assets: list[SourceAsset]
    source_id: str
    source_token: str
    metadata_path: Path
