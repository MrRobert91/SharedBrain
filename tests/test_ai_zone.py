import json

import frontmatter
import pytest

from sharedbrain.ai_zone import AIZone, AIZoneError
from sharedbrain.vault import Vault


@pytest.fixture
def ai_zone(vault: Vault) -> AIZone:
    return AIZone(vault, default_model="anthropic:claude-fable-5")


def test_write_outside_ai_zone_rejected(ai_zone: AIZone):
    with pytest.raises(AIZoneError, match="_ai"):
        ai_zone.create("Notas/hackeada.md", "contenido")


def test_traversal_rejected(ai_zone: AIZone):
    with pytest.raises(AIZoneError):
        ai_zone.create("_ai/../fuera.md", "contenido")


def test_frontmatter_injected(ai_zone: AIZone, vault: Vault):
    ai_zone.create("_ai/inbox/analisis.md", "Un análisis.", sources=["Notas/sobre-mi.md"])
    note = vault.read("_ai/inbox/analisis.md")
    fm = note.frontmatter
    assert fm["origin"] == "ai"
    assert fm["status"] == "draft"
    assert fm["model"] == "anthropic:claude-fable-5"
    assert fm["sources"] == ["Notas/sobre-mi.md"]


def test_extra_frontmatter_cannot_fake_origin(ai_zone: AIZone, vault: Vault):
    ai_zone.create(
        "_ai/inbox/tramposa.md", "x",
        extra_frontmatter={"origin": "human", "status": "validated"},
    )
    fm = vault.read("_ai/inbox/tramposa.md").frontmatter
    assert fm["origin"] == "ai"
    assert fm["status"] == "draft"


def test_validated_content_protected(ai_zone: AIZone):
    with pytest.raises(AIZoneError, match="validado"):
        ai_zone.update("_ai/profile/valores.md", "nuevo contenido")
    with pytest.raises(AIZoneError, match="validado"):
        ai_zone.create("_ai/profile/valores.md", "nuevo", overwrite=True)


def test_update_preserves_frontmatter(ai_zone: AIZone, vault: Vault):
    ai_zone.create("_ai/inbox/nota.md", "v1", type="critique")
    ai_zone.update("_ai/inbox/nota.md", "v2")
    note = vault.read("_ai/inbox/nota.md")
    assert note.body.strip() == "v2"
    assert note.frontmatter["type"] == "critique"


def test_writes_are_logged(ai_zone: AIZone, vault: Vault):
    ai_zone.create("_ai/inbox/logueada.md", "x", actor="test")
    log_file = vault.ai_path / ".log" / "writes.jsonl"
    entries = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
    assert entries[-1]["actor"] == "test"
    assert entries[-1]["path"] == "_ai/inbox/logueada.md"


def test_invalid_type_rejected(ai_zone: AIZone):
    with pytest.raises(AIZoneError, match="type"):
        ai_zone.create("_ai/inbox/x.md", "x", type="loquesea")
