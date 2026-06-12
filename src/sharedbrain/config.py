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
    # repo git del vault (owner/repo o URL); si se define, el vault se clona
    # en el primer arranque y `vault sync` lo mantiene al día
    vault_repo: str | None = None
    vault_branch: str | None = None
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
        """Carga el YAML y aplica overrides por variables de entorno.

        Las variables de entorno permiten desplegar sin archivo de config
        (p. ej. un contenedor suelto en Sliplane): con SHAREDBRAIN_VAULT
        definido, el YAML es opcional.
        """
        path = cls.find_config_file(explicit)
        data: dict = {}
        if path is not None:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        env = os.environ
        if vault := env.get("SHAREDBRAIN_VAULT"):
            data["vault"] = vault
        if vault_repo := env.get("SHAREDBRAIN_VAULT_REPO"):
            data["vault_repo"] = vault_repo
        if vault_branch := env.get("SHAREDBRAIN_VAULT_BRANCH"):
            data["vault_branch"] = vault_branch
        if ai_dir := env.get("SHAREDBRAIN_AI_DIR"):
            data["ai_dir"] = ai_dir
        if db := env.get("SHAREDBRAIN_DB"):
            data["db"] = db
        models = data.setdefault("models", {})
        if isinstance(models, dict):
            if model := env.get("SHAREDBRAIN_MODEL"):
                models["default"] = model
            if cheap := env.get("SHAREDBRAIN_MODEL_CHEAP"):
                models["cheap"] = cheap

        if "vault" not in data:
            raise FileNotFoundError(
                f"No se encontró {CONFIG_FILENAME} ni la variable SHAREDBRAIN_VAULT. "
                f"Crea la config con `sharedbrain init <vault>` o define SHAREDBRAIN_VAULT."
            )
        return cls.model_validate(data)
