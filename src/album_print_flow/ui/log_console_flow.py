from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def current_log_level_rank(window: Any, *, log_level_rank: dict[str, int]) -> int:
    return log_level_rank.get(window.log_level_filter_value, log_level_rank["INFO"])


def current_log_text_filter(window: Any) -> str:
    return window.log_text_filter_value.strip().lower()


def log_entry_visible(
    window: Any,
    level: str,
    line: str,
    *,
    log_level_rank: dict[str, int],
) -> bool:
    rank = log_level_rank.get(level, log_level_rank["INFO"])
    if rank < window.current_log_level_rank():
        return False
    text_filter = window.current_log_text_filter()
    if not text_filter:
        return True
    return text_filter in line.lower()


def refresh_log_console(window: Any) -> None:
    window.log_console.clear()
    for level, line in window.log_entries:
        if window._log_entry_visible(level, line):
            window.log_console.append(line)


def on_log_level_changed(
    window: Any,
    value: str,
    *,
    log_level_rank: dict[str, int],
) -> None:
    level = value.strip().upper()
    if level not in log_level_rank:
        level = "INFO"
    window.log_level_filter_value = level
    window.refresh_log_console()


def on_log_text_filter_changed(window: Any, value: str) -> None:
    window.log_text_filter_value = value.strip()
    window.refresh_log_console()


def clear_log_console(window: Any) -> None:
    window.log_entries = []
    window.log_console.clear()


def thread_safe_append_log(window: Any, level: str, message: str) -> None:
    window.log_message_requested.emit(str(level), str(message))


def log_file_path(
    _window: Any,
    *,
    settings_org: str,
    log_filename: str,
) -> Path | None:
    return Path.home() / ".config" / settings_org / log_filename


def append_log(
    window: Any,
    level: str,
    message: str,
    *,
    qthread_cls: type,
    log_level_rank: dict[str, int],
) -> None:
    if qthread_cls.currentThread() != window.thread():
        window.log_message_requested.emit(str(level), str(message))
        return

    level_text = level.strip().upper() or "INFO"
    if level_text not in log_level_rank:
        level_text = "INFO"
    if window.maybe_update_album_sync_status_from_log(level_text, str(message)):
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [{level_text}] {message}"
    window.log_entries.append((level_text, line))
    if window._log_entry_visible(level_text, line):
        window.log_console.append(line)

    path = window.log_file_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file_handle:
            file_handle.write(line + "\n")
    except OSError:
        return


__all__ = [
    "append_log",
    "clear_log_console",
    "current_log_level_rank",
    "current_log_text_filter",
    "log_file_path",
    "log_entry_visible",
    "on_log_level_changed",
    "on_log_text_filter_changed",
    "refresh_log_console",
    "thread_safe_append_log",
]
