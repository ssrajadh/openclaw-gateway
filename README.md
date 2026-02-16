# OpenClaw Gateway

**OpenClaw Gateway** is an open-source governance and security gateway designed for the [OpenClaw](https://github.com/openclaw/openclaw) ecosystem. It bridges the gap between viral autonomous agents and the strict security requirements of the modern enterprise.

## Why OpenClaw Gateway?
OpenClaw (formerly Moltbot/Clawdbot) is "Claude with hands," but those hands have too much power. Enterprises are blocking OpenClaw because it lacks audit trails and granular permissions. **OpenClaw Gateway fixes this.**

It acts as a **Model Context Protocol (MCP) Proxy**, intercepting every action an agent takes and applying enterprise-grade guardrails before execution.

## Key Features
- **Real-time Audit Logging:** Every shell command, API call, and file access is logged to a persistent PostgreSQL store.
- **Command Guardrails:** Prevent destructive actions (e.g., `rm -rf /`, `curl | bash`) via regex and LLM-based vetting.
- **Human-in-the-Loop (HITL):** Pause high-risk actions and require manual approval via WhatsApp or a secure Web Dashboard.
- **MCP Native:** Plugs into the existing 100+ OpenClaw skills ecosystem with zero configuration.

## Tech Stack
- **Engine:** Python 3.12+ (FastAPI)
- **Orchestration:** LangGraph (for complex reasoning vetting)
- **Database:** PostgreSQL (Audit & State)
- **Protocol:** Model Context Protocol (MCP)

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
   - `PORT` — Port for this FastAPI app (default `8000`).

3. **Run the gateway:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Or use the port from `.env`: `uvicorn app.main:app --host 0.0.0.0 --port $(grep PORT .env | cut -d= -f2)`.

4. **Endpoints:**
   - `GET /health` — Health check.
   - `POST /execute` — Run a task. Body: `{"prompt": "list my sessions", "user_id": null}`. Response: `{"status": "success"|"error"|"pending_approval", "output": ...}`.
   - `GET /audit` — Forensic retrieval of audit logs. Query: `?status=ALLOWED` or `?status=PENDING` to filter.

5. **Docker (FastAPI + PostgreSQL):**
   ```bash
   docker compose up -d
   ```
   Requires `DATABASE_URL` (set automatically by docker-compose). Ensure PostgreSQL is up before the gateway starts.

6. **Tests:**
   ```bash
   pytest
   ```
