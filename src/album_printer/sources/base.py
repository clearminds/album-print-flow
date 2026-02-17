from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from PySide6.QtWidgets import QWidget

from album_printer.sources.types import SourceLoadResult


class SourceAdapter(Protocol):
    source_id: str
    label: str

    def load_via_ui(self, parent: QWidget | None = None) -> SourceLoadResult | None: ...

    def refresh(
        self,
        context_id: str,
        preferred_path: Path | None = None,
    ) -> SourceLoadResult: ...


class SourceRegistry:
    def __init__(self, adapters: Sequence[SourceAdapter]) -> None:
        self._adapters = {adapter.source_id: adapter for adapter in adapters}

    def all(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def get(self, source_id: str) -> SourceAdapter | None:
        return self._adapters.get(source_id)
