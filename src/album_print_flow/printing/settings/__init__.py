"""Print settings UI split by backend (IPP, CUPS, Qt)."""

from album_print_flow.printing.settings.cups import build_driver_options_section
from album_print_flow.printing.settings.ipp import build_ipp_section
from album_print_flow.printing.settings.qt import build_paper_section

__all__ = [
    "build_driver_options_section",
    "build_ipp_section",
    "build_paper_section",
]
