from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QComboBox

from album_print_flow.app_printing_entrypoints import CUPS_KEYS
from album_print_flow.printing.flows.history import (
    clear_failed_logs_for_selected as clear_failed_logs_for_selected_flow,
)
from album_print_flow.printing.flows.history import (
    clear_selected_print_status as clear_selected_print_status_flow,
)
from album_print_flow.printing.flows.history import (
    ensure_photo_entry_for_path as ensure_photo_entry_for_path_flow,
)
from album_print_flow.printing.flows.history import (
    is_already_printed as is_already_printed_flow,
)
from album_print_flow.printing.flows.history import (
    is_ignored_for_print_all as is_ignored_for_print_all_flow,
)
from album_print_flow.printing.flows.history import (
    latest_print_status_for_path as latest_print_status_for_path_flow,
)
from album_print_flow.printing.flows.history import (
    mark_selected_as_printed as mark_selected_as_printed_flow,
)
from album_print_flow.printing.flows.history import (
    on_ignore_for_print_all_toggled as on_ignore_for_print_all_toggled_flow,
)
from album_print_flow.printing.flows.history import (
    should_include_in_print_all as should_include_in_print_all_flow,
)
from album_print_flow.printing.flows.history import (
    update_selected_print_info as update_selected_print_info_flow,
)
from album_print_flow.printing.flows.paper import paper_size_mm as paper_size_mm_flow
from album_print_flow.printing.flows.selection import print_all as print_all_flow
from album_print_flow.printing.flows.selection import (
    print_selected as print_selected_flow,
)
from album_print_flow.printing.flows.selection import (
    selected_paths_for_printing as selected_paths_for_printing_flow,
)
from album_print_flow.printing.flows.setup import (
    get_cups_capabilities as get_cups_capabilities_flow,
)
from album_print_flow.printing.flows.setup import (
    is_cups_available as is_cups_available_flow,
)
from album_print_flow.printing.flows.setup import (
    populate_printers_combo as populate_printers_combo_flow,
)


def ensure_photo_entry_for_path(window: Any, path: Path) -> dict[str, object]:
    return ensure_photo_entry_for_path_flow(window, path)


def is_ignored_for_print_all(window: Any, path: Path) -> bool:
    return is_ignored_for_print_all_flow(window, path)


def is_already_printed(window: Any, path: Path) -> bool:
    return is_already_printed_flow(window, path)


def should_include_in_print_all(window: Any, path: Path) -> bool:
    return should_include_in_print_all_flow(window, path)


def latest_print_status_for_path(window: Any, path: Path) -> str:
    return latest_print_status_for_path_flow(window, path)


def on_ignore_for_print_all_toggled(window: Any, checked: bool) -> None:
    on_ignore_for_print_all_toggled_flow(window, checked)


def mark_selected_as_printed(window: Any) -> None:
    mark_selected_as_printed_flow(window)


def clear_failed_logs_for_selected(window: Any) -> None:
    clear_failed_logs_for_selected_flow(window)


def clear_selected_print_status(window: Any) -> None:
    clear_selected_print_status_flow(window)


def update_selected_print_info(window: Any) -> None:
    update_selected_print_info_flow(window)


def populate_printers_combo(window: Any, combo: QComboBox) -> None:
    populate_printers_combo_flow(window, combo)


def is_cups_available() -> bool:
    return is_cups_available_flow()


def get_cups_capabilities(
    window: Any,
    printer_name: str,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    return get_cups_capabilities_flow(window, printer_name, CUPS_KEYS)


def paper_size_mm(paper_value: str) -> tuple[float, float]:
    return paper_size_mm_flow(paper_value)


def selected_paths_for_printing(window: Any) -> list[Path]:
    return selected_paths_for_printing_flow(window)


def print_selected(window: Any) -> None:
    print_selected_flow(window)


def print_all(window: Any) -> None:
    print_all_flow(window)


def print_borderless_calibration_pages(
    window: Any,
    printer_name: str,
    media_value: str,
    media_type_value: str,
    print_quality_value: str,
    scale_values: list[int],
    *,
    print_borderless_calibration_pages_flow: Any,
    print_borderless_calibration_flow_kwargs: dict[str, object],
) -> tuple[int, list[str]]:
    return print_borderless_calibration_pages_flow(
        window,
        printer_name,
        media_value,
        media_type_value,
        print_quality_value,
        scale_values,
        **print_borderless_calibration_flow_kwargs,
    )


def print_all_via_cups(
    window: Any,
    paths: list[Path],
    printer_name: str,
    *,
    print_all_via_cups_flow: Any,
    print_all_via_cups_flow_kwargs: dict[str, object],
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    return print_all_via_cups_flow(
        window,
        paths,
        printer_name,
        **print_all_via_cups_flow_kwargs,
    )


def print_all_via_qt(
    window: Any,
    paths: list[Path],
    printer_name: str,
    *,
    print_all_via_qt_flow: Any,
    print_all_via_qt_flow_kwargs: dict[str, object],
) -> tuple[list[Path], list[str], str]:
    return print_all_via_qt_flow(
        window,
        paths,
        printer_name,
        **print_all_via_qt_flow_kwargs,
    )


def record_print_history(
    window: Any,
    attempted_paths: list[Path],
    printed_paths: list[Path],
    failed_names: list[str],
    printer_name: str,
    backend: str,
    error: str,
    job_ids: dict[str, str] | None = None,
    *,
    record_print_history_flow: Any,
) -> None:
    record_print_history_flow(
        window,
        attempted_paths,
        printed_paths,
        failed_names,
        printer_name,
        backend,
        error,
        job_ids,
    )


def print_paths(
    window: Any,
    paths: list[Path],
    *,
    print_paths_flow: Any,
) -> None:
    print_paths_flow(window, paths)


def execute_print_paths(
    window: Any,
    paths: list[Path],
    *,
    execute_print_paths_flow: Any,
) -> tuple[list[Path], list[str], str, str, str, dict[str, str]]:
    return execute_print_paths_flow(window, paths)


def print_all_via_ipp(
    window: Any,
    paths: list[Path],
    ipp_uri: str,
    *,
    print_all_via_ipp_flow: Any,
    print_all_via_ipp_flow_kwargs: dict[str, object],
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    return print_all_via_ipp_flow(
        window,
        paths,
        ipp_uri,
        **print_all_via_ipp_flow_kwargs,
    )


__all__ = [
    "clear_failed_logs_for_selected",
    "clear_selected_print_status",
    "execute_print_paths",
    "ensure_photo_entry_for_path",
    "get_cups_capabilities",
    "is_already_printed",
    "is_cups_available",
    "is_ignored_for_print_all",
    "latest_print_status_for_path",
    "mark_selected_as_printed",
    "on_ignore_for_print_all_toggled",
    "paper_size_mm",
    "populate_printers_combo",
    "print_all",
    "print_all_via_cups",
    "print_all_via_ipp",
    "print_all_via_qt",
    "print_borderless_calibration_pages",
    "print_paths",
    "print_selected",
    "record_print_history",
    "selected_paths_for_printing",
    "should_include_in_print_all",
    "update_selected_print_info",
]
