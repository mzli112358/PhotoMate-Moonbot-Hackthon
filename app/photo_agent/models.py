from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class State(str, Enum):
    IDLE = "S0"
    DETECT_INTENT = "S1"
    ASK_INTENT = "S2"
    POSE_GUIDANCE = "S3"
    SHOOT = "S4"
    REVIEW = "S5"
    DELIVER = "S6"


class UserIntent(str, Enum):
    ACCEPT = "accept"
    DECLINE = "decline"
    READY = "ready"
    SATISFIED = "satisfied"
    RETAKE = "retake"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class WakeSignal:
    person_present: bool
    dwell_seconds: float
    facing_robot: bool

    def is_awake(self, dwell_threshold: float = 3.0) -> bool:
        return self.person_present and self.facing_robot and self.dwell_seconds >= dwell_threshold


@dataclass(frozen=True)
class GuidanceTurn:
    ts: float
    prompt_source: str
    text: str = ""


@dataclass(frozen=True)
class CaptureResult:
    photo_id: str
    path: Path
    ok: bool
    frame: Any | None = None
    error: str | None = None


@dataclass(frozen=True)
class QualityResult:
    face_in_frame: bool
    eyes_open: bool
    sharp: bool
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.face_in_frame and self.eyes_open and self.sharp


@dataclass(frozen=True)
class DeliveryResult:
    photo_id: str
    photo_url: str
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    call_id: str


@dataclass
class SessionContext:
    state: State = State.IDLE
    session_id: str | None = None
    photo_id: str | None = None
    photo_path: Path | None = None
    photo_url: str | None = None
    guidance_turns: list[GuidanceTurn] = field(default_factory=list)
    response_in_flight: bool = False
    retake_count: int = 0
    ask_timeout_count: int = 0
    session_started_at: float = 0.0
    guidance_interval_s: float = 5.0
    max_guidance_turns: int = 8
    max_retake: int = 2

    def reset(self) -> None:
        interval = self.guidance_interval_s
        max_turns = self.max_guidance_turns
        max_retake = self.max_retake
        self.__dict__.update(
            SessionContext(
                guidance_interval_s=interval,
                max_guidance_turns=max_turns,
                max_retake=max_retake,
            ).__dict__
        )
