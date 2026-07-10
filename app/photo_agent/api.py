from __future__ import annotations

from fastapi import APIRouter, HTTPException
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

    return router
