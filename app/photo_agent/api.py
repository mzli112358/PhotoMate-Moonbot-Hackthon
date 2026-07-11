from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.photo_agent.delivery import PhotoStore


def create_photo_router(store: PhotoStore) -> APIRouter:
    router = APIRouter()

    @router.get("/api/photos/{photo_id}", response_class=FileResponse)
    def get_photo(photo_id: str) -> FileResponse:
        path = store.resolve(photo_id)
        if path is None:
            raise HTTPException(status_code=404, detail="photo not found")
        return FileResponse(path, media_type="image/jpeg", filename=path.name)

    @router.get("/api/photos/{photo_id}/meta")
    def get_photo_metadata(photo_id: str, request: Request) -> dict[str, str]:
        path = store.resolve(photo_id)
        if path is None:
            raise HTTPException(status_code=404, detail="photo not found")
        return {
            "photo_id": photo_id,
            "photo_url": str(request.url_for("get_photo", photo_id=photo_id)),
        }

    @router.delete("/api/photos/{photo_id}")
    def delete_photo(photo_id: str) -> dict[str, str | bool]:
        if not store.delete(photo_id):
            raise HTTPException(status_code=404, detail="photo not found")
        return {"ok": True, "photo_id": photo_id}

    return router
