from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import sys
from typing import Callable

LOGGER = logging.getLogger("photomate.photo_agent.fallback")


class NullFallbackNotifier:
    async def notify(self, message: str) -> None:
        LOGGER.warning("fallback_notification", extra={"message_text": message, "audible": False})


class SystemFallbackNotifier:
    """Best-effort local speech fallback using an installed OS speech command."""

    def __init__(
        self,
        *,
        command: str | None = None,
        command_runner: Callable[..., object] = subprocess.run,
    ) -> None:
        if command is None:
            command = "/usr/bin/say" if sys.platform == "darwin" else shutil.which("espeak")
        self.command = command
        self.command_runner = command_runner

    async def notify(self, message: str) -> None:
        audible = bool(self.command)
        LOGGER.warning("fallback_notification", extra={"message_text": message, "audible": audible})
        if self.command:
            await asyncio.to_thread(
                self.command_runner,
                [self.command, message],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
