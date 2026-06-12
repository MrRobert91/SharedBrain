"""App web: API del panel + MCP por HTTP + frontend estático, en un proceso."""

from __future__ import annotations

import asyncio
import base64
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import Config
from .ideas import list_idea_notes
from .mcp_server import build_server
from .runs import RunLog, tracked
from .vault import Vault, VaultError

FRONTEND_DIST = Path(__file__).parent / "static"


def _write_preserving_frontmatter(vault: Vault, rel: str, new_body: str) -> None:
    """Reescribe el cuerpo de una nota conservando su frontmatter (acción humana)."""
    import frontmatter as fm_lib

    abs_path = vault.resolve(rel)
    post = fm_lib.loads(abs_path.read_text(encoding="utf-8-sig"))
    post.content = new_body
    abs_path.write_text(fm_lib.dumps(post) + "\n", encoding="utf-8")

# un pipeline LLM a la vez: evita ejecuciones duplicadas desde el panel
_pipeline_lock = asyncio.Lock()


class TaskRequest(BaseModel):
    task: str


class GenerateRequest(BaseModel):
    goal: str | None = None
    horizon: str | None = None
    custom_goal: str | None = None
    n: int = 5


class FeedbackRequest(BaseModel):
    text: str


class VerdictRequest(BaseModel):
    verdict: str | None = None
    status: str | None = None


class SyncRequest(BaseModel):
    origin: str
    slug: str | None = None


def build_app(config: Config) -> FastAPI:
    # primer arranque en un servidor: clonar el vault si está configurado como repo
    from .gitsync import ensure_vault

    ensure_vault(config)
    config.vault.mkdir(parents=True, exist_ok=True)
    vault = Vault(config.vault, config.ai_dir)
    runlog = RunLog(config.db)

    # MCP por HTTP en el mismo proceso: los agentes remotos se conectan a /mcp/
    mcp_app = build_server(config).http_app(path="/")
    app = FastAPI(title="SharedBrain", version="0.1.0", lifespan=mcp_app.lifespan)
    app.mount("/mcp", mcp_app)

    # Auth opcional para despliegues expuestos (Sliplane, VPS...): si
    # SHAREDBRAIN_PASSWORD está definida, todo (panel, API, MCP) exige
    # Basic Auth (cualquier usuario + esa contraseña).
    if password := os.environ.get("SHAREDBRAIN_PASSWORD"):

        @app.middleware("http")
        async def basic_auth(request: Request, call_next):
            header = request.headers.get("authorization", "")
            ok = False
            if header.startswith("Basic "):
                try:
                    decoded = base64.b64decode(header[6:]).decode()
                    _, _, given = decoded.partition(":")
                    ok = secrets.compare_digest(given, password)
                except Exception:
                    ok = False
            if not ok:
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="SharedBrain"'},
                )
            return await call_next(request)

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

    @app.get("/api/vault/status")
    def api_vault_status() -> dict:
        from .gitsync import vault_status

        status = vault_status(config)
        last_sync = next(
            (r for r in runlog.recent(200) if r["pipeline"] == "vault.sync" and r["status"] == "ok"),
            None,
        )
        status["last_sync"] = last_sync["finished"] if last_sync else None
        return status

    @app.get("/api/vault/tree")
    def api_vault_tree() -> list[dict]:
        """Listado plano de notas (el árbol lo construye el frontend)."""
        out = []
        for note in vault.iter_notes("all"):
            out.append({
                "path": note.path,
                "title": note.title,
                "origin": note.origin,
                "type": note.type,
                "status": note.status,
            })
        return out

    @app.get("/api/stats")
    def api_stats() -> dict:
        """Resumen del estado de notas, ideas y proyectos + sugerencias."""
        human = ai = 0
        for note in vault.iter_notes("all"):
            if note.origin == "human":
                human += 1
            else:
                ai += 1
        from .ideas import get_section

        ideas = list_idea_notes(vault)
        by_verdict: dict[str, int] = {}
        sin_critica = 0
        for n in ideas:
            v = str(n.frontmatter.get("verdict") or "sin-evaluar")
            by_verdict[v] = by_verdict.get(v, 0) + 1
            critica = get_section(n.body, "Crítica")
            if not critica or critica.startswith("_Pendiente"):
                sin_critica += 1
        projects_dir = vault.ai_path / "projects"
        n_projects = sum(1 for p in projects_dir.iterdir() if p.is_dir()) if projects_dir.is_dir() else 0
        packs_dir = vault.ai_path / "packs"
        n_packs = len(list(packs_dir.glob("*.md"))) if packs_dir.is_dir() else 0
        profile_dir = vault.ai_path / "profile"
        profile_sections = list(profile_dir.glob("*.md")) if profile_dir.is_dir() else []
        profile_validated = sum(
            1 for f in profile_sections
            if vault.read(vault.relpath(f)).status == "validated"
        )

        suggestions: list[str] = []
        if human == 0:
            suggestions.append("El vault no tiene notas humanas: sincronízalo o añade notas.")
        if not profile_sections:
            suggestions.append("No hay perfil inferido. Ejecútalo desde la pestaña Perfil.")
        elif profile_validated < len(profile_sections):
            suggestions.append(
                f"Perfil: {len(profile_sections) - profile_validated} sección(es) sin validar. "
                "Revísalas y marca status: validated."
            )
        if not ideas:
            suggestions.append("Aún no hay ideas. Genera la primera tanda desde Ideas.")
        if sin_critica:
            suggestions.append(f"{sin_critica} idea(s) sin crítica: pásalas por el sparring.")
        pendientes = by_verdict.get("sin-evaluar", 0)
        if pendientes:
            suggestions.append(f"{pendientes} idea(s) sin veredicto tuyo: decide hacer/aparcar/descartar.")
        hacer = by_verdict.get("hacer", 0)
        if hacer and n_projects == 0:
            suggestions.append("Tienes ideas en 'hacer' sin promocionar a proyecto.")

        return {
            "notes": {"human": human, "ai": ai},
            "ideas": {"total": len(ideas), "by_verdict": by_verdict, "sin_critica": sin_critica},
            "projects": n_projects,
            "packs": n_packs,
            "profile": {"sections": len(profile_sections), "validated": profile_validated},
            "suggestions": suggestions,
        }

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
            generate_ideas(
                config, goal=req.goal, horizon=req.horizon,
                custom_goal=req.custom_goal, n=req.n,
            ),
        )
        return {"written": written}

    @app.post("/api/ideas/{slug}/critique")
    async def api_ideas_critique(slug: str) -> dict:
        from .pipelines.ideas import critique_idea
        written = await _run("ideas.critique", {"slug": slug}, critique_idea(config, slug))
        return {"written": written}

    @app.post("/api/ideas/{slug}/feedback")
    def api_ideas_feedback(slug: str, req: FeedbackRequest) -> dict:
        """Añade una nota del usuario a la ficha (feedback humano, sin LLM)."""
        from datetime import date

        from .ideas import append_user_note

        rel = f"{config.ai_dir}/ideas/{slug}.md"
        try:
            note = vault.read(rel)
        except VaultError as e:
            raise HTTPException(404, str(e)) from e
        new_body = append_user_note(note.body, req.text, date.today().isoformat())
        _write_preserving_frontmatter(vault, rel, new_body)
        return {"written": [rel]}

    @app.patch("/api/ideas/{slug}")
    def api_ideas_verdict(slug: str, req: VerdictRequest) -> dict:
        """Acción humana desde el panel: fijar veredicto y/o estado de una idea."""
        import frontmatter as fm_lib

        rel = f"{config.ai_dir}/ideas/{slug}.md"
        abs_path = vault.resolve(rel)
        if not abs_path.is_file():
            raise HTTPException(404, f"No existe la idea {slug}")
        post = fm_lib.loads(abs_path.read_text(encoding="utf-8-sig"))
        if req.verdict:
            if req.verdict not in {"hacer", "reducir", "aparcar", "descartar", "sin-evaluar"}:
                raise HTTPException(422, f"verdict inválido: {req.verdict}")
            post.metadata["verdict"] = req.verdict
        if req.status:
            if req.status not in {"draft", "reviewed", "validated", "rejected"}:
                raise HTTPException(422, f"status inválido: {req.status}")
            post.metadata["status"] = req.status
        abs_path.write_text(fm_lib.dumps(post) + "\n", encoding="utf-8")
        return {"written": [rel]}

    @app.post("/api/ideas/{slug}/rebuild")
    async def api_ideas_rebuild(slug: str) -> dict:
        from .pipelines.ideas import rebuild_idea
        written = await _run("ideas.rebuild", {"slug": slug}, rebuild_idea(config, slug))
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

    @app.post("/api/vault/sync")
    async def api_vault_sync() -> dict:
        from .gitsync import GitSyncError, sync_vault

        run_id = runlog.start("vault.sync", {})
        try:
            # git es bloqueante: fuera del event loop
            actions = await asyncio.to_thread(sync_vault, config)
        except GitSyncError as e:
            runlog.fail(run_id, str(e))
            raise HTTPException(500, str(e)) from e
        runlog.finish(run_id, actions)
        return {"written": actions}

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
