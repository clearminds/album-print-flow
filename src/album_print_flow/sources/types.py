from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class SourceAsset:
    key: str
    local_path: Path
    display_name: str
    source_photo_id: str | None = None
    captured_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_data: dict[str, object] | None = None


@dataclass(slots=True)
class SourceLoadResult:
    source_id: str
    source_label: str
    context_id: str
    context_label: str
    assets: list[SourceAsset]
    metadata_root: Path | None
    is_new_context: bool
