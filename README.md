# OpenClaw Gateway

**OpenClaw Gateway** is an open-source governance and security gateway designed for the [OpenClaw](https://github.com/openclaw/openclaw) ecosystem. It bridges the gap between viral autonomous agents and the strict security requirements of the modern enterprise.

## Why OpenClaw Gateway?
OpenClaw (formerly Moltbot/Clawdbot) is "Claude with hands," but those hands have too much power. Enterprises are blocking OpenClaw because it lacks audit trails and granular permissions. **OpenClaw Gateway fixes this.**

It acts as a **Model Context Protocol (MCP) Proxy**, intercepting every action an agent takes and applying enterprise-grade guardrails before execution.

## Key Features
- **Real-time Audit Logging:** Every shell command, API call, and file access is logged to a persistent PostgreSQL store.
- **Command Guardrails:** Prevent destructive actions (e.g., `rm -rf /`, `curl | bash`) via regex and LLM-based vetting.
- **RBAC for Agents:** Assign "Least Privilege" scopes to your agents (e.g., "Can read JIRA, cannot write to Production Terminal").
- **Human-in-the-Loop (HITL):** Pause high-risk actions and require manual approval via WhatsApp or a secure Web Dashboard.
- **MCP Native:** Plugs into the existing 100+ OpenClaw skills ecosystem with zero configuration.

## 🛠️ Tech Stack
- **Engine:** Python 3.12+ (FastAPI)
- **Orchestration:** LangGraph (for complex reasoning vetting)
- **Database:** PostgreSQL (Audit & State)
- **Protocol:** Model Context Protocol (MCP)
