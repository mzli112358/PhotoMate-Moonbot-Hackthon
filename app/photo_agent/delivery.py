"""Local filesystem photo delivery adapter."""

from __future__ import annotations

import threading
from pathlib import Path

from app.photo_agent.models import DeliveryResult


class PhotoStore:
    def __init__(self) -> None:
        self._paths: dict[str, Path] = {}
        self._lock = threading.RLock()

    def register(self, photo_id: str, path: Path) -> None:
        resolved = path.resolve()
        if not photo_id or not resolved.is_file():
            raise ValueError("photo_id and an existing file are required")
        with self._lock:
            self._paths[photo_id] = resolved

    def resolve(self, photo_id: str) -> Path | None:
        with self._lock:
            path = self._paths.get(photo_id)
        return path if path and path.is_file() else None

    def delete(self, photo_id: str, *, delete_file: bool = True) -> bool:
        with self._lock:
            path = self._paths.pop(photo_id, None)
        if path is None:
            return False
        if delete_file:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                with self._lock:
                    self._paths[photo_id] = path
                return False
        return True


class DownloadUrlRegistry:
    """Maps photo_id -> public download URL produced by object storage."""

    def __init__(self) -> None:
        self._urls: dict[str, str] = {}
        self._lock = threading.RLock()

    def set(self, photo_id: str, url: str) -> None:
        if not photo_id or not url:
            return
        with self._lock:
            self._urls[photo_id] = url

    def get(self, photo_id: str) -> str | None:
        with self._lock:
            return self._urls.get(photo_id)


class FileDeliveryAdapter:
    def __init__(
        self,
        store: PhotoStore,
        base_url: str,
        download_registry: "DownloadUrlRegistry | None" = None,
    ) -> None:
        self.store = store
        self.base_url = base_url.rstrip("/")
        self.download_registry = download_registry or GLOBAL_DOWNLOAD_REGISTRY

    def register_photo(self, photo_id: str, path: Path) -> None:
        self.store.register(photo_id, path)

    async def show(self, photo_id: str) -> bool:
        return self.store.resolve(photo_id) is not None

    async def deliver(self, photo_id: str) -> DeliveryResult:
        if self.store.resolve(photo_id) is None:
            return DeliveryResult(photo_id, "", False, "photo_not_found")
        # Prefer the public object-storage URL (scannable from a phone); fall back
        # to the LAN-only local endpoint when storage is not configured.
        public_url = self.download_registry.get(photo_id)
        url = public_url or f"{self.base_url}/api/photos/{photo_id}"
        return DeliveryResult(photo_id, url, True)


GLOBAL_PHOTO_STORE = PhotoStore()
GLOBAL_DOWNLOAD_REGISTRY = DownloadUrlRegistry()
