"""Pipeline de paquetes de contexto: compilar lo mínimo necesario para una tarea."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..ai_zone import AIZone
from ..agents import build_agent
from ..config import Config
from ..ideas import slugify
from ..vault import Vault
from .context import notes_dump, profile_context, relevant_notes

PACK_SYSTEM = """\
Eres el compilador de paquetes de contexto de SharedBrain. Recibes la
descripción de una tarea, el perfil del usuario y notas relevantes. Produces
un único documento Markdown AUTOCONTENIDO con todo lo que un agente necesita
para hacer bien esa tarea — y nada más.

Reglas:
1. Menos es más: incluye solo lo que cambia cómo se ejecuta la tarea.
   Un paquete inflado es peor que uno corto.
2. Estructura fija: Objetivo de la tarea / Contexto del usuario relevante /
   Contexto específico / Instrucciones para el agente / Fuentes.
3. Las instrucciones deben ser operativas (qué hacer, qué evitar, qué estilo).
4. En Fuentes lista las rutas de las notas usadas.
5. Escribe en español.
"""


class Pack(BaseModel):
    title: str
    markdown: str = Field(description="El paquete completo, autocontenido")
    sources: list[str]


async def create_pack(config: Config, task: str) -> str:
    """Compila un paquete de contexto para la tarea descrita. Devuelve la ruta."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)
    notes = relevant_notes(vault, task)

    agent = build_agent(config.models.default, Pack, PACK_SYSTEM)
    result = await agent.run(
        f"## Tarea\n{task}\n\n"
        f"## Perfil del usuario\n{profile_context(vault)}\n\n"
        f"## Notas relevantes\n{notes_dump(notes)}"
    )
    pack = result.output
    rel = f"{config.ai_dir}/packs/{slugify(pack.title)}.md"
    ai_zone.create(
        rel, pack.markdown.strip() + "\n", type="pack", sources=pack.sources,
        extra_frontmatter={"title": pack.title, "task": task},
        overwrite=True, actor="pipeline:packs.create",
    )
    return rel
