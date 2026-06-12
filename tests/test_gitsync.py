import subprocess
from pathlib import Path

import pytest

from sharedbrain.config import Config
from sharedbrain.gitsync import GitSyncError, _normalize_repo_url, ensure_vault, sync_vault


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8"
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


@pytest.fixture
def remote(tmp_path: Path) -> Path:
    """Repo bare que hace de 'GitHub' + contenido inicial."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)
    seed = tmp_path / "seed"
    seed.mkdir()
    _git(seed, "init", "-b", "main")
    _git(seed, "config", "user.name", "test")
    _git(seed, "config", "user.email", "t@t")
    (seed / "nota.md").write_text("Mi nota humana.", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-m", "inicial")
    _git(seed, "remote", "add", "origin", str(bare))
    _git(seed, "push", "-u", "origin", "main")
    return bare


def test_normalize_repo_url():
    assert _normalize_repo_url("david/vault") == "https://github.com/david/vault.git"
    assert _normalize_repo_url("git@github.com:david/vault.git") == "https://github.com/david/vault.git"
    assert _normalize_repo_url("https://github.com/david/vault") == "https://github.com/david/vault.git"


def test_ensure_vault_clones(remote: Path, tmp_path: Path):
    vault = tmp_path / "vault"
    config = Config(vault=vault, vault_repo=str(remote))
    result = ensure_vault(config)
    assert result and "clonado" in result
    assert (vault / "nota.md").is_file()
    # segunda llamada: ya es repo, no hace nada
    assert ensure_vault(config) is None


def test_ensure_vault_refuses_nonempty_dir(remote: Path, tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "algo.md").write_text("x", encoding="utf-8")
    with pytest.raises(GitSyncError, match="no clono encima"):
        ensure_vault(Config(vault=vault, vault_repo=str(remote)))


def test_sync_vault_commits_pulls_pushes(remote: Path, tmp_path: Path):
    vault = tmp_path / "vault"
    config = Config(vault=vault, vault_repo=str(remote))
    ensure_vault(config)

    # cambio local (lo que generaría un pipeline en el servidor)
    ai = vault / "_ai" / "ideas"
    ai.mkdir(parents=True)
    (ai / "nueva.md").write_text("---\norigin: ai\n---\nIdea.", encoding="utf-8")

    actions = sync_vault(config)
    assert "commit de cambios locales" in actions
    assert "push" in actions
    # el remoto recibió el cambio (--git-dir explícito: safe.bareRepository)
    out = subprocess.run(
        ["git", "--git-dir", str(remote), "ls-tree", "-r", "--name-only", "main"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert "_ai/ideas/nueva.md" in out.stdout


def test_sync_vault_without_repo_raises(tmp_path: Path):
    vault = tmp_path / "suelto"
    vault.mkdir()
    with pytest.raises(GitSyncError):
        sync_vault(Config(vault=vault))
