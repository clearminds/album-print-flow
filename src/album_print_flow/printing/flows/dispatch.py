from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtPrintSupport import QPrinterInfo
from PySide6.QtWidgets import QMessageBox

from album_print_flow.ipp_backend import IppBackendError, get_ipp_capabilities


def execute_print_paths(
    window: Any,
    paths: list[Path],
) -> tuple[list[Path], list[str], str, str, str, dict[str, str]]:
    if not paths:
        return [], [], "No images provided.", "", window.print_backend_value, {}

    window.append_log(
        "DEBUG",
        "Print request files: " + ", ".join(path.name for path in paths),
    )

    photos = window.folder_metadata.get("photos")
    duplicate_names: list[str] = []
    if isinstance(photos, dict):
        for path in paths:
            photo_meta = photos.get(window.metadata_key_for_path(path))
            if not isinstance(photo_meta, dict):
                continue
            if int(photo_meta.get("total_printed", 0)) > 0:
                duplicate_names.append(path.name)

    if duplicate_names:
        examples = "\n".join(f"- {name}" for name in duplicate_names[:5])
        message = (
            f"{len(duplicate_names)} selected photo(s) were already printed "
            "before.\n\n"
            "Examples:\n"
            f"{examples}\n\n"
            "Print anyway?"
        )
        reply = QMessageBox.question(
            window,
            "Already printed photos",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            window.append_log(
                "INFO",
                "Print cancelled by user due to already printed photo selection",
            )
            return (
                [],
                [],
                "Cancelled by user",
                "",
                window.print_backend_value,
                {},
            )

    backend = window.print_backend_value
    printer_name = window.printer_value
    job_ids: dict[str, str] = {}
    window.append_log(
        "DEBUG",
        (
            f"Print start: backend={backend}, printer={printer_name or '-'}, "
            f"ipp_uri={window.ipp_uri_value or '-'}, count={len(paths)}"
        ),
    )

    if backend == "IPP":
        if not window.ipp_uri_value:
            QMessageBox.warning(
                window,
                "No IPP URI",
                "Set an IPP URI in Print Settings when Print Backend is IPP.",
            )
            window.append_log(
                "ERROR", "Print failed: IPP backend selected without IPP URI"
            )
            return (
                [],
                [path.name for path in paths],
                "IPP URI is missing",
                "",
                backend,
                {},
            )

        ipp_uri = window.ipp_uri_value.strip()
        if ipp_uri and ipp_uri not in window.ipp_capabilities_cache:
            try:
                window.ipp_capabilities_cache[ipp_uri] = get_ipp_capabilities(ipp_uri)
            except IppBackendError:
                window.ipp_capabilities_cache[ipp_uri] = None

        printed, failed, error, job_ids = window.print_all_via_ipp(
            paths, window.ipp_uri_value
        )
        target_name = window.current_ipp_target_name()
    else:
        if backend == "CUPS":
            if not printer_name:
                QMessageBox.warning(
                    window,
                    "No printer",
                    "No printer selected. Open Print Settings "
                    "and choose a printer first.",
                )
                window.append_log(
                    "ERROR", "Print failed: CUPS backend selected without printer"
                )
                return (
                    [],
                    [path.name for path in paths],
                    "Printer is missing",
                    "",
                    backend,
                    {},
                )
            if not window.is_cups_available():
                QMessageBox.warning(
                    window,
                    "CUPS unavailable",
                    "CUPS backend selected, but CUPS tools are not available.",
                )
                window.append_log("ERROR", "Print failed: CUPS tools are unavailable")
                return (
                    [],
                    [path.name for path in paths],
                    "CUPS tools unavailable",
                    "",
                    backend,
                    {},
                )
            printed, failed, error, job_ids = window.print_all_via_cups(
                paths, printer_name
            )
        elif backend == "Qt":
            if not printer_name:
                default_printer = QPrinterInfo.defaultPrinter()
                if default_printer and default_printer.printerName():
                    printer_name = default_printer.printerName()
                else:
                    QMessageBox.warning(
                        window,
                        "No printer",
                        "No printer selected and no default Qt printer found.",
                    )
                    window.append_log(
                        "ERROR", "Print failed: no selected/default Qt printer"
                    )
                    return (
                        [],
                        [path.name for path in paths],
                        "No Qt printer available",
                        "",
                        backend,
                        {},
                    )
            printed, failed, error = window.print_all_via_qt(paths, printer_name)
        else:
            if not printer_name:
                QMessageBox.warning(
                    window,
                    "No printer",
                    "No printer selected. Open Print Settings "
                    "and choose a printer first.",
                )
                window.append_log(
                    "ERROR", "Print failed: Auto backend without selected printer"
                )
                return (
                    [],
                    [path.name for path in paths],
                    "Printer is missing",
                    "",
                    backend,
                    {},
                )
            if window.is_cups_available():
                printed, failed, error, job_ids = window.print_all_via_cups(
                    paths, printer_name
                )
            else:
                printed, failed, error = window.print_all_via_qt(paths, printer_name)
        target_name = printer_name

    window.record_print_history(
        paths,
        printed,
        failed,
        target_name,
        backend,
        error,
        job_ids=job_ids,
    )
    window.refresh_image_list_labels(window.selected_path())
    window.update_selected_print_info()

    queue_only_backend = backend in {"CUPS", "IPP"}
    action_word = "Queued" if queue_only_backend else "Sent"
    message = f"{action_word} {len(printed)} image(s) to {target_name}."
    if error:
        message += f" Error: {error}"
    if failed:
        message += f" Failed: {', '.join(failed[:5])}"

    log_level = "ERROR" if error else ("WARNING" if failed else "INFO")
    count_label = "queued" if queue_only_backend else "printed"
    summary = (
        f"Print queued via {backend} to {target_name}: "
        f"{count_label}={len(printed)}, failed={len(failed)}"
    )
    window.append_log(
        log_level,
        summary,
    )
    if error:
        window.append_log("ERROR", f"Print backend error: {error}")
    if failed:
        window.append_log("DEBUG", "Print failed files: " + ", ".join(failed))

    window.statusBar().showMessage(message)
    return printed, failed, error, target_name, backend, job_ids


__all__ = ["execute_print_paths"]
