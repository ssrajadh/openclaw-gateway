"""Tests for /execute and graph execution (mocked worker and audit)."""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.graph.nodes import plan_node, execute_node


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
async def test_execute_node_calls_worker():
    with (
        patch("app.graph.nodes.invoke_tool", new_callable=AsyncMock) as mock_invoke,
        patch("app.graph.nodes.create_pending_record", new_callable=AsyncMock) as mock_create,
        patch("app.graph.nodes.update_record", new_callable=AsyncMock) as mock_update,
    ):
        mock_invoke.return_value = {"ok": True, "result": {"sessions": []}}
        mock_create.return_value = 1
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
        mock_create.assert_called_once_with(actor_id=None, tool_call="sessions_list", raw_input={})
        mock_update.assert_called_once()


@patch("app.main.list_audit_logs", new_callable=AsyncMock)
def test_get_audit(mock_list):
    mock_list.return_value = [{"id": 1, "tool_call": "terminal.run", "security_status": "ALLOWED"}]
    resp = client.get("/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert "records" in data
    assert len(data["records"]) == 1
    assert data["records"][0]["tool_call"] == "terminal.run"


@patch("app.main.list_audit_logs", new_callable=AsyncMock)
def test_get_audit_filtered_by_status(mock_list):
    mock_list.return_value = []
    resp = client.get("/audit?status=ALLOWED")
    assert resp.status_code == 200
    mock_list.assert_called_once_with(status="ALLOWED")
