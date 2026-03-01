from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage


class ThumbnailWorkerSignals(QObject):
    finished = Signal(object, int, object)


class ThumbnailWorker(QRunnable):
    def __init__(
        self,
        path: Path,
        generation: int,
        cache_path: Path,
        legacy_cache_path: Path | None = None,
        *,
        load_image_as_rgb_fn: Callable[[Path], Image.Image],
        thumbnail_size: int,
    ) -> None:
        super().__init__()
        self.path = path
        self.generation = generation
        self.cache_path = cache_path
        self.legacy_cache_path = legacy_cache_path
        self.load_image_as_rgb_fn = load_image_as_rgb_fn
        self.thumbnail_size = int(thumbnail_size)
        self.signals = ThumbnailWorkerSignals()

    def run(self) -> None:
        image: QImage | None = None

        source_mtime_ns: int | None = None
        try:
            source_mtime_ns = self.path.stat().st_mtime_ns
        except OSError:
            source_mtime_ns = None

        if source_mtime_ns is not None:
            candidate_paths: list[Path] = [self.cache_path]
            if self.legacy_cache_path is not None:
                candidate_paths.append(self.legacy_cache_path)
            for candidate in candidate_paths:
                if (
                    self.legacy_cache_path is not None
                    and candidate == self.legacy_cache_path
                    and not self.cache_path.exists()
                ):
                    try:
                        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                        candidate.replace(self.cache_path)
                        candidate = self.cache_path
                    except OSError:
                        pass

                try:
                    cache_mtime_ns = candidate.stat().st_mtime_ns
                    if cache_mtime_ns < source_mtime_ns:
                        continue
                    cached = QImage(str(candidate))
                    if cached.isNull():
                        continue
                    if candidate != self.cache_path:
                        try:
                            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                            cached.save(str(self.cache_path), "PNG")
                        except OSError:
                            pass
                    self.signals.finished.emit(self.path, self.generation, cached)
                    return
                except OSError:
                    continue

        try:
            thumb = self.load_image_as_rgb_fn(self.path)
            thumb.thumbnail(
                (self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS
            )
            image = QImage(ImageQt(thumb))
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                thumb.save(self.cache_path, format="PNG")
            except OSError:
                pass
        except OSError:
            image = None

        self.signals.finished.emit(self.path, self.generation, image)


__all__ = [
    "ThumbnailWorker",
    "ThumbnailWorkerSignals",
]
