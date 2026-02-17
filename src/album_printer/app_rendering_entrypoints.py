from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageFont

from album_printer.app_image_entrypoints import datetime_for_image, load_image_as_rgb
from album_printer.app_primitives import apply_manual_rotation, center_crop_to_ratio
from album_printer.processing_settings import ProcessingSettings
from album_printer.rendering_helpers import apply_stamp as apply_stamp_impl
from album_printer.rendering_helpers import load_stamp_font as load_stamp_font_impl
from album_printer.rendering_helpers import (
    location_stamp_text as location_stamp_text_impl,
)
from album_printer.rendering_helpers import render_image as render_image_impl
from album_printer.rendering_helpers import (
    render_preview_image as render_preview_image_impl,
)
from album_printer.rendering_helpers import stamp_text as stamp_text_impl

STAMP_FONTS = {
    "Photo Stamp Mono": "fonts/PhotoStampMono.ttf",
    "Classic Mono": "fonts/ClassicMono.ttf",
}
DEFAULT_STAMP_COLOR = "#FF9100"
DEFAULT_STAMP_BORDER_COLOR = "#000000"


def stamp_text(path: Path, settings: ProcessingSettings) -> str:
    return stamp_text_impl(
        path,
        settings,
        datetime_for_image_fn=datetime_for_image,
    )


def location_stamp_text(settings: ProcessingSettings) -> str:
    return location_stamp_text_impl(settings)


def load_stamp_font(
    font_name: str, font_size: int
) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    return load_stamp_font_impl(
        font_name,
        font_size,
        base_path=Path(__file__).resolve().parent,
        stamp_fonts=STAMP_FONTS,
    )


def apply_stamp(
    image: Image.Image,
    text: str,
    settings: ProcessingSettings,
    *,
    corner: str | None = None,
    scale_percent: int | None = None,
    offset_x_px: int | None = None,
    offset_y_px: int | None = None,
    color_value: str | None = None,
    border_color_value: str | None = None,
    vertical: bool | None = None,
    adaptive_text: bool | None = None,
) -> Image.Image:
    return apply_stamp_impl(
        image,
        text,
        settings,
        load_stamp_font_fn=load_stamp_font,
        default_stamp_color=DEFAULT_STAMP_COLOR,
        default_stamp_border_color=DEFAULT_STAMP_BORDER_COLOR,
        corner=corner,
        scale_percent=scale_percent,
        offset_x_px=offset_x_px,
        offset_y_px=offset_y_px,
        color_value=color_value,
        border_color_value=border_color_value,
        vertical=vertical,
        adaptive_text=adaptive_text,
    )


def render_image(
    path: Path,
    settings: ProcessingSettings,
    debug_logger: Callable[[str], None] | None = None,
) -> Image.Image:
    return render_image_impl(
        path,
        settings,
        load_image_as_rgb_fn=load_image_as_rgb,
        apply_manual_rotation_fn=apply_manual_rotation,
        center_crop_to_ratio_fn=center_crop_to_ratio,
        stamp_text_fn=stamp_text,
        location_stamp_text_fn=location_stamp_text,
        apply_stamp_fn=apply_stamp,
        debug_logger=debug_logger,
    )


def render_preview_image(
    path: Path,
    settings: ProcessingSettings,
    max_dimension: int,
    debug_logger: Callable[[str], None] | None = None,
) -> Image.Image:
    return render_preview_image_impl(
        path,
        settings,
        max_dimension,
        load_image_as_rgb_fn=load_image_as_rgb,
        apply_manual_rotation_fn=apply_manual_rotation,
        center_crop_to_ratio_fn=center_crop_to_ratio,
        stamp_text_fn=stamp_text,
        location_stamp_text_fn=location_stamp_text,
        apply_stamp_fn=apply_stamp,
        debug_logger=debug_logger,
    )


__all__ = [
    "DEFAULT_STAMP_BORDER_COLOR",
    "DEFAULT_STAMP_COLOR",
    "STAMP_FONTS",
    "apply_stamp",
    "load_stamp_font",
    "location_stamp_text",
    "render_image",
    "render_preview_image",
    "stamp_text",
]
