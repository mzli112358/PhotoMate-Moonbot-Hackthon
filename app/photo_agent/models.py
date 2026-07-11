from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class State(str, Enum):
    IDLE = "S0"
    DETECT_INTENT = "S1"
    ASK_INTENT = "S2"
    POSE_GUIDANCE = "S3"
    REVIEW = "S5"
    DELIVER = "S6"


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


@dataclass
class PoseGoal:
    goal_id: str
    description: str
    success_criteria: list[str] = field(default_factory=list)
    status: str = "active"


@dataclass
class PoseContext:
    episode_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    revision: int = 0
    logical_turn: int = 0
    active_goal: PoseGoal | None = None
    goal_history: list[PoseGoal] = field(default_factory=list)
    progress: str = "not_started"
    last_visual_observation: str = ""
    last_user_feedback_summary: str = ""
    last_guidance_intent: str = ""
    last_spoken_text: str = ""
    completion_reason: str | None = None
    processed_call_ids: set[str] = field(default_factory=set, repr=False)

    def snapshot_for_prompt(self) -> str:
        payload = {
            "episode_id": self.episode_id,
            "revision": self.revision,
            "logical_turn": self.logical_turn,
            "active_goal": (
                {
                    "goal_id": self.active_goal.goal_id,
                    "description": self.active_goal.description,
                    "success_criteria": self.active_goal.success_criteria,
                    "status": self.active_goal.status,
                }
                if self.active_goal
                else None
            ),
            "goal_history": [
                {
                    "goal_id": goal.goal_id,
                    "description": goal.description,
                    "status": goal.status,
                }
                for goal in self.goal_history[-3:]
            ],
            "progress": self.progress,
            "last_visual_observation": self.last_visual_observation,
            "last_user_feedback_summary": self.last_user_feedback_summary,
            "last_guidance_intent": self.last_guidance_intent,
            "last_spoken_text": self.last_spoken_text,
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


@dataclass
class PoseTurnState:
    source: str
    phase: str = "assessing"
    tool_result_received: bool = False
    pending_capture: bool = False
    capture_after_speech: bool = False
    pending_tool_submit: tuple[str, dict[str, Any]] | None = None
    assessment_response_id: str | None = None
    capture_response_id: str | None = None
    speech_response_id: str | None = None
    post_capture_speech: bool = False
    speech_retry_used: bool = False


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
    pose_context: PoseContext | None = None
    pose_turn: PoseTurnState | None = None
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
