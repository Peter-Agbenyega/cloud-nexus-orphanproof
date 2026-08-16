"""Read-only database connection helpers."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from orphanproof.config import Settings


class Database:
    """Creates psycopg connections only when an endpoint or caller asks for one."""

    def __init__(self, database_url: str | None = None, settings: Settings | None = None):
        self._database_url = database_url
        self._settings = settings

    @property
    def database_url(self) -> str:
        if self._database_url:
            return _with_resolved_root_cert(self._database_url)
        if self._settings is None:
            raise RuntimeError("DATABASE_URL is required for the live repository")
        return _with_resolved_root_cert(self._settings.require_database_url())

    @contextmanager
    def connect(self) -> Iterator[Any]:
        connection = psycopg.connect(self.database_url, row_factory=dict_row)
        try:
            yield connection
        finally:
            connection.close()


def _with_resolved_root_cert(database_url: str) -> str:
    info = conninfo_to_dict(database_url)
    sslmode = info.get("sslmode")
    if sslmode is None or sslmode.lower() not in {"verify-full", "verify-ca"}:
        return database_url
    if "sslrootcert" in info:
        return database_url

    explicit_root = os.getenv("ORPHANPROOF_DATABASE_SSLROOTCERT")
    if explicit_root:
        info["sslrootcert"] = explicit_root
        return make_conninfo(**info)

    local_root = os.path.expanduser("~/.postgresql/root.crt")
    if os.path.exists(local_root):
        info["sslrootcert"] = local_root
        return make_conninfo(**info)

    return database_url
