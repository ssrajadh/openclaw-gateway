-- Audit log table for MVP (dual-phase sandwich pattern)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id TEXT,
    tool_call TEXT NOT NULL,
    raw_input JSONB,
    security_status TEXT NOT NULL,
    execution_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_security_status ON audit_logs (security_status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs (timestamp);
