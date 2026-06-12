"""CLI de SharedBrain (typer)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from .config import CONFIG_FILENAME, Config

app = typer.Typer(help="SharedBrain: capa de contexto personal para agentes de IA.")
ideas_app = typer.Typer(help="Generar, criticar y priorizar ideas de proyectos.")
profile_app = typer.Typer(help="Perfil personal inferido.")
app.add_typer(ideas_app, name="ideas")
app.add_typer(profile_app, name="profile")

AI_SUBDIRS = ("profile", "ideas", "projects", "packs", "inbox")

CONFIG_TEMPLATE = """\
vault: {vault}
ai_dir: _ai
models:
  default: anthropic:claude-fable-5
  # cheap: anthropic:claude-haiku-4-5-20251001
projects: []
"""


def _load_config() -> Config:
    try:
        return Config.load()
    except FileNotFoundError as e:
        typer.secho(str(e), fg="red", err=True)
        raise typer.Exit(1) from e


@app.command()
def init(vault: Path = typer.Argument(..., help="Ruta al vault de Obsidian")) -> None:
    """Crea la zona IA en el vault y un sharedbrain.config.yaml en el cwd."""
    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        typer.secho(f"El vault no existe: {vault}", fg="red", err=True)
        raise typer.Exit(1)
    for sub in AI_SUBDIRS:
        (vault / "_ai" / sub).mkdir(parents=True, exist_ok=True)
    config_path = Path.cwd() / CONFIG_FILENAME
    if config_path.exists():
        typer.echo(f"Config ya existe: {config_path} (no se toca)")
    else:
        config_path.write_text(CONFIG_TEMPLATE.format(vault=vault.as_posix()), encoding="utf-8")
        typer.echo(f"Config creada: {config_path}")
    typer.secho(f"Zona IA lista en {vault / '_ai'}", fg="green")


@app.command()
def search(
    query: str,
    scope: str = typer.Option("all", help="all | human | ai"),
    limit: int = typer.Option(10),
) -> None:
    """Búsqueda léxica en el vault (útil para depurar qué ve el sistema)."""
    from .search import search as do_search
    from .vault import Vault

    config = _load_config()
    vault = Vault(config.vault, config.ai_dir)
    results = do_search(vault, query, scope=scope, limit=limit)  # type: ignore[arg-type]
    if not results:
        typer.echo("Sin resultados.")
        return
    for r in results:
        typer.secho(f"{r.score:6.1f}  {r.note.path}", fg="cyan")
        typer.echo(f"        {r.snippet[:120]}")


@app.command()
def serve(
    web: bool = typer.Option(False, "--web", help="Servir panel web + API + MCP HTTP"),
    host: str = typer.Option("127.0.0.1", help="Host para --web (0.0.0.0 en Docker)"),
    port: int = typer.Option(8765, help="Puerto para --web"),
) -> None:
    """Arranca el servidor MCP (stdio) o, con --web, el panel completo."""
    config = _load_config()
    if web:
        import uvicorn

        from .webapp import build_app

        typer.secho(f"Panel: http://{host}:{port}  ·  MCP HTTP: http://{host}:{port}/mcp/", fg="green")
        uvicorn.run(build_app(config), host=host, port=port)
    else:
        from .mcp_server import build_server

        build_server(config).run()


@profile_app.command("infer")
def profile_infer() -> None:
    """Infiere el perfil personal desde las notas humanas (usa el LLM configurado)."""
    from .pipelines.profile import infer_profile

    config = _load_config()
    typer.echo(f"Inferiendo perfil con {config.models.default}...")
    written = asyncio.run(infer_profile(config))
    for path in written:
        typer.secho(f"  escrito: {path}", fg="green")
    typer.echo("Revisa las secciones en Obsidian y marca status: validated cuando estés conforme.")


def _run_pipeline(pipeline: str, args: dict, coro) -> list[str]:
    """Ejecuta un pipeline registrándolo en el log de actividad."""
    from .runs import RunLog, tracked

    config = _load_config()
    log = RunLog(config.db)
    result = asyncio.run(tracked(log, pipeline, args, coro))
    return result if isinstance(result, list) else [result]


@ideas_app.command("generate")
def ideas_generate(
    goal: str = typer.Option(None, help="monetización | marca-personal | educación | investigación | aprendizaje"),
    horizon: str = typer.Option(None, help="corto | medio | largo"),
    objetivo: str = typer.Option(None, help="Objetivo específico en texto libre (prioritario)"),
    from_note: str = typer.Option(None, "--from", help="Ruta de una nota con una idea de partida"),
    n: int = typer.Option(5, help="Número máximo de ideas"),
) -> None:
    """Genera fichas de idea ancladas en tu perfil y tus notas."""
    from .pipelines.ideas import generate_ideas

    config = _load_config()
    typer.echo(f"Generando ideas con {config.models.default}...")
    written = _run_pipeline(
        "ideas.generate", {"goal": goal, "horizon": horizon, "custom_goal": objetivo, "n": n},
        generate_ideas(config, goal=goal, horizon=horizon, custom_goal=objetivo,
                       from_note=from_note, n=n),
    )
    for path in written:
        typer.secho(f"  idea: {path}", fg="green")


@ideas_app.command("rebuild")
def ideas_rebuild(slug: str) -> None:
    """Regenera una idea incorporando tus notas de feedback."""
    from .pipelines.ideas import rebuild_idea

    config = _load_config()
    written = _run_pipeline("ideas.rebuild", {"slug": slug}, rebuild_idea(config, slug))
    typer.secho(f"Idea regenerada: {written[0]}", fg="green")


@ideas_app.command("critique")
def ideas_critique(slug: str) -> None:
    """Crítica constructiva de una idea (se añade a la propia ficha)."""
    from .pipelines.ideas import critique_idea

    config = _load_config()
    written = _run_pipeline("ideas.critique", {"slug": slug}, critique_idea(config, slug))
    typer.secho(f"Crítica añadida: {written[0]}", fg="green")


@ideas_app.command("compare")
def ideas_compare(slugs: list[str] = typer.Argument(None)) -> None:
    """Ranking razonado de ideas (todas, o las que indiques)."""
    from .pipelines.ideas import compare_ideas

    config = _load_config()
    written = _run_pipeline("ideas.compare", {"slugs": slugs}, compare_ideas(config, slugs or None))
    typer.secho(f"Ranking: {written[0]}", fg="green")


@ideas_app.command("promote")
def ideas_promote(slug: str) -> None:
    """Convierte una idea en proyecto: specs en _ai/projects/<slug>/."""
    from .pipelines.projects import promote_idea

    config = _load_config()
    written = _run_pipeline("project.promote", {"slug": slug}, promote_idea(config, slug))
    for path in written:
        typer.secho(f"  escrito: {path}", fg="green")
    typer.echo("Entrega agentes.md (o un pack) al agente que vaya a construirlo.")


@app.command("pack")
def pack_create(task: str = typer.Argument(..., help="Descripción de la tarea")) -> None:
    """Compila un paquete de contexto autocontenido para una tarea."""
    from .pipelines.packs import create_pack

    config = _load_config()
    written = _run_pipeline("packs.create", {"task": task}, create_pack(config, task))
    typer.secho(f"Pack: {written[0]}", fg="green")


@app.command("vault-sync")
def vault_sync() -> None:
    """Sincroniza el vault con su repo git: commit local, pull --rebase, push."""
    from .gitsync import GitSyncError, sync_vault

    config = _load_config()
    try:
        for action in sync_vault(config):
            typer.secho(f"  {action}", fg="green")
    except GitSyncError as e:
        typer.secho(str(e), fg="red", err=True)
        raise typer.Exit(1) from e


@app.command("project-sync")
def project_sync(
    origin: str = typer.Argument(..., help="Ruta local o owner/repo de GitHub"),
    slug: str = typer.Option(None, help="Slug del proyecto (por defecto, nombre del repo)"),
) -> None:
    """Extrae contexto real de un repositorio → _ai/projects/<slug>/."""
    from .pipelines.projects import sync_project

    config = _load_config()
    written = _run_pipeline("project.sync", {"origin": origin}, sync_project(config, origin, slug))
    for path in written:
        typer.secho(f"  escrito: {path}", fg="green")


@ideas_app.command("list")
def ideas_list(
    verdict: str = typer.Option(None), goal: str = typer.Option(None)
) -> None:
    """Lista las fichas de ideas con sus metadatos."""
    from .vault import Vault

    config = _load_config()
    vault = Vault(config.vault, config.ai_dir)
    ideas_dir = vault.ai_path / "ideas"
    rows = []
    if ideas_dir.is_dir():
        for f in sorted(ideas_dir.glob("*.md")):
            note = vault.read(vault.relpath(f))
            fm = note.frontmatter
            if verdict and fm.get("verdict") != verdict:
                continue
            if goal and fm.get("goal") != goal:
                continue
            rows.append((note.title, fm.get("goal", "-"), str(fm.get("effort", "-")),
                         str(fm.get("impact", "-")), fm.get("verdict", "sin-evaluar")))
    if not rows:
        typer.echo("No hay ideas todavía. (ideas generate llega en la fase 3)")
        return
    typer.echo(f"{'idea':40} {'goal':16} {'eff':>3} {'imp':>3}  verdict")
    for title, g, e, i, v in rows:
        typer.echo(f"{title[:40]:40} {g:16} {e:>3} {i:>3}  {v}")


if __name__ == "__main__":
    app()
