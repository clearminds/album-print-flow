from __future__ import annotations

from typing import Any


def present_status(window: Any, message: str, timeout_ms: int = 0) -> None:
    message_text = str(message)
    if int(timeout_ms) > 0:
        window.statusBar().showMessage(message_text, int(timeout_ms))
        return
    window.statusBar().showMessage(message_text)


def present_log(window: Any, level: str, message: str) -> None:
    window.append_log(str(level), str(message))


def present_status_and_log(window: Any, *, level: str, message: str) -> None:
    present_status(window, message)
    present_log(window, level, message)


__all__ = [
    "present_log",
    "present_status",
    "present_status_and_log",
]
