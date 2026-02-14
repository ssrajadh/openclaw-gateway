"""LangGraph nodes: plan step and execute step (audit + worker)."""

from app.audit.service import create_pending_record, update_record
from app.worker_client import WorkerInvokeError, invoke_tool

# Type alias for graph state
GraphState = dict


async def plan_node(state: GraphState) -> GraphState:
    """
    Plan node: use LLM to map prompt -> list of { tool, args } steps.
    For Step 2 we use a simple structured output; the LLM returns JSON steps.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    from langchain_core.output_parsers import JsonOutputParser

    prompt = state.get("prompt") or ""
    if not prompt.strip():
        return {**state, "steps": [], "results": [], "done": True, "error": "Empty prompt"}

    parser = JsonOutputParser()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    system = (
        "You are a task planner. Given a user prompt, output a JSON array of steps. "
        "Each step must have exactly: \"tool\" (string, the OpenClaw tool name) and \"args\" (object). "
        "Use only tool names like: sessions_list, terminal.run, filesystem.read_text_file. "
        "Output only valid JSON, e.g. [{\"tool\": \"sessions_list\", \"args\": {}}]."
    )
    msg = HumanMessage(content=f"{system}\n\nUser prompt: {prompt}")
    try:
        response = await llm.ainvoke([msg])
        text = response.content if hasattr(response, "content") else str(response)
        # Parse JSON array
        steps = parser.parse(text)
        if not isinstance(steps, list):
            steps = [steps] if isinstance(steps, dict) else []
        normalized = []
        for s in steps:
            if isinstance(s, dict) and "tool" in s:
                normalized.append({
                    "tool": str(s["tool"]),
                    "args": s.get("args") if isinstance(s.get("args"), dict) else {},
                })
        return {**state, "steps": normalized, "current_index": 0, "results": [], "error": None}
    except Exception as e:
        return {**state, "steps": [], "results": [], "done": True, "error": str(e)}


async def execute_node(state: GraphState) -> GraphState:
    """
    Execute node: Phase A log (PENDING) -> invoke worker -> Phase B log (ALLOWED).
    """
    steps = state.get("steps") or []
    current_index = state.get("current_index", 0)
    results = list(state.get("results") or [])
    actor_id = state.get("user_id")

    if current_index >= len(steps):
        return {**state, "done": True, "results": results}

    step = steps[current_index]
    tool = step.get("tool", "")
    args = step.get("args") or {}

    if not tool:
        return {
            **state,
            "done": True,
            "results": results,
            "error": "Step missing tool",
        }

    # Phase A: Insert PENDING audit record
    audit_id = await create_pending_record(actor_id=actor_id, tool_call=tool, raw_input=args)

    try:
        out = await invoke_tool(tool, args)
        results.append({"tool": tool, "ok": True, "result": out.get("result")})
        # Phase B: Update with ALLOWED + execution result
        await update_record(
            audit_id=audit_id,
            security_status="ALLOWED",
            execution_result={"ok": True, "result": out.get("result")},
        )
    except WorkerInvokeError as e:
        results.append({"tool": tool, "ok": False, "error": e.message})
        await update_record(
            audit_id=audit_id,
            security_status="ALLOWED",
            execution_result={"ok": False, "error": e.message},
        )
        return {
            **state,
            "done": True,
            "results": results,
            "error": e.message,
        }
    except Exception as e:
        msg = str(e)
        results.append({"tool": tool, "ok": False, "error": msg})
        await update_record(
            audit_id=audit_id,
            security_status="ALLOWED",
            execution_result={"ok": False, "error": msg},
        )
        return {
            **state,
            "done": True,
            "results": results,
            "error": msg,
        }

    next_index = current_index + 1
    if next_index >= len(steps):
        return {**state, "current_index": next_index, "results": results, "done": True}
    return {**state, "current_index": next_index, "results": results, "done": False}
