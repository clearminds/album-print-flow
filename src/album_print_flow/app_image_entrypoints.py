from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image

from album_print_flow.app_primitives import (
    _dms_to_decimal,
    parse_datetime_from_filename,
)
from album_print_flow.image_io_helpers import (
    datetime_for_image as datetime_for_image_impl,
)
from album_print_flow.image_io_helpers import (
    exif_datetime_for_image as exif_datetime_for_image_impl,
)
from album_print_flow.image_io_helpers import (
    exif_location_for_image as exif_location_for_image_impl,
)
from album_print_flow.image_io_helpers import (
    extract_exif_datetime as extract_exif_datetime_impl,
)
from album_print_flow.image_io_helpers import (
    extract_exif_location as extract_exif_location_impl,
)
from album_print_flow.image_io_helpers import (
    extract_metadata_for_image_path as extract_metadata_for_image_path_impl,
)
from album_print_flow.image_io_helpers import (
    extract_metadata_from_open_image as extract_metadata_from_open_image_impl,
)
from album_print_flow.image_io_helpers import (
    load_image_as_rgb as load_image_as_rgb_impl,
)
from album_print_flow.image_io_helpers import (
    original_metadata_path_for_image as original_metadata_path_for_image_impl,
)
from album_print_flow.image_io_helpers import path_cache_key as path_cache_key_impl
from album_print_flow.image_io_helpers import (
    store_image_metadata_cache as store_image_metadata_cache_impl,
)

try:
    import rawpy
except Exception:
    rawpy = None

RAW_EXTENSIONS = {
    ".dng",
    ".arw",
    ".cr2",
    ".cr3",
    ".nef",
    ".nrw",
    ".orf",
    ".rw2",
    ".raf",
    ".pef",
    ".srw",
}
HEIC_SIDECAR_SUFFIXES = (".heic", ".heif")
HEIC_JPEG_SIDECAR_SUFFIX = ".jpg"
HEIC_SIDECAR_JPEG_QUALITY = 95
IMAGE_RGB_CACHE_MAX_ITEMS = 16
IMAGE_METADATA_CACHE_MAX_ITEMS = 128

_image_rgb_cache: OrderedDict[tuple[str, int, int], Image.Image] = OrderedDict()
_image_metadata_cache: OrderedDict[
    tuple[str, int, int],
    tuple[datetime | None, tuple[float, float] | None],
] = OrderedDict()

DATETIME_ORIGINAL_TAG = next(
    tag for tag, name in ExifTags.TAGS.items() if name == "DateTimeOriginal"
)
DATETIME_DIGITIZED_TAG = next(
    tag for tag, name in ExifTags.TAGS.items() if name == "DateTimeDigitized"
)
DATETIME_TAG = next(tag for tag, name in ExifTags.TAGS.items() if name == "DateTime")
GPSINFO_TAG = next(
    (tag for tag, name in ExifTags.TAGS.items() if name == "GPSInfo"),
    None,
)


def _path_cache_key(path: Path) -> tuple[str, int, int] | None:
    return path_cache_key_impl(path)


def _extract_exif_datetime(exif: object) -> datetime | None:
    return extract_exif_datetime_impl(
        exif,
        datetime_original_tag=DATETIME_ORIGINAL_TAG,
        datetime_digitized_tag=DATETIME_DIGITIZED_TAG,
        datetime_tag=DATETIME_TAG,
    )


def _extract_exif_location(exif: object) -> tuple[float, float] | None:
    return extract_exif_location_impl(
        exif,
        gpsinfo_tag=GPSINFO_TAG,
        dms_to_decimal_fn=_dms_to_decimal,
    )


def _extract_metadata_from_open_image(
    image: Image.Image,
) -> tuple[datetime | None, tuple[float, float] | None]:
    return extract_metadata_from_open_image_impl(
        image,
        extract_exif_datetime_fn=_extract_exif_datetime,
        extract_exif_location_fn=_extract_exif_location,
    )


def _store_image_metadata_cache(
    path: Path,
    captured_at: datetime | None,
    location: tuple[float, float] | None,
) -> None:
    store_image_metadata_cache_impl(
        path,
        captured_at,
        location,
        path_cache_key_fn=_path_cache_key,
        image_metadata_cache=_image_metadata_cache,
        image_metadata_cache_max_items=IMAGE_METADATA_CACHE_MAX_ITEMS,
    )


def _extract_metadata_for_image_path(
    path: Path,
) -> tuple[datetime | None, tuple[float, float] | None]:
    return extract_metadata_for_image_path_impl(
        path,
        path_cache_key_fn=_path_cache_key,
        image_metadata_cache=_image_metadata_cache,
        extract_metadata_from_open_image_fn=_extract_metadata_from_open_image,
        store_image_metadata_cache_fn=_store_image_metadata_cache,
    )


def datetime_for_image(path: Path) -> datetime:
    return datetime_for_image_impl(
        path,
        original_metadata_path_for_image_fn=original_metadata_path_for_image,
        extract_metadata_for_image_path_fn=_extract_metadata_for_image_path,
        parse_datetime_from_filename_fn=parse_datetime_from_filename,
    )


def exif_datetime_for_image(path: Path) -> datetime | None:
    return exif_datetime_for_image_impl(
        path,
        original_metadata_path_for_image_fn=original_metadata_path_for_image,
        extract_metadata_for_image_path_fn=_extract_metadata_for_image_path,
    )


def load_image_as_rgb(
    path: Path,
    debug_logger: Callable[[str], None] | None = None,
) -> Image.Image:
    return load_image_as_rgb_impl(
        path,
        path_cache_key_fn=_path_cache_key,
        image_rgb_cache=_image_rgb_cache,
        image_rgb_cache_max_items=IMAGE_RGB_CACHE_MAX_ITEMS,
        heic_sidecar_suffixes=HEIC_SIDECAR_SUFFIXES,
        heic_jpeg_sidecar_suffix=HEIC_JPEG_SIDECAR_SUFFIX,
        extract_metadata_from_open_image_fn=_extract_metadata_from_open_image,
        store_image_metadata_cache_fn=_store_image_metadata_cache,
        extract_metadata_for_image_path_fn=_extract_metadata_for_image_path,
        original_metadata_path_for_image_fn=original_metadata_path_for_image,
        heic_sidecar_jpeg_quality=HEIC_SIDECAR_JPEG_QUALITY,
        rawpy_module=rawpy,
        raw_extensions=RAW_EXTENSIONS,
        debug_logger=debug_logger,
    )


def exif_location_for_image(path: Path) -> tuple[float, float] | None:
    return exif_location_for_image_impl(
        path,
        original_metadata_path_for_image_fn=original_metadata_path_for_image,
        extract_metadata_for_image_path_fn=_extract_metadata_for_image_path,
    )


def original_metadata_path_for_image(path: Path) -> Path:
    return original_metadata_path_for_image_impl(path)


__all__ = [
    "datetime_for_image",
    "exif_datetime_for_image",
    "exif_location_for_image",
    "load_image_as_rgb",
    "original_metadata_path_for_image",
]
