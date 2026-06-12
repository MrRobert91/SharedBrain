from pathlib import Path

import pytest

from sharedbrain.repos import gather, parse_origin


def test_parse_origin_local(tmp_path: Path):
    assert parse_origin(str(tmp_path)) == ("local", None)


def test_parse_origin_github():
    assert parse_origin("https://github.com/david/sharedbrain") == ("github", "david/sharedbrain")
    assert parse_origin("david/sharedbrain.git") == ("github", "david/sharedbrain")


def test_parse_origin_invalid():
    with pytest.raises(ValueError):
        parse_origin("C:/no/existe/esta/ruta")


def test_gather_local_this_repo():
    # este propio repo sirve de fixture realista
    ctx = gather(str(Path(__file__).resolve().parents[1]))
    assert ctx.slug == "sharedbrain"
    assert any("pyproject.toml" in f for f in ctx.tree)
    assert ctx.readme.startswith("# SharedBrain")
    assert "py" in ctx.languages
    dump = ctx.dump()
    assert "## Estructura" in dump and "## README" in dump
