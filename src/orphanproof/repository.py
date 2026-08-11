"""Read-only repository for persistent memory records."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Protocol

from orphanproof.database import Database

MAX_RESOURCE_LIMIT = 100
RESOURCE_COLUMNS = """
    id,
    resource_key,
    resource_type,
    region,
    created_by,
    created_via,
    first_seen,
    last_activity,
    monthly_cost_estimate,
    lifecycle_state,
    current_evidence,
    is_synthetic
"""


class MemoryRepositoryProtocol(Protocol):
    def list_resources(
        self,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...

    def get_resource(self, resource_key: str) -> dict[str, Any] | None: ...

    def get_memory_events(self, resource_id: str) -> list[dict[str, Any]]: ...

    def get_exceptions(self, resource_id: str) -> list[dict[str, Any]]: ...

    def get_decisions(self, resource_id: str) -> list[dict[str, Any]]: ...

    def get_human_approvals(self, resource_id: str) -> list[dict[str, Any]]: ...

    def get_memory_context(self, resource_key: str) -> dict[str, Any] | None: ...


class ReadOnlyQueryError(RuntimeError):
    """Raised when repository SQL does not meet the P3 read-only contract."""


def validate_pagination(limit: int, offset: int) -> None:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit > MAX_RESOURCE_LIMIT:
        raise ValueError("limit must be less than or equal to 100")
    if offset < 0:
        raise ValueError("offset must be non-negative")


def _assert_select_only(sql: str) -> None:
    normalized = sql.strip()
    if not re.match(r"^SELECT\b", normalized, re.I):
        raise ReadOnlyQueryError("repository queries must be SELECT-only")
    blocked = re.compile(r"\b(INSERT|UPDATE|UPSERT|DELETE|DROP|TRUNCATE|ALTER|CREATE)\b", re.I)
    if blocked.search(normalized):
        raise ReadOnlyQueryError("repository query contains a blocked SQL operation")


def _fetch_all(database: Database, sql: str, params: Sequence[Any]) -> list[dict[str, Any]]:
    _assert_select_only(sql)
    with database.connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())


def _fetch_one(database: Database, sql: str, params: Sequence[Any]) -> dict[str, Any] | None:
    rows = _fetch_all(database, sql, params)
    return rows[0] if rows else None


class MemoryRepository:
    """Retrieves persistent memory without mutating database state."""

    def __init__(self, database: Database):
        self._database = database

    def list_resources(
        self,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        validate_pagination(limit, offset)
        if resource_type:
            sql = f"""
                SELECT {RESOURCE_COLUMNS}
                FROM orphanproof.resources
                WHERE resource_type = %s
                ORDER BY resource_key ASC
                LIMIT %s OFFSET %s
            """
            params: tuple[Any, ...] = (resource_type, limit, offset)
        else:
            sql = f"""
                SELECT {RESOURCE_COLUMNS}
                FROM orphanproof.resources
                ORDER BY resource_key ASC
                LIMIT %s OFFSET %s
            """
            params = (limit, offset)
        return _fetch_all(self._database, sql, params)

    def get_resource(self, resource_key: str) -> dict[str, Any] | None:
        sql = f"""
            SELECT {RESOURCE_COLUMNS}
            FROM orphanproof.resources
            WHERE resource_key = %s
        """
        return _fetch_one(self._database, sql, (resource_key,))

    def get_memory_events(self, resource_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT
                id,
                event_type,
                summary,
                evidence,
                source,
                occurred_at,
                recorded_at
            FROM orphanproof.memory_events
            WHERE resource_id = %s
            ORDER BY occurred_at ASC, recorded_at ASC
        """
        return _fetch_all(self._database, sql, (resource_id,))

    def get_exceptions(self, resource_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT
                id,
                reason,
                approved_by,
                approved_at,
                expires_at,
                status
            FROM orphanproof.exceptions
            WHERE resource_id = %s
            ORDER BY
                CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END ASC,
                approved_at DESC
        """
        return _fetch_all(self._database, sql, (resource_id,))

    def get_decisions(self, resource_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT
                id,
                verdict,
                confidence_score,
                blast_radius,
                evidence_summary,
                recommended_action,
                rollback_plan,
                human_status,
                decision_source,
                decided_at
            FROM orphanproof.decisions
            WHERE resource_id = %s
            ORDER BY decided_at DESC
        """
        return _fetch_all(self._database, sql, (resource_id,))

    def get_human_approvals(self, resource_id: str) -> list[dict[str, Any]]:
        sql = """
            SELECT
                ha.id,
                ha.decision_id,
                d.verdict AS decision_verdict,
                ha.status,
                ha.reviewer,
                ha.rationale,
                ha.reviewed_at
            FROM orphanproof.human_approvals AS ha
            INNER JOIN orphanproof.decisions AS d
                ON d.id = ha.decision_id
            WHERE d.resource_id = %s
            ORDER BY ha.reviewed_at DESC
        """
        return _fetch_all(self._database, sql, (resource_id,))

    def get_memory_context(self, resource_key: str) -> dict[str, Any] | None:
        resource = self.get_resource(resource_key)
        if resource is None:
            return None
        resource_id = str(resource["id"])
        return {
            "resource": resource,
            "memory_events": self.get_memory_events(resource_id),
            "exceptions": self.get_exceptions(resource_id),
            "historical_decisions": self.get_decisions(resource_id),
            "human_approvals": self.get_human_approvals(resource_id),
        }
