from sharedbrain.ideas import (
    IdeaCard,
    IdeaCritique,
    render_critique,
    render_idea,
    replace_section,
    slugify,
)


def _card(**overrides) -> IdeaCard:
    base = dict(
        title="Curso de Agentes de IA",
        goal="educación", horizon="corto", effort=2, impact=4, fit=5,
        descripcion="d", problema="p", encaje="e", publico="pub",
        impacto_posible="i", dificultad="dif", mvp_minimo="mvp",
        riesgos="r", puntos_ciegos="pc", como_reducirla="red",
        como_ampliarla="amp", outputs="demo", criterios_decision="c",
        sources=["Notas/idea-curso.md"],
    )
    base.update(overrides)
    return IdeaCard(**base)


def test_slugify():
    assert slugify("Curso de Agentes de IA") == "curso-de-agentes-de-ia"
    assert slugify("¡Educación práctica!") == "educacion-practica"
    assert slugify("***") == "idea"


def test_render_idea_has_all_sections():
    body, fm = render_idea(_card())
    for heading in ("Descripción", "Problema que resuelve", "MVP mínimo",
                    "Puntos ciegos", "Criterios de decisión", "Crítica", "Veredicto"):
        assert f"## {heading}" in body
    assert fm["verdict"] == "sin-evaluar"
    assert fm["goal"] == "educación"


def test_replace_section_existing():
    body, _ = render_idea(_card())
    updated = replace_section(body, "Crítica", "Esta idea es sólida.")
    assert "Esta idea es sólida." in updated
    assert "_Pendiente" not in updated
    assert "## Veredicto" in updated  # las secciones posteriores sobreviven


def test_replace_section_missing_appends():
    out = replace_section("# Algo\n\n## Una\n\nx\n", "Nueva", "contenido")
    assert out.rstrip().endswith("contenido")
    assert "## Nueva" in out


def test_user_notes_append_and_get():
    from sharedbrain.ideas import append_user_note, get_section

    body, _ = render_idea(_card())
    body = append_user_note(body, "Más pequeño.", "2026-06-12")
    body = append_user_note(body, "Para Python.", "2026-06-13")
    section = get_section(body, "Notas del usuario")
    assert "_Añade aquí" not in section  # el placeholder desaparece
    assert "**2026-06-12**: Más pequeño." in section
    assert "**2026-06-13**: Para Python." in section
    assert "## Veredicto" in body  # el resto de la ficha sobrevive


def test_render_critique():
    crit = IdeaCritique(
        resumen="Buena pero grande.", demasiado_grande="Sí, acótala.",
        alternativas="Pocas.", esfuerzo_impacto="Compensa.", ventaja_real="Sí.",
        supuestos="Demanda real.", primera_comprobacion="Encuesta.",
        verdict_sugerido="reducir", effort=3, impact=4, fit=5,
    )
    md = render_critique(crit)
    assert "**reducir**" in md
    assert "Primera comprobación barata" in md
