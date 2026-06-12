import pytest

from sharedbrain.vault import Vault, VaultError


def test_scan_classifies_origin(vault: Vault):
    notes = list(vault.iter_notes("all"))
    by_path = {n.path: n for n in notes}
    assert by_path["Notas/sobre-mi.md"].origin == "human"
    assert by_path["_ai/profile/valores.md"].origin == "ai"
    assert not any(".obsidian" in n.path for n in notes)


def test_scope_filters(vault: Vault):
    assert all(n.origin == "human" for n in vault.iter_notes("human"))
    assert all(n.origin == "ai" for n in vault.iter_notes("ai"))
    assert len(list(vault.iter_notes("human"))) == 3


def test_read_parses_frontmatter(vault: Vault):
    note = vault.read("_ai/ideas/curso-agentes.md")
    assert note.type == "idea"
    assert note.frontmatter["goal"] == "educación"
    assert "Curso práctico" in note.body


def test_path_traversal_rejected(vault: Vault):
    with pytest.raises(VaultError):
        vault.read("../fuera.md")
