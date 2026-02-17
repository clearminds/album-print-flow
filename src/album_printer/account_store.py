from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SubmoduleAccountStore:
    def __init__(
        self,
        app_name: str,
        state_filename: str,
        *,
        defaults: dict[str, Any] | None = None,
    ) -> None:
        self.app_name = app_name
        self.state_filename = str(state_filename)
        self.defaults = dict(defaults or {})

    def config_root(self) -> Path:
        return Path.home() / ".config" / self.app_name

    def state_path(self) -> Path:
        return self.config_root() / self.state_filename

    def load_state(self) -> dict[str, Any]:
        path = self.state_path()
        if not path.exists():
            return dict(self.defaults)

        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                merged = dict(self.defaults)
                merged.update(data)
                return merged
        except (OSError, json.JSONDecodeError):
            pass

        return dict(self.defaults)

    def save_state(self, state: dict[str, Any]) -> None:
        path = self.state_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, indent=2, ensure_ascii=False)
            tmp.replace(path)
        except OSError:
            return

    @staticmethod
    def get_accounts(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
        raw_accounts = state.get("accounts")
        if not isinstance(raw_accounts, dict):
            return {}

        accounts: dict[str, dict[str, Any]] = {}
        for key, value in raw_accounts.items():
            if not isinstance(key, str):
                continue
            accounts[key] = value if isinstance(value, dict) else {}
        return accounts

    @staticmethod
    def get_last_account_id(state: dict[str, Any]) -> str:
        return str(state.get("last_account_id", "") or "").strip()

    @staticmethod
    def set_last_account_id(state: dict[str, Any], account_id: str) -> None:
        state["last_account_id"] = str(account_id or "").strip()
