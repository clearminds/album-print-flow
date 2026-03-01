from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


def print_all_via_ipp(
    window: Any,
    paths: list[Path],
    ipp_uri: str,
    render_image_fn: Callable[..., Any],
    print_jobs_via_ipp_fn: Callable[
        ..., tuple[list[Path], list[str], str, dict[str, str]]
    ],
    ipp_backend_error_cls: type[Exception],
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    wait_for_completion = window.ipp_wait_for_completion_value
    if wait_for_completion:
        window.append_log(
            "WARNING",
            "IPP wait-for-completion is currently forced "
            "to queue-only to avoid UI blocking.",
        )
        wait_for_completion = False

    window.append_log(
        "DEBUG",
        (
            f"IPP print start: uri={ipp_uri}, count={len(paths)}, "
            f"wait_for_completion={wait_for_completion}, "
            f"media={window.cups_media_value or 'default'}, "
            f"media_type={window.cups_media_type_value or 'default'}, "
            f"quality={window.cups_print_quality_value or 'default'}"
        ),
    )
    with tempfile.TemporaryDirectory(prefix="album_print_flow_ipp_") as temp_dir:
        render_targets: list[Path] = []
        render_map: dict[Path, Path] = {}
        failed: list[str] = []

        for source in paths:
            out = Path(temp_dir) / f"{source.stem}.jpg"
            try:
                image = render_image_fn(
                    source,
                    window.processing_settings_for_path(source),
                    debug_logger=lambda message: window.append_log("DEBUG", message),
                )
                image.save(out, format="JPEG", quality=95, optimize=True)
                render_targets.append(out)
                render_map[out] = source
            except OSError as error:
                failed.append(source.name)
                window.append_log(
                    "DEBUG",
                    f"IPP render failed for {source.name}: {error}",
                )

        if not render_targets:
            return [], failed, "No printable images were rendered for IPP.", {}

        try:
            printed_rendered, failed_rendered, error, rendered_job_ids = (
                print_jobs_via_ipp_fn(
                    ipp_uri=ipp_uri,
                    image_files=render_targets,
                    media=window.cups_media_value,
                    media_type=window.cups_media_type_value,
                    print_quality=window.cups_print_quality_value,
                    borderless_mode=window.borderless_mode_value,
                    wait_for_completion=wait_for_completion,
                    debug_logger=lambda message: window.append_log("DEBUG", message),
                )
            )
        except ipp_backend_error_cls as exc:
            window.append_log("ERROR", f"IPP backend exception: {exc}")
            return [], [path.name for path in paths], str(exc), {}

        printed_sources = [
            render_map[path] for path in printed_rendered if path in render_map
        ]
        job_ids: dict[str, str] = {}
        for rendered_name, job_id in rendered_job_ids.items():
            for rendered_path, source_path in render_map.items():
                if rendered_path.name == rendered_name:
                    job_ids[source_path.name] = job_id
                    break
        failed.extend(failed_rendered)
        for path in printed_sources:
            window.append_log("DEBUG", f"IPP queued {path.name}")
        if failed_rendered:
            window.append_log(
                "DEBUG",
                "IPP backend failed files: " + ", ".join(failed_rendered),
            )
        if error:
            window.append_log("DEBUG", f"IPP backend detail: {error}")
        return printed_sources, failed, error, job_ids
