"""Carga de configuración (sharedbrain.config.yaml)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

CONFIG_FILENAME = "sharedbrain.config.yaml"
CONFIG_ENV_VAR = "SHAREDBRAIN_CONFIG"


class ModelsConfig(BaseModel):
    # Formato pydantic-ai: "<provider>:<model>", p. ej. "anthropic:claude-fable-5"
    default: str = "anthropic:claude-fable-5"
    cheap: str | None = None

    def for_tier(self, tier: str) -> str:
        if tier == "cheap" and self.cheap:
            return self.cheap
        return self.default


class ProjectConfig(BaseModel):
    slug: str
    repo: str


class Config(BaseModel):
    vault: Path
    ai_dir: str = "_ai"
    db: Path = Path("sharedbrain.sqlite3")  # estado operativo (actividad del panel)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    projects: list[ProjectConfig] = Field(default_factory=list)

    @field_validator("vault", mode="before")
    @classmethod
    def _expand(cls, v: object) -> object:
        if isinstance(v, str):
            return Path(v).expanduser()
        return v

    @property
    def ai_path(self) -> Path:
        return self.vault / self.ai_dir

    @classmethod
    def find_config_file(cls, explicit: Path | None = None) -> Path | None:
        """Orden: ruta explícita > $SHAREDBRAIN_CONFIG > cwd > ~/.config/sharedbrain/."""
        candidates: list[Path] = []
        if explicit:
            candidates.append(explicit)
        if env := os.environ.get(CONFIG_ENV_VAR):
            candidates.append(Path(env))
        candidates.append(Path.cwd() / CONFIG_FILENAME)
        candidates.append(Path.home() / ".config" / "sharedbrain" / CONFIG_FILENAME)
        for path in candidates:
            if path.is_file():
                return path
        return None

    @classmethod
    def load(cls, explicit: Path | None = None) -> Config:
        path = cls.find_config_file(explicit)
        if path is None:
            raise FileNotFoundError(
                f"No se encontró {CONFIG_FILENAME}. Crea uno con `sharedbrain init <vault>` "
                f"o define {CONFIG_ENV_VAR}."
            )
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)
