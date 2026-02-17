from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


def path_cache_key(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return (str(path), stat.st_mtime_ns, stat.st_size)


def extract_exif_datetime(
    exif: object,
    *,
    datetime_original_tag: int,
    datetime_digitized_tag: int,
    datetime_tag: int,
) -> datetime | None:
    if exif is None or not hasattr(exif, "get"):
        return None
    for tag in (datetime_original_tag, datetime_digitized_tag, datetime_tag):
        try:
            value = exif.get(tag)
        except Exception:
            value = None
        if not value:
            continue
        try:
            return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
    return None


def extract_exif_location(
    exif: object,
    *,
    gpsinfo_tag: int | None,
    dms_to_decimal_fn: Callable[[object, str], float | None],
) -> tuple[float, float] | None:
    if gpsinfo_tag is None or exif is None or not hasattr(exif, "get"):
        return None

    try:
        gps_info = exif.get(gpsinfo_tag)
    except Exception:
        gps_info = None
    if not isinstance(gps_info, dict):
        return None

    lat_ref_raw = gps_info.get(1)
    lat_dms = gps_info.get(2)
    lon_ref_raw = gps_info.get(3)
    lon_dms = gps_info.get(4)

    lat_ref = str(lat_ref_raw or "").strip().upper()
    lon_ref = str(lon_ref_raw or "").strip().upper()
    if lat_ref not in {"N", "S"} or lon_ref not in {"E", "W"}:
        return None

    latitude = dms_to_decimal_fn(lat_dms, lat_ref)
    longitude = dms_to_decimal_fn(lon_dms, lon_ref)
    if latitude is None or longitude is None:
        return None

    if latitude < -90.0 or latitude > 90.0 or longitude < -180.0 or longitude > 180.0:
        return None
    return latitude, longitude


def extract_metadata_from_open_image(
    image: Image.Image,
    *,
    extract_exif_datetime_fn: Callable[[object], datetime | None],
    extract_exif_location_fn: Callable[[object], tuple[float, float] | None],
) -> tuple[datetime | None, tuple[float, float] | None]:
    try:
        exif = image.getexif() or {}
    except Exception:
        exif = {}
    return extract_exif_datetime_fn(exif), extract_exif_location_fn(exif)


def store_image_metadata_cache(
    path: Path,
    captured_at: datetime | None,
    location: tuple[float, float] | None,
    *,
    path_cache_key_fn: Callable[[Path], tuple[str, int, int] | None],
    image_metadata_cache: Any,
    image_metadata_cache_max_items: int,
) -> None:
    key = path_cache_key_fn(path)
    if key is None:
        return
    image_metadata_cache[key] = (captured_at, location)
    image_metadata_cache.move_to_end(key)
    while len(image_metadata_cache) > image_metadata_cache_max_items:
        image_metadata_cache.popitem(last=False)


def extract_metadata_for_image_path(
    path: Path,
    *,
    path_cache_key_fn: Callable[[Path], tuple[str, int, int] | None],
    image_metadata_cache: Any,
    extract_metadata_from_open_image_fn: Callable[
        [Image.Image], tuple[datetime | None, tuple[float, float] | None]
    ],
    store_image_metadata_cache_fn: Callable[
        [Path, datetime | None, tuple[float, float] | None], None
    ],
) -> tuple[datetime | None, tuple[float, float] | None]:
    key = path_cache_key_fn(path)
    if key is not None:
        cached = image_metadata_cache.get(key)
        if cached is not None:
            image_metadata_cache.move_to_end(key)
            return cached

    captured_at: datetime | None = None
    location: tuple[float, float] | None = None
    try:
        with Image.open(path) as image:
            captured_at, location = extract_metadata_from_open_image_fn(image)
    except OSError:
        pass

    store_image_metadata_cache_fn(path, captured_at, location)
    return captured_at, location


def original_metadata_path_for_image(path: Path) -> Path:
    name = path.name.lower()
    if name.endswith(".heic.jpg") or name.endswith(".heif.jpg"):
        original_candidate = path.with_name(path.name[:-4])
        if original_candidate.exists() and original_candidate.is_file():
            return original_candidate
    return path


def datetime_for_image(
    path: Path,
    *,
    original_metadata_path_for_image_fn: Callable[[Path], Path],
    extract_metadata_for_image_path_fn: Callable[
        [Path], tuple[datetime | None, tuple[float, float] | None]
    ],
    parse_datetime_from_filename_fn: Callable[[str], datetime | None],
) -> datetime:
    metadata_path = original_metadata_path_for_image_fn(path)
    captured_at, _location = extract_metadata_for_image_path_fn(metadata_path)
    if captured_at is not None:
        return captured_at

    from_filename = parse_datetime_from_filename_fn(metadata_path.name)
    if from_filename:
        return from_filename

    return datetime.fromtimestamp(metadata_path.stat().st_mtime)


def exif_datetime_for_image(
    path: Path,
    *,
    original_metadata_path_for_image_fn: Callable[[Path], Path],
    extract_metadata_for_image_path_fn: Callable[
        [Path], tuple[datetime | None, tuple[float, float] | None]
    ],
) -> datetime | None:
    metadata_path = original_metadata_path_for_image_fn(path)
    captured_at, _location = extract_metadata_for_image_path_fn(metadata_path)
    return captured_at


def exif_location_for_image(
    path: Path,
    *,
    original_metadata_path_for_image_fn: Callable[[Path], Path],
    extract_metadata_for_image_path_fn: Callable[
        [Path], tuple[datetime | None, tuple[float, float] | None]
    ],
) -> tuple[float, float] | None:
    metadata_path = original_metadata_path_for_image_fn(path)
    _captured_at, location = extract_metadata_for_image_path_fn(metadata_path)
    return location


def load_image_as_rgb(
    path: Path,
    *,
    path_cache_key_fn: Callable[[Path], tuple[str, int, int] | None],
    image_rgb_cache: Any,
    image_rgb_cache_max_items: int,
    heic_sidecar_suffixes: tuple[str, ...],
    heic_jpeg_sidecar_suffix: str,
    extract_metadata_from_open_image_fn: Callable[
        [Image.Image], tuple[datetime | None, tuple[float, float] | None]
    ],
    store_image_metadata_cache_fn: Callable[
        [Path, datetime | None, tuple[float, float] | None], None
    ],
    extract_metadata_for_image_path_fn: Callable[
        [Path], tuple[datetime | None, tuple[float, float] | None]
    ],
    original_metadata_path_for_image_fn: Callable[[Path], Path],
    heic_sidecar_jpeg_quality: int,
    rawpy_module: object,
    raw_extensions: set[str],
    debug_logger: Callable[[str], None] | None = None,
) -> Image.Image:
    def load_from_memory_cache(candidate: Path) -> Image.Image | None:
        key = path_cache_key_fn(candidate)
        if key is None:
            return None
        cached = image_rgb_cache.get(key)
        if cached is None:
            return None
        image_rgb_cache.move_to_end(key)
        return cached.copy()

    def store_in_memory_cache(candidate: Path, image_rgb: Image.Image) -> None:
        key = path_cache_key_fn(candidate)
        if key is None:
            return
        image_rgb_cache[key] = image_rgb.copy()
        image_rgb_cache.move_to_end(key)
        while len(image_rgb_cache) > image_rgb_cache_max_items:
            image_rgb_cache.popitem(last=False)

    cached_primary = load_from_memory_cache(path)
    if cached_primary is not None:
        return cached_primary

    suffix = path.suffix.lower()
    sidecar_path = None
    if suffix in heic_sidecar_suffixes:
        sidecar_path = path.with_name(f"{path.name}{heic_jpeg_sidecar_suffix}")
        if sidecar_path.exists():
            cached_sidecar = load_from_memory_cache(sidecar_path)
            if cached_sidecar is not None:
                return cached_sidecar
            try:
                with Image.open(sidecar_path) as source:
                    captured_at, location = extract_metadata_from_open_image_fn(source)
                    store_image_metadata_cache_fn(path, captured_at, location)
                    if captured_at is None and location is None:
                        extract_metadata_for_image_path_fn(
                            original_metadata_path_for_image_fn(path)
                        )
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    store_in_memory_cache(sidecar_path, image)
                    return image
            except OSError as sidecar_error:
                if debug_logger is not None:
                    debug_logger(
                        "IMAGE sidecar decode failed, falling back to source: "
                        f"{sidecar_path.name}: {sidecar_error}"
                    )

    try:
        with Image.open(path) as source:
            captured_at, location = extract_metadata_from_open_image_fn(source)
            store_image_metadata_cache_fn(
                original_metadata_path_for_image_fn(path), captured_at, location
            )
            image = ImageOps.exif_transpose(source).convert("RGB")

            if sidecar_path is not None and not sidecar_path.exists():
                try:
                    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
                    temp_sidecar = sidecar_path.with_name(
                        f".{sidecar_path.name}.{uuid.uuid4().hex}.tmp"
                    )
                    image.save(
                        temp_sidecar,
                        format="JPEG",
                        quality=heic_sidecar_jpeg_quality,
                        optimize=True,
                    )
                    temp_sidecar.replace(sidecar_path)
                except OSError as sidecar_save_error:
                    if debug_logger is not None:
                        debug_logger(
                            "IMAGE sidecar save failed (continuing): "
                            f"{sidecar_path.name}: {sidecar_save_error}"
                        )

            if sidecar_path is not None and sidecar_path.exists():
                store_in_memory_cache(sidecar_path, image)
            else:
                store_in_memory_cache(path, image)
            return image
    except OSError as original_error:
        if debug_logger is not None:
            debug_logger(f"IMAGE Pillow decode failed: {path.name}: {original_error}")

        if rawpy_module is None or suffix not in raw_extensions:
            raise

        try:
            with rawpy_module.imread(str(path)) as raw_image:
                rgb = raw_image.postprocess(
                    use_camera_wb=True,
                    output_bps=8,
                )
            image = Image.fromarray(rgb).convert("RGB")
            store_in_memory_cache(path, image)
            return image
        except Exception as raw_error:
            if debug_logger is not None:
                debug_logger(f"IMAGE rawpy fallback failed: {path.name}: {raw_error}")
            raise OSError(
                f"Unsupported or unreadable image file: {path.name}"
            ) from raw_error


__all__ = [
    "datetime_for_image",
    "exif_datetime_for_image",
    "exif_location_for_image",
    "extract_exif_datetime",
    "extract_exif_location",
    "extract_metadata_for_image_path",
    "extract_metadata_from_open_image",
    "load_image_as_rgb",
    "original_metadata_path_for_image",
    "path_cache_key",
    "store_image_metadata_cache",
]
