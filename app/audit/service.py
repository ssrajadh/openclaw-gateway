"""Audit service: Phase A (create PENDING), Phase B (update with result), and retrieval."""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.db import get_session


async def create_pending_record(
    actor_id: str | None,
    tool_call: str,
    raw_input: dict[str, Any],
) -> int:
    """
    Phase A: Insert a PENDING audit record. Returns the row id for Phase B update.
    """
    async with get_session() as session:
        result = await session.execute(
            text("""
                INSERT INTO audit_logs (
                    timestamp, actor_id, tool_call, raw_input,
                    security_status, created_at
                )
                VALUES (
                    :timestamp, :actor_id, :tool_call, :raw_input::jsonb,
                    'PENDING', :created_at
                )
                RETURNING id
            """),
            {
                "timestamp": datetime.now(timezone.utc),
                "actor_id": actor_id,
                "tool_call": tool_call,
                "raw_input": json.dumps(raw_input) if raw_input else "{}",
                "created_at": datetime.now(timezone.utc),
            },
        )
        row = result.fetchone()
        return row[0]


async def update_record(
    audit_id: int,
    security_status: str,
    execution_result: dict[str, Any] | None,
) -> None:
    """
    Phase B: Update the audit record with execution result and final status.
    """
    async with get_session() as session:
        await session.execute(
            text("""
                UPDATE audit_logs
                SET security_status = :security_status,
                    execution_result = :execution_result::jsonb,
                    updated_at = :updated_at
                WHERE id = :audit_id
            """),
            {
                "audit_id": audit_id,
                "security_status": security_status,
                "execution_result": json.dumps(execution_result) if execution_result else "null",
                "updated_at": datetime.now(timezone.utc),
            },
        )


async def list_audit_logs(status: str | None = None) -> list[dict[str, Any]]:
    """
    Retrieve audit records, optionally filtered by security_status.
    """
    async with get_session() as session:
        if status:
            result = await session.execute(
                text("""
                    SELECT id, timestamp, actor_id, tool_call, raw_input,
                           security_status, execution_result, created_at, updated_at
                    FROM audit_logs
                    WHERE security_status = :status
                    ORDER BY timestamp DESC
                """),
                {"status": status},
            )
        else:
            result = await session.execute(
                text("""
                    SELECT id, timestamp, actor_id, tool_call, raw_input,
                           security_status, execution_result, created_at, updated_at
                    FROM audit_logs
                    ORDER BY timestamp DESC
                """),
            )
        rows = result.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1].isoformat() if r[1] else None,
                "actor_id": r[2],
                "tool_call": r[3],
                "raw_input": r[4],
                "security_status": r[5],
                "execution_result": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
                "updated_at": r[8].isoformat() if r[8] else None,
            }
            for r in rows
        ]
