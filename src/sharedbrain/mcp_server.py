"""Servidor MCP: la API de contexto para agentes (plano pasivo, sin LLM)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastmcp import FastMCP
from pydantic import Field

from .ai_zone import AIZone, AIZoneError
from .config import Config
from .ideas import IdeaCard, render_idea, slugify
from .search import search
from .vault import Vault, VaultError

INSTRUCTIONS = """\
SharedBrain es la capa de contexto personal del usuario, construida sobre su
vault de Obsidian. Reglas:
- Las notas humanas son SOLO LECTURA. Toda escritura va a la zona IA (_ai/)
  y queda marcada como generada por IA.
- El contenido con status "validated" tiene más peso que el "draft".
- No generes ruido: escribe solo notas que ayuden a decidir o ejecutar.
"""


def build_server(config: Config) -> FastMCP:
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault)
    mcp = FastMCP("sharedbrain", instructions=INSTRUCTIONS)

    @mcp.tool
    def search_context(
        query: str,
        scope: Annotated[
            Literal["all", "human", "ai"],
            Field(description="Buscar en todo el vault, solo notas humanas o solo zona IA"),
        ] = "all",
        limit: int = 10,
    ) -> list[dict]:
        """Busca notas relevantes en el vault personal (búsqueda léxica)."""
        return [
            {
                "path": r.note.path,
                "title": r.note.title,
                "origin": r.note.origin,
                "type": r.note.type,
                "status": r.note.status,
                "score": r.score,
                "snippet": r.snippet,
            }
            for r in search(vault, query, scope=scope, limit=limit)
        ]

    @mcp.tool
    def read_note(path: str) -> dict:
        """Lee una nota completa del vault por su ruta relativa."""
        try:
            note = vault.read(path)
        except VaultError as e:
            raise ValueError(str(e)) from e
        return {
            "path": note.path,
            "title": note.title,
            "origin": note.origin,
            "frontmatter": note.frontmatter,
            "body": note.body,
        }

    @mcp.tool
    def get_profile(
        section: Annotated[
            str | None,
            Field(description="identidad | objetivos | valores | patrones (None = todas)"),
        ] = None,
    ) -> list[dict]:
        """Devuelve el perfil personal inferido del usuario (zona IA, revisable)."""
        profile_dir = vault.ai_path / "profile"
        if not profile_dir.is_dir():
            return []
        sections = []
        for f in sorted(profile_dir.glob("*.md")):
            if section and f.stem != section:
                continue
            note = vault.read(vault.relpath(f))
            sections.append(
                {
                    "section": f.stem,
                    "status": note.status,
                    "confidence": note.frontmatter.get("confidence"),
                    "body": note.body,
                }
            )
        return sections

    @mcp.tool
    def list_ideas(
        verdict: str | None = None,
        goal: str | None = None,
    ) -> list[dict]:
        """Lista las fichas de ideas de proyecto con sus metadatos."""
        ideas_dir = vault.ai_path / "ideas"
        if not ideas_dir.is_dir():
            return []
        out = []
        for f in sorted(ideas_dir.glob("*.md")):
            note = vault.read(vault.relpath(f))
            fm = note.frontmatter
            if verdict and fm.get("verdict") != verdict:
                continue
            if goal and fm.get("goal") != goal:
                continue
            out.append(
                {
                    "path": note.path,
                    "title": note.title,
                    "status": note.status,
                    **{
                        k: fm.get(k)
                        for k in ("goal", "horizon", "effort", "impact", "fit", "verdict")
                    },
                }
            )
        return out

    @mcp.tool
    def create_ai_note(
        path: Annotated[str, Field(description="Ruta relativa dentro de la zona IA, p. ej. _ai/inbox/analisis.md")],
        content: str,
        type: Annotated[
            Literal["inference", "idea", "critique", "project-context", "pack", "note"],
            Field(description="Tipo de nota IA"),
        ] = "note",
        sources: Annotated[
            list[str] | None,
            Field(description="Rutas de las notas de las que se deriva (trazabilidad)"),
        ] = None,
    ) -> str:
        """Crea una nota generada por IA en la zona IA del vault. El frontmatter
        de trazabilidad (origin, status, fechas) se inyecta automáticamente."""
        try:
            return ai_zone.create(path, content, type=type, sources=sources, actor="mcp")
        except AIZoneError as e:
            raise ValueError(str(e)) from e

    @mcp.tool
    def update_ai_note(path: str, content: str) -> str:
        """Actualiza el cuerpo de una nota IA existente (conserva frontmatter).
        Las notas validadas por el usuario no pueden modificarse."""
        try:
            return ai_zone.update(path, content, actor="mcp")
        except AIZoneError as e:
            raise ValueError(str(e)) from e

    @mcp.tool
    def upsert_idea(idea: IdeaCard) -> str:
        """Crea o actualiza una ficha de idea de proyecto completa. Usa esto
        (no create_ai_note) para ideas: valida las secciones y el frontmatter."""
        slug = slugify(idea.title)
        body, fm = render_idea(idea)
        try:
            return ai_zone.create(
                f"{config.ai_dir}/ideas/{slug}.md", body, type="idea",
                sources=idea.sources, extra_frontmatter=fm, overwrite=True, actor="mcp",
            )
        except AIZoneError as e:
            raise ValueError(str(e)) from e

    @mcp.tool
    def list_packs() -> list[dict]:
        """Lista los paquetes de contexto disponibles."""
        packs_dir = vault.ai_path / "packs"
        if not packs_dir.is_dir():
            return []
        out = []
        for f in sorted(packs_dir.glob("*.md")):
            note = vault.read(vault.relpath(f))
            out.append({"slug": f.stem, "title": note.title,
                        "task": note.frontmatter.get("task"), "status": note.status})
        return out

    @mcp.tool
    def get_pack(slug: str) -> str:
        """Devuelve un paquete de contexto autocontenido para una tarea."""
        try:
            return vault.read(f"{config.ai_dir}/packs/{slug}.md").body
        except VaultError as e:
            raise ValueError(str(e)) from e

    @mcp.tool
    def list_projects() -> list[dict]:
        """Lista los proyectos con contexto en la zona IA."""
        projects_dir = vault.ai_path / "projects"
        if not projects_dir.is_dir():
            return []
        out = []
        for d in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
            docs = [f.stem for f in d.glob("*.md")]
            out.append({"slug": d.name, "docs": docs})
        return out

    @mcp.tool
    def get_project_context(
        project: str,
        doc: Annotated[
            str, Field(description="context | roadmap | decisiones | agentes")
        ] = "context",
    ) -> str:
        """Devuelve un documento de contexto de un proyecto (estado, roadmap,
        decisiones o instrucciones para agentes)."""
        try:
            return vault.read(f"{config.ai_dir}/projects/{project}/{doc}.md").body
        except VaultError as e:
            raise ValueError(str(e)) from e

    @mcp.tool
    def update_project_context(project: str, doc: str, content: str) -> str:
        """Actualiza (o crea) un documento de contexto de proyecto."""
        rel = f"{config.ai_dir}/projects/{project}/{doc}.md"
        try:
            if vault.exists(rel):
                return ai_zone.update(rel, content, actor="mcp")
            return ai_zone.create(rel, content, type="project-context", actor="mcp")
        except AIZoneError as e:
            raise ValueError(str(e)) from e

    return mcp
