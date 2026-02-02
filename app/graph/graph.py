"""LangGraph build: plan -> execute loop -> end."""

from langgraph.graph import StateGraph, END

from app.graph.nodes import plan_node, execute_node

# State: prompt, user_id, steps, results, current_index, done, error, pending_approval
GraphState = dict


def _route_after_execute(state: GraphState) -> str:
    """If done or error, end; else loop back to execute."""
    if state.get("done") or state.get("error"):
        return "end"
    return "execute"


def build_graph() -> StateGraph:
    """Build the plan -> execute loop graph."""
    builder = StateGraph(GraphState)

    builder.add_node("plan", plan_node)
    builder.add_node("execute", execute_node)

    builder.set_entry_point("plan")
    builder.add_edge("plan", "execute")
    builder.add_conditional_edges(
        "execute",
        _route_after_execute,
        {"execute": "execute", "end": END},
    )

    return builder.compile()


# Singleton compiled graph for the app
_execution_graph = None


def get_execution_graph():
    global _execution_graph
    if _execution_graph is None:
        _execution_graph = build_graph()
    return _execution_graph
