from pathlib import Path

import pytest

from sharedbrain.vault import Vault


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Vault de ejemplo: notas humanas desordenadas + zona IA con contenido."""
    notes = tmp_path / "Notas"
    notes.mkdir()
    (notes / "sobre-mi.md").write_text(
        "# Sobre mí\n\nSoy programador de Python. Me interesan los agentes de IA, "
        "el open source y las herramientas educativas.\n",
        encoding="utf-8",
    )
    (notes / "idea-curso.md").write_text(
        "---\ntags: [idea, educación]\n---\n"
        "Idea: un curso práctico sobre agentes de IA con proyectos reales.\n",
        encoding="utf-8",
    )
    (tmp_path / "diario.md").write_text(
        "Hoy pensé en priorizar mejor mis proyectos en vez de empezar más.\n",
        encoding="utf-8",
    )
    # Carpeta que debe ignorarse
    obsidian = tmp_path / ".obsidian"
    obsidian.mkdir()
    (obsidian / "config.md").write_text("no debería aparecer", encoding="utf-8")
    # Zona IA preexistente
    profile = tmp_path / "_ai" / "profile"
    profile.mkdir(parents=True)
    (profile / "valores.md").write_text(
        "---\norigin: ai\ntype: inference\nstatus: validated\nconfidence: high\n---\n"
        "Valoras el software libre y la educación.\n",
        encoding="utf-8",
    )
    ideas = tmp_path / "_ai" / "ideas"
    ideas.mkdir(parents=True)
    (ideas / "curso-agentes.md").write_text(
        "---\norigin: ai\ntype: idea\nstatus: draft\ngoal: educación\n"
        "effort: 3\nimpact: 4\nfit: 5\nverdict: sin-evaluar\n---\n"
        "# Curso de agentes\n\n## Descripción\nCurso práctico.\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def vault(vault_dir: Path) -> Vault:
    return Vault(vault_dir, "_ai")
