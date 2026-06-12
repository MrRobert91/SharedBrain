"""Tests de integración del servidor MCP usando el cliente en memoria de fastmcp."""

import json
from pathlib import Path

import pytest
from fastmcp import Client

from sharedbrain.config import Config
from sharedbrain.mcp_server import build_server


@pytest.fixture
def server(vault_dir: Path):
    config = Config(vault=vault_dir, ai_dir="_ai")
    return build_server(config)


def _data(result):
    # fastmcp devuelve structured content; el resultado json viene en .data
    return result.data


@pytest.mark.anyio
async def test_search_and_read(server):
    async with Client(server) as client:
        res = _data(await client.call_tool("search_context", {"query": "python agentes"}))
        assert res
        path = res[0]["path"]
        note = _data(await client.call_tool("read_note", {"path": path}))
        assert note["path"] == path
        assert note["body"]


@pytest.mark.anyio
async def test_get_profile(server):
    async with Client(server) as client:
        sections = _data(await client.call_tool("get_profile", {}))
        assert any(s["section"] == "valores" for s in sections)


@pytest.mark.anyio
async def test_list_ideas_filter(server):
    async with Client(server) as client:
        ideas = _data(await client.call_tool("list_ideas", {"goal": "educación"}))
        assert len(ideas) == 1
        assert ideas[0]["fit"] == 5
        none = _data(await client.call_tool("list_ideas", {"goal": "monetización"}))
        assert none == []


@pytest.mark.anyio
async def test_create_ai_note_enforced(server, vault_dir: Path):
    async with Client(server) as client:
        await client.call_tool(
            "create_ai_note",
            {"path": "_ai/inbox/desde-mcp.md", "content": "hola", "type": "note"},
        )
        written = vault_dir / "_ai" / "inbox" / "desde-mcp.md"
        assert written.is_file()
        assert "origin: ai" in written.read_text(encoding="utf-8")

        with pytest.raises(Exception):
            await client.call_tool(
                "create_ai_note", {"path": "Notas/no.md", "content": "x"}
            )


@pytest.fixture
def anyio_backend():
    return "asyncio"
