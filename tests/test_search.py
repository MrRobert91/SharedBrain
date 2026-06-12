from sharedbrain.search import search
from sharedbrain.vault import Vault


def test_search_finds_and_ranks(vault: Vault):
    results = search(vault, "agentes de IA")
    assert results
    paths = [r.note.path for r in results]
    assert "Notas/sobre-mi.md" in paths


def test_search_ignores_accents(vault: Vault):
    # "educacion" sin tilde debe encontrar "educación"
    results = search(vault, "educacion")
    assert any("idea-curso" in r.note.path or "curso-agentes" in r.note.path for r in results)


def test_search_scope(vault: Vault):
    results = search(vault, "agentes", scope="ai")
    assert results
    assert all(r.note.origin == "ai" for r in results)


def test_empty_query(vault: Vault):
    assert search(vault, "   ") == []
