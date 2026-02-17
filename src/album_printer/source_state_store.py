from __future__ import annotations

import json
from pathlib import Path


def source_state_path(app_name: str) -> Path:
    root = Path.home() / ".config" / app_name
    return root / "source_state.json"


def load_source_state(app_name: str) -> dict[str, object]:
    path = source_state_path(app_name)
    if not path.exists():
        return {"version": 1, "google_photo_state": {}}

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            state = {"version": 1, "google_photo_state": {}} | data
            if not isinstance(state.get("google_photo_state"), dict):
                state["google_photo_state"] = {}
            return state
    except (OSError, json.JSONDecodeError):
        pass

    return {"version": 1, "google_photo_state": {}}


def save_source_state(app_name: str, state: dict[str, object]) -> None:
    path = source_state_path(app_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except OSError:
        return
