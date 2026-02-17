from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QWidget

from album_printer.sources.types import SourceAsset, SourceLoadResult


class FolderSource:
    source_id = "folder"
    label = "Folder"
    help_text = (
        "Load images from a local folder on this computer.\n"
        "Best when your originals are already downloaded and organized locally.\n"
        "Refresh scans the folder for newly added files."
    )

    def __init__(self, supported_extensions: set[str]) -> None:
        self._supported_extensions = {value.lower() for value in supported_extensions}

    def load_via_ui(self, parent: QWidget | None = None) -> SourceLoadResult | None:
        folder = QFileDialog.getExistingDirectory(parent, "Select image folder")
        if not folder:
            return None
        return self._load_folder(Path(folder))

    def refresh(
        self,
        context_id: str,
        preferred_path: Path | None = None,
    ) -> SourceLoadResult:
        return self._load_folder(Path(context_id))

    def _load_folder(self, folder_path: Path) -> SourceLoadResult:
        def is_sidecar_jpeg(path: Path) -> bool:
            name = path.name.lower()
            return name.endswith(".heic.jpg") or name.endswith(".heif.jpg")

        assets = [
            SourceAsset(
                key=path.name,
                local_path=path,
                display_name=path.name,
            )
            for path in sorted(folder_path.iterdir())
            if (
                path.is_file()
                and path.suffix.lower() in self._supported_extensions
                and not is_sidecar_jpeg(path)
            )
        ]

        return SourceLoadResult(
            source_id=self.source_id,
            source_label=self.label,
            context_id=str(folder_path),
            context_label=str(folder_path),
            assets=assets,
            metadata_root=folder_path,
            is_new_context=not (folder_path / ".album_printer.json").exists(),
        )
