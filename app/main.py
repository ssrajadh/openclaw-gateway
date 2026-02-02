"""FastAPI app: /health and /execute."""

import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException

logger = logging.getLogger(__name__)
from pydantic import BaseModel

from app.graph.graph import get_execution_graph

app = FastAPI(title="OpenClaw Gateway", version="0.1.0")


class ExecuteBody(BaseModel):
    prompt: str
    user_id: str | None = None


class ExecuteResponse(BaseModel):
    status: str  # "success" | "error" | "pending_approval"
    output: list | str | None = None


@app.get("/health")
async def health():
    """Health check. Optionally check worker reachability later."""
    return {"status": "ok"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(body: ExecuteBody):
    """
    Run the LangGraph pipeline: plan steps from prompt, then execute each step
    (RBAC + worker proxy). Caller is the OpenClaw web UI.
    """
    graph = get_execution_graph()
    initial_state: dict = {
        "prompt": body.prompt,
        "user_id": body.user_id,
        "steps": [],
        "results": [],
        "current_index": 0,
        "done": False,
        "error": None,
        "pending_approval": False,
    }
    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.exception("Execute failed")
        raise HTTPException(status_code=500, detail=str(e))

    error = final_state.get("error")
    pending = final_state.get("pending_approval")
    results = final_state.get("results") or []

    if pending:
        return ExecuteResponse(status="pending_approval", output=results)
    if error:
        # When worker tool execution fails due to WebSocket token mismatch,
        # point the user to the README fix (gateway.remote.token on the worker).
        err_str = str(error)
        if "1008" in err_str and ("gateway token mismatch" in err_str or "gateway.remote.token" in err_str):
            err_str += "\n\nHint: On the OpenClaw worker, set gateway.remote.token to match gateway.auth.token (see README)."
        return ExecuteResponse(status="error", output=err_str)
    return ExecuteResponse(status="success", output=results)
