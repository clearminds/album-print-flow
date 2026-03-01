from __future__ import annotations

APP_DESKTOP_ID = "se.clearimnds.album-print-flow"
APP_ORGANIZATION_NAME = "clearimnds"
APP_ORGANIZATION_DOMAIN = "clearimnds.se"

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

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
    *RAW_EXTENSIONS,
}

METADATA_FILENAME = ".album_print_flow.json"
LOG_FILENAME = "album_print_flow.log"
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
LOG_LEVEL_RANK = {"DEBUG": 0, "INFO": 10, "WARNING": 20, "ERROR": 30}

CROP_RATIOS = ["2:3", "3:4", "4:5", "1:1", "16:9"]
CROP_RATIO_LABELS = {
    "2:3": "2:3 (10x15 cm / 4x6 in, 13x18 cm / 5x7 in, 20x30 cm / 8x12 in)",
    "3:4": "3:4 (15x20 cm / 6x8 in)",
    "4:5": "4:5 (20x25 cm / 8x10 in)",
    "1:1": "1:1 (10x10 cm / 4x4 in)",
    "16:9": "16:9 (10x18 cm / 4x7 in, panoramic)",
}
PAPER_LABELS = {
    "10x15 cm": "10x15 cm (4x6 in)",
    "A3": "A3 (11.7x16.5 in)",
    "A3+": "A3+ (13x19 in)",
    "A4": "A4 (8.3x11.7 in)",
    "A4+": "A4+ (8.3x13 in)",
}
SORT_MODES = [
    "Filename (A-Z)",
    "Filename (Z-A)",
    "EXIF Date (Oldest first)",
    "EXIF Date (Newest first)",
    "Filename Date (Oldest first)",
    "Filename Date (Newest first)",
    "File Modified (Oldest first)",
    "File Modified (Newest first)",
]

TABLE_COL_THUMB = 0
TABLE_COL_STATE = 1
TABLE_COL_PRINT = 2
TABLE_COL_FILE = 3
TABLE_COL_DATE_USED = 4
TABLE_COL_LOCATION = 5
TABLE_COL_ASPECT = 6

THUMBNAIL_SIZE = 40
THUMBNAIL_MAX_INFLIGHT = 4
THUMBNAIL_UI_CACHE_WARMUP_MAX = 36
TABLE_METADATA_BATCH_SIZE = 4
TABLE_METADATA_BATCH_SIZE_IDLE = 6
TABLE_METADATA_BATCH_SIZE_SCROLLING = 2
TABLE_METADATA_SCROLL_WINDOW_SECONDS = 0.35
REFRAME_HANDLE_SIZE = 14
STAMP_SCALE_MIN_PERCENT = 20
STAMP_SCALE_MAX_PERCENT = 180
STAMP_OFFSET_MIN_PX = 0
STAMP_OFFSET_MAX_PX = 240

SETTINGS_ORG = "album-print-flow"
SETTINGS_APP = "AlbumPrintFlow"
PRINT_BACKENDS = ["Auto", "CUPS", "Qt", "IPP"]

NOMINATIM_DEFAULT_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS = 1.0
NOMINATIM_CACHE_FILENAME = "nominatim_reverse_cache.json"
NOMINATIM_CACHE_MAX_ENTRIES = 2000
NOMINATIM_AUTH_MODES = ["None", "Bearer Token", "Basic Auth"]
NOMINATIM_ZOOM_LEVEL_OPTIONS: list[tuple[int, str]] = [
    (18, "18 — Building"),
    (17, "17 — Major Streets"),
    (16, "16 — Minor Streets"),
    (15, "15 — Blocks"),
    (14, "14 — Suburb"),
    (13, "13 — Village / Town / City District"),
    (12, "12 — Town / City"),
    (10, "10 — Region / State"),
    (8, "8 — County"),
    (5, "5 — Country"),
    (0, "0 — None"),
]
LOCATION_FORMAT_OPTIONS = [
    "Address Label",
    "Street Address",
    "City, Region",
    "County, Country",
    "Country",
    "Custom Template",
    "Lat/Lon",
    "DMS",
]
LOCATION_FORMAT_TEMPLATE_DEFAULT = "{city}, {admin.level4}, {country}"
LOCATION_TEMPLATE_TOKENS = [
    "label",
    "housenumber",
    "street",
    "postcode",
    "city",
    "county",
    "country",
    "admin.level7",
    "admin.level6",
    "admin.level5",
    "admin.level4",
    "admin.level3",
    "admin.level2",
]
PER_IMAGE_LOCATION_STAMP_OVERRIDES = [
    "Default",
    "Off",
    "Custom Text",
    *LOCATION_FORMAT_OPTIONS,
]

__all__ = [
    "APP_DESKTOP_ID",
    "APP_ORGANIZATION_DOMAIN",
    "APP_ORGANIZATION_NAME",
    "CROP_RATIOS",
    "CROP_RATIO_LABELS",
    "LOCATION_FORMAT_OPTIONS",
    "LOCATION_FORMAT_TEMPLATE_DEFAULT",
    "LOCATION_TEMPLATE_TOKENS",
    "LOG_FILENAME",
    "LOG_LEVELS",
    "LOG_LEVEL_RANK",
    "METADATA_FILENAME",
    "NOMINATIM_AUTH_MODES",
    "NOMINATIM_CACHE_FILENAME",
    "NOMINATIM_CACHE_MAX_ENTRIES",
    "NOMINATIM_DEFAULT_RATE_LIMIT_SECONDS",
    "NOMINATIM_DEFAULT_REVERSE_URL",
    "NOMINATIM_ZOOM_LEVEL_OPTIONS",
    "PAPER_LABELS",
    "PER_IMAGE_LOCATION_STAMP_OVERRIDES",
    "PRINT_BACKENDS",
    "RAW_EXTENSIONS",
    "REFRAME_HANDLE_SIZE",
    "SETTINGS_APP",
    "SETTINGS_ORG",
    "SORT_MODES",
    "STAMP_OFFSET_MAX_PX",
    "STAMP_OFFSET_MIN_PX",
    "STAMP_SCALE_MAX_PERCENT",
    "STAMP_SCALE_MIN_PERCENT",
    "SUPPORTED_EXTENSIONS",
    "TABLE_COL_ASPECT",
    "TABLE_COL_DATE_USED",
    "TABLE_COL_FILE",
    "TABLE_COL_LOCATION",
    "TABLE_COL_PRINT",
    "TABLE_COL_STATE",
    "TABLE_COL_THUMB",
    "TABLE_METADATA_BATCH_SIZE",
    "TABLE_METADATA_BATCH_SIZE_IDLE",
    "TABLE_METADATA_BATCH_SIZE_SCROLLING",
    "TABLE_METADATA_SCROLL_WINDOW_SECONDS",
    "THUMBNAIL_MAX_INFLIGHT",
    "THUMBNAIL_SIZE",
    "THUMBNAIL_UI_CACHE_WARMUP_MAX",
]
