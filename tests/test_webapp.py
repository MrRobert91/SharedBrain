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


def test_api_ideas(client: TestClient):
    ideas = client.get("/api/ideas").json()
    assert len(ideas) == 1
    assert ideas[0]["slug"] == "curso-agentes"
    assert ideas[0]["goal"] == "educación"


def test_api_profile(client: TestClient):
    profile = client.get("/api/profile").json()
    assert any(s["section"] == "valores" and s["status"] == "validated" for s in profile)


def test_api_note_and_404(client: TestClient):
    note = client.get("/api/note", params={"path": "Notas/sobre-mi.md"}).json()
    assert "Python" in note["body"]
    assert client.get("/api/note", params={"path": "no/existe.md"}).status_code == 404


def test_api_runs_empty(client: TestClient):
    assert client.get("/api/runs").json() == []


def test_mcp_mounted(client: TestClient):
    # el endpoint MCP HTTP responde (406/400 sin handshake correcto, pero no 404)
    res = client.post("/mcp/", json={})
    assert res.status_code != 404


def test_basic_auth_when_password_set(
    vault_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SHAREDBRAIN_PASSWORD", "secreta")
    config = Config(vault=vault_dir, ai_dir="_ai", db=tmp_path / "runs.sqlite3")
    with TestClient(build_app(config)) as c:
        assert c.get("/api/ideas").status_code == 401
        assert c.post("/mcp/", json={}).status_code == 401
        ok = c.get("/api/ideas", auth=("cualquiera", "secreta"))
        assert ok.status_code == 200
        assert c.get("/api/ideas", auth=("x", "mala")).status_code == 401
