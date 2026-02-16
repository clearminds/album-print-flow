"""Google Photos API client wrapper.

This module provides a simplified interface to the Google Photos API.
"""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from album_printer.sources.google_photos_auth import GooglePhotosAuth


class GooglePhotosClient:
    """Client for interacting with Google Photos API."""

    def __init__(self, auth: GooglePhotosAuth) -> None:
        """Initialize Google Photos client.

        Args:
            auth: Authentication handler
        """
        self.auth = auth
        self._service = None

    def _get_service(self):
        """Get or create Google Photos API service."""
        if self._service is None:
            credentials = self.auth.get_credentials()
            if not credentials:
                raise RuntimeError("Not authenticated. Please authenticate first.")
            self._service = build(
                "photoslibrary", "v1", credentials=credentials, static_discovery=False
            )
        return self._service

    def list_albums(self, page_size: int = 50) -> list[dict[str, Any]]:
        """List all albums.

        Args:
            page_size: Number of albums to fetch per page

        Returns:
            List of album metadata dictionaries
        """
        try:
            service = self._get_service()
            albums = []
            page_token = None

            while True:
                response = (
                    service.albums()
                    .list(pageSize=page_size, pageToken=page_token)
                    .execute()
                )

                if "albums" in response:
                    albums.extend(response["albums"])

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return albums
        except HttpError as e:
            raise RuntimeError(f"Failed to list albums: {e}") from e

    def get_album_photos(
        self, album_id: str, page_size: int = 100
    ) -> list[dict[str, Any]]:
        """Get all photos from an album.

        Args:
            album_id: Album ID to fetch photos from
            page_size: Number of photos to fetch per page

        Returns:
            List of photo metadata dictionaries
        """
        try:
            service = self._get_service()
            photos = []
            page_token = None

            while True:
                body = {
                    "albumId": album_id,
                    "pageSize": page_size,
                }
                if page_token:
                    body["pageToken"] = page_token

                response = service.mediaItems().search(body=body).execute()

                if "mediaItems" in response:
                    photos.extend(response["mediaItems"])

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return photos
        except HttpError as e:
            raise RuntimeError(f"Failed to get album photos: {e}") from e

    def get_photo_url(self, media_item: dict[str, Any]) -> str | None:
        """Get download URL for a photo.

        Args:
            media_item: Media item metadata from API

        Returns:
            Download URL or None if not available
        """
        base_url = media_item.get("baseUrl")
        if not base_url:
            return None

        # Add parameters for full resolution download
        return f"{base_url}=d"

    def get_photo_metadata(self, media_item: dict[str, Any]) -> dict[str, Any]:
        """Extract relevant metadata from a media item.

        Args:
            media_item: Media item metadata from API

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            "id": media_item.get("id"),
            "filename": media_item.get("filename"),
            "mime_type": media_item.get("mimeType"),
            "creation_time": media_item.get("mediaMetadata", {}).get("creationTime"),
            "width": media_item.get("mediaMetadata", {}).get("width"),
            "height": media_item.get("mediaMetadata", {}).get("height"),
        }

        # Extract location if available
        photo_metadata = media_item.get("mediaMetadata", {}).get("photo", {})
        if photo_metadata:
            camera_make = photo_metadata.get("cameraMake")
            camera_model = photo_metadata.get("cameraModel")
            focal_length = photo_metadata.get("focalLength")
            aperture = photo_metadata.get("apertureFNumber")
            iso = photo_metadata.get("isoEquivalent")

            metadata.update(
                {
                    "camera_make": camera_make,
                    "camera_model": camera_model,
                    "focal_length": focal_length,
                    "aperture": aperture,
                    "iso": iso,
                }
            )

        # Extract GPS location if available
        location = media_item.get("mediaMetadata", {}).get("location")
        if location:
            lat = location.get("latitude")
            lon = location.get("longitude")
            if lat is not None and lon is not None:
                metadata["location"] = f"{lat}, {lon}"

        return metadata
