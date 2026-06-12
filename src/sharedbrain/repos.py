"""Extracción de contexto en bruto de repositorios (determinista, sin LLM).

Soporta dos orígenes con la misma salida:
- Ruta local: usa git por subprocess.
- GitHub (owner/repo o URL): usa la API REST con GITHUB_TOKEN si existe
  (los repos públicos funcionan sin token, con rate limit bajo).
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import httpx

GITHUB_API = "https://api.github.com"
MAX_TREE_ENTRIES = 300
MAX_README_CHARS = 15_000


@dataclass
class RepoContext:
    slug: str
    origin: str  # ruta local o owner/repo
    description: str = ""
    default_branch: str = "main"
    readme: str = ""
    tree: list[str] = field(default_factory=list)
    recent_commits: list[str] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)

    def dump(self) -> str:
        parts = [
            f"# Repo: {self.origin} (rama {self.default_branch})",
            f"Descripción: {self.description or '(sin descripción)'}",
            f"Lenguajes: {', '.join(self.languages) or '(desconocidos)'}",
            "\n## Estructura\n" + "\n".join(self.tree[:MAX_TREE_ENTRIES]),
            "\n## Commits recientes\n" + ("\n".join(self.recent_commits) or "(ninguno)"),
            "\n## Issues abiertas\n" + ("\n".join(self.open_issues) or "(ninguna)"),
            "\n## README\n" + (self.readme[:MAX_README_CHARS] or "(sin README)"),
        ]
        return "\n".join(parts)


_GITHUB_RE = re.compile(r"^(?:https?://github\.com/)?(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$")


def parse_origin(origin: str) -> tuple[str, str | None]:
    """Devuelve ("local", None) si es ruta existente, o ("github", "owner/repo")."""
    if Path(origin).expanduser().is_dir():
        return "local", None
    if m := _GITHUB_RE.match(origin):
        return "github", f"{m.group('owner')}/{m.group('repo')}"
    raise ValueError(f"No es una ruta local existente ni un repo de GitHub: {origin}")


def gather(origin: str, slug: str | None = None) -> RepoContext:
    kind, gh = parse_origin(origin)
    if kind == "local":
        return _gather_local(Path(origin).expanduser().resolve(), slug)
    assert gh is not None
    return _gather_github(gh, slug)


# --- local ---

def _git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace",
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _gather_local(repo: Path, slug: str | None) -> RepoContext:
    ctx = RepoContext(slug=slug or repo.name.lower(), origin=str(repo))
    ctx.default_branch = _git(repo, "branch", "--show-current") or "main"
    # --others --exclude-standard: incluye archivos aún sin commitear
    files = _git(repo, "ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    ctx.tree = files[:MAX_TREE_ENTRIES]
    ctx.recent_commits = _git(repo, "log", "-15", "--pretty=%h %ad %s", "--date=short").splitlines()
    for name in ("README.md", "readme.md", "README.rst", "README"):
        f = repo / name
        if f.is_file():
            ctx.readme = f.read_text(encoding="utf-8-sig", errors="replace")
            break
    exts = {Path(f).suffix.lstrip(".") for f in files if Path(f).suffix}
    ctx.languages = sorted(e for e in exts if e in {
        "py", "ts", "tsx", "js", "jsx", "rs", "go", "java", "rb", "c", "cpp", "cs", "swift", "kt"
    })
    return ctx


# --- github ---

def _github_client() -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token := (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")):
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=GITHUB_API, headers=headers, timeout=30)


def _gather_github(full_name: str, slug: str | None) -> RepoContext:
    with _github_client() as client:
        meta = client.get(f"/repos/{full_name}")
        meta.raise_for_status()
        data = meta.json()
        ctx = RepoContext(
            slug=slug or data["name"].lower(),
            origin=full_name,
            description=data.get("description") or "",
            default_branch=data.get("default_branch", "main"),
        )
        langs = client.get(f"/repos/{full_name}/languages")
        if langs.is_success:
            ctx.languages = list(langs.json().keys())
        readme = client.get(f"/repos/{full_name}/readme", headers={"Accept": "application/vnd.github.raw+json"})
        if readme.is_success:
            ctx.readme = readme.text
        tree = client.get(f"/repos/{full_name}/git/trees/{ctx.default_branch}", params={"recursive": "1"})
        if tree.is_success:
            ctx.tree = [e["path"] for e in tree.json().get("tree", []) if e["type"] == "blob"][:MAX_TREE_ENTRIES]
        commits = client.get(f"/repos/{full_name}/commits", params={"per_page": 15})
        if commits.is_success:
            ctx.recent_commits = [
                f"{c['sha'][:7]} {c['commit']['author']['date'][:10]} {c['commit']['message'].splitlines()[0]}"
                for c in commits.json()
            ]
        issues = client.get(f"/repos/{full_name}/issues", params={"state": "open", "per_page": 30})
        if issues.is_success:
            ctx.open_issues = [
                f"#{i['number']} {i['title']}" for i in issues.json() if "pull_request" not in i
            ]
        return ctx
