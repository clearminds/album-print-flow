"""Registry for source adapters."""

from __future__ import annotations

from typing import Any

from album_printer.sources.adapter import SourceAdapter
from album_printer.sources.models import SourceLoadResult


class SourceRegistry:
    """Registry for managing source adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        """Register a source adapter.

        Args:
            adapter: The adapter to register
        """
        source_id = adapter.get_source_id()
        if source_id in self._adapters:
            raise ValueError(f"Source adapter '{source_id}' already registered")
        self._adapters[source_id] = adapter

    def get_adapter(self, source_id: str) -> SourceAdapter | None:
        """Get an adapter by its source ID.

        Args:
            source_id: The source identifier

        Returns:
            The adapter, or None if not found
        """
        return self._adapters.get(source_id)

    def list_adapters(self) -> list[SourceAdapter]:
        """List all registered adapters.

        Returns:
            List of all registered adapters
        """
        return list(self._adapters.values())

    def load_from_source(
        self, source_id: str, params: dict[str, Any]
    ) -> SourceLoadResult:
        """Load assets using the specified source adapter.

        Args:
            source_id: The source identifier
            params: Source-specific parameters

        Returns:
            SourceLoadResult with loaded assets

        Raises:
            ValueError: If source not found or cannot load
        """
        adapter = self.get_adapter(source_id)
        if adapter is None:
            raise ValueError(f"Unknown source: {source_id}")

        if not adapter.can_load(params):
            raise ValueError(f"Source '{source_id}' cannot load with given parameters")

        return adapter.load(params)


# Global registry instance
_registry: SourceRegistry | None = None


def get_source_registry() -> SourceRegistry:
    """Get the global source registry instance.

    Returns:
        The global SourceRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = SourceRegistry()
        _register_builtin_adapters(_registry)
    return _registry


def _register_builtin_adapters(registry: SourceRegistry) -> None:
    """Register built-in source adapters.

    Args:
        registry: The registry to register adapters with
    """
    # Import adapters here to avoid circular dependencies
    from album_printer.sources.folder_source import FolderSource
    from album_printer.sources.google_photos_source import GooglePhotosSource

    registry.register(FolderSource())
    registry.register(GooglePhotosSource())
