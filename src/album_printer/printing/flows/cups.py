from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


def print_all_via_cups(
    window: Any,
    paths: list[Path],
    printer_name: str,
    resolve_cups_media_value_fn: Callable[[str, list[str], bool], str],
    render_image_fn: Callable[..., Any],
    apply_borderless_content_scale_fn: Callable[[Any, int], Any],
    parse_cups_request_id_fn: Callable[[str], str],
    query_cups_job_status_text_fn: Callable[[str], str],
) -> tuple[list[Path], list[str], str, dict[str, str]]:
    printed_successfully: list[Path] = []
    failed: list[str] = []
    job_ids: dict[str, str] = {}
    borderless = window.borderless_enabled()

    caps, _resolved_keys = window.get_cups_capabilities(printer_name)
    effective_media_value = resolve_cups_media_value_fn(
        window.cups_media_value,
        caps.get("media", []),
        borderless,
    )

    window.append_log(
        "DEBUG",
        (
            f"CUPS print start: printer={printer_name}, count={len(paths)}, "
            f"media={effective_media_value or window.cups_media_value or 'default'}, "
            f"media_type={window.cups_media_type_value or 'default'}, "
            f"quality={window.cups_print_quality_value or 'default'}, "
            f"borderless_scale={window.borderless_content_scale_percent}%"
        ),
    )
    if window.cups_media_value and effective_media_value != window.cups_media_value:
        window.append_log(
            "DEBUG",
            (
                "CUPS media remap: "
                "requested="
                f"{window.cups_media_value} "
                f"effective={effective_media_value}"
            ),
        )

    with tempfile.TemporaryDirectory(prefix="album_printer_") as temp_dir:
        for path in paths:
            out = Path(temp_dir) / f"{path.stem}.jpg"
            try:
                image = render_image_fn(
                    path,
                    window.processing_settings_for_path(path),
                    debug_logger=lambda message: window.append_log("DEBUG", message),
                )
                if borderless:
                    image = apply_borderless_content_scale_fn(
                        image,
                        window.borderless_content_scale_percent,
                    )
                image.save(out, format="JPEG", quality=95, optimize=True)
            except OSError as error:
                failed.append(path.name)
                window.append_log(
                    "DEBUG",
                    f"CUPS render failed for {path.name}: {error}",
                )
                continue

            command = ["lp", "-d", printer_name]
            if effective_media_value:
                command.extend(
                    ["-o", f"{window.cups_media_key}={effective_media_value}"]
                )
            if window.cups_media_type_value:
                command.extend(
                    [
                        "-o",
                        f"{window.cups_media_type_key}={window.cups_media_type_value}",
                    ]
                )
            if window.cups_print_quality_value:
                command.extend(
                    [
                        "-o",
                        f"{window.cups_print_quality_key}="
                        f"{window.cups_print_quality_value}",
                    ]
                )

            if borderless:
                command.extend(
                    [
                        "-o",
                        "scaling=100",
                        "-o",
                        "position=center",
                    ]
                )

            command.append(str(out))
            try:
                result = subprocess.run(
                    command, capture_output=True, text=True, check=False
                )
            except OSError as error:
                window.append_log("ERROR", f"CUPS command failed: {error}")
                return printed_successfully, failed, str(error), job_ids

            if result.returncode == 0:
                printed_successfully.append(path)
                request_id = parse_cups_request_id_fn(result.stdout)
                if request_id:
                    job_ids[path.name] = request_id
                    window.append_log(
                        "DEBUG", f"CUPS queued {path.name} as {request_id}"
                    )
                    status_text = query_cups_job_status_text_fn(request_id)
                    if status_text:
                        window.append_log(
                            "DEBUG",
                            f"CUPS job {request_id}: {status_text}",
                        )
                else:
                    window.append_log("DEBUG", f"CUPS queued {path.name}")
            else:
                failed.append(path.name)
                stderr = (result.stderr or "").strip()
                stdout = (result.stdout or "").strip()
                detail = stderr or stdout or "no output"
                window.append_log(
                    "DEBUG",
                    (
                        f"CUPS failed {path.name}: returncode={result.returncode}, "
                        f"detail={detail[:220]}"
                    ),
                )

    return printed_successfully, failed, "", job_ids
