from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any


def maybe_update_album_sync_status_from_log(
    window: Any,
    level: str,
    message: str,
    *,
    present_status_fn: Callable[..., None],
) -> bool:
    if level != "DEBUG":
        return False
    if not (window.source_load_in_progress or window.source_refresh_in_progress):
        return False

    match = re.search(
        (
            r"GOOGLE_ALBUM_URL\s+sync progress\s+item=(\d+)/(\d+)"
            r"\s+new=(\d+)\s+failed=(\d+)"
        ),
        message,
    )
    if not match:
        return False

    current = int(match.group(1))
    total = int(match.group(2))
    new_count = int(match.group(3))
    failed_count = int(match.group(4))

    window.update_footer_progress("Album Sync", current, total)

    present_status_fn(
        window,
        f"Album URL sync {current}/{total} • new {new_count} • failed {failed_count}",
    )
    return True


__all__ = [
    "maybe_update_album_sync_status_from_log",
]
