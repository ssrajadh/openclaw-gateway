"""FastAPI app: /health, /execute, and /audit."""

import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Query

logger = logging.getLogger(__name__)
from pydantic import BaseModel

from app.audit.service import list_audit_logs
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


@app.get("/audit")
async def get_audit(
    status: str | None = Query(None, description="Filter by security_status (e.g. ALLOWED, PENDING)"),
    actor_id: str | None = Query(None, description="Filter by actor_id"),
    limit: int = Query(10, description="Number of records to return"),
):
    """
    Forensic retrieval: list audit log entries, optionally filtered by status.
    Example: GET /audit?status=ALLOWED&limit=5
    """
    try:
        records = await list_audit_logs(status=status, actor_id=actor_id, limit=limit)
        return {"records": records}
    except Exception as e:
        logger.exception("Audit retrieval failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit/pretty")
async def get_audit_pretty(
    actor_id: str | None = Query(None, description="Filter by actor_id"),
    limit: int = Query(10, description="Number of records to return"),
):
    """Get audit logs in a pretty, human-readable format"""
    try:
        logs = await list_audit_logs(actor_id=actor_id, limit=limit)
        
        if not logs:
            return {"message": "No audit logs found"}
        
        output = []
        output.append("=" * 120)
        output.append(f"{'ID':<5} {'USER':<15} {'TOOL':<25} {'STATUS':<12} {'RESULT':<10} {'TIME':<25}")
        output.append("=" * 120)
        
        for log in logs:
            result_str = "✓ OK" if log.get("execution_result") and log["execution_result"].get("ok") else "✗ FAIL"
            time_str = log["created_at"][:19] if log.get("created_at") else "N/A"
            
            output.append(
                f"{log['id']:<5} {log['actor_id']:<15} {log['tool_call']:<25} "
                f"{log['security_status']:<12} {result_str:<10} {time_str:<25}"
            )
            
            # Show input details
            if log.get("raw_input"):
                input_str = str(log["raw_input"])
                if len(input_str) > 80:
                    input_str = input_str[:77] + "..."
                output.append(f"      Input: {input_str}")
            
            # Show error details for failures
            if log.get("execution_result") and not log["execution_result"].get("ok"):
                error = log["execution_result"].get("error", "Unknown error")
                if len(error) > 80:
                    error = error[:77] + "..."
                output.append(f"      Error: {error}")
            
            output.append("-" * 120)
        
        output.append(f"\nTotal records: {len(logs)}")
        output.append("=" * 120)
        
        return {"formatted_logs": "\n".join(output)}
    except Exception as e:
        logger.exception("Pretty audit retrieval failed")
        raise HTTPException(status_code=500, detail=str(e))


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
