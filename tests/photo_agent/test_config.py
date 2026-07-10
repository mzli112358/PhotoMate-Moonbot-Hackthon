from __future__ import annotations

from pathlib import Path

from app.photo_agent.config import load_runtime_config


def test_runtime_config_uses_yaml_and_environment_without_markdown_secret(
    tmp_path: Path, monkeypatch
) -> None:
    config_file = tmp_path / "app.yaml"
    config_file.write_text(
        """
photo_agent:
  mode: mock
  camera_index: 2
  workspace_host: yaml.example.com
  photo_dir: data/test-photos
  base_url: http://127.0.0.1:9000
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DASHSCOPE_API_KEY", "env-secret")
    monkeypatch.setenv("OMNI_MODEL", "env-model")
    monkeypatch.setenv("PHOTOMATE_PHOTO_AGENT__CAMERA_INDEX", "4")

    result = load_runtime_config(config_file=config_file, root_dir=tmp_path)

    assert result.api_key == "env-secret"
    assert result.model == "env-model"
    assert result.camera_index == 4
    assert result.workspace_host == "yaml.example.com"
    assert result.photo_dir == tmp_path / "data/test-photos"
