from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal


class SourceRefreshWorkerSignals(QObject):
    finished = Signal(int, object, object, object)


class SourceRefreshWorker(QRunnable):
    def __init__(
        self,
        request_id: int,
        adapter: object,
        context_id: str,
        preferred_path: Path | None,
    ) -> None:
        super().__init__()
        self.request_id = int(request_id)
        self.adapter = adapter
        self.context_id = context_id
        self.preferred_path = preferred_path
        self.signals = SourceRefreshWorkerSignals()

    def run(self) -> None:
        try:
            refresh_method = getattr(self.adapter, "refresh", None)
            if not callable(refresh_method):
                raise RuntimeError("Active source does not support refresh")
            result = refresh_method(self.context_id, self.preferred_path)
            self.signals.finished.emit(
                self.request_id,
                result,
                None,
                self.preferred_path,
            )
        except Exception as error:
            self.signals.finished.emit(
                self.request_id,
                None,
                error,
                self.preferred_path,
            )


class SourceLoadWorkerSignals(QObject):
    finished = Signal(int, object, object, object)


class SourceLoadWorker(QRunnable):
    def __init__(
        self,
        request_id: int,
        adapter: object,
        context_id: str,
        payload: object = None,
    ) -> None:
        super().__init__()
        self.request_id = int(request_id)
        self.adapter = adapter
        self.context_id = context_id
        self.payload = payload
        self.signals = SourceLoadWorkerSignals()

    def run(self) -> None:
        try:
            refresh_method = getattr(self.adapter, "refresh", None)
            if not callable(refresh_method):
                raise RuntimeError("Active source does not support loading")
            result = refresh_method(self.context_id, None)
            self.signals.finished.emit(self.request_id, result, None, self.payload)
        except Exception as error:
            self.signals.finished.emit(self.request_id, None, error, self.payload)


class BookmarkScanWorkerSignals(QObject):
    finished = Signal(object, object)


class BookmarkScanWorker(QRunnable):
    def __init__(self, adapter: object, max_albums: int = 30) -> None:
        super().__init__()
        self.adapter = adapter
        self.max_albums = int(max_albums)
        self.signals = BookmarkScanWorkerSignals()

    def run(self) -> None:
        try:
            check_method = getattr(self.adapter, "check_bookmarked_updates", None)
            if not callable(check_method):
                raise RuntimeError("Album source does not support bookmark checks")
            updates = check_method(max_albums=self.max_albums)
            self.signals.finished.emit(updates, None)
        except Exception as error:
            self.signals.finished.emit(None, error)


__all__ = [
    "BookmarkScanWorker",
    "BookmarkScanWorkerSignals",
    "SourceLoadWorker",
    "SourceLoadWorkerSignals",
    "SourceRefreshWorker",
    "SourceRefreshWorkerSignals",
]
