from __future__ import annotations

from pathlib import Path
from typing import Any


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
    "execute_print_paths",
    "print_all_via_cups",
    "print_all_via_ipp",
    "print_all_via_qt",
    "print_borderless_calibration_pages",
    "print_paths",
    "record_print_history",
]
