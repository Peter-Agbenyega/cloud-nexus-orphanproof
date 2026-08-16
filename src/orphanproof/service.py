"""Evidence-only memory retrieval service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from orphanproof.models import (
    EventType,
    EvidenceCounts,
    EvidenceSignals,
    ExceptionStatus,
    HistoricalDecision,
    HumanApproval,
    MemoryContext,
    MemoryEvent,
    ResourceDetail,
    ResourceException,
    ResourceSummary,
    VectorMemoryResponse,
    Verdict,
)
from orphanproof.repository import MAX_RESOURCE_LIMIT, MemoryRepositoryProtocol


class ResourceNotFoundError(LookupError):
    """Raised when a resource key is not known to OrphanProof memory."""


class InvalidPaginationError(ValueError):
    """Raised when pagination values exceed the P3 repository contract."""


class MemoryService:
    def __init__(
        self,
        repository: MemoryRepositoryProtocol,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self._repository = repository
        self._now_provider = now_provider or self._utc_now

    def list_resources(
        self,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ResourceSummary]:
        self._validate_pagination(limit, offset)
        rows = self._repository.list_resources(
            resource_type=resource_type, limit=limit, offset=offset
        )
        return [ResourceSummary.model_validate(row) for row in rows]

    def get_resource(self, resource_key: str) -> ResourceDetail:
        row = self._repository.get_resource(resource_key)
        if row is None:
            raise ResourceNotFoundError(resource_key)
        return ResourceDetail.model_validate(row)

    def get_memory_context(self, resource_key: str) -> MemoryContext:
        raw_context = self._repository.get_memory_context(resource_key)
        if raw_context is None:
            raise ResourceNotFoundError(resource_key)
        return self.build_memory_context_from_raw(raw_context)

    def build_memory_context_from_raw(self, raw_context: dict[str, Any]) -> MemoryContext:
        resource = ResourceDetail.model_validate(raw_context["resource"])
        events = [MemoryEvent.model_validate(row) for row in raw_context["memory_events"]]
        exceptions = [ResourceException.model_validate(row) for row in raw_context["exceptions"]]
        decisions = [
            HistoricalDecision.model_validate(row) for row in raw_context["historical_decisions"]
        ]
        approvals = [HumanApproval.model_validate(row) for row in raw_context["human_approvals"]]
        now = self._current_time()
        return MemoryContext(
            resource=resource,
            memory_events=events,
            exceptions=exceptions,
            historical_decisions=decisions,
            human_approvals=approvals,
            evidence_counts=self._build_counts(events, exceptions, decisions, approvals, now),
            evidence_signals=self._build_signals(events, exceptions, decisions, now),
        )

    def get_demo_links(self) -> dict[str, Any]:
        return {
            "analysis_mode": "evidence_only",
            "ai_verdict_generated": False,
            "planned_capabilities": [
                "MCP retrieval",
                "vector similarity retrieval",
                "Amazon Bedrock reasoning",
                "current AI verdict generation",
            ],
            "resources": [
                {
                    "resource_key": "demo-rds-dr-standby-001",
                    "story": "RDS disaster-recovery standby",
                    "description": (
                        "Synthetic disaster-recovery standby story. The API returns stored "
                        "evidence only and does not generate a new AI verdict."
                    ),
                    "is_synthetic": True,
                    "links": {
                        "resource": "/api/v1/resources/demo-rds-dr-standby-001",
                        "memory_context": (
                            "/api/v1/resources/demo-rds-dr-standby-001/memory-context"
                        ),
                    },
                },
                {
                    "resource_key": "demo-ebs-abandoned-001",
                    "story": "Abandoned EBS volume investigation",
                    "description": (
                        "Synthetic abandoned-volume investigation story. The API returns stored "
                        "evidence only and does not generate a new AI verdict."
                    ),
                    "is_synthetic": True,
                    "links": {
                        "resource": "/api/v1/resources/demo-ebs-abandoned-001",
                        "memory_context": (
                            "/api/v1/resources/demo-ebs-abandoned-001/memory-context"
                        ),
                    },
                },
            ],
        }

    def build_vector_memory_response(
        self,
        context: MemoryContext,
        embedding_model: str,
        memory_transport: str,
        similar_historical_decisions: list[Any],
    ) -> VectorMemoryResponse:
        return VectorMemoryResponse(
            resource_key=context.resource.resource_key,
            embedding_model=embedding_model,
            memory_transport=memory_transport,
            similar_historical_decisions=similar_historical_decisions,
            evidence_signals=context.evidence_signals,
            vector_neighbors_used=len(similar_historical_decisions),
        )

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        if limit < 1:
            raise InvalidPaginationError("limit must be at least 1")
        if limit > MAX_RESOURCE_LIMIT:
            raise InvalidPaginationError("limit must be at most 100")
        if offset < 0:
            raise InvalidPaginationError("offset must be non-negative")

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC)

    def _current_time(self) -> datetime:
        return self._now_provider().astimezone(UTC)

    @staticmethod
    def _exception_is_effectively_active(
        exception: ResourceException,
        now: datetime,
    ) -> bool:
        return exception.status == ExceptionStatus.ACTIVE and (
            exception.expires_at is None or exception.expires_at.astimezone(UTC) > now
        )

    @classmethod
    def _exception_is_effectively_expired(
        cls,
        exception: ResourceException,
        now: datetime,
    ) -> bool:
        return exception.status == ExceptionStatus.EXPIRED or (
            exception.status == ExceptionStatus.ACTIVE
            and exception.expires_at is not None
            and exception.expires_at.astimezone(UTC) <= now
        )

    @classmethod
    def _build_counts(
        cls,
        events: list[MemoryEvent],
        exceptions: list[ResourceException],
        decisions: list[HistoricalDecision],
        approvals: list[HumanApproval],
        now: datetime,
    ) -> EvidenceCounts:
        return EvidenceCounts(
            total_memory_events=len(events),
            active_exceptions=sum(
                cls._exception_is_effectively_active(exception, now) for exception in exceptions
            ),
            expired_exceptions=sum(
                cls._exception_is_effectively_expired(exception, now) for exception in exceptions
            ),
            historical_decisions=len(decisions),
            human_approvals=len(approvals),
        )

    @classmethod
    def _build_signals(
        cls,
        events: list[MemoryEvent],
        exceptions: list[ResourceException],
        decisions: list[HistoricalDecision],
        now: datetime,
    ) -> EvidenceSignals:
        event_types = {event.event_type for event in events}
        verdicts = {decision.verdict for decision in decisions}
        return EvidenceSignals(
            active_exception_exists=any(
                cls._exception_is_effectively_active(exception, now) for exception in exceptions
            ),
            expired_exception_exists=any(
                cls._exception_is_effectively_expired(exception, now) for exception in exceptions
            ),
            dependency_evidence_exists=EventType.DEPENDENCY in event_types,
            ownership_evidence_exists=EventType.OWNERSHIP in event_types,
            creation_evidence_exists=EventType.CREATION in event_types,
            activity_evidence_exists=EventType.ACTIVITY in event_types,
            prior_keep_exists=Verdict.KEEP in verdicts,
            prior_quarantine_exists=Verdict.QUARANTINE in verdicts,
            prior_remove_exists=Verdict.REMOVE in verdicts,
        )
