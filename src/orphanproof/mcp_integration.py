"""CockroachDB Cloud Managed MCP read-only integration."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from orphanproof.config import Settings
from orphanproof.models import ManagedMcpCapabilityReport

MCP_PROVIDER = "cockroachdb_cloud_managed_mcp"
ALLOWED_MCP_TOOLS = frozenset(
    {
        "list_databases",
        "list_tables",
        "get_table_schema",
        "select_query",
        "explain_query",
    }
)
DENIED_MCP_TOOLS = frozenset(
    {
        "create_database",
        "create_table",
        "insert_rows",
        "update_rows",
        "delete_rows",
        "drop_table",
        "drop_database",
    }
)


class McpIntegrationError(RuntimeError):
    """Raised for sanitized MCP failures."""


class McpClientProtocol(Protocol):
    def list_tools(self) -> list[str]: ...

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any: ...


def is_tool_allowed(tool_name: str) -> bool:
    return tool_name in ALLOWED_MCP_TOOLS and tool_name not in DENIED_MCP_TOOLS


class CockroachManagedMcpClient:
    """Small sync wrapper around the official MCP Python SDK."""

    def __init__(self, settings: Settings, timeout_seconds: float = 10.0) -> None:
        self._settings = settings
        self._timeout_seconds = timeout_seconds

    def list_tools(self) -> list[str]:
        return asyncio.run(self._list_tools_async())

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not is_tool_allowed(tool_name):
            raise McpIntegrationError("MCP tool is not allowed by OrphanProof read-only policy")
        return asyncio.run(self._call_tool_async(tool_name, arguments))

    def capability_report(self, connect: bool = False) -> ManagedMcpCapabilityReport:
        configured = self._settings.mcp_is_configured()
        if not configured:
            return ManagedMcpCapabilityReport(
                configured=False,
                connected=False,
                allowed_tools=sorted(ALLOWED_MCP_TOOLS),
                error="MCP runtime configuration is not present",
            )
        if not connect:
            return ManagedMcpCapabilityReport(
                configured=True,
                connected=False,
                allowed_tools=sorted(ALLOWED_MCP_TOOLS),
            )
        try:
            tools = self.list_tools()
        except Exception as exc:
            raise McpIntegrationError(_sanitize_mcp_error(exc)) from exc
        return ManagedMcpCapabilityReport(
            configured=True,
            connected=True,
            allowed_tools=sorted(tool for tool in tools if is_tool_allowed(tool)),
        )

    async def _list_tools_async(self) -> list[str]:
        async with self._session() as session:
            result = await asyncio.wait_for(session.list_tools(), timeout=self._timeout_seconds)
            return [tool.name for tool in result.tools]

    async def _call_tool_async(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with self._session() as session:
            return await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=self._timeout_seconds,
            )

    def _headers(self) -> dict[str, str]:
        if not self._settings.mcp_is_configured():
            raise McpIntegrationError("MCP runtime configuration is not present")
        assert self._settings.mcp_cluster_id is not None
        assert self._settings.mcp_bearer_token is not None
        return {
            "Authorization": "Bearer " + self._settings.mcp_bearer_token.get_secret_value(),
            "mcp-cluster-id": self._settings.mcp_cluster_id.get_secret_value(),
        }

    def _session(self) -> Any:
        if not self._settings.mcp_url.startswith("https://"):
            raise McpIntegrationError("MCP URL must use HTTPS")
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except Exception as exc:  # pragma: no cover - depends on optional package install
            raise McpIntegrationError("official MCP Python SDK is not installed") from exc

        class _SessionContext:
            def __init__(self, outer: CockroachManagedMcpClient) -> None:
                self._outer = outer
                self._http_context = None
                self._session_context = None
                self._session = None

            async def __aenter__(self) -> Any:
                self._http_context = streamablehttp_client(
                    self._outer._settings.mcp_url,
                    headers=self._outer._headers(),
                )
                read_stream, write_stream, _ = await self._http_context.__aenter__()
                self._session_context = ClientSession(read_stream, write_stream)
                self._session = await self._session_context.__aenter__()
                await self._session.initialize()
                return self._session

            async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
                if self._session_context is not None:
                    await self._session_context.__aexit__(exc_type, exc, tb)
                if self._http_context is not None:
                    await self._http_context.__aexit__(exc_type, exc, tb)

        return _SessionContext(self)


def _sanitize_mcp_error(exc: Exception) -> str:
    name = exc.__class__.__name__
    text = str(exc).splitlines()[0][:120]
    for marker in ("Bearer ", "ORPHANPROOF_MCP_BEARER_TOKEN", "ORPHANPROOF_MCP_CLUSTER_ID"):
        text = text.replace(marker, "[REDACTED]")
    return f"MCP connection failed: {name}: {text}"
