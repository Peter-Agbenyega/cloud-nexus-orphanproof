"""Typed response models for Phase P3 evidence retrieval."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class ResourceType(StrEnum):
    EBS_VOLUME = "EBS_VOLUME"
    ELASTIC_IP = "ELASTIC_IP"
    RDS_INSTANCE = "RDS_INSTANCE"


class CreationMethod(StrEnum):
    MANUAL = "MANUAL"
    TERRAFORM = "TERRAFORM"
    CLOUDFORMATION = "CLOUDFORMATION"
    SERVICE = "SERVICE"
    UNKNOWN = "UNKNOWN"


class EventType(StrEnum):
    CREATION = "CREATION"
    ACTIVITY = "ACTIVITY"
    EXCEPTION = "EXCEPTION"
    REJECTION = "REJECTION"
    NOTE = "NOTE"
    DEPENDENCY = "DEPENDENCY"
    OWNERSHIP = "OWNERSHIP"


class ExceptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class Verdict(StrEnum):
    KEEP = "KEEP"
    QUARANTINE = "QUARANTINE"
    REMOVE = "REMOVE"


class HumanStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PhaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ResourceSummary(PhaseModel):
    id: UUID
    resource_key: str
    resource_type: ResourceType
    region: str
    created_via: CreationMethod
    last_activity: datetime | None = None
    monthly_cost_estimate: Decimal
    lifecycle_state: str
    is_synthetic: bool

    @field_serializer("monthly_cost_estimate")
    def serialize_cost(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ResourceDetail(ResourceSummary):
    created_by: str | None = None
    first_seen: datetime
    current_evidence: dict[str, Any] = Field(default_factory=dict)


class MemoryEvent(PhaseModel):
    id: UUID
    event_type: EventType
    summary: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: str
    occurred_at: datetime
    recorded_at: datetime


class ResourceException(PhaseModel):
    id: UUID
    reason: str
    approved_by: str
    approved_at: datetime
    expires_at: datetime | None = None
    status: ExceptionStatus


class HistoricalDecision(PhaseModel):
    id: UUID
    verdict: Verdict
    confidence_score: Decimal
    blast_radius: str
    evidence_summary: str
    recommended_action: str
    rollback_plan: str
    human_status: HumanStatus
    decision_source: str
    decided_at: datetime

    @field_serializer("confidence_score")
    def serialize_confidence(self, value: Decimal) -> str:
        return f"{value:.2f}"


class HumanApproval(PhaseModel):
    id: UUID
    decision_id: UUID
    decision_verdict: Verdict
    status: HumanStatus
    reviewer: str
    rationale: str
    reviewed_at: datetime


class EvidenceCounts(PhaseModel):
    total_memory_events: int
    active_exceptions: int
    expired_exceptions: int
    historical_decisions: int
    human_approvals: int


class EvidenceSignals(PhaseModel):
    active_exception_exists: bool
    expired_exception_exists: bool
    dependency_evidence_exists: bool
    ownership_evidence_exists: bool
    creation_evidence_exists: bool
    activity_evidence_exists: bool
    prior_keep_exists: bool
    prior_quarantine_exists: bool
    prior_remove_exists: bool


class MemoryContext(PhaseModel):
    resource: ResourceDetail
    memory_events: list[MemoryEvent]
    exceptions: list[ResourceException]
    historical_decisions: list[HistoricalDecision]
    human_approvals: list[HumanApproval]
    evidence_counts: EvidenceCounts
    evidence_signals: EvidenceSignals
    analysis_mode: Literal["evidence_only"] = "evidence_only"
    ai_verdict_generated: Literal[False] = False
    planned_capabilities: list[str] = Field(
        default_factory=lambda: [
            "MCP retrieval",
            "vector similarity retrieval",
            "Amazon Bedrock reasoning",
            "current AI verdict generation",
        ]
    )


class MemoryTransport(StrEnum):
    DIRECT_COCKROACHDB = "direct_cockroachdb"
    COCKROACHDB_MANAGED_MCP = "cockroachdb_managed_mcp"
    TEST_FAKE = "test_fake"


class CurrentAIVerdict(PhaseModel):
    verdict: Verdict
    confidence_score: int = Field(ge=0, le=100)
    evidence_summary: str = Field(min_length=1)
    blast_radius: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
    rollback_plan: str = Field(min_length=1)
    human_review_required: Literal[True] = True

    @model_validator(mode="after")
    def reject_execution_claims(self) -> CurrentAIVerdict:
        destructive_claims = (
            "deleted",
            "terminated",
            "released",
            "detached",
            "modified",
            "stopped",
            "removed the resource",
            "action taken",
        )
        combined = " ".join(
            [
                self.evidence_summary,
                self.blast_radius,
                self.recommended_action,
                self.rollback_plan,
            ]
        ).lower()
        if any(claim in combined for claim in destructive_claims):
            raise ValueError("current verdict must not claim a destructive action occurred")
        return self


class SimilarHistoricalDecision(PhaseModel):
    decision_id: UUID
    resource_key: str
    resource_type: ResourceType
    lifecycle_state: str
    historical_verdict: Verdict
    distance: float = Field(ge=0)
    similarity: float
    evidence_summary: str
    recommended_action: str
    blast_radius: str
    rollback_plan: str


class ManagedMcpCapabilityReport(PhaseModel):
    provider: Literal["cockroachdb_cloud_managed_mcp"] = "cockroachdb_cloud_managed_mcp"
    configured: bool
    connected: bool
    read_only_policy: Literal[True] = True
    allowed_tools: list[str]
    write_tools_allowed: Literal[False] = False
    error: str | None = None


class P4AnalysisResponse(PhaseModel):
    resource: ResourceDetail
    current_ai_verdict: CurrentAIVerdict
    similar_historical_decisions: list[SimilarHistoricalDecision]
    evidence_signals: EvidenceSignals
    memory_transport: MemoryTransport
    embedding_model: str
    reasoning_model: str
    analysis_mode: Literal["ai_assisted"] = "ai_assisted"
    ai_verdict_generated: Literal[True] = True
    decision_persisted: Literal[False] = False
    automatic_action_taken: Literal[False] = False
    human_review_required: Literal[True] = True
    vector_neighbors_used: int = Field(ge=0, le=5)


class HealthResponse(PhaseModel):
    status: str
    service: str
    version: str
    phase: str
    environment: str
    database_mode: str
    analysis_mode: Literal["evidence_only"] = "evidence_only"
    ai_verdict_generated: Literal[False] = False


class DemoResourceLinks(PhaseModel):
    resource: str
    memory_context: str


class DemoResource(PhaseModel):
    resource_key: str
    story: str
    description: str
    is_synthetic: bool
    links: DemoResourceLinks
    analysis_mode: Literal["evidence_only"] = "evidence_only"
    ai_verdict_generated: Literal[False] = False

    @field_validator("is_synthetic")
    @classmethod
    def require_synthetic_demo(cls, value: bool) -> bool:
        if not value:
            raise ValueError("P3 demo resources must be synthetic")
        return value
