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


def load_settings(env_file: Path = REPO_ROOT / ".env") -> Settings:
    return Settings(_env_file=env_file, _env_file_encoding="utf-8")


def build_status_lines(settings: Settings) -> list[str]:
    lines = [
        "MCP_PROVIDER=cockroachdb_cloud_managed_mcp",
        f"MCP_CLUSTER_ID_PRESENT={settings.mcp_cluster_id is not None}",
        f"MCP_AUTH_PRESENT={settings.mcp_bearer_token is not None}",
    ]
    if not settings.mcp_is_configured():
        lines.append("MCP_LIVE_VERIFICATION=SKIPPED")
    return lines


def main() -> int:
    settings = load_settings()
    for line in build_status_lines(settings):
        print(line)
    if not settings.mcp_is_configured():
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
