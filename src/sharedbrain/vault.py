"""Lectura del vault: notas humanas (solo lectura) y zona IA."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterator, Literal

import frontmatter

IGNORED_DIRS = {".obsidian", ".git", ".trash", ".log", "node_modules", "__pycache__"}

Origin = Literal["human", "ai"]
Scope = Literal["all", "human", "ai"]


class VaultError(Exception):
    pass


@dataclass
class Note:
    path: str  # ruta relativa al vault, en formato posix
    title: str
    body: str
    frontmatter: dict = field(default_factory=dict)
    origin: Origin = "human"

    @property
    def type(self) -> str | None:
        return self.frontmatter.get("type")

    @property
    def status(self) -> str | None:
        return self.frontmatter.get("status")


class Vault:
    """Acceso al vault. Toda ruta externa es relativa al root y se valida
    contra path traversal; la clasificación humano/IA se deriva del path."""

    def __init__(self, root: Path, ai_dir: str = "_ai") -> None:
        self.root = root.resolve()
        if not self.root.is_dir():
            raise VaultError(f"El vault no existe: {self.root}")
        self.ai_dir = ai_dir

    # --- rutas ---

    def resolve(self, rel_path: str) -> Path:
        abs_path = (self.root / rel_path).resolve()
        if not abs_path.is_relative_to(self.root):
            raise VaultError(f"Ruta fuera del vault: {rel_path}")
        return abs_path

    def relpath(self, abs_path: Path) -> str:
        return abs_path.relative_to(self.root).as_posix()

    def origin_of(self, rel_path: str) -> Origin:
        parts = PurePosixPath(rel_path).parts
        return "ai" if parts and parts[0] == self.ai_dir else "human"

    @property
    def ai_path(self) -> Path:
        return self.root / self.ai_dir

    # --- lectura ---

    def read(self, rel_path: str) -> Note:
        abs_path = self.resolve(rel_path)
        if not abs_path.is_file():
            raise VaultError(f"La nota no existe: {rel_path}")
        return self._parse(abs_path)

    def exists(self, rel_path: str) -> bool:
        try:
            return self.resolve(rel_path).is_file()
        except VaultError:
            return False

    def iter_notes(self, scope: Scope = "all") -> Iterator[Note]:
        for abs_path in self._iter_files(self.root):
            rel = self.relpath(abs_path)
            origin = self.origin_of(rel)
            if scope != "all" and origin != scope:
                continue
            try:
                yield self._parse(abs_path)
            except Exception:
                continue  # una nota corrupta no debe tumbar el escaneo

    def _iter_files(self, directory: Path) -> Iterator[Path]:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith(".") or entry.name in IGNORED_DIRS:
                continue
            if entry.is_dir():
                yield from self._iter_files(entry)
            elif entry.suffix.lower() == ".md":
                yield entry

    def _parse(self, abs_path: Path) -> Note:
        # utf-8-sig: tolera el BOM que añaden muchos editores en Windows
        post = frontmatter.loads(abs_path.read_text(encoding="utf-8-sig"))
        rel = self.relpath(abs_path)
        title = str(post.metadata.get("title") or abs_path.stem)
        return Note(
            path=rel,
            title=title,
            body=post.content,
            frontmatter=dict(post.metadata),
            origin=self.origin_of(rel),
        )
