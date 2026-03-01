from __future__ import annotations

from PIL import Image

from album_print_flow.printing_helpers import (
    apply_borderless_content_scale as apply_borderless_content_scale_impl,
)
from album_print_flow.printing_helpers import (
    create_borderless_calibration_image as create_borderless_calibration_image_impl,
)
from album_print_flow.printing_helpers import (
    is_explicit_borderless_media as is_explicit_borderless_media_impl,
)
from album_print_flow.printing_helpers import (
    media_size_mm_from_value as media_size_mm_from_value_impl,
)
from album_print_flow.printing_helpers import (
    parse_cups_options_output as parse_cups_options_output_impl,
)
from album_print_flow.printing_helpers import (
    parse_cups_request_id as parse_cups_request_id_impl,
)
from album_print_flow.printing_helpers import parse_ipp_job_id as parse_ipp_job_id_impl
from album_print_flow.printing_helpers import (
    pretty_option_label as pretty_option_label_impl,
)
from album_print_flow.printing_helpers import (
    query_cups_job_status_text as query_cups_job_status_text_impl,
)
from album_print_flow.printing_helpers import (
    resolve_cups_media_value as resolve_cups_media_value_impl,
)

CUPS_KEYS = ["media", "media-type", "print-quality"]
CUPS_ALIASES = {
    "media": ["media", "pagesize", "page-size", "page_size"],
    "media-type": ["media-type", "mediatype", "media_type"],
    "print-quality": [
        "print-quality",
        "printquality",
        "quality",
        "cupsprintquality",
        "resolution",
    ],
}

MEDIA_NAME_MAP = {
    "iso_a3_297x420mm": "A3",
    "iso_a4_210x297mm": "A4",
    "iso_a5_148x210mm": "A5",
    "na_letter_8.5x11in": "US Letter",
    "na_legal_8.5x14in": "US Legal",
    "4x6": "4x6 in (10x15 cm)",
    "5x7": "5x7 in",
    "8x10": "8x10 in",
    "10x15cm": "10x15 cm",
    "13x18cm": "13x18 cm",
    "a3": "A3",
    "a4": "A4",
}

MEDIA_TYPE_MAP = {
    "stationery": "Plain Paper",
    "plain": "Plain Paper",
    "photographicglossy": "Photo Glossy",
    "photographicsemigloss": "Photo Semi-Gloss",
    "photographicmatte": "Photo Matte",
    "matte": "Matte",
    "glossy": "Glossy",
    "envelope": "Envelope",
}

QUALITY_MAP = {
    "3": "Draft",
    "4": "Normal",
    "5": "High",
    "draft": "Draft",
    "normal": "Normal",
    "high": "High",
}


def pretty_option_label(kind: str, raw_value: str) -> str:
    return pretty_option_label_impl(
        kind,
        raw_value,
        media_name_map=MEDIA_NAME_MAP,
        media_type_map=MEDIA_TYPE_MAP,
        quality_map=QUALITY_MAP,
    )


def media_size_mm_from_value(media: str) -> tuple[float, float] | None:
    return media_size_mm_from_value_impl(media)


def resolve_cups_media_value(
    selected_media: str,
    supported_media: list[str],
    borderless_enabled: bool,
) -> str:
    return resolve_cups_media_value_impl(
        selected_media,
        supported_media,
        borderless_enabled,
    )


def is_explicit_borderless_media(media: str) -> bool:
    return is_explicit_borderless_media_impl(media)


def parse_cups_options_output(
    output: str,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    return parse_cups_options_output_impl(
        output,
        cups_keys=CUPS_KEYS,
        cups_aliases=CUPS_ALIASES,
    )


def parse_cups_request_id(output: str) -> str:
    return parse_cups_request_id_impl(output)


def query_cups_job_status_text(request_id: str) -> str:
    return query_cups_job_status_text_impl(request_id)


def create_borderless_calibration_image(
    width_px: int,
    height_px: int,
    scale_percent: int,
    test_label: str,
) -> Image.Image:
    return create_borderless_calibration_image_impl(
        width_px,
        height_px,
        scale_percent,
        test_label,
    )


def apply_borderless_content_scale(
    image: Image.Image,
    scale_percent: int,
) -> Image.Image:
    return apply_borderless_content_scale_impl(image, scale_percent)


def parse_ipp_job_id(value: str) -> int | None:
    return parse_ipp_job_id_impl(value)


__all__ = [
    "CUPS_KEYS",
    "apply_borderless_content_scale",
    "create_borderless_calibration_image",
    "is_explicit_borderless_media",
    "media_size_mm_from_value",
    "parse_cups_options_output",
    "parse_cups_request_id",
    "parse_ipp_job_id",
    "pretty_option_label",
    "query_cups_job_status_text",
    "resolve_cups_media_value",
]
