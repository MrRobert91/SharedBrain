"""Pipelines de ideas: generar, criticar y comparar (plano activo, usa LLM)."""

from __future__ import annotations

import frontmatter
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from ..ai_zone import AIZone
from ..config import Config
from ..ideas import (
    IdeaCard,
    IdeaCritique,
    list_idea_notes,
    render_critique,
    render_idea,
    replace_section,
    slugify,
)
from ..vault import Vault
from .context import notes_dump, profile_context, relevant_notes

GENERATE_SYSTEM = """\
Eres el generador de ideas de SharedBrain. Tu trabajo NO es listar ideas
genéricas: es proponer proyectos que solo tienen sentido para ESTE usuario,
anclados en su perfil y sus notas.

Reglas estrictas:
1. Las ideas deben servir a los OBJETIVOS ACTUALES del usuario (sección
   Perfil/objetivos). Si una idea no conecta con un objetivo, descártala.
2. En `encaje` y `sources` cita las notas y partes del perfil concretas que
   sustentan la idea. Si no puedes anclar una idea en el contexto, no la
   propongas: di menos ideas antes que rellenar con genéricas.
3. Sé honesto en effort/impact/fit; no infles las puntuaciones.
4. `mvp_minimo` debe ser realmente mínimo: lo más pequeño que valida la idea.
5. `criterios_decision` debe incluir qué comprobar ANTES de empezar.
6. Escribe en español.
"""

CRITIQUE_SYSTEM = """\
Eres el sparring intelectual de SharedBrain. Recibes una ficha de idea y el
perfil del usuario. Tu trabajo es challengear la idea de forma constructiva:
encontrar debilidades, contradicciones con el perfil, riesgos y supuestos sin
validar — y proponer la versión mejor o más pequeña.

Sé directo y específico. Una crítica que solo dice "depende" no sirve.
Si la idea es buena, dilo y explica por qué; no inventes pegas. Si es mala
para los objetivos actuales del usuario, di "descartar" sin miedo.
Escribe en español.
"""

COMPARE_SYSTEM = """\
Eres el priorizador de SharedBrain. Recibes varias fichas de idea y el perfil
del usuario (sus objetivos actuales van primero). Produce un ranking razonado:
qué hacer primero y por qué, qué aparcar, qué descartar. El criterio principal
es: ¿qué acerca más al usuario a sus objetivos actuales con el menor esfuerzo?
Escribe en español.
"""


class IdeaBatch(BaseModel):
    ideas: list[IdeaCard]


class Ranking(BaseModel):
    markdown: str = Field(description="Ranking razonado en Markdown: orden, por qué, y siguiente paso para la primera")


def _agent(config: Config, output_type: type, system: str) -> Agent:
    return Agent(config.models.default, output_type=output_type, system_prompt=system)


async def generate_ideas(
    config: Config,
    *,
    goal: str | None = None,
    horizon: str | None = None,
    from_note: str | None = None,
    n: int = 5,
) -> list[str]:
    """Genera N fichas de idea ancladas en perfil + notas. Devuelve rutas escritas."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)

    criteria = []
    if goal:
        criteria.append(f"- Objetivo de las ideas: {goal}")
    if horizon:
        criteria.append(f"- Horizonte: proyectos de plazo {horizon}")
    query = " ".join(filter(None, [goal, horizon])) or "proyectos ideas objetivos"
    notes = relevant_notes(vault, query)
    base = ""
    if from_note:
        note = vault.read(from_note)
        base = f"\n## Idea de partida (desarrollar/derivar de aquí)\n<<< {note.path} >>>\n{note.body}\n"
        criteria.append(f"- Trabaja sobre la idea ya existente en la nota {note.path}")

    prompt = (
        f"## Perfil del usuario\n{profile_context(vault)}\n\n"
        f"## Notas personales relevantes\n{notes_dump(notes)}\n"
        f"{base}\n"
        f"## Encargo\nGenera como máximo {n} ideas de proyecto.\n"
        + "\n".join(criteria)
    )
    result = await _agent(config, IdeaBatch, GENERATE_SYSTEM).run(prompt)

    written = []
    for card in result.output.ideas[:n]:
        slug = slugify(card.title)
        rel = f"{config.ai_dir}/ideas/{slug}.md"
        body, fm = render_idea(card)
        ai_zone.create(
            rel, body, type="idea", sources=card.sources, extra_frontmatter=fm,
            overwrite=True, actor="pipeline:ideas.generate",
        )
        written.append(rel)
    return written


async def critique_idea(config: Config, slug: str) -> str:
    """Añade la sección Crítica a la ficha y actualiza las puntuaciones."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)
    rel = f"{config.ai_dir}/ideas/{slug}.md"
    note = vault.read(rel)

    prompt = (
        f"## Perfil del usuario\n{profile_context(vault)}\n\n"
        f"## Ficha de idea a criticar\n{note.body}"
    )
    result = await _agent(config, IdeaCritique, CRITIQUE_SYSTEM).run(prompt)
    critique = result.output

    new_body = replace_section(note.body, "Crítica", render_critique(critique))
    ai_zone.update(rel, new_body, actor="pipeline:ideas.critique")
    # reestimación de puntuaciones tras la crítica (el verdict sigue siendo del usuario)
    abs_path = vault.resolve(rel)
    post = frontmatter.loads(abs_path.read_text(encoding="utf-8-sig"))
    post.metadata.update(
        effort=critique.effort, impact=critique.impact, fit=critique.fit,
        verdict_sugerido=critique.verdict_sugerido,
    )
    abs_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    return rel


async def compare_ideas(config: Config, slugs: list[str] | None = None) -> str:
    """Ranking razonado de ideas. Sin slugs compara todas. Escribe en inbox/."""
    vault = Vault(config.vault, config.ai_dir)
    ai_zone = AIZone(vault, default_model=config.models.default)
    notes = list_idea_notes(vault)
    if slugs:
        wanted = set(slugs)
        notes = [n for n in notes if n.path.rsplit("/", 1)[-1].removesuffix(".md") in wanted]
    if len(notes) < 2:
        raise RuntimeError("Hacen falta al menos 2 ideas para comparar.")

    fichas = "\n\n".join(f"<<< IDEA: {n.path} >>>\n{n.body}" for n in notes)
    prompt = (
        f"## Perfil del usuario\n{profile_context(vault)}\n\n"
        f"## Fichas de idea\n{fichas}\n\n## Encargo\nProduce el ranking razonado."
    )
    result = await _agent(config, Ranking, COMPARE_SYSTEM).run(prompt)

    rel = f"{config.ai_dir}/inbox/ranking-ideas.md"
    ai_zone.create(
        rel, result.output.markdown.strip() + "\n", type="critique",
        sources=[n.path for n in notes], overwrite=True, actor="pipeline:ideas.compare",
    )
    return rel
