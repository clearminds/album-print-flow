from __future__ import annotations

import hashlib
import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image
from PIL.ExifTags import IFD
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except Exception:
    pillow_heif = None

from album_printer.account_store import SubmoduleAccountStore
from album_printer.sources.types import SourceAsset, SourceLoadResult


def _sanitize_text(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def _sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())
    cleaned = cleaned.strip("._")
    return cleaned or "album"


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_exif_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _format_relative_loaded_at(value: object) -> str:
    if not isinstance(value, str):
        return ""
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return _sanitize_text(value)

    try:
        now = (
            datetime.now(parsed.tzinfo) if parsed.tzinfo is not None else datetime.now()
        )
        delta_seconds = int((now - parsed).total_seconds())
    except Exception:
        return _sanitize_text(value)

    if delta_seconds < 60:
        return "just now"
    if delta_seconds < 3600:
        return f"{max(1, delta_seconds // 60)}m ago"
    if delta_seconds < 86400:
        return f"{max(1, delta_seconds // 3600)}h ago"
    if delta_seconds < 86400 * 7:
        return f"{max(1, delta_seconds // 86400)}d ago"
    return parsed.strftime("%Y-%m-%d %H:%M")


def _rational_to_float(value: object) -> float | None:
    try:
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            denominator = float(value.denominator)
            if denominator == 0.0:
                return None
            return float(value.numerator) / denominator
        if isinstance(value, tuple) and len(value) == 2:
            denominator = float(value[1])
            if denominator == 0.0:
                return None
            return float(value[0]) / denominator
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _gps_components_to_degrees(value: object) -> float | None:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        return None
    deg = _rational_to_float(value[0])
    minute = _rational_to_float(value[1])
    second = _rational_to_float(value[2])
    if deg is None or minute is None or second is None:
        return None
    return deg + (minute / 60.0) + (second / 3600.0)


def _gps_decimal(ref: object, value: object) -> float | None:
    degrees = _gps_components_to_degrees(value)
    if degrees is None:
        return None
    sign = 1.0
    if isinstance(ref, (bytes, bytearray)):
        try:
            ref = ref.decode("utf-8", errors="ignore")
        except Exception:
            ref = ""
    ref_text = str(ref or "").strip().upper()
    if ref_text in {"S", "W"}:
        sign = -1.0
    return sign * degrees


def _guess_extension(content_type: str, payload: bytes) -> str:
    content_type_lower = content_type.lower()
    if "heif" in content_type_lower or "heic" in content_type_lower:
        return ".heic"
    if "jpeg" in content_type_lower or "jpg" in content_type_lower:
        return ".jpg"
    if "png" in content_type_lower:
        return ".png"
    if "webp" in content_type_lower:
        return ".webp"
    if "gif" in content_type_lower:
        return ".gif"

    prefix = payload[:16]
    if prefix.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(prefix) >= 12 and prefix[4:12] == b"ftypheic":
        return ".heic"
    if len(prefix) >= 12 and prefix[4:12] == b"ftypheif":
        return ".heic"
    if prefix.startswith(b"GIF8"):
        return ".gif"
    return ".jpg"


def _is_displayable_content_type(content_type: str) -> bool:
    text = str(content_type or "").strip().lower()
    if not text.startswith("image/"):
        return False
    subtype = text.split("/", 1)[1].split(";", 1)[0].strip()
    return subtype in {
        "jpeg",
        "jpg",
        "pjpeg",
        "png",
        "webp",
        "gif",
        "heic",
        "heif",
        "tiff",
        "tif",
        "bmp",
    }


@dataclass(slots=True)
class _DownloadedMedia:
    payload: bytes
    content_type: str
    variant: str


class GooglePhotosAlbumUrlSource:
    source_id = "google-photos-album-url"
    label = "Google Photos Album URL"
    help_text = (
        "Loads a shared Google Photos album URL (photos.app.goo.gl / photos.google.com).\n"
        "Designed for metadata-friendly downloads where available (tries original download variant first).\n"
        "Great for shared family albums and quick reload checks for newly added photos."
    )

    def __init__(
        self,
        app_name: str = "album-print-flow",
        debug_logger: Callable[[str, str], None] | None = None,
    ) -> None:
        self.app_name = app_name
        self.debug_logger = debug_logger
        self._cancel_requested = False
        self.google_account_store = SubmoduleAccountStore(
            app_name,
            "google_contexts.json",
            defaults={"accounts": {}, "last_account_id": "", "albums": {}},
        )

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def clear_cancel(self) -> None:
        self._cancel_requested = False

    def _ensure_not_cancelled(self) -> None:
        if self._cancel_requested:
            self._info("sync cancelled by user")
            raise RuntimeError("Album sync cancelled")

    def _log(self, level: str, message: str) -> None:
        logger = self.debug_logger
        if logger is None:
            return
        try:
            logger(level, f"GOOGLE_ALBUM_URL {message}")
        except Exception:
            return

    def _debug(self, message: str) -> None:
        self._log("DEBUG", message)

    def _info(self, message: str) -> None:
        self._log("INFO", message)

    def config_root(self) -> Path:
        return Path.home() / ".config" / self.app_name

    def cache_root(self) -> Path:
        return Path.home() / ".cache" / self.app_name / "google-photos-albums"

    def state_path(self) -> Path:
        return self.config_root() / "google_album_url_state.json"

    def _active_account_key(self) -> str:
        account_id = self._active_google_account_id()
        return account_id if account_id else "__default__"

    def load_state(self) -> dict[str, object]:
        path = self.state_path()
        if not path.exists():
            return {
                "version": 1,
                "bookmarks_by_account": {},
                "recent_by_account": {},
                "url_context_map": {},
            }
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                state = {
                    "version": 1,
                    "bookmarks_by_account": {},
                    "recent_by_account": {},
                    "url_context_map": {},
                } | data
                if not isinstance(state.get("bookmarks_by_account"), dict):
                    state["bookmarks_by_account"] = {}
                if not isinstance(state.get("recent_by_account"), dict):
                    state["recent_by_account"] = {}
                if not isinstance(state.get("url_context_map"), dict):
                    state["url_context_map"] = {}
                return state
        except (OSError, json.JSONDecodeError):
            pass
        return {
            "version": 1,
            "bookmarks_by_account": {},
            "recent_by_account": {},
            "url_context_map": {},
        }

    def _context_hints(self, state: dict[str, object]) -> dict[str, str]:
        raw_map = state.get("url_context_map")
        if not isinstance(raw_map, dict):
            return {}
        hints: dict[str, str] = {}
        for key, value in raw_map.items():
            normalized_key = self._normalize_share_url(str(key or ""))
            normalized_value = self._normalize_share_url(str(value or ""))
            if normalized_key and normalized_value:
                hints[normalized_key] = normalized_value
        return hints

    def _set_context_hint(
        self,
        state: dict[str, object],
        input_url: str,
        context_id: str,
    ) -> None:
        normalized_input = self._normalize_share_url(input_url)
        normalized_context = self._normalize_share_url(context_id)
        if not normalized_input or not normalized_context:
            return
        hints = self._context_hints(state)
        hints[normalized_input] = normalized_context
        hints[normalized_context] = normalized_context
        state["url_context_map"] = hints

    def _active_google_account_id(self) -> str:
        context = self.google_account_store.load_state()
        return self.google_account_store.get_last_account_id(context)

    def _bookmarks_for_active_account(
        self, state: dict[str, object]
    ) -> list[dict[str, object]]:
        by_account = state.get("bookmarks_by_account")
        if isinstance(by_account, dict):
            account_items = by_account.get(self._active_account_key())
            if isinstance(account_items, list):
                return [item for item in account_items if isinstance(item, dict)]
        return []

    def _set_bookmarks_for_active_account(
        self,
        state: dict[str, object],
        bookmarks: list[dict[str, object]],
    ) -> None:
        cleaned = [item for item in bookmarks if isinstance(item, dict)]
        by_account = state.get("bookmarks_by_account")
        if not isinstance(by_account, dict):
            by_account = {}
        by_account[self._active_account_key()] = cleaned
        state["bookmarks_by_account"] = by_account

    def _recent_for_active_account(
        self, state: dict[str, object]
    ) -> list[dict[str, object]]:
        by_account = state.get("recent_by_account")
        if isinstance(by_account, dict):
            account_items = by_account.get(self._active_account_key())
            if isinstance(account_items, list):
                return [item for item in account_items if isinstance(item, dict)]
        return []

    def _set_recent_for_active_account(
        self,
        state: dict[str, object],
        recent_entries: list[dict[str, object]],
    ) -> None:
        cleaned = [item for item in recent_entries if isinstance(item, dict)]
        by_account = state.get("recent_by_account")
        if not isinstance(by_account, dict):
            by_account = {}
        by_account[self._active_account_key()] = cleaned
        state["recent_by_account"] = by_account

    def _bookmarks_for_picker(
        self, state: dict[str, object]
    ) -> list[dict[str, object]]:
        active_items = self._bookmarks_for_active_account(state)
        if active_items:
            return active_items
        by_account = state.get("bookmarks_by_account")
        merged: list[dict[str, object]] = []
        if isinstance(by_account, dict):
            for account_items in by_account.values():
                if not isinstance(account_items, list):
                    continue
                for item in account_items:
                    if isinstance(item, dict):
                        merged.append(item)
        if merged:
            return merged
        return merged

    def _recent_for_picker(self, state: dict[str, object]) -> list[dict[str, object]]:
        active_items = self._recent_for_active_account(state)
        if active_items:
            return active_items
        by_account = state.get("recent_by_account")
        merged: list[dict[str, object]] = []
        if isinstance(by_account, dict):
            for account_items in by_account.values():
                if not isinstance(account_items, list):
                    continue
                for item in account_items:
                    if isinstance(item, dict):
                        merged.append(item)
        if merged:
            return merged
        return merged

    def list_accounts(self) -> list[dict[str, str]]:
        state = self.load_state()
        bookmarks = self._bookmarks_for_picker(state)
        rows: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for bookmark in bookmarks:
            if not isinstance(bookmark, dict):
                continue
            url = self._normalize_share_url(str(bookmark.get("url", "")))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            name = _sanitize_text(str(bookmark.get("name", "")))
            label = name or url
            rows.append(
                {
                    "account_id": url,
                    "label": label,
                    "source_label": self.label,
                }
            )
        return rows

    def add_account_interactive(self, parent: QWidget | None = None) -> bool:
        url_text, ok = QInputDialog.getText(
            parent,
            "Add Entry",
            "Google Photos album URL",
        )
        if not ok:
            return False

        normalized_url = self._normalize_share_url(url_text)
        if not normalized_url:
            QMessageBox.warning(parent, self.label, "Album URL is empty")
            return False
        if (
            "photos.app.goo.gl" not in normalized_url
            and "photos.google.com" not in normalized_url
        ):
            QMessageBox.warning(
                parent,
                self.label,
                "URL does not look like a Google Photos shared album link.",
            )
            return False

        default_name = normalized_url
        bookmark_name, ok = QInputDialog.getText(
            parent,
            "Entry Name",
            "Name",
            text=default_name,
        )
        if not ok:
            return False

        state = self.load_state()
        self._add_bookmark(
            state,
            _sanitize_text(str(bookmark_name)) or default_name,
            normalized_url,
        )
        self.save_state(state)
        return True

    def delete_account(self, account_id: str) -> bool:
        target = self._normalize_share_url(str(account_id or ""))
        if not target:
            return False

        state = self.load_state()
        bookmarks = self._bookmarks_for_active_account(state)
        filtered = [
            bookmark
            for bookmark in bookmarks
            if self._normalize_share_url(str(bookmark.get("url", ""))) != target
        ]
        if len(filtered) == len(bookmarks):
            return False

        self._set_bookmarks_for_active_account(state, filtered)
        self.save_state(state)
        return True

    def refresh_account_oauth(self, parent: QWidget | None, account_id: str) -> bool:
        _ = parent
        target = self._normalize_share_url(str(account_id or ""))
        if not target:
            return False
        try:
            self._album_key_set_for_url(target)
        except Exception:
            return False
        return True

    def save_state(self, state: dict[str, object]) -> None:
        path = self.state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, ensure_ascii=False)
            tmp.replace(path)
        except OSError:
            return

    def _normalize_share_url(self, value: str) -> str:
        text = _sanitize_text(value)
        if not text:
            return ""
        if not text.startswith("http://") and not text.startswith("https://"):
            text = "https://" + text
        return text

    def _extract_album_title(self, html_text: str, fallback: str) -> str:
        meta = re.search(
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            html_text,
            flags=re.IGNORECASE,
        )
        if meta:
            return _sanitize_text(html.unescape(meta.group(1))) or fallback
        title = re.search(
            r"<title>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL
        )
        if title:
            return _sanitize_text(html.unescape(title.group(1))) or fallback
        return fallback

    def _extract_media_bases(self, html_text: str) -> list[str]:
        normalized_html = (
            html_text.replace("\\/", "/")
            .replace("\\u003d", "=")
            .replace("\\u0026", "&")
        )
        urls = re.findall(
            r"https://lh3\.googleusercontent\.com/pw/[^\"'\s)]+",
            normalized_html,
        )
        bases: list[str] = []
        seen: set[str] = set()
        for raw_url in urls:
            base = raw_url.split("=", 1)[0].strip()
            if not base or base in seen:
                continue
            seen.add(base)
            bases.append(base)
        return bases

    def _extract_web_captured_at_map(
        self,
        html_text: str,
        base_urls: list[str],
    ) -> dict[str, datetime]:
        normalized_html = (
            html_text.replace("\\/", "/")
            .replace("\\u003d", "=")
            .replace("\\u0026", "&")
        )
        pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
        mapping: dict[str, datetime] = {}
        if not normalized_html or not base_urls:
            return mapping

        for base_url in base_urls:
            index = normalized_html.find(base_url)
            if index < 0:
                continue
            start = max(0, index - 2200)
            end = min(len(normalized_html), index + 2200)
            window = normalized_html[start:end]
            center = index - start

            best: datetime | None = None
            best_distance: int | None = None
            for match in pattern.finditer(window):
                parsed = _parse_iso_datetime(match.group(0))
                if parsed is None:
                    continue
                distance = abs(match.start() - center)
                if best is None or best_distance is None or distance < best_distance:
                    best = parsed
                    best_distance = distance

            if best is not None:
                mapping[base_url] = best

        return mapping

    def _extract_web_location_map(
        self,
        html_text: str,
        base_urls: list[str],
    ) -> dict[str, tuple[float, float]]:
        normalized_html = (
            html_text.replace("\\/", "/")
            .replace("\\u003d", "=")
            .replace("\\u0026", "&")
        )
        mapping: dict[str, tuple[float, float]] = {}
        if not normalized_html or not base_urls:
            return mapping

        def _valid_pair(lat: float, lon: float) -> tuple[float, float] | None:
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon)
            return None

        lat_pattern = re.compile(
            r'"(?:lat|latitude)"\s*:\s*(-?\d+(?:\.\d+)?)',
            flags=re.IGNORECASE,
        )
        lon_pattern = re.compile(
            r'"(?:lon|lng|longitude)"\s*:\s*(-?\d+(?:\.\d+)?)',
            flags=re.IGNORECASE,
        )
        tuple_pattern = re.compile(r"(-?\d{1,2}\.\d{4,})\s*,\s*(-?\d{1,3}\.\d{4,})")

        for base_url in base_urls:
            index = normalized_html.find(base_url)
            if index < 0:
                continue
            start = max(0, index - 2600)
            end = min(len(normalized_html), index + 2600)
            window = normalized_html[start:end]
            center = index - start

            best_pair: tuple[float, float] | None = None
            best_distance: int | None = None

            lat_matches = [
                (match.start(), match.group(1))
                for match in lat_pattern.finditer(window)
            ]
            lon_matches = [
                (match.start(), match.group(1))
                for match in lon_pattern.finditer(window)
            ]
            if lat_matches and lon_matches:
                for lat_pos, lat_text in lat_matches:
                    try:
                        lat_value = float(lat_text)
                    except ValueError:
                        continue
                    nearest_lon = min(
                        lon_matches, key=lambda item: abs(item[0] - lat_pos)
                    )
                    try:
                        lon_value = float(nearest_lon[1])
                    except ValueError:
                        continue
                    pair = _valid_pair(lat_value, lon_value)
                    if pair is None:
                        continue
                    distance = min(abs(lat_pos - center), abs(nearest_lon[0] - center))
                    if best_distance is None or distance < best_distance:
                        best_pair = pair
                        best_distance = distance

            if best_pair is None:
                for match in tuple_pattern.finditer(window):
                    try:
                        lat_value = float(match.group(1))
                        lon_value = float(match.group(2))
                    except ValueError:
                        continue
                    pair = _valid_pair(lat_value, lon_value)
                    if pair is None:
                        continue
                    distance = abs(match.start() - center)
                    if best_distance is None or distance < best_distance:
                        best_pair = pair
                        best_distance = distance

            if best_pair is not None:
                mapping[base_url] = best_pair

        return mapping

    def _context_candidates_for_url(self, album_url: str) -> list[str]:
        normalized = self._normalize_share_url(album_url)
        candidates: list[str] = []
        state = self.load_state()
        if normalized:
            context_hint = self._context_hints(state).get(normalized, "")
            if context_hint:
                candidates.append(context_hint)
            if normalized not in candidates:
                candidates.append(normalized)

        def add_candidates_from_entries(entries: list[dict[str, object]]) -> None:
            for item in entries:
                if not isinstance(item, dict):
                    continue
                item_url = self._normalize_share_url(str(item.get("url", "")))
                if item_url != normalized:
                    continue
                context_id = self._normalize_share_url(
                    str(item.get("last_context_id") or item.get("context_id") or "")
                )
                if context_id and context_id not in candidates:
                    candidates.append(context_id)

        add_candidates_from_entries(self._bookmarks_for_active_account(state))
        add_candidates_from_entries(self._recent_for_active_account(state))

        for bucket_key in ("bookmarks_by_account", "recent_by_account"):
            by_account = state.get(bucket_key)
            if not isinstance(by_account, dict):
                continue
            for entries in by_account.values():
                if not isinstance(entries, list):
                    continue
                normalized_entries = [
                    item for item in entries if isinstance(item, dict)
                ]
                if normalized_entries:
                    add_candidates_from_entries(normalized_entries)

        return candidates

    def cached_snapshot(self, album_url: str) -> SourceLoadResult | None:
        for context_id in self._context_candidates_for_url(album_url):
            album_dir = self._album_dir(context_id)
            manifest = self._load_manifest(album_dir)
            items_raw = manifest.get("items")
            if not isinstance(items_raw, dict) or not items_raw:
                continue

            item_entries: list[dict[str, object]] = [
                value for value in items_raw.values() if isinstance(value, dict)
            ]
            if not item_entries:
                continue

            item_entries.sort(
                key=lambda value: (
                    int(value.get("order", 0))
                    if isinstance(value.get("order", 0), (int, float))
                    else 0
                )
            )

            assets: list[SourceAsset] = []
            for entry in item_entries:
                key = _sanitize_text(str(entry.get("key", "")))
                file_name = _sanitize_text(str(entry.get("file_name", "")))
                if not key or not file_name:
                    continue
                local_path = album_dir / file_name
                if not local_path.exists():
                    continue

                captured_at = _parse_iso_datetime(entry.get("captured_at"))
                latitude = entry.get("latitude")
                longitude = entry.get("longitude")
                lat_value = (
                    float(latitude) if isinstance(latitude, (int, float)) else None
                )
                lon_value = (
                    float(longitude) if isinstance(longitude, (int, float)) else None
                )
                base_url = _sanitize_text(str(entry.get("base_url", "")))
                source_data = {
                    "album_url": context_id,
                    "album_title": _sanitize_text(str(manifest.get("title", ""))),
                    "media_key": key,
                    "media_base_url": base_url,
                    "download_variant": str(entry.get("download_variant") or ""),
                    "content_type": str(entry.get("content_type") or ""),
                }

                assets.append(
                    SourceAsset(
                        key=key,
                        local_path=local_path,
                        display_name=file_name,
                        source_photo_id=key,
                        captured_at=captured_at,
                        latitude=lat_value,
                        longitude=lon_value,
                        source_data=source_data,
                    )
                )

            if not assets:
                continue

            title = _sanitize_text(str(manifest.get("title", ""))) or context_id
            context_label = f"{title} [{len(assets)} cached]"
            return SourceLoadResult(
                source_id=self.source_id,
                source_label=self.label,
                context_id=context_id,
                context_label=context_label,
                assets=assets,
                metadata_root=album_dir,
                is_new_context=False,
            )

        return None

    def live_sync_snapshot_info(self, album_url: str) -> dict[str, object] | None:
        for context_id in self._context_candidates_for_url(album_url):
            album_dir = self._album_dir(context_id)
            manifest = self._load_manifest(album_dir)
            items_raw = manifest.get("items")
            if not isinstance(items_raw, dict):
                continue

            item_count = len(items_raw)
            if item_count <= 0:
                continue

            return {
                "context_id": context_id,
                "title": _sanitize_text(str(manifest.get("title", ""))) or context_id,
                "item_count": int(item_count),
                "last_sync_at": _sanitize_text(str(manifest.get("last_sync_at", ""))),
                "last_sync_new": int(manifest.get("last_sync_new", 0) or 0),
                "last_sync_failed": int(manifest.get("last_sync_failed", 0) or 0),
            }

        return None

    def _album_key_set_for_url(self, album_url: str) -> tuple[str, str, set[str]]:
        normalized_url = self._normalize_share_url(album_url)
        if not normalized_url:
            raise RuntimeError("Album URL is empty")
        try:
            response = requests.get(normalized_url, allow_redirects=True, timeout=30)
        except requests.RequestException as error:
            raise RuntimeError(f"Unable to open album URL: {error}") from error

        if not response.ok:
            raise RuntimeError(
                f"Unable to open album URL (HTTP {response.status_code})"
            )

        resolved_url = self._normalize_share_url(response.url)
        if (
            "photos.google.com" not in resolved_url
            and "photos.app.goo.gl" not in resolved_url
        ):
            raise RuntimeError("URL did not resolve to a Google Photos album")

        album_title = self._extract_album_title(response.text, fallback=resolved_url)
        base_urls = self._extract_media_bases(response.text)
        if not base_urls:
            raise RuntimeError("No album media found at URL")
        keys = {
            hashlib.sha256(base_url.encode("utf-8")).hexdigest()[:24]
            for base_url in base_urls
        }
        return resolved_url, album_title, keys

    def check_bookmarked_updates(self, max_albums: int = 30) -> list[dict[str, object]]:
        state = self.load_state()
        bookmarks_raw = self._bookmarks_for_active_account(state)
        if not bookmarks_raw:
            return []

        updates: list[dict[str, object]] = []
        checked = 0
        for bookmark in bookmarks_raw:
            if checked >= max(1, int(max_albums)):
                break
            if not isinstance(bookmark, dict):
                continue
            url = self._normalize_share_url(str(bookmark.get("url", "")))
            if not url:
                continue

            checked += 1
            try:
                resolved_url, album_title, current_keys = self._album_key_set_for_url(
                    url
                )
            except Exception as error:
                self._debug(f"bookmark check skipped url={url} reason={error}")
                continue

            album_dir = self._album_dir(resolved_url)
            manifest = self._load_manifest(album_dir)
            items_raw = manifest.get("items")
            previous_items = items_raw if isinstance(items_raw, dict) else {}
            previous_keys = set(previous_items.keys())

            new_count = len(current_keys - previous_keys)
            removed_count = len(previous_keys - current_keys)
            if new_count <= 0 and removed_count <= 0:
                continue

            display_name = _sanitize_text(str(bookmark.get("name", ""))) or album_title
            updates.append(
                {
                    "name": display_name,
                    "url": url,
                    "resolved_url": resolved_url,
                    "title": album_title,
                    "new_count": int(new_count),
                    "removed_count": int(removed_count),
                    "total_count": int(len(current_keys)),
                }
            )

        if updates:
            self._info(f"bookmark check found updates for {len(updates)} album(s)")
        else:
            self._debug("bookmark check found no updates")
        return updates

    def _album_dir(self, context_id: str) -> Path:
        digest = hashlib.sha256(context_id.encode("utf-8")).hexdigest()[:20]
        return self.cache_root() / digest

    def _manifest_path(self, album_dir: Path) -> Path:
        return album_dir / "manifest.json"

    def _load_manifest(self, album_dir: Path) -> dict[str, object]:
        manifest_path = self._manifest_path(album_dir)
        if not manifest_path.exists():
            return {"version": 1, "items": {}, "title": ""}
        try:
            with manifest_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                payload = {"version": 1, "items": {}, "title": ""} | data
                if not isinstance(payload.get("items"), dict):
                    payload["items"] = {}
                return payload
        except (OSError, json.JSONDecodeError):
            pass
        return {"version": 1, "items": {}, "title": ""}

    def _save_manifest(self, album_dir: Path, payload: dict[str, object]) -> None:
        manifest_path = self._manifest_path(album_dir)
        try:
            album_dir.mkdir(parents=True, exist_ok=True)
            tmp = manifest_path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            tmp.replace(manifest_path)
        except OSError:
            return

    def _download_media(self, base_url: str) -> _DownloadedMedia | None:
        variants = [("download", base_url + "=d"), ("base", base_url)]
        skipped_download_content_type = ""
        for variant_name, candidate in variants:
            try:
                response = requests.get(candidate, timeout=45)
            except requests.RequestException:
                continue
            if not response.ok or not response.content:
                continue
            content_type = str(response.headers.get("content-type") or "").split(
                ";", 1
            )[0]
            if not content_type.lower().startswith("image/"):
                continue
            if variant_name == "download" and not _is_displayable_content_type(
                content_type
            ):
                skipped_download_content_type = content_type
                self._debug(
                    "download variant skipped (unsupported original) "
                    f"content_type={content_type}"
                )
                continue
            if variant_name == "base" and skipped_download_content_type:
                self._debug(
                    "using base image fallback after unsupported original "
                    f"download_content_type={skipped_download_content_type} "
                    f"base_content_type={content_type}"
                )
            return _DownloadedMedia(
                payload=response.content,
                content_type=content_type,
                variant=variant_name,
            )
        return None

    def _extract_file_metadata(
        self,
        file_path: Path,
    ) -> tuple[datetime | None, float | None, float | None]:
        captured_at: datetime | None = None
        latitude: float | None = None
        longitude: float | None = None
        try:
            image = Image.open(file_path)
            exif = image.getexif()
            if exif:
                captured_at = _parse_exif_datetime(exif.get(36867) or exif.get(306))
                gps_ifd = exif.get_ifd(IFD.GPSInfo)
                if isinstance(gps_ifd, dict):
                    latitude = _gps_decimal(gps_ifd.get(1), gps_ifd.get(2))
                    longitude = _gps_decimal(gps_ifd.get(3), gps_ifd.get(4))
                    if latitude is not None and not (-90.0 <= latitude <= 90.0):
                        latitude = None
                    if longitude is not None and not (-180.0 <= longitude <= 180.0):
                        longitude = None
        except Exception:
            return (None, None, None)
        return (captured_at, latitude, longitude)

    def _update_recent_state(
        self,
        state: dict[str, object],
        url: str,
        context_id: str,
        title: str,
        asset_count: int,
        new_count: int,
    ) -> None:
        self._set_context_hint(state, url, context_id)
        now = datetime.now().isoformat(timespec="seconds")
        existing_bookmarks = self._bookmarks_for_active_account(state)
        for bookmark in existing_bookmarks:
            if _sanitize_text(str(bookmark.get("url", ""))) == url:
                bookmark["last_loaded_at"] = now
                bookmark["last_context_id"] = context_id
                bookmark["last_asset_count"] = int(asset_count)
                bookmark["last_new_count"] = int(new_count)
        self._set_bookmarks_for_active_account(state, existing_bookmarks)

        recent_entries = self._recent_for_active_account(state)
        recent_entries = [
            item
            for item in recent_entries
            if isinstance(item, dict)
            and _sanitize_text(str(item.get("url", ""))) != url
        ]
        recent_entries.insert(
            0,
            {
                "url": url,
                "title": title,
                "context_id": context_id,
                "loaded_at": now,
                "asset_count": int(asset_count),
                "new_count": int(new_count),
            },
        )
        self._set_recent_for_active_account(state, recent_entries[:30])

    def _add_bookmark(self, state: dict[str, object], name: str, url: str) -> None:
        bookmarks = self._bookmarks_for_active_account(state)
        normalized_url = _sanitize_text(url)
        cleaned_name = _sanitize_text(name) or normalized_url

        for bookmark in bookmarks:
            if not isinstance(bookmark, dict):
                continue
            if _sanitize_text(str(bookmark.get("url", ""))) == normalized_url:
                bookmark["name"] = cleaned_name
                self._set_bookmarks_for_active_account(state, bookmarks)
                return

        bookmarks.append(
            {
                "name": cleaned_name,
                "url": normalized_url,
                "added_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self._set_bookmarks_for_active_account(state, bookmarks)

    def choose_album_url_via_ui(
        self, parent: QWidget | None
    ) -> tuple[str, bool] | None:
        state = self.load_state()
        bookmarks = self._bookmarks_for_picker(state)
        recent_entries = self._recent_for_picker(state)

        def as_non_negative_int(value: object) -> int:
            if isinstance(value, bool):
                return 0
            try:
                return max(0, int(value))
            except (TypeError, ValueError):
                return 0

        def sort_timestamp(value: object) -> float:
            if not isinstance(value, str):
                return 0.0
            parsed = _parse_iso_datetime(value)
            if parsed is None:
                return 0.0
            try:
                return float(parsed.timestamp())
            except Exception:
                return 0.0

        recent_by_url: dict[str, dict[str, object]] = {}
        for recent in recent_entries:
            if not isinstance(recent, dict):
                continue
            recent_url = self._normalize_share_url(str(recent.get("url", "")))
            if recent_url and recent_url not in recent_by_url:
                recent_by_url[recent_url] = recent

        bookmark_rows: list[tuple[float, str, str]] = []
        seen_bookmarks: set[str] = set()
        for bookmark in bookmarks:
            if not isinstance(bookmark, dict):
                continue
            url = self._normalize_share_url(str(bookmark.get("url", "")))
            if not url or url in seen_bookmarks:
                continue
            seen_bookmarks.add(url)

            fallback_recent = recent_by_url.get(url, {})
            name = _sanitize_text(str(bookmark.get("name", "")))
            title = _sanitize_text(str(fallback_recent.get("title", "")))
            label = name or title or url

            new_count = as_non_negative_int(bookmark.get("last_new_count"))
            if new_count <= 0:
                new_count = as_non_negative_int(fallback_recent.get("new_count"))
            asset_count = as_non_negative_int(bookmark.get("last_asset_count"))
            if asset_count <= 0:
                asset_count = as_non_negative_int(fallback_recent.get("asset_count"))

            details: list[str] = []
            if new_count > 0:
                details.append(f"new {new_count}")
            if asset_count > 0:
                details.append(f"{asset_count} photos")

            loaded_at_raw = str(
                bookmark.get("last_loaded_at") or fallback_recent.get("loaded_at") or ""
            )
            loaded_at = _format_relative_loaded_at(loaded_at_raw)
            if loaded_at:
                details.append(f"updated {loaded_at}")

            label_text = label
            if details:
                label_text = f"{label} ({', '.join(details)})"
            bookmark_rows.append((sort_timestamp(loaded_at_raw), label_text, url))

        bookmark_rows.sort(key=lambda row: row[0], reverse=True)
        bookmark_items: list[tuple[str, str]] = [
            (label_text, url) for _sort_key, label_text, url in bookmark_rows
        ]

        recent_rows: list[tuple[float, str, str]] = []
        seen_recent: set[str] = set()
        for recent in recent_entries:
            if not isinstance(recent, dict):
                continue
            url = self._normalize_share_url(str(recent.get("url", "")))
            if not url or url in seen_recent:
                continue
            seen_recent.add(url)

            title = _sanitize_text(str(recent.get("title", ""))) or url
            new_count = as_non_negative_int(recent.get("new_count"))
            asset_count = as_non_negative_int(recent.get("asset_count"))
            loaded_at_raw = str(recent.get("loaded_at", ""))
            loaded_at = _format_relative_loaded_at(loaded_at_raw)

            details: list[str] = []
            if new_count > 0:
                details.append(f"new {new_count}")
            if asset_count > 0:
                details.append(f"{asset_count} photos")
            if loaded_at:
                details.append(f"updated {loaded_at}")

            label_text = title
            if details:
                label_text = f"{title} ({', '.join(details)})"
            recent_rows.append((sort_timestamp(loaded_at_raw), label_text, url))

        recent_rows.sort(key=lambda row: row[0], reverse=True)
        recent_items: list[tuple[str, str]] = [
            (label_text, url) for _sort_key, label_text, url in recent_rows
        ]

        entry_sets: dict[str, list[tuple[str, str]]] = {
            "Bookmarks": bookmark_items,
            "Recent Entries": recent_items,
        }

        dialog = QDialog(parent)
        dialog.setWindowTitle("Entries / Bookmarks")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Entries for:", dialog))

        entry_type_combo = QComboBox(dialog)
        entry_type_combo.addItems(["Bookmarks", "Recent Entries"])
        if not bookmark_items and recent_items:
            entry_type_combo.setCurrentText("Recent Entries")
        layout.addWidget(entry_type_combo)

        layout.addWidget(QLabel("Paste album URL or choose a saved entry", dialog))

        url_combo = QComboBox(dialog)
        url_combo.setEditable(True)
        url_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        url_combo.setMinimumWidth(560)
        layout.addWidget(url_combo)

        def repopulate_url_entries() -> None:
            selected_type = str(entry_type_combo.currentText() or "Bookmarks")
            entries = entry_sets.get(selected_type, [])
            current_text = str(url_combo.currentText() or "")
            url_combo.blockSignals(True)
            url_combo.clear()
            for display_label, entry_url in entries:
                url_combo.addItem(display_label, entry_url)
            if current_text:
                url_combo.setEditText(current_text)
            elif entries:
                url_combo.setCurrentIndex(0)
            url_combo.blockSignals(False)

        repopulate_url_entries()
        entry_type_combo.currentTextChanged.connect(
            lambda _value: repopulate_url_entries()
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        selected_data = str(url_combo.currentData() or "").strip()
        url = selected_data or str(url_combo.currentText() or "")
        normalized_url = self._normalize_share_url(url)
        if not normalized_url:
            QMessageBox.warning(parent, "Google Photos Album URL", "Album URL is empty")
            return None

        if (
            "photos.app.goo.gl" not in normalized_url
            and "photos.google.com" not in normalized_url
        ):
            QMessageBox.warning(
                parent,
                "Google Photos Album URL",
                "URL does not look like a Google Photos shared album link.",
            )
            return None

        bookmark_urls = {entry_url for _label, entry_url in bookmark_items}
        loaded_from_bookmark = normalized_url in bookmark_urls
        return (normalized_url, loaded_from_bookmark)

    def maybe_save_bookmark_via_ui(
        self,
        parent: QWidget | None,
        input_url: str,
        result: SourceLoadResult,
        loaded_from_bookmark: bool,
    ) -> None:
        if loaded_from_bookmark:
            return

        save_bookmark = QMessageBox.question(
            parent,
            "Save Bookmark",
            "Save this album URL as a bookmark?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if save_bookmark != QMessageBox.StandardButton.Yes:
            return

        default_name = _sanitize_text(result.context_label)[:48] or "album"
        bookmark_name, ok = QInputDialog.getText(
            parent,
            "Bookmark Name",
            "Bookmark name",
            text=default_name,
        )
        if not ok:
            return

        latest_state = self.load_state()
        self._add_bookmark(
            latest_state,
            _sanitize_text(str(bookmark_name)) or default_name,
            input_url,
        )
        self.save_state(latest_state)

    def load_via_ui(self, parent: QWidget | None = None) -> SourceLoadResult | None:
        selected = self.choose_album_url_via_ui(parent)
        if selected is None:
            return None

        normalized_url, loaded_from_bookmark = selected

        try:
            result = self._load_album(normalized_url)
        except RuntimeError as error:
            QMessageBox.warning(parent, "Google Photos Album URL", str(error))
            return None

        self.maybe_save_bookmark_via_ui(
            parent=parent,
            input_url=normalized_url,
            result=result,
            loaded_from_bookmark=loaded_from_bookmark,
        )
        return result

    def refresh(
        self,
        context_id: str,
        preferred_path: Path | None = None,
    ) -> SourceLoadResult:
        _ = preferred_path
        context = self._normalize_share_url(context_id)
        if not context:
            raise RuntimeError("Google Photos album URL is missing")
        return self._load_album(context)

    def _load_album(self, album_url: str) -> SourceLoadResult:
        self.clear_cancel()
        self._debug(f"load started url={album_url}")
        try:
            response = requests.get(album_url, allow_redirects=True, timeout=45)
        except requests.RequestException as error:
            raise RuntimeError(f"Unable to open album URL: {error}") from error

        if not response.ok:
            raise RuntimeError(
                f"Unable to open album URL (HTTP {response.status_code})"
            )

        resolved_url = self._normalize_share_url(response.url)
        html_text = response.text
        if (
            "photos.google.com" not in resolved_url
            and "photos.app.goo.gl" not in resolved_url
        ):
            raise RuntimeError("URL did not resolve to a Google Photos album")

        base_urls = self._extract_media_bases(html_text)
        if not base_urls:
            raise RuntimeError("No album media found at URL")
        web_captured_at_map = self._extract_web_captured_at_map(html_text, base_urls)
        web_location_map = self._extract_web_location_map(html_text, base_urls)
        self._info(f"sync discovered {len(base_urls)} media item(s)")

        album_title = self._extract_album_title(html_text, fallback=resolved_url)
        album_dir = self._album_dir(resolved_url)
        manifest = self._load_manifest(album_dir)
        existed_before = self._manifest_path(album_dir).exists()

        previous_items = manifest.get("items")
        if not isinstance(previous_items, dict):
            previous_items = {}

        ordered_keys = [
            hashlib.sha256(url.encode("utf-8")).hexdigest()[:24] for url in base_urls
        ]
        current_key_set = set(ordered_keys)
        previous_key_set = set(previous_items.keys())

        new_key_count = len(current_key_set - previous_key_set)
        removed_key_count = len(previous_key_set - current_key_set)

        missing_local_count = 0
        for key in ordered_keys:
            previous_entry = previous_items.get(key)
            if not isinstance(previous_entry, dict):
                continue
            file_name = _sanitize_text(str(previous_entry.get("file_name", "")))
            if not file_name:
                missing_local_count += 1
                continue
            if not (album_dir / file_name).exists():
                missing_local_count += 1

        if new_key_count == 0 and removed_key_count == 0 and missing_local_count == 0:
            self._info(
                "sync fast-path unchanged "
                f"total={len(base_urls)} new=0 removed=0 missing=0"
            )
            assets: list[SourceAsset] = []
            now_text = datetime.now().isoformat(timespec="seconds")
            for order, base_url in enumerate(base_urls, start=1):
                self._ensure_not_cancelled()
                key = hashlib.sha256(base_url.encode("utf-8")).hexdigest()[:24]
                previous_entry = previous_items.get(key)
                if not isinstance(previous_entry, dict):
                    continue

                file_name = _sanitize_text(str(previous_entry.get("file_name", "")))
                if not file_name:
                    continue
                local_path = album_dir / file_name
                if not local_path.exists():
                    continue

                captured_at = _parse_iso_datetime(previous_entry.get("captured_at"))
                if captured_at is None:
                    captured_at = web_captured_at_map.get(base_url)
                latitude = previous_entry.get("latitude")
                longitude = previous_entry.get("longitude")
                lat_value = (
                    float(latitude) if isinstance(latitude, (int, float)) else None
                )
                lon_value = (
                    float(longitude) if isinstance(longitude, (int, float)) else None
                )
                if lat_value is None or lon_value is None:
                    web_location = web_location_map.get(base_url)
                    if web_location is not None:
                        lat_value, lon_value = web_location

                source_data = {
                    "album_url": resolved_url,
                    "album_title": album_title,
                    "media_key": key,
                    "media_base_url": base_url,
                    "download_variant": str(
                        previous_entry.get("download_variant") or ""
                    ),
                    "content_type": str(previous_entry.get("content_type") or ""),
                }

                assets.append(
                    SourceAsset(
                        key=key,
                        local_path=local_path,
                        display_name=file_name,
                        source_photo_id=key,
                        captured_at=captured_at,
                        latitude=lat_value,
                        longitude=lon_value,
                        source_data=source_data,
                    )
                )

                previous_entry["order"] = order
                previous_entry["base_url"] = base_url
                previous_entry["last_seen_at"] = now_text

            manifest["version"] = 1
            manifest["album_url"] = album_url
            manifest["resolved_url"] = resolved_url
            manifest["title"] = album_title
            manifest["last_sync_at"] = now_text
            manifest["last_sync_total"] = len(base_urls)
            manifest["last_sync_new"] = 0
            manifest["last_sync_removed"] = 0
            manifest["last_sync_failed"] = 0
            manifest["items"] = previous_items
            self._save_manifest(album_dir, manifest)

            state = self.load_state()
            self._update_recent_state(
                state, album_url, resolved_url, album_title, len(assets), 0
            )
            self.save_state(state)

            if not assets:
                raise RuntimeError("No image assets could be loaded from album URL")

            context_label = f"{album_title} [{len(assets)} items, 0 new]"
            return SourceLoadResult(
                source_id=self.source_id,
                source_label=self.label,
                context_id=resolved_url,
                context_label=context_label,
                assets=assets,
                metadata_root=album_dir,
                is_new_context=not existed_before,
            )

        current_items: dict[str, object] = {}
        live_manifest_items: dict[str, object] = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in previous_items.items()
        }
        assets: list[SourceAsset] = []
        new_count = 0
        failed_count = 0
        now_text = datetime.now().isoformat(timespec="seconds")

        for order, base_url in enumerate(base_urls, start=1):
            self._ensure_not_cancelled()
            self._debug(
                "sync progress "
                f"item={order}/{len(base_urls)} new={new_count} failed={failed_count}"
            )

            key = hashlib.sha256(base_url.encode("utf-8")).hexdigest()[:24]
            previous_entry = previous_items.get(key)
            entry = previous_entry.copy() if isinstance(previous_entry, dict) else {}

            file_name = _sanitize_text(str(entry.get("file_name", "")))
            local_path = album_dir / file_name if file_name else None
            if local_path is None or not local_path.exists():
                downloaded = self._download_media(base_url)
                if downloaded is None:
                    failed_count += 1
                    self._log("WARNING", f"download failed key={key} item={order}")
                    continue
                extension = _guess_extension(
                    downloaded.content_type, downloaded.payload
                )
                file_name = f"{key}{extension}"
                local_path = album_dir / file_name
                try:
                    album_dir.mkdir(parents=True, exist_ok=True)
                    with local_path.open("wb") as handle:
                        handle.write(downloaded.payload)
                except OSError:
                    failed_count += 1
                    self._log("WARNING", f"write failed key={key} item={order}")
                    continue
                entry["file_name"] = file_name
                entry["download_variant"] = downloaded.variant
                entry["content_type"] = downloaded.content_type
                new_count += 1

            captured_at = _parse_iso_datetime(entry.get("captured_at"))
            if captured_at is None:
                captured_at = web_captured_at_map.get(base_url)
            latitude = entry.get("latitude")
            longitude = entry.get("longitude")
            lat_value = float(latitude) if isinstance(latitude, (int, float)) else None
            lon_value = (
                float(longitude) if isinstance(longitude, (int, float)) else None
            )

            if lat_value is None or lon_value is None:
                web_location = web_location_map.get(base_url)
                if web_location is not None:
                    lat_value, lon_value = web_location

            if captured_at is None or lat_value is None or lon_value is None:
                extracted_at, extracted_lat, extracted_lon = (
                    self._extract_file_metadata(local_path)
                )
                if captured_at is None and extracted_at is not None:
                    captured_at = extracted_at
                if lat_value is None and extracted_lat is not None:
                    lat_value = extracted_lat
                if lon_value is None and extracted_lon is not None:
                    lon_value = extracted_lon

            entry["base_url"] = base_url
            entry["key"] = key
            entry["order"] = order
            entry["last_seen_at"] = now_text
            if captured_at is not None:
                entry["captured_at"] = captured_at.isoformat(timespec="seconds")
            if lat_value is not None and lon_value is not None:
                entry["latitude"] = float(lat_value)
                entry["longitude"] = float(lon_value)

            current_items[key] = entry
            live_manifest_items[key] = entry

            manifest["version"] = 1
            manifest["album_url"] = album_url
            manifest["resolved_url"] = resolved_url
            manifest["title"] = album_title
            manifest["last_sync_at"] = now_text
            manifest["last_sync_total"] = len(base_urls)
            manifest["last_sync_new"] = int(new_count)
            manifest["last_sync_removed"] = int(removed_key_count)
            manifest["last_sync_failed"] = int(failed_count)
            manifest["items"] = live_manifest_items
            self._save_manifest(album_dir, manifest)

            source_data = {
                "album_url": resolved_url,
                "album_title": album_title,
                "media_key": key,
                "media_base_url": base_url,
                "download_variant": str(entry.get("download_variant") or ""),
                "content_type": str(entry.get("content_type") or ""),
            }

            display_name = file_name
            assets.append(
                SourceAsset(
                    key=key,
                    local_path=local_path,
                    display_name=display_name,
                    source_photo_id=key,
                    captured_at=captured_at,
                    latitude=lat_value,
                    longitude=lon_value,
                    source_data=source_data,
                )
            )

        manifest["version"] = 1
        manifest["album_url"] = album_url
        manifest["resolved_url"] = resolved_url
        manifest["title"] = album_title
        manifest["last_sync_at"] = now_text
        manifest["last_sync_total"] = len(base_urls)
        manifest["last_sync_new"] = int(new_count)
        manifest["last_sync_removed"] = int(removed_key_count)
        manifest["last_sync_failed"] = int(failed_count)
        manifest["items"] = current_items
        self._save_manifest(album_dir, manifest)

        state = self.load_state()
        self._update_recent_state(
            state, album_url, resolved_url, album_title, len(assets), new_count
        )
        self.save_state(state)

        if not assets:
            raise RuntimeError("No image assets could be downloaded from album URL")

        self._info(
            "sync completed "
            f"title={album_title!r} total={len(base_urls)} loaded={len(assets)} "
            f"new={new_count} failed={failed_count}"
        )

        context_label = f"{album_title} [{len(assets)} items, {new_count} new]"
        return SourceLoadResult(
            source_id=self.source_id,
            source_label=self.label,
            context_id=resolved_url,
            context_label=context_label,
            assets=assets,
            metadata_root=album_dir,
            is_new_context=not existed_before,
        )
