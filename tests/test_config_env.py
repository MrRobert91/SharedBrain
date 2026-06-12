from pathlib import Path

import pytest

from sharedbrain.config import Config


def test_env_only_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)  # sin sharedbrain.config.yaml
    monkeypatch.setenv("SHAREDBRAIN_VAULT", str(tmp_path / "vault"))
    monkeypatch.setenv("SHAREDBRAIN_MODEL", "openrouter:anthropic/claude-sonnet-4.6")
    monkeypatch.setenv("SHAREDBRAIN_MODEL_CHEAP", "openrouter:google/gemini-flash")
    config = Config.load()
    assert config.vault == tmp_path / "vault"
    assert config.models.default == "openrouter:anthropic/claude-sonnet-4.6"
    assert config.models.for_tier("cheap") == "openrouter:google/gemini-flash"


def test_env_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "sharedbrain.config.yaml").write_text(
        f"vault: {(tmp_path / 'v').as_posix()}\nmodels:\n  default: anthropic:claude-fable-5\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SHAREDBRAIN_MODEL", "openai:gpt-5.2")
    config = Config.load()
    assert config.models.default == "openai:gpt-5.2"
    assert config.vault == tmp_path / "v"  # lo no-overrideado se respeta


def test_missing_everything_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHAREDBRAIN_VAULT", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # que no encuentre ~/.config
    with pytest.raises(FileNotFoundError):
        Config.load()
