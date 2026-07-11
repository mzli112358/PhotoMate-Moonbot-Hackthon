from __future__ import annotations

import asyncio

import pytest

from app.photo_agent import server as server_module


@pytest.mark.asyncio
async def test_photo_api_server_uses_base_url_and_stops_cleanly() -> None:
    photo_server_class = getattr(server_module, "PhotoApiServer", None)
    assert photo_server_class is not None, "PhotoApiServer is not implemented"

    class FakeServer:
        def __init__(self, config) -> None:
            self.config = config
            self.started = True
            self.should_exit = False

        async def serve(self) -> None:
            while not self.should_exit:
                await asyncio.sleep(0)

    made: list[FakeServer] = []

    def factory(config):
        server = FakeServer(config)
        made.append(server)
        return server

    server = photo_server_class(
        "http://127.0.0.1:8123",
        app=object(),
        server_factory=factory,
        startup_timeout=0.2,
    )

    await server.start()
    await server.stop()

    assert made[0].config.host == "127.0.0.1"
    assert made[0].config.port == 8123
    assert made[0].should_exit is True
