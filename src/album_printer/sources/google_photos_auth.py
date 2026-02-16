"""Google Photos authentication helper.

This module handles OAuth2 authentication for Google Photos API access.
"""

from __future__ import annotations

import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Photos API scope - read-only access to photos
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]

# Default paths for credentials storage
DEFAULT_CREDENTIALS_FILE = "google_photos_credentials.json"
DEFAULT_TOKEN_FILE = ".google_photos_token.pickle"


class GooglePhotosAuth:
    """Handles Google Photos OAuth2 authentication."""

    def __init__(
        self,
        credentials_path: Path | None = None,
        token_path: Path | None = None,
    ) -> None:
        """Initialize authentication handler.

        Args:
            credentials_path: Path to OAuth2 client credentials JSON file
            token_path: Path to store/load authentication tokens
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._credentials: Credentials | None = None

    def get_credentials(self) -> Credentials | None:
        """Get valid Google Photos API credentials.

        Returns:
            Valid credentials or None if authentication is needed
        """
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to load existing token
        if self.token_path and self.token_path.exists():
            try:
                with open(self.token_path, "rb") as token_file:
                    self._credentials = pickle.load(token_file)
            except Exception:
                self._credentials = None

        # Refresh if expired
        if (
            self._credentials
            and self._credentials.expired
            and self._credentials.refresh_token
        ):
            try:
                self._credentials.refresh(Request())
                self._save_token()
                return self._credentials
            except Exception:
                self._credentials = None

        return self._credentials

    def authenticate(self) -> Credentials | None:
        """Perform OAuth2 authentication flow.

        Returns:
            Valid credentials or None if authentication failed
        """
        if not self.credentials_path or not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                "Please provide a valid OAuth2 credentials file from "
                "Google Cloud Console."
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), SCOPES
            )
            self._credentials = flow.run_local_server(
                port=0,
                authorization_prompt_message="",
                success_message="Authentication successful! You can close this window.",
                open_browser=True,
            )
            self._save_token()
            return self._credentials
        except Exception as e:
            raise RuntimeError(f"Authentication failed: {e}") from e

    def _save_token(self) -> None:
        """Save authentication token to disk."""
        if self.token_path and self._credentials:
            try:
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, "wb") as token_file:
                    pickle.dump(self._credentials, token_file)
            except Exception:
                pass  # Fail silently, token will be re-authenticated next time

    def is_authenticated(self) -> bool:
        """Check if valid credentials are available.

        Returns:
            True if authenticated, False otherwise
        """
        creds = self.get_credentials()
        return creds is not None and creds.valid

    def clear_credentials(self) -> None:
        """Clear stored credentials and tokens."""
        self._credentials = None
        if self.token_path and self.token_path.exists():
            try:
                self.token_path.unlink()
            except Exception:
                pass
