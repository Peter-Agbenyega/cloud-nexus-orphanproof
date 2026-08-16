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
            return _with_system_root_cert(self._database_url)
        if self._settings is None:
            raise RuntimeError("DATABASE_URL is required for the live repository")
        return _with_system_root_cert(self._settings.require_database_url())

    @contextmanager
    def connect(self) -> Iterator[Any]:
        connection = psycopg.connect(self.database_url, row_factory=dict_row)
        try:
            yield connection
        finally:
            connection.close()


def _with_system_root_cert(database_url: str) -> str:
    info = conninfo_to_dict(database_url)
    sslmode = info.get("sslmode")
    if sslmode and sslmode.lower() != "disable":
        packaged_root = os.getenv("ORPHANPROOF_DATABASE_SSLROOTCERT")
        if packaged_root:
            info["sslrootcert"] = packaged_root
            return make_conninfo(**info)
    if sslmode and sslmode.lower() != "disable" and "sslrootcert" not in info:
        info["sslrootcert"] = "system"
        return make_conninfo(**info)
    return database_url
