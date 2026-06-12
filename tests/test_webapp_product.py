"""Tests de los endpoints del panel-producto: feedback, verdict, stats, vault."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sharedbrain.config import Config
from sharedbrain.webapp import build_app


@pytest.fixture
def client(vault_dir: Path, tmp_path: Path):
    config = Config(vault=vault_dir, ai_dir="_ai", db=tmp_path / "runs.sqlite3")
    with TestClient(build_app(config)) as c:
        yield c


def test_feedback_appends_user_note(client: TestClient):
    r = client.post("/api/ideas/curso-agentes/feedback", json={"text": "Hazlo más corto."})
    assert r.status_code == 200
    body = client.get("/api/ideas").json()[0]["body"]
    assert "## Notas del usuario" in body
    assert "Hazlo más corto." in body
    # segunda nota se acumula
    client.post("/api/ideas/curso-agentes/feedback", json={"text": "Enfócalo a Python."})
    body = client.get("/api/ideas").json()[0]["body"]
    assert "Hazlo más corto." in body and "Enfócalo a Python." in body


def test_feedback_404(client: TestClient):
    assert client.post("/api/ideas/no-existe/feedback", json={"text": "x"}).status_code == 404


def test_verdict_patch(client: TestClient):
    r = client.patch("/api/ideas/curso-agentes", json={"verdict": "hacer", "status": "reviewed"})
    assert r.status_code == 200
    idea = client.get("/api/ideas").json()[0]
    assert idea["verdict"] == "hacer"
    assert idea["status"] == "reviewed"
    assert client.patch("/api/ideas/curso-agentes", json={"verdict": "loquesea"}).status_code == 422


def test_stats(client: TestClient):
    stats = client.get("/api/stats").json()
    assert stats["notes"]["human"] == 3
    assert stats["ideas"]["total"] == 1
    assert stats["ideas"]["sin_critica"] == 1
    assert stats["profile"]["sections"] == 1
    assert stats["profile"]["validated"] == 1
    assert any("sin crítica" in s for s in stats["suggestions"])


def test_vault_tree(client: TestClient):
    tree = client.get("/api/vault/tree").json()
    paths = {n["path"] for n in tree}
    assert "Notas/sobre-mi.md" in paths
    assert "_ai/profile/valores.md" in paths
    origins = {n["path"]: n["origin"] for n in tree}
    assert origins["Notas/sobre-mi.md"] == "human"


def test_vault_status_no_git(client: TestClient):
    status = client.get("/api/vault/status").json()
    assert status["is_git"] is False
    assert status["last_sync"] is None
