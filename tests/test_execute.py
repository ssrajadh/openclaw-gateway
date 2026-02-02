"""Tests for /execute and graph execution (mocked worker)."""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.graph.nodes import plan_node, execute_node
from app import rbac


client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_execute_empty_prompt():
    resp = client.post("/execute", json={"prompt": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("error", "success")
    if data["status"] == "error":
        assert "Empty" in str(data.get("output", ""))


@pytest.mark.asyncio
async def test_plan_node_empty_prompt():
    state = {"prompt": "", "user_id": None}
    out = await plan_node(state)
    assert out["steps"] == []
    assert out.get("error") == "Empty prompt"
    assert out.get("done") is True


@pytest.mark.asyncio
async def test_execute_node_no_steps():
    state = {"steps": [], "current_index": 0, "results": [], "user_id": None}
    out = await execute_node(state)
    assert out["done"] is True
    assert out["results"] == []


@pytest.mark.asyncio
async def test_rbac_allows_all():
    allowed = rbac.allowed_tools("any_user")
    assert "*" in allowed
    assert rbac.is_tool_allowed("any_user", "terminal.run") is True


@pytest.mark.asyncio
async def test_execute_node_rbac_deny():
    with patch.object(rbac, "is_tool_allowed", return_value=False):
        state = {
            "steps": [{"tool": "terminal.run", "args": {"command": "ls"}}],
            "current_index": 0,
            "results": [],
            "user_id": "u1",
        }
        out = await execute_node(state)
        assert out["done"] is True
        assert "RBAC" in out.get("error", "")
        assert out["results"] == []


@pytest.mark.asyncio
async def test_execute_node_calls_worker():
    with patch("app.graph.nodes.invoke_tool", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = {"ok": True, "result": {"sessions": []}}
        state = {
            "steps": [{"tool": "sessions_list", "args": {}}],
            "current_index": 0,
            "results": [],
            "user_id": None,
        }
        out = await execute_node(state)
        assert out["done"] is True
        assert out["results"] == [{"tool": "sessions_list", "ok": True, "result": {"sessions": []}}]
        mock_invoke.assert_called_once_with("sessions_list", {})
