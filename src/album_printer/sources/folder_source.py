"""Folder-based source adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from album_printer.sources.adapter import SourceAdapter
from album_printer.sources.models import SourceAsset, SourceLoadResult

# Supported file extensions for images
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
METADATA_FILENAME = ".album_printer.json"


class FolderSource(SourceAdapter):
    """Source adapter for loading images from a local folder."""

    def get_source_id(self) -> str:
        """Return 'folder' as the source identifier."""
        return "folder"

    def get_display_name(self) -> str:
        """Return 'Folder' as the display name."""
        return "Folder"

    def can_load(self, params: dict[str, Any]) -> bool:
        """Check if a valid folder path is provided.
        
        Args:
            params: Expected to contain 'path' key with folder path
            
        Returns:
            True if path exists and is a directory
        """
        path = params.get("path")
        if not path:
            return False
        
        folder_path = Path(path)
        return folder_path.exists() and folder_path.is_dir()

    def load(self, params: dict[str, Any]) -> SourceLoadResult:
        """Load images from a folder.
        
        Args:
            params: Must contain 'path' key with folder path
            
        Returns:
            SourceLoadResult with assets from the folder
            
        Raises:
            ValueError: If path is invalid or not a directory
        """
        path = params.get("path")
        if not path:
            raise ValueError("Missing required parameter: path")
        
        folder_path = Path(path)
        if not folder_path.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")
        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
        
        # Scan for image files
        image_files = sorted(
            [
                p
                for p in folder_path.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
        )
        
        # Convert to SourceAsset objects
        assets = []
        for image_path in image_files:
            asset = SourceAsset(
                asset_id=self._generate_asset_id(image_path),
                display_name=image_path.name,
                local_path=image_path,
                datetime_hint=None,  # Will be extracted later from EXIF
                location=None,  # Will be extracted later from EXIF or Google
            )
            assets.append(asset)
        
        # Use folder path as source token
        source_token = str(folder_path.resolve())
        
        # Metadata path is the folder itself
        metadata_path = folder_path
        
        return SourceLoadResult(
            assets=assets,
            source_id=self.get_source_id(),
            source_token=source_token,
            metadata_path=metadata_path,
        )

    def _generate_asset_id(self, image_path: Path) -> str:
        """Generate a stable asset ID for a local file.
        
        For folder source, we use a hash of the absolute path to ensure
        stability while being unique within the folder.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Stable asset ID string
        """
        # Use filename as primary identifier for folder source
        # This maintains compatibility with existing filename-based metadata
        return image_path.name
