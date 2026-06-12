"""Modelo de la ficha de idea y su materialización en Markdown.

La ficha es el contrato entre generación, crítica y priorización: secciones
fijas + frontmatter filtrable. Este módulo es determinista (sin LLM) para que
sea testeable; los pipelines lo usan para escribir/leer fichas.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel, Field

from .vault import Note, Vault

Goal = Literal[
    "monetización", "marca-personal", "educación", "investigación", "aprendizaje", "otro"
]
Horizon = Literal["corto", "medio", "largo"]
Verdict = Literal["hacer", "reducir", "aparcar", "descartar", "sin-evaluar"]


class IdeaCard(BaseModel):
    """Ficha de idea completa. El LLM debe rellenar todas las secciones."""

    title: str
    goal: Goal
    horizon: Horizon
    effort: int = Field(ge=1, le=5, description="1 = trivial, 5 = meses de trabajo")
    impact: int = Field(ge=1, le=5)
    fit: int = Field(ge=1, le=5, description="Encaje con el perfil del usuario")
    descripcion: str
    problema: str = Field(description="Problema que resuelve")
    encaje: str = Field(description="Por qué encaja con el usuario, citando su perfil/notas")
    publico: str = Field(description="Público objetivo")
    impacto_posible: str
    dificultad: str = Field(description="Dificultad estimada y por qué")
    mvp_minimo: str = Field(description="Alcance mínimo viable, lo más pequeño que valida")
    riesgos: str
    puntos_ciegos: str
    como_reducirla: str
    como_ampliarla: str
    outputs: str = Field(description="Demo, artículo, repo, producto, curso, paper...")
    criterios_decision: str = Field(description="Por qué hacerla o descartarla; qué validar primero")
    sources: list[str] = Field(
        default_factory=list, description="Notas del vault que inspiran o sustentan la idea"
    )


class IdeaCritique(BaseModel):
    """Crítica constructiva de una idea (sparring intelectual)."""

    resumen: str = Field(description="Veredicto razonado en 2-4 frases")
    demasiado_grande: str = Field(description="¿Es demasiado grande o vaga? Cómo acotarla")
    alternativas: str = Field(description="¿Existen ya alternativas? ¿Aporta algo distinto?")
    esfuerzo_impacto: str = Field(description="¿Compensa el esfuerzo frente al impacto?")
    ventaja_real: str = Field(description="¿Tiene el usuario una ventaja real para ejecutarla?")
    supuestos: str = Field(description="Supuestos que habría que validar, y cómo")
    primera_comprobacion: str = Field(description="Lo más barato que se puede hacer para saber si merece la pena")
    verdict_sugerido: Verdict
    effort: int = Field(ge=1, le=5, description="Reestimación tras la crítica")
    impact: int = Field(ge=1, le=5)
    fit: int = Field(ge=1, le=5)


SECTION_ORDER: list[tuple[str, str]] = [
    ("descripcion", "Descripción"),
    ("problema", "Problema que resuelve"),
    ("encaje", "Por qué encaja conmigo"),
    ("publico", "Público objetivo"),
    ("impacto_posible", "Impacto posible"),
    ("dificultad", "Dificultad estimada"),
    ("mvp_minimo", "MVP mínimo"),
    ("riesgos", "Riesgos principales"),
    ("puntos_ciegos", "Puntos ciegos"),
    ("como_reducirla", "Cómo reducirla"),
    ("como_ampliarla", "Cómo ampliarla"),
    ("outputs", "Outputs posibles"),
    ("criterios_decision", "Criterios de decisión"),
]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "idea"


def render_idea(card: IdeaCard) -> tuple[str, dict]:
    """Devuelve (cuerpo markdown, frontmatter extra) de la ficha."""
    parts = [f"# {card.title}"]
    for attr, heading in SECTION_ORDER:
        parts.append(f"\n## {heading}\n\n{getattr(card, attr).strip()}")
    parts.append("\n## Crítica\n\n_Pendiente. Genérala con `sharedbrain ideas critique <slug>`._")
    parts.append("\n## Veredicto\n\n_Lo decides tú: edita `verdict` en el frontmatter._")
    body = "\n".join(parts) + "\n"
    fm = {
        "title": card.title,
        "goal": card.goal,
        "horizon": card.horizon,
        "effort": card.effort,
        "impact": card.impact,
        "fit": card.fit,
        "verdict": "sin-evaluar",
    }
    return body, fm


def render_critique(critique: IdeaCritique) -> str:
    rows = [
        ("", critique.resumen),
        ("¿Demasiado grande o vaga?", critique.demasiado_grande),
        ("Alternativas existentes", critique.alternativas),
        ("Esfuerzo vs impacto", critique.esfuerzo_impacto),
        ("Ventaja real", critique.ventaja_real),
        ("Supuestos a validar", critique.supuestos),
        ("Primera comprobación barata", critique.primera_comprobacion),
        ("Veredicto sugerido", f"**{critique.verdict_sugerido}** "
         f"(effort {critique.effort}, impact {critique.impact}, fit {critique.fit})"),
    ]
    out = []
    for heading, text in rows:
        if heading:
            out.append(f"### {heading}\n\n{text.strip()}")
        else:
            out.append(text.strip())
    return "\n\n".join(out) + "\n"


def replace_section(body: str, heading: str, new_content: str) -> str:
    """Sustituye el contenido de una sección `## heading` manteniendo el resto."""
    pattern = re.compile(rf"(^## {re.escape(heading)}\s*\n)(.*?)(?=^## |\Z)", re.M | re.S)
    if not pattern.search(body):
        return body.rstrip() + f"\n\n## {heading}\n\n{new_content}\n"
    return pattern.sub(lambda m: m.group(1) + "\n" + new_content + "\n\n", body, count=1)


def list_idea_notes(vault: Vault) -> list[Note]:
    ideas_dir = vault.ai_path / "ideas"
    if not ideas_dir.is_dir():
        return []
    return [vault.read(vault.relpath(f)) for f in sorted(ideas_dir.glob("*.md"))]
