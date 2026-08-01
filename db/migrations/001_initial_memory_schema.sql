SET CLUSTER SETTING feature.vector_index.enabled = true;

CREATE SCHEMA IF NOT EXISTS orphanproof;

CREATE TABLE IF NOT EXISTS orphanproof.resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_key TEXT UNIQUE NOT NULL,
    resource_type TEXT NOT NULL,
    region TEXT NOT NULL,
    created_by TEXT,
    created_via TEXT NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL,
    last_activity TIMESTAMPTZ,
    monthly_cost_estimate DECIMAL(12,2) NOT NULL DEFAULT 0,
    lifecycle_state TEXT NOT NULL,
    current_evidence JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_synthetic BOOL NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT resources_resource_type_check
        CHECK (resource_type IN ('EBS_VOLUME', 'ELASTIC_IP', 'RDS_INSTANCE')),
    CONSTRAINT resources_created_via_check
        CHECK (created_via IN ('MANUAL', 'TERRAFORM', 'CLOUDFORMATION', 'SERVICE', 'UNKNOWN')),
    CONSTRAINT resources_monthly_cost_estimate_check
        CHECK (monthly_cost_estimate >= 0)
);

CREATE TABLE IF NOT EXISTS orphanproof.memory_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id UUID NOT NULL REFERENCES orphanproof.resources(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::JSONB,
    source TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT memory_events_event_type_check
        CHECK (event_type IN ('CREATION', 'ACTIVITY', 'EXCEPTION', 'REJECTION', 'NOTE', 'DEPENDENCY', 'OWNERSHIP'))
);

CREATE TABLE IF NOT EXISTS orphanproof.exceptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id UUID NOT NULL REFERENCES orphanproof.resources(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approved_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT exceptions_status_check
        CHECK (status IN ('ACTIVE', 'EXPIRED', 'REVOKED'))
);

CREATE TABLE IF NOT EXISTS orphanproof.decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_id UUID NOT NULL REFERENCES orphanproof.resources(id) ON DELETE CASCADE,
    verdict TEXT NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL,
    blast_radius TEXT NOT NULL,
    evidence_summary TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    rollback_plan TEXT NOT NULL,
    human_status TEXT NOT NULL DEFAULT 'PENDING',
    decision_source TEXT NOT NULL DEFAULT 'AGENT',
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT decisions_verdict_check
        CHECK (verdict IN ('KEEP', 'QUARANTINE', 'REMOVE')),
    CONSTRAINT decisions_confidence_score_check
        CHECK (confidence_score BETWEEN 0 AND 100),
    CONSTRAINT decisions_human_status_check
        CHECK (human_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    CONSTRAINT decisions_decision_source_check
        CHECK (decision_source IN ('AGENT', 'HUMAN', 'SEED'))
);

CREATE TABLE IF NOT EXISTS orphanproof.decision_embeddings (
    decision_id UUID PRIMARY KEY REFERENCES orphanproof.decisions(id) ON DELETE CASCADE,
    memory_text TEXT NOT NULL,
    embedding VECTOR(1024) NOT NULL,
    embedding_model TEXT NOT NULL DEFAULT 'amazon.titan-embed-text-v2:0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orphanproof.human_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES orphanproof.decisions(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    rationale TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT human_approvals_status_check
        CHECK (status IN ('APPROVED', 'REJECTED'))
);

CREATE INDEX IF NOT EXISTS resources_type_state_idx
    ON orphanproof.resources (resource_type, lifecycle_state);

CREATE INDEX IF NOT EXISTS memory_events_resource_occurred_idx
    ON orphanproof.memory_events (resource_id, occurred_at);

CREATE INDEX IF NOT EXISTS exceptions_resource_status_idx
    ON orphanproof.exceptions (resource_id, status);

CREATE INDEX IF NOT EXISTS decisions_resource_decided_idx
    ON orphanproof.decisions (resource_id, decided_at);

CREATE INDEX IF NOT EXISTS decisions_verdict_human_status_idx
    ON orphanproof.decisions (verdict, human_status);

CREATE VECTOR INDEX IF NOT EXISTS decision_embeddings_cosine_idx
    ON orphanproof.decision_embeddings (embedding vector_cosine_ops);
