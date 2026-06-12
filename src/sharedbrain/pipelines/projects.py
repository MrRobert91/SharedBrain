"""Pipelines de proyectos: sync de repos y promoción idea → proyecto."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..ai_zone import AIZone
from ..agents import build_agent
from ..config import Config
from ..ideas import slugify
from ..repos import gather
from ..vault import Vault
from .context import profile_context

SYNC_SYSTEM = """\
Eres el analista de proyectos de SharedBrain. Recibes el contexto en bruto de
un repositorio (estructura, commits, issues, README) y produces el contexto
destilado del proyecto para que el usuario y sus agentes sepan en qué estado
está y qué hacer a continuación.

Reglas:
- Sé concreto: estado REAL según el código y los commits, no según el README.
- "Qué falta" debe ser accionable, no genérico.
- `instrucciones_agentes` son instrucciones operativas para un agente de
  código que vaya a trabajar en el repo (stack, convenciones, dónde está qué).
- Escribe en español.
"""

PROMOTE_SYSTEM = """\
Eres el arquitecto de arranque de SharedBrain. Recibes una ficha de idea ya
evaluada y el perfil del usuario. Tu trabajo: convertirla en un proyecto
ejecutable — especificación inicial, roadmap por fases que empiece por el MVP
mínimo de la ficha, e instrucciones para el agente que lo va a construir.

Reglas:
- El roadmap fase 1 debe ser el MVP mínimo de la ficha, no más.
- Las instrucciones para agentes deben bastar para que un agente de código
  empiece a trabajar sin hacer preguntas obvias.
- Respeta las preferencias del perfil (stack, estilo de ejecución, valores).
- Escribe en español.
"""


class ProjectContext(BaseModel):
    descripcion: str
    objetivo_actual: str
    estado: str = Field(description="Estado real de desarrollo según el repo")
    que_falta: str = Field(description="Qué falta para MVP/demo/producto, accionable")
    roadmap: str = Field(description="Roadmap propuesto en Markdown")
    decisiones: str = Field(description="Decisiones técnicas visibles en el repo")
    instrucciones_agentes: str
    ideas_mejora: str = Field(description="Ideas para mejorar el proyecto o contenido derivable")


class ProjectSpec(BaseModel):
    nombre: str
    contexto: str = Field(description="context.md: descripción, objetivo, alcance, restricciones")
    roadmap: str = Field(description="roadmap.md: fases empezando por el MVP mínimo")
    instrucciones_agentes: str = Field(description="agentes.md: brief operativo para un agente de código")


def _write_project(ai_zone: AIZone, ai_dir: str, slug: str, files: dict[str, str],
                   sources: list[str], actor: str) -> list[str]:
    written = []
    for name, body in files.items():
        rel = f"{ai_dir}/projects/{slug}/{name}"
        ai_zone.create(rel, body.strip() + "\n", type="project-context",
                       sources=sources, overwrite=True, actor=actor)
        written.append(rel)
    return written


async def sync_project(config: Config, origin: str, slug: str | None = None) -> list[str]:
    """Extrae contexto del repo y escribe/actualiza _ai/projects/<slug>/."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)
    repo = gather(origin, slug)

    agent = build_agent(config.models.default, ProjectContext, SYNC_SYSTEM)
    result = await agent.run(
        f"## Perfil del usuario (para enfocar 'qué falta' e ideas)\n{profile_context(vault)}\n\n"
        f"## Contexto en bruto del repositorio\n{repo.dump()}"
    )
    out = result.output
    source = f"repo:{repo.origin}"
    files = {
        "context.md": (
            f"# {repo.slug}\n\n## Descripción\n{out.descripcion}\n\n"
            f"## Objetivo actual\n{out.objetivo_actual}\n\n## Estado\n{out.estado}\n\n"
            f"## Qué falta\n{out.que_falta}\n\n## Ideas de mejora\n{out.ideas_mejora}"
        ),
        "roadmap.md": out.roadmap,
        "decisiones.md": out.decisiones,
        "agentes.md": out.instrucciones_agentes,
    }
    return _write_project(ai_zone, config.ai_dir, repo.slug, files, [source], "pipeline:project.sync")


async def promote_idea(config: Config, idea_slug: str) -> list[str]:
    """Convierte una ficha de idea en especificaciones de proyecto."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)
    idea_rel = f"{config.ai_dir}/ideas/{idea_slug}.md"
    idea = vault.read(idea_rel)

    agent = build_agent(config.models.default, ProjectSpec, PROMOTE_SYSTEM)
    result = await agent.run(
        f"## Perfil del usuario\n{profile_context(vault)}\n\n"
        f"## Ficha de idea a promocionar\n{idea.body}"
    )
    spec = result.output
    slug = slugify(spec.nombre) or idea_slug
    files = {
        "context.md": spec.contexto,
        "roadmap.md": spec.roadmap,
        "agentes.md": spec.instrucciones_agentes,
    }
    return _write_project(ai_zone, config.ai_dir, slug, files, [idea_rel], "pipeline:project.promote")
