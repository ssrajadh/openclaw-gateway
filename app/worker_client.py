"""HTTP client for OpenClaw worker POST /tools/invoke."""

import httpx

from app.config import get_settings


class WorkerInvokeError(Exception):
    """Raised when /tools/invoke returns 4xx/5xx or invalid response."""

    def __init__(self, status_code: int | None, message: str, body: object = None):
        self.status_code = status_code
        self.message = message
        self.body = body
        super().__init__(message)


async def invoke_tool(
    tool: str,
    args: dict,
    *,
    action: str | None = None,
    session_key: str | None = None,
) -> dict:
    """
    Call the OpenClaw worker's POST /tools/invoke.
    Returns {"ok": True, "result": ...} or raises WorkerInvokeError.
    """
    settings = get_settings()
    url = settings.openclaw_worker_url.rstrip("/") + "/tools/invoke"
    headers: dict[str, str] = {
        "Content-Type": "application/json",
    }
    token = (settings.openclaw_worker_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body: dict = {"tool": tool, "args": args or {}}
    if action is not None:
        body["action"] = action
    if session_key is not None:
        body["sessionKey"] = session_key

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=body, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, dict) and data.get("ok") is True:
            return data
        raise WorkerInvokeError(
            resp.status_code,
            "Response ok but missing ok: true or result",
            data,
        )

    try:
        err_body = resp.json()
    except Exception:
        err_body = resp.text
    msg = "unknown"
    if isinstance(err_body, dict) and "error" in err_body:
        err = err_body["error"]
        if isinstance(err, dict) and "message" in err:
            msg = str(err["message"])
        else:
            msg = str(err)
    elif isinstance(err_body, str):
        msg = err_body
    raise WorkerInvokeError(resp.status_code, msg, err_body)
