"""Lifecycle wrapper for the local photo HTTP server."""

from __future__ import annotations

import asyncio
from typing import Any, Callable
from urllib.parse import urlparse


class PhotoApiServer:
    def __init__(
        self,
        base_url: str,
        *,
        app: Any | None = None,
        server_factory: Callable[[Any], Any] | None = None,
        startup_timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url
        self.app = app
        self.server_factory = server_factory
        self.startup_timeout = startup_timeout
        self.server: Any | None = None
        self.task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        import uvicorn

        if self.app is None:
            from app.main import app

            self.app = app
        parsed = urlparse(self.base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 8000
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        factory = self.server_factory or uvicorn.Server
        self.server = factory(config)
        self.task = asyncio.create_task(self.server.serve(), name="photo-api")
        deadline = asyncio.get_running_loop().time() + self.startup_timeout
        while not getattr(self.server, "started", False):
            if self.task.done():
                error = self.task.exception()
                raise RuntimeError(f"photo API failed to start: {error}")
            if asyncio.get_running_loop().time() >= deadline:
                await self.stop()
                raise TimeoutError(f"photo API startup timed out after {self.startup_timeout}s")
            await asyncio.sleep(0.01)

    async def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True
        if self.task is not None:
            try:
                await asyncio.wait_for(self.task, timeout=5.0)
            except TimeoutError:
                self.task.cancel()
                await asyncio.gather(self.task, return_exceptions=True)
        self.server = None
        self.task = None

    async def __aenter__(self) -> "PhotoApiServer":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.stop()
