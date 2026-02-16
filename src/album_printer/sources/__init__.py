"""Source abstraction layer for loading images from various sources."""

from album_printer.sources.adapter import SourceAdapter
from album_printer.sources.models import SourceAsset, SourceLoadResult
from album_printer.sources.registry import SourceRegistry, get_source_registry

__all__ = [
    "SourceAdapter",
    "SourceAsset",
    "SourceLoadResult",
    "SourceRegistry",
    "get_source_registry",
]
