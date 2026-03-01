from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QSplashScreen

from album_print_flow.app_branding import app_about_text as app_about_text_impl
from album_print_flow.app_branding import app_branding_info as app_branding_info_impl
from album_print_flow.app_branding import app_runtime_line as app_runtime_line_impl
from album_print_flow.app_branding import app_version as app_version_impl
from album_print_flow.app_branding import (
    create_splash_screen as create_splash_screen_impl,
)
from album_print_flow.app_branding import (
    is_debugger_attached as is_debugger_attached_impl,
)

APP_DISPLAY_NAME = "Album Print Flow"
APP_COPYRIGHT = "© clearminds, 2026"
APP_TAGLINE = "Photo crop, stamp, and print workflow"


def is_debugger_attached() -> bool:
    return is_debugger_attached_impl()


def app_version() -> str:
    return app_version_impl()


def app_runtime_line() -> str:
    return app_runtime_line_impl()


def app_branding_info() -> dict[str, str]:
    return app_branding_info_impl(
        app_display_name=APP_DISPLAY_NAME,
        app_tagline=APP_TAGLINE,
        app_copyright=APP_COPYRIGHT,
    )


def app_about_text() -> str:
    return app_about_text_impl(
        app_display_name=APP_DISPLAY_NAME,
        app_tagline=APP_TAGLINE,
        app_copyright=APP_COPYRIGHT,
    )


def create_splash_screen() -> QSplashScreen:
    return create_splash_screen_impl(
        app_display_name=APP_DISPLAY_NAME,
        app_tagline=APP_TAGLINE,
        app_copyright=APP_COPYRIGHT,
        base_file=Path(__file__),
    )


__all__ = [
    "APP_COPYRIGHT",
    "APP_DISPLAY_NAME",
    "APP_TAGLINE",
    "app_about_text",
    "app_branding_info",
    "app_runtime_line",
    "app_version",
    "create_splash_screen",
    "is_debugger_attached",
]
