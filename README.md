# OpenClaw Gateway

**OpenClaw Gateway** is an open-source governance and security gateway designed for the [OpenClaw](https://github.com/openclaw/openclaw) ecosystem. It bridges the gap between viral autonomous agents and the strict security requirements of the modern enterprise.

## Why OpenClaw Gateway?

OpenClaw (formerly Moltbot/Clawdbot) is "Claude with hands," but those hands have too much power. Enterprises are blocking OpenClaw because it lacks audit trails and granular permissions. **OpenClaw Gateway fixes this** by providing audit logging, guardrails, and human-in-the-loop controls.

## MVP (Current)

What's implemented today:

- **Prompt-based orchestration** — Call `POST /execute` with a prompt; the gateway uses an LLM (LangGraph) to plan tool steps, then executes them via the OpenClaw worker's HTTP API.
- **Dual-phase audit logging (sandwich pattern)** — Every tool call is logged *before* execution (PENDING) and *after* (ALLOWED), so evidence exists even if execution fails or crashes.
- **PostgreSQL audit store** — Structured schema: actor_id, tool_call, raw_input, security_status, execution_result, timestamps.
- **Forensic retrieval API** — `GET /audit?status=ALLOWED` and `GET /audit/pretty` to query and inspect logs.
- **Docker Compose** — FastAPI + PostgreSQL for local or VPS deployment.
- **Worker + Tavily integration** — Calls OpenClaw worker `POST /tools/invoke` for tools like `sessions_list`, and Tavily API for web search.

## Planned / Future

Not yet implemented:

- **MCP Proxy** — Sit in the middle of OpenClaw's native MCP traffic to intercept and log tool calls from the UI/agent directly, not just via the gateway's `/execute` endpoint.
- **Risk scoring & blocking** — Keyword-based or LLM-based detection of high-risk commands (e.g. `rm -rf`, `sudo`); block or flag before execution.
- **Human-in-the-Loop (HITL)** — Pause high-risk actions and require manual approval via WhatsApp, Slack, or a web dashboard before execution.
- **request_id linking** — Correlate multiple tool calls to a single prompt/request for forensic traceability.
- **Intent field** — LLM-summarized intent for each command (e.g. "Delete root filesystem") for security context.

## Tech Stack

- **Engine:** Python 3.12+ (FastAPI)
- **Orchestration:** LangGraph (plan + execute)
- **Database:** PostgreSQL (audit logs)

## Running the gateway

1. **Install dependencies** (from repo root):
   ```bash
   pip install -e ".[dev]"
   ```
   Or with uv: `uv pip install -e ".[dev]"`

2. **Configure environment.** Copy `.env.example` to `.env` and set:
   - `OPENCLAW_WORKER_URL` — Base URL of the OpenClaw worker (e.g. `http://127.0.0.1:18789` or an ngrok URL if the worker is behind a tunnel).
   - `OPENCLAW_WORKER_TOKEN` — Bearer token for the worker’s `/tools/invoke` endpoint (must match the worker’s gateway auth token).
   - `OPENAI_API_KEY` — OpenAI API key (required for the plan node; used by LangChain to turn prompts into tool steps).
   - `DATABASE_URL` — PostgreSQL URL for audit logs (default: `postgresql+asyncpg://gateway:gateway@localhost:5432/gateway`).
   - `PORT` — Port for this FastAPI app (default `8000`).

3. **Run the gateway:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Or use the port from `.env`: `uvicorn app.main:app --host 0.0.0.0 --port $(grep PORT .env | cut -d= -f2)`.

4. **Endpoints:**
   - `GET /health` — Health check.
   - `POST /execute` — Run a task. Body: `{"prompt": "list my sessions", "user_id": null}`. Response: `{"status": "success"|"error"|"pending_approval", "output": ...}`.
   - `GET /audit` — Forensic retrieval. Query: `?status=ALLOWED`, `?status=PENDING`, `?actor_id=...`, `?limit=...`.
   - `GET /audit/pretty` — Human-readable formatted audit logs.

5. **Docker (FastAPI + PostgreSQL):**
   ```bash
   docker compose up -d
   ```
   Requires `DATABASE_URL` (set automatically by docker-compose). Ensure PostgreSQL is up before the gateway starts.

6. **Tests:**
   ```bash
   pytest
   ```
