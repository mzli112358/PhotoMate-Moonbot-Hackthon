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


class FileDeliveryAdapter:
    def __init__(self, store: PhotoStore, base_url: str) -> None:
        self.store = store
        self.base_url = base_url.rstrip("/")

    def register_photo(self, photo_id: str, path: Path) -> None:
        self.store.register(photo_id, path)

    async def show(self, photo_id: str) -> bool:
        return self.store.resolve(photo_id) is not None

    async def deliver(self, photo_id: str) -> DeliveryResult:
        if self.store.resolve(photo_id) is None:
            return DeliveryResult(photo_id, "", False, "photo_not_found")
        return DeliveryResult(photo_id, f"{self.base_url}/api/photos/{photo_id}", True)


GLOBAL_PHOTO_STORE = PhotoStore()
