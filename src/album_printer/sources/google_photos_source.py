from __future__ import annotations

import inspect
import json
import os
import re
import socket
import threading
import time
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from album_printer.account_store import SubmoduleAccountStore
from album_printer.sources.types import SourceAsset, SourceLoadResult

SCOPES = [
    "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
ALBUMS_ENDPOINT = "https://photoslibrary.googleapis.com/v1/albums"
SHARED_ALBUMS_ENDPOINT = "https://photoslibrary.googleapis.com/v1/sharedAlbums"
MEDIA_SEARCH_ENDPOINT = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
PICKER_SESSIONS_ENDPOINT = "https://photospicker.googleapis.com/v1/sessions"
PICKER_MEDIA_ITEMS_ENDPOINT = "https://photospicker.googleapis.com/v1/mediaItems"

VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".ts",
    ".webm",
    ".wmv",
}


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "photo"


def _parse_iso_datetime(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _as_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_location(item: dict[str, Any]) -> tuple[float, float] | None:
    media_metadata = item.get("mediaMetadata")
    if isinstance(media_metadata, dict):
        location = media_metadata.get("location")
        if isinstance(location, dict):
            latitude = _as_float(location.get("latitude"))
            longitude = _as_float(location.get("longitude"))
            if latitude is not None and longitude is not None:
                if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
                    return latitude, longitude

    geo_data = item.get("geoData")
    if isinstance(geo_data, dict):
        latitude = _as_float(geo_data.get("latitude"))
        longitude = _as_float(geo_data.get("longitude"))
        if latitude is not None and longitude is not None:
            if -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0:
                return latitude, longitude
    return None


def _is_picker_image_item(item: dict[str, Any]) -> bool:
    try:
        media_file = item.get("mediaFile")
        media_file_data = media_file if isinstance(media_file, dict) else {}

        mime_type = (
            str(media_file_data.get("mimeType") or item.get("mimeType") or "")
            .strip()
            .lower()
        )
        if mime_type:
            return mime_type.startswith("image/")

        media_type = (
            str(media_file_data.get("mediaType") or item.get("mediaType") or "")
            .strip()
            .lower()
        )
        if media_type:
            if media_type in {"photo", "image"}:
                return True
            if media_type in {"video", "movie"}:
                return False

        filename = (
            str(media_file_data.get("filename") or item.get("filename") or "")
            .strip()
            .lower()
        )
        if filename:
            dot_index = filename.rfind(".")
            suffix = filename[dot_index:] if dot_index > 0 else ""
            if suffix in VIDEO_EXTENSIONS:
                return False
    except Exception:
        return False

    return False


class GooglePhotosSource:
    source_id = "google-photos"
    label = "Google Photos Photo Picker"
    help_text = (
        "Uses Google Photos Photo Picker API.\n"
        "You pick items from your Google Photos account and the app downloads them to local cache.\n"
        "Fast and convenient, but some items may miss location metadata depending on Google output."
    )

    def __init__(
        self,
        app_name: str = "album-print-flow",
        debug_logger: Callable[[str, str], None] | None = None,
    ) -> None:
        self.app_name = app_name
        self.debug_logger = debug_logger
        self.context_store = SubmoduleAccountStore(
            app_name,
            "google_contexts.json",
            defaults={"accounts": {}, "last_account_id": "", "albums": {}},
        )

    def _log(self, level: str, message: str) -> None:
        logger = self.debug_logger
        if logger is None:
            return
        try:
            logger(level, f"GOOGLE {message}")
        except Exception:
            return

    def _debug(self, message: str) -> None:
        self._log("DEBUG", message)

    def _info(self, message: str) -> None:
        self._log("INFO", message)

    def _find_free_local_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            return int(sock.getsockname()[1])

    def _signal_oauth_cancel(self, port: int) -> None:
        cancel_urls = [
            f"http://127.0.0.1:{port}/?error=access_denied",
            f"http://localhost:{port}/?error=access_denied",
        ]
        for url in cancel_urls:
            try:
                urllib_request.urlopen(url, timeout=0.8).read(32)
                return
            except Exception:
                continue

    def config_root(self) -> Path:
        return Path.home() / ".config" / self.app_name

    def cache_root(self) -> Path:
        return Path.home() / ".cache" / self.app_name / "google-photos"

    def clear_media_cache(self, *, keep_metadata: bool = True) -> dict[str, int]:
        root = self.cache_root()
        if not root.exists():
            return {
                "accounts": 0,
                "deleted_files": 0,
                "kept_metadata": 0,
                "errors": 0,
            }

        deleted_files = 0
        kept_metadata = 0
        errors = 0
        touched_accounts: set[str] = set()

        for account_dir in root.iterdir():
            if not account_dir.is_dir():
                continue

            media_cache_dir = account_dir / "media_items"
            if not media_cache_dir.exists() or not media_cache_dir.is_dir():
                continue

            touched_accounts.add(account_dir.name)

            for file_path in media_cache_dir.iterdir():
                if not file_path.is_file():
                    continue

                if keep_metadata and file_path.suffix.lower() == ".json":
                    kept_metadata += 1
                    continue

                try:
                    file_path.unlink()
                    deleted_files += 1
                except OSError:
                    errors += 1

            if not keep_metadata:
                try:
                    media_cache_dir.rmdir()
                except OSError:
                    pass

        self._info(
            "Cleared Google media cache: "
            f"accounts={len(touched_accounts)} deleted_files={deleted_files} "
            f"kept_metadata={kept_metadata} errors={errors}"
        )

        return {
            "accounts": len(touched_accounts),
            "deleted_files": deleted_files,
            "kept_metadata": kept_metadata,
            "errors": errors,
        }

    def account_token_path(self, account_id: str) -> Path:
        safe_account = re.sub(r"[^A-Za-z0-9._-]+", "_", account_id.strip())
        safe_account = safe_account.strip("._") or "default"
        return self.config_root() / f"google_token_{safe_account}.json"

    def token_service_name(self) -> str:
        return f"{self.app_name}.google-photos"

    def token_account_name_for(self, account_id: str) -> str:
        return f"oauth-token:{account_id}"

    def oauth_client_path(self) -> Path:
        candidates = self.oauth_client_path_candidates()
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def bundled_oauth_client_path(self) -> Path:
        package_root = Path(__file__).resolve().parents[1]
        return package_root / "oauth" / "google_client_secret.json"

    def oauth_client_path_candidates(self) -> list[Path]:
        explicit = os.getenv("ALBUM_PRINTER_GOOGLE_CLIENT_SECRET_FILE", "").strip()
        if explicit:
            return [Path(explicit)]

        return [
            self.config_root() / "google_client_secret.json",
            self.bundled_oauth_client_path(),
        ]

    def contexts_path(self) -> Path:
        return self.context_store.state_path()

    def load_contexts(self) -> dict[str, object]:
        data = self.context_store.load_state()
        accounts = data.get("accounts")
        if not isinstance(accounts, dict):
            data["accounts"] = {}
        albums = data.get("albums")
        if not isinstance(albums, dict):
            data["albums"] = {}
        if not isinstance(data.get("last_account_id"), str):
            data["last_account_id"] = ""
        return data

    def _context_key(self, account_id: str, album_id: str) -> str:
        return f"{account_id}::{album_id}"

    def _parse_context_id(self, context_id: str) -> tuple[str, str]:
        text = context_id.strip()
        if "::" not in text:
            return "", ""
        account_id, album_id = text.split("::", 1)
        return account_id.strip(), album_id.strip()

    def _account_label(self, account_id: str, account_info: dict[str, object]) -> str:
        display_name = str(account_info.get("display_name", "")).strip()
        email = str(account_info.get("email", "")).strip()
        if display_name and email:
            return f"{display_name} ({email})"
        if email:
            return email
        if display_name:
            return display_name
        return account_id

    def _delete_stored_account_token(self, account_id: str) -> None:
        try:
            import keyring

            try:
                keyring.delete_password(
                    self.token_service_name(),
                    self.token_account_name_for(account_id),
                )
            except Exception:
                pass
        except Exception:
            pass

        token_path = self.account_token_path(account_id)
        try:
            if token_path.exists():
                token_path.unlink()
        except OSError:
            pass

    def _fetch_google_account_identity(self, session: Any) -> tuple[str, str, str]:
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo"
        response = session.get(userinfo_endpoint, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Invalid user info response")

        account_id = str(payload.get("sub", "")).strip()
        email = str(payload.get("email", "")).strip()
        display_name = str(payload.get("name", "")).strip()
        if not account_id:
            raise RuntimeError("Could not determine account id from Google user info")
        return account_id, email, display_name

    def _format_google_api_error(self, error: Exception, *, operation: str) -> str:
        response = getattr(error, "response", None)
        status_code = getattr(response, "status_code", None)
        self._debug(
            f"API error during {operation}: status={status_code or '-'} raw={error}"
        )

        api_message = ""
        if response is not None:
            try:
                payload = response.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                error_payload = payload.get("error")
                if isinstance(error_payload, dict):
                    api_message = str(error_payload.get("message", "")).strip()

        detail = api_message or str(error)

        if status_code == 403:
            guidance = (
                "Google Photos request was rejected (403 Forbidden).\n\n"
                "Check Google Cloud setup for the same OAuth project:\n"
                "1) APIs & Services -> Library -> enable Google Photos Library API\n"
                "2) OAuth consent screen -> add this Google account as a Test user\n"
                "3) Sign in with the account that is allowed for that project\n"
                "4) Retry File -> Test Google Setup\n\n"
                f"Details: {detail}"
            )
            return guidance

        return f"Failed to {operation}: {detail}"

    def _pick_account_or_action(
        self,
        parent: QWidget | None,
        contexts: dict[str, object],
    ) -> tuple[str, str] | None:
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict) or not accounts:
            return ("action", "add")

        labels: list[str] = []
        by_label: dict[str, str] = {}
        last_account_id = str(contexts.get("last_account_id", "")).strip()
        start_index = 0
        for index, (account_id, raw_info) in enumerate(accounts.items()):
            info = raw_info if isinstance(raw_info, dict) else {}
            label = self._account_label(account_id, info)
            if label in by_label:
                label = f"{label} [{account_id[:8]}]"
            labels.append(label)
            by_label[label] = account_id
            if account_id == last_account_id:
                start_index = index

        entries = [
            *labels,
            "──────────",
            "Add account…",
            "Manage accounts…",
        ]
        selected_index = min(start_index, max(0, len(entries) - 1))

        while True:
            choice, ok = QInputDialog.getItem(
                parent,
                "Google Photos",
                "Select account",
                entries,
                selected_index,
                False,
            )
            if not ok:
                self._debug("Account/action picker cancelled")
                return None

            if choice in by_label:
                self._debug(f"Selected existing account id={by_label[choice]}")
                return ("account", by_label[choice])
            if choice == "Add account…":
                self._debug("Selected action: add account")
                return ("action", "add")
            if choice == "Manage accounts…":
                self._debug("Selected action: manage accounts")
                return ("action", "manage")

    def _pick_existing_account(
        self,
        parent: QWidget | None,
        contexts: dict[str, object],
        *,
        title: str,
        prompt: str,
    ) -> str | None:
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict) or not accounts:
            return None

        labels: list[str] = []
        by_label: dict[str, str] = {}
        last_account_id = str(contexts.get("last_account_id", "")).strip()
        start_index = 0
        for index, (account_id, raw_info) in enumerate(accounts.items()):
            info = raw_info if isinstance(raw_info, dict) else {}
            label = self._account_label(account_id, info)
            if label in by_label:
                label = f"{label} [{account_id[:8]}]"
            labels.append(label)
            by_label[label] = account_id
            if account_id == last_account_id:
                start_index = index

        choice, ok = QInputDialog.getItem(
            parent,
            title,
            prompt,
            labels,
            start_index,
            False,
        )
        if not ok:
            return None
        return by_label.get(choice)

    def _remove_account(self, contexts: dict[str, object], account_id: str) -> None:
        self._debug(f"Removing account id={account_id}")
        accounts = contexts.get("accounts")
        if isinstance(accounts, dict):
            accounts.pop(account_id, None)

        albums = contexts.get("albums")
        if isinstance(albums, dict):
            prefix = f"{account_id}::"
            for key in list(albums.keys()):
                if key.startswith(prefix):
                    albums.pop(key, None)

        last_account_id = str(contexts.get("last_account_id", "")).strip()
        if last_account_id == account_id:
            contexts["last_account_id"] = ""

        self._delete_stored_account_token(account_id)
        self.save_contexts(contexts)

    def _account_choices(
        self,
        contexts: dict[str, object],
    ) -> tuple[list[tuple[str, str]], str]:
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict) or not accounts:
            return [], ""

        choices: list[tuple[str, str]] = []
        labels_seen: set[str] = set()
        last_account_id = str(contexts.get("last_account_id", "")).strip()
        default_account_id = ""

        for account_id, raw_info in accounts.items():
            info = raw_info if isinstance(raw_info, dict) else {}
            label = self._account_label(account_id, info)
            if label in labels_seen:
                label = f"{label} [{account_id[:8]}]"
            labels_seen.add(label)
            choices.append((label, account_id))
            if account_id == last_account_id:
                default_account_id = account_id

        return choices, default_account_id

    def list_accounts(self) -> list[dict[str, str]]:
        contexts = self.load_contexts()
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict):
            return []

        rows: list[dict[str, str]] = []
        for account_id, raw_info in accounts.items():
            info = raw_info if isinstance(raw_info, dict) else {}
            email = str(info.get("email", "")).strip()
            display_name = str(info.get("display_name", "")).strip()
            label = self._account_label(account_id, info)
            rows.append(
                {
                    "source_id": self.source_id,
                    "source_label": self.label,
                    "account_id": str(account_id),
                    "email": email,
                    "display_name": display_name,
                    "label": label,
                }
            )

        rows.sort(key=lambda row: row.get("label", "").lower())
        return rows

    def add_account_interactive(self, parent: QWidget | None = None) -> bool:
        contexts = self.load_contexts()
        added = self._add_account_via_ui(parent, contexts)
        return added is not None

    def delete_account(self, account_id: str) -> bool:
        account_id_text = str(account_id or "").strip()
        if not account_id_text:
            return False

        contexts = self.load_contexts()
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict) or account_id_text not in accounts:
            return False

        self._remove_account(contexts, account_id_text)
        return True

    def refresh_account_oauth(
        self,
        parent: QWidget | None,
        account_id: str,
    ) -> bool:
        account_id_text = str(account_id or "").strip()
        if not account_id_text:
            return False

        contexts = self.load_contexts()
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict) or account_id_text not in accounts:
            return False

        session = self._authorized_session(
            parent,
            account_id_text,
            force_interactive=True,
        )
        if session is None:
            return False

        try:
            refreshed_account_id, email, display_name = (
                self._fetch_google_account_identity(session)
            )
        except Exception:
            refreshed_account_id = account_id_text
            email = ""
            display_name = ""

        final_account_id = refreshed_account_id or account_id_text
        creds = getattr(session, "credentials", None)
        if creds is not None:
            self._save_credentials(creds, final_account_id)

        if final_account_id != account_id_text:
            self._remove_account(contexts, account_id_text)
            accounts = contexts.get("accounts")
            if not isinstance(accounts, dict):
                accounts = {}
                contexts["accounts"] = accounts

        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict):
            accounts = {}
            contexts["accounts"] = accounts

        existing = accounts.get(final_account_id)
        existing_info = existing if isinstance(existing, dict) else {}
        accounts[final_account_id] = {
            "email": email or str(existing_info.get("email", "")).strip(),
            "display_name": (
                display_name
                or str(existing_info.get("display_name", "")).strip()
                or email
                or final_account_id
            ),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        contexts["last_account_id"] = final_account_id
        self.save_contexts(contexts)
        return True

    def save_contexts(self, contexts: dict[str, object]) -> None:
        self.context_store.save_state(contexts)

    def _credentials_from_token(self, account_id: str) -> object | None:
        from google.oauth2.credentials import Credentials

        token_json = self._load_token_json_from_secret_manager(account_id)
        if token_json:
            try:
                token_payload = json.loads(token_json)
                if isinstance(token_payload, dict):
                    return Credentials.from_authorized_user_info(token_payload, SCOPES)
            except (ValueError, TypeError):
                pass

        token_path = self.account_token_path(account_id)
        if not token_path.exists():
            return None
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            return creds
        except (OSError, ValueError):
            return None

    def _save_credentials(self, credentials: object, account_id: str) -> None:
        token_json = str(credentials.to_json())
        if self._save_token_json_to_secret_manager(token_json, account_id):
            return

        token_path = self.account_token_path(account_id)
        try:
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with token_path.open("w", encoding="utf-8") as handle:
                handle.write(token_json)
        except OSError:
            return

    def _load_token_json_from_secret_manager(self, account_id: str) -> str:
        try:
            import keyring
        except Exception:
            return ""

        try:
            value = keyring.get_password(
                self.token_service_name(),
                self.token_account_name_for(account_id),
            )
        except Exception:
            return ""
        return str(value or "")

    def _save_token_json_to_secret_manager(
        self, token_json: str, account_id: str
    ) -> bool:
        if not token_json.strip():
            return False

        try:
            import keyring
        except Exception:
            return False

        try:
            keyring.set_password(
                self.token_service_name(),
                self.token_account_name_for(account_id),
                token_json,
            )
            return True
        except Exception:
            return False

    def _is_valid_oauth_client_json(self, payload: object) -> bool:
        if not isinstance(payload, dict):
            return False
        installed = payload.get("installed")
        if not isinstance(installed, dict):
            return False

        required_keys = {
            "client_id",
            "client_secret",
            "auth_uri",
            "token_uri",
            "redirect_uris",
        }
        if not required_keys.issubset(installed.keys()):
            return False

        redirect_uris = installed.get("redirect_uris")
        if not isinstance(redirect_uris, list) or not redirect_uris:
            return False
        return True

    def _save_oauth_client_payload(self, payload: dict[str, object]) -> Path:
        target_path = self.config_root() / "google_client_secret.json"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return target_path

    def _import_oauth_client_json_interactive(
        self, parent: QWidget | None
    ) -> Path | None:
        message = QMessageBox(parent)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Google Photos setup")
        message.setText("Google OAuth client file not found.")
        message.setInformativeText(
            "Set up OAuth Desktop credentials in Google Cloud:\n"
            "1) Google Cloud Console -> APIs & Services -> OAuth consent screen\n"
            "2) Create consent screen and add your test user\n"
            "3) APIs & Services -> Credentials -> Create Credentials -> OAuth client ID\n"
            "4) Application type: Desktop app\n"
            "5) Download the JSON\n\n"
            "Then import it here (recommended path):\n"
            f"{self.config_root() / 'google_client_secret.json'}"
        )

        paste_button = message.addButton(
            "Paste JSON", QMessageBox.ButtonRole.ActionRole
        )
        select_button = message.addButton(
            "Select JSON file...", QMessageBox.ButtonRole.ActionRole
        )
        cancel_button = message.addButton(QMessageBox.StandardButton.Cancel)
        message.setDefaultButton(select_button)
        message.exec()

        clicked = message.clickedButton()
        if clicked is cancel_button:
            return None

        if clicked is paste_button:
            raw_text, ok = QInputDialog.getMultiLineText(
                parent,
                "Paste OAuth Desktop JSON",
                "Paste the complete JSON downloaded from Google Cloud:",
                "",
            )
            if not ok or not raw_text.strip():
                return None

            try:
                payload = json.loads(raw_text)
            except json.JSONDecodeError:
                QMessageBox.warning(
                    parent,
                    "Google Photos",
                    "Invalid JSON. Please paste the full OAuth Desktop JSON.",
                )
                return None

            if not self._is_valid_oauth_client_json(payload):
                QMessageBox.warning(
                    parent,
                    "Google Photos",
                    "The JSON is not a valid OAuth Desktop client file.",
                )
                return None

            try:
                saved = self._save_oauth_client_payload(payload)
                QMessageBox.information(
                    parent,
                    "Google Photos",
                    f"Saved OAuth client file to:\n{saved}",
                )
                return saved
            except OSError as error:
                QMessageBox.critical(
                    parent,
                    "Google Photos",
                    f"Failed to save OAuth client JSON: {error}",
                )
                return None

        if clicked is select_button:
            selected, _ = QFileDialog.getOpenFileName(
                parent,
                "Select Google OAuth client JSON",
                str(Path.home()),
                "JSON files (*.json);;All files (*)",
            )
            if not selected:
                return None

            try:
                raw_text = Path(selected).read_text(encoding="utf-8")
                payload = json.loads(raw_text)
            except (OSError, json.JSONDecodeError) as error:
                QMessageBox.warning(
                    parent,
                    "Google Photos",
                    f"Could not read JSON file: {error}",
                )
                return None

            if not self._is_valid_oauth_client_json(payload):
                QMessageBox.warning(
                    parent,
                    "Google Photos",
                    "Selected file is not a valid OAuth Desktop client JSON.",
                )
                return None

            try:
                saved = self._save_oauth_client_payload(payload)
                QMessageBox.information(
                    parent,
                    "Google Photos",
                    f"Saved OAuth client file to:\n{saved}",
                )
                return saved
            except OSError as error:
                QMessageBox.critical(
                    parent,
                    "Google Photos",
                    f"Failed to save OAuth client JSON: {error}",
                )
                return None

        return None

    def _ensure_oauth_client_available(self, parent: QWidget | None) -> bool:
        client_path = self.oauth_client_path()
        if client_path.exists():
            return True
        imported_path = self._import_oauth_client_json_interactive(parent)
        return imported_path is not None

    def _add_account_via_ui(
        self,
        parent: QWidget | None,
        contexts: dict[str, object],
    ) -> tuple[str, Any] | None:
        self._debug("Starting add-account flow")
        if not self._ensure_oauth_client_available(parent):
            self._debug("Add-account aborted: OAuth client JSON unavailable")
            return None

        provisional_account_id = "new-account"
        session = self._authorized_session(
            parent,
            provisional_account_id,
            force_interactive=True,
        )
        if session is None:
            self._debug("Add-account aborted: authentication returned no session")
            return None

        try:
            account_id, email, display_name = self._fetch_google_account_identity(
                session
            )
        except Exception as error:
            QMessageBox.critical(
                parent,
                "Google Photos",
                f"Could not determine Google account identity: {error}",
            )
            return None

        creds = getattr(session, "credentials", None)
        if creds is None:
            QMessageBox.critical(
                parent,
                "Google Photos",
                "Could not access OAuth credentials for the authenticated account.",
            )
            return None

        self._save_credentials(creds, account_id)
        self._delete_stored_account_token(provisional_account_id)

        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict):
            accounts = {}
            contexts["accounts"] = accounts

        accounts[account_id] = {
            "email": email,
            "display_name": display_name or email or account_id,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        contexts["last_account_id"] = account_id
        self.save_contexts(contexts)
        self._info(
            f"Added account id={account_id} email={email or '-'} display={display_name or '-'}"
        )
        return account_id, session

    def _manage_accounts_via_ui(
        self,
        parent: QWidget | None,
        contexts: dict[str, object],
    ) -> None:
        self._debug("Opening manage-accounts window")
        dialog = QDialog(parent)
        dialog.setWindowTitle("Manage Google Accounts")
        dialog.setModal(True)
        dialog.resize(560, 360)

        root = QVBoxLayout(dialog)
        root.addWidget(
            QLabel(
                "Select an account and click Delete. "
                "This removes local token cache for that account.",
                dialog,
            )
        )

        account_list = QListWidget(dialog)
        root.addWidget(account_list, 1)

        button_row = QHBoxLayout()
        delete_button = QPushButton("Delete Selected", dialog)
        button_row.addWidget(delete_button)
        button_row.addStretch(1)
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        close_buttons.rejected.connect(dialog.reject)
        button_row.addWidget(close_buttons)
        root.addLayout(button_row)

        def repopulate() -> None:
            account_list.clear()
            choices, default_account_id = self._account_choices(contexts)
            default_row = 0
            for row, (label, account_id) in enumerate(choices):
                item = QListWidgetItem(label)
                item.setData(int(Qt.ItemDataRole.UserRole), account_id)
                account_list.addItem(item)
                if account_id == default_account_id:
                    default_row = row
            if account_list.count() > 0:
                account_list.setCurrentRow(default_row)
            delete_button.setEnabled(account_list.count() > 0)

        def delete_selected() -> None:
            item = account_list.currentItem()
            if item is None:
                return
            account_id = str(item.data(int(Qt.ItemDataRole.UserRole)) or "").strip()
            if not account_id:
                return

            reply = QMessageBox.question(
                dialog,
                "Manage Google Accounts",
                "Delete this Google account from Album Print Flow?\n"
                "This removes local token cache for this account.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            self._remove_account(contexts, account_id)
            self._info(f"Deleted account id={account_id}")
            repopulate()

            if account_list.count() == 0:
                QMessageBox.information(
                    dialog, "Google Photos", "No accounts remaining."
                )

        delete_button.clicked.connect(delete_selected)
        close_buttons.accepted.connect(dialog.accept)

        repopulate()
        dialog.exec()

    def _select_or_add_account(
        self,
        parent: QWidget | None,
    ) -> tuple[str, Any] | None:
        self._debug("Starting account selection flow")
        contexts = self.load_contexts()
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict):
            accounts = {}
            contexts["accounts"] = accounts

        while True:
            if not accounts:
                added = self._add_account_via_ui(parent, contexts)
                if added is None:
                    self._debug("Account selection aborted: add-account returned None")
                    return None
                return added

            choice = self._pick_account_or_action(parent, contexts)
            if choice is None:
                return None
            choice_type, value = choice

            if choice_type == "action" and value == "add":
                added = self._add_account_via_ui(parent, contexts)
                if added is not None:
                    return added
                continue

            if choice_type == "action" and value == "manage":
                self._manage_accounts_via_ui(parent, contexts)
                accounts = contexts.get("accounts")
                if not isinstance(accounts, dict):
                    accounts = {}
                    contexts["accounts"] = accounts
                continue

            if choice_type != "account":
                continue

            account_id = value

            session = self._authorized_session(parent, account_id)
            if session is None:
                self._debug(f"Session acquisition failed for account id={account_id}")
                continue

            contexts["last_account_id"] = account_id
            self.save_contexts(contexts)
            self._debug(f"Session ready for account id={account_id}")
            return account_id, session

    def test_setup_via_ui(self, parent: QWidget | None = None) -> bool:
        selected = self._select_or_add_account(parent)
        if selected is None:
            return False
        account_id, session = selected

        try:
            response = session.get(ALBUMS_ENDPOINT, params={"pageSize": 1}, timeout=30)
            response.raise_for_status()
        except Exception as error:
            message = self._format_google_api_error(
                error, operation="verify Google setup"
            )
            QMessageBox.critical(
                parent,
                "Google Photos",
                "Google setup test failed after authentication.\n\n" + message,
            )
            return False

        QMessageBox.information(
            parent,
            "Google Photos",
            "Google setup looks good.\n\n"
            f"Active account: {account_id}\n"
            "OAuth client JSON is valid, sign-in works, and Google Photos API access is reachable.",
        )
        return True

    def _authenticate(
        self,
        parent: QWidget | None,
        account_id: str,
        *,
        force_interactive: bool = False,
    ) -> object | None:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        self._debug(
            "Authenticate start: "
            f"account_id={account_id} force_interactive={force_interactive}"
        )

        creds = None if force_interactive else self._credentials_from_token(account_id)
        if creds is not None:
            if creds.valid:
                self._debug(
                    f"Using cached valid credentials for account_id={account_id}"
                )
                return creds
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self._save_credentials(creds, account_id)
                    self._debug(
                        f"Refreshed cached credentials for account_id={account_id}"
                    )
                    return creds
                except Exception:
                    self._debug(
                        f"Credential refresh failed for account_id={account_id}; "
                        "falling back to interactive login"
                    )
                    pass

        client_path = self.oauth_client_path()
        if not client_path.exists():
            imported_path = self._import_oauth_client_json_interactive(parent)
            if imported_path is None:
                return None
            client_path = imported_path

        try:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
            oauth_port = self._find_free_local_port()
            oauth_host = "localhost"
            flow.redirect_uri = f"http://{oauth_host}:{oauth_port}/"
            result: dict[str, object] = {"creds": None, "error": None}
            self._debug(
                "Starting interactive OAuth local server flow "
                f"on {oauth_host}:{oauth_port}"
            )

            def _oauth_worker() -> None:
                try:
                    run_kwargs: dict[str, object] = {
                        "host": oauth_host,
                        "port": oauth_port,
                        "authorization_prompt_message": "",
                        "open_browser": True,
                        "access_type": "offline",
                        "include_granted_scopes": "true",
                        "prompt": "consent",
                    }
                    try:
                        signature = inspect.signature(flow.run_local_server)
                        if "timeout_seconds" in signature.parameters:
                            run_kwargs["timeout_seconds"] = 300
                    except Exception:
                        pass

                    result["creds"] = flow.run_local_server(**run_kwargs)
                except Exception as worker_error:
                    result["error"] = worker_error

            worker = threading.Thread(target=_oauth_worker, daemon=True)
            worker.start()

            progress = QProgressDialog(parent)
            progress.setWindowTitle("Google Photos")
            progress.setLabelText(
                "Waiting for Google sign-in in your browser...\n"
                "Complete login and consent to continue."
            )
            progress.setCancelButtonText("Cancel")
            progress.setRange(0, 0)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()

            cancelled = False
            while worker.is_alive():
                QApplication.processEvents()
                if progress.wasCanceled():
                    cancelled = True
                    self._debug(
                        f"OAuth cancelled by user; signaling callback server on port {oauth_port}"
                    )
                    self._signal_oauth_cancel(oauth_port)
                    break
                time.sleep(0.03)

            if cancelled and worker.is_alive():
                worker.join(timeout=2.0)

            progress.close()

            if cancelled:
                self._info("Google sign-in cancelled by user")
                return None

            worker_error = result.get("error")
            if isinstance(worker_error, Exception):
                raise worker_error

            creds = result.get("creds")
            if creds is None:
                raise RuntimeError("Google sign-in did not return credentials")

            self._save_credentials(creds, account_id)
            self._debug(
                f"Interactive authentication succeeded for account_id={account_id}"
            )
            return creds
        except Exception as error:
            QMessageBox.critical(
                parent,
                "Google Photos",
                f"Google sign-in failed: {error}",
            )
            return None

    def _authorized_session(
        self,
        parent: QWidget | None,
        account_id: str,
        *,
        force_interactive: bool = False,
    ) -> object | None:
        from google.auth.transport.requests import AuthorizedSession

        credentials = self._authenticate(
            parent,
            account_id,
            force_interactive=force_interactive,
        )
        if credentials is None:
            return None
        return AuthorizedSession(credentials)

    def _parse_duration_seconds(self, value: object, default: float) -> float:
        text = str(value or "").strip().lower()
        if text.endswith("s"):
            text = text[:-1]
        try:
            parsed = float(text)
        except (TypeError, ValueError):
            return default
        if parsed <= 0:
            return default
        return parsed

    def _create_picker_session(
        self,
        session: Any,
        *,
        max_item_count: int = 2000,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "pickingConfig": {
                "maxItemCount": str(max(1, min(2000, int(max_item_count)))),
            }
        }
        response = session.post(PICKER_SESSIONS_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Invalid picker session response")

        session_id = str(data.get("id", "")).strip()
        picker_uri = str(data.get("pickerUri", "")).strip()
        if not session_id or not picker_uri:
            raise RuntimeError("Picker session response missing id/pickerUri")

        self._info(f"Picker session created: id={session_id}")
        return data

    def _delete_picker_session(self, session: Any, session_id: str) -> None:
        session_id_text = str(session_id or "").strip()
        if not session_id_text:
            return
        try:
            response = session.delete(
                f"{PICKER_SESSIONS_ENDPOINT}/{session_id_text}",
                timeout=20,
            )
            if response.status_code in {200, 204, 404}:
                self._debug(f"Picker session closed: id={session_id_text}")
            else:
                self._debug(
                    "Picker session delete returned status "
                    f"{response.status_code}: id={session_id_text}"
                )
        except Exception as error:
            self._debug(
                f"Picker session delete failed: id={session_id_text} error={error}"
            )

    def _wait_for_picker_completion(
        self,
        parent: QWidget | None,
        session: Any,
        picker_session: dict[str, Any],
    ) -> bool:
        session_id = str(picker_session.get("id", "")).strip()
        if not session_id:
            raise RuntimeError("Picker session id is missing")

        polling = picker_session.get("pollingConfig")
        polling_dict = polling if isinstance(polling, dict) else {}
        poll_interval = self._parse_duration_seconds(
            polling_dict.get("pollInterval"),
            2.0,
        )
        timeout_seconds = self._parse_duration_seconds(
            polling_dict.get("timeoutIn"),
            300.0,
        )

        progress = QProgressDialog(parent)
        progress.setWindowTitle("Google Photos Picker")
        progress.setLabelText(
            "Waiting for Google Photos selection...\n"
            "Use your browser window, search by album title if needed, then return here."
        )
        progress.setCancelButtonText("Cancel")
        progress.setRange(0, 0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        started_at = time.monotonic()
        try:
            while True:
                QApplication.processEvents()
                if progress.wasCanceled():
                    self._info("Picker selection cancelled by user")
                    self._delete_picker_session(session, session_id)
                    return False

                elapsed = time.monotonic() - started_at
                if timeout_seconds > 0 and elapsed > timeout_seconds:
                    raise RuntimeError(
                        "Picker selection timed out. Start Google Photos load again."
                    )

                response = session.get(
                    f"{PICKER_SESSIONS_ENDPOINT}/{session_id}",
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("Invalid picker status response")

                if bool(payload.get("mediaItemsSet", False)):
                    self._info(f"Picker selection completed: id={session_id}")
                    return True

                poll_cfg = payload.get("pollingConfig")
                if isinstance(poll_cfg, dict):
                    poll_interval = self._parse_duration_seconds(
                        poll_cfg.get("pollInterval"),
                        poll_interval,
                    )
                    timeout_seconds = self._parse_duration_seconds(
                        poll_cfg.get("timeoutIn"),
                        timeout_seconds,
                    )

                wait_until = time.monotonic() + max(0.2, poll_interval)
                while time.monotonic() < wait_until:
                    QApplication.processEvents()
                    if progress.wasCanceled():
                        self._info("Picker selection cancelled by user")
                        self._delete_picker_session(session, session_id)
                        return False
                    time.sleep(0.05)
        finally:
            progress.close()

    def _run_worker_with_progress(
        self,
        parent: QWidget | None,
        *,
        title: str,
        label: str,
        task: Callable[[threading.Event], object],
    ) -> object:
        result: dict[str, object] = {"value": None, "error": None}
        cancel_event = threading.Event()

        def _worker() -> None:
            try:
                result["value"] = task(cancel_event)
            except Exception as error:
                result["error"] = error
            except BaseException as error:
                result["error"] = RuntimeError(str(error) or error.__class__.__name__)
                self._debug(
                    "Worker task failed with BaseException: "
                    f"{error.__class__.__name__}: {error}\n{traceback.format_exc()}"
                )

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

        progress = QProgressDialog(parent)
        progress.setWindowTitle(title)
        progress.setLabelText(label)
        progress.setCancelButtonText("Cancel")
        progress.setRange(0, 0)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        cancelled = False
        while thread.is_alive():
            QApplication.processEvents()
            if progress.wasCanceled() and not cancel_event.is_set():
                cancelled = True
                self._info("Google picker media download cancelled by user")
                cancel_event.set()
            time.sleep(0.03)

        progress.close()
        thread.join(timeout=0.1)

        if cancelled:
            raise RuntimeError("Google Photos download cancelled by user")

        worker_error = result.get("error")
        if isinstance(worker_error, Exception):
            raise worker_error

        return result.get("value")

    def _list_picked_media_items(
        self,
        session: Any,
        picker_session_id: str,
        cancel_event: threading.Event | None = None,
    ) -> list[dict[str, Any]]:
        self._debug(f"Listing picked media items for session={picker_session_id}")
        items: list[dict[str, Any]] = []
        skipped_non_images = 0
        page_token = ""

        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Google Photos download cancelled by user")

            params: dict[str, str | int] = {
                "sessionId": picker_session_id,
                "pageSize": 100,
            }
            if page_token:
                params["pageToken"] = page_token

            response = session.get(
                PICKER_MEDIA_ITEMS_ENDPOINT,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("Invalid picker media list response")

            raw_items = payload.get("mediaItems")
            if isinstance(raw_items, list):
                for item in raw_items:
                    if isinstance(item, dict):
                        try:
                            if _is_picker_image_item(item):
                                items.append(item)
                            else:
                                skipped_non_images += 1
                        except Exception:
                            skipped_non_images += 1

            page_token = str(payload.get("nextPageToken", "")).strip()
            if not page_token:
                break

        self._info(
            "Picked media list complete: "
            f"session={picker_session_id} image_count={len(items)} "
            f"skipped_non_images={skipped_non_images}"
        )
        return items

    def _download_picked_media_items(
        self,
        session: Any,
        account_id: str,
        picker_session_id: str,
        picked_items: list[dict[str, Any]],
        cancel_event: threading.Event | None = None,
    ) -> tuple[list[SourceAsset], Path]:
        safe_account = re.sub(r"[^A-Za-z0-9._-]+", "_", account_id.strip())
        safe_account = safe_account.strip("._") or "default"
        picker_cache_dir = (
            self.cache_root() / safe_account / f"picker_{picker_session_id}"
        )
        picker_cache_dir.mkdir(parents=True, exist_ok=True)

        media_cache_dir = self.cache_root() / safe_account / "media_items"
        media_cache_dir.mkdir(parents=True, exist_ok=True)

        index_path = media_cache_dir / ".gpicker_media_index.json"
        index_map: dict[str, str] = {}
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        if isinstance(key, str) and isinstance(value, str):
                            index_map[key] = value
            except (OSError, json.JSONDecodeError):
                index_map = {}

        assets: list[SourceAsset] = []
        used_names = set(index_map.values())
        reused_count = 0
        downloaded_count = 0

        for item in picked_items:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Google Photos download cancelled by user")

            try:
                is_image_item = _is_picker_image_item(item)
            except Exception:
                is_image_item = False
            if not is_image_item:
                continue

            media_file = item.get("mediaFile")
            media_file_data = media_file if isinstance(media_file, dict) else {}

            media_id = str(item.get("id", "")).strip()
            base_url = str(
                media_file_data.get("baseUrl") or item.get("baseUrl") or ""
            ).strip()
            mime_type = (
                str(media_file_data.get("mimeType") or item.get("mimeType") or "")
                .strip()
                .lower()
            )

            if not media_id or not base_url:
                continue
            if not mime_type.startswith("image/"):
                continue

            mapped_name = index_map.get(media_id, "").strip()
            if mapped_name:
                local_path = media_cache_dir / mapped_name
            else:
                raw_name = str(
                    media_file_data.get("filename") or item.get("filename") or media_id
                )
                filename = _sanitize_filename(raw_name)
                local_path = media_cache_dir / filename
                stem = local_path.stem
                suffix = local_path.suffix
                collision = 1
                while local_path.name in used_names:
                    local_path = media_cache_dir / f"{stem}_{collision}{suffix}"
                    collision += 1
                index_map[media_id] = local_path.name
                used_names.add(local_path.name)

            if not local_path.exists():
                response = session.get(f"{base_url}=d", timeout=120)
                response.raise_for_status()
                with local_path.open("wb") as handle:
                    handle.write(response.content)
                downloaded_count += 1
            else:
                reused_count += 1

            creation_time = str(
                media_file_data.get("createTime") or item.get("createTime") or ""
            )
            captured_at = _parse_iso_datetime(creation_time)

            location = _extract_location(item)
            latitude: float | None = None
            longitude: float | None = None
            if location is not None:
                latitude, longitude = location

            source_data: dict[str, object] = {
                "provider": "google-photos",
                "flow": "picker",
                "picker_session_id": picker_session_id,
                "mime_type": mime_type,
                "base_url": base_url,
                "filename": local_path.name,
                "create_time": creation_time,
            }
            if latitude is not None and longitude is not None:
                source_data["location"] = {
                    "latitude": latitude,
                    "longitude": longitude,
                }

            assets.append(
                SourceAsset(
                    key=f"gpicker:{media_id}",
                    local_path=local_path,
                    display_name=local_path.name,
                    source_photo_id=media_id,
                    captured_at=captured_at,
                    latitude=latitude,
                    longitude=longitude,
                    source_data=source_data,
                )
            )

        try:
            with index_path.open("w", encoding="utf-8") as handle:
                json.dump(index_map, handle, indent=2, ensure_ascii=False)
        except OSError:
            pass

        self._info(
            "Picker media cache summary: "
            f"account={safe_account} downloaded={downloaded_count} reused={reused_count}"
        )

        return assets, picker_cache_dir

    def _list_albums(
        self,
        session: Any,
    ) -> list[dict[str, Any]]:
        self._debug("Listing Google albums")
        albums: list[dict[str, Any]] = []
        page_token = ""
        page_index = 0
        while True:
            params: dict[str, str | int] = {"pageSize": 50}
            if page_token:
                params["pageToken"] = page_token
            response = session.get(ALBUMS_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            raw_albums = payload.get("albums")
            if isinstance(raw_albums, list):
                for item in raw_albums:
                    if isinstance(item, dict):
                        albums.append(item)
            page_index += 1
            self._debug(f"Albums page {page_index}: collected_total={len(albums)}")
            page_token = str(payload.get("nextPageToken", "")).strip()
            if not page_token:
                break
        self._info(f"Album listing complete: {len(albums)} album(s)")
        return albums

    def _list_shared_albums(
        self,
        session: Any,
    ) -> list[dict[str, Any]]:
        self._debug("Listing Google shared albums")
        albums: list[dict[str, Any]] = []
        page_token = ""
        page_index = 0
        while True:
            params: dict[str, str | int] = {"pageSize": 50}
            if page_token:
                params["pageToken"] = page_token
            response = session.get(SHARED_ALBUMS_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            raw_albums = payload.get("sharedAlbums")
            if isinstance(raw_albums, list):
                for item in raw_albums:
                    if isinstance(item, dict):
                        albums.append(item)
            page_index += 1
            self._debug(
                f"Shared albums page {page_index}: collected_total={len(albums)}"
            )
            page_token = str(payload.get("nextPageToken", "")).strip()
            if not page_token:
                break
        self._info(f"Shared album listing complete: {len(albums)} album(s)")
        return albums

    def _album_label(
        self, album: dict[str, Any], *, prefix: str = ""
    ) -> tuple[str, str]:
        title = str(album.get("title", "Untitled")).strip() or "Untitled"
        count = str(album.get("mediaItemsCount", "?")).strip() or "?"
        album_id = str(album.get("id", "")).strip()
        if not album_id:
            return "", ""
        label = f"{prefix}{title} ({count})"
        return label, album_id

    def _album_search_text(self, album: dict[str, Any], album_kind: str) -> str:
        title = str(album.get("title", "Untitled")).strip() or "Untitled"
        count = str(album.get("mediaItemsCount", "?")).strip() or "?"
        album_id = str(album.get("id", "")).strip()
        kind_text = "shared" if album_kind == "shared" else "album"
        return f"{title} {count} {album_id} {kind_text}".lower()

    def _fetch_album_cover_thumbnail(
        self,
        session: Any,
        album: dict[str, Any],
        *,
        size: int = 112,
    ) -> QPixmap | None:
        base_url = str(album.get("coverPhotoBaseUrl", "")).strip()
        if not base_url:
            return None
        url = f"{base_url}=w{size}-h{size}-c"
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            data = response.content
        except Exception:
            return None

        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return None
        return pixmap

    def _select_album(
        self,
        parent: QWidget | None,
        session: Any,
        albums: list[dict[str, Any]],
        shared_albums: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], str] | None:
        if not albums and not shared_albums:
            QMessageBox.information(parent, "Google Photos", "No albums found.")
            return None

        dialog = QDialog(parent)
        dialog.setWindowTitle("Google Photos")
        dialog.setModal(True)
        dialog.resize(640, 460)

        layout = QVBoxLayout(dialog)
        helper = QLabel("Select an album to import")
        layout.addWidget(helper)

        search_row = QHBoxLayout()
        search_label = QLabel("Search")
        search_field = QLineEdit(dialog)
        search_field.setPlaceholderText("Filter albums by title, type, id, count")
        search_row.addWidget(search_label)
        search_row.addWidget(search_field)
        layout.addLayout(search_row)

        tabs = QTabWidget(dialog)
        all_list = QListWidget(dialog)
        own_list = QListWidget(dialog)
        shared_list = QListWidget(dialog)
        tabs.addTab(all_list, f"All ({len(albums) + len(shared_albums)})")
        tabs.addTab(own_list, f"Albums ({len(albums)})")
        tabs.addTab(shared_list, f"Shared Albums ({len(shared_albums)})")
        layout.addWidget(tabs)

        all_by_row: list[tuple[dict[str, Any], str]] = []
        all_labels: set[str] = set()

        for album in albums:
            label, album_id = self._album_label(album, prefix="[A] ")
            if not album_id:
                continue
            unique_label = label
            suffix = 1
            while unique_label in all_labels:
                suffix += 1
                unique_label = f"{label} [{album_id[:8]}-{suffix}]"
            all_labels.add(unique_label)
            item = QListWidgetItem(unique_label)
            item.setData(
                int(Qt.ItemDataRole.UserRole), self._album_search_text(album, "album")
            )
            all_list.addItem(item)
            all_by_row.append((album, "album"))

        for album in shared_albums:
            label, album_id = self._album_label(album, prefix="[S] ")
            if not album_id:
                continue
            unique_label = label
            suffix = 1
            while unique_label in all_labels:
                suffix += 1
                unique_label = f"{label} [{album_id[:8]}-{suffix}]"
            all_labels.add(unique_label)
            item = QListWidgetItem(unique_label)
            item.setData(
                int(Qt.ItemDataRole.UserRole), self._album_search_text(album, "shared")
            )
            all_list.addItem(item)
            all_by_row.append((album, "shared"))

        own_by_row: list[dict[str, Any]] = []
        own_labels: set[str] = set()
        for album in albums:
            label, album_id = self._album_label(album)
            if not album_id:
                continue
            unique_label = label
            suffix = 1
            while unique_label in own_labels:
                suffix += 1
                unique_label = f"{label} [{album_id[:8]}-{suffix}]"
            own_labels.add(unique_label)
            item = QListWidgetItem(unique_label)
            item.setData(
                int(Qt.ItemDataRole.UserRole), self._album_search_text(album, "album")
            )
            own_list.addItem(item)
            own_by_row.append(album)

        shared_by_row: list[dict[str, Any]] = []
        shared_labels: set[str] = set()
        for album in shared_albums:
            label, album_id = self._album_label(album)
            if not album_id:
                continue
            unique_label = label
            suffix = 1
            while unique_label in shared_labels:
                suffix += 1
                unique_label = f"{label} [{album_id[:8]}-{suffix}]"
            shared_labels.add(unique_label)
            item = QListWidgetItem(unique_label)
            item.setData(
                int(Qt.ItemDataRole.UserRole), self._album_search_text(album, "shared")
            )
            shared_list.addItem(item)
            shared_by_row.append(album)

        details_row = QHBoxLayout()
        cover_label = QLabel(dialog)
        cover_label.setFixedSize(112, 112)
        cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_label.setText("No cover")
        details_label = QLabel(dialog)
        details_label.setWordWrap(True)
        details_label.setText("Select an album to view details")
        details_row.addWidget(cover_label)
        details_row.addWidget(details_label, 1)
        layout.addLayout(details_row)

        cover_cache: dict[str, QPixmap | None] = {}

        def selected_album_from_current_tab() -> tuple[dict[str, Any], str] | None:
            if tabs.currentIndex() == 0:
                row = all_list.currentRow()
                if 0 <= row < len(all_by_row):
                    return all_by_row[row]
                return None
            if tabs.currentIndex() == 1:
                row = own_list.currentRow()
                if 0 <= row < len(own_by_row):
                    return own_by_row[row], "album"
                return None
            row = shared_list.currentRow()
            if 0 <= row < len(shared_by_row):
                return shared_by_row[row], "shared"
            return None

        def update_details_panel() -> None:
            selected = selected_album_from_current_tab()
            if selected is None:
                details_label.setText("Select an album to view details")
                cover_label.setPixmap(QPixmap())
                cover_label.setText("No cover")
                return

            album, album_kind = selected
            title = str(album.get("title", "Untitled")).strip() or "Untitled"
            count = str(album.get("mediaItemsCount", "?")).strip() or "?"
            album_id = str(album.get("id", "")).strip()
            kind_text = "Shared Album" if album_kind == "shared" else "Album"
            has_cover = bool(str(album.get("coverPhotoBaseUrl", "")).strip())
            details_label.setText(
                f"Type: {kind_text}\n"
                f"Title: {title}\n"
                f"Items: {count}\n"
                f"ID: {album_id}\n"
                f"Cover: {'Yes' if has_cover else 'No'}\n"
                "Last added: not available from album list API"
            )

            if not album_id:
                cover_label.setPixmap(QPixmap())
                cover_label.setText("No cover")
                return

            if album_id not in cover_cache:
                cover_cache[album_id] = self._fetch_album_cover_thumbnail(
                    session, album
                )
            pixmap = cover_cache.get(album_id)
            if pixmap is None:
                cover_label.setPixmap(QPixmap())
                cover_label.setText("No cover")
            else:
                cover_label.setPixmap(
                    pixmap.scaled(
                        cover_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                cover_label.setText("")

        def apply_filter() -> None:
            query = search_field.text().strip().lower()
            for widget in (all_list, own_list, shared_list):
                for index in range(widget.count()):
                    item = widget.item(index)
                    search_text = str(
                        item.data(int(Qt.ItemDataRole.UserRole)) or ""
                    ).lower()
                    item.setHidden(bool(query) and query not in search_text)

            update_details_panel()

        search_field.textChanged.connect(lambda _value: apply_filter())
        tabs.currentChanged.connect(lambda _index: update_details_panel())
        all_list.currentRowChanged.connect(lambda _row: update_details_panel())
        own_list.currentRowChanged.connect(lambda _row: update_details_panel())
        shared_list.currentRowChanged.connect(lambda _row: update_details_panel())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if own_by_row:
            tabs.setCurrentIndex(0)
            all_list.setCurrentRow(0)
            own_list.setCurrentRow(0)
        elif shared_by_row:
            all_list.setCurrentRow(0)
            shared_list.setCurrentRow(0)
            tabs.setCurrentIndex(0)

        update_details_panel()

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        selected = selected_album_from_current_tab()
        if selected is None:
            QMessageBox.information(parent, "Google Photos", "Please select an album.")
            return None
        return selected

    def _list_album_media_items(
        self,
        session: Any,
        album_id: str,
    ) -> list[dict[str, Any]]:
        self._debug(f"Listing media items for album_id={album_id}")
        items: list[dict[str, Any]] = []
        page_token = ""
        page_index = 0
        while True:
            payload: dict[str, str | int] = {"albumId": album_id, "pageSize": 100}
            if page_token:
                payload["pageToken"] = page_token
            response = session.post(MEDIA_SEARCH_ENDPOINT, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            raw_items = data.get("mediaItems")
            if isinstance(raw_items, list):
                for item in raw_items:
                    if isinstance(item, dict):
                        items.append(item)
            page_index += 1
            self._debug(
                f"Media page {page_index} for album_id={album_id}: "
                f"collected_total={len(items)}"
            )
            page_token = str(data.get("nextPageToken", "")).strip()
            if not page_token:
                break
        self._info(
            f"Media listing complete for album_id={album_id}: {len(items)} item(s)"
        )
        return items

    def _download_album(
        self,
        session: Any,
        account_id: str,
        album_id: str,
        album_title: str,
    ) -> tuple[list[SourceAsset], Path]:
        self._debug(
            f"Download start: account_id={account_id} album_id={album_id} "
            f"title={album_title}"
        )
        safe_account = re.sub(r"[^A-Za-z0-9._-]+", "_", account_id.strip())
        safe_account = safe_account.strip("._") or "default"
        cache_dir = self.cache_root() / safe_account / album_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        index_path = cache_dir / ".gphotos_index.json"
        index_map: dict[str, str] = {}
        if index_path.exists():
            try:
                with index_path.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        if isinstance(key, str) and isinstance(value, str):
                            index_map[key] = value
            except (OSError, json.JSONDecodeError):
                index_map = {}

        items = self._list_album_media_items(session, album_id)
        assets: list[SourceAsset] = []
        used_names: set[str] = set()

        for existing_name in index_map.values():
            used_names.add(existing_name)

        for item in items:
            media_id = str(item.get("id", "")).strip()
            base_url = str(item.get("baseUrl", "")).strip()
            mime_type = str(item.get("mimeType", "")).strip().lower()
            if not media_id or not base_url:
                continue
            if not mime_type.startswith("image/"):
                continue

            mapped_name = index_map.get(media_id, "").strip()
            if mapped_name:
                local_path = cache_dir / mapped_name
            else:
                filename = _sanitize_filename(str(item.get("filename", media_id)))
                local_path = cache_dir / filename
                stem = local_path.stem
                suffix = local_path.suffix
                collision = 1
                while local_path.name in used_names:
                    local_path = cache_dir / f"{stem}_{collision}{suffix}"
                    collision += 1
                index_map[media_id] = local_path.name
                used_names.add(local_path.name)

            if not local_path.exists():
                download_url = f"{base_url}=d"
                response = session.get(download_url, timeout=120)
                response.raise_for_status()
                with local_path.open("wb") as handle:
                    handle.write(response.content)

            if media_id not in index_map:
                index_map[media_id] = local_path.name
                used_names.add(local_path.name)

            media_metadata = item.get("mediaMetadata")
            captured_at = None
            if isinstance(media_metadata, dict):
                captured_at = _parse_iso_datetime(
                    str(media_metadata.get("creationTime", ""))
                )

            location = _extract_location(item)
            latitude: float | None = None
            longitude: float | None = None
            if location is not None:
                latitude, longitude = location

            assets.append(
                SourceAsset(
                    key=f"gphoto:{media_id}",
                    local_path=local_path,
                    display_name=local_path.name,
                    source_photo_id=media_id,
                    captured_at=captured_at,
                    latitude=latitude,
                    longitude=longitude,
                    source_data={
                        "provider": "google-photos",
                        "flow": "library",
                        "album_id": album_id,
                        "album_title": album_title,
                        "mime_type": mime_type,
                        "base_url": base_url,
                        "filename": local_path.name,
                    },
                )
            )

        try:
            with index_path.open("w", encoding="utf-8") as handle:
                json.dump(index_map, handle, indent=2, ensure_ascii=False)
        except OSError:
            pass

        contexts = self.load_contexts()
        albums = contexts.get("albums")
        if not isinstance(albums, dict):
            albums = {}
            contexts["albums"] = albums
        context_key = self._context_key(account_id, album_id)
        albums[context_key] = {
            "account_id": account_id,
            "title": album_title,
            "album_type": "album",
            "cache_dir": str(cache_dir),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.save_contexts(contexts)

        self._info(
            f"Download complete: account_id={account_id} album_id={album_id} "
            f"assets={len(assets)} cache_dir={cache_dir}"
        )

        return assets, cache_dir

    def load_via_ui(self, parent: QWidget | None = None) -> SourceLoadResult | None:
        selected = self._select_or_add_account(parent)
        if selected is None:
            return None
        account_id, session = selected

        picker_session_id = ""

        try:
            picker_session = self._create_picker_session(session)
            picker_session_id = str(picker_session.get("id", "")).strip()
            picker_uri = str(picker_session.get("pickerUri", "")).strip()
            if not picker_uri:
                raise RuntimeError("Picker session did not provide pickerUri")

            opened = QDesktopServices.openUrl(QUrl(picker_uri))
            if not opened:
                raise RuntimeError(
                    "Could not open Google Photos Picker in your browser"
                )

            if not self._wait_for_picker_completion(parent, session, picker_session):
                return None

            picked_items_result = self._run_worker_with_progress(
                parent,
                title="Google Photos",
                label="Retrieving selected items from Google Photos...",
                task=lambda cancel_event: self._list_picked_media_items(
                    session,
                    picker_session_id,
                    cancel_event=cancel_event,
                ),
            )
            picked_items = (
                picked_items_result if isinstance(picked_items_result, list) else []
            )
            self._debug(
                f"Picker selected raw item count={len(picked_items)} session={picker_session_id}"
            )
            for index, item in enumerate(picked_items, start=1):
                try:
                    payload_text = json.dumps(item, ensure_ascii=False, sort_keys=True)
                except Exception:
                    payload_text = str(item)
                if len(payload_text) > 4000:
                    payload_text = payload_text[:4000] + "…"
                self._debug(f"Picker selected raw item {index}: {payload_text}")

            if not picked_items:
                QMessageBox.information(
                    parent,
                    "Google Photos",
                    "No images were selected in Google Photos Picker.",
                )
                return None

            download_result = self._run_worker_with_progress(
                parent,
                title="Google Photos",
                label=f"Downloading {len(picked_items)} selected image(s)...",
                task=lambda cancel_event: self._download_picked_media_items(
                    session,
                    account_id,
                    picker_session_id,
                    picked_items,
                    cancel_event=cancel_event,
                ),
            )
            if (
                not isinstance(download_result, tuple)
                or len(download_result) != 2
                or not isinstance(download_result[1], Path)
            ):
                raise RuntimeError("Invalid picker download result")
            assets, metadata_root = download_result
            self._debug(
                f"Picker normalized asset count={len(assets)} metadata_root={metadata_root}"
            )
            for index, asset in enumerate(assets, start=1):
                captured_text = (
                    asset.captured_at.isoformat(timespec="seconds")
                    if asset.captured_at is not None
                    else ""
                )
                self._debug(
                    "Picker normalized asset "
                    f"{index}: key={asset.key} "
                    f"photo_id={asset.source_photo_id or ''} "
                    f"display={asset.display_name} "
                    f"local={asset.local_path} "
                    f"captured_at={captured_text} "
                    f"lat={asset.latitude if asset.latitude is not None else ''} "
                    f"lon={asset.longitude if asset.longitude is not None else ''}"
                )

            contexts = self.load_contexts()
            albums_cache = contexts.get("albums")
            if not isinstance(albums_cache, dict):
                albums_cache = {}
                contexts["albums"] = albums_cache
            album_id = f"picker:{picker_session_id}"
            context_key = self._context_key(account_id, album_id)
            entry = albums_cache.get(context_key)
            if not isinstance(entry, dict):
                entry = {}
            entry["account_id"] = account_id
            entry["title"] = "Picker Selection"
            entry["album_type"] = "picker"
            entry["cache_dir"] = str(metadata_root)
            entry["updated_at"] = datetime.now().isoformat(timespec="seconds")
            albums_cache[context_key] = entry
            self.save_contexts(contexts)

            context_id = self._context_key(account_id, album_id)

            return SourceLoadResult(
                source_id=self.source_id,
                source_label=self.label,
                context_id=context_id,
                context_label=f"Google Photos ({account_id}) [Picker]: {len(assets)} item(s)",
                assets=assets,
                metadata_root=metadata_root,
                is_new_context=not (metadata_root / ".album_printer.json").exists(),
            )
        except Exception as error:
            message = self._format_google_api_error(
                error,
                operation="load Google Photos picker selection",
            )
            QMessageBox.critical(
                parent,
                "Google Photos",
                message,
            )
            return None
        finally:
            if picker_session_id:
                self._delete_picker_session(session, picker_session_id)

    def refresh(
        self,
        context_id: str,
        preferred_path: Path | None = None,
    ) -> SourceLoadResult:
        account_id_from_context, album_id = self._parse_context_id(context_id)
        if not account_id_from_context or not album_id:
            raise RuntimeError("Invalid Google Photos context id")

        if album_id.startswith("picker:"):
            raise RuntimeError(
                "Google Photos Picker selections cannot be refreshed. "
                "Use Load ... -> Google Photos to pick items again."
            )

        contexts = self.load_contexts()
        accounts = contexts.get("accounts")
        if not isinstance(accounts, dict):
            accounts = {}

        account_id = account_id_from_context.strip()
        if account_id not in accounts:
            raise RuntimeError("Google account for this context no longer exists")

        session = self._authorized_session(None, account_id)
        if session is None:
            raise RuntimeError("Google Photos authentication failed")

        albums = contexts.get("albums")
        album_title = "Album"
        album_type = "album"
        if isinstance(albums, dict):
            album_entry = albums.get(self._context_key(account_id, album_id))
            if isinstance(album_entry, dict):
                album_title = (
                    str(album_entry.get("title", album_title)).strip() or album_title
                )
            album_type = str(album_entry.get("album_type", "album")).strip() or "album"

        try:
            assets, metadata_root = self._download_album(
                session,
                account_id,
                album_id,
                album_title,
            )
        except Exception as error:
            message = self._format_google_api_error(
                error,
                operation="refresh Google Photos album",
            )
            raise RuntimeError(message) from error

        resolved_context_id = self._context_key(account_id, album_id)

        return SourceLoadResult(
            source_id=self.source_id,
            source_label=self.label,
            context_id=resolved_context_id,
            context_label=(
                f"Google Photos ({account_id}) "
                f"[{'Shared' if album_type == 'shared' else 'Album'}]: {album_title}"
            ),
            assets=assets,
            metadata_root=metadata_root,
            is_new_context=not (metadata_root / ".album_printer.json").exists(),
        )
