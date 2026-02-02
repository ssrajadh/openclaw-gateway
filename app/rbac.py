"""RBAC stub: allowed tools per user. Step 3 will replace with policies.yaml."""


def allowed_tools(user_id: str | None) -> set[str]:
    """
    Return the set of tool names the user is allowed to invoke.
    Step 2: fixed set for testing. Step 3: load from policies.yaml and roles.
    """
    # Allow all for now so execution path is testable
    return {"*"}


def is_tool_allowed(user_id: str | None, tool: str) -> bool:
    """True if user is allowed to invoke this tool."""
    allowed = allowed_tools(user_id)
    if "*" in allowed:
        return True
    return tool in allowed
