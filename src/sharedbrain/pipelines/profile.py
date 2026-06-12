"""Pipeline `profile infer`: infiere el perfil personal desde las notas humanas.

Plano activo: usa el LLM configurado por el usuario (pydantic-ai). La salida
son archivos en _ai/profile/ como `draft`, con confidence y sources. Si una
sección ya está `validated`, la propuesta va a _ai/inbox/ — nunca se pisa.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from ..ai_zone import AIZone, AIZoneError
from ..config import Config
from ..vault import Note, Vault

# Presupuesto de caracteres de notas que se envían al modelo (~25k tokens).
CONTEXT_CHAR_BUDGET = 100_000

SECTIONS = ("identidad", "objetivos", "valores", "patrones")

SYSTEM_PROMPT = """\
Eres el motor de inferencia de perfil de SharedBrain, una capa de contexto
personal. Recibirás un volcado de notas personales en bruto (posiblemente
desordenadas, incompletas o contradictorias) de su autor.

Tu tarea: inferir un perfil personal honesto y útil, dividido en secciones:
- identidad: quién es, habilidades, en qué trabaja, qué temas le interesan.
- objetivos: qué persigue, metas declaradas e implícitas.
- valores: qué le importa, restricciones personales/profesionales.
- patrones: patrones recurrentes en sus ideas, proyectos y forma de trabajar
  (tipo de soluciones que prefiere, estilo de ejecución, frameworks).

Reglas estrictas:
1. Toda afirmación debe estar anclada en las notas. Cita en `sources` las
   rutas de las notas que la sustentan. Si no hay evidencia, no lo afirmes.
2. Son inferencias, no verdades: asigna `confidence` con criterio. Marca low
   cuando extrapolas de poca evidencia.
3. Calidad sobre cantidad: mejor pocas afirmaciones útiles que un perfil
   largo y genérico que podría ser de cualquiera.
4. Escribe en español, en Markdown, en segunda persona ("Prefieres...").
5. Si las notas no dan para una sección, devuélvela con un aviso explícito
   de evidencia insuficiente en lugar de inventar.
"""


class ProfileSection(BaseModel):
    name: Literal["identidad", "objetivos", "valores", "patrones"]
    markdown: str = Field(description="Contenido de la sección en Markdown")
    confidence: Literal["high", "medium", "low"]
    sources: list[str] = Field(description="Rutas de notas que sustentan la sección")


class ProfileInference(BaseModel):
    sections: list[ProfileSection]


def _select_notes(vault: Vault, budget: int = CONTEXT_CHAR_BUDGET) -> list[Note]:
    """Selección MVP: notas humanas más recientes hasta agotar presupuesto."""
    notes = list(vault.iter_notes("human"))
    notes.sort(key=lambda n: vault.resolve(n.path).stat().st_mtime, reverse=True)
    selected, used = [], 0
    for note in notes:
        size = len(note.body)
        if size < 20:  # notas vacías o casi vacías no aportan
            continue
        if used + size > budget:
            continue
        selected.append(note)
        used += size
    return selected


def _build_prompt(notes: list[Note]) -> str:
    chunks = [f"<<< NOTA: {n.path} >>>\n{n.body.strip()}" for n in notes]
    return (
        f"Notas personales del usuario ({len(notes)} notas):\n\n"
        + "\n\n".join(chunks)
        + "\n\nInfiere el perfil personal."
    )


async def infer_profile(config: Config) -> list[str]:
    """Ejecuta la inferencia y escribe el perfil. Devuelve las rutas escritas."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)
    notes = _select_notes(vault)
    if not notes:
        raise RuntimeError("No hay notas humanas con contenido en el vault.")

    agent = Agent(
        config.models.default,
        output_type=ProfileInference,
        system_prompt=SYSTEM_PROMPT,
    )
    result = await agent.run(_build_prompt(notes))

    written: list[str] = []
    for section in result.output.sections:
        target = f"{config.ai_dir}/profile/{section.name}.md"
        fallback = f"{config.ai_dir}/inbox/propuesta-perfil-{section.name}.md"
        body = section.markdown.strip() + "\n"
        fm = {"confidence": section.confidence}
        try:
            ai_zone.create(
                target, body, type="inference", sources=section.sources,
                extra_frontmatter=fm, overwrite=True, actor="pipeline:profile",
            )
            written.append(target)
        except AIZoneError:
            # sección validada por el usuario → propuesta a inbox
            ai_zone.create(
                fallback, body, type="inference", sources=section.sources,
                extra_frontmatter=fm, overwrite=True, actor="pipeline:profile",
            )
            written.append(fallback)
    return written
