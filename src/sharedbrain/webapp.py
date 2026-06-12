"""App web: API del panel + MCP por HTTP + frontend estático, en un proceso."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Config
from .ideas import list_idea_notes
from .mcp_server import build_server
from .runs import RunLog, tracked
from .vault import Vault, VaultError

FRONTEND_DIST = Path(__file__).parent / "static"

# un pipeline LLM a la vez: evita ejecuciones duplicadas desde el panel
_pipeline_lock = asyncio.Lock()


class TaskRequest(BaseModel):
    task: str


class GenerateRequest(BaseModel):
    goal: str | None = None
    horizon: str | None = None
    n: int = 5


class SyncRequest(BaseModel):
    origin: str
    slug: str | None = None


def build_app(config: Config) -> FastAPI:
    vault = Vault(config.vault, config.ai_dir)
    runlog = RunLog(config.db)

    # MCP por HTTP en el mismo proceso: los agentes remotos se conectan a /mcp/
    mcp_app = build_server(config).http_app(path="/")
    app = FastAPI(title="SharedBrain", version="0.1.0", lifespan=mcp_app.lifespan)
    app.mount("/mcp", mcp_app)

    async def _run(pipeline: str, args: dict, coro):
        if _pipeline_lock.locked():
            raise HTTPException(409, "Ya hay un pipeline en ejecución; espera a que termine.")
        async with _pipeline_lock:
            try:
                return await tracked(runlog, pipeline, args, coro)
            except Exception as e:  # noqa: BLE001 — el panel necesita el motivo
                raise HTTPException(500, f"{type(e).__name__}: {e}") from e

    # --- lectura ---

    @app.get("/api/profile")
    def api_profile() -> list[dict]:
        profile_dir = vault.ai_path / "profile"
        if not profile_dir.is_dir():
            return []
        out = []
        for f in sorted(profile_dir.glob("*.md")):
            note = vault.read(vault.relpath(f))
            out.append({"section": f.stem, "status": note.status,
                        "confidence": note.frontmatter.get("confidence"), "body": note.body})
        return out

    @app.get("/api/ideas")
    def api_ideas() -> list[dict]:
        out = []
        for note in list_idea_notes(vault):
            fm = note.frontmatter
            out.append({
                "slug": note.path.rsplit("/", 1)[-1].removesuffix(".md"),
                "title": note.title, "status": note.status, "body": note.body,
                **{k: fm.get(k) for k in
                   ("goal", "horizon", "effort", "impact", "fit", "verdict", "verdict_sugerido")},
            })
        return out

    @app.get("/api/projects")
    def api_projects() -> list[dict]:
        projects_dir = vault.ai_path / "projects"
        out = []
        if projects_dir.is_dir():
            for d in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
                docs = {}
                for f in sorted(d.glob("*.md")):
                    docs[f.stem] = vault.read(vault.relpath(f)).body
                out.append({"slug": d.name, "docs": docs})
        configured = {p.slug: p.repo for p in config.projects}
        for item in out:
            item["repo"] = configured.get(item["slug"])
        return out

    @app.get("/api/packs")
    def api_packs() -> list[dict]:
        packs_dir = vault.ai_path / "packs"
        if not packs_dir.is_dir():
            return []
        out = []
        for f in sorted(packs_dir.glob("*.md")):
            note = vault.read(vault.relpath(f))
            out.append({"slug": f.stem, "title": note.title,
                        "task": note.frontmatter.get("task"), "body": note.body})
        return out

    @app.get("/api/runs")
    def api_runs() -> list[dict]:
        return runlog.recent()

    @app.get("/api/note")
    def api_note(path: str) -> dict:
        try:
            note = vault.read(path)
        except VaultError as e:
            raise HTTPException(404, str(e)) from e
        return {"path": note.path, "title": note.title,
                "frontmatter": note.frontmatter, "body": note.body}

    # --- acciones (pipelines) ---

    @app.post("/api/profile/infer")
    async def api_profile_infer() -> dict:
        from .pipelines.profile import infer_profile
        written = await _run("profile.infer", {}, infer_profile(config))
        return {"written": written}

    @app.post("/api/ideas/generate")
    async def api_ideas_generate(req: GenerateRequest) -> dict:
        from .pipelines.ideas import generate_ideas
        written = await _run(
            "ideas.generate", req.model_dump(),
            generate_ideas(config, goal=req.goal, horizon=req.horizon, n=req.n),
        )
        return {"written": written}

    @app.post("/api/ideas/{slug}/critique")
    async def api_ideas_critique(slug: str) -> dict:
        from .pipelines.ideas import critique_idea
        written = await _run("ideas.critique", {"slug": slug}, critique_idea(config, slug))
        return {"written": written}

    @app.post("/api/ideas/{slug}/promote")
    async def api_ideas_promote(slug: str) -> dict:
        from .pipelines.projects import promote_idea
        written = await _run("project.promote", {"slug": slug}, promote_idea(config, slug))
        return {"written": written}

    @app.post("/api/packs/create")
    async def api_packs_create(req: TaskRequest) -> dict:
        from .pipelines.packs import create_pack
        written = await _run("packs.create", {"task": req.task}, create_pack(config, req.task))
        return {"written": written}

    @app.post("/api/projects/sync")
    async def api_projects_sync(req: SyncRequest) -> dict:
        from .pipelines.projects import sync_project
        written = await _run(
            "project.sync", req.model_dump(), sync_project(config, req.origin, req.slug)
        )
        return {"written": written}

    # --- frontend ---

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str) -> FileResponse:
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app
