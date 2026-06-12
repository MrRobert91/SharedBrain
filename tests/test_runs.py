from pathlib import Path

import pytest

from sharedbrain.runs import RunLog, tracked


@pytest.fixture
def log(tmp_path: Path) -> RunLog:
    return RunLog(tmp_path / "test.sqlite3")


def test_start_finish(log: RunLog):
    run_id = log.start("ideas.generate", {"goal": "educación"})
    log.finish(run_id, ["_ai/ideas/x.md"])
    [run] = log.recent()
    assert run["status"] == "ok"
    assert run["outputs"] == ["_ai/ideas/x.md"]
    assert run["args"]["goal"] == "educación"


def test_fail(log: RunLog):
    run_id = log.start("profile.infer", {})
    log.fail(run_id, "RuntimeError: sin notas")
    [run] = log.recent()
    assert run["status"] == "error"
    assert "sin notas" in run["error"]


@pytest.mark.anyio
async def test_tracked_records_success(log: RunLog):
    async def fake_pipeline():
        return ["a.md", "b.md"]

    result = await tracked(log, "fake", {}, fake_pipeline())
    assert result == ["a.md", "b.md"]
    assert log.recent()[0]["status"] == "ok"


@pytest.mark.anyio
async def test_tracked_records_error(log: RunLog):
    async def boom():
        raise RuntimeError("explotó")

    with pytest.raises(RuntimeError):
        await tracked(log, "fake", {}, boom())
    run = log.recent()[0]
    assert run["status"] == "error"
    assert "explotó" in run["error"]


@pytest.fixture
def anyio_backend():
    return "asyncio"
