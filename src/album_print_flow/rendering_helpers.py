from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
    ImageStat,
)
from PySide6.QtGui import QColor


def stamp_text(
    path: Path,
    settings: Any,
    *,
    datetime_for_image_fn: Callable[[Path], object],
) -> str:
    if settings.stamp_mode == "None":
        return ""

    dt = settings.datetime_override or datetime_for_image_fn(path)
    if settings.stamp_mode == "Date":
        return dt.strftime("%Y-%m-%d")
    if settings.clock_mode == "12h":
        return dt.strftime("%Y-%m-%d %I:%M %p")
    return dt.strftime("%Y-%m-%d %H:%M")


def location_stamp_text(settings: Any) -> str:
    if not settings.location_stamp_enabled:
        return ""
    return settings.location_text.strip()


def load_stamp_font(
    font_name: str,
    font_size: int,
    *,
    base_path: Path,
    stamp_fonts: dict[str, str],
) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    relative = stamp_fonts.get(font_name, stamp_fonts["Photo Stamp Mono"])
    bundled = base_path / relative
    if bundled.exists():
        try:
            return ImageFont.truetype(str(bundled), font_size)
        except OSError:
            pass

    for fallback in ("DejaVuSansMono.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(fallback, font_size)
        except OSError:
            continue

    return ImageFont.load_default()


def apply_stamp(
    image: Image.Image,
    text: str,
    settings: Any,
    *,
    load_stamp_font_fn: Callable[
        [str, int], ImageFont.ImageFont | ImageFont.FreeTypeFont
    ],
    default_stamp_color: str,
    default_stamp_border_color: str,
    corner: str | None = None,
    scale_percent: int | None = None,
    offset_x_px: int | None = None,
    offset_y_px: int | None = None,
    color_value: str | None = None,
    border_color_value: str | None = None,
    vertical: bool | None = None,
    adaptive_text: bool | None = None,
) -> Image.Image:
    if not text:
        return image

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    draw = ImageDraw.Draw(image)

    if settings.orientation == "Portrait":
        base_size = max(26, int(image.width * 0.065))
    else:
        base_size = max(22, int(image.width * 0.048))

    stamp_corner = corner if corner is not None else settings.corner
    stamp_scale_percent = (
        scale_percent if scale_percent is not None else settings.stamp_scale_percent
    )
    stamp_offset_x_px = (
        offset_x_px if offset_x_px is not None else settings.stamp_offset_x_px
    )
    stamp_offset_y_px = (
        offset_y_px if offset_y_px is not None else settings.stamp_offset_y_px
    )
    stamp_color = color_value if color_value is not None else settings.stamp_color
    stamp_border_color = (
        border_color_value
        if border_color_value is not None
        else settings.stamp_border_color
    )
    stamp_vertical = vertical if vertical is not None else settings.stamp_vertical

    margin_x = int(round(image.width * max(0, stamp_offset_x_px) / 1000.0))
    margin_y = int(round(image.height * max(0, stamp_offset_y_px) / 1000.0))

    font_size = int(base_size * (stamp_scale_percent / 100.0))
    font_size = max(14, font_size)
    font = load_stamp_font_fn(settings.stamp_font, font_size)

    stroke_width = max(2, int(font_size * 0.12))
    adaptive_text_enabled = (
        adaptive_text
        if adaptive_text is not None
        else bool(getattr(settings, "stamp_adaptive_text", False))
    )
    if adaptive_text_enabled:
        stroke_width = 0

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top

    base_layer_width = text_width + stroke_width * 2
    base_layer_height = text_height + stroke_width * 2
    if stamp_vertical:
        stamp_w = base_layer_height
        stamp_h = base_layer_width
    else:
        stamp_w = base_layer_width
        stamp_h = base_layer_height

    if "Top" in stamp_corner:
        y = margin_y
    else:
        y = image.height - stamp_h - margin_y

    if "Left" in stamp_corner:
        x = margin_x
    else:
        x = image.width - stamp_w - margin_x

    x = max(0, min(image.width - stamp_w, x))
    y = max(0, min(image.height - stamp_h, y))

    color = QColor(stamp_color)
    if not color.isValid():
        color = QColor(default_stamp_color)
    border_color = QColor(stamp_border_color)
    if not border_color.isValid():
        border_color = QColor(default_stamp_border_color)

    if adaptive_text_enabled:
        text_mask = Image.new("L", (base_layer_width, base_layer_height), 0)
        text_draw = ImageDraw.Draw(text_mask)
        text_draw.text(
            (-left, -top),
            text,
            fill=255,
            font=font,
        )

        if stamp_vertical:
            text_mask = text_mask.rotate(90, expand=True)

        sample_region = image.crop((x, y, x + stamp_w, y + stamp_h)).convert("L")
        adaptive_threshold = int(getattr(settings, "adaptive_luminance_threshold", 128))
        adaptive_threshold = max(0, min(255, adaptive_threshold))
        text_layer = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
        cursor_x = -left
        for char in text:
            char_mask_base = Image.new("L", (base_layer_width, base_layer_height), 0)
            char_draw = ImageDraw.Draw(char_mask_base)
            char_draw.text((cursor_x, -top), char, fill=255, font=font)
            cursor_x += draw.textlength(char, font=font)

            if stamp_vertical:
                char_mask = char_mask_base.rotate(90, expand=True)
            else:
                char_mask = char_mask_base

            char_bbox = char_mask.getbbox()
            if char_bbox is None:
                continue

            char_mask_crop = char_mask.crop(char_bbox)
            char_sample_crop = sample_region.crop(char_bbox)
            mean_luma = float(ImageStat.Stat(char_sample_crop, char_mask_crop).mean[0])
            if mean_luma < float(adaptive_threshold):
                glyph_rgb = (255, 255, 255)
                border_rgb = (0, 0, 0)
            else:
                glyph_rgb = (0, 0, 0)
                border_rgb = (255, 255, 255)

            border_mask = ImageChops.subtract(
                char_mask.filter(ImageFilter.MaxFilter(5)),
                char_mask,
            )
            border_mask_crop = border_mask.crop(char_bbox)

            bbox_w = char_bbox[2] - char_bbox[0]
            bbox_h = char_bbox[3] - char_bbox[1]

            border_layer = Image.new("RGBA", (bbox_w, bbox_h), border_rgb + (0,))
            border_layer.putalpha(border_mask_crop)
            text_layer.alpha_composite(border_layer, (char_bbox[0], char_bbox[1]))

            glyph_layer = Image.new("RGBA", (bbox_w, bbox_h), glyph_rgb + (0,))
            glyph_layer.putalpha(char_mask_crop)
            text_layer.alpha_composite(glyph_layer, (char_bbox[0], char_bbox[1]))
    else:
        text_layer = Image.new(
            "RGBA",
            (base_layer_width, base_layer_height),
            (0, 0, 0, 0),
        )
        text_draw = ImageDraw.Draw(text_layer)
        text_draw.text(
            (stroke_width - left, stroke_width - top),
            text,
            fill=(color.red(), color.green(), color.blue()),
            font=font,
            stroke_width=stroke_width,
            stroke_fill=(border_color.red(), border_color.green(), border_color.blue()),
        )

        if stamp_vertical:
            text_layer = text_layer.rotate(90, expand=True)

    image.alpha_composite(text_layer, (x, y))
    return image.convert("RGB")


def render_image(
    path: Path,
    settings: Any,
    *,
    load_image_as_rgb_fn: Callable[..., Image.Image],
    apply_manual_rotation_fn: Callable[[Image.Image, int], Image.Image],
    center_crop_to_ratio_fn: Callable[..., Image.Image],
    stamp_text_fn: Callable[[Path, Any], str],
    location_stamp_text_fn: Callable[[Any], str],
    apply_stamp_fn: Callable[..., Image.Image],
    debug_logger: Callable[[str], None] | None = None,
) -> Image.Image:
    image = load_image_as_rgb_fn(path, debug_logger=debug_logger)
    image = apply_manual_rotation_fn(image, settings.rotation_degrees)

    image = center_crop_to_ratio_fn(
        image,
        settings.orientation,
        settings.crop_ratio,
        settings.crop_zoom_percent,
        settings.crop_offset_x_percent,
        settings.crop_offset_y_percent,
    )
    image = ImageEnhance.Brightness(image).enhance(settings.brightness_percent / 100.0)
    image = apply_stamp_fn(image, stamp_text_fn(path, settings), settings)
    image = apply_stamp_fn(
        image,
        location_stamp_text_fn(settings),
        settings,
        corner=settings.location_corner,
        scale_percent=settings.location_stamp_scale_percent,
        offset_x_px=settings.location_stamp_offset_x_px,
        offset_y_px=settings.location_stamp_offset_y_px,
        color_value=settings.location_stamp_color,
        border_color_value=settings.location_stamp_border_color,
        vertical=settings.location_stamp_vertical,
        adaptive_text=settings.location_stamp_adaptive_text,
    )
    return image


def render_preview_image(
    path: Path,
    settings: Any,
    max_dimension: int,
    *,
    load_image_as_rgb_fn: Callable[..., Image.Image],
    apply_manual_rotation_fn: Callable[[Image.Image, int], Image.Image],
    center_crop_to_ratio_fn: Callable[..., Image.Image],
    stamp_text_fn: Callable[[Path, Any], str],
    location_stamp_text_fn: Callable[[Any], str],
    apply_stamp_fn: Callable[..., Image.Image],
    debug_logger: Callable[[str], None] | None = None,
) -> Image.Image:
    image = load_image_as_rgb_fn(path, debug_logger=debug_logger)
    image = apply_manual_rotation_fn(image, settings.rotation_degrees)

    if max_dimension > 0:
        longest = max(image.width, image.height)
        if longest > max_dimension:
            scale = max_dimension / float(longest)
            resized = (
                max(1, int(round(image.width * scale))),
                max(1, int(round(image.height * scale))),
            )
            image = image.resize(resized, Image.Resampling.LANCZOS)

    image = center_crop_to_ratio_fn(
        image,
        settings.orientation,
        settings.crop_ratio,
        settings.crop_zoom_percent,
        settings.crop_offset_x_percent,
        settings.crop_offset_y_percent,
    )
    image = ImageEnhance.Brightness(image).enhance(settings.brightness_percent / 100.0)
    image = apply_stamp_fn(image, stamp_text_fn(path, settings), settings)
    image = apply_stamp_fn(
        image,
        location_stamp_text_fn(settings),
        settings,
        corner=settings.location_corner,
        scale_percent=settings.location_stamp_scale_percent,
        offset_x_px=settings.location_stamp_offset_x_px,
        offset_y_px=settings.location_stamp_offset_y_px,
        color_value=settings.location_stamp_color,
        border_color_value=settings.location_stamp_border_color,
        vertical=settings.location_stamp_vertical,
        adaptive_text=settings.location_stamp_adaptive_text,
    )
    return image


__all__ = [
    "apply_stamp",
    "load_stamp_font",
    "location_stamp_text",
    "render_image",
    "render_preview_image",
    "stamp_text",
]
