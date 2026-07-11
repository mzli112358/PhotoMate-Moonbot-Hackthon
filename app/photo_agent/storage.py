"""Pluggable object-storage uploaders for delivering captured media.

The default deployment uploads to a public Supabase Storage bucket and returns a
permanent public URL that a phone can open by scanning the QR code. When storage
is not configured the uploader is a no-op and the pipeline falls back to the
LAN-only `/api/photos/{id}` link.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

LOGGER = logging.getLogger("photomate.photo_agent.storage")


class StorageUploader(Protocol):
    @property
    def enabled(self) -> bool: ...

    async def upload(self, photo_id: str, path: Path) -> str | None:
        """Upload the file and return a public URL, or None on failure/disabled."""
        ...


class NullStorageUploader:
    """Fallback used when no object storage is configured."""

    enabled = False

    async def upload(self, photo_id: str, path: Path) -> str | None:
        return None


class SupabaseStorageUploader:
    """Uploads to a public Supabase Storage bucket via the Storage REST API."""

    def __init__(self, *, url: str, service_key: str, bucket: str) -> None:
        self._base = url.rstrip("/")
        self._service_key = service_key
        self._bucket = bucket

    @property
    def enabled(self) -> bool:
        return bool(self._base and self._service_key and self._bucket)

    def _object_path(self, photo_id: str, path: Path) -> str:
        suffix = path.suffix or ".jpg"
        return f"photos/{photo_id}{suffix}"

    def public_url(self, object_path: str) -> str:
        return f"{self._base}/storage/v1/object/public/{self._bucket}/{object_path}"

    def _upload_sync(self, object_path: str, data: bytes, content_type: str) -> str:
        endpoint = f"{self._base}/storage/v1/object/{self._bucket}/{object_path}"
        request = urllib.request.Request(
            endpoint,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._service_key}",
                "apikey": self._service_key,
                "Content-Type": content_type,
                # Overwrite if a prior take reused the id; keeps retakes idempotent.
                "x-upsert": "true",
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
            response.read()
        return self.public_url(object_path)

    async def upload(self, photo_id: str, path: Path) -> str | None:
        import asyncio

        if not self.enabled:
            return None
        if not path.is_file():
            LOGGER.warning("storage_upload_missing_file", extra={"photo_id": photo_id})
            return None
        object_path = self._object_path(photo_id, path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            data = await asyncio.to_thread(path.read_bytes)
            url = await asyncio.to_thread(self._upload_sync, object_path, data, content_type)
            LOGGER.info("storage_upload_ok", extra={"photo_id": photo_id, "url": url})
            return url
        except (urllib.error.URLError, OSError, TimeoutError) as exc:  # noqa: BLE001
            LOGGER.warning(
                "storage_upload_failed", extra={"photo_id": photo_id, "error": str(exc)}
            )
            return None


def build_storage_uploader() -> StorageUploader:
    url = os.getenv("SUPABASE_URL", "").strip()
    # Server-side uploads must use the secret/service_role key (bypasses RLS); the
    # publishable/anon key is rejected by the "authenticated"-only bucket policy.
    service_key = (
        os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        or os.getenv("SUPABASE_SECRET_KEY", "").strip()
    )
    bucket = os.getenv("SUPABASE_BUCKET", "media").strip()
    if url and service_key and bucket:
        return SupabaseStorageUploader(url=url, service_key=service_key, bucket=bucket)
    return NullStorageUploader()
