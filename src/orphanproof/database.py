"""Read-only database connection helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
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
            return self._database_url
        if self._settings is None:
            raise RuntimeError("DATABASE_URL is required for the live repository")
        return self._settings.require_database_url()

    @contextmanager
    def connect(self) -> Iterator[Any]:
        connection = psycopg.connect(self.database_url, row_factory=dict_row)
        try:
            yield connection
        finally:
            connection.close()
