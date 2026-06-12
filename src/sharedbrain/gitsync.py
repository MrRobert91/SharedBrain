"""Sincronización del vault vía git.

Pensado para despliegues remotos (Sliplane, VPS): el vault es un repo git
(normalmente privado en GitHub) que se clona en el primer arranque y se
sincroniza bajo demanda.

Seguridad del token: GITHUB_TOKEN se inyecta por invocación con
`-c url...insteadOf`, así nunca queda escrito en .git/config del volumen.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


class GitSyncError(Exception):
    pass


def _token_args() -> list[str]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return []
    return [
        "-c",
        f"url.https://x-access-token:{token}@github.com/.insteadOf=https://github.com/",
    ]


def _normalize_repo_url(repo: str) -> str:
    """Acepta 'owner/repo', URL https o ssh; normaliza a https para poder
    inyectar el token."""
    if repo.startswith("git@github.com:"):
        repo = "https://github.com/" + repo.removeprefix("git@github.com:")
    if not repo.startswith(("https://", "http://", "file://")) and "/" in repo:
        repo = f"https://github.com/{repo}"
    if repo.startswith("https://github.com/") and not repo.endswith(".git"):
        repo += ".git"
    return repo


def _git(args: list[str], cwd: Path | None = None) -> str:
    cmd = ["git", *_token_args(), *args]
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace",
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode != 0:
        # nunca incluir el token en el error
        detail = (result.stderr or result.stdout).strip()
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        if token:
            detail = detail.replace(token, "***")
        raise GitSyncError(f"git {args[0]} falló: {detail[:500]}")
    return result.stdout.strip()


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def ensure_vault(config: Config) -> str | None:
    """Si hay vault_repo configurado y el vault no es aún un repo, lo clona.
    Devuelve una descripción de lo hecho, o None si no había nada que hacer."""
    if not config.vault_repo:
        return None
    vault = config.vault
    if is_git_repo(vault):
        return None
    if vault.exists() and any(vault.iterdir()):
        raise GitSyncError(
            f"El vault {vault} tiene contenido pero no es un repo git; "
            f"no clono encima para no pisar nada."
        )
    vault.parent.mkdir(parents=True, exist_ok=True)
    url = _normalize_repo_url(config.vault_repo)
    args = ["clone", "--depth", "50", url, str(vault)]
    if config.vault_branch:
        args[1:1] = ["--branch", config.vault_branch]
    _git(args)
    return f"clonado {config.vault_repo} en {vault}"


def vault_status(config: Config) -> dict:
    """Estado de sincronización del vault para el panel. Nunca lanza: si algo
    falla devuelve lo que pueda con un campo error."""
    vault = config.vault
    status: dict = {
        "repo": config.vault_repo,
        "is_git": is_git_repo(vault) if vault.exists() else False,
        "branch": None,
        "dirty_files": 0,
        "last_commit": None,
        "error": None,
    }
    if not status["is_git"]:
        return status
    try:
        status["branch"] = _git(["branch", "--show-current"], cwd=vault) or "(detached)"
        porcelain = _git(["status", "--porcelain"], cwd=vault)
        status["dirty_files"] = len(porcelain.splitlines()) if porcelain else 0
        log = _git(["log", "-1", "--pretty=%h|%ad|%s", "--date=iso-strict"], cwd=vault)
        if log:
            sha, date, msg = log.split("|", 2)
            status["last_commit"] = {"sha": sha, "date": date, "message": msg}
    except GitSyncError as e:
        status["error"] = str(e)
    return status


def sync_vault(config: Config) -> list[str]:
    """Commit de cambios locales (zona IA), pull --rebase y push.
    Devuelve un resumen de las acciones realizadas."""
    vault = config.vault
    actions: list[str] = []
    if not is_git_repo(vault):
        cloned = ensure_vault(config)
        if cloned:
            return [cloned]
        raise GitSyncError(f"El vault {vault} no es un repo git y no hay vault_repo configurado.")

    if _git(["status", "--porcelain"], cwd=vault):
        _git(["add", "-A"], cwd=vault)
        _git(["-c", "user.name=sharedbrain", "-c", "user.email=sharedbrain@local",
              "commit", "-m",
              f"sharedbrain: cambios locales {datetime.now(timezone.utc).isoformat(timespec='seconds')}"],
             cwd=vault)
        actions.append("commit de cambios locales")

    _git(["pull", "--rebase"], cwd=vault)
    actions.append("pull --rebase")

    if _git(["log", "--oneline", "@{u}..HEAD"], cwd=vault):
        _git(["push"], cwd=vault)
        actions.append("push")
    return actions
