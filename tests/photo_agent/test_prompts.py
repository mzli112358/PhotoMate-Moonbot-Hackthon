from __future__ import annotations

from pathlib import Path

import pytest

from app.photo_agent.prompts import (
    DEFAULT_PROMPTS,
    PromptConflictError,
    PromptRegistry,
    PromptValidationError,
)


def make_registry(tmp_path: Path, *, max_history: int = 20) -> PromptRegistry:
    return PromptRegistry(
        config_path=tmp_path / "photo_agent_prompts.yaml",
        history_dir=tmp_path / "history",
        max_history=max_history,
    )


def test_missing_config_loads_complete_defaults_without_writing(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    snapshot = registry.snapshot()

    assert snapshot.prompts == DEFAULT_PROMPTS
    assert "system.base" in snapshot.prompts
    assert "action.S2.ask_initial" in snapshot.prompts
    assert "action.S5.ask_review" in snapshot.prompts
    assert not (tmp_path / "photo_agent_prompts.yaml").exists()


def test_save_is_persistent_and_requires_expected_version(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    before = registry.snapshot()

    saved = registry.save(
        {"action.S3.guidance": "请向左一步。"},
        expected_version=before.version,
    )

    assert saved.version != before.version
    assert saved.prompts["action.S3.guidance"] == "请向左一步。"
    reloaded = make_registry(tmp_path).snapshot()
    assert reloaded == saved

    with pytest.raises(PromptConflictError):
        registry.save(
            {"action.S3.guidance": "这是过期覆盖。"},
            expected_version=before.version,
        )


def test_save_rejects_unknown_or_empty_prompts(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    version = registry.snapshot().version

    with pytest.raises(PromptValidationError, match="unknown prompt"):
        registry.save({"action.S9.unknown": "x"}, expected_version=version)

    with pytest.raises(PromptValidationError, match="cannot be empty"):
        registry.save({"system.base": "   "}, expected_version=version)


def test_history_is_bounded_and_rollback_creates_a_new_version(tmp_path: Path) -> None:
    registry = make_registry(tmp_path, max_history=2)
    original = registry.snapshot()
    first = registry.save(
        {"action.S2.ask_initial": "版本一"}, expected_version=original.version
    )
    second = registry.save(
        {"action.S2.ask_initial": "版本二"}, expected_version=first.version
    )
    third = registry.save(
        {"action.S2.ask_initial": "版本三"}, expected_version=second.version
    )

    history = registry.history()

    assert [item.version for item in history] == [third.version, second.version, first.version]
    assert original.version not in {item.version for item in history}

    rolled_back = registry.rollback(first.version, expected_version=third.version)
    assert rolled_back.version not in {first.version, third.version}
    assert rolled_back.prompts["action.S2.ask_initial"] == "版本一"


def test_render_requires_declared_template_values(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)

    assert registry.render("action.S3.quality_failed", quality_reason="闭眼") == (
        "照片质检未通过：闭眼，请简短提示重拍。"
    )

    with pytest.raises(PromptValidationError, match="missing template value"):
        registry.render("action.S3.quality_failed")


def test_diff_reports_only_changed_prompt_values(tmp_path: Path) -> None:
    registry = make_registry(tmp_path)
    original = registry.snapshot()
    saved = registry.save(
        {
            "action.S2.ask_initial": "新询问",
            "action.S5.ask_review": "新复核",
        },
        expected_version=original.version,
    )

    diff = registry.diff(original.version, saved.version)

    assert diff == {
        "action.S2.ask_initial": {"before": DEFAULT_PROMPTS["action.S2.ask_initial"], "after": "新询问"},
        "action.S5.ask_review": {"before": DEFAULT_PROMPTS["action.S5.ask_review"], "after": "新复核"},
    }
