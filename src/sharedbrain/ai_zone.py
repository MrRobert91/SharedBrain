"""Escritura controlada en la zona IA (_ai/).

Aquí se materializan las reglas de permisos: las escrituras de agentes y
pipelines pasan por esta clase, que (1) restringe el path a la zona IA,
(2) inyecta el frontmatter de trazabilidad aunque quien escribe no lo envíe,
(3) protege el perfil validado y (4) registra cada escritura en un log.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath

import frontmatter

from .vault import Vault, VaultError

AI_NOTE_TYPES = {"inference", "idea", "critique", "project-context", "pack", "note"}
STATUSES = {"draft", "reviewed", "validated", "rejected"}


class AIZoneError(Exception):
    pass


class AIZone:
    def __init__(self, vault: Vault, default_model: str | None = None) -> None:
        self.vault = vault
        self.default_model = default_model

    # --- API pública ---

    def create(
        self,
        rel_path: str,
        body: str,
        *,
        type: str = "note",
        sources: list[str] | None = None,
        extra_frontmatter: dict | None = None,
        model: str | None = None,
        overwrite: bool = False,
        actor: str = "unknown",
    ) -> str:
        abs_path = self._check_target(rel_path)
        if abs_path.exists() and not overwrite:
            raise AIZoneError(f"Ya existe: {rel_path} (usa update o overwrite=True)")
        if type not in AI_NOTE_TYPES:
            raise AIZoneError(f"type inválido: {type}. Válidos: {sorted(AI_NOTE_TYPES)}")
        self._guard_validated(abs_path, rel_path)

        today = date.today().isoformat()
        metadata: dict = {
            "origin": "ai",
            "type": type,
            "status": "draft",
            "created": today,
            "updated": today,
            "model": model or self.default_model or "unknown",
        }
        if sources:
            metadata["sources"] = sources
        if extra_frontmatter:
            # lo extra nunca pisa la trazabilidad
            metadata = {**extra_frontmatter, **metadata}

        abs_path.parent.mkdir(parents=True, exist_ok=True)
        self._dump(abs_path, metadata, body)
        self._log(actor, "create", rel_path)
        return rel_path

    def update(self, rel_path: str, body: str, *, actor: str = "unknown") -> str:
        """Actualiza el cuerpo de una nota IA existente conservando su frontmatter."""
        abs_path = self._check_target(rel_path)
        if not abs_path.is_file():
            raise AIZoneError(f"No existe: {rel_path} (usa create)")
        self._guard_validated(abs_path, rel_path)
        post = frontmatter.loads(abs_path.read_text(encoding="utf-8-sig"))
        metadata = dict(post.metadata)
        metadata["updated"] = date.today().isoformat()
        self._dump(abs_path, metadata, body)
        self._log(actor, "update", rel_path)
        return rel_path

    # --- reglas ---

    def _check_target(self, rel_path: str) -> Path:
        parts = PurePosixPath(rel_path).parts
        if not parts or parts[0] != self.vault.ai_dir:
            raise AIZoneError(
                f"Los agentes solo pueden escribir dentro de {self.vault.ai_dir}/. "
                f"Ruta rechazada: {rel_path}"
            )
        if not rel_path.endswith(".md"):
            raise AIZoneError(f"Solo se escriben archivos .md: {rel_path}")
        try:
            abs_path = self.vault.resolve(rel_path)
        except VaultError as e:
            raise AIZoneError(str(e)) from e
        # la ruta resuelta (sin ../) también debe quedar dentro de la zona IA
        if not abs_path.is_relative_to(self.vault.ai_path):
            raise AIZoneError(
                f"Los agentes solo pueden escribir dentro de {self.vault.ai_dir}/. "
                f"Ruta rechazada: {rel_path}"
            )
        return abs_path

    def _guard_validated(self, abs_path: Path, rel_path: str) -> None:
        """El contenido validado por el usuario nunca se sobreescribe
        automáticamente: la propuesta de cambio debe ir a _ai/inbox/."""
        if not abs_path.is_file():
            return
        status = frontmatter.loads(abs_path.read_text(encoding="utf-8-sig")).metadata.get("status")
        if status == "validated":
            raise AIZoneError(
                f"{rel_path} está validado por el usuario y no puede modificarse. "
                f"Escribe una propuesta en {self.vault.ai_dir}/inbox/ en su lugar."
            )

    # --- soporte ---

    def _dump(self, abs_path: Path, metadata: dict, body: str) -> None:
        post = frontmatter.Post(body, **metadata)
        abs_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")

    def _log(self, actor: str, action: str, rel_path: str) -> None:
        log_dir = self.vault.ai_path / ".log"
        log_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "path": rel_path,
        }
        with (log_dir / "writes.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
