"""Registro de ejecuciones de pipelines (estado operativo → SQLite).

El conocimiento vive en el vault; esto solo alimenta la vista de actividad
del panel. La BD se crea junto a la config (./sharedbrain.sqlite3).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """\
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'running',
    outputs TEXT NOT NULL DEFAULT '[]',
    error TEXT,
    started TEXT NOT NULL,
    finished TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunLog:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def start(self, pipeline: str, args: dict | None = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO runs (pipeline, args, started) VALUES (?, ?, ?)",
                (pipeline, json.dumps(args or {}, ensure_ascii=False), _now()),
            )
            return int(cur.lastrowid)

    def finish(self, run_id: int, outputs: list[str]) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE runs SET status='ok', outputs=?, finished=? WHERE id=?",
                (json.dumps(outputs, ensure_ascii=False), _now(), run_id),
            )

    def fail(self, run_id: int, error: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE runs SET status='error', error=?, finished=? WHERE id=?",
                (error[:2000], _now(), run_id),
            )

    def recent(self, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["args"] = json.loads(d["args"])
            d["outputs"] = json.loads(d["outputs"])
            out.append(d)
        return out


async def tracked(log: RunLog, pipeline: str, args: dict, coro):
    """Ejecuta una corutina de pipeline registrando inicio/fin/error."""
    run_id = log.start(pipeline, args)
    try:
        result = await coro
        outputs = result if isinstance(result, list) else [result]
        log.finish(run_id, outputs)
        return result
    except Exception as e:
        log.fail(run_id, f"{type(e).__name__}: {e}")
        raise
