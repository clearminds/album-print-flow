from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable

from PIL import Image, ImageDraw, ImageFont


def pretty_option_label(
    kind: str,
    raw_value: str,
    *,
    media_name_map: dict[str, str],
    media_type_map: dict[str, str],
    quality_map: dict[str, str],
) -> str:
    value = (raw_value or "").strip()
    if not value:
        return value

    key = value.lower()
    if kind == "media":
        translated = media_name_map.get(key)
    elif kind == "media-type":
        translated = media_type_map.get(key)
    else:
        translated = quality_map.get(key)

    if translated:
        return f"{translated} ({value})"

    fallback = value.replace("_", " ").replace("-", " ").strip()
    if fallback and fallback != value:
        fallback = " ".join(part.capitalize() for part in fallback.split())
        return f"{fallback} ({value})"
    return value


def media_size_mm_from_value(media: str) -> tuple[float, float] | None:
    value = (media or "").strip().lower()
    if not value:
        return None

    direct_sizes: dict[str, tuple[float, float]] = {
        "a3": (297.0, 420.0),
        "a4": (210.0, 297.0),
        "a5": (148.0, 210.0),
        "4x6": (101.6, 152.4),
        "5x7": (127.0, 177.8),
        "8x10": (203.2, 254.0),
        "10x15cm": (100.0, 150.0),
        "13x18cm": (130.0, 180.0),
    }
    known = direct_sizes.get(value)
    if known is not None:
        return known

    match = re.search(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)(mm|cm|in)", value)
    if not match:
        return None

    width = float(match.group(1))
    height = float(match.group(2))
    unit = match.group(3)
    if unit == "mm":
        return width, height
    if unit == "cm":
        return width * 10.0, height * 10.0
    return width * 25.4, height * 25.4


def resolve_cups_media_value(
    selected_media: str,
    supported_media: list[str],
    borderless_enabled: bool,
) -> str:
    requested = (selected_media or "").strip()
    if not requested or not supported_media:
        return requested

    normalized = [(value, value.lower()) for value in supported_media if value]
    requested_lower = requested.lower()

    def find_exact(value: str) -> str | None:
        target = value.lower()
        for original, lower in normalized:
            if lower == target:
                return original
        return None

    exact = find_exact(requested)
    if borderless_enabled:
        if exact and "borderless" in exact.lower():
            return exact

        direct_candidates = (
            f"{requested}.Borderless",
            f"{requested}.borderless",
            f"{requested}Borderless",
            f"T{requested}",
        )
        for candidate in direct_candidates:
            found = find_exact(candidate)
            if found is not None:
                return found

        for original, lower in normalized:
            if requested_lower in lower and "borderless" in lower:
                return original
        return exact or requested

    if exact:
        return exact
    return requested


def is_explicit_borderless_media(media: str) -> bool:
    value = (media or "").strip().lower()
    if not value:
        return False
    return "borderless" in value


def parse_cups_options_output(
    output: str,
    *,
    cups_keys: Iterable[str],
    cups_aliases: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, str]]:
    parsed: dict[str, list[str]] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        left, right = line.split(":", maxsplit=1)
        key = left.split("/", maxsplit=1)[0].strip().lower()

        tokens = [t.lstrip("*") for t in right.strip().split() if t]
        cleaned: list[str] = []
        for token in tokens:
            if token in cleaned:
                continue
            if token.startswith("("):
                continue
            if re.search(r"[\/=]", token):
                continue
            cleaned.append(token)
        parsed[key] = cleaned

    result = {key: [] for key in cups_keys}
    resolved_keys = {
        "media": "media",
        "media-type": "media-type",
        "print-quality": "print-quality",
    }
    for canonical, aliases in cups_aliases.items():
        merged: list[str] = []
        resolved = canonical
        for alias in aliases:
            values = parsed.get(alias, [])
            if values and resolved == canonical:
                resolved = alias
            for option in values:
                if option not in merged:
                    merged.append(option)
        result[canonical] = merged
        resolved_keys[canonical] = resolved
    return result, resolved_keys


def parse_cups_request_id(output: str) -> str:
    text = (output or "").strip()
    if not text:
        return ""
    match = re.search(r"request\s+id\s+is\s+([^\s]+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def query_cups_job_status_text(request_id: str) -> str:
    job = (request_id or "").strip()
    if not job:
        return ""

    try:
        result = subprocess.run(
            ["lpstat", "-W", "all", "-l", "-o"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""

    output = (result.stdout or "").strip()
    if not output:
        error_text = (result.stderr or "").strip()
        return error_text

    lines = output.splitlines()
    header_index = -1
    for index, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith(job + " ") or line == job:
            header_index = index
            break

    if header_index < 0:
        return ""

    status_value = ""
    fallback_value = ""
    for raw in lines[header_index + 1 :]:
        if raw and not raw.startswith(" ") and not raw.startswith("\t"):
            break
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("status:"):
            status_text = line.split(":", maxsplit=1)[1].strip()
            if status_text:
                status_value = f"Status: {status_text}"
                break
            continue
        if not fallback_value and (
            lowered.startswith("alerts:")
            or lowered.startswith("printer-state-reasons:")
            or lowered.startswith("queued for")
            or lowered.startswith("processing")
            or lowered.startswith("completed")
        ):
            fallback_value = line

    if status_value:
        return status_value
    if fallback_value:
        return fallback_value
    return lines[header_index].strip()


def query_cups_job_state(request_id: str) -> str:
    """Return a structured CUPS job state for the given request ID.

    Returns one of: "completed", "processing", "pending", "canceled",
    "aborted", "not-found".
    """
    job = (request_id or "").strip()
    if not job:
        return "not-found"

    try:
        result = subprocess.run(
            ["lpstat", "-W", "all", "-l", "-o"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "not-found"

    output = (result.stdout or "").strip()
    if not output:
        return "not-found"

    lines = output.splitlines()
    header_index = -1
    for index, raw in enumerate(lines):
        line = raw.strip()
        if line.startswith(job + " ") or line == job:
            header_index = index
            break

    if header_index < 0:
        return "not-found"

    for raw in lines[header_index + 1 :]:
        if raw and not raw.startswith(" ") and not raw.startswith("\t"):
            break
        lowered = raw.strip().lower()
        if not lowered:
            continue
        for state in ("completed", "canceled", "aborted", "processing", "pending"):
            if state in lowered:
                return state

    header_lower = lines[header_index].strip().lower()
    for state in ("completed", "canceled", "aborted", "processing", "pending"):
        if state in header_lower:
            return state

    return "pending"


def create_borderless_calibration_image(
    width_px: int,
    height_px: int,
    scale_percent: int,
    test_label: str,
) -> Image.Image:
    width = max(600, int(width_px))
    height = max(600, int(height_px))
    image = Image.new("RGB", (width, height), "#F8FAFC")
    draw = ImageDraw.Draw(image)

    block = max(20, min(width, height) // 24)
    color_a = (240, 244, 248)
    color_b = (222, 230, 238)
    for top in range(0, height, block):
        row = top // block
        for left in range(0, width, block):
            col = left // block
            color = color_a if (row + col) % 2 == 0 else color_b
            draw.rectangle((left, top, left + block - 1, top + block - 1), fill=color)

    border_outer = max(12, min(width, height) // 40)
    border_inner = max(4, border_outer // 3)
    draw.rectangle((0, 0, width - 1, height - 1), outline="#B91C1C", width=border_outer)
    inset = border_outer + border_inner
    draw.rectangle(
        (inset, inset, width - inset - 1, height - inset - 1),
        outline="#111827",
        width=border_inner,
    )

    cx = width // 2
    cy = height // 2
    draw.line((cx, inset, cx, height - inset - 1), fill="#2563EB", width=2)
    draw.line((inset, cy, width - inset - 1, cy), fill="#2563EB", width=2)

    guide_step = max(60, min(width, height) // 12)
    for offset in range(guide_step, min(cx, cy), guide_step):
        draw.rectangle(
            (cx - offset, cy - offset, cx + offset, cy + offset),
            outline="#0F766E",
            width=2,
        )

    marker_size = max(46, min(width, height) // 10)
    corners = [
        (inset, inset),
        (width - inset - marker_size, inset),
        (inset, height - inset - marker_size),
        (width - inset - marker_size, height - inset - marker_size),
    ]
    for left, top in corners:
        draw.rectangle(
            (left, top, left + marker_size, top + marker_size),
            outline="#7C2D12",
            width=max(3, border_inner),
        )

    corner_font_size = max(22, int(min(width, height) * 0.042))
    info_font_size = max(24, int(min(width, height) * 0.046))
    try:
        corner_font = ImageFont.truetype("DejaVuSans-Bold.ttf", corner_font_size)
        info_font = ImageFont.truetype("DejaVuSans-Bold.ttf", info_font_size)
    except OSError:
        corner_font = ImageFont.load_default()
        info_font = ImageFont.load_default()

    draw.text((inset + 12, inset + 8), "TOP LEFT", fill="#111827", font=corner_font)
    draw.text(
        (width - inset - max(180, int(width * 0.18)), inset + 8),
        "TOP RIGHT",
        fill="#111827",
        font=corner_font,
    )
    draw.text(
        (inset + 12, height - inset - max(42, int(height * 0.05))),
        "BOTTOM LEFT",
        fill="#111827",
        font=corner_font,
    )
    draw.text(
        (
            width - inset - max(220, int(width * 0.22)),
            height - inset - max(42, int(height * 0.05)),
        ),
        "BOTTOM RIGHT",
        fill="#111827",
        font=corner_font,
    )

    title = f"BORDERLESS CALIBRATION - SCALE {int(scale_percent)}%"
    subtitle = "Goal: all red/black border lines should remain visible"
    draw.text(
        (inset + 12, cy - max(56, int(height * 0.07))),
        title,
        fill="#0F172A",
        font=info_font,
    )
    draw.text(
        (inset + 12, cy - max(20, int(height * 0.02))),
        subtitle,
        fill="#334155",
        font=info_font,
    )

    marker_w = max(260, int(width * 0.34))
    marker_h = max(72, int(height * 0.12))
    marker_left = cx - marker_w // 2
    marker_top = cy - marker_h // 2 + 48
    draw.rectangle(
        (marker_left, marker_top, marker_left + marker_w, marker_top + marker_h),
        fill="#FFFFFF",
        outline="#0F172A",
        width=max(3, border_inner),
    )

    center_font_size = max(44, int(min(width, height) * 0.095))
    try:
        center_font = ImageFont.truetype("DejaVuSans-Bold.ttf", center_font_size)
    except OSError:
        center_font = ImageFont.load_default()

    center_text = f"TEST {test_label} · {int(scale_percent)}%"
    text_left, text_top, text_right, text_bottom = draw.textbbox(
        (0, 0), center_text, font=center_font
    )
    text_w = text_right - text_left
    text_h = text_bottom - text_top
    text_x = marker_left + (marker_w - text_w) // 2 - text_left
    text_y = marker_top + (marker_h - text_h) // 2 - text_top
    draw.text(
        (text_x, text_y),
        center_text,
        fill="#111827",
        font=center_font,
        stroke_width=2,
        stroke_fill="#FFFFFF",
    )
    return image


def apply_borderless_content_scale(
    image: Image.Image,
    scale_percent: int,
) -> Image.Image:
    scale = max(85, min(110, int(scale_percent)))
    if scale == 100:
        return image

    width = max(1, image.width)
    height = max(1, image.height)
    target_w = max(1, int(round(width * (scale / 100.0))))
    target_h = max(1, int(round(height * (scale / 100.0))))

    resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if scale < 100:
        canvas = Image.new("RGB", (width, height), "#FFFFFF")
        x = (width - target_w) // 2
        y = (height - target_h) // 2
        canvas.paste(resized, (x, y))
        return canvas

    left = max(0, (target_w - width) // 2)
    top = max(0, (target_h - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def parse_ipp_job_id(value: str) -> int | None:
    text = (value or "").strip()
    if not text:
        return None

    if text.isdigit():
        return int(text)

    match = re.search(r"(\d+)$", text)
    if not match:
        return None
    return int(match.group(1))


__all__ = [
    "apply_borderless_content_scale",
    "create_borderless_calibration_image",
    "is_explicit_borderless_media",
    "media_size_mm_from_value",
    "parse_cups_options_output",
    "parse_cups_request_id",
    "parse_ipp_job_id",
    "pretty_option_label",
    "query_cups_job_state",
    "query_cups_job_status_text",
    "resolve_cups_media_value",
]
