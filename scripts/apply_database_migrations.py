#!/usr/bin/env python3
"""Run the local CockroachDB memory schema migration or verifier with psql."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
MIGRATION_SQL = REPO_ROOT / "db" / "migrations" / "001_initial_memory_schema.sql"
VERIFICATION_SQL = REPO_ROOT / "db" / "verification" / "001_verify_memory_schema.sql"
PGSSLROOTCERT = Path.home() / ".postgresql" / "root.crt"
HOMEBREW_PSQL = Path("/opt/homebrew/opt/libpq/bin/psql")
COMMANDS = {
    "migrate": MIGRATION_SQL,
    "verify": VERIFICATION_SQL,
}


class MigrationConfigError(RuntimeError):
    """Raised when local migration configuration is incomplete."""


def fail(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_database_url(env_path: Path) -> str:
    if not env_path.exists():
        raise MigrationConfigError("local .env file is missing")

    with env_path.open("r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            if key.strip() != "DATABASE_URL":
                continue

            value = value.strip()
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]
            if value:
                return value

    raise MigrationConfigError("required database URL setting is missing")


def database_url_to_pg_env(database_url: str) -> dict[str, str]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise MigrationConfigError("database URL must use the postgres protocol")

    try:
        port = parsed.port
    except ValueError as exc:
        raise MigrationConfigError("database URL contains an invalid port") from exc

    required_fields = {
        "host": parsed.hostname,
        "port": port,
        "database": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
    }
    missing = [name for name, value in required_fields.items() if not value]
    if missing:
        raise MigrationConfigError(
            "database URL is missing required field(s): " + ", ".join(missing)
        )

    query = parse_qs(parsed.query)
    sslmode = query.get("sslmode", ["verify-full"])[0] or "verify-full"

    return {
        "PGHOST": parsed.hostname or "",
        "PGPORT": str(port),
        "PGDATABASE": unquote(parsed.path.lstrip("/")),
        "PGUSER": unquote(parsed.username or ""),
        "PGPASSWORD": unquote(parsed.password or ""),
        "PGSSLMODE": sslmode,
        "PGSSLROOTCERT": str(PGSSLROOTCERT),
    }


def find_psql() -> str:
    discovered = shutil.which("psql")
    if discovered:
        return discovered
    if HOMEBREW_PSQL.exists():
        return str(HOMEBREW_PSQL)
    raise MigrationConfigError("psql was not found")


def run_sql(command: str, sql_path: Path) -> int:
    if not sql_path.exists():
        raise MigrationConfigError(f"SQL file is missing for {command}")
    if not PGSSLROOTCERT.exists():
        raise MigrationConfigError("CockroachDB CA certificate is missing")

    database_url = load_database_url(ENV_PATH)
    pg_env = database_url_to_pg_env(database_url)
    psql = find_psql()

    env = os.environ.copy()
    env.update(pg_env)
    env.update(
        {
            "PSQL_PAGER": "cat",
            "PAGER": "cat",
        }
    )

    print(f"starting database {command}", flush=True)
    result = subprocess.run(
        [psql, "-X", "-v", "ON_ERROR_STOP=1", "-P", "pager=off", "-f", str(sql_path)],
        env=env,
        check=False,
    )
    if result.returncode == 0:
        print(f"database {command} completed successfully", flush=True)
    else:
        print(f"database {command} failed", file=sys.stderr, flush=True)
    return result.returncode


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in COMMANDS:
        fail("usage: python3 scripts/apply_database_migrations.py {migrate|verify}", 2)

    command = argv[1]
    try:
        return run_sql(command, COMMANDS[command])
    except MigrationConfigError as exc:
        fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
