#!/usr/bin/env python3
"""Safely verify CockroachDB Cloud Managed MCP read capability."""
# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from orphanproof.config import Settings
from orphanproof.mcp_integration import CockroachManagedMcpClient, is_tool_allowed


def main() -> int:
    settings = Settings()
    print("MCP_PROVIDER=cockroachdb_cloud_managed_mcp")
    print(f"MCP_CLUSTER_ID_PRESENT={settings.mcp_cluster_id is not None}")
    print(f"MCP_AUTH_PRESENT={settings.mcp_bearer_token is not None}")
    if not settings.mcp_is_configured():
        print("MCP_LIVE_VERIFICATION=SKIPPED")
        return 0

    client = CockroachManagedMcpClient(settings)
    tools = client.list_tools()
    select_available = "select_query" in tools and is_tool_allowed("select_query")
    write_tools_allowed = any(
        is_tool_allowed(tool)
        for tool in ("create_database", "create_table", "insert_rows", "delete_rows")
    )
    print("MCP_CONNECTED=True")
    print(f"MCP_SELECT_QUERY_AVAILABLE={select_available}")
    print(f"MCP_WRITE_TOOLS_ALLOWED_BY_APP={write_tools_allowed}")
    if not select_available:
        print("MCP_ORPHANPROOF_READ_VERIFIED=False")
        return 1
    client.call_tool(
        "select_query",
        {
            "query": "SELECT COUNT(*) AS resource_count FROM orphanproof.resources",
        },
    )
    print("MCP_ORPHANPROOF_READ_VERIFIED=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
