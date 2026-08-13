"""Memory context provider abstractions for direct CockroachDB and Managed MCP."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from orphanproof.mcp_integration import McpClientProtocol, McpIntegrationError
from orphanproof.models import MemoryContext, MemoryTransport
from orphanproof.repository import MemoryRepositoryProtocol
from orphanproof.service import MemoryService, ResourceNotFoundError


class MemoryContextProviderProtocol(Protocol):
    memory_transport: MemoryTransport

    def get_memory_context(self, resource_key: str) -> MemoryContext: ...


class DirectMemoryContextProvider:
    memory_transport = MemoryTransport.DIRECT_COCKROACHDB

    def __init__(
        self,
        repository: MemoryRepositoryProtocol,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._service = MemoryService(repository, now_provider=now_provider)

    def get_memory_context(self, resource_key: str) -> MemoryContext:
        return self._service.get_memory_context(resource_key)


class ManagedMcpMemoryContextProvider:
    memory_transport = MemoryTransport.COCKROACHDB_MANAGED_MCP

    def __init__(
        self,
        mcp_client: McpClientProtocol,
        row_mapper: Callable[[str, Any], MemoryContext] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._mcp_client = mcp_client
        self._row_mapper = row_mapper
        self._builder = MemoryService(_EmptyRepository(), now_provider=now_provider)

    def get_memory_context(self, resource_key: str) -> MemoryContext:
        if self._row_mapper is not None:
            try:
                result = self._mcp_client.call_tool(
                    "select_query",
                    {
                        "query": (
                            "SELECT resource_key FROM orphanproof.resources WHERE resource_key = $1"
                        ),
                        "params": [resource_key],
                    },
                )
            except McpIntegrationError:
                raise
            except Exception as exc:
                raise McpIntegrationError("MCP memory retrieval failed") from exc
            try:
                return self._row_mapper(resource_key, result)
            except ResourceNotFoundError:
                raise
            except Exception as exc:
                raise McpIntegrationError("MCP memory result could not be mapped") from exc

        try:
            resource_rows = self._select_rows(
                "select_query",
                """
                SELECT
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
                FROM orphanproof.resources
                WHERE resource_key = $1
                """,
                [resource_key],
            )
            if not resource_rows:
                raise ResourceNotFoundError(resource_key)
            resource = resource_rows[0]
            resource_id = str(resource["id"])
            raw_context = {
                "resource": resource,
                "memory_events": self._select_rows(
                    "select_query",
                    """
                    SELECT
                        id,
                        event_type,
                        summary,
                        evidence,
                        source,
                        occurred_at,
                        recorded_at
                    FROM orphanproof.memory_events
                    WHERE resource_id = $1
                    ORDER BY occurred_at ASC, recorded_at ASC
                    """,
                    [resource_id],
                ),
                "exceptions": self._select_rows(
                    "select_query",
                    """
                    SELECT
                        id,
                        reason,
                        approved_by,
                        approved_at,
                        expires_at,
                        status
                    FROM orphanproof.exceptions
                    WHERE resource_id = $1
                    ORDER BY approved_at DESC
                    """,
                    [resource_id],
                ),
                "historical_decisions": self._select_rows(
                    "select_query",
                    """
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
                    WHERE resource_id = $1
                    ORDER BY decided_at DESC
                    """,
                    [resource_id],
                ),
                "human_approvals": self._select_rows(
                    "select_query",
                    """
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
                    WHERE d.resource_id = $1
                    ORDER BY ha.reviewed_at DESC
                    """,
                    [resource_id],
                ),
            }
        except McpIntegrationError:
            raise
        except ResourceNotFoundError:
            raise
        except Exception as exc:
            raise McpIntegrationError("MCP memory retrieval failed") from exc
        return self._builder.build_memory_context_from_raw(raw_context)

    def _select_rows(self, tool_name: str, query: str, params: list[str]) -> list[dict[str, Any]]:
        result = self._mcp_client.call_tool(
            tool_name,
            {
                "query": query,
                "params": params,
            },
        )
        return _extract_rows(result)


class _EmptyRepository:
    def list_resources(
        self,
        resource_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return []

    def get_resource(self, resource_key: str) -> dict[str, Any] | None:
        return None

    def get_memory_events(self, resource_id: str) -> list[dict[str, Any]]:
        return []

    def get_exceptions(self, resource_id: str) -> list[dict[str, Any]]:
        return []

    def get_decisions(self, resource_id: str) -> list[dict[str, Any]]:
        return []

    def get_human_approvals(self, resource_id: str) -> list[dict[str, Any]]:
        return []

    def get_memory_context(self, resource_key: str) -> dict[str, Any] | None:
        return None


def _extract_rows(result: Any) -> list[dict[str, Any]]:
    if isinstance(result, list):
        return [dict(row) for row in result]
    if isinstance(result, dict):
        for key in ("rows", "results", "data"):
            rows = result.get(key)
            if isinstance(rows, list):
                return [dict(row) for row in rows]
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
                if isinstance(text, str):
                    parsed = json.loads(text)
                    return _extract_rows(parsed)
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return _extract_rows(structured)
    content = getattr(result, "content", None)
    if content is not None:
        return _extract_rows({"content": content})
    raise McpIntegrationError("MCP select_query result did not contain rows")
